#!/usr/bin/env python3
"""
Analyze heat pumps with SCOP data across multiple dimensions.

Dimension structure: TEMP_CLIMATE_INDOOR_HPTYPE
- First digit (4,5): Application temperature (low vs medium supply temp)
- Second digit (1,2,3): Climate zones
  * 1 = Warmer climate (mean SCOP ~5.07)
  * 2 = Colder climate (mean SCOP ~3.65)
  * 3 = Average climate (mean SCOP ~4.08)
- Third/fourth digits: Usually 0 (equipment variants)

Investigates:
- Count of heat pumps with data across multiple dimensions
- Statistical distribution of SCOP values
- Potential duplicates (same specs, different model names)
"""

import json
from pathlib import Path
from collections import defaultdict
import statistics


def analyze_multi_climate_scop():
    """Analyze heat pumps with SCOP data across application temps and climate zones."""
    print("="*70)
    print("MULTI-DIMENSION SCOP ANALYSIS")
    print("="*70 + "\n")
    
    db_files = list(Path('data/database').glob('*.json'))
    
    # Store heat pumps with both climate SCOPs
    heat_pumps_with_both = []
    
    # Track by manufacturer
    manufacturer_counts = defaultdict(int)
    
    # For duplicate detection
    specs_to_models = defaultdict(list)
    
    print("Scanning database files...")
    
    for idx, db_file in enumerate(db_files, 1):
        if idx % 200 == 0:
            print(f"  Progress: {idx}/{len(db_files)}")
        
        try:
            with open(db_file) as f:
                data = json.load(f)
            
            if 'heat_pumps' not in data:
                continue
            
            manufacturer = data['file_metadata'].get('Manufacturer', 'Unknown')
            model_name = data['file_metadata'].get('Modelname', 'Unknown')
            
            for hp in data['heat_pumps']:
                measurements = hp.get('measurements', {})
                
                # Check for SCOP (EN14825_003)
                if 'EN14825_003' not in measurements:
                    continue
                
                scop_dims = measurements['EN14825_003']
                
                # Find low temp application SCOP (dimension 4_X_0_0)
                low_temp_scop = None
                low_temp_dim = None
                for dim_code, value in scop_dims.items():
                    if dim_code.startswith('4_'):
                        try:
                            val = float(value)
                            if 1.0 <= val <= 10.0:
                                low_temp_scop = val
                                low_temp_dim = dim_code
                                break
                        except (ValueError, TypeError):
                            pass
                
                # Find medium temp application SCOP (dimension 5_X_0_0)
                medium_temp_scop = None
                medium_temp_dim = None
                for dim_code, value in scop_dims.items():
                    if dim_code.startswith('5_'):
                        try:
                            val = float(value)
                            if 1.0 <= val <= 10.0:
                                medium_temp_scop = val
                                medium_temp_dim = dim_code
                                break
                        except (ValueError, TypeError):
                            pass
                
                # Only keep if we have both
                if low_temp_scop is not None and medium_temp_scop is not None:
                    hp_info = {
                        'manufacturer': manufacturer,
                        'model_name': model_name,
                        'variant': hp.get('variant', ''),
                        'low_temp_scop': low_temp_scop,
                        'low_temp_dim': low_temp_dim,
                        'medium_temp_scop': medium_temp_scop,
                        'medium_temp_dim': medium_temp_dim,
                        'scop_ratio': medium_temp_scop / low_temp_scop,
                        'file': db_file.name
                    }
                    heat_pumps_with_both.append(hp_info)
                    manufacturer_counts[manufacturer] += 1
                    
                    # Create spec signature for duplicate detection
                    # Round to 2 decimals to catch near-identical units
                    spec_sig = (
                        round(low_temp_scop, 2),
                        round(medium_temp_scop, 2)
                    )
                    specs_to_models[spec_sig].append(hp_info)
        
        except (json.JSONDecodeError, KeyError) as e:
            continue
    
    print(f"\n{'='*70}")
    print("RESULTS:")
    print(f"  Total heat pumps with BOTH application temps: {len(heat_pumps_with_both):,}")
    print(f"  Unique manufacturers: {len(manufacturer_counts)}")
    
    # Statistics on Low Temperature Application SCOP
    low_temp_scops = [hp['low_temp_scop'] for hp in heat_pumps_with_both]
    print(f"\n{'='*70}")
    print("LOW TEMPERATURE APPLICATION SCOP (dimension 4_X_0_0):")
    print(f"  Sample size: {len(low_temp_scops):,}")
    print(f"  Mean: {statistics.mean(low_temp_scops):.2f}")
    print(f"  Median: {statistics.median(low_temp_scops):.2f}")
    print(f"  Std Dev: {statistics.stdev(low_temp_scops):.2f}")
    print(f"  Min: {min(low_temp_scops):.2f}")
    print(f"  Max: {max(low_temp_scops):.2f}")
    print(f"  25th percentile: {statistics.quantiles(low_temp_scops, n=4)[0]:.2f}")
    print(f"  75th percentile: {statistics.quantiles(low_temp_scops, n=4)[2]:.2f}")
    
    print(f"\n  Distribution:")
    ranges = [(0, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 10)]
    for low, high in ranges:
        count = sum(1 for v in low_temp_scops if low <= v < high)
        pct = 100 * count / len(low_temp_scops)
        bar = '█' * int(pct / 2)
        print(f"    {low:.1f} - {high:.1f}: {count:5,} ({pct:5.1f}%) {bar}")
    
    # Statistics on Medium Temperature Application SCOP
    medium_temp_scops = [hp['medium_temp_scop'] for hp in heat_pumps_with_both]
    print(f"\n{'='*70}")
    print("MEDIUM TEMPERATURE APPLICATION SCOP (dimension 5_X_0_0):")
    print(f"  Sample size: {len(medium_temp_scops):,}")
    print(f"  Mean: {statistics.mean(medium_temp_scops):.2f}")
    print(f"  Median: {statistics.median(medium_temp_scops):.2f}")
    print(f"  Std Dev: {statistics.stdev(medium_temp_scops):.2f}")
    print(f"  Min: {min(medium_temp_scops):.2f}")
    print(f"  Max: {max(medium_temp_scops):.2f}")
    print(f"  25th percentile: {statistics.quantiles(medium_temp_scops, n=4)[0]:.2f}")
    print(f"  75th percentile: {statistics.quantiles(medium_temp_scops, n=4)[2]:.2f}")
    
    print(f"\n  Distribution:")
    for low, high in ranges:
        count = sum(1 for v in medium_temp_scops if low <= v < high)
        pct = 100 * count / len(medium_temp_scops)
        bar = '█' * int(pct / 2)
        print(f"    {low:.1f} - {high:.1f}: {count:5,} ({pct:5.1f}%) {bar}")
    
    # SCOP ratio analysis
    scop_ratios = [hp['scop_ratio'] for hp in heat_pumps_with_both]
    print(f"\n{'='*70}")
    print("SCOP RATIO ANALYSIS (Medium/Low Application Temp):")
    print(f"  Mean ratio: {statistics.mean(scop_ratios):.3f}")
    print(f"  Median ratio: {statistics.median(scop_ratios):.3f}")
    print(f"  Medium temp SCOP is typically {statistics.mean(scop_ratios):.1%} of low temp SCOP")
    print(f"  This reflects: higher supply temp = lower efficiency")
    
    # Top manufacturers
    print(f"\n{'='*70}")
    print("TOP 20 MANUFACTURERS BY MULTI-CLIMATE SCOP DATA:")
    for manufacturer, count in sorted(manufacturer_counts.items(), key=lambda x: x[1], reverse=True)[:20]:
        print(f"  {manufacturer[:50]:50s}: {count:4,} heat pumps")
    
    # Duplicate detection
    print(f"\n{'='*70}")
    print("POTENTIAL DUPLICATE ANALYSIS:")
    print("(Models with identical SCOP values - may be rebadged for different markets)\n")
    
    duplicates_found = 0
    for spec_sig, models in specs_to_models.items():
        if len(models) > 1:
            # Check if they have different manufacturers or model names
            unique_manufacturers = set(m['manufacturer'] for m in models)
            unique_models = set(f"{m['manufacturer']}::{m['model_name']}" for m in models)
            
            if len(unique_manufacturers) > 1 or len(unique_models) > 1:
                duplicates_found += 1
                if duplicates_found <= 20:  # Show first 20 examples
                    low_scop, med_scop = spec_sig
                    print(f"Identical specs (Low temp SCOP={low_scop:.2f}, Medium temp SCOP={med_scop:.2f}):")
                    print(f"  Found in {len(models)} variants:")
                    for m in models[:5]:  # Show up to 5 variants
                        print(f"    - {m['manufacturer']} :: {m['model_name']} {m['variant']}")
                    if len(models) > 5:
                        print(f"    ... and {len(models) - 5} more")
                    print()
    
    if duplicates_found > 20:
        print(f"... and {duplicates_found - 20} more groups of potential duplicates")
    
    print(f"\n{'='*70}")
    print(f"SUMMARY:")
    print(f"  Total potential duplicate groups: {duplicates_found:,}")
    print(f"  These may represent:")
    print(f"    - Rebadged models for different markets")
    print(f"    - OEM partnerships (same unit, different brand)")
    print(f"    - Model variants with identical performance")


if __name__ == '__main__':
    analyze_multi_climate_scop()
