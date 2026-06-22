# Phase 2 Modeling Report

Generated: 2026-06-21

Branch: `enrico`

## Purpose

Phase 2 productionizes the modeling investigation from the `enrico` branch while
keeping the Phase 1 cleanup from `main`. The target remains monthly biodiesel
demand in tonnes for Spain national demand plus Madrid, Catalonia, Andalusia,
and Valencia.

This work is implemented in the official script pipeline, not in throwaway
notebooks or scratch scripts.

## What Changed

The production modeling script now uses a recursive multi-step walk-forward
validation gate instead of the previous one-step gate.

The new gate:

- uses only the 2023-2024 training period for model-selection proposals;
- evaluates recursive paths up to 6 months ahead inside the training window;
- evaluates ML models the same way they are deployed, with each predicted month
  feeding the next month's lag features;
- holds macro lag inputs at the last known value during recursive paths;
- keeps `Nacional` separate from regional pooling;
- allows the four regional series to consider Logistic, Gompertz, and pooled
  regional ML candidates.

A final no-regression acceptance gate then compares the proposed Phase 2 model
against the Phase 1 selected model on the 2025 holdout. A proposed model is kept
only if it does not worsen the Phase 1 holdout MAPE.

## Pooling Result

Pooled regional ML was tested on the stacked regional panel for Madrid,
Catalonia, Andalusia, and Valencia. `Nacional` was not pooled because it is the
national total and should not be fit jointly with its component regions.

The production decision is target-specific:

| Target | Phase 1 Model | Phase 1 MAPE | Phase 2 Proposed | Proposed MAPE | Final Model | Decision |
|---|---|---:|---|---:|---|---|
| Nacional | SARIMA | 29.0% | Logistic | 36.7% | SARIMA | Kept Phase 1, no regression allowed |
| Madrid | Gompertz | 197.1% | Logistic | 73.6% | Logistic | Accepted |
| Catalonia | Gompertz | 164.2% | Pooled Random Forest | 46.8% | Pooled Random Forest | Accepted |
| Andalusia | Logistic | 48.4% | Pooled Random Forest | 49.5% | Logistic | Kept Phase 1, no regression allowed |
| Valencia | Gompertz | 34.2% | Logistic | 34.7% | Gompertz | Kept Phase 1, no regression allowed |

Average selected 2025 MAPE improves from 94.6% to 46.4%.

## Why Not Use Pooled Models Everywhere?

Pooling is useful only where it passes both gates.

- Madrid's best pooled model scores well on the 2025 holdout, but the
  training-only multi-step gate did not select it. It is therefore rejected for
  production to avoid choosing models directly from test-set performance.
- Catalonia's pooled Random Forest is selected by the training-only gate and
  improves the 2025 holdout, so it is accepted.
- Andalusia and Valencia do not receive pooled models because the proposed
  pooled or curve alternatives do not beat their Phase 1 selected models on the
  2025 holdout.

## Current Selected Models

| Target | Final Model | 2025 MAPE | 2025 R2 |
|---|---|---:|---:|
| Nacional | SARIMA | 29.0% | -0.009 |
| Madrid | Logistic | 73.6% | -8.273 |
| Catalonia | Pooled Random Forest | 46.8% | -5.158 |
| Andalusia | Logistic | 48.4% | -1.555 |
| Valencia | Gompertz | 34.2% | -1.246 |

## New Output Files

- `data/outputs/phase2_model_acceptance.csv`: proposed model, Phase 1 model,
  final selected model, and accept/reject decision per target.
- `data/outputs/phase2_pooling_experiment_metrics.csv`: 2025 holdout metrics
  for pooled regional ML candidates.
- `data/outputs/phase2_pooling_decision.csv`: pooled-model decision summary.

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

Catalonia's selected pooled Random Forest forecast is intentionally
plateau-like: tree models interpolate from learned demand levels and do not
extrapolate a new unbounded trend. This is acceptable because it improves the
2025 holdout and avoids the explosive behavior seen in unbounded models, but it
should be explained as a conservative plateau forecast rather than a structural
growth curve.

R2 remains negative for every selected target except near-zero national SARIMA,
so these forecasts should be presented as directional planning scenarios, not
high-precision demand commitments.
