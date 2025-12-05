import pandas as pd
import pytest

from scripts.analysis.calculate_scop_en14825 import SCOPCalculator


def _annex_h_calculator():
    test_points = {
        'A': {'Tj': -7, 'Pdh': 9.55, 'COPd': 3.26},
        'B': {'Tj': 2, 'Pdh': 11.17, 'COPd': 4.00},
        'C': {'Tj': 7, 'Pdh': 12.66, 'COPd': 4.91},
        'D': {'Tj': 12, 'Pdh': 14.3, 'COPd': 5.5},
        'E': {'Tj': -10, 'Pdh': 7.8, 'COPd': 2.6},
        'F': {'Tj': -6, 'Pdh': 9.7, 'COPd': 3.3}
    }

    return SCOPCalculator(
        climate='Average',
        Pdesignh=11.46,
        test_points=test_points,
        Tbiv=-6,
        TOL=-10,
        Cd=0.9
    )


def test_scop_metrics_match_annex_h():
    calculator = SCOPCalculator(
        climate='Average',
        Pdesignh=None,
        test_points={
            'A': {'Tj': -7, 'Pdh': 9.55, 'COPd': 3.26},
            'B': {'Tj': 2, 'Pdh': 11.17, 'COPd': 4.00},
            'C': {'Tj': 7, 'Pdh': 12.66, 'COPd': 4.91},
            'D': {'Tj': 12, 'Pdh': 14.3, 'COPd': 5.5},
            'E': {'Tj': -10, 'Pdh': 7.8, 'COPd': 2.6},
            'F': {'Tj': -6, 'Pdh': 9.7, 'COPd': 3.3}
        },
        Tbiv=-6,
        TOL=-10,
        Cd=0.9
    )
    metrics, df_bins = calculator.calculate_scop_on()

    assert metrics['SCOPon'] == pytest.approx(3.598, rel=1e-3)
    assert metrics['SCOP'] == pytest.approx(metrics['SCOP_from_SCOPnet'], rel=1e-3)

    numeric_bins = df_bins[df_bins['j'] != 'TOTAL'].copy()
    numeric_bins['Tj'] = pd.to_numeric(numeric_bins['Tj'], errors='coerce')
    numeric_bins = numeric_bins.dropna(subset=['Tj'])

    tbiv_mask = numeric_bins['Tj'] >= calculator.Tbiv
    assert (numeric_bins.loc[tbiv_mask, 'elbu(Tj)'] == 0).all()

    at_two = numeric_bins.loc[numeric_bins['Tj'] == 2]
    assert not at_two['Pdh(Tj)'].isna().all()
    assert not at_two['COPd(Tj)'].isna().all()


def test_pdesignh_inferred_from_tbiv():
    baseline = _annex_h_calculator()
    calculator = SCOPCalculator(
        climate=baseline.climate,
        Pdesignh=None,
        test_points=baseline.test_points,
        Tbiv=baseline.Tbiv,
        TOL=baseline.TOL,
        Cd=baseline.Cd
    )

    assert calculator.Pdesignh == pytest.approx(baseline.Pdesignh, rel=1e-3)