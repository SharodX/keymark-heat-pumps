import json
import glob
import os
from collections import Counter

def find_cdh_keys():
    files = glob.glob("/workspaces/keymark-heat-pumps/data/pdf_extractions/*.json")
    cdh_keys = Counter()
    
    print(f"Scanning {len(files)} files...")
    
    for i, filepath in enumerate(files):
        if i > 100: break # Limit to 100 files for speed
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                for record in data.get('records', []):
                    for key in record.keys():
                        if "Cdh" in key or "Degradation" in key:
                            cdh_keys[key] += 1
                        # Also check values if they are like "Cdh ..."
                        val = record.get("", "")
                        if isinstance(val, str) and ("Cdh" in val or "Degradation" in val):
                             cdh_keys[val] += 1
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            
    print("\nFound Cdh keys/values:")
    for key, count in cdh_keys.most_common():
        print(f"{key}: {count}")

if __name__ == "__main__":
    find_cdh_keys()
