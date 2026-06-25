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

A separate, more serious issue was then found in the script pipeline itself:
Cataluña's SARIMAX selection (92.3% 2025 holdout MAPE, the weakest result in
the project) turned out to be a numerically degenerate fit -- 9 exogenous
features plus ARMA/seasonal terms is too many parameters for the ~22-34 rows
available per target, and the same non-convergence/near-zero-residual-variance
signature was found on 4 of the 5 targets, not just Cataluña. Fixed by
rejecting any SARIMA/SARIMAX fit that fails to converge or whose residual
variance collapses, at the point of fitting, so the rejection propagates
through every existing call site automatically. See "Current Selected Model
Quality" below and `PHASE2_MODELING_REPORT.md` for the full investigation and
the resulting model changes.

A second, independent audit pass then found that the SARIMA order grid's
full-history degeneracy check (added above to catch a literal flat-line
forecast) had itself been applied as a filter across all 15 candidate
orders using full-2023-2025-history fits, contradicting the project's own
"never select using test-set performance" rule. Fixed: SARIMA order ranking
is now training-only with zero exceptions, and the full-history check runs
exactly once, on the single training-only winner, as a disclosed post-hoc
safety veto (`sarima_safety_check.csv`) rather than a selection criterion.
Re-running the full pipeline produced byte-identical results for every
target; see `PHASE2_MODELING_REPORT.md`'s "SARIMA Order Selection:
Training-Only Ranking With a Disclosed Safety Veto" section for the full
investigation.

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
| `data/inputs/mandato_biocarburantes.csv` | 15 x 4 | Annual schedule (2016-2030) | One deterministic mandate feature (`Mandato_Energia_Pct`). All BOE citations verified (2026-06-25); 2027-2030 are the team's own +1.5pp/year projection, not legislated values -- see `Status`/`Fuente` columns. |
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
| `data/features/features_modelo_completo.csv` | 180 x 35 | 2023-01 to 2025-12 | Five targets x 36 months. |
| `data/features/features_train.csv` | 120 x 35 | 2023-01 to 2024-12 | Temporal train split. |
| `data/features/features_test.csv` | 60 x 35 | 2025-01 to 2025-12 | Temporal holdout split; loaded only after model selection is fixed. |
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
| `sarima_grid_search_results.csv` | Training-only walk-forward SARIMA grid-search diagnostics for each target, including the training-window 24-month stability check. Ranking and filtering across all 15 candidates uses only 2023-2024 data. |
| `sarima_order_acceptance.csv` | Records the training-only SARIMA order selected for each target, plus whether that single winner failed the post-hoc full-history shippability safety check (`Safety_Check_Degenerate`) and whether a reviewed override was used (`Override_Applied`/`Override_Reason`). The safety check is the only place 2025 data is used anywhere in SARIMA order selection, and it can only veto the already-chosen winner -- it never ranks or filters the candidate grid. See `sarima_safety_check.csv` for the full per-target audit trail. |
| `sarima_safety_check.csv` | Per-target record of the post-hoc SARIMA shippability safety check: the training-only winning order, whether its full-history refit is degenerate, and whether a reviewed `SARIMA_SAFETY_OVERRIDES` entry was applied. |
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
| `degenerate_fits.csv` | Every SARIMA/SARIMAX fit rejected for non-convergence or near-zero residual variance, with target, pipeline stage, and reason. SARIMAX appears here for 4 of 5 targets. |

## Current Selected Model Quality

| Target | Selected Model | Training Walk-Forward MAPE | 2025 Holdout MAPE | 2025 Holdout R2 |
|---|---|---:|---:|---:|
| Nacional | Logistic | 43.1% | 36.7% | -1.041 |
| Madrid | Logistic | 37.2% | 73.6% | -8.273 |
| Cataluña | SARIMA | 66.9% | 50.1% | -7.182 |
| Andalucía | SARIMA | 48.8% | 52.6% | -1.929 |
| Valencia | Gompertz | 57.3% | 34.2% | -1.246 |

Average selected 2025 holdout MAPE is 49.4%. Cataluña's SARIMAX result (92.3%)
is gone: that fit never converged (confirmed directly -- `sigma2` had
collapsed to 5.07e-7 and statsmodels itself reported a non-convergence
warning and a near-singular covariance matrix), and plain SARIMA, a fit that
actually converges, now wins on the same leak-free evidence. Nacional's
selected model also changed (SARIMA to Logistic) as a side effect of applying
the same fit-quality check to plain SARIMA's order grid search for
consistency: 3 of its 11 training-only folds for the previously-best order
were themselves silently non-convergent.

All selected R2 values are negative, so forecasts should be presented as
directional planning estimates, not precision demand commitments. Andalucía
and Cataluña's forecasts remain fairly flat in absolute terms (24-month
ranges of 157.9 Tm and 64.6 Tm respectively) -- both pass the pipeline's
degeneracy checks, but this is a real small-sample limitation (not enough
clean seasonal history to support a strongly seasonal SARIMA order without
overfitting), not something further pipeline engineering resolves.

## Dataset Lineage

`consumo_biodiesel_ccaa.csv` (and the equivalent provincial/targets files)
are committed as already-processed artifacts with no notebook or script
that derives them from a raw source. They are reproducible anyway:
`scripts/03_clean_cnmc_petroleum.py`'s `reconcile_biodiesel()` independently
verifies, on every run, that CNMC's `CNMC_Biodiesel_Tm` -- built entirely
from `data/raw/consumos_mensuales_petroleo/ds_*.csv` -- reconciles exactly
(0.0 Tm max diff) against `consumo_biodiesel_ccaa.csv`'s `Consumo_Tm` for
every CCAA, every month, 2023-2025. CNMC is therefore the project's real
reproducible-from-raw lineage for the target; the `ESTADISTICAS-BIOS CERT
DEFINITIVAS *.xlsx` files in `data/` are historical/supplementary CORES
material only -- no current script reads them, no 2025-dated file of that
type exists, and they are not required to reproduce any output below. See
`memory.md`'s "Target Lineage Clarified" entry.

```text
data/raw/consumos_mensuales_petroleo/ds_*.csv
  -> scripts/03_clean_cnmc_petroleum.py
  -> data/processed/cnmc_*.csv
  -> (CNMC_Biodiesel_Tm reconciles exactly against consumo_biodiesel_ccaa.csv)

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
