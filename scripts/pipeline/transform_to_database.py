#!/usr/bin/env python3
"""
Transform grouped JSONL files into a structured database format.

This script processes the staged JSONL files and creates a normalized JSON database
with proper grouping by heat pump and separation of metadata from measurements.

Structure:
- Each file contains one or more heat pumps
- Each heat pump has:
  - title: Model name
  - metadata (info=0): File-level constants
  - hp_properties (info=1): Heat pump-specific properties
  - measurements (info=2): Dimensioned measurement arrays
"""

import json
from pathlib import Path
from collections import defaultdict
import sys
from datetime import datetime


# Classification constants
MEASUREMENT_PREFIXES = ('EN14825', 'EN14511', 'EN16147', 'EN12102')
PROBLEMATIC_FILES = {
    '_Advantix_S.p.A.i-290_0106.jsonl',
    '_Ariston_Thermo_GroupNIMBUS_90_M_-_ARIANEXT_90_M_-_AEROTOP_MONO_09_-_ENERGION_M_9.jsonl',
    '_Ariston_Thermo_GroupNIMBUS_ARIANEXT_AEROTOP_ENERGION_120_150_M_-_COMPACT.jsonl',
    '_Ariston_Thermo_GroupNIMBUS_ARIANEXT_AEROTOP_ENERGION_120_150_M_-_Plus_LB.jsonl',
    '_Ariston_Thermo_GroupNIMBUS_ARIANEXT_AEROTOP_ENERGION_35_50_S_-_COMPACT.jsonl',
    '_BAXI_Climatización_S.L.UIridium_9.jsonl',
    '_Bosch_Thermotechnik_GmbHBosch_CS5800i_6800iAW_10_12_OR.jsonl',
    '_DAIKIN_Europe_N.V.DAIKIN_ALTHERMA_3_M_9KW.jsonl',
    '_DAIKIN_Europe_N.V.DAIKIN_ALTHERMA_3_R_ECH2O_08KW_(300L)_(_A).jsonl',
    '_DAIKIN_Europe_N.V.Daikin_Altherma_3_R_MT_ECH2O_08-12_kW_(300L).jsonl'
}


def load_staging_jsonl(file_path):
    """Load all records from a JSONL file."""
    records = []
    with open(file_path) as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def normalize_indoor_type(indoor):
    """Fix anomalous indoor type values."""
    if indoor == 'EN14511_2_001':
        return '0'
    return indoor


class TransformationLogger:
    """Comprehensive logging for transformation process."""
    
    def __init__(self, log_dir):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.events = []
        self.skipped_records = []
        self.corrupted_records = []
        self.warnings = []
        self.errors = []
        self.file_stats = defaultdict(dict)
    
    def log_skipped_record(self, file_name, hp_title, reason, record=None):
        """Log a skipped record."""
        self.skipped_records.append({
            'file': file_name,
            'heat_pump': hp_title,
            'reason': reason,
            'record': record,
            'timestamp': datetime.now().isoformat()
        })
    
    def log_corrupted_record(self, file_name, hp_title, varname, issue, record=None):
        """Log a corrupted record that was fixed or skipped."""
        self.corrupted_records.append({
            'file': file_name,
            'heat_pump': hp_title,
            'varname': varname,
            'issue': issue,
            'record': record,
            'timestamp': datetime.now().isoformat()
        })
    
    def log_warning(self, file_name, message):
        """Log a warning."""
        self.warnings.append({
            'file': file_name,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
    
    def log_error(self, file_name, error, traceback_info=None):
        """Log an error."""
        self.errors.append({
            'file': file_name,
            'error': str(error),
            'traceback': traceback_info,
            'timestamp': datetime.now().isoformat()
        })
    
    def record_file_stats(self, file_name, stats):
        """Record statistics for a file."""
        self.file_stats[file_name] = {
            'heat_pumps_extracted': stats.get('heat_pumps', 0),
            'measurements_extracted': stats.get('measurements', 0),
            'records_skipped': stats.get('skipped', 0),
            'records_corrupted': stats.get('corrupted', 0),
            'timestamp': datetime.now().isoformat()
        }
    
    def save_logs(self):
        """Save all logs to files."""
        logs = {
            'transformation_summary': {
                'total_skipped_records': len(self.skipped_records),
                'total_corrupted_records': len(self.corrupted_records),
                'total_warnings': len(self.warnings),
                'total_errors': len(self.errors),
                'files_with_stats': len(self.file_stats),
                'generated_at': datetime.now().isoformat()
            },
            'skipped_records': self.skipped_records,
            'corrupted_records': self.corrupted_records,
            'warnings': self.warnings,
            'errors': self.errors,
            'file_statistics': dict(self.file_stats)
        }
        
        log_file = self.log_dir / 'transformation_log.json'
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)
        
        return log_file


def group_by_heat_pump(records):
    """
    Group records by heat pump (title field marks boundaries).
    Returns list of heat pump groups.
    """
    hp_groups = []
    current_group = []
    
    for rec in records:
        if rec.get('varname') == 'title':
            if current_group:
                hp_groups.append(current_group)
            current_group = [rec]  # Start new group with title
        else:
            current_group.append(rec)
    
    if current_group:
        hp_groups.append(current_group)
    
    return hp_groups


def extract_file_metadata(records):
    """Extract file-level metadata (info=0 records)."""
    metadata = {}
    for rec in records:
        if rec.get('info') == '0':
            varname = rec.get('varname')
            value = rec.get('value')
            if varname and varname not in ['title']:
                metadata[varname] = value
    return metadata


def extract_hp_metadata(records):
    """Extract heat pump metadata (info=1 records, camelCase varnames)."""
    metadata = {}
    for rec in records:
        if rec.get('info') == '1':
            varname = rec.get('varname')
            value = rec.get('value')
            if varname and varname != 'title':
                metadata[varname] = value
    return metadata


def extract_measurements(records):
    """
    Extract measurements (info=2, EN* varnames).
    Returns dict keyed by (temp, climate, indoor, hptype) with varname->value mappings.
    """
    measurements = defaultdict(dict)
    
    for rec in records:
        if rec.get('info') != '2':
            continue
        
        varname = rec.get('varname', '')
        if not varname.startswith(MEASUREMENT_PREFIXES):
            continue
        
        # Skip corrupted record
        if rec.get('indoorunittype') == 'EN14511_2_001':
            continue
        
        # Normalize dimensions
        temp = rec.get('temperature')
        climate = rec.get('climate')
        indoor = normalize_indoor_type(rec.get('indoorunittype'))
        hptype = rec.get('hptype')
        value = rec.get('value')
        
        # Create dimension key
        dim_key = (temp, climate, indoor, hptype)
        measurements[dim_key][varname] = value
    
    return measurements


def transform_file(jsonl_file, logger):
    """
    Transform a single JSONL file into structured database format.
    Returns dict with file metadata and heat pump array.
    """
    records = load_staging_jsonl(jsonl_file)
    
    if not records:
        logger.log_warning(jsonl_file.name, "File is empty")
        return None
    
    # Extract file metadata (shared across all HPs in this file)
    file_metadata = extract_file_metadata(records)
    
    # Group records by heat pump
    hp_groups = group_by_heat_pump(records)
    
    if not hp_groups:
        logger.log_warning(jsonl_file.name, "No heat pump groups found")
        return None
    
    heat_pumps = []
    file_stats = {
        'heat_pumps': 0,
        'measurements': 0,
        'skipped': 0,
        'corrupted': 0
    }
    
    for hp_idx, hp_group in enumerate(hp_groups):
        # Get heat pump title
        title_rec = next((r for r in hp_group if r.get('varname') == 'title'), None)
        if not title_rec:
            logger.log_skipped_record(
                jsonl_file.name,
                f"HP#{hp_idx}",
                "No title record found",
                None
            )
            file_stats['skipped'] += 1
            continue
        
        hp_title = title_rec.get('value', 'Unknown')
        
        # Extract HP metadata and measurements
        hp_meta = extract_hp_metadata(hp_group)
        measurements = extract_measurements(hp_group)
        
        if not measurements:
            logger.log_warning(
                jsonl_file.name,
                f"Heat pump '{hp_title}' has no measurements"
            )
        
        # Check for anomalies
        for rec in hp_group:
            if rec.get('info') == '2' and rec.get('varname', '').startswith(MEASUREMENT_PREFIXES):
                if rec.get('indoorunittype') == 'EN14511_2_001':
                    logger.log_corrupted_record(
                        jsonl_file.name,
                        hp_title,
                        rec.get('varname'),
                        "Anomalous indoorunittype (varname copied into field)",
                        rec
                    )
                    file_stats['corrupted'] += 1
        
        # Build heat pump object
        hp_obj = {
            'title': hp_title,
            'properties': hp_meta if hp_meta else {},
            'measurements': {}
        }
        
        # Convert measurements to structured format
        # Group by varname, then by dimensions (convert tuple keys to strings for JSON)
        measurements_by_varname = defaultdict(dict)
        for dim_key, values_dict in measurements.items():
            # Convert dimension tuple to string key for JSON compatibility
            dim_key_str = f"{dim_key[0]}_{dim_key[1]}_{dim_key[2]}_{dim_key[3]}"
            for varname, value in values_dict.items():
                if varname not in measurements_by_varname:
                    measurements_by_varname[varname] = {}
                measurements_by_varname[varname][dim_key_str] = value
        
        # Build measurement structure
        for varname in sorted(measurements_by_varname.keys()):
            hp_obj['measurements'][varname] = measurements_by_varname[varname]
        
        heat_pumps.append(hp_obj)
        file_stats['heat_pumps'] += 1
        file_stats['measurements'] += len(hp_obj['measurements'])
    
    if not heat_pumps:
        logger.log_warning(jsonl_file.name, "No heat pumps successfully extracted")
        return None
    
    logger.record_file_stats(jsonl_file.name, file_stats)
    
    return {
        'file_metadata': file_metadata,
        'heat_pumps': heat_pumps
    }


def main():
    staging_dir = Path('data/staging')
    output_dir = Path('data/database')
    log_dir = Path('data/logs')
    
    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize logger
    logger = TransformationLogger(log_dir)
    
    # Get all valid JSONL files
    jsonl_files = sorted([f for f in staging_dir.glob('*.jsonl') 
                         if f.name not in PROBLEMATIC_FILES])
    
    print(f"Transforming {len(jsonl_files)} files to database...\n")
    
    stats = {
        'total_files': len(jsonl_files),
        'successful': 0,
        'failed': 0,
        'total_heat_pumps': 0,
        'total_measurements': 0,
    }
    
    for i, jsonl_file in enumerate(jsonl_files):
        if (i + 1) % 100 == 0:
            print(f"Progress: {i+1}/{len(jsonl_files)}")
        
        try:
            db_obj = transform_file(jsonl_file, logger)
            
            if db_obj is None:
                stats['failed'] += 1
                continue
            
            # Write to JSON
            output_file = output_dir / (jsonl_file.stem.replace('_', '__') + '.json')
            with open(output_file, 'w') as f:
                json.dump(db_obj, f, indent=2)
            
            stats['successful'] += 1
            stats['total_heat_pumps'] += len(db_obj['heat_pumps'])
            
            # Count measurements
            for hp in db_obj['heat_pumps']:
                for varname, dims in hp['measurements'].items():
                    stats['total_measurements'] += len(dims)
        
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.log_error(jsonl_file.name, e, error_trace)
            print(f"Error processing {jsonl_file.name}: {e}")
            stats['failed'] += 1
    
    print("\n" + "="*100)
    print("TRANSFORMATION SUMMARY")
    print("="*100)
    print(f"\nFiles processed: {stats['successful']}/{stats['total_files']}")
    print(f"Files failed: {stats['failed']}")
    print(f"Total heat pumps extracted: {stats['total_heat_pumps']:,}")
    print(f"Total measurement data points: {stats['total_measurements']:,}")
    print(f"\nDatabase written to: {output_dir}")
    
    # Save logs
    log_file = logger.save_logs()
    print(f"Transformation log written to: {log_file}")
    
    # Write summary
    summary = {
        'transformation_date': datetime.now().isoformat(),
        'files_processed': stats['successful'],
        'files_failed': stats['failed'],
        'total_heat_pumps': stats['total_heat_pumps'],
        'total_measurements': stats['total_measurements'],
        'log_issues': {
            'skipped_records': len(logger.skipped_records),
            'corrupted_records': len(logger.corrupted_records),
            'warnings': len(logger.warnings),
            'errors': len(logger.errors)
        },
        'output_directory': str(output_dir),
        'log_directory': str(log_dir)
    }
    
    with open(output_dir / 'summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print("\n" + "-"*100)
    print("LOG SUMMARY")
    print("-"*100)
    print(f"  Skipped records: {len(logger.skipped_records)}")
    print(f"  Corrupted records (fixed/skipped): {len(logger.corrupted_records)}")
    print(f"  Warnings: {len(logger.warnings)}")
    print(f"  Errors: {len(logger.errors)}")
    
    if logger.warnings:
        print(f"\n⚠️  WARNINGS:")
        for warn in logger.warnings[:5]:
            print(f"  • {warn['file']}: {warn['message']}")
        if len(logger.warnings) > 5:
            print(f"  ... and {len(logger.warnings) - 5} more")
    
    if logger.errors:
        print(f"\n❌ ERRORS:")
        for err in logger.errors[:5]:
            print(f"  • {err['file']}: {err['error']}")
        if len(logger.errors) > 5:
            print(f"  ... and {len(logger.errors) - 5} more")


if __name__ == '__main__':
    main()
