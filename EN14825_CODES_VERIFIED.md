# EN14825 Code Mapping - STATISTICALLY VERIFIED

## Overview

This document contains the verified mapping of EN14825 codes to physical parameters, based on a statistical analysis of 1,441 matched database/PDF pairs (November 2025).

## Core Performance Metrics

| Code | Parameter | Unit | Description | Confidence |
|------|-----------|------|-------------|------------|
| **EN14825_001** | **ηs** | % | Seasonal space heating energy efficiency | High |
| **EN14825_002** | **Prated** | kW | Rated heating capacity | High |
| **EN14825_003** | **SCOP** | - | Seasonal coefficient of performance | High |
| **EN14825_004** | **Tbiv** | °C | Bivalent temperature | High |
| **EN14825_005** | **TOL** | °C | Operating limit temperature | High |
| **EN14825_029** | **Qhe** | kWh/yr | Annual heating energy consumption | High |

## Heating Capacity & COP (Part Load Points)

| Code | Parameter | Temp | Description |
|------|-----------|------|-------------|
| **EN14825_008** | Pdh | -7°C | Heating capacity at -7°C |
| **EN14825_009** | COP | -7°C | COP at -7°C |
| **EN14825_010** | Pdh | +2°C | Heating capacity at +2°C |
| **EN14825_011** | COP | +2°C | COP at +2°C |
| **EN14825_012** | Pdh | +7°C | Heating capacity at +7°C |
| **EN14825_013** | COP | +7°C | COP at +7°C |
| **EN14825_014** | Pdh | +12°C | Heating capacity at +12°C |
| **EN14825_015** | COP | +12°C | COP at +12°C |
| **EN14825_016** | Pdh | Tbiv | Heating capacity at Tbiv |
| **EN14825_017** | COP | Tbiv | COP at Tbiv |
| **EN14825_018** | Pdh | TOL | Heating capacity at TOL |
| **EN14825_019** | COP | TOL | COP at TOL |
| **EN14825_044** | Pdh | -15°C | Heating capacity at -15°C (Colder Climate) |
| **EN14825_045** | COP | -15°C | COP at -15°C (Colder Climate) |

## Degradation Coefficients (Heating - Cdh)

| Code | Parameter | Temp | Description |
|------|-----------|------|-------------|
| **EN14825_047** | Cdh | -7°C | Degradation coefficient at -7°C |
| **EN14825_048** | Cdh | +2°C | Degradation coefficient at +2°C |
| **EN14825_049** | Cdh | +7°C | Degradation coefficient at +7°C |
| **EN14825_050** | Cdh | +12°C | Degradation coefficient at +12°C |
| **EN14825_051** | Cdh | -15°C | Degradation coefficient at -15°C |
| **EN14825_021** | Cdh | TOL | Degradation coefficient at TOL |

## Cooling Performance (SEER & EER)

| Code | Parameter | Temp | Description |
|------|-----------|------|-------------|
| **EN14825_030** | Pdesignc | - | Design cooling capacity |
| **EN14825_031** | SEER | - | Seasonal Energy Efficiency Ratio |
| **EN14825_041** | Qce | - | Annual cooling energy consumption |
| **EN14825_032** | Pdc | 35°C | Cooling capacity at 35°C |
| **EN14825_033** | EER | 35°C | EER at 35°C |
| **EN14825_034** | Pdc | 30°C | Cooling capacity at 30°C |
| **EN14825_035** | EER | 30°C | EER at 30°C |
| **EN14825_036** | Pdc | 25°C | Cooling capacity at 25°C |
| **EN14825_037** | EER | 25°C | EER at 25°C |
| **EN14825_038** | Pdc | 20°C | Cooling capacity at 20°C |
| **EN14825_039** | EER | 20°C | EER at 20°C |

## Degradation Coefficients (Cooling - Cdc)

| Code | Parameter | Temp | Description |
|------|-----------|------|-------------|
| **EN14825_052** | Cdc | 35°C | Degradation coefficient at 35°C |
| **EN14825_053** | Cdc | 30°C | Degradation coefficient at 30°C |
| **EN14825_054** | Cdc | 25°C | Degradation coefficient at 25°C |
| **EN14825_055** | Cdc | 20°C | Degradation coefficient at 20°C |

## Auxiliary Power & Other

| Code | Parameter | Unit | Description |
|------|-----------|------|-------------|
| **EN14825_022** | WTOL | °C | Water temperature at operating limit |
| **EN14825_023** | Poff | W | Off-mode power |
| **EN14825_024** | PTO | W | Thermostat-off mode power |
| **EN14825_025** | PSB | W | Standby mode power |
| **EN14825_026** | PCK | W | Crankcase heater power |
| **EN14825_027** | Control | - | Capacity control (Fixed/Variable) |
| **EN14825_028** | PSUP | kW | Supplementary heater capacity |

*Last updated: 2025-11-24*
