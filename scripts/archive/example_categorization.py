#!/usr/bin/env python3
"""
Example: Using header metadata for heat pump categorization.

Demonstrates how to leverage PDF header information to:
1. Filter heat pumps by climate zone
2. Categorize by application (heating/cooling/DHW)
3. Extract test conditions and standards compliance
"""

import json
from pathlib import Path
from collections import defaultdict


def categorize_by_climate():
    """Example: Categorize heat pumps by available climate data."""
    print("="*80)
    print("HEAT PUMP CATEGORIZATION BY CLIMATE COVERAGE")
    print("="*80 + "\n")
    
    db_dir = Path('data/database')
    
    # Categories
    categories = {
        'full_climate': [],      # Has all 3 climates (1, 2, 3)
        'partial_climate': [],   # Has 2 climates
        'single_climate': [],    # Has 1 climate
        'no_climate': []         # No climate data
    }
    
    # Climate zone identification (based on SCOP analysis)
    CLIMATE_MAP = {
        '1': 'Warmer',
        '2': 'Colder', 
        '3': 'Average'
    }
    
    print("Processing database files...\n")
    
    for db_file in list(db_dir.glob('*.json'))[:200]:  # Sample
        try:
            with open(db_file) as f:
                data = json.load(f)
            
            metadata = data.get('file_metadata', {})
            
            for hp in data.get('heat_pumps', []):
                scop_data = hp.get('measurements', {}).get('EN14825_003', {})
                
                if not scop_data:
                    continue
                
                # Identify available climate zones (from dimension codes)
                climate_digits = set()
                climate_scops = {}
                
                for dim_code, scop_value in scop_data.items():
                    try:
                        scop = float(scop_value)
                        if 1.0 <= scop <= 10.0:
                            parts = dim_code.split('_')
                            if len(parts) >= 2:
                                climate_digit = parts[1]
                                climate_digits.add(climate_digit)
                                climate_name = CLIMATE_MAP.get(climate_digit, f'Unknown_{climate_digit}')
                                climate_scops[climate_name] = scop
                    except (ValueError, TypeError):
                        pass
                
                # Categorize
                hp_info = {
                    'manufacturer': metadata.get('Manufacturer', 'Unknown'),
                    'model': metadata.get('Modelname', 'Unknown'),
                    'variant': hp.get('variant', ''),
                    'climates': sorted(climate_digits),
                    'climate_scops': climate_scops
                }
                
                num_climates = len(climate_digits)
                if num_climates == 3:
                    categories['full_climate'].append(hp_info)
                elif num_climates == 2:
                    categories['partial_climate'].append(hp_info)
                elif num_climates == 1:
                    categories['single_climate'].append(hp_info)
                else:
                    categories['no_climate'].append(hp_info)
        
        except (json.JSONDecodeError, KeyError):
            continue
    
    # Report
    print("Category Distribution:")
    print(f"  Full climate coverage (3 zones):  {len(categories['full_climate']):4d} heat pumps")
    print(f"  Partial coverage (2 zones):       {len(categories['partial_climate']):4d} heat pumps")
    print(f"  Single climate:                   {len(categories['single_climate']):4d} heat pumps")
    print(f"  No climate data:                  {len(categories['no_climate']):4d} heat pumps")
    
    # Show examples
    print("\n" + "="*80)
    print("EXAMPLES: Heat Pumps with Full Climate Coverage")
    print("="*80)
    
    for hp in categories['full_climate'][:10]:
        print(f"\n{hp['manufacturer']}: {hp['model']}")
        print(f"  Climate zones: {', '.join(hp['climates'])}")
        print(f"  SCOP by climate:")
        for climate, scop in sorted(hp['climate_scops'].items()):
            print(f"    {climate:10s}: {scop:.2f}")


def filter_by_application_temp():
    """Example: Filter heat pumps by application temperature."""
    print("\n" + "="*80)
    print("FILTERING BY APPLICATION TEMPERATURE")
    print("="*80 + "\n")
    
    db_dir = Path('data/database')
    
    low_temp_only = []      # Only has low temp (4_X_0_0)
    medium_temp_only = []   # Only has medium temp (5_X_0_0)
    both_temps = []         # Has both
    
    for db_file in list(db_dir.glob('*.json'))[:200]:
        try:
            with open(db_file) as f:
                data = json.load(f)
            
            metadata = data.get('file_metadata', {})
            
            for hp in data.get('heat_pumps', []):
                scop_data = hp.get('measurements', {}).get('EN14825_003', {})
                
                has_low_temp = any(k.startswith('4_') for k in scop_data.keys())
                has_medium_temp = any(k.startswith('5_') for k in scop_data.keys())
                
                hp_info = {
                    'manufacturer': metadata.get('Manufacturer', 'Unknown'),
                    'model': metadata.get('Modelname', 'Unknown')
                }
                
                if has_low_temp and has_medium_temp:
                    both_temps.append(hp_info)
                elif has_low_temp:
                    low_temp_only.append(hp_info)
                elif has_medium_temp:
                    medium_temp_only.append(hp_info)
        
        except:
            pass
    
    print("Application Temperature Coverage:")
    print(f"  Both temperatures:  {len(both_temps):4d} heat pumps (most versatile)")
    print(f"  Low temp only:      {len(low_temp_only):4d} heat pumps (optimized for underfloor)")
    print(f"  Medium temp only:   {len(medium_temp_only):4d} heat pumps (radiator systems)")
    
    if low_temp_only:
        print("\nExamples of Low Temperature Only heat pumps:")
        for hp in low_temp_only[:5]:
            print(f"  - {hp['manufacturer']}: {hp['model']}")


def usage_examples():
    """Print usage examples."""
    print("\n" + "="*80)
    print("USAGE EXAMPLES: Selecting Appropriate Test Data")
    print("="*80)
    print("""
# Get heat pump performance for specific use case:

# Case 1: Underfloor heating in mild climate (best case)
scop_best = measurements['EN14825_003']['4_1_0_0']  # Low temp, Warmer climate

# Case 2: Radiators in cold climate (worst case)  
scop_worst = measurements['EN14825_003']['5_2_0_0']  # Medium temp, Colder climate

# Case 3: Standard comparison (average conditions, low temp)
scop_standard = measurements['EN14825_003']['4_3_0_0']  # Low temp, Average climate

# Case 4: Get performance across all climates
for dim_code, scop in measurements['EN14825_003'].items():
    if dim_code.startswith('4_'):  # Low temperature application
        climate_digit = dim_code.split('_')[1]
        climate_name = CLIMATE_MAP.get(climate_digit, 'Unknown')
        print(f"{climate_name} Climate: SCOP = {scop}")
""")


if __name__ == '__main__':
    categorize_by_climate()
    filter_by_application_temp()
    usage_examples()
