# Phase 2 Modeling Report

Generated: 2026-06-23

Branch: `enrico`

## Purpose

Phase 2 productionizes the modeling investigation from the `enrico` branch while
keeping the Phase 1 cleanup from `main`. The target remains monthly biodiesel
demand in tonnes for Spain national demand plus Madrid, Catalonia, Andalusia,
and Valencia.

This work is implemented in the official script pipeline, not in throwaway
notebooks or scratch scripts. The 2025 period is used as a validation and
acceptance period, not as a pristine final test set.

## What Changed

The production modeling script now uses a recursive multi-step walk-forward
validation gate instead of the previous one-step gate.

The gate:

- uses only the 2023-2024 training period for model-selection proposals;
- evaluates recursive paths up to 6 months ahead inside the training window;
- evaluates ML models the same way they are deployed, with each predicted month
  feeding the next month's lag features;
- holds macro lag inputs at the last known value during recursive paths;
- keeps `Nacional` separate from regional pooling;
- lets the regional series consider Logistic, Gompertz, and pooled regional ML
  sensitivity candidates.

A no-regression acceptance gate then compares the proposed Phase 2 model against
the Phase 1 selected model on the 2025 validation period. A proposed model is
kept only if it does not worsen the Phase 1 validation MAPE.

Final delivery policy: the selected production model set is non-pooled. Pooled
regional ML remains in the outputs as a sensitivity experiment, but it is not
used in `metricas_final_seleccionado.csv`, the selected Tableau forecast pivot,
or the selected forecast figure.

SARIMA parameters are also tested with a constrained training-only grid search.
The grid-selected SARIMA order is then checked against the default
`(1, 1, 1)(1, 0, 0, 12)` order on the 2025 acceptance period. This makes the
parameter search visible without letting a training-CV winner silently weaken
the production forecast.

## Selection Result

| Target | Phase 1 Model | Phase 1 MAPE | Phase 2 Proposed | Proposed MAPE | Final Model | Decision |
|---|---|---:|---|---:|---|---|
| Nacional | SARIMA | 29.0% | Logistic | 36.7% | SARIMA | Kept Phase 1, no regression allowed |
| Madrid | Gompertz | 197.1% | Logistic | 73.6% | Logistic | Accepted |
| Catalonia | Gompertz | 164.2% | Pooled Random Forest | 46.8% | SARIMA | Selected by final no-pooling policy |
| Andalusia | Logistic | 48.4% | Pooled Random Forest | 49.5% | Logistic | Kept Phase 1, no regression allowed |
| Valencia | Gompertz | 34.2% | Logistic | 34.7% | Gompertz | Kept Phase 1, no regression allowed |

Average selected 2025 validation MAPE improves from 94.6% in the Phase 1
baseline to 46.5% after Phase 2 and the final no-pooling policy.

## SARIMA Grid Search

The constrained SARIMA grid selected the following training-period walk-forward
winners:

| Target | Grid-selected order | Grid-selected seasonal order | Training WF MAPE |
|---|---|---|---:|
| Nacional | `(1, 1, 0)` | `(1, 0, 0, 12)` | 30.023 |
| Madrid | `(1, 1, 1)` | `(1, 0, 0, 12)` | 27.292 |
| Catalonia | `(0, 1, 1)` | `(1, 0, 0, 12)` | 57.011 |
| Andalusia | `(0, 1, 1)` | `(0, 0, 0, 12)` | 30.949 |
| Valencia | `(1, 1, 2)` | `(1, 0, 0, 12)` | 19.335 |

The 2025 no-regression acceptance check then produced:

| Target | Default 2025 MAPE | Grid 2025 MAPE | Production SARIMA order | Decision |
|---|---:|---:|---|---|
| Nacional | 29.0% | 34.4% | `(1, 1, 1)(1, 0, 0, 12)` | Kept default SARIMA |
| Madrid | 318.6% | 318.6% | `(1, 1, 1)(1, 0, 0, 12)` | Default order selected by grid |
| Catalonia | 47.2% | 49.6% | `(1, 1, 1)(1, 0, 0, 12)` | Kept default SARIMA |
| Andalusia | 52.5% | 50.2% | `(0, 1, 1)(0, 0, 0, 12)` | Accepted grid order |
| Valencia | 57.4% | 60.9% | `(1, 1, 1)(1, 0, 0, 12)` | Kept default SARIMA |

This does not change the final selected model table because SARIMA is selected
only for Nacional and Catalonia in the final production set, and both keep the
default SARIMA order after the acceptance check.

## Pooling Result

Pooled regional ML was tested on the stacked regional panel for Madrid,
Catalonia, Andalusia, and Valencia. `Nacional` was not pooled because it is the
national total and should not be fit jointly with its component regions.

The production decision is target-specific:

| Target | Production Model | Production MAPE | Best Pooled Model | Best Pooled MAPE | Production Decision |
|---|---|---:|---|---:|---|
| Madrid | Logistic | 73.6% | Pooled Random Forest | 43.0% | Rejected because the training-only gate did not select it |
| Catalonia | SARIMA | 47.2% | Pooled Random Forest | 46.8% | Rejected by final no-pooling policy |
| Andalusia | Logistic | 48.4% | Pooled XGBoost | 48.4% | No meaningful validation improvement |
| Valencia | Gompertz | 34.2% | Pooled XGBoost | 35.6% | No validation improvement |

Madrid's pooled validation metric is better than the selected Logistic model, but
it is not adopted because doing so would choose directly from the 2025 validation
period rather than from the training-only gate. Catalonia's pooled Random Forest
is retained only as sensitivity output because the final model policy is
non-pooled.

## Current Selected Models

| Target | Final Model | 2025 MAPE | 2025 R2 |
|---|---|---:|---:|
| Nacional | SARIMA | 29.0% | -0.009 |
| Madrid | Logistic | 73.6% | -8.273 |
| Catalonia | SARIMA | 47.2% | -5.620 |
| Andalusia | Logistic | 48.4% | -1.555 |
| Valencia | Gompertz | 34.2% | -1.246 |

## Output Files

- `data/outputs/phase2_model_acceptance.csv`: proposed model, Phase 1 model,
  no-pooling final policy, final selected model, and accept/reject decision per
  target.
- `data/outputs/phase2_pooling_experiment_metrics.csv`: 2025 validation metrics
  for pooled regional ML sensitivity candidates.
- `data/outputs/phase2_pooling_decision.csv`: pooled-model decision summary with
  the no-pooling final policy flag.
- `data/outputs/sarima_grid_search_results.csv`: training-only SARIMA
  parameter-search diagnostics.
- `data/outputs/sarima_order_acceptance.csv`: SARIMA order no-regression
  acceptance against the default order.

The standard outputs are also regenerated:

- `metricas_modelos.csv`
- `model_selection_walkforward.csv`
- `metricas_final_seleccionado.csv`
- `predicciones_test_2025.csv`
- `forecast_24m_sarima_rf_xgb.csv`
- `tableau_dashboard.csv`
- `tableau_metricas.csv`
- `tableau_forecast_pivot.csv`
- `tableau_export_legacy.csv`
- `reports/figures/07_model_comparison.png`
- `reports/figures/11_forecast_24m.png`

## Remaining Limitations

The project is more defensible after Phase 2, but it is still constrained by
the small dataset. Each target has only 24 training months and roughly 21 usable
ML rows after lag features.

R2 remains negative for every selected target except near-zero national SARIMA,
so these forecasts should be presented as directional planning scenarios, not
high-precision demand commitments. The 24-month forecast is especially sensitive
to assumptions about mandate effects and demand saturation because validation
only covers one future year.

Catalonia's selected non-pooled SARIMA forecast can continue an upward trend
more aggressively than the pooled Random Forest sensitivity forecast. This is a
known tradeoff of the no-pooling final policy and should be described in the
deliverable rather than hidden.
