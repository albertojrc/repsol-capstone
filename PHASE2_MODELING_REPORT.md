# Training-Only Model Selection Report

Generated: 2026-06-24

Branch: `sacha`

## Purpose

This branch rebuilds only the modeling layer. The data cleaning, master dataset,
feature engineering, CNMC joins, mandate schedule, leakage-safe lags, plots, and
exports are retained.

The final design is not "feature-aware models only." Instead, each target gets an
open seven-family comparison and the training-only evidence decides.

## Candidate Set

For each target, the headline-eligible candidates are:

- SARIMA
- SARIMAX, using seasonal terms plus lagged macro, lagged CNMC diesel-market, and mandate features
- Logistic growth curve
- Gompertz growth curve
- Ridge regression on the engineered feature set
- Random Forest on the engineered feature set
- XGBoost on the engineered feature set

All seven are eligible to win for all five targets. Pooled Ridge, Pooled Random
Forest, Pooled XGBoost, and Diesel Share remain in the metrics output as
diagnostics only; they cannot be selected as the headline model.

## Selection Rule

Model-family selection is made only by recursive multi-step walk-forward
validation inside the 2023-2024 training window. The 2025 holdout is loaded only
after `Selected_Model` is fixed and is used only for reported MAE/RMSE/MAPE/R2.

SARIMA order selection is also training-only. The SARIMA grid uses the same
training-window walk-forward scores and rejects orders whose training-origin
24-month forecast is degenerate before sorting by walk-forward MAPE. There is no
2025 SARIMA no-regression gate.

The walk-forward horizon is now 12 months so the selector sees longer recursive
behavior rather than only short-horizon folds.

## Seven-Candidate Walk-Forward Results

MAPE values below are training-window walk-forward MAPEs.

| Target | SARIMA | SARIMAX | Logistic | Gompertz | Ridge | Random Forest | XGBoost | Selected |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Nacional | 39.7 | 54.2 | 43.1 | 43.6 | 86.1 | 79.6 | 77.1 | SARIMA |
| Madrid | 73.2 | 94.3 | 37.2 | 59.2 | 6559.8 | 86.9 | 86.3 | Logistic |
| Cataluña | 69.6 | 68.5 | 82.5 | 82.8 | 88.0 | 85.3 | 85.1 | SARIMAX |
| Andalucía | 53.9 | 89.8 | 68.3 | 68.7 | 96.4 | 90.5 | 84.3 | SARIMA |
| Valencia | 59.3 | 87.5 | 60.5 | 57.3 | 99.0 | 99.3 | 98.9 | Gompertz |

## Honest 2025 Holdout Metrics

These metrics are reported after selection and are not used to choose the model.

| Target | Selected model | MAE | RMSE | MAPE | R2 |
|---|---|---:|---:|---:|---:|
| Nacional | SARIMA | 4,278.0 | 4,921.8 | 29.0% | -0.009 |
| Madrid | Logistic | 1,924.0 | 2,057.2 | 73.6% | -8.273 |
| Cataluña | SARIMAX | 2,722.3 | 2,862.4 | 92.3% | -19.827 |
| Andalucía | SARIMA | 853.5 | 1,027.6 | 49.7% | -1.662 |
| Valencia | Gompertz | 360.3 | 446.6 | 34.2% | -1.246 |

## Forecast-Shape Checks

`scripts/06_validate_outputs.py` now fails if selected-model forecasts contain:

- identical or near-identical 24-month paths for two different targets
- a near-flat selected forecast
- an exact or near-exact repeating cycle shorter than the 24-month horizon

The selected forecasts pass those checks. Manual inspection confirms no two
targets are identical, no selected target is a flat constant, and no selected
target exactly repeats its prior 12 months.

## Uncertainty Band

`reports/figures/11_forecast_24m.png` no longer uses a cosmetic fixed +/-20%
band. The selected forecast band is now derived from each target's selected-model
2025 error, using the larger of the target's holdout RMSE and MAPE-scaled
forecast level. This makes Madrid and Cataluña visibly wider than Nacional.

## Diagnostic Results

Pooled regional ML remains useful as a sensitivity check. In the 2025 holdout it
beats the headline model for Madrid, Cataluña, and Andalucía, but it is retained
only as a diagnostic because the headline production design is independent
per-target modeling with no pooled winner.

The previous pooled Random Forest diagnostic could collapse to identical regional
paths because the shallow trees ignored region dummies once recursive lag
features stabilized. The pooled Random Forest now uses higher tree capacity for
the larger pooled panel, and a controlled same-history/different-region-dummy
check confirms that pooled RF and pooled XGBoost produce different regional
paths. Direct per-target Random Forest keeps the conservative tiny-sample
settings.

Cataluña is the main warning case: training-only walk-forward selects SARIMAX by
a narrow margin over SARIMA, but the never-used-for-selection 2025 holdout is
weak at 92.3% MAPE. This should be stated plainly in the business interpretation.

## Output Files

- `data/outputs/metricas_modelos.csv`: all independent candidates plus diagnostic pooled/Diesel Share metrics
- `data/outputs/metricas_final_seleccionado.csv`: selected-model holdout metrics
- `data/outputs/metricas_final_selected.csv`: English alias of selected metrics
- `data/outputs/model_selection_walkforward.csv`: training-only seven-candidate selection table
- `data/outputs/sarima_grid_search_results.csv`: training-only SARIMA order grid
- `data/outputs/sarima_order_acceptance.csv`: training-only SARIMA production orders
- `data/outputs/phase2_model_acceptance.csv`: selected-model lineage
- `data/outputs/phase2_pooling_experiment_metrics.csv`: diagnostic pooled metrics
- `data/outputs/phase2_pooling_decision.csv`: diagnostic-only pooled decision table
- `data/outputs/forecast_24m_sarima_rf_xgb.csv`: legacy all-model forecast file
- `data/outputs/forecast_24m_selected.csv`: selected-only headline forecast
- `reports/figures/07_model_comparison.png`, `11_forecast_24m.png`: regenerated figures

## Remaining Limitations

The sample is still very small: 24 training months and 12 holdout months per
target. The 2025 holdout is now honest, but it is still only one year.

Some selected models are univariate because the training-only evidence selected
them. This is intentional: engineered variables are evaluated in SARIMAX and the
ML families, but they are not forced to win.

R2 remains negative for all selected targets. Treat the forecasts as directional
planning inputs, not high-precision operational commitments.
