import duckdb
import json
import os
import glob
import re
from collections import defaultdict

# Connect to DuckDB
con = duckdb.connect('data/keymark.duckdb')

# Get all database files (structured)
db_files = glob.glob('data/database/*.json')
print(f"Found {len(db_files)} database files.")

# Get all pdf extraction files (raw)
pdf_files = glob.glob('data/pdf_extractions/*.json')
print(f"Found {len(pdf_files)} PDF extraction files.")

# Create a lookup for pdf files to speed up matching
# Normalize filename: lowercase, remove non-alphanumeric
def normalize_filename(fname):
    base = os.path.basename(fname)
    name_without_ext = os.path.splitext(base)[0]
    return re.sub(r'[^a-z0-9]', '', name_without_ext.lower())

pdf_lookup = {}
for pf in pdf_files:
    norm = normalize_filename(pf)
    pdf_lookup[norm] = pf

# Mapping statistics: EN_CODE -> JSON_KEY -> Count
mapping_stats = defaultdict(lambda: defaultdict(int))
# Value match statistics: EN_CODE -> Total Matches
match_counts = defaultdict(int)
# Total occurrences of EN_CODE in DB for the scanned models
code_occurrences = defaultdict(int)

def normalize_value(val_str):
    """
    Extracts the first numeric value from a string.
    Returns float or None.
    """
    if isinstance(val_str, (int, float)):
        return float(val_str)
    if not isinstance(val_str, str):
        return None
    
    # Regex to find numbers, handling negatives and decimals
    # Matches -123.45, 123, .45
    match = re.search(r'-?\d*\.?\d+', val_str.replace(',', '.'))
    if match:
        try:
            return float(match.group())
        except ValueError:
            return None
    return None

def normalize_key(key):
    """
    Normalize JSON keys to group similar descriptions.
    """
    key = key.lower().strip()
    key = re.sub(r'\s+', ' ', key) # Collapse whitespace
    return key

print("Starting verification...")

matched_files_count = 0

for i, db_filepath in enumerate(db_files):
    if i % 100 == 0:
        print(f"Processing file {i}/{len(db_files)}")
        
    try:
        with open(db_filepath, 'r') as f:
            db_data = json.load(f)
    except Exception as e:
        print(f"Error reading {db_filepath}: {e}")
        continue

    # Get Manufacturer and Model from DB file metadata
    metadata = db_data.get('file_metadata', {})
    manufacturer = metadata.get('Manufacturer')
    model_name = metadata.get('Modelname')
    
    if not manufacturer or not model_name:
        continue
        
    # Find corresponding PDF extraction file
    db_fname_norm = normalize_filename(db_filepath)
    
    found_pdf = None
    
    # Let's try to find a match in pdf_lookup keys
    for pdf_norm, pdf_path in pdf_lookup.items():
        if db_fname_norm in pdf_norm:
            found_pdf = pdf_path
            break
            
    if not found_pdf:
        continue
        
    matched_files_count += 1
    
    # Load PDF extraction data
    try:
        with open(found_pdf, 'r') as f:
            pdf_data = json.load(f)
    except Exception as e:
        print(f"Error reading {found_pdf}: {e}")
        continue
        
    # Flatten JSON data for this file: { normalized_key: [values] }
    json_values = defaultdict(list)
    
    if 'records' in pdf_data:
        for record in pdf_data['records']:
            for k, v in record.items():
                if k in ['source_page', 'source_table', 'model_id', 'submodel_id']:
                    continue
                
                norm_val = normalize_value(v)
                if norm_val is not None:
                    json_values[norm_val].append(k)
                    
    # Now verify against DB values
    if 'heat_pumps' not in db_data:
        continue
        
    for hp in db_data['heat_pumps']:
        if 'measurements' not in hp:
            continue
            
        for en_code, dimensions in hp['measurements'].items():
            for dim, val_str in dimensions.items():
                db_val = normalize_value(val_str)
                if db_val is None:
                    continue
                
                code_occurrences[en_code] += 1
                
                # Check if this value exists in our JSON extracted values
                found = False
                if db_val in json_values:
                    found = True
                    for json_key in json_values[db_val]:
                        mapping_stats[en_code][json_key] += 1
                    match_counts[en_code] += 1
                else:
                    # Fuzzy float match
                    for j_val, j_keys in json_values.items():
                        if abs(j_val - db_val) < 0.001: # Tolerance
                            found = True
                            for json_key in j_keys:
                                mapping_stats[en_code][json_key] += 1
                            match_counts[en_code] += 1
                            break 
                
                if not found:
                     # Check percentages
                     if db_val > 10 and (db_val / 100.0) in json_values:
                         for json_key in json_values[db_val / 100.0]:
                             mapping_stats[en_code][json_key] += 1
                         match_counts[en_code] += 1
                     elif db_val < 10 and (db_val * 100.0) in json_values:
                         for json_key in json_values[db_val * 100.0]:
                             mapping_stats[en_code][json_key] += 1
                         match_counts[en_code] += 1

print(f"Matched {matched_files_count} database files to PDF extractions.")

# Generate Report
print("\n" + "="*50)
print("MAPPING VERIFICATION REPORT")
print("="*50)

sorted_codes = sorted(code_occurrences.keys())

for code in sorted_codes:
    total = code_occurrences[code]
    matches = match_counts[code]
    match_rate = (matches / total) * 100 if total > 0 else 0
    
    print(f"\nCode: {code}")
    print(f"  Found in DB: {total} times")
    print(f"  Matched in JSON: {matches} times ({match_rate:.1f}%)")
    
    if matches > 0:
        print("  Top 5 corresponding JSON keys:")
        # Sort keys by frequency
        top_keys = sorted(mapping_stats[code].items(), key=lambda x: x[1], reverse=True)[:5]
        for key, count in top_keys:
            percentage = (count / matches) * 100
            print(f"    - '{key}': {count} ({percentage:.1f}%)")
