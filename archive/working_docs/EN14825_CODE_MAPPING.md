# EN14825 Code Mapping

## Overview

This document maps EN14825 measurement codes to their actual physical parameters based on analysis of the complete_mapping.json and PDF verification.

**Reference PDF Data (for validation):**
```
EN 14825 | Average Climate
Low temperature (4_3_0_0) / Medium temperature (5_3_0_0)

ηs:     179% / 135%
Prated: 4.00 kW / 4.00 kW  
SCOP:   4.56 / 3.45
Tbiv:   -7°C / -7°C
TOL:    -20°C / -15°C
PSUP:   0.20 kW / 0.10 kW
```

---

## Core EN14825 Codes

### EN14825_001 - Seasonal Space Heating Energy Efficiency (ηs)
- **Unit:** % (percentage)
- **Sample values:** 188, 178, 177, 180
- **Typical range:** 100-250%
- **PDF reference:** ηs = 179% (low temp), 135% (medium temp)
- **Description:** Seasonal space heating energy efficiency expressed as percentage

### EN14825_002 - Design Heating Capacity / Related Metric
- **Unit:** kW or unitless
- **Sample values:** 7.50, 8.50, 12.5
- **Typical range:** 4-20
- **Status:** ⚠️ UNCLEAR - Does not match PDF Prated (4.00 kW)
- **Note:** Values seem too high to be Prated directly. Might be related to heating capacity at specific test point.

### EN14825_003 - Seasonal Coefficient of Performance (SCOP)
- **Unit:** Unitless ratio
- **Sample values:** 4.78, 4.50, 4.51, 4.57
- **Typical range:** 2.5-8.0
- **PDF reference:** SCOP = 4.56 (low temp), 3.45 (medium temp)
- **Description:** Seasonal coefficient of performance for heating

### EN14825_004 - Bivalent Temperature (Tbiv)
- **Unit:** °C
- **Sample values:** -7, -7, -7
- **Typical range:** -22 to +7°C
- **PDF reference:** Tbiv = -7°C
- **Description:** Temperature at which backup heating is activated

### EN14825_005 - Operating Limit Temperature (TOL)
- **Unit:** °C  
- **Sample values:** -10, -10, -10
- **Typical range:** -28 to +2°C
- **PDF reference:** TOL = -20°C (low temp), -15°C (medium temp)
- **Description:** Lowest outdoor temperature at which heat pump can operate

---

## Temperature-Specific Heating Capacity Codes

### EN14825_008 - Pdh at Tj = -7°C (likely)
- **Unit:** kW
- **Sample values:** 7.02, 7.50, 11.1
- **PDF reference:** Pdh Tj = -7°C = 3.90 kW
- **Description:** Design heating capacity at outdoor temperature -7°C

### EN14825_009 - COP at Tj = -7°C (likely)
- **Unit:** Unitless ratio
- **Sample values:** 2.59, 2.98, 3.12
- **PDF reference:** COP Tj = -7°C = 3.01 (low temp), 2.26 (medium temp)
- **Description:** Coefficient of performance at outdoor temperature -7°C

### EN14825_010 - Pdh at Tj = +2°C (likely)
- **Unit:** kW
- **Sample values:** 3.83, 4.60, 6.7
- **PDF reference:** Pdh Tj = +2°C = 2.40 kW
- **Description:** Design heating capacity at outdoor temperature +2°C

### EN14825_011 - COP at Tj = +2°C (likely)
- **Unit:** Unitless ratio
- **Sample values:** 4.98, 4.46, 4.44
- **PDF reference:** COP Tj = +2°C = 4.53 (low temp), 3.32 (medium temp)
- **Description:** Coefficient of performance at outdoor temperature +2°C

### EN14825_012 - Pdh at Tj = +7°C (likely)
- **Unit:** kW
- **Sample values:** 2.61, 3.90, 5.7
- **PDF reference:** Pdh Tj = +7°C = 2.80 kW
- **Description:** Design heating capacity at outdoor temperature +7°C

### EN14825_013 - COP at Tj = +7°C (likely)
- **Unit:** Unitless ratio
- **Sample values:** 6.18, 5.89, 5.84
- **PDF reference:** COP Tj = +7°C = 5.57 (low temp), 4.35 (medium temp)
- **Description:** Coefficient of performance at outdoor temperature +7°C

### EN14825_014 - Pdh at Tj = +12°C (likely)
- **Unit:** kW
- **Sample values:** 2.33, 4.40, 6.0
- **PDF reference:** Pdh Tj = 12°C = 3.30 kW
- **Description:** Design heating capacity at outdoor temperature +12°C

### EN14825_015 - COP at Tj = +12°C (likely)
- **Unit:** Unitless ratio
- **Sample values:** 7.63, 7.14, 7.40
- **PDF reference:** COP Tj = 12°C = 7.01 (low temp), 6.01 (medium temp)
- **Description:** Coefficient of performance at outdoor temperature +12°C

### EN14825_044 - Pdh at Tj = -15°C
- **Unit:** kW
- **Sample values:** 5.68, 5.23
- **Description:** Design heating capacity at outdoor temperature -15°C (Colder Climate)

### EN14825_045 - COP at Tj = -15°C
- **Unit:** Unitless ratio
- **Sample values:** 2.77, 2.17
- **Description:** Coefficient of performance at outdoor temperature -15°C (Colder Climate)

---

## Backup Heating & Power Consumption

### EN14825_022 - Water Temperature (WTOL)
- **Unit:** °C
- **Sample values:** 75, 55, 35
- **Typical range:** 35-75°C
- **PDF reference:** WTOL = 60°C
- **Description:** Water temperature at operating limit

### EN14825_023 - Standby Power (Poff)
- **Unit:** W
- **Sample values:** 6, 4, 21
- **Typical range:** 0-50 W
- **PDF reference:** Poff = 19 W
- **Description:** Off-mode electrical power consumption

### EN14825_024 - Thermostat-Off Mode Power (PTO)
- **Unit:** W
- **Sample values:** 6, 20, 41
- **Typical range:** 0-50 W
- **PDF reference:** PTO = 22 W
- **Description:** Thermostat-off mode electrical power consumption

### EN14825_025 - Standby Mode Power (PSB)
- **Unit:** W
- **Sample values:** 6, 8, 21
- **Typical range:** 0-50 W
- **PDF reference:** PSB = 19 W
- **Description:** Standby mode electrical power consumption

### EN14825_026 - Crankcase Heater Power (PCK)
- **Unit:** W
- **Sample values:** 0, 0, 0
- **Typical range:** 0-100 W
- **PDF reference:** PCK = 0 W
- **Description:** Crankcase heater mode electrical power consumption

### EN14825_028 - Supplementary Heater Capacity (PSUP)
- **Unit:** kW
- **Sample values:** 0.59, 1.20, 1.4
- **Typical range:** 0-10 kW
- **PDF reference:** PSUP = 0.20 kW (low temp), 0.10 kW (medium temp)
- **Description:** Rated heat output of supplementary heater

### EN14825_029 - Annual Energy Consumption (Qhe)
- **Unit:** kWh/year
- **Sample values:** 3241, 3875, 5726, 5649
- **Typical range:** 1000-10000 kWh/year
- **PDF reference:** Qhe = 1988 kWh (low temp), 2624 kWh (medium temp)
- **Description:** Annual heating energy consumption

---

## Degradation Coefficients (Cdh/Cdc)

These codes represent the degradation coefficient for heating (Cdh) and cooling (Cdc) at specific temperature points. Values are typically 1.0 or slightly below (e.g., 0.9-0.99).

### EN14825_021 - Cdh at TOL
- **Unit:** Unitless
- **Sample values:** 1.0, 0.99
- **Description:** Degradation coefficient for heating at Operating Limit Temperature (TOL)

### EN14825_047 - Cdh at Tj = -7°C
- **Unit:** Unitless
- **Sample values:** 1.0, 0.99
- **Description:** Degradation coefficient for heating at outdoor temperature -7°C

### EN14825_048 - Cdh at Tj = +2°C
- **Unit:** Unitless
- **Sample values:** 1.0, 0.97
- **Description:** Degradation coefficient for heating at outdoor temperature +2°C

### EN14825_049 - Cdh at Tj = +7°C
- **Unit:** Unitless
- **Sample values:** 0.977, 0.982, 0.95
- **Description:** Degradation coefficient for heating at outdoor temperature +7°C

### EN14825_050 - Cdh at Tj = +12°C
- **Unit:** Unitless
- **Sample values:** 0.969, 0.976, 0.95
- **Description:** Degradation coefficient for heating at outdoor temperature +12°C

### EN14825_051 - Cdh at Tj = -15°C
- **Unit:** Unitless
- **Sample values:** 0.9, 0.95
- **Description:** Degradation coefficient for heating at outdoor temperature -15°C (Colder Climate)

---

## Cooling Performance Codes (SEER & EER)

Based on statistical verification and PDF analysis (e.g., Advantix models).

### EN14825_030 - Pdesignc (Cooling Design Capacity)
- **Unit:** kW
- **Sample values:** 12.41, 13.75
- **Description:** Design cooling capacity

### EN14825_031 - SEER
- **Unit:** Unitless ratio
- **Sample values:** 5.02, 5.04
- **Description:** Seasonal Energy Efficiency Ratio

### EN14825_032 - Pdc at Tj = 35°C
- **Unit:** kW
- **Description:** Cooling capacity at outdoor temperature 35°C

### EN14825_033 - EER at Tj = 35°C
- **Unit:** Unitless ratio
- **Description:** Energy Efficiency Ratio at outdoor temperature 35°C

### EN14825_034 - Pdc at Tj = 30°C
- **Unit:** kW
- **Description:** Cooling capacity at outdoor temperature 30°C

### EN14825_035 - EER at Tj = 30°C
- **Unit:** Unitless ratio
- **Description:** Energy Efficiency Ratio at outdoor temperature 30°C

### EN14825_036 - Pdc at Tj = 25°C
- **Unit:** kW
- **Description:** Cooling capacity at outdoor temperature 25°C

### EN14825_037 - EER at Tj = 25°C
- **Unit:** Unitless ratio
- **Description:** Energy Efficiency Ratio at outdoor temperature 25°C

### EN14825_038 - Pdc at Tj = 20°C
- **Unit:** kW
- **Description:** Cooling capacity at outdoor temperature 20°C

### EN14825_039 - EER at Tj = 20°C
- **Unit:** Unitless ratio
- **Description:** Energy Efficiency Ratio at outdoor temperature 20°C

### EN14825_041 - Qce (Annual Cooling Energy)
- **Unit:** kWh/year
- **Sample values:** 1483, 1635
- **Description:** Annual energy consumption for cooling

---

## Degradation Coefficients (Cooling - Cdc)

### EN14825_052 - Cdc at Tj = 35°C
- **Unit:** Unitless
- **Sample values:** 1.0
- **Description:** Degradation coefficient for cooling at outdoor temperature 35°C

### EN14825_053 - Cdc at Tj = 30°C
- **Unit:** Unitless
- **Sample values:** 1.0, 0.98, 0.983
- **Description:** Degradation coefficient for cooling at outdoor temperature 30°C

### EN14825_054 - Cdc at Tj = 25°C
- **Unit:** Unitless
- **Sample values:** 1.0, 0.966
- **Description:** Degradation coefficient for cooling at outdoor temperature 25°C

### EN14825_055 - Cdc at Tj = 20°C
- **Unit:** Unitless
- **Sample values:** 0.963, 0.964, 0.958
- **Description:** Degradation coefficient for cooling at outdoor temperature 20°C

---

## Data Quality Issues

### ⚠️ Value Mismatches

Several codes show significant discrepancies between database sample values and PDF reference values:

1. **EN14825_002**: Sample values (7.5-12.5) don't match PDF Prated (4.00 kW)
2. **EN14825_008-015**: Power and COP values are often 2-3x higher than PDF values
3. **EN14825_029**: Sample values (3241-5726 kWh) higher than PDF values (1988-2624 kWh)

**Possible causes:**
- Different heat pump sizes in samples vs reference PDF
- Unit conversion issues (e.g., values stored in deciKW instead of kW)
- Incorrect code-to-parameter mapping in source data extraction
- Multiple variants/configurations mixed in sample values

### 🔍 Missing Prated

The rated heating capacity (Prated) from the PDF (4.00 kW) does not clearly map to any single EN14825 code. Candidates:
- EN14825_002 (values too high: 7-12)
- EN14825_008/010/012/014 (specific temperature points, not rated capacity)

**Action needed:** Verify source PDFs and extraction logic to find correct Prated mapping.

---

## Dimension Codes

Based on DIMENSION_CODE_MAPPING.md:

### Position 0 - Application Temperature
- `4` = Low temperature (35°C supply) - Higher SCOP
- `5` = Medium temperature (55°C supply) - Lower SCOP

### Position 1 - Climate Zone
- `1` = Warmer climate
- `2` = Colder climate  
- `3` = Average climate

### Positions 2-3 - Equipment Variants
- `0` = Standard configuration
- Other values = Variant configurations

**Example:** `4_3_0_0` = Low temperature (35°C), Average climate, Standard equipment

---

## Recommendations

1. **Verify EN14825_002**: Check if this is actually Prated or another parameter
2. **Cross-reference PDFs**: Sample 10-20 PDFs to validate code mappings
3. **Unit standardization**: Ensure all power values are in consistent units (kW not deciKW)
4. **Document extraction logic**: Review scripts/transform_to_database.py and ingestion pipeline
5. **Create test cases**: Use the reference PDF data as validation test case

---

*Last updated: 2025-11-18*
*Status: DRAFT - Requires validation against source PDFs*
