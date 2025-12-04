# Dimension Code Mapping

## Overview

Heat pump performance measurements use dimension codes formatted as:

```
TEMP_CLIMATE_INDOOR_HPTYPE
```

Example codes: `4_1_0_0`, `5_2_0_0`

---

## Position 1 – Application Temperature

Controls the supply temperature for the heating system.

- `4` → Low temperature application (≈35 °C supply, e.g. underfloor heating)
  - Higher efficiency, higher SCOP
  - Mean SCOP ≈ 5.27 across 5,468 units
- `5` → Medium temperature application (≈55 °C supply, e.g. radiators)
  - Lower efficiency, lower SCOP
  - Mean SCOP ≈ 3.77
  - Typical efficiency ratio: medium ≈ 72 % of low temperature SCOP

Evidence:
- PDF tables expose columns `low_temperature` and `medium_temperature`
- Physics expectations (higher supply temperature → lower efficiency)
- Consistent ratios observed in dataset (`scripts/analyze_multi_climate_scop.py`)

---

## Position 2 – Climate Zone (EN 14825)

Represents climatic conditions for seasonal testing. Derived from PDF header rows such as `EN 14825 | Average Climate`.

| Digit | Climate Zone | Mean SCOP | PDF Table Count |
|-------|--------------|-----------|-----------------|
| `1`   | Warmer       | 5.07      | 4,559           |
| `2`   | Colder       | 3.65      | 3,882           |
| `3`   | Average      | 4.08      | 9,282           |

Key observations:
- Climate designations appear as table headers, not column labels.
- `Average` is the most common zone tested.
- SCOP ordering matches expectations (warmer climates yield higher efficiency).

---

## Positions 3 & 4 – Equipment Variants

- `0` → Standard indoor unit / heat pump type.
- Other digits (rare) indicate variant configurations (e.g., tank packages, alternative indoor units). Most dataset entries use `0` in both positions.

---

## Common Dimension Patterns

```
4_1_0_0 → Low temp, Warmer climate  (highest SCOP)
4_2_0_0 → Low temp, Colder climate
4_3_0_0 → Low temp, Average climate
5_1_0_0 → Medium temp, Warmer climate
5_2_0_0 → Medium temp, Colder climate (lowest SCOP)
5_3_0_0 → Medium temp, Average climate
```

Example (Bosch WLW156 family):

| Dimension | Description                     | SCOP |
|-----------|---------------------------------|------|
| 4_1_0_0   | Low temp, Warmer climate        | 6.53 |
| 4_2_0_0   | Low temp, Colder climate        | 4.08 |
| 4_3_0_0   | Low temp, Average climate       | 4.81 |
| 5_1_0_0   | Medium temp, Warmer climate     | 4.43 |
| 5_2_0_0   | Medium temp, Colder climate     | 3.02 |
| 5_3_0_0   | Medium temp, Average climate    | 3.45 |

---

## Related EN Standards in Dataset

- **EN 14825** – Seasonal performance (SCOP). Climate headers: Average, Colder, Warmer, Cooling.
- **EN 14511** – Single-point performance (COP at specific temperatures).
- **EN 16147** – Domestic hot water (occasional climate references).
- **EN 12102** – Acoustic performance (climate headers similar to EN 14825).

See `scripts/extract_header_metadata.py` and generated `data/header_climate_mapping.json` for raw header frequency counts.

---

## Usage Tips

- Use matching dimension codes when comparing models.
- For standard comparisons, use `4_3_0_0` (low temp, average climate).
- For worst-case evaluation, use `5_2_0_0` (medium temp, colder climate).
- Inspect all available dimensions to understand performance spread across climates and supply temperatures.

---

_Last updated: November 2025_
