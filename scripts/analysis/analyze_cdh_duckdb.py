import duckdb
import pandas as pd

def analyze_cdh_codes():
    con = duckdb.connect('/workspaces/keymark-heat-pumps/data/keymark.duckdb')
    
    # Check a wider range of codes to find the missing Cdh @ -7C
    # We know 021, 047, 048, 049, 050, 051 are likely Cdh.
    # We are looking for something to replace 020.
    
    # Let's scan all codes and find ones with avg value between 0.8 and 1.1
    print("Scanning all codes for Cdh-like values...")
    
    query = """
    SELECT 
        en_code,
        COUNT(*) as count,
        MIN(value) as min_val,
        MAX(value) as max_val,
        AVG(value) as avg_val
    FROM measurements 
    GROUP BY en_code
    HAVING AVG(value) BETWEEN 0.8 AND 1.1 AND COUNT(*) > 1000
    ORDER BY en_code
    """
    result = con.sql(query).df()
    print(result)

if __name__ == "__main__":
    analyze_cdh_codes()
