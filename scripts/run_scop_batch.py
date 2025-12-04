#!/usr/bin/env python3
"""Batch SCOP simulation across the Keymark DuckDB database.

This script iterates over variant/dimension combinations, gathers the
required EN14825 inputs, runs the SCOP calculator, and emits a CSV file
matching ``SCOP_RESULTS_TEMPLATE.md``. Use it to run whole-database
regressions or to spot-check subsets filtered by dimension.
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.calculate_scop_en14825 import SCOPCalculator

BASE_REQUIRED_CODES = [
    'EN14825_002',  # Prated / Pdesignh
    'EN14825_003',  # Reported SCOP
    'EN14825_004',  # Tbiv
    'EN14825_005',  # TOL
    'EN14825_008', 'EN14825_009',  # -7°C
    'EN14825_010', 'EN14825_011',  # +2°C
    'EN14825_012', 'EN14825_013',  # +7°C
    'EN14825_014', 'EN14825_015',  # +12°C
    'EN14825_016', 'EN14825_017',  # Tbiv point
    'EN14825_018', 'EN14825_019',  # TOL point
    'EN14825_023', 'EN14825_024', 'EN14825_025', 'EN14825_026',  # Aux powers
    'EN14825_029',  # Reported Qhe
]

OPTIONAL_CODES = [
    'EN14825_001',  # Reported ηs
    'EN14825_021',  # Cd @ TOL
    'EN14825_047',  # Cd @ -7°C
    'EN14825_048',  # Cd @ +2°C
    'EN14825_049',  # Cd @ +7°C
    'EN14825_050',  # Cd @ +12°C
    'EN14825_051',  # Cd @ -15°C
    'EN14825_044',  # Pdh @ -15°C
    'EN14825_045',  # COP @ -15°C
]

CLIMATE_MAP = {'1': 'Warmer', '2': 'Colder', '3': 'Average'}
APPLICATION_MAP = {
    '4': 'Low temp (35°C)',
    '5': 'Medium temp (55°C)',
    '6': 'High temp (65°C)'
}

CSV_COLUMNS = [
    'manufacturer_name', 'model_name', 'variant_name', 'dimension',
    'application_label', 'climate_label', 'unit_type',
    'pdesignh_reported_kw', 'pdesignh_inferred_kw',
    'tbiv_c', 'tol_c',
    'poff_kw', 'pto_kw', 'psb_kw', 'pck_kw',
    'reported_scop', 'calculated_scop', 'delta_scop_pct',
    'reported_eta_percent', 'calculated_eta_percent', 'delta_eta_pct',
    'reported_qhe_kwh', 'calculated_qhe_active_kwh', 'delta_qhe_pct',
    'scopnet', 'scopon', 'calc_qh_kwh', 'q_sup_kwh', 'q_offmode_kwh',
    'missing_required_en_codes', 'missing_optional_en_codes',
    'status', 'status_message', 'timestamp_utc'
]


@dataclass
class Combo:
    manufacturer: str
    model: str
    variant: str
    dimension: str


def required_codes_for_climate(climate: Optional[str]) -> List[str]:
    codes = BASE_REQUIRED_CODES.copy()
    if climate == 'Warmer':
        codes = [code for code in codes if code not in ('EN14825_008', 'EN14825_009')]
    return codes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run SCOP simulations for every qualifying variant/dimension."
    )
    parser.add_argument(
        '--db-path', default='data/keymark.duckdb',
        help='Path to the DuckDB database (default: data/keymark.duckdb)'
    )
    parser.add_argument(
        '--output', default='scop_results.csv',
        help='Destination CSV file (default: scop_results.csv)'
    )
    parser.add_argument(
        '--dimensions', nargs='*',
        help='Optional list of exact dimension tokens to include (e.g. 4_2_0_0)'  # noqa: E501
    )
    parser.add_argument(
        '--unit-type', choices=['air', 'water_brine'], default='air',
        help='Unit type passed to SCOPCalculator (affects ηs correction)'
    )
    parser.add_argument(
        '--limit', type=int, default=None,
        help='Optional max number of variant/dimension combos to process'
    )
    parser.add_argument(
        '--model-type', default=None,
        help="Filter to models whose metadata Type matches the given string (e.g. 'Outdoor Air/Water')"
    )
    parser.add_argument(
        '--include-nonstandard', action='store_true',
        help='Include dimensions outside the [456]_[123]_0_0 pattern'
    )
    parser.add_argument(
        '--quiet', action='store_true',
        help='Suppress per-row progress logs'
    )
    parser.add_argument(
        '--progress-interval', type=int, default=None,
        help='Print progress every N combos (overrides --quiet for those checkpoints)'
    )
    args = parser.parse_args()
    if args.progress_interval is not None and args.progress_interval <= 0:
        parser.error('--progress-interval must be a positive integer')
    return args


def connect(db_path: str) -> duckdb.DuckDBPyConnection:
    try:
        return duckdb.connect(db_path, read_only=True)
    except Exception as exc:  # pragma: no cover - duckdb raises native errors
        print(f"Failed to open DuckDB database at {db_path}: {exc}", file=sys.stderr)
        raise


def fetch_combos(
    con: duckdb.DuckDBPyConnection,
    dimensions: Optional[Sequence[str]],
    include_nonstandard: bool,
    limit: Optional[int],
    model_type: Optional[str],
) -> List[Combo]:
    params: List[str] = []
    where_clauses: List[str] = []

    if dimensions:
        placeholders = ','.join('?' for _ in dimensions)
        where_clauses.append(f"m.dimension IN ({placeholders})")
        params.extend(dimensions)
    elif not include_nonstandard:
        where_clauses.append("regexp_matches(m.dimension, '^[456]_[123]_0_0$')")

    join_clause = ''
    if model_type:
        join_clause = "JOIN models mo USING (manufacturer_name, model_name)"
        where_clauses.append("json_extract_string(mo.metadata, '$.Type') = ?")
        params.append(model_type)

    where_sql = ''
    if where_clauses:
        where_sql = 'WHERE ' + ' AND '.join(where_clauses)

    limit_clause = f'LIMIT {limit}' if limit else ''
    query = f"""
        SELECT DISTINCT m.manufacturer_name, m.model_name, m.variant_name, m.dimension
        FROM measurements m
        {join_clause}
        {where_sql}
        ORDER BY 1, 2, 3, 4
        {limit_clause}
    """
    rows = con.execute(query, params).fetchall()
    return [Combo(*row) for row in rows]


def gather_measurements(con: duckdb.DuckDBPyConnection, combo: Combo) -> Dict[str, float]:
    rows = con.execute(
        """
        SELECT en_code, value
        FROM measurements
        WHERE manufacturer_name = ?
          AND model_name = ?
          AND variant_name = ?
          AND dimension = ?
        """,
        [combo.manufacturer, combo.model, combo.variant, combo.dimension]
    ).fetchall()
    return {code: value for code, value in rows}


def build_row_template(combo: Combo, application: str, climate: str,
                        unit_type: str) -> Dict[str, Optional[float]]:
    return {
        'manufacturer_name': combo.manufacturer,
        'model_name': combo.model,
        'variant_name': combo.variant,
        'dimension': combo.dimension,
        'application_label': application,
        'climate_label': climate,
        'unit_type': unit_type,
        'pdesignh_reported_kw': None,
        'pdesignh_inferred_kw': None,
        'tbiv_c': None,
        'tol_c': None,
        'poff_kw': None,
        'pto_kw': None,
        'psb_kw': None,
        'pck_kw': None,
        'reported_scop': None,
        'calculated_scop': None,
        'delta_scop_pct': None,
        'reported_eta_percent': None,
        'calculated_eta_percent': None,
        'delta_eta_pct': None,
        'reported_qhe_kwh': None,
        'calculated_qhe_active_kwh': None,
        'delta_qhe_pct': None,
        'scopnet': None,
        'scopon': None,
        'calc_qh_kwh': None,
        'q_sup_kwh': None,
        'q_offmode_kwh': None,
        'missing_required_en_codes': '',
        'missing_optional_en_codes': '',
        'status': 'pending',
        'status_message': '',
        'timestamp_utc': datetime.now(timezone.utc).isoformat()
    }


def calculate_percent_delta(calculated: Optional[float], reported: Optional[float]) -> Optional[float]:
    if reported in (None, 0) or calculated is None:
        return None
    return (calculated - reported) / reported * 100.0


def run_calculation(values: Dict[str, float], combo: Combo, application: str,
                    climate: str, unit_type: str, include_minus7: bool) -> Tuple[Dict[str, float], SCOPCalculator]:
    Tbiv = values['EN14825_004']
    TOL = values['EN14825_005']
    test_points: Dict[str, Dict[str, float]] = {}
    if include_minus7:
        test_points['A'] = {
            'Tj': -7,
            'Pdh': values['EN14825_008'],
            'COPd': values['EN14825_009'],
            'Cd': values.get('EN14825_047', 0.9)
        }
    test_points['B'] = {'Tj': 2, 'Pdh': values['EN14825_010'], 'COPd': values['EN14825_011'], 'Cd': values.get('EN14825_048', 0.9)}
    test_points['C'] = {'Tj': 7, 'Pdh': values['EN14825_012'], 'COPd': values['EN14825_013'], 'Cd': values.get('EN14825_049', 0.9)}
    test_points['D'] = {'Tj': 12, 'Pdh': values['EN14825_014'], 'COPd': values['EN14825_015'], 'Cd': values.get('EN14825_050', 0.9)}
    test_points['E'] = {'Tj': TOL, 'Pdh': values['EN14825_018'], 'COPd': values['EN14825_019'], 'Cd': values.get('EN14825_021', 0.9)}
    
    # Tbiv point - No specific Cd code exists, let calculator interpolate
    test_points['F'] = {'Tj': Tbiv, 'Pdh': values['EN14825_016'], 'COPd': values['EN14825_017']}

    # Optional -15°C point (mainly for Colder climate)
    if 'EN14825_044' in values and 'EN14825_045' in values:
        test_points['G'] = {
            'Tj': -15,
            'Pdh': values['EN14825_044'],
            'COPd': values['EN14825_045'],
            'Cd': values.get('EN14825_051', 0.9)
        }

    calculator = SCOPCalculator(
        climate=climate,
        Pdesignh=None,
        test_points=test_points,
        Tbiv=Tbiv,
        TOL=TOL,
        Cd=0.9,
        POFF=values['EN14825_023'] / 1000.0,
        PTO=values['EN14825_024'] / 1000.0,
        PSB=values['EN14825_025'] / 1000.0,
        PCK=values['EN14825_026'] / 1000.0,
        unit_type=unit_type
    )
    metrics, _ = calculator.calculate_scop_on()
    return metrics, calculator


def main() -> None:
    args = parse_args()
    db_path = args.db_path
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    con = connect(db_path)
    combos = fetch_combos(
        con,
        args.dimensions,
        args.include_nonstandard,
        args.limit,
        args.model_type,
    )
    if not combos:
        print("No variant/dimension combinations matched the filters.")
        return

    with output_path.open('w', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS)
        writer.writeheader()

        successes = 0
        failures = 0
        for idx, combo in enumerate(combos, start=1):
            dim_tokens = combo.dimension.split('_')
            app_digit = dim_tokens[0] if dim_tokens else ''
            climate_digit = dim_tokens[1] if len(dim_tokens) > 1 else ''
            application = APPLICATION_MAP.get(app_digit, 'Unknown')
            climate = CLIMATE_MAP.get(climate_digit)

            row = build_row_template(combo, application, climate or 'Unknown', args.unit_type)
            values = gather_measurements(con, combo)
            required_codes = required_codes_for_climate(climate)
            missing_required = [code for code in required_codes if code not in values]
            missing_optional = [code for code in OPTIONAL_CODES if code not in values]
            row['missing_required_en_codes'] = ';'.join(missing_required)
            row['missing_optional_en_codes'] = ';'.join(missing_optional)

            if climate is None:
                row['status'] = 'error'
                row['status_message'] = f"Unsupported climate digit in dimension {combo.dimension}"
                failures += 1
                writer.writerow(row)
                continue

            if missing_required:
                row['status'] = 'missing-data'
                row['status_message'] = 'Missing required EN codes'
                failures += 1
                writer.writerow(row)
                continue

            include_minus7 = 'EN14825_008' in values and 'EN14825_009' in values
            try:
                metrics, calculator = run_calculation(
                    values, combo, application, climate, args.unit_type, include_minus7
                )
            except Exception as exc:  # pragma: no cover - defensive
                row['status'] = 'error'
                row['status_message'] = str(exc)
                failures += 1
                writer.writerow(row)
                continue

            # Populate row with calculated values
            row.update({
                'pdesignh_reported_kw': values.get('EN14825_002'),
                'pdesignh_inferred_kw': calculator.Pdesignh,
                'tbiv_c': values.get('EN14825_004'),
                'tol_c': values.get('EN14825_005'),
                'poff_kw': values.get('EN14825_023') / 1000.0,
                'pto_kw': values.get('EN14825_024') / 1000.0,
                'psb_kw': values.get('EN14825_025') / 1000.0,
                'pck_kw': values.get('EN14825_026') / 1000.0,
                'reported_scop': values.get('EN14825_003'),
                'calculated_scop': metrics['SCOP'],
                'delta_scop_pct': calculate_percent_delta(metrics['SCOP'], values.get('EN14825_003')),
                'reported_eta_percent': values.get('EN14825_001'),
                'calculated_eta_percent': metrics['ηs'],
                'delta_eta_pct': calculate_percent_delta(metrics['ηs'], values.get('EN14825_001')),
                'reported_qhe_kwh': values.get('EN14825_029'),
                'calculated_qhe_active_kwh': metrics['QHE_active'],
                'delta_qhe_pct': calculate_percent_delta(metrics['QHE_active'], values.get('EN14825_029')),
                'scopnet': metrics['SCOPnet'],
                'scopon': metrics['SCOPon'],
                'calc_qh_kwh': metrics['QH'],
                'q_sup_kwh': metrics['QSUP'],
                'q_offmode_kwh': metrics['Q_offmode'],
                'status': 'ok',
                'status_message': ''
            })

            writer.writerow(row)
            successes += 1

            report_progress = False
            if args.progress_interval is not None:
                if idx % args.progress_interval == 0 or idx == len(combos):
                    report_progress = True
            elif not args.quiet and idx % 25 == 0:
                report_progress = True

            if report_progress:
                print(
                    f"Processed {idx} / {len(combos)} combos (successes={successes}, failures={failures})",
                    flush=True
                )

    print(f"Finished. Successes={successes}, Failures/Skipped={failures}. Results saved to {output_path}")


if __name__ == '__main__':
    main()
