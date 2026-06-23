# Data Audit Report

Generated / refreshed: 2026-06-23
Scope: tracked production datasets, feature tables, outputs, and known optional artifacts.

## Executive Summary

The production data pipeline is coherent at the dataset level: national demand
reconciles to the sum of the CCAA rows, the five delivery targets are present, and
the script path builds causal lag features for the modeling table.

Phase 2 improves the modeling layer on branch `enrico`: model selection now uses
recursive multi-step walk-forward validation, pooled regional ML is tested in the
official script path, and a no-regression acceptance gate prevents Phase 2 changes
from weakening the Phase 1 selected models on the 2025 validation period.

The final delivery policy is no pooling. Pooled regional ML remains available as
a documented sensitivity experiment, but the selected production forecast uses
only non-pooled target-level models.

## Production Inputs

| File | Shape | Date Range | Notes |
|---|---:|---|---|
| `data/inputs/master_dataset.csv` | 720 x 22 | 2023-01 to 2025-12 | Primary production table. Primary key is `Fecha` + `CCAA`. |
| `data/inputs/consumo_biodiesel_ccaa.csv` | 720 x 3 | 2023-01 to 2025-12 | Biodiesel target input by CCAA plus national row. |
| `data/inputs/consumo_biodiesel_targets.csv` | 180 x 4 | 2023-01 to 2025-12 | Five modeled targets only. Superseded by `master_dataset.csv` in production scripts. |
| `data/inputs/consumo_biodiesel_provincial.csv` | 1872 x 5 | 2023-01 to 2025-12 | Province-level source, not used in the CCAA-level model. |
| `data/inputs/macro_indicadores_ine.csv` | 36 x 5 | 2023-01 to 2025-12 | National macro indicators, broadcast to regions. |
| `data/inputs/brent_oil_price_monthly_2023_onwards.csv` | 41 x 5 | 2023-01 to 2026-05 | Only rows through 2025-12 enter the master dataset. |
| `data/inputs/precios_combustibles_2023.csv` | 75553 x 5 | 2023-01-01 to 2023-12-31 | Optional price-ablation source. |
| `data/inputs/precios_combustibles_2024.csv` | 75762 x 5 | 2024-01-01 to 2024-12-31 | Optional price-ablation source. |
| `data/inputs/precios_combustibles_2025.csv` | 75524 x 5 | 2025-01-01 to 2025-12-31 | Optional price-ablation source. |
| `data/inputs/mandato_biocarburantes.csv` | 15 x 5 | Annual schedule | Deterministic mandate features. |
| `data/inputs/turismo_visitantes_ccaa.csv` | 15 x 9 | 2025-10 only | Not used; single-month coverage cannot support a monthly time series model. |

## Processed CNMC Tables

| File | Shape | Date Range | Notes |
|---|---:|---|---|
| `data/processed/cnmc_consumos_petroleo_provincial.csv` | 27664 x 7 | 2023-01 to 2026-02 | Cleaned province-product-month CNMC data. |
| `data/processed/cnmc_consumos_petroleo_ccaa.csv` | 10640 x 5 | 2023-01 to 2026-02 | CCAA-product-month table plus computed `ESPAÑA`. |
| `data/processed/cnmc_diesel_market_features.csv` | 760 x 7 | 2023-01 to 2026-02 | Diesel-market features. Master builder filters to 2025-12. |

Validation checks in the script path:

- Raw CNMC product names and province mappings are validated.
- CNMC biodiesel reconciles exactly to `Consumo_Tm` for 2023-2025.
- National `Consumo_Tm`, `CNMC_Biodiesel_Tm`, `GasoleoA_Tm`, and `DieselPool_Tm` reconcile exactly to the sum of regional rows.
- The production master and modeling feature tables contain no 2026 rows.

## Modeling Feature Tables

| File | Shape | Split | Notes |
|---|---:|---|---|
| `data/features/features_modelo_completo.csv` | 180 x 36 | 2023-01 to 2025-12 | Five targets x 36 months. |
| `data/features/features_train.csv` | 120 x 36 | 2023-01 to 2024-12 | Temporal train split. |
| `data/features/features_test.csv` | 60 x 36 | 2025-01 to 2025-12 | Temporal validation / acceptance split. |
| `data/features/features_precios_combustibles.csv` | 36 x 81 | 2023-01 to 2025-12 | Optional price-ablation features. |

Expected feature nulls:

- Lag and rolling columns are null in early months by construction.
- `features_test.csv` has no nulls in the model-used rows.

Known data issues:

- `PVP_Gasolina98` and `PAI_Gasolina98` have 36 null rows in `master_dataset.csv`, all for Melilla. This is expected because Gasolina 98 is not sold there.
- Many non-target CCAA rows have zero biodiesel consumption in early months. The modeled five-target table has 14 zero target rows, all in 2023, reflecting early/low adoption periods.
- National fuel-price rows are simple monthly means across CCAA rows, not demand-weighted prices.

## Outputs

| File | Current Role |
|---|---|
| `metricas_modelos.csv` | Metrics for the current CNMC-aware candidates, including pooled regional ML. |
| `model_selection_walkforward.csv` | Recursive multi-step model-selection scores over the training period. |
| `metricas_final_seleccionado.csv` | 2025 validation metrics for the selected model per target. |
| `predicciones_test_2025.csv` | 2025 predictions for all current candidates. |
| `forecast_24m_sarima_rf_xgb.csv` | 2026-2027 forecasts for all current candidates. Legacy filename. |
| `phase2_model_acceptance.csv` | Phase 1 model, Phase 2 proposed model, no-pooling final policy, final selected model, and acceptance decision. |
| `phase2_pooling_experiment_metrics.csv` | 2025 validation metrics for pooled regional ML candidates. |
| `phase2_pooling_decision.csv` | Target-level accept/reject explanation for pooled ML, including the no-pooling final policy. |
| `metricas_modelos_con_precios.csv` | Optional price-ablation metrics from notebook 08. |
| `forecast_24m_con_precios.csv` | Optional price-ablation forecasts from notebook 08. |
| `metricas_comparativa.csv` | Combined current metrics plus optional price-ablation metrics when available. |
| `tableau_dashboard.csv` | Historical, test prediction, and forecast rows for dashboarding. |
| `tableau_metricas.csv` | Dashboard metrics table with selected-model flags. |
| `tableau_forecast_pivot.csv` | Selected forecast pivoted by target. |
| `tableau_export_legacy.csv` | Historical plus selected forecast in legacy long format. |

## Current Selected Model Quality

| Target | Selected Model | 2025 MAPE | 2025 R2 | Readiness |
|---|---|---:|---:|---|
| Nacional | SARIMA | 29.0% | -0.009 | Kept from Phase 1; Phase 2 proposal regressed. |
| Madrid | Logistic | 73.6% | -8.273 | Improved versus Phase 1 Gompertz. |
| Cataluña | SARIMA | 47.2% | -5.620 | Best non-pooled validation alternative under the final no-pooling policy. |
| Andalucía | Logistic | 48.4% | -1.555 | Kept from Phase 1; pooled proposal regressed slightly. |
| Valencia | Gompertz | 34.2% | -1.246 | Weak but less severe. |

Average selected MAPE improved from 94.6% in Phase 1 to 46.5% after Phase 2 and
the no-pooling final policy.
Remaining risk: all selected R2 values are still negative except near-zero national
SARIMA, so the forecasts should be presented as directional planning estimates.

## Dataset Lineage

```text
CNMC raw CSVs
  -> scripts/03_clean_cnmc_petroleum.py
  -> data/processed/cnmc_*.csv

consumo_biodiesel_ccaa.csv
macro_indicadores_ine.csv
brent_oil_price_monthly_2023_onwards.csv
precios_combustibles_2023/24/25.csv
cnmc_diesel_market_features.csv
  -> scripts/02_master_dataset_builder.py
  -> data/inputs/master_dataset.csv

master_dataset.csv
mandato_biocarburantes.csv
  -> scripts/04_build_features.py
  -> data/features/features_modelo_completo.csv
  -> data/features/features_train.csv
  -> data/features/features_test.csv

features_*.csv
  -> scripts/05_modeling_with_cnmc.py
  -> data/outputs/*.csv
  -> data/outputs/phase2_*.csv
  -> reports/figures/07_model_comparison.png
  -> reports/figures/11_forecast_24m.png
```
