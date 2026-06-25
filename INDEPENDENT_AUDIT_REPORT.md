# Independent Audit Report

Date: 2026-06-25
Branch audited: `sacha`
Scope: full repository — `scripts/02`-`06`, `notebooks/01`-`13`, all root-level
markdown documentation, `memory.md`.

This audit is independent of, and does not assume the accuracy of, the project's
own prior self-audits (`AUDIT_FIX_PLAN.md`, `DATA_AUDIT_REPORT.md`,
`NOTEBOOKS_AUDIT.md`, `PHASE2_MODELING_REPORT.md`). Every finding below was
verified directly against current code, current data files, or current
notebook source — not against what those documents claim. Several of this
project's own prior claims did not survive that verification; those are
flagged explicitly below.

Findings are ordered **Critical > Important > Info > Low**, per the request.
A "Confirmed Passes" section at the end lists things this project does well,
because a credible audit has to show both.

## Executive summary

| Severity | Count |
|---|---:|
| Critical | 5 |
| Important | 12 |
| Info | 12 |
| Low | 6 |

The core forecasting pipeline (`scripts/02`-`06`) is methodologically sound on
the single dimension that matters most: **the train/test boundary is real**.
Model selection is provably finalized before the 2025 holdout is even loaded
in `main()`, scalers are always fit on training folds only, and recursive
forecasts never peek at true future values. That is the right foundation.

The two genuine, severe problems are elsewhere: (1) the business-interpretation
notebook (13) does not disclose the project's own most damaging finding
(every selected model has negative R², i.e. loses to a naive mean) anywhere in
its prose, and omits two other findings the team already produced
(scenario-blindness of the selected models, residual autocorrelation); and
(2) notebooks and the production script silently fight over the same output
filenames at two separate pipeline stages, with no provenance guard, which is
a live corruption risk, not a hypothetical one.

---

## Critical

### C1. The business-interpretation notebook never explains the project's central negative finding

`notebooks/13_business_interpretation_and_recommendations.ipynb` is the one
deliverable whose job is translating model output into business language. It
fails the audit's cherry-picking check in a specific, checkable way:

- The string "R2" / "R²" never appears in any markdown prose cell — only
  inside a results table and inside chart-title f-strings. No sentence
  anywhere explains what a negative R² means (the model is outperformed by
  predicting the historical mean), even though every one of the 5 selected
  models has negative R² (range -1.041 to -8.273) and the average 2025
  holdout MAPE is 49.4%. Section 3 (cell `db19318a`) comes closest, but only
  ever names MAPE ("50.1% MAPE... second-weakest"), never R² or its sign.
- This is not fabrication — every number shown is traceable to a real output
  file — but the single most important sentence a non-technical reader needs
  ("every selected model is currently worse than guessing the average") is
  never written in the notebook a Repsol stakeholder is meant to read.

### C2. Two of the team's own documented findings are missing from the same notebook

- `data/outputs/scenario_sensitivity.csv` (the Macro_Downturn / Mandate_Delayed
  sensitivity analysis) is never loaded or mentioned in notebook 13, even
  though Section 6 recommends "scenario planning." Worse: every row in that
  CSV has `Selected_Model_Uses_Scenario_Inputs = False` — **none of the 5
  actually-selected production models (Logistic×2, SARIMA×2, Gompertz) were
  ever scenario-tested.** The notebook recommends scenario thinking while
  citing zero evidence that the selected models respond to scenarios at all.
- `data/outputs/ljung_box_residual_diagnostics.csv` shows statistically
  significant residual autocorrelation for Cataluña (p=0.043) and Andalucía
  (p=0.032) — both SARIMA-selected, both leaving real structure unexplained.
  Notebook 13 never cites this. Adjacent text instead says Cataluña's SARIMA
  "actually converges," which is true but invites a reader to conflate
  "converges" with "fits adequately" — exactly what the Ljung-Box result
  contradicts.

### C3. Notebooks and the production script silently overwrite each other's outputs at two pipeline stages, with no provenance guard

This is a live hazard, demonstrated against the actual repository state, not a
hypothetical one:

- **Inputs/features stage:** `notebooks/02_data_cleaning.ipynb` (cell-14),
  `notebooks/03_external_data.ipynb` (cell-20), `notebooks/04_master_dataset.ipynb`
  (cell-18), and `notebooks/05_feature_engineering.ipynb` (cell-20) all write
  directly to the exact paths the production scripts own
  (`data/inputs/consumo_biodiesel_ccaa.csv`, `macro_indicadores_ine.csv`,
  `master_dataset.csv`, `data/features/features_*.csv`) — with older,
  incompatible schemas (notebook 04 builds a 19-column master table vs. the
  script's 22; notebook 05 builds 21 features vs. the script's 35). Only
  notebook 05's risk is documented anywhere (`NOTEBOOKS_AUDIT.md`); notebooks
  02, 03, and 04 carry the identical risk, undocumented. Production files are
  *currently* in the correct script-built state (verified directly), so
  nothing is broken today — but nothing prevents a normal "let me re-run the
  EDA notebook" action from corrupting it.
- **Model-output stage:** `notebooks/07_modeling.ipynb` writes to
  `metricas_models.csv`, `model_selection_walkforward.csv`,
  `metricas_final_selected.csv`, `predicciones_test_2025.csv`, and
  `forecast_24m_sarima_rf_xgb.csv` — all five paths `scripts/05_modeling_with_cnmc.py`
  also owns, with an older 6-candidate universe (no SARIMAX, no CNMC
  features). Notebook 08 additionally collides on `metricas_comparativa.csv`.
  `notebooks/09_evaluation.ipynb` reads exactly these five files with **zero**
  staleness or model-set guard — contrast with notebooks 10/10.1, which do
  check `HEADLINE_FINAL_MODELS` and trigger an automatic rebuild if the files
  look stale. Notebook 09 has no equivalent protection, so it would silently
  display wrong numbers with no error if run after notebook 07.

### C4. Mojibake encoding artifacts are permanently baked into saved, slide-ready chart images

`notebooks/13_business_interpretation_and_recommendations.ipynb:357`:

```python
ax.set_title(f'{target} ? selected model: {model} | 2025 MAPE: {metric.MAPE:.1f}% | R2: {metric.R2:.3f}', fontweight='bold')
```

The literal `?` character (an encoding artifact from an earlier translation
pass) renders directly into all five saved PNGs in `reports/figures/`
(`13_business_{andalucia,cataluna,madrid,valencia,national}_train_validation_forecast.png`),
which the notebook's own text says are intended for reuse "in slides or the
final report." The same artifact also appears in the notebook's own H2 header
(`## 0. Setup ? Load Validated Production Outputs`, line 25). This is the
exact recurring mojibake bug a prior audit round fixed elsewhere in this repo
(`Catalu?a`/`Andaluc?a`, fixed in notebooks 10/10.1/13's prose per
`NOTEBOOKS_AUDIT.md`) — but it has resurfaced here, in the most visible
output of the most stakeholder-facing notebook in the project.

### C5. The mandate-feature future window has a documented edge case that is silently wrong if extended past 2030

Not yet triggered, but worth flagging as Critical because of what it would
silently do: `mandate_values_for_date()` in `scripts/05_modeling_with_cnmc.py`
(lines 214-219) raises a clear `ValueError` if asked for a year outside
`mandato_biocarburantes.csv`'s 2016-2030 range — this is good, fail-loud
behavior, *today*. But the same file's schedule for 2027-2030 is explicitly
the team's own linear-projection guess (+1.5pp/year), not law, per the
README's own disclosure. Nothing in the code or in `mandato_biocarburantes.csv`
prevents a future contributor from silently extending the CSV with another
naive +1.5pp/year row for 2031 and presenting it with the same "Status"/
"Fuente" formatting as the genuinely legislated 2016-2026 rows, with no
structural distinction between "law" and "guess" enforced anywhere except a
text column. Given this project's own history of exactly this kind of
data-integrity slip (the 2026-06-25 fix to this same file, per the README),
this is rated Critical on recurrence risk, not on current impact.

---

## Important

### I1. SARIMA order-selection touches 2025 (holdout) data, contradicting the project's own documentation

In `tune_sarima_orders()` (`scripts/05_modeling_with_cnmc.py:732-825`), each
candidate SARIMA order's eligibility to compete is gated by **two** stability
checks: one fit on `df_train` only (2023-2024), and a second,
`full_history_reason`, fit on `df_all` — which is `features_modelo_completo.csv`,
**2023-2025, i.e. it includes the holdout** (lines 760-766). Orders degenerate
under either check are excluded before the surviving set is ranked by
training-only `WalkForward_MAPE` (lines 793-798):

```python
stable = finite[
    ~finite["Training_Origin_24m_Degenerate"] & ~finite["FullHistory_Origin_24m_Degenerate"]
].copy()
if not stable.empty:
    finite = stable
```

This means *which orders are allowed to compete* depends partly on whether
fitting through 2025 produces a stable 24-month forecast — i.e., 2025 data
does influence the selection pathway, even though the final ranking metric
itself remains training-only. This directly contradicts explicit claims in
`DATA_AUDIT_REPORT.md` ("No 2025 data is used in this decision") and
`PHASE2_MODELING_REPORT.md` ("There is no 2025 SARIMA no-regression gate").
**Severity context:** this does not inflate any reported accuracy metric, and
it only affects which (p,d,q)(P,D,Q) order is used *within* the SARIMA family,
not which model family wins for any target — the family-selection walk-forward
(`run_walk_forward`) has no equivalent full-history check. Still, it is a
real, citable methodology/documentation mismatch in the section of this
project that most needs to be airtight.

### I2-I4. Three independent, demonstrable bugs in notebook 09, none caught by the project's own "fixed and re-verified" claim

- **I2 — Uncalibrated band, mislabeled as fixed.** `notebooks/09_evaluation.ipynb`
  cell-14 still contains the original flat heuristic band:
  ```python
  ax.fill_between(fdf['Fecha'], fdf['Forecast']*0.8, fdf['Forecast']*1.2,
                  color=color, alpha=0.12, label='±20% band')
  ```
  The real calibrated-interval fix (`predict_sarima_with_ci`, and the
  "illustrative, not calibrated" disclaimer) that the README credits as a
  completed 2026-06-25 fix landed only in `scripts/05_modeling_with_cnmc.py`
  (verified: grep for "calibrated"/"illustrative" across notebook 09 returns
  zero matches). A reviewer reading notebook 09 in isolation sees an
  unlabeled, arbitrary ±20% band with no caveat that it is not a real
  confidence interval.
- **I3 — Missing dict key will crash the moment SARIMAX wins anything.**
  `MODEL_COLORS` (notebook 09, setup cell) has keys for SARIMA, Random Forest,
  XGBoost, Logistic, Gompertz, and Ridge — **no SARIMAX**. Two call sites index
  it directly and unguarded (`MODEL_COLORS[sel]` in the annotate/arrowprops
  calls in cell-14). SARIMAX is currently degenerate-excluded for 4 of 5
  targets, but that is a function of *today's* data, not a structural
  guarantee — the moment a future data refresh produces a converged,
  competitive SARIMAX fit for any target, this notebook throws `KeyError`.
  Separately, the `for mdl, color in MODEL_COLORS.items()` plotting loop
  means a SARIMAX forecast curve is silently never drawn even when present in
  the underlying CSV, regardless of the crash.
- **I4 — No independently checkable evidence that 07/08/09/10/10.1 currently
  execute without error.** All code cells in these five notebooks have
  `"execution_count": null` and empty `"outputs": []` in the committed
  `.ipynb` JSON. On its own this is **not** proof the notebooks were never
  run — this repo's own stated convention (and `AUDIT_FIX_PLAN.md`'s own log)
  is to clear outputs before every commit, so a clean diff is the *expected*
  state either way. The fair conclusion is narrower but still real: there is
  no artifact (CI log, saved output, anything) that lets a reviewer verify
  the repeated "re-executed end to end, runs clean" claims in
  `NOTEBOOKS_AUDIT.md` without re-running the notebooks themselves — and I2/I3
  above are concrete, source-level proof that at least one of those claims
  (notebook 09 "fixed and re-verified") is not fully accurate.

### I5. The causal-lag validation gate has a blind spot, in both places it exists

`validate_features()` in `scripts/04_build_features.py` (lines 155-174) *and*
`validate_feature_tables()` in `scripts/06_validate_outputs.py` (lines
153-184) both independently re-derive and check only `Lag_1/2/3/12` and the
two `DIESEL_MARKET_COLS` `_lag1` columns for causal correctness. Neither ever
re-checks `Roll_mean_3`, `Roll_mean_6`, `Roll_std_3`, or the four
`MACRO_COLS` `_lag1` columns (`IPI_original_lag1`, `IPI_ajustado_lag1`,
`IPC_var_anual_lag1`, `Tasa_paro_lag1`). I independently hand-verified these
*are* currently computed correctly (shift-then-roll, per-target group), but a
future refactor that broke that pattern in one of these eight untested
columns would pass both validation gates cleanly — there is no regression
protection for the majority of the engineered feature set.

### I6. The mini regulation model never actually reads the regulation schedule it cites

`notebooks/12_mini_trend_regulation_model.ipynb`'s title and three separate
markdown passages assert specific mandate figures ("11.5% (2025) → 14%
(2026, RD 5/2026)"), but the notebook's only data load is
`pd.read_csv(INP / 'master_dataset.csv')` — `mandato_biocarburantes.csv` is
never opened anywhere in the notebook. The cited figures are currently
correct (independently verified against the CSV), but there is no mechanical
link, so a future correction to the mandate schedule (this file was already
corrected once, on 2026-06-25) could silently leave this notebook's prose
stale with nothing to flag it. Separately, the notebook's RED III figures
("29% renewable / 14.5% GHG-intensity by 2030") appear nowhere else in the
repository and have no citation — unverifiable from within the repo, which
matters for a dual academic/Repsol audience.

### I7. Growth-curve (Logistic/Gompertz) bounds are wide enough to be an extrapolation risk, and selection has no out-of-sample penalty

Both `scripts/05_modeling_with_cnmc.py:362-381` and the equivalent logic in
notebook 12 fit Logistic/Gompertz curves with bounds that let the asymptote
`L` range up to **60× the observed historical maximum** and the inflection
point land up to 5 years outside the observed window, on only ~24-36 monthly
points with 3 free parameters, selected by walk-forward MAPE with no AIC/BIC
parameter penalty. I checked the actual current forecasts this produces
(Nacional: 23,286 → 28,027 Tm; Valencia: 1,212 → 1,803 Tm over 24 months) —
neither shows runaway behavior today, so this has not yet caused a visible
problem. But the bounds are loose enough that a future data update could
produce a poorly-identified, very different `L` with an equally good-looking
in-sample fit, and nothing in the pipeline would flag it as different from
today's reasonable result.

### I8. `memory.md`'s own "Current Status" section is stale and contradicts the rest of the file

`memory.md` Section 9 ("Current Status", around line 1083) and Section 7
still show the pre-degeneracy-fix model table (e.g., Nacional = SARIMA
29.0%/-0.009, Cataluña = SARIMAX 92.3%/-19.827), which contradicts the file's
own top-of-file entry and every other current document (README.md,
DATA_AUDIT_REPORT.md, PHASE2_MODELING_REPORT.md — all agree on Nacional =
Logistic 36.7%, Cataluña = SARIMA 50.1%/-7.182), with no "superseded" pointer
added. Since `memory.md` is the file this project's own README explicitly
designates as the long-term source of truth, a reader who jumps to its
"Current Status" section (the obvious place to look) gets the wrong answer
for 2 of 5 targets.

### I9. `AUDIT_FIX_PLAN.md` is missing its own most recent entry

The file's header still reads "Last updated: 2026-06-24." It contains zero
reference to the 2026-06-25 six-item fix round (mandate data integrity,
residual diagnostics, calibrated intervals, price-feature re-scoring,
scenario sensitivity) that is documented in README.md, memory.md,
DATA_AUDIT_REPORT.md, and PHASE2_MODELING_REPORT.md. This is the one file
whose entire purpose is to be that changelog, and it stops one round short.

### I10. Business-interpretation language is consistently softer than the team's own stated reasoning

`notebooks/13`, cell `a17350c1`: "Treat regional forecasts as directional
signals... especially where validation metrics are weak." This never states
the actual, more specific reason the team itself documented elsewhere ("not
precision demand commitments... because of the negative R2 values" —
README.md). No interpretive text anywhere in notebook 13 connects the
visually obvious 2025 prediction-vs-actual divergence in the regional charts
(e.g., Cataluña's SARIMA line declining toward ~800 Tm while actual 2025
demand spikes to ~3,800 Tm) to the R²/MAPE numbers displayed in the same
chart's title.

### I11. Notebook 02 has an unrelated, undocumented bug

`notebooks/02_data_cleaning.ipynb` cell-6 references a column named
`'Province'`, which does not exist in the current production file (the real
column is `'Provincia'`, confirmed against `data/inputs/consumo_biodiesel_provincial.csv`'s
header). This notebook would crash if re-run today. It is not mentioned in
`NOTEBOOKS_AUDIT.md`, whose own bug-fix narrative checked notebooks 05-09 for
literal-renaming issues but not 02-04 for this kind of independent break.
(Side effect: this bug currently blocks the notebook before it would reach
C3's dangerous overwrite cell for the provincial-file path — but it would
still re-open that exposure the moment someone "fixes" the column name back.)

### I12. Comparison-table metric set is inconsistent within notebook 08's own output

`notebooks/08_modeling_with_prices.ipynb` cell-7 builds price-augmented model
rows with only `{MAE, RMSE, MAPE}` — no R² key — so after concatenation with
the base metrics (which do have R²), the price-augmented rows show `NaN` for
R² in the same `metricas_comparativa.csv` table that's meant to support
apples-to-apples comparison.

---

## Info

1. National-level fuel-price columns (`PVP_*`, `PAI_*` for `CCAA == "ESPAÑA"`)
   are a simple unweighted mean across the 19 regional rows, not a
   demand/population-weighted average. This is already disclosed in
   `DATA_AUDIT_REPORT.md`, so it's a methodological simplification to keep in
   mind, not a hidden issue.
2. `tune_sarima_orders()` (`scripts/05_modeling_with_cnmc.py:732-825`) runs
   roughly 5 targets × 15 grid orders × ~13 fits per order (≈975 SARIMA
   fits) with zero progress output anywhere in that code path — the single
   longest-running stage of the pipeline is also its quietest.
3. Dead code: `strip_accents()` in `scripts/03_clean_cnmc_petroleum.py:51-54`
   is defined but never called anywhere in the repo.
4. Unused import: `numpy` is imported in `scripts/02_master_dataset_builder.py:25`
   but never referenced (`np.` has zero matches in that file).
5. A defensive mojibake fallback (`"Año" if "Año" in mandates.columns else "AÃ±o"`)
   is duplicated identically in `scripts/04_build_features.py:68` and
   `scripts/05_modeling_with_cnmc.py:199`. The current `mandato_biocarburantes.csv`
   header is clean, so this branch is currently unreachable — a harmless
   fossil of a past encoding bug, but duplicated rather than centralized.
6. `NOTEBOOKS_AUDIT.md:73` still cites a "36-column" feature table; the
   2026-06-25 mandate fix dropped this to 35 columns (removed
   `Mandato_Biodiesel_Blend_Pct`). This doc was refreshed one day before that
   fix landed and was never touched again.
7. Near-total absence of function-level docstrings across all 5 production
   scripts (e.g. `scripts/05_modeling_with_cnmc.py` has 49 `def` blocks, only
   3 with docstrings). No convention requires this in this repo, so it's not
   a violation — just a maintainability note for non-trivial functions like
   `build_sarimax_future_exog` and `recursive_forecast_pooled_ml`.
8. Em-dash usage is inconsistent across the repo: `memory.md` (36 occurrences)
   and most notebooks use them freely; every other root-level `.md` file
   (README, DATA_AUDIT_REPORT, PHASE2_MODELING_REPORT, AUDIT_FIX_PLAN,
   NOTEBOOKS_AUDIT, datasets_excluded_from_master) has zero. No style
   convention is stated anywhere in this repo, so this is informational, not
   a violation of a stated rule.
9. `scripts/__pycache__/` contains `.pyc` files compiled under three
   different Python versions (3.11, 3.13, 3.14), evidence that development
   happened across inconsistent local interpreters despite the README's "use
   3.11 only" guidance. Correctly gitignored (not tracked), and the
   committed `.venv`/`requirements.txt` are consistently pinned to 3.11 — so
   this is historical residue, not a live problem.
10. `data/outputs/phase2_model_acceptance.csv` does not contain most of the
    columns notebooks 10/10.1 reference by name (`Training_WalkForward_Proposed_Model`,
    `Selected_Model_2025_Validation_MAPE`, etc.) — only `Target`,
    `Selected_Model`, `Final_Selection_Source`, and `Decision` actually exist.
    The notebooks defensively filter to existing columns, so this degrades
    the printed table's richness rather than crashing or showing wrong data.
11. Notebook 12's cell outputs are fully cleared, so its claims (which curve
    won per series, the printed scenario table) can't be checked by reading
    the `.ipynb` alone — consistent with this repo's "clear outputs before
    commit" convention, but worth noting since other notebooks' audit
    entries include an explicit "re-executed, confirmed clean" statement and
    notebook 12's audit history does not.
12. Notebook 13's Section 6 recommendations are mostly generic ("monitor
    actuals," "add Repsol sales data") rather than tied to a specific
    region/number/timeframe. This is honestly disclosed as a scope limit (no
    Repsol-internal data available), so it is a content-richness gap rather
    than a misrepresentation.

---

## Low

1. Pipeline execution order (`03` before `02`) is documented consistently
   everywhere it appears, and `scripts/02_master_dataset_builder.py` raises
   an explicit `FileNotFoundError` telling the user to run `03` first if the
   order is wrong — confirmed no ambiguity or silent failure mode here.
2. No orphan scripts or notebooks: every file under `scripts/` and every
   numbered notebook is referenced in `NOTEBOOKS_AUDIT.md` and/or `README.md`
   (notebook 11 was deliberately removed and that removal is documented).
3. Library versions are mutually consistent across `requirements.txt`,
   `environment.yml`, and `pyproject.toml` (all agree on Python 3.11; the
   committed `.venv` matches the pins exactly).
4. No generic placeholder variable names (`df2`, `tmp`, `final_final`, etc.)
   found anywhere in `scripts/`.
5. No live TODO/FIXME/HACK markers anywhere in the repository.
6. No live mojibake remains in any root-level documentation file — the only
   `?`-for-`ñ`/`í` references found in `.md` files are historical mentions
   describing an already-fixed bug, not live instances.

---

## Confirmed passes

A credible audit has to show what's done right, not just what's wrong:

- **The train/test boundary is real and provably enforced by code order, not
  just by convention.** In `scripts/05_modeling_with_cnmc.py:main()`, model
  selection (`tune_sarima_orders`, `run_walk_forward`, `build_model_acceptance`)
  completes and is fixed *before* `df_test` (2025) is even read from disk
  (line 1629 comes after line 1627). This is the single most important
  leakage check in the whole project, and it passes by construction.
- Every `StandardScaler` in the modeling script is fit only on the current
  training fold (`train_ml`, `train_sarimax`, `train_share_model`), never on
  combined train+test data, in every call site checked.
- Recursive multi-step forecasts (`recursive_forecast_ml`,
  `predict_sarimax`/`build_sarimax_future_exog`) correctly feed back only
  predicted/simulated values, never true future actuals. SARIMAX's future
  exogenous inputs are explicitly simulated (seasonal-naive diesel price,
  macro held flat) rather than assumed known — and this is done
  *consistently* between the 2025 holdout evaluation and the real 2026-2027
  production forecast, which is the correct, non-obvious design choice and
  avoids a classic SARIMAX leakage trap.
- Lag and rolling-window features (`scripts/04_build_features.py`) are
  genuinely causal: `.shift()` always precedes `.rolling()`, always
  per-`Target` group. Verified two ways — by reading the code and by hand-
  tracing real values in `features_modelo_completo.csv` (e.g. Nacional
  2023-04's `GasoleoA_Tm_roll3_lag1` exactly equals the mean of Jan-Mar 2023).
- National-level aggregates genuinely reconcile to the sum of CCAA rows
  (verified against raw numbers, not just the docstring's claim).
- All merge keys are explicit and provably unique before any join — row
  counts can't silently explode or drop rows; no leftover `_x`/`_y` columns
  anywhere.
- A hard `ValueError` guard (`scripts/05_modeling_with_cnmc.py:1642-1649`)
  prevents a model already flagged as a degenerate fit from ever becoming
  the selected production model.
- Metric formulas (MAE, RMSE, MAPE, R²) are correct and implemented
  identically in notebook 07 and the production script — verified at the
  formula level, not just trusted.
- The mandate schedule's previously-broken non-monotonic ratchet is now
  fixed (15.5% → 17.0% → 18.5% → 20.0% for 2027-2030), and every decree
  citation in `mandato_biocarburantes.csv` was independently checked against
  the BOE and is accurate.
- Notebook 13's Section 1 is a genuinely good practice: explicit, specific
  disclosure of what the model cannot prove (Repsol market share,
  station-level demand, price elasticity, a causal mandate effect) — honest
  scoping, not generic hedging.
- The Ljung-Box/ACF residual diagnostics added in notebook 09 are correctly
  implemented on genuine test-set residuals, with an honest small-sample
  caveat stated in the notebook's own text.
- The mini trend/regulation model (notebook 12) is correctly and verifiably
  isolated from the main pipeline — no script in `scripts/02`-`06` reads its
  output, and this isolation is explicitly documented in two separate places.
- Ridge and Diesel Share (both extreme-failure candidates, e.g. Ridge's
  Madrid MAPE of 6,559.8%) are kept in the raw metrics CSVs for transparency
  but deliberately excluded from the comparison chart so they don't flatten
  every other model's bar to invisibility — a good transparency-vs-readability
  tradeoff, explicitly labeled in the chart's own subtitle.

---

## Suggested priority order for fixing

1. C1/C2 (notebook 13 honesty gaps) — highest stakeholder-visibility risk,
   cheapest to fix (add a few paragraphs; the underlying data already exists).
2. C3 (output-collision hazard) — add a provenance guard (e.g. a written
   "model set" marker file, or the same `HEADLINE_FINAL_MODELS` check
   notebooks 10/10.1 already use) to notebook 09 and to the affected
   data-input notebooks.
3. C4 (mojibake in saved figures) — one-line fix, regenerate 5 PNGs.
4. I1 (SARIMA full-history check) — either correct the documentation's "no
   2025 data" claim to describe the actual (narrow, defensible) exception, or
   remove the full-history check from the eligibility filter and rely solely
   on the training-window check.
5. I2/I3 (notebook 09 bugs) — add the missing SARIMAX color/guard and the
   calibration disclaimer, or formally retire notebook 09 in favor of the
   script's own figures, which already have both fixes.
6. Everything else, roughly in the order listed.
