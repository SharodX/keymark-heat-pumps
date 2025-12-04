# SCOP Verification Implementation

## Overview

This implementation provides a complete SCOP (Seasonal Coefficient of Performance) calculation and verification tool based on **EN14825:2018** standard. The system calculates three key metrics:

1. **SCOPon** - Includes supplementary heater energy in denominator
2. **SCOPnet** - Excludes supplementary heater from denominator (net heat pump performance)
3. **ηs** - Seasonal efficiency percentage

## Key Formulas (EN14825:2018 Section 8.2.1)

### SCOP Metrics

```
SCOPon  = QH / (QHE + QSUP)
SCOPnet = QH / QHE
ηs      = SCOPnet × CC × 100%
```

Where:
- **QH** = Total annual heating demand (kWh)
- **QHE** = Heat pump electrical energy consumption (kWh)
- **QSUP** = Supplementary heater electrical energy (kWh)
- **CC** = 0.4 (conversion coefficient for electricity = 1/2.5)
- The 2.5 factor is the primary energy factor accounting for generation/distribution losses

### Typical Values

For a well-performing heat pump:
- **SCOPon**: 3.5 - 4.5 (typical range)
- **SCOPnet**: 3.6 - 4.6 (slightly higher, excludes supplementary heater)
- **ηs**: 140% - 180% (seasonal efficiency)

## Implementation Files

### 1. Core Calculation Engine
**File**: `/scripts/calculate_scop_en14825.py`

The `SCOPCalculator` class implements the EN14825 bin method:

```python
calculator = SCOPCalculator(
    climate='Average',          # 'Average', 'Warmer', or 'Colder'
    Pdesignh=11.46,            # Design heating load (kW)
    test_points={...},          # Dict with test point data
    Tbiv=-6,                    # Bivalent temperature (°C)
    TOL=-10,                    # Operating limit temperature (°C)
    Cd=0.9                      # Degradation coefficient
)

metrics, df = calculator.calculate_scop_on()
```

**Returns**:
- `metrics`: Dict containing `{'SCOPon', 'SCOPnet', 'ηs', 'QH', 'QHE', 'QSUP'}`
- `df`: Detailed DataFrame with bin-by-bin calculations

### 2. Streamlit Dashboard Page
**File**: `/frontend/pages/scop_verification.py`

Interactive web interface for SCOP verification:
- Select heat pump from database
- View test point data
- Calculate SCOP using EN14825 method
- Compare calculated vs reported values
- Visualize energy distribution

### 3. Jupyter Notebook
**File**: `/scop_analysis_simple.ipynb`

Analysis notebook demonstrating:
- Example calculation from EN14825 Annex H
- Step-by-step verification
- Visualization of results
- Validation against expected values

## Calculation Methodology

### 1. Test Points

The standard defines 6 test points (labeled A-F):
- **A**: -7°C
- **B**: +2°C
- **C**: +7°C
- **D**: +12°C
- **E**: TOL (Operating Limit Temperature, e.g., -10°C)
- **F**: Tbiv (Bivalent Temperature, e.g., -6°C)

Each test point has:
- `Tj`: Outdoor temperature (°C)
- `Pdh`: Declared heating capacity (kW)
- `COPd`: COP at declared capacity

### 2. COPbin Calculation

**Key Innovation**: Calculate CC, CR, and COPbin **only at test points**, then interpolate/extrapolate.

At each test point:
1. Calculate capacity ratio: `CR = Ph(Tj) / Pdh(Tj)`
2. If `CR < 1` (cycling operation):
   - `CC = (CR × Cd + (1 - Cd)) / CR`
3. Else (continuous operation):
   - `CC = 1.0`
4. Calculate `COPbin = COPd / CC`

### 3. Interpolation and Extrapolation

**Within test range** (-10°C to 12°C):
- Linear interpolation of COPbin values

**Beyond test range** (13°C to 15°C):
- Linear extrapolation using slope from last two test points (C & D)
- Example: Slope = (COPbin_D - COPbin_C) / (12 - 7) = -0.164 per °C

**Why Linear Extrapolation?**
At high temperatures, capacity greatly exceeds load, causing more frequent cycling and degradation. The COPbin trend naturally decreases.

### 4. Energy Calculation

For each temperature bin:
```python
# Heating load
Ph = Pdesignh × (Tj - 16) / (Tdesignh - 16)

# Interpolate COPbin from test points
COPbin = interpolate_copbin(Tj)

# Supplementary heater requirement
elbu = max(0, Ph - Pdh)

# Annual energy for this bin
if Pdh >= Ph:
    Eelec = hj × Ph / COPbin
else:
    Eelec = hj × [(Ph - elbu) / COPbin + elbu]
```

## Validation Results

### EN14825 Annex H Example

**Input Parameters**:
- Climate: Average
- Pdesignh: 11.46 kW
- Tbiv: -6°C
- TOL: -10°C
- Cd: 0.9

**Results**:
```
Calculated:
  SCOPon:  3.60 (3.597573 unrounded)
  SCOPnet: 3.66 (3.664817 unrounded)
  ηs:      147%

Expected (Annex H):
  SCOPon: 3.61

Difference: 0.012 (0.34% error) ✅
```

**Energy Breakdown**:
- Total heating demand (QH): 23,672 kWh
- Heat pump energy (QHE): 6,459 kWh
- Supplementary heater (QSUP): 121 kWh
- Total energy: 6,580 kWh

## Usage Guide

### Option 1: Streamlit Dashboard

```bash
# Start the Streamlit app
cd /workspaces/keymark-heat-pumps
streamlit run frontend/streamlit_app.py

# Navigate to "SCOP Verification" page
# Select heat pump and configuration
# View calculated vs reported SCOP
```

### Option 2: Python Script

```python
from scripts.calculate_scop_en14825 import SCOPCalculator

# Define test points
test_points = {
    'A': {'Tj': -7, 'Pdh': 9.55, 'COPd': 3.26},
    'B': {'Tj': 2, 'Pdh': 11.17, 'COPd': 4.00},
    'C': {'Tj': 7, 'Pdh': 12.66, 'COPd': 4.91},
    'D': {'Tj': 12, 'Pdh': 14.3, 'COPd': 5.5},
    'E': {'Tj': -10, 'Pdh': 7.8, 'COPd': 2.6},
    'F': {'Tj': -6, 'Pdh': 9.7, 'COPd': 3.3}
}

# Calculate SCOP
calculator = SCOPCalculator(
    climate='Average',
    Pdesignh=11.46,
    test_points=test_points,
    Tbiv=-6,
    TOL=-10,
    Cd=0.9
)

metrics, df = calculator.calculate_scop_on()

print(f"SCOPon: {metrics['SCOPon']:.2f}")
print(f"SCOPnet: {metrics['SCOPnet']:.2f}")
print(f"ηs: {metrics['ηs']:.0f}%")
```

### Option 3: Jupyter Notebook

```bash
# Open the analysis notebook
jupyter notebook scop_analysis_simple.ipynb

# Run all cells to see example calculation
```

## Key Implementation Details

### 1. No Premature Rounding

All intermediate calculations use full precision. Rounding is applied only for final display:
- Temperatures: integers
- COP values: 2 decimals
- Power values: 2 decimals
- Energy values: integers

### 2. Test Point Only Calculations

CC and CR are calculated only at the 6 test points where we have actual measured data. This avoids error accumulation from interpolated values.

### 3. Linear Extrapolation

Beyond the test data range (>12°C), we use linear extrapolation based on the slope from the last two test points. This is more physically realistic than flat extrapolation.

### 4. Climate Data

Bin data (temperature bins and hours) is defined for three climate zones:
- **Average**: Tdesignh = -10°C, 26 bins
- **Warmer**: Tdesignh = +2°C, 14 bins  
- **Colder**: Tdesignh = -22°C, 38 bins

## Comparison: Reported vs Calculated

The dashboard shows:
- ✅ **Match**: Difference < 1%
- ⚠️ **Deviation**: Difference 1-5%
- ❌ **Large difference**: Difference > 5%

Small differences (<5%) are normal due to:
1. Rounding in reported values
2. Different extrapolation methods
3. Measurement uncertainties
4. Calculation precision differences

## References

- **EN14825:2018**: Air conditioners, liquid chilling packages and heat pumps, with electrically driven compressors, for space heating and cooling - Testing and rating at part load conditions and calculation of seasonal performance
- **Annex H**: Example calculation for fixed capacity air-to-water heat pump

## Notes

1. **SCOPnet vs SCOPon**: SCOPnet is always slightly higher because it excludes supplementary heater energy from the denominator. This represents the "pure" heat pump performance.

2. **Seasonal Efficiency (ηs)**: The 147% efficiency means the heat pump delivers 1.47 kWh of heat for every 1 kWh of electrical input (accounting for primary energy conversion).

3. **Degradation Coefficient (Cd)**: Typically 0.9 for water/brine systems, 0.25 for air systems. This accounts for cycling losses when capacity exceeds demand.

4. **Primary Energy Factor**: The CC = 0.4 (40%) is based on the assumption that 1 kWh of electricity requires 2.5 kWh of primary energy (fossil fuels) to generate and distribute.
