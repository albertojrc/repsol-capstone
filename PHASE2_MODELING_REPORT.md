# Training-Only Model Selection Report

Generated: 2026-06-24 (updated same day after the SARIMAX degeneracy fix)

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
training-window walk-forward scores and rejects orders that fail either of two
independent stability checks before sorting by walk-forward MAPE: a
training-window 24-month forecast must not be flat/repeating, and a
full-36-month-history 24-month forecast (the actual shape `final_forecasts()`
ships) must not be flat/repeating either. There is no 2025 SARIMA no-regression
gate.

A SARIMA or SARIMAX fit is also rejected outright -- before it is ever scored,
at the point of fitting -- if it is numerically degenerate: the optimizer did
not converge, or the fitted residual variance (`sigma2`) has collapsed below
`1e-3`. This is the signature of a model with too many parameters for too few
rows, and it was added specifically because SARIMAX exhibited it (see below).

The walk-forward horizon is 12 months so the selector sees longer recursive
behavior rather than only short-horizon folds.

## Why The Degeneracy-At-Fit-Time Check Was Added

Cataluña's first selected model under this design was SARIMAX, at 92.3% 2025
holdout MAPE -- the weakest result in the project. Direct investigation of the
refit model found `sigma2` had collapsed to 5.07e-7 and statsmodels reported
`Maximum Likelihood optimization failed to converge` plus a near-singular
covariance matrix (condition number 4.85e+22). Checking all 5 targets showed
this is not Cataluña-specific: SARIMAX's 9 exogenous regressors plus
ARMA/seasonal terms (~11 parameters) against only ~22-34 usable training rows
produced the same non-convergence/near-zero-sigma2 signature for 4 of 5
targets (Nacional, Madrid, Cataluña, Valencia); only Andalucía's fit was
numerically healthy.

Per-fold walk-forward inspection showed why this passed selection anyway:
Cataluña's SARIMAX fold errors had std 62.8 (one fold spiking to 283.9% MAPE)
against plain SARIMA's std 25.0, yet their *medians* (68.5% vs 69.6%) looked
close enough for SARIMAX to "win" by a hair. The median aggregation -- a
deliberate, otherwise-sound design choice to stop a single bad fold dominating
selection -- was exactly what hid the instability.

**Decision made (explicitly, not a default):** fix this with a fit-quality
gate, not by trimming `SARIMAX_EXOG_FEATS` to make SARIMAX artificially
competitive. If SARIMAX is not viable at this sample size, that is the honest
finding to report, not something to engineer around.

The same fit-quality check was applied to plain SARIMA too, for consistency --
the same overfitting risk exists in principle for any order in the SARIMA
grid, just far less often. This had a real effect: 3 of Nacional's 11
training-only walk-forward folds for its previously-best order
`(1,1,1)(1,0,0,12)` were themselves silently non-convergent; excluding them
raised that order's honest score from 39.7% to 51.9%, which is why a
different order -- and ultimately Logistic instead of SARIMA -- now wins for
Nacional.

## Seven-Candidate Walk-Forward Results (after the fix)

MAPE values below are training-window walk-forward MAPEs. `inf` means every
fold for that candidate was either an exception or a degenerate fit.

| Target | SARIMA | SARIMAX | Logistic | Gompertz | Ridge | Random Forest | XGBoost | Selected |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Nacional | 48.9 | inf | 43.1 | 43.6 | 86.1 | 79.6 | 77.1 | Logistic |
| Madrid | 42.9 | inf | 37.2 | 59.2 | 6559.8 | 86.9 | 86.3 | Logistic |
| Cataluña | 66.9 | inf | 82.5 | 82.8 | 88.0 | 85.3 | 85.1 | SARIMA |
| Andalucía | 48.8 | inf | 68.3 | 68.7 | 96.4 | 90.5 | 84.3 | SARIMA |
| Valencia | 66.9 | 92.1 | 60.5 | 57.3 | 99.0 | 99.3 | 98.9 | Gompertz |

SARIMAX is no longer eligible for Nacional, Madrid, Cataluña, or Andalucía
(every fold degenerate). For Valencia it has a real but poor score (92.1%)
and still loses to Gompertz. SARIMAX wins zero targets after this fix -- this
is the expected, honest consequence of the decision above, not a remaining bug.

## Honest 2025 Holdout Metrics

These metrics are reported after selection and are not used to choose the model.

| Target | Selected model | MAE | RMSE | MAPE | R2 |
|---|---|---:|---:|---:|---:|
| Nacional | Logistic | 6,228.7 | 6,999.4 | 36.7% | -1.041 |
| Madrid | Logistic | 1,924.0 | 2,057.2 | 73.6% | -8.273 |
| Cataluña | SARIMA | 1,557.8 | 1,794.1 | 50.1% | -7.182 |
| Andalucía | SARIMA | 898.8 | 1,077.9 | 52.6% | -1.929 |
| Valencia | Gompertz | 360.3 | 446.6 | 34.2% | -1.246 |

Cataluña's holdout MAPE improved from 92.3% to 50.1% (still the second-worst
target). Nacional's holdout MAPE moved from 29.0% to 36.7% -- numerically
worse in isolation, but the 29.0% was partly earned by training-CV folds since
shown to be non-convergent noise, not real skill; 36.7% is the more
trustworthy number even though the headline figure looks worse.

## Forecast-Shape Checks

`scripts/06_validate_outputs.py` fails if selected-model forecasts contain:

- identical or near-identical 24-month paths for two different targets
- a near-flat selected forecast
- an exact or near-exact repeating cycle shorter than the 24-month horizon

The selected forecasts pass those checks, but Andalucía (range 157.9 Tm over
24 months) and Cataluña (range 64.6 Tm) are still fairly flat in absolute
terms -- they pass the thresholds without being dynamic. This reflects a real
small-sample limitation (not enough clean seasonal history to support a
strongly seasonal SARIMA order without overfitting), now explicitly checked
for via the full-history stability test, rather than discovered by accident
the way the original near-flat Andalucía order was.

## Uncertainty Band

`reports/figures/11_forecast_24m.png` uses a forecast band derived from each
target's selected-model 2025 error, using the larger of the target's holdout
RMSE and MAPE-scaled forecast level, not a cosmetic fixed +/-20% band.

## Diagnostic Results

Pooled regional ML remains useful as a sensitivity check. In the 2025 holdout
it beats the headline model for Madrid, Cataluña, and Andalucía, but it is
retained only as a diagnostic because the headline production design is
independent per-target modeling with no pooled winner.

## Output Files

- `data/outputs/metricas_modelos.csv`: all independent candidates plus diagnostic pooled/Diesel Share metrics
- `data/outputs/metricas_final_seleccionado.csv`: selected-model holdout metrics
- `data/outputs/metricas_final_selected.csv`: English alias of selected metrics
- `data/outputs/model_selection_walkforward.csv`: training-only seven-candidate selection table
- `data/outputs/sarima_grid_search_results.csv`: training-only SARIMA order grid, now with both training-window and full-history degeneracy columns
- `data/outputs/sarima_order_acceptance.csv`: training-only SARIMA production orders
- `data/outputs/degenerate_fits.csv`: every SARIMA/SARIMAX fit rejected for non-convergence or near-zero sigma2, with target, stage, and reason
- `data/outputs/phase2_model_acceptance.csv`: selected-model lineage
- `data/outputs/phase2_pooling_experiment_metrics.csv`: diagnostic pooled metrics
- `data/outputs/phase2_pooling_decision.csv`: diagnostic-only pooled decision table
- `data/outputs/forecast_24m_sarima_rf_xgb.csv`: legacy all-model forecast file (now 1152 rows, not 1248, because SARIMAX rows are absent for 4 targets)
- `data/outputs/forecast_24m_selected.csv`: selected-only headline forecast
- `reports/figures/07_model_comparison.png`, `11_forecast_24m.png`: regenerated figures

## Remaining Limitations

The sample is still very small: 24 training months and 12 holdout months per
target. The 2025 holdout is honest, but it is still only one year.

Some selected models are univariate because the training-only evidence
selected them. This is intentional: engineered variables are evaluated in
SARIMAX and the ML families, but they are not forced to win -- and at this
sample size, SARIMAX's richer feature set is currently a liability, not an
advantage.

R2 remains negative for all selected targets. Treat the forecasts as
directional planning inputs, not high-precision operational commitments.

`SARIMAX_EXOG_FEATS` was deliberately left unchanged rather than trimmed to
make SARIMAX artificially competitive. If it is revisited, size it relative to
the smallest target's usable training rows (~22), not independently of
sample size the way the current 9-feature list was chosen.
