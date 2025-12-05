# COMPLETE EN CODE REFERENCE

**Comprehensive mapping of all 77 EN measurement codes found in the Keymark heat pump database.**

---

## Quick Reference

| Standard | Focus Area | Codes | Measurements |
|----------|------------|-------|--------------|
| **EN14825** | Seasonal Performance (SCOP, heating capacity) | 51 | 808K+ |
| **EN14511** | Single-Point Performance Testing | 12 | 63K+ |
| **EN16147** | Domestic Hot Water (DHW) | 10 | 23K+ |
| **EN12102** | Sound Power Levels (Acoustic) | 4 | 35K+ |

---

## EN14825 - Seasonal Space Heating Performance

**Purpose:** Seasonal coefficient of performance and energy consumption for space heating.

### Core Seasonal Metrics

| Code | Name | Description | Unit | Typical Range |
|------|------|-------------|------|---------------|
| EN14825_001 | **ηs** | Seasonal space heating energy efficiency | % | 90-330% |
| EN14825_002 | **Prated** | Rated heating capacity (design load) | kW | 2-177 kW |
| EN14825_003 | **SCOP** | Seasonal coefficient of performance | - | 2.0-8.5 |
| EN14825_004 | **Tbiv** | Bivalent temperature (backup heating activation) | °C | -22 to +7°C |
| EN14825_005 | **TOL** | Operating limit temperature (minimum outdoor temp) | °C | -28 to +2°C |

### Performance at Specific Outdoor Temperatures

**Heating capacity (Pdh) and COP at test points:**

| Code | Parameter | Test Point | Unit | Description |
|------|-----------|------------|------|-------------|
| EN14825_008 | Pdh @ Tj=-7°C | -7°C | kW | Heating capacity at -7°C outdoor |
| EN14825_009 | COP @ Tj=-7°C | -7°C | - | Efficiency at -7°C outdoor |
| EN14825_010 | Pdh @ Tj=+2°C | +2°C | kW | Heating capacity at +2°C outdoor |
| EN14825_011 | COP @ Tj=+2°C | +2°C | - | Efficiency at +2°C outdoor |
| EN14825_012 | Pdh @ Tj=+7°C | +7°C | kW | Heating capacity at +7°C outdoor |
| EN14825_013 | COP @ Tj=+7°C | +7°C | - | Efficiency at +7°C outdoor |
| EN14825_014 | Pdh @ Tj=+12°C | +12°C | kW | Heating capacity at +12°C outdoor |
| EN14825_015 | COP @ Tj=+12°C | +12°C | - | Efficiency at +12°C outdoor |
| EN14825_016 | Pdh @ Tj=Tbiv | Tbiv | kW | Heating capacity at bivalent temp |
| EN14825_017 | COP @ Tj=Tbiv | Tbiv | - | Efficiency at bivalent temp |
| EN14825_018 | Pdh @ Tj=TOL | TOL | kW | Heating capacity at operating limit |
| EN14825_019 | COP @ Tj=TOL | TOL | - | Efficiency at operating limit |

### Additional Test Points (Extreme Cold)

**For heat pumps designed for extremely cold climates (TOL ≤ -15°C):**

| Code | Parameter | Test Point | Unit | Description |
|------|-----------|------------|------|-------------|
| EN14825_044 | Pdh @ Tj=-15°C | -15°C | kW | Heating capacity at -15°C outdoor |
| EN14825_045 | COP @ Tj=-15°C | -15°C | - | Efficiency at -15°C outdoor |
| EN14825_046 | Cdh @ Tj=-15°C | -15°C | - | Degradation coefficient at -15°C |

### Degradation Coefficients (Cdh)

**Accounts for cycling losses and part-load operation:**

| Code | Parameter | Test Point | Typical Value |
|------|-----------|------------|---------------|
| EN14825_020 | Cdh @ Tj=-7°C | -7°C | 0.9-1.0 |
| EN14825_021 | Cdh @ Tj=+2°C | +2°C | 0.9-1.0 |
| EN14825_047 | Cdh @ Tj=+7°C | +7°C | 0.9-1.0 |
| EN14825_048 | Cdh @ Tj=+12°C | +12°C | 0.9-1.0 |
| EN14825_049 | Cdh @ Tj=Tbiv | Tbiv | 0.9-1.0 |
| EN14825_050 | Cdh @ Tj=TOL | TOL | 0.9-1.0 |
| EN14825_051 | Cdh (additional) | varies | 0.9-1.0 |

### Power Consumption & Settings

| Code | Name | Description | Unit | Typical Range |
|------|------|-------------|------|---------------|
| EN14825_022 | **WTOL** | Water temperature at operating limit | °C | 1-85°C |
| EN14825_023 | **Poff** | Off-mode electrical power consumption | W | 0-300 W |
| EN14825_024 | **PTO** | Thermostat-off mode power consumption | W | 0-700 W |
| EN14825_025 | **PSB** | Standby mode power consumption | W | 0-273 W |
| EN14825_026 | **PCK** | Crankcase heater mode power consumption | W | 0-173 W |
| EN14825_027 | **Suppl. heater type** | Supplementary heater type code (0-3) | code | 0=none, 1=electric |
| EN14825_028 | **PSUP** | Rated heat output of supplementary heater | kW | 0-68 kW |
| EN14825_029 | **Qhe** | Annual heating energy consumption | kWh/yr | 0-136,567 kWh |

### Domestic Hot Water (DHW) Performance

**Heating capacity and COP for DHW mode:**

| Code | Parameter | Description | Unit |
|------|-----------|-------------|------|
| EN14825_030 | Pdh DHW | DHW heating capacity | kW |
| EN14825_031 | COP DHW | DHW coefficient of performance | - |
| EN14825_032 | Pdh DHW (alt) | Alternative DHW capacity measurement | kW |
| EN14825_033 | COP DHW (alt) | Alternative DHW COP measurement | - |
| EN14825_034 | Pdh DHW @ Tj | DHW capacity at specific outdoor temp | kW |
| EN14825_035 | COP DHW @ Tj | DHW COP at specific outdoor temp | - |
| EN14825_036 | Pdh DHW (3) | Third DHW capacity measurement point | kW |
| EN14825_037 | COP DHW (3) | Third DHW COP measurement point | - |
| EN14825_038 | Pdh DHW (4) | Fourth DHW capacity measurement point | kW |
| EN14825_039 | COP DHW (4) | Fourth DHW COP measurement point | - |
| EN14825_041 | **Qdhw** | Annual DHW energy consumption | kWh/yr |
| EN14825_042 | Unknown DHW | Unknown DHW parameter (rare) | ? |
| EN14825_043 | DHW capacity | DHW-related capacity metric | kW |

### Mixed Operation (Space Heating + DHW)

| Code | Parameter | Description | Unit |
|------|-----------|-------------|------|
| EN14825_044 | Pdh mixed | Mixed mode heating capacity | kW |
| EN14825_045 | COP mixed | Mixed mode COP | - |
| EN14825_052 | Cdh DHW | DHW degradation coefficient | - |
| EN14825_053 | Cdh mixed +2°C | Mixed operation degradation at +2°C | - |
| EN14825_054 | Cdh mixed +7°C | Mixed operation degradation at +7°C | - |
| EN14825_055 | Cdh mixed +12°C | Mixed operation degradation at +12°C | - |

---

## EN14511 - Single-Point Performance Testing

**Purpose:** Laboratory testing at specific, controlled conditions (not seasonal).

| Code | Name | Description | Unit | Range |
|------|------|-------------|------|-------|
| EN14511_2_001 | **Heating capacity A** | Heating capacity at test condition A | kW | 1.6-240 kW |
| EN14511_2_002 | **Power input A** | Electrical power input at condition A | kW | 0.4-85.2 kW |
| EN14511_2_003 | **COP A** | Coefficient of performance at condition A | - | 1.8-6.7 |
| EN14511_2_005 | **Heating capacity B** | Heating capacity at test condition B | kW | 0.8-121 kW |
| EN14511_2_006 | **COP B** | COP at test condition B (rare) | - | 2.5-5.6 |
| EN14511_2_007 | **Power input B** | Power input at test condition B | kW | 2.3-17.1 kW |
| EN14511_4_001 | **Test mode 1** | Test configuration indicator | code | Always 2 |
| EN14511_4_002 | **Test mode 2** | Test configuration indicator | code | Always 2 |
| EN14511_4_003 | **Test mode 3** | Test configuration indicator | code | Always 2 |
| EN14511_4_004 | **Test mode 4** | Test configuration indicator | code | Always 2 |
| EN14511_4_005 | **Test mode 5** | Test configuration indicator | code | 0 or 2 |
| EN14511_4_006 | **Test mode 6** | Test configuration indicator | code | Always 2 |

**Note:** EN14511 tests are typically performed at:
- **Condition A:** Air 7°C / Water 35°C (or similar standard test point)
- **Condition B:** Air -7°C / Water 55°C (or similar colder test point)

**Test mode codes** appear to be binary flags indicating which test configurations were performed (2 = tested, 0 = not tested).

---

## EN16147 - Domestic Hot Water Performance

**Purpose:** Energy efficiency and performance testing specifically for DHW production.

| Code | Name | Description | Unit | Range |
|------|------|-------------|------|-------|
| EN16147_001 | Unknown | Unknown DHW parameter (very rare) | ? | 0.0 |
| EN16147_002 | **DHW heating capacity** | Domestic hot water heating capacity | kW | 0-185 kW |
| EN16147_003 | **DHW COP** | DHW coefficient of performance | - | 0-4.3 |
| EN16147_004 | **DHW power input** | Electrical power input for DHW | kW | 0-154.8 kW |
| EN16147_005 | **DHW temperature** | DHW outlet or tank temperature | °C | 0-189°C |
| EN16147_006 | **DHW inlet temp** | DHW inlet water temperature | °C | 0-62.4°C |
| EN16147_007 | **DHW test metric** | Unknown DHW test parameter | ? | -99 to 434 |
| EN16147_008 | **DHW test mode 1** | Test configuration indicator | code | Always 2 |
| EN16147_009 | **DHW test mode 2** | Test configuration indicator | code | Always 2 |
| EN16147_010 | **DHW test mode 3** | Test configuration indicator | code | Always 2 |

**Note:** EN16147 focuses on:
- Heat pump water heaters
- Combined space heating + DHW systems
- Energy efficiency for DHW production
- Tank performance and stratification

---

## EN12102 - Sound Power Levels (Acoustic Performance)

**Purpose:** Measurement of noise levels for indoor and outdoor units.

| Code | Name | Description | Unit | Range |
|------|------|-------------|------|-------|
| EN12102_1_001 | **Sound power (indoor)** | Indoor unit sound power level | dB(A) | -99 to 72 dB(A) |
| EN12102_1_002 | **Sound power (outdoor)** | Outdoor unit sound power level | dB(A) | 0-93 dB(A) |
| EN12102_2_001 | **Sound power (heating)** | Sound power during heating mode | dB(A) | 16-60 dB(A) |
| EN12102_2_002 | **Sound power (cooling)** | Sound power during cooling mode | dB(A) | 54-65 dB(A) |

**Note:** 
- Negative values (-99) likely indicate "not applicable" or missing data
- Typical residential outdoor units: 50-65 dB(A)
- Typical residential indoor units: 25-45 dB(A)
- EN12102_1 codes are most common (19K measurements)
- EN12102_2 codes are rare (384 measurements)

---

## Database Coverage Summary

| Standard | Codes | Total Measurements | Unique Models | Coverage |
|----------|-------|-------------------|---------------|----------|
| EN14825 | 51 | 808,556 | 1,604 | ✅ Primary |
| EN14511 | 12 | 63,246 | 1,603 | ✅ Good |
| EN12102 | 4 | 35,529 | 1,450 | ✅ Good |
| EN16147 | 10 | 23,305 | 713 | ⚠️ Partial |
| **TOTAL** | **77** | **930,636** | **1,715** | |

---

## Dimension Code Structure

**Format:** `{temp}_{climate}_{indoor}_{hptype}`

### Position 0 - Application Temperature
- `4` = Low temperature (35°C supply, e.g., underfloor heating) - Higher SCOP
- `5` = Medium temperature (55°C supply, e.g., radiators) - Lower SCOP
- `6` = High temperature (65°C supply, rare)

### Position 1 - Climate Zone (EN 14825)
- `1` = Warmer climate
- `2` = Colder climate
- `3` = Average climate
- `0` = Not applicable / test condition

### Positions 2-3 - Equipment Configuration
- `0_0` = Standard configuration
- Other values indicate variant configurations (alternative indoor units, tanks, etc.)

**Common patterns:**
- `4_3_0_0` = Low temp (35°C), Average climate, Standard ← Most common
- `5_3_0_0` = Medium temp (55°C), Average climate, Standard
- `4_2_0_0` = Low temp, Colder climate
- `5_1_0_0` = Medium temp, Warmer climate
- `0_0_0_0` = Single-point test (EN14511, not climate-specific)

---

## Data Quality Notes

### High-Quality Codes (use for analytics)
✅ EN14825_001-005 (Core seasonal metrics)
✅ EN14825_008-019 (Temperature-specific performance)
✅ EN14825_022-029 (Power consumption & annual energy)
✅ EN14511_2_001-003 (Single-point heating capacity & COP)

### Moderate-Quality Codes
⚠️ EN14825_030-055 (DHW & mixed operation - partial coverage)
⚠️ EN16147_002-007 (DHW-specific - only 713 models)
⚠️ EN12102_1_001-002 (Sound levels - some missing data)

### Low-Quality Codes
❌ EN14825_020, 042 (Very rare, unclear meaning)
❌ EN14511_4_* (All constant value 2, test flags only)
❌ EN16147_001, 007 (Unclear purpose, extreme ranges)
❌ EN12102_1_001 negative values (Data quality issue)

---

*Last updated: 2025-11-18*
*Source: Keymark database with 808K+ measurements from 1,715 heat pump models*
