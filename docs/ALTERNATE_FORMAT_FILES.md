# Alternate Format CSV Files

## Summary

Out of 2,850 source CSV files, **404 files (14%)** use an alternate format that the current pipeline cannot process. These are automatically detected and skipped during transformation.

## Detection Criteria

Files are considered "alternate format" if their first line does NOT start with `"modelID"` (the standard header).

## Categories

### 1. Metadata-Only Stubs (398 files)

These files contain only 7 rows of basic metadata with no actual measurement data:

```csv
"","Refrigerant","R32","0","0","0","0"
"","Mass of Refrigerant","0,870kg","0","0","0","0"
"","Date","25.03.2021","0","0","0","0"
"","Manufacturer","AERMEC S.p.A.","0","0","0","0"
"","Modelname","HMI040 / DHWT300","0","0","0","0"
"","Type","Outdoor Air/Water","0","0","0","0"
"","Energy","Electricity","0","0","0","0"
```

**Format characteristics:**
- Column 1: Empty
- Column 2: Field name (Refrigerant, Date, Manufacturer, Modelname, Type, Energy)
- Column 3: Value
- Columns 4-7: Zeros

**Status:** No measurement data to extract. Can be safely skipped.

### 2. Headerless Measurement Files (6 files)

These files contain actual EN14511/EN14825 measurements but are missing the header row:

| Filename | Rows | Content |
|----------|------|---------|
| `_Ariston_Thermo_GroupNIMBUS_ARIANEXT_AEROTOP_ENERGION_120_150_M_-_COMPACT.csv` | 3,302 | EN14511 measurements |
| `_Nibe_ABF1x55-12.csv` | 2,160 | EN14511 measurements |
| `_Viessmann_Climate_Solutions_GmbH_&_Co._KGVitocal_x50-A_z4.csv` | 1,446 | EN14511 measurements |
| `_Nibe_ABF1X53-6.csv` | 513 | EN14511 measurements |
| `_tecalor_GmbHTTL_15_AS,_TTL_15_ACS.csv` | 160 | EN14511 measurements |
| `_Viessmann_Climate_Solutions_GmbH_&_Co._KGVitocal_x50-A_z2.csv` | 9 | Minimal data |

**Format characteristics:**
- Same column structure as standard files: `modelID, varName, value, temperature, climate, indoorUnittype, info, hpType`
- Missing the header row - data starts on line 1
- First column contains model identifiers like `"model-181"` or variant names

**Example:**
```csv
"model-181","EN14511_4_001","2","0","10","0","2","0"
"model-181","EN14511_2_001","5.06","4","10","0","2","0"
```

**Status:** Contains valuable data. Future work could inject the standard header to process these.

## Future Work

To recover the 6 headerless measurement files:

1. Detect files where first column looks like a model ID (not empty, not "modelID")
2. Prepend the standard header: `"modelID","varName","value","temperature","climate","indoorUnittype","info","hpType"`
3. Re-run ingestion and transformation

## File Counts

```
Total source CSVs:        2,850
├── Standard format:      2,446 (86%) → Successfully processed
└── Alternate format:       404 (14%) → Skipped
    ├── Metadata stubs:     398 (no data)
    └── Headerless data:      6 (recoverable)
```

## Last Updated

December 5, 2025
