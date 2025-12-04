# SCOP Batch Results Template

This template defines the canonical columns emitted by the SCOP batch simulation pipeline. Every row represents a unique `(manufacturer, model, variant, dimension)` combination that satisfied the minimum EN14825 input requirements and successfully ran through `scripts/calculate_scop_en14825.py`.

| Column | Type | Description |
| --- | --- | --- |
| `manufacturer_name` | string | Manufacturer taken from the `measurements` table (or `variants` table if needed). |
| `model_name` | string | Model family for the variant. |
| `variant_name` | string | Variant identifier (as reported in the database). |
| `dimension` | string | EN dimension token (e.g. `4_2_0_0`). |
| `application_label` | string | Human readable text derived from the first dimension digit (e.g. `Low temp (35°C)`). |
| `climate_label` | string | Human readable text derived from the second dimension digit (`Warmer`, `Average`, `Colder`). |
| `unit_type` | string | Passed through to `SCOPCalculator` (`air` or `water_brine`). |
| `pdesignh_reported_kw` | float | Declared design load from `EN14825_002` (kW). |
| `pdesignh_inferred_kw` | float | Inferred design load from the Tbiv point (calculator output). |
| `tbiv_c` | float | Bivalent temperature (`EN14825_004`). |
| `tol_c` | float | Operating limit temperature (`EN14825_005`). |
| `poff_kw` | float | Off-mode power consumption (`EN14825_023`) converted to kW. |
| `pto_kw` | float | Thermostat-off power (`EN14825_024`) converted to kW. |
| `psb_kw` | float | Standby mode power (`EN14825_025`) converted to kW. |
| `pck_kw` | float | Crankcase heater power (`EN14825_026`) converted to kW. |
| `reported_scop` | float | Certificate SCOP (`EN14825_003`). |
| `calculated_scop` | float | SCOP returned by the calculator (Formula 18). |
| `delta_scop_pct` | float | Percent difference `(calculated−reported)/reported × 100`. |
| `reported_eta_percent` | float | Reported ηs value (`EN14825_001`). |
| `calculated_eta_percent` | float | ηs produced by the calculator (Formula 14, %). |
| `delta_eta_pct` | float | Percent difference relative to reported ηs. |
| `reported_qhe_kwh` | float | Certificate heat pump energy consumption (`EN14825_029`). |
| `calculated_qhe_active_kwh` | float | `metrics["QHE_active"]` (active-mode electrical energy). |
| `delta_qhe_pct` | float | Percent difference relative to reported Qhe. |
| `calc_qh_kwh` | float | `metrics["QH"]` — total heat delivered by the unit. |
| `scopnet` | float | `metrics["SCOPnet"]`. |
| `scopon` | float | `metrics["SCOPon"]`. |
| `q_sup_kwh` | float | Supplementary heater energy (`metrics["QSUP"]`). |
| `q_offmode_kwh` | float | Off-mode electrical energy (`metrics["Q_offmode"]`). |
| `missing_required_en_codes` | string | Semicolon-separated list of required EN codes that were absent (empty when the run succeeded). |
| `missing_optional_en_codes` | string | Semicolon-separated list of optional EN codes that were absent (e.g. Cdh at −7 °C and +2 °C). |
| `status` | string | `ok`, `missing-data`, or `error`. |
| `status_message` | string | Free-form diagnostic text for skipped/error rows. |
| `timestamp_utc` | string | ISO-8601 timestamp when the row was generated. |

Additional columns can be appended as needed (e.g., reversible-hour flags, inferred supplementary-heater utilisation metrics, etc.) but the above set enables apples-to-apples comparison of certificate vs calculated results across the entire database.
