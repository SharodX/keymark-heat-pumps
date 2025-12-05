# SCOP Metrics Comprehensive Guide

## Overview
This document explains all SCOP-related metrics calculated according to EN14825:2018 and their relationships.

## Metrics Definitions

### 1. SCOPnet (Heat Pump Only)
**Formula:** `SCOPnet = QH / QHE`

- **QH**: Total annual heating demand (kWh)
- **QHE**: Heat pump energy consumption only (excludes supplementary heater)

**Description:** Performance of the heat pump itself, excluding any auxiliary electric heaters. This shows the "pure" efficiency of the heat pump compressor and refrigeration cycle.

**Use case:** Comparing heat pump efficiency independent of supplementary heating requirements.

---

### 2. SCOPon (Active Mode SCOP)
**Formula (19):** `SCOPon = QH / (QHE + QSUP)`

- **QSUP**: Supplementary electric heater energy consumption (kWh)

**Description:** Performance during active heating mode, including both heat pump and supplementary electric heater. This is the metric calculated in EN14825 Annex H examples.

**Use case:** This is the traditional "SCOP" that appears in many specifications when off-mode consumption is zero or not measured.

---

### 3. SCOP (Total System Performance)
**Formula (18):** `SCOP = QH / (QHE + QSUP + Q_offmode)`

Where `Q_offmode` is calculated from:
```
Q_offmode = HOFF × POFF + HTO × PTO + HSB × PSB + HCK × PCK
```

**Off-mode hours (heating only units):**
| Climate | HOFF  | HTO | HSB | HCK  |
|---------|-------|-----|-----|------|
| Average | 3,672 | 179 | 0   | 3,851|
| Warmer  | 4,345 | 755 | 0   | 4,476|
| Colder  | 2,189 | 131 | 0   | 2,944|

**Off-mode powers (from database EN codes):**
- **POFF** (EN14825_023): Off mode power consumption
- **PTO** (EN14825_024): Thermostat-off mode power
- **PSB** (EN14825_025): Standby mode power
- **PCK** (EN14825_026): Crankcase heater mode power

**Description:** Complete system performance including all energy consumption throughout the year, including periods when the unit is not actively heating.

**Use case:** This is the **DATABASE SCOP VALUE** - the official seasonal performance that accounts for all energy consumption.

---

### 4. ηs,h (Seasonal Space Heating Efficiency)
**Formula (14):** `ηs,h = (1/CC) × SCOP - ΣF(i)`

Where:
- **CC = 2.5** (conversion coefficient for electricity)
- **F(1) = 3%** (0.03) - Temperature controls correction
- **F(2) = 5%** (0.05) for water/brine units, 0% for air units - Pump consumption correction
- **ΣF(i) = F(1) + F(2)**

**Expanded formula:**
```
ηs,h = 0.4 × SCOP - (0.03 to 0.08)
```

**Description:** The seasonal efficiency percentage considering conversion from electrical to thermal energy and accounting for auxiliary component inefficiencies.

**Use case:** This is the **DATABASE EFFICIENCY VALUE** - used for energy labeling and regulatory compliance.

---

## Calculation Flow

```
Test Point Data (A, B, C, D, E, F)
    ↓
COPbin calculation (with Cd degradation at each test point)
    ↓
Interpolate COPbin for all temperature bins
    ↓
Calculate energy for each bin:
    - Heat pump energy (QHE)
    - Supplementary heater energy (QSUP)
    ↓
Sum all bins:
    - Total heating demand (QH)
    - Total HP energy (QHE)
    - Total supplementary energy (QSUP)
    ↓
Add off-mode consumption:
    - Q_offmode = Σ(Hours × Power)
    ↓
Calculate metrics:
    ┌─────────────────────────────────┐
    │ SCOPnet = QH / QHE              │ (HP only)
    ├─────────────────────────────────┤
    │ SCOPon = QH / (QHE + QSUP)      │ (Active mode)
    ├─────────────────────────────────┤
    │ SCOP = QH / (QHE + QSUP + Qoff) │ (Total, DATABASE)
    ├─────────────────────────────────┤
    │ ηs,h = 0.4 × SCOP - ΣF          │ (Efficiency %, DATABASE)
    └─────────────────────────────────┘
```

---

## Important Notes

### Cd (Degradation Coefficient)
- **Per-test-point Cd values are now supported** (if available in database)
- If not available, uses default value (typically 0.9 for water/brine systems)
- Cd is interpolated between test points for bin calculations
- Accounts for efficiency losses due to on/off cycling at part load

### Relationships
1. **SCOPnet ≥ SCOPon ≥ SCOP** (always true)
   - SCOPnet excludes supplementary heater
   - SCOPon includes active mode only
   - SCOP includes all consumption

2. **When supplementary heater is not needed:** SCOPnet = SCOPon

3. **When off-mode consumption is zero:** SCOPon = SCOP

4. **Verification:** SCOP can be recalculated from components:
   ```
   SCOP = QH / (QH/SCOPnet + QSUP + Q_offmode)
   ```

---

## Example Output

### Test Configuration
```
Heat Pump: Fixed capacity air-to-water, low temperature
Climate: Average
Pdesignh: 11.46 kW
Cd values: 0.88 to 0.95 (per test point)
Off-mode powers: POFF=15W, PTO=20W, PCK=30W
```

### Calculated Metrics
```
1. SCOP METRICS:
   SCOPnet: 3.6648 → 3.66  (Heat pump only)
   SCOPon:  3.5976 → 3.60  (Active mode, Formula 19)
   SCOP:    3.5048 → 3.50  (Total, Formula 18) ← DATABASE VALUE

2. ENERGY BREAKDOWN:
   Total heating demand (QH):      23,671.95 kWh
   Heat pump energy (QHE):          6,459.25 kWh
   Supplementary heater (QSUP):       120.73 kWh
   ──────────────────────────────────────────
   Active mode energy total:        6,579.98 kWh

3. AUXILIARY POWER CONSUMPTION:
   Off mode (15W × 3672h):             55.08 kWh
   Thermostat-off (20W × 179h):         3.58 kWh
   Crankcase heater (30W × 3851h):    115.53 kWh
   ──────────────────────────────────────────
   Total off-mode energy:             174.19 kWh

   TOTAL ENERGY:                    6,754.17 kWh

4. SCOP CALCULATION:
   SCOP = 23,671.95 / 6,754.17 = 3.5048

5. SEASONAL EFFICIENCY (Formula 14):
   ηs,h = (1/2.5) × 3.5048 - 0.03
        = 0.4 × 3.5048 - 0.03
        = 1.4019 - 0.03
        = 1.3719
        = 137.19% ← DATABASE COMPARISON VALUE
```

### Impact Analysis
- Off-mode consumption: 174.19 kWh (2.58% of total energy)
- SCOP reduction: 2.58% (from 3.60 to 3.50)
- Efficiency reduction: 3.71 percentage points (from 141% to 137%)

---

## Database Comparison

### For Verification
Compare these values from calculations against database:

| Metric | Database Field | Calculation | Match Criteria |
|--------|---------------|-------------|----------------|
| SCOP | `scop` | Formula 18 | ±1% typically |
| ηs,h | `efficiency_pct` | Formula 14 | ±2% typically |

### Expected Deviations
Small differences (< 3%) can occur due to:
1. Rounding in published values
2. Extrapolation beyond test point range
3. Different interpolation methods
4. Missing off-mode power data (when SCOP = SCOPon)

---

## Implementation Notes

### Code Changes
1. **`interpolate_cd()` method**: Interpolates Cd from test point values
2. **`calculate_cop_bin()` updated**: Accepts optional Cd parameter
3. **`calculate_scop_on()` expanded**: Calculates SCOPnet, SCOPon, SCOP, and ηs,h
4. **Metrics dictionary enhanced**: Now includes all intermediate values

### Dashboard Updates
1. Four metric cards: SCOPnet, SCOPon, SCOP, ηs,h
2. Energy breakdown: QHE, QSUP, Q_offmode
3. Calculation breakdown expandable section
4. Auxiliary power details when available

---

## References

- EN14825:2018 Section 8: Calculation of seasonal coefficient of performance
- EN14825:2018 Annex A: Tables A.4 and A.6 (off-mode hours)
- EN14825:2018 Annex B: Climate bins for heating
- EN14825:2018 Annex H: Example calculations
- Formula 14: Seasonal space heating energy efficiency
- Formula 18: SCOP with off-mode consumption
- Formula 19: SCOPon (active mode only)
