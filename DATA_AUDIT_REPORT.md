# Data Audit Report

Generated / refreshed: 2026-06-24 (branch `sacha`)
Scope: tracked production datasets, feature tables, outputs, and known optional artifacts.

## Executive Summary

The production data pipeline is coherent at the dataset level: national demand
reconciles to the sum of the CCAA rows, the five delivery targets are present, and
the script path builds causal lag features for the modeling table. This part of
the pipeline (`scripts/02`, `scripts/03`, `scripts/04`) is unchanged from earlier
audits and remains leakage-free.

The modeling layer was rebuilt on branch `sacha` around a stricter rule: every
target independently runs an open seven-family competition (SARIMA, SARIMAX,
Logistic, Gompertz, Ridge, Random Forest, XGBoost), and the winner is selected
only by recursive multi-step walk-forward validation inside the 2023-2024
training window. The 2025 period is read only after `Selected_Model` is already
fixed, and is used solely to report an honest holdout metric. Pooled regional ML
and Diesel Share remain in the metrics tables as diagnostics, but are not
eligible for the headline forecast. See `PHASE2_MODELING_REPORT.md` for the full
selection table and methodology history.

This refresh also found and fixed three notebook-only regressions introduced by
an earlier "translate notebook content to English" pass, which had renamed
data-column string literals (not just prose) inside code cells:

- `'Tendencia'` (the real trend-index column built by `scripts/04`) had been
  renamed to `'Trend'` inside notebooks 05, 07, 08, and 09, which crashed every
  one of those notebooks with `KeyError: 'Trend'` against the real feature
  tables.
- The raw `Producto` values and the `gasolina95`/`gasolina98` price-feature
  slugs had been renamed to `gasoline95`/`gasoline98` (and `'Diesel A
  habitual'`/`'Diesel Premium'`) inside notebooks 06 and 08, which silently
  failed to match the real `Producto`/column values.
- Notebooks 10, 10.1, and 13 still referenced `Default_2025_MAPE` /
  `Grid_Selected_2025_MAPE`, two columns that no longer exist in
  `sarima_order_acceptance.csv` after the SARIMA order selection was rebuilt to
  be training-only.

All four have been fixed and the affected notebooks (05, 06, 07, 08, 09, 13)
were re-executed end to end to confirm they run clean and to regenerate their
figures. See `NOTEBOOKS_AUDIT.md` for the full notebook-by-notebook status.

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
| `data/features/features_test.csv` | 60 x 36 | 2025-01 to 2025-12 | Temporal holdout split; loaded only after model selection is fixed. |
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
| `metricas_modelos.csv` / `metricas_models.csv` | 2025 holdout metrics for all 7 headline candidates plus Diesel Share and pooled regional ML (duplicate filenames, same content). |
| `sarima_grid_search_results.csv` | Training-only walk-forward SARIMA grid-search diagnostics for each target, including a degeneracy check on the training-window 24-month stability forecast. |
| `sarima_order_acceptance.csv` | Records the training-only grid-selected SARIMA order adopted into production for each target. No 2025 data is used in this decision. |
| `model_selection_walkforward.csv` | Recursive multi-step walk-forward scores for all 7 headline candidates per target, the training-only proposed model, and the final selected model. |
| `metricas_final_seleccionado.csv` / `metricas_final_selected.csv` | 2025 holdout metrics for the model already selected by training-only walk-forward (duplicate filenames, same content). |
| `predicciones_test_2025.csv` | 2025 predictions for all current candidates. |
| `forecast_24m_sarima_rf_xgb.csv` | 2026-2027 forecasts for all current candidates. Legacy filename. |
| `forecast_24m_selected.csv` | The clean 24-month headline forecast: one model per target, the one selected by training-only walk-forward. |
| `phase2_model_acceptance.csv` | Per-target eligible-model set, the training-only proposed model, the selected model, and the training-only walk-forward MAPE that justified selection. No 2025-based acceptance/rejection step remains. |
| `phase2_pooling_experiment_metrics.csv` | 2025 holdout metrics for pooled regional ML sensitivity candidates (diagnostic only). |
| `phase2_pooling_decision.csv` | Confirms pooled regional ML is never eligible for the headline forecast, and records whether a pooled candidate would have scored better on the 2025 holdout (for transparency only). |
| `metricas_modelos_con_precios.csv` | Optional price-ablation metrics from notebook 08. |
| `forecast_24m_con_precios.csv` | Optional price-ablation forecasts from notebook 08. |
| `metricas_comparativa.csv` | Combined current metrics plus optional price-ablation metrics when available. |
| `tableau_dashboard.csv` | Historical, test prediction, and forecast rows for dashboarding. |
| `tableau_metricas.csv` | Dashboard metrics table with selected-model flags. |
| `tableau_forecast_pivot.csv` | Selected forecast pivoted by target. |
| `tableau_export_legacy.csv` | Historical plus selected forecast in legacy long format. |

## Current Selected Model Quality

| Target | Selected Model | Training Walk-Forward MAPE | 2025 Holdout MAPE | 2025 Holdout R2 |
|---|---|---:|---:|---:|
| Nacional | SARIMA | 39.7% | 29.0% | -0.009 |
| Madrid | Logistic | 37.2% | 73.6% | -8.273 |
| Cataluña | SARIMAX | 68.5% | 92.3% | -19.827 |
| Andalucía | SARIMA | 53.9% | 49.7% | -1.662 |
| Valencia | Gompertz | 57.3% | 34.2% | -1.246 |

Average selected 2025 holdout MAPE is 55.8%. This is worse on average than the
earlier (now superseded) policy-restricted selection's 46.5%, because that
number partly reflected 2025-informed acceptance gates that have since been
removed. Three of five targets (Nacional, Madrid, Valencia) select the exact
same model either way; only Cataluña and Andalucía changed, and Cataluña's
result is the weakest in the current set: SARIMAX won the training-only
comparison by a very narrow margin over SARIMA (68.5 vs 69.6), but loses badly
on the 2025 holdout. This is disclosed, not hidden, in notebook 10's summary
cell.

All selected R2 values are negative except the near-zero Nacional SARIMA, so
forecasts should be presented as directional planning estimates, not precision
demand commitments.

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
