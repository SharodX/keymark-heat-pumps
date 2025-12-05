import duckdb
import json
import glob

con = duckdb.connect('data/keymark.duckdb')

# Check DB content
print("DB Tables:")
print(con.execute("SHOW TABLES").fetchall())

print("\nSample measurements:")
print(con.execute("SELECT * FROM measurements LIMIT 5").fetchall())

# Check a JSON file
files = glob.glob('data/pdf_extractions/*.json')
if files:
    fpath = files[0]
    print(f"\nChecking file: {fpath}")
    with open(fpath, 'r') as f:
        data = json.load(f)
        
    model_ids = set()
    if 'records' in data:
        for r in data['records']:
            if 'model_id' in r:
                model_ids.add(r['model_id'])
    
    print(f"Model IDs in JSON: {model_ids}")
    
    for mid in model_ids:
        print(f"Checking DB for model: {mid}")
        count = con.execute("SELECT count(*) FROM measurements WHERE model_name = ?", [mid]).fetchone()[0]
        print(f"  Found {count} rows")
else:
    print("No JSON files found")
