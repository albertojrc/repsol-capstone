# Repsol Eco-Fuels Demand Forecasting

This repository forecasts monthly biodiesel demand in Spain for a 24-month horizon
from a forecast origin of 2025-12. The modeled target is total market demand for
biodiesel sold/reported as its own distinct product (`Consumo_Tm`, metric tonnes),
not Repsol sales.

## Target Definition (read first)

Spanish fuel statistics report two separate things under "biodiesel":

1. Biodiesel blended at low concentration (~10.5-14%, per the national mandate)
   into ordinary Gasóleo A diesel. CNMC reports this volume as part of `GASÓLEO A`
   consumption, not separately.
2. Biodiesel sold/reported as its own distinct product line (the CNMC `BIODIESEL`
   category) -- e.g. higher-concentration blends sold to specific fleets/users.

`Consumo_Tm`, the target modeled throughout this project, is **#2**. This was
confirmed directly with the Repsol representative: the team was explicitly asked
to forecast biodiesel sold/reported as its own distinct product line, not the
biodiesel content embedded in the national diesel pool. It is also confirmed
numerically: national `GasoleoA_Tm` runs ~1.7-1.9M Tm/month against `Consumo_Tm`'s
~10-27K Tm/month, and `Biodiesel_GasoleoA_Ratio` sits at 0.5-1.4%, far below the
11.5-14% mandate level it would track if it included the blended portion. Every
reference to "total market biodiesel demand" elsewhere in this repository (this
file, `memory.md`, notebook 13) means this distinct-product-line definition, not
an estimate of all biodiesel content in Spain's fuel mix. See
`notebooks/12_mini_trend_regulation_model.ipynb` for the original technical
writeup of this distinction.

The required delivery scope is:

- National demand (`Nacional`, sourced from `ESPAÑA`)
- Madrid
- Cataluña
- Andalucía
- Valencia
- Monthly forecasts for 2026-01 through 2027-12

## Reproducible Environment

Use Python 3.11. The default Python 3.14 runtime is not supported by the pinned
dependency set.

Recommended setup with `uv`:

```powershell
uv venv --python 3.11 .venv
uv pip install -r requirements.txt --python .\.venv\Scripts\python.exe
```

Conda users can also create the environment from `environment.yml`.

## Production Pipeline

Run these commands from the repository root:

```powershell
.\.venv\Scripts\python scripts/03_clean_cnmc_petroleum.py
.\.venv\Scripts\python scripts/02_master_dataset_builder.py
.\.venv\Scripts\python scripts/04_build_features.py
.\.venv\Scripts\python scripts/05_modeling_with_cnmc.py
.\.venv\Scripts\python scripts/06_validate_outputs.py
.\.venv\Scripts\python scripts/07_selected_model_drivers.py
```

This rebuilds:

- `data/processed/cnmc_*.csv`
- `data/inputs/master_dataset.csv`, `.xlsx`, and metadata
- `data/features/features_modelo_completo.csv`
- `data/features/features_train.csv`
- `data/features/features_test.csv`
- model metrics, SARIMA grid-search diagnostics, 2025 predictions, 2026-2027 forecasts, Tableau exports, and final figures
- `data/outputs/sarima_safety_check.csv`: per-target audit trail for the post-hoc SARIMA
  shippability safety check described in Model Selection below -- the training-only winner,
  whether it failed the full-history safety check, and whether a reviewed
  `SARIMA_SAFETY_OVERRIDES` entry was used.
- `data/outputs/selected_model_sarima_drivers.csv`, `selected_model_curve_parameters.csv`, and
  `selected_model_curve_seasonal.csv`: interpretable coefficient/parameter detail for whichever
  model is currently selected per target (SARIMA lag/seasonal-term significance, or Logistic/
  Gompertz curve shape and seasonal decomposition), used by
  `notebooks/13_business_interpretation_and_recommendations.ipynb`. Re-run this script after
  `scripts/05` any time the headline selection changes; notebook 13 will raise a clear error if
  these files go stale relative to the current selection.
- `data/outputs/mini_model_cross_check.csv`: compares the production forecast against
  `notebooks/12_mini_trend_regulation_model.ipynb`'s independent Conservative/Central/Optimistic
  scenarios, and records which curve family (Logistic vs. Gompertz) the mini model's own in-sample
  R2 would have picked versus what production actually selected. Requires
  `data/outputs/mini_model_scenarios.csv` to already exist (run notebook 12 first); the step is
  skipped with a warning, not a hard failure, if that file is missing.

`forecast_24m_sarima_rf_xgb.csv` is a legacy filename. It now contains all current
candidate families used by the CNMC-aware script, including SARIMA, SARIMAX, Ridge,
Random Forest, XGBoost, Logistic, Gompertz, Diesel Share, and pooled regional ML.
The clean headline forecast is exported as `forecast_24m_selected.csv`.

## Data Sources

- CNMC petroleum-consumption data: this is the reproducible-from-raw lineage for the
  biodiesel target itself, not just diesel-market context. `data/raw/consumos_mensuales_petroleo/ds_*.csv`
  -> `scripts/03_clean_cnmc_petroleum.py` -> `cnmc_diesel_market_features.csv`'s
  `CNMC_Biodiesel_Tm` column reconciles exactly (0.0 Tm max diff) against
  `consumo_biodiesel_ccaa.csv`'s `Consumo_Tm` for the full 2023-2025 window, verified
  on every pipeline run.
- CORES / certified biofuel source files (`ESTADISTICAS-BIOS CERT DEFINITIVAS *.xlsx`):
  CORES/CNMC's original biofuel-certification files, kept as historical/supplementary
  reference material. No notebook or script parses them, no 2025-dated file of that
  type exists in the repo, and they are not required to reproduce any current pipeline
  output -- see `memory.md`'s "Target Lineage Clarified" entry.
- INE: macroeconomic indicators
- BOE mandate schedule: deterministic biofuel mandate features
- Fuel price files: optional price-ablation notebook outputs

The project does not currently use DGT vehicle data in the production dataset.

## Current Dataset Shapes

- `data/inputs/master_dataset.csv`: 720 rows x 22 columns
- `data/features/features_modelo_completo.csv`: 180 rows x 35 columns
- `data/features/features_train.csv`: 120 rows x 35 columns
- `data/features/features_test.csv`: 60 rows x 35 columns
- `data/outputs/forecast_24m_sarima_rf_xgb.csv`: 1152 rows x 4 columns (fewer than
  the theoretical maximum because SARIMAX is excluded as a degenerate fit for
  4 of 5 targets; see `data/outputs/degenerate_fits.csv`)
- `data/outputs/forecast_24m_selected.csv`: 120 rows x 4 columns

## Notebooks

The notebooks are retained for exploration and narrative context. The scripts in
`scripts/` are the source of truth for final reproducible outputs. Notebook outputs
are intentionally cleared to avoid stale local paths, warnings, and old results being
mistaken for a fresh run.

`notebooks/13_business_interpretation_and_recommendations.ipynb` adds the
business-facing interpretation layer: selected-model results by region, regional
train/validation/forecast plots, model limitations, feature interpretation, Repsol
internal-data needs, and recommendations.

## Project Memory Maintenance

`memory.md` is the long-term project log. It is not updated automatically, so any
person or assistant making a major project change should update it in the same
work session, pull request, or commit.

Update `memory.md` when a change affects:

- dataset sources, coverage, merge logic, or target definitions
- feature engineering, leakage controls, or validation policy
- model families, model-selection logic, SARIMA orders, or final selected models
- output files, dashboard exports, forecast origin, or headline metrics
- business interpretation, project scope, or important caveats
- git/branch state that future collaborators need to understand

Tiny formatting edits do not need a memory update. If unsure, add a short dated
entry near the top of `memory.md` and state what changed, why it matters, and how
it was verified.

## Model Selection

The `sacha` branch rebuilds the modeling layer as an open seven-family
competition for each target. Every target independently fits and ranks:

- SARIMA
- SARIMAX, using lagged macro, lagged CNMC diesel-market, seasonal, and mandate features
- Logistic growth curve
- Gompertz growth curve
- Ridge regression on the engineered feature set
- Random Forest on the engineered feature set
- XGBoost on the engineered feature set

All seven are eligible to win for every target. Pooled regional Ridge / Random
Forest / XGBoost and Diesel Share remain in `metricas_modelos.csv` as diagnostics
and sensitivity comparisons, but they are not eligible for the headline forecast.

Selection is made only by recursive multi-step walk-forward validation inside
the 2023-2024 training window. The 2025 period is used only after the selected
model is fixed, to report honest holdout MAE/RMSE/MAPE/R2. The code path in
`scripts/05_modeling_with_cnmc.py` finalizes `Selected_Model` before loading
`features_test.csv`.

A SARIMA/SARIMAX fit is also rejected outright (treated the same as any other
training failure, never eligible to be scored or selected) if it is
numerically degenerate: the optimizer did not converge, or the fitted
residual variance has collapsed to near zero. This is the same overfitting
signature as a model having too many parameters for too few rows. SARIMAX's 8
exogenous regressors plus ARMA/seasonal terms (~10 parameters against ~22-34
training rows) hit this for every target's 2025 holdout fit, and for 4 of the
5 targets' full-history production-forecast fit -- it is excluded everywhere
except where the fit genuinely converges. Every exclusion is written to
`data/outputs/degenerate_fits.csv` with its target, stage, and reason.

SARIMA order ranking is training-only: every candidate order in the grid is
scored and filtered for degeneracy using only the 2023-2024 training window.
The single training-only winner per target then goes through one additional,
disclosed step: a post-hoc shippability safety check fits that winner on the
full 2023-2025 history (the same data the production forecast actually ships
with) and verifies the resulting 24-month forecast is not degenerate. This is
the only place 2025 data is used anywhere in SARIMA order selection, and it
can only veto the single winner -- it never ranks or filters the candidate
grid. If the winner fails it, the pipeline does not auto-substitute another
candidate or silently fall back to the plain default order; it requires an
explicit, reviewed entry in `SARIMA_SAFETY_OVERRIDES`
(`scripts/05_modeling_with_cnmc.py`), or it raises. Cataluña's training-only
winner currently fails this check and uses such a reviewed override -- see
`data/outputs/sarima_safety_check.csv` -- but the resulting order is
unchanged from before this disclosure existed.

| Target | Selected model | Training walk-forward MAPE | 2025 holdout MAPE |
|---|---|---:|---:|
| Nacional | Logistic | 43.1% | 36.7% |
| Madrid | Logistic | 37.2% | 73.6% |
| Cataluña | SARIMA | 66.9% | 50.1% |
| Andalucía | SARIMA | 48.8% | 52.6% |
| Valencia | Gompertz | 57.3% | 34.2% |

Cataluña's SARIMAX result from an earlier version of this pipeline (92.3%
holdout MAPE) is gone: that fit never converged and has been excluded, and
plain SARIMA -- a real, converged fit -- now wins on the same leak-free
training-only evidence. Nacional's selected model also changed from SARIMA to
Logistic, not because of SARIMAX, but because the same degeneracy check was
applied uniformly to plain SARIMA's order grid search too: 3 of Nacional's
11 training-only walk-forward folds for its previously-best order had
themselves been silently non-convergent, flattering its aggregated score
before this fix.

See `PHASE2_MODELING_REPORT.md` for the full seven-candidate table, diagnostic
pooled-model results, forecast-shape validation, and remaining limitations.

## Audit Fixes (2026-06-25)

A formal audit found six issues worth fixing before this goes in front of a
reviewer. All are now fixed and re-verified end to end:

- **Mandate schedule data integrity.** `data/inputs/mandato_biocarburantes.csv`
  had a `Mandato_Energia_Pct` value that dropped from 15.5% (2027) back to
  14.0% (2028-2030), breaking the monotonic ratchet every other year follows.
  Fixed to continue the same +1.5pp/year projection (17.0/18.5/20.0%), clearly
  labeled as the team's own projection, not legislated fact, since no Real
  Decreto exists yet for those years. The `Mandato_Biodiesel_Blend_Pct`
  feature was removed entirely: it was attributed to "Decreto 61/2023," which
  does not exist in the BOE -- the only real decree numbered 61 (RD 61/2006)
  governs an unrelated *maximum* blend-compatibility wall, not a rising
  minimum mandate. Every other decree citation in that file (RD 1085/2015, RD
  205/2021, RD 376/2022, RD 5/2026) was independently verified against BOE and
  is accurate (two citation dates were off by one day and have been fixed).
  Feature tables are now 35 columns (was 36); `ML_FEATS` lost one entry
  (`Mandato_Energia_Pct` is now the only mandate feature).
- **Formal residual diagnostics.** `09_evaluation.ipynb` promised an ACF
  check in its own markdown but never ran one. Added a Ljung-Box test plus
  ACF/PACF plots on each target's selected-model test residuals
  (`data/outputs/ljung_box_residual_diagnostics.csv`,
  `reports/figures/09b_residual_acf_pacf.png`). Result: Cataluña and
  Andalucía (both SARIMA-selected) show statistically significant residual
  autocorrelation at the 5% level -- a real, previously undetected signal that
  those two fits are leaving structure on the table. Caveat: only 12 test
  points per target, so treat this as a coarse screen.
- **Price-feature ablation re-scored without test-set peeking.**
  `06_price_features.ipynb` and `08_modeling_with_prices.ipynb` decided
  whether to keep price features using full-window correlation / 2025 test
  MAPE -- a leakage risk, since the test set then influences a feature-set
  decision. Both now use train-only (2023-2024) walk-forward CV as the actual
  decision criterion. Result: price features do **not** clearly help (1/5
  targets for Random Forest, 0/5 for XGBoost) -- the original full-window
  correlation overstated their value. Doesn't change the production model set
  (none of the 5 selected models use price features).
- **Calibrated SARIMA prediction intervals.** The forecast chart used only a
  heuristic MAPE/RMSE-scaled visual band, explicitly not a statistical
  interval. SARIMA-selected targets (Cataluña, Andalucía) now get a real
  calibrated prediction interval from the fit's own forecast-error variance
  (`data/outputs/forecast_24m_sarima_confidence_intervals.csv`,
  `predict_sarima_with_ci` in `scripts/05_modeling_with_cnmc.py`). The
  textbook-default 95% level was tried first and is dramatically wider than
  the old heuristic band by month 24 -- an honest finding, not a bug, and
  still on the record (Cataluña: a ~3,400 Tm point forecast against a
  ~232,000 Tm 95% upper bound by month 24) -- but it explodes asymmetrically
  enough after back-transforming out of log1p space to make the chart
  unreadable. The shipped chart/export now use 50%
  (`SARIMA_CHART_CI_ALPHA`) instead: the same calibrated method, just a
  less conservative, legible level, not a smaller estimate of the true
  uncertainty. Logistic/Gompertz targets keep the heuristic band, labeled
  "illustrative, not calibrated."
- **Sensitivity analysis for the macro/mandate assumptions.** The 24-month
  forecast previously held macro and mandate inputs at one fixed scenario
  with no alternative. Added `build_scenario_sensitivity()`, which re-runs the
  feature-aware ML candidates (Ridge, Random Forest, XGBoost) under a
  Macro_Downturn shock and a Mandate_Delayed scenario
  (`data/outputs/scenario_sensitivity.csv`). Genuine finding: Random Forest
  and XGBoost are *structurally blind* to the mandate-delay scenario, because
  `Mandato_Energia_Pct` only ranges 10.5-11.5 in training data and both the
  legislated and delayed forecast-period values sit beyond every tree split
  threshold the model learned -- a textbook tree-extrapolation limitation, not
  a bug (verified by overriding to an absurd value and confirming the
  prediction did not move). None of the 5 currently-selected production
  models use macro/mandate features at all, so the production forecast itself
  remains scenario-invariant regardless.

## Audit Fixes (2026-06-25, second pass)

A separate, independent audit pass found that the SARIMA order grid's
full-history degeneracy check -- added in the fixes above to catch a
literal flat-line forecast -- was applied as a filter across all 15
candidate orders, using each candidate's fit on the full 2023-2025 history
(including 2025) to decide which orders were even eligible to win. That
contradicts this project's own hard rule that no 2025 data is ever used in
model selection. Fixed: SARIMA order ranking is now training-only with zero
exceptions, and the full-history check runs exactly once, on the single
training-only winner, as a disclosed post-hoc safety veto rather than a
selection criterion (see the Model Selection section above and
`scripts/05_modeling_with_cnmc.py`'s `SARIMA_SAFETY_OVERRIDES`). Re-running
the full pipeline end to end after this fix produced byte-identical
forecasts, metrics, and selected models for all 5 targets -- the fix changes
only how the methodology is structured and disclosed, not any result.
Cataluña is the one target whose training-only winner fails the safety
check; it now uses a recorded, reviewed override to the same order it was
already shipping, with the reasoning written into
`data/outputs/sarima_safety_check.csv` instead of being invisible.

## Audit Fixes (2026-06-25, third pass)

The Cataluña and Andalucía SARIMA forecast charts looked visually broken:
the calibrated 95% prediction interval (added in the first audit-fixes
round above) explodes asymmetrically by month 24 once back-transformed out
of log1p space, e.g. Cataluña's ~3,400 Tm point forecast against a
~232,000 Tm 95% upper bound. That is mathematically honest, not a bug -- a
24-month-ahead interval from a model fit on ~30 monthly points really is
that uncertain -- but it makes the chart unreadable and the number not
practically usable for a planning conversation. Changing the underlying
model to produce a tidier-looking interval was rejected as the fix: that
would reopen the test-set-selection question this project has otherwise
been careful about, for a cosmetic reason. Instead, `scripts/05_modeling_with_cnmc.py`'s
`predict_sarima_with_ci` now defaults its caller to a 50% interval
(`SARIMA_CHART_CI_ALPHA`) for the shipped chart and
`data/outputs/forecast_24m_sarima_confidence_intervals.csv`, instead of the
textbook-default 95%. This is a deliberate display-legibility choice, not
a claim that the true 24-month uncertainty is smaller than the 95% figure
-- that figure remains derivable from the same function
(`predict_sarima_with_ci(result, n_steps, alpha=0.05)`) and is kept on the
record in `memory.md`. `notebooks/13_business_interpretation_and_recommendations.ipynb`'s
own regional plots (Section 1.4) now build the identical calibrated/
heuristic band distinction for all 5 targets, at the same 50% level.

## Repository Layout

```text
repsol-capstone/
├── data/
│   ├── inputs/
│   ├── features/
│   ├── outputs/
│   ├── processed/
│   └── raw/
├── notebooks/
├── reports/
│   └── figures/
├── scripts/
├── requirements.txt
├── environment.yml
└── README.md
```
