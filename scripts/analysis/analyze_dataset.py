#!/usr/bin/env python3
"""
Comprehensive dataset analysis for heat pump performance data.

Analyzes:
- Dataset structure (files, manufacturers, models, variants)
- Data availability by EN standard
- Cold climate performance statistics (COP and SCOP)
- Manufacturer rankings
"""

import json
from pathlib import Path
from collections import defaultdict, Counter
import statistics


def analyze_dataset_structure():
    """Analyze basic dataset structure."""
    print("="*80)
    print("DATASET STRUCTURE ANALYSIS")
    print("="*80 + "\n")
    
    db_dir = Path('data/database')
    db_files = list(db_dir.glob('*.json'))
    
    manufacturers = set()
    models = set()
    all_variants = []
    
    for db_file in db_files:
        try:
            with open(db_file) as f:
                data = json.load(f)
            
            metadata = data.get('file_metadata', {})
            manufacturer = metadata.get('Manufacturer', 'Unknown')
            model = metadata.get('Modelname', 'Unknown')
            
            manufacturers.add(manufacturer)
            models.add(f"{manufacturer}::{model}")
            
            for hp in data.get('heat_pumps', []):
                variant = hp.get('variant', '')
                all_variants.append({
                    'manufacturer': manufacturer,
                    'model': model,
                    'variant': variant
                })
        
        except (json.JSONDecodeError, KeyError):
            continue
    
    print(f"Database Files: {len(db_files):,}")
    print(f"Unique Manufacturers: {len(manufacturers):,}")
    print(f"Unique Model Families: {len(models):,}")
    print(f"Total Heat Pump Variants: {len(all_variants):,}")
    print(f"Average Variants per Model: {len(all_variants) / len(models):.1f}")


def analyze_data_availability():
    """Analyze what data is available by EN standard."""
    print("\n" + "="*80)
    print("DATA AVAILABILITY BY EN STANDARD")
    print("="*80 + "\n")
    
    db_dir = Path('data/database')
    
    en_code_counts = Counter()
    en_code_files = defaultdict(set)
    
    for db_file in db_dir.glob('*.json'):
        try:
            with open(db_file) as f:
                data = json.load(f)
            
            for hp in data.get('heat_pumps', []):
                measurements = hp.get('measurements', {})
                
                for en_code in measurements.keys():
                    en_code_counts[en_code] += 1
                    en_code_files[en_code].add(db_file.name)
        
        except (json.JSONDecodeError, KeyError):
            continue
    
    # Categorize EN codes
    categories = {
        'EN14825': [],  # Seasonal performance
        'EN14511': [],  # Primary performance
        'EN16147': [],  # DHW
        'EN12102': [],  # Sound
        'Other': []
    }
    
    for en_code, count in en_code_counts.items():
        if 'EN14825' in en_code:
            categories['EN14825'].append((en_code, count, len(en_code_files[en_code])))
        elif 'EN14511' in en_code:
            categories['EN14511'].append((en_code, count, len(en_code_files[en_code])))
        elif 'EN16147' in en_code:
            categories['EN16147'].append((en_code, count, len(en_code_files[en_code])))
        elif 'EN12102' in en_code:
            categories['EN12102'].append((en_code, count, len(en_code_files[en_code])))
        else:
            categories['Other'].append((en_code, count, len(en_code_files[en_code])))
    
    for category, codes in categories.items():
        if codes:
            print(f"\n{category}:")
            for en_code, count, file_count in sorted(codes, key=lambda x: -x[1])[:10]:
                print(f"  {en_code:30s}: {count:6,} measurements from {file_count:4,} files")


def analyze_cold_climate_performance():
    """Analyze cold climate COP and SCOP statistics."""
    print("\n" + "="*80)
    print("COLD CLIMATE PERFORMANCE ANALYSIS")
    print("="*80 + "\n")
    
    db_dir = Path('data/database')
    
    # Cold climate is dimension 4_2_0_0 (low temp, colder climate)
    # COP at -7°C is dimension 4_10_0_0 (specific test point)
    
    cold_climate_cops = []
    cold_climate_scops = []
    manufacturer_data = defaultdict(lambda: {'cops': [], 'scops': []})
    
    for db_file in db_dir.glob('*.json'):
        try:
            with open(db_file) as f:
                data = json.load(f)
            
            manufacturer = data.get('file_metadata', {}).get('Manufacturer', 'Unknown')
            
            for hp in data.get('heat_pumps', []):
                measurements = hp.get('measurements', {})
                
                # Get COP at -7°C (dimension 4_10_0_0)
                cop_data = measurements.get('EN14511_013', {})
                if '4_10_0_0' in cop_data:
                    try:
                        cop = float(cop_data['4_10_0_0'])
                        if 1.0 <= cop <= 10.0:
                            cold_climate_cops.append(cop)
                            manufacturer_data[manufacturer]['cops'].append(cop)
                    except (ValueError, TypeError):
                        pass
                
                # Get SCOP for colder climate (dimension 4_2_0_0)
                scop_data = measurements.get('EN14825_003', {})
                if '4_2_0_0' in scop_data:
                    try:
                        scop = float(scop_data['4_2_0_0'])
                        if 1.0 <= scop <= 10.0:
                            cold_climate_scops.append(scop)
                            manufacturer_data[manufacturer]['scops'].append(scop)
                    except (ValueError, TypeError):
                        pass
        
        except (json.JSONDecodeError, KeyError):
            continue
    
    # COP Statistics
    if cold_climate_cops:
        print("COLD CLIMATE COP (at -7°C, dimension 4_10_0_0):")
        print(f"  Heat pumps with data: {len(cold_climate_cops):,}")
        print(f"  Mean COP: {statistics.mean(cold_climate_cops):.2f}")
        print(f"  Median COP: {statistics.median(cold_climate_cops):.2f}")
        print(f"  Std Dev: {statistics.stdev(cold_climate_cops):.2f}")
        print(f"  Min COP: {min(cold_climate_cops):.2f}")
        print(f"  Max COP: {max(cold_climate_cops):.2f}")
        
        print(f"\n  COP Distribution:")
        ranges = [(0, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 10)]
        for low, high in ranges:
            count = sum(1 for c in cold_climate_cops if low <= c < high)
            pct = 100 * count / len(cold_climate_cops)
            print(f"    {low:.1f} - {high:.1f}: {count:5,} ({pct:5.1f}%)")
    
    # SCOP Statistics
    if cold_climate_scops:
        print(f"\nCOLD CLIMATE SCOP (Colder climate zone, dimension 4_2_0_0):")
        print(f"  Heat pumps with data: {len(cold_climate_scops):,}")
        print(f"  Mean SCOP: {statistics.mean(cold_climate_scops):.2f}")
        print(f"  Median SCOP: {statistics.median(cold_climate_scops):.2f}")
        print(f"  Std Dev: {statistics.stdev(cold_climate_scops):.2f}")
        print(f"  Min SCOP: {min(cold_climate_scops):.2f}")
        print(f"  Max SCOP: {max(cold_climate_scops):.2f}")
        
        print(f"\n  SCOP Distribution:")
        ranges = [(0, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 10)]
        for low, high in ranges:
            count = sum(1 for s in cold_climate_scops if low <= s < high)
            pct = 100 * count / len(cold_climate_scops)
            print(f"    {low:.1f} - {high:.1f}: {count:5,} ({pct:5.1f}%)")
    
    # Overlap analysis
    print(f"\n  Heat pumps with BOTH COP and SCOP: Analysis...")
    both_count = sum(1 for mfr_data in manufacturer_data.values() 
                     if mfr_data['cops'] and mfr_data['scops'])
    print(f"  Manufacturers with both metrics: {both_count}")
    
    # Top manufacturers
    print("\n" + "="*80)
    print("TOP MANUFACTURERS BY COLD CLIMATE DATA")
    print("="*80 + "\n")
    
    mfr_summary = []
    for mfr, data in manufacturer_data.items():
        if data['scops']:
            mfr_summary.append({
                'manufacturer': mfr,
                'count': len(data['scops']),
                'avg_scop': statistics.mean(data['scops'])
            })
    
    mfr_summary.sort(key=lambda x: -x['count'])
    
    print("By Data Availability:")
    for item in mfr_summary[:20]:
        print(f"  {item['manufacturer'][:50]:50s}: {item['count']:4,} heat pumps, avg SCOP {item['avg_scop']:.2f}")


if __name__ == '__main__':
    analyze_dataset_structure()
    analyze_data_availability()
    analyze_cold_climate_performance()
