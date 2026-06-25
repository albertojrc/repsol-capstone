# Audit Fix Plan

Created: 2026-06-21
Last updated: 2026-06-24

## Phase 1 Scope

Requested scope: fix reproducibility, broken/stale docs, notebook/script
inconsistencies, price-feature regional bug, output lineage, and repo cleanup.

Explicitly out of scope for Phase 1: changing the modeling methodology.

## Completed In Phase 1

- Declared Python 3.11 as the supported runtime via `.python-version`.
- Added `pyproject.toml` with the supported Python range so environment tools do
  not inherit an incompatible Python 3.14 project requirement.
- Added `environment.yml` for Conda-compatible environment creation.
- Added missing direct dependency `scipy` to `requirements.txt`.
- Updated `.gitignore` for `.venv/` and AppleDouble metadata files.
- Removed tracked AppleDouble files and duplicate root-level raw downloads.
- Refreshed `README.md`, `DATA_AUDIT_REPORT.md`, `NOTEBOOKS_AUDIT.md`, and
  `datasets_excluded_from_master.md`.
- Cleared stale notebook outputs and execution counts.
- Added a production note to all notebooks.
- Fixed the target-label mismatch in `notebooks/08_modeling_with_prices.ipynb`.
- Made `scripts/02_master_dataset_builder.py` console output Windows-safe and
  corrected its stale header from 17 to 22 columns.
- Fixed `scripts/05_modeling_with_cnmc.py` so `metricas_comparativa.csv` combines
  current metrics with optional price-ablation metrics instead of duplicating
  `metricas_modelos.csv`.
- Added an explicit NumPy seed in the production modeling script.
- Rebuilt the production artifacts from the script path through feature
  generation and modeling outputs.

## Completed In Phase 2 On `enrico`

- Preserved the Phase 1 cleanup from `main` on the `enrico` branch.
- Replaced the one-step model-selection gate with a recursive multi-step
  walk-forward gate inside the 2023-2024 training period.
- Tested pooled regional ML models in the official script pipeline.
- Kept `Nacional` separate from pooled regional modeling.
- Added a no-regression acceptance gate versus the Phase 1 selected models.
- Accepted Phase 2 changes only for Madrid and Catalonia before the final
  no-pooling delivery policy:
  - Madrid: Gompertz -> Logistic, MAPE 197.1% -> 73.6%.
  - Catalonia: Gompertz -> Pooled Random Forest, MAPE 164.2% -> 46.8%
    as a pooled sensitivity result.
- Rejected Phase 2 proposals for Nacional, Andalusia, and Valencia because they
  did not improve the Phase 1 selected 2025 validation result.
- Added `PHASE2_MODELING_REPORT.md` and `data/outputs/phase2_*.csv` lineage
  files documenting the production decision.

## Completed In Final Audit Cleanup

- Adopted the final no-pooling policy for production selected models.
- Set Catalonia's final production model to SARIMA, the best non-pooled 2025
  validation alternative, while keeping pooled Random Forest as sensitivity
  output.
- Reframed the 2025 period as validation / acceptance rather than a pristine
  final test.
- Updated README and audit reports to align with the script pipeline, final
  model policy, and current output roles.
- Fixed notebook compatibility issues found during the audit:
  - `09_evaluation.ipynb` pandas frequency aliases.
  - `09_evaluation.ipynb` stale ML feature list.
  - preserved the upstream removal of `11_mini_demand_model.ipynb`, which is
    superseded by what is now notebook 11 (renumbered from 12 on 2026-06-25,
    see `memory.md`).
- Cleared notebook outputs and execution counts again after content updates.
- Added `scripts/06_validate_outputs.py` to assert dataset shapes, temporal
  split boundaries, lag causality, no-pooled final selection, and dashboard
  export consistency after rebuilds.
- Added constrained SARIMA grid search in the production modeling script, with a
  2025 no-regression acceptance check against the default SARIMA order.
- Added `sarima_grid_search_results.csv` and `sarima_order_acceptance.csv` output
  lineage, and documented the result in notebooks 10, 10.1, and 13.
- Added an explicit project-memory maintenance rule in `README.md` and
  `memory.md`: major data, model, output, scope, validation, or interpretation
  changes should update `memory.md` in the same work session, pull request, or
  commit.

## Completed In Sacha Branch Refresh (2026-06-24)

The "final no-pooling policy" described above is superseded on branch `sacha`.
The modeling layer was rebuilt around an open seven-model competition per
target (SARIMA, SARIMAX, Logistic, Gompertz, Ridge, Random Forest, XGBoost),
selected only by training-only recursive walk-forward validation -- no
2025-informed acceptance gate remains anywhere in the selection path. Pooled
regional ML and Diesel Share are diagnostics only, never headline-eligible.
See `PHASE2_MODELING_REPORT.md` and `DATA_AUDIT_REPORT.md` for the current
selected-model table and methodology.

This refresh also found and fixed three notebook regressions left by an
earlier "translate to English" pass that had renamed real data-column string
literals inside code (not just prose), breaking notebooks 05, 06, 07, 08, 09,
10, 10.1, and 13 to varying degrees:

- `'Tendencia'` renamed to `'Trend'` in notebooks 05/07/08/09, causing
  `KeyError: 'Trend'` against the real feature tables.
- The raw `Producto` values and `gasolina95`/`gasolina98` slugs renamed to
  English in notebooks 06/08, causing a silent zero-match in notebook 06 and
  `KeyError` in notebook 08.
- Stale `Default_2025_MAPE`/`Grid_Selected_2025_MAPE` column references in
  notebooks 10/10.1/13, left over from the removed 2025-acceptance-gate design.

All affected notebooks were fixed, re-executed end to end, and their figures
regenerated. The shared-filename production outputs that notebooks 05/07/08
overwrite when run (`data/features/*.csv`, several `data/outputs/*.csv`) were
restored to the authoritative script-produced state afterward.

## Completed: SARIMAX Degeneracy Fix (same day)

The Cataluña SARIMAX result referenced below as "still open" was investigated
and fixed. It was not a close call between two valid models: the SARIMAX fit
never converged (`sigma2` collapsed to 5.07e-7), and the same failure was
found on 4 of 5 targets. `scripts/05_modeling_with_cnmc.py` now rejects any
SARIMA/SARIMAX fit that fails to converge or has near-zero residual variance,
at the point of fitting. Cataluña now selects SARIMA (50.1% holdout MAPE, down
from 92.3%); Nacional's selection also changed (SARIMA to Logistic) as a
consistency side effect of applying the same check to plain SARIMA. See
`memory.md` and `PHASE2_MODELING_REPORT.md` for the full investigation.

## Completed: SARIMA Order Selection No Longer Touches 2025 Data (2026-06-25, second pass)

A second, independent audit pass found that the full-history degeneracy
check added in the SARIMAX-degeneracy fix above had itself been implemented
as a filter across all 15 candidate SARIMA orders, using each candidate's
fit on the full 2023-2025 history (including 2025) to decide eligibility
before ranking by training-only MAPE -- a genuine violation of this
project's "never select using test-set performance" rule, not just a close
call. Concretely, Cataluña's best training-only order, (0,1,1)(1,0,0,12) at
63.66% MAPE, was excluded solely because its full-history refit ships a
near-flat forecast; the next-best training-only order, (0,1,2)(1,0,0,12) at
66.90%, was used instead. The other 4 targets were unaffected in practice
(their best training-only order already passed the full-history check too).

Fixed: `tune_sarima_orders()` in `scripts/05_modeling_with_cnmc.py` now
ranks every candidate purely by training-only `WalkForward_MAPE`. The full
2023-2025 history is used exactly once, on the single training-only winner,
via a new post-hoc safety check (`sarima_shippability_reason()`) that can
veto but never rank or filter the grid. On failure it requires an explicit,
reviewed entry in the new `SARIMA_SAFETY_OVERRIDES` dict rather than
auto-substituting another candidate or silently falling back to the plain
default order (verified worse: 87.4% training MAPE for Cataluña's default
order vs. 66.9% shipped). One override is recorded, for Cataluña, pointing
at the same order already in production. `scripts/06_validate_outputs.py`
now also fails if any target's safety check fails without a matching
recorded override.

Re-ran the full `05 -> 06 -> 07` pipeline and diffed every output file
against the pre-fix state: every selected model, SARIMA order, 2025 holdout
metric, forecast value, and figure is byte-identical. Only
`sarima_grid_search_results.csv` and `sarima_order_acceptance.csv` changed
shape (disclosure columns), and a new `data/outputs/sarima_safety_check.csv`
audit trail was added. Updated `README.md`, `memory.md`,
`PHASE2_MODELING_REPORT.md`, `DATA_AUDIT_REPORT.md`, and notebooks 10, 10.1,
and 13 to match. See `memory.md`'s "2026-06-25 SARIMA Order Selection No
Longer Touches 2025 Data" entry for the full investigation.

## Completed: Target Lineage Documented as Reproducible via CNMC (2026-06-25)

An audit found that the target variable's raw-to-processed derivation
looked unreproducible: no notebook or script reads the three
`ESTADISTICAS-BIOS CERT DEFINITIVAS *.xlsx` files in `data/`, and no
2025-dated file of that type exists at all. Resolved without writing new
extraction code: `scripts/03_clean_cnmc_petroleum.py` and
`scripts/02_master_dataset_builder.py` already assert, on every run, that
CNMC's `CNMC_Biodiesel_Tm` (built entirely from the raw, fully-coded
`data/raw/consumos_mensuales_petroleo/ds_*.csv` files) reconciles exactly
against `consumo_biodiesel_ccaa.csv`'s `Consumo_Tm` for the full 2023-2025
window. CNMC is therefore documented as the canonical, reproducible
lineage; the BIOS CERT Excel files are now described as historical/
supplementary reference material, not a reproducibility requirement.
Deliberately did not attempt to wire up the Excel files themselves (30+
sheets, no confirmed CCAA-level monthly breakdown, no need once CNMC is
recognized as sufficient). Updated `memory.md`, `README.md`, and
`DATA_AUDIT_REPORT.md`.

## Completed: Notebooks 07/08 No Longer Share Output Filenames With scripts/05 (2026-06-25)

Notebooks 07 and 08 previously wrote to several of the same `data/outputs/*.csv`
filenames that `scripts/05_modeling_with_cnmc.py` owns, so running either
notebook would silently overwrite production outputs with an older,
narrower candidate set. Fixed by redirecting every colliding `to_csv`/figure
path in both notebooks to a `legacy_notebook07_`/`legacy_notebook08_`-prefixed
filename, so they can never again clobber the production script's outputs
no matter what order anything is run in. See `NOTEBOOKS_AUDIT.md` for the
updated per-notebook status.

## Completed: SARIMA Chart/Export Confidence Level Changed From 95% to 50% (2026-06-25)

The calibrated SARIMA prediction interval (added above) made the Cataluña
and Andalucía forecast charts look visually broken: at the textbook-default
95% level, the interval explodes asymmetrically by month 24 once
back-transformed out of log1p space (Cataluña: a ~3,400 Tm point forecast
against a ~232,000 Tm 95% upper bound). Mathematically honest, not a bug,
but unusable for a planning conversation. Rejected re-fitting/re-selecting
SARIMA to produce a tidier interval, since that would reopen the
test-set-selection question this project has otherwise been careful about,
for a cosmetic reason. Fixed instead by changing the *display* level:
`scripts/05_modeling_with_cnmc.py`'s `predict_sarima_with_ci` is now called
with `SARIMA_CHART_CI_ALPHA = 0.5` for the shipped chart and
`data/outputs/forecast_24m_sarima_confidence_intervals.csv`; the chart
legend is computed from this constant rather than hardcoded. The function
still defaults to `alpha=0.05` and the true 95% figure remains on the
record in `memory.md`. `notebooks/12_business_interpretation_and_recommendations.ipynb`'s
own regional plots were updated to match. Re-ran `05 -> 06 -> 07` and
re-executed notebook 12; `scripts/06_validate_outputs.py`'s CI checks are
alpha-agnostic and still pass.

## Completed: Fixed Independent Audit Findings M1 and M2 (2026-06-25)

M1: `notebooks/02_data_cleaning.ipynb` and `notebooks/03_external_data.ipynb`
claimed output paths under `data/processed/` that don't match what the code
actually saves (`data/inputs/`). Fixed every markdown reference in both
notebooks to the real `to_csv` paths; verified row counts against the
current files rather than assuming the old numbers still held.

M2: ~25 `except Exception` blocks around model-fitting calls in
`scripts/05_modeling_with_cnmc.py` only persisted exceptions containing the
literal string "degenerate"; everything else printed once and vanished.
Added `log_model_exception()` and a new `data/outputs/model_fit_exceptions.csv`
(aggregated by Target/Model/Stage/Exception with a Count) covering all 22
except-blocks that weren't already self-logging via some other persisted
column. Investigated what it found immediately: 226 occurrences, only 30
non-degenerate across 2 explainable causes (an intentional SARIMAX
not-enough-rows guard, and a statsmodels-internal edge case for
heavily-differenced SARIMA orders on too few training rows) -- neither
affects any winning candidate. Re-ran `05 -> 06`: every existing production
output is byte-identical; the validator got a schema-only check for the new
file. See `memory.md`'s "Audit Fixes M1/M2" entry for the full detail.

## Completed: Notebooks 12 and 13 Renumbered to 11 and 12 (2026-06-25)

`11_mini_demand_model.ipynb` was removed upstream long ago, leaving a gap
in the notebook sequence (10, [gap], 12, 13). Renumbered
`12_mini_trend_regulation_model.ipynb` -> `11_mini_trend_regulation_model.ipynb`
and `13_business_interpretation_and_recommendations.ipynb` ->
`12_business_interpretation_and_recommendations.ipynb` via `git mv` to close
it, so the sequence is now 10, 11, 12 with no gap. Also renamed that
notebook's own `13_business_*.png` figure outputs to `12_business_*.png` to
match, and fixed every internal self-reference (titles, the cross-reference
each notebook makes to the other, the figure-filename-construction code)
plus every external cross-reference in `README.md`, `NOTEBOOKS_AUDIT.md`,
`scripts/07_selected_model_drivers.py`, and `notebooks/05_feature_engineering.ipynb`.
Re-executed both renamed notebooks end to end and re-ran
`scripts/06_validate_outputs.py` to confirm nothing broke. See `memory.md`'s
dated entry for the full file-by-file accounting, including which
historical mentions of the old numbers were deliberately left alone.

## Still Open After Final Cleanup

- Treat the forecasts as directional planning scenarios because all selected
  target-level R2 values remain negative.
- Andalucía and Cataluña's forecasts are still fairly flat in absolute terms
  (24-month ranges of 157.9 Tm and 64.6 Tm respectively). They pass the
  pipeline's degeneracy checks, but this reflects a genuine small-sample
  limitation (not enough clean seasonal history for a strongly seasonal
  SARIMA order without overfitting), not something more pipeline engineering
  resolves.
- Consider a stronger backtesting design if more historical data becomes
  available.
- Keep HVO / renewable diesel outside the target unless new usable regional data
  becomes available.
- Notebooks 07 and 08 still implement an older, smaller candidate set
  (pre-SARIMAX, pre-CNMC features) than the production script. They are
  fixed and runnable again, but reflect a previous modeling generation --
  consider retiring them or refactoring them to mirror `scripts/05` if they
  are kept as more than a historical reference.
