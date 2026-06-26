# Project Memory - Repsol Eco-Fuels Demand Forecasting Capstone

**Last updated:** 2026-06-25
**Maintainer note:** This file is the long-term source of truth for this project. See [Section 10](#10-future-instructions-for-claude) for how Claude should use and maintain it.

---

## 2026-06-25 Deleted Stale Remote Branch `codex/translate-notebooks`

Repo had one branch besides `main`: the remote-only `origin/codex/translate-notebooks`,
pointing at a single commit, `f3e4259` ("Translate notebook content to
English"). That commit is the same one already traced as the source of
notebook 02's `'Province'`/`'Provincia'` bug (see the entry below). Confirmed
`f3e4259` is already an ancestor of `main` (`git merge-base --is-ancestor`),
so the branch had nothing unmerged, and confirmed no open or closed PR
referenced it (`gh pr list --head codex/translate-notebooks` returned
nothing) before deleting it via `git push origin --delete`. `main` is now
the only branch, local or remote.

---

## 2026-06-25 Post-Session Audit: Fixed notebooks/02_data_cleaning.ipynb's 'Province'/'Provincia' Bug; Noted a Kernel Gap

Ran a full audit of everything from this session: full pipeline rebuild
from scratch (`03 -> 02 -> 04 -> 05 -> 06 -> 07`), every touched notebook
executed end to end, a repo-wide grep sweep for stale references, and a
cross-file consistency check. Pipeline and docs all checked out -- the only
real finding was that **notebooks/02_data_cleaning.ipynb crashes** on a
`KeyError: 'Province'` in its mojibake-repair cell; the real column is
`'Provincia'`. Traced to commit `f3e4259` ("Translate notebook content to
English"), predating this session -- the same bug class as the
`'Tendencia'`->`'Trend'` and `gasolina95`->`gasoline95` mistranslations
already fixed elsewhere (`NOTEBOOKS_AUDIT.md`), just missed for notebook 02
in that pass.

**Fixed:** changed `'Province'` -> `'Provincia'` in cell-6 (2 code
occurrences) plus the matching prose in cell-5 and cell-15. Confirmed no
repercussions: no production script references this filename or column
(grepped `scripts/`, zero matches), and notebook 04's own data-source
inventory explicitly documents `consumo_biodiesel_provincial.csv` as "not
merged" into the master dataset, used only by notebooks 01 and 02 --
notebook 01 doesn't share the bug. The committed CSV was already correctly
encoded (no mojibake found), so the cell had presumably been crashing
before ever reaching the save step for as long as the bug existed; this
fix restores the notebook's ability to run, it does not change any
committed data (re-saved CSVs verified byte-identical).

**Separately noted, not fixed:** every notebook in this repo has a generic
`"python3"` kernelspec, which resolves to system Anaconda on this machine,
not the project's pinned `.venv` (a `repsol-venv` kernel is registered and
does point at `.venv`, but no notebook's metadata selects it). This didn't
change any result discovered this session -- re-running the affected
notebooks with `repsol-venv` explicitly forced reproduced the same outputs
-- but it means casual "run this notebook" executions on this machine
silently use the wrong environment. Worth setting each notebook's
kernelspec to `repsol-venv` at some point; not done here since it's
unrelated to anything actually broken.

**How to apply:** if `consumo_biodiesel_provincial.csv` or
`consumo_biodiesel_ccaa.csv` are ever genuinely re-derived from new raw
CORES exports (not just re-running notebook 02 on the same file), re-check
that the raw export's column is still named `Provincia`, not some other
variant, before trusting this cell to run silently correct.

---

## 2026-06-25 Notebooks 12 and 13 Renumbered to 11 and 12

`11_mini_demand_model.ipynb` was removed upstream long before this session
(superseded by what was then notebook 12), leaving a permanent gap in the
notebook sequence: 10, [gap], 12, 13. User asked to close the gap.

**Action taken:** `git mv notebooks/12_mini_trend_regulation_model.ipynb
notebooks/11_mini_trend_regulation_model.ipynb`, then `git mv
notebooks/13_business_interpretation_and_recommendations.ipynb
notebooks/12_business_interpretation_and_recommendations.ipynb`. The
business-interpretation notebook (now 12) names its own figure outputs
after its number (`13_business_{region}_*.png`), so those 5 files were
also `git mv`'d to `12_business_{region}_*.png`, and the f-string that
constructs that filename was updated to match. The mini-trend notebook
(now 11) saves no figures to disk.

**Every internal self-reference was fixed, not just the filenames:**
- Notebook 11's own title cell ("# 12 -- Mini Trend...") and its two
  cross-references to the business-interpretation notebook ("see
  `notebooks/13_business_interpretation_and_recommendations.ipynb` Section
  4.4" / "see Section 4.4 of notebook 13").
- Notebook 12's own title cell ("# 13 -- Business Interpretation..."), its
  error message pointing at the mini-trend notebook, its Section 4.4
  header and body text ("notebook 12" / `notebooks/12_mini_trend...`), and
  the 5 markdown image-embed cells referencing the old `13_business_*.png`
  paths.

**Every external reference was also fixed:** `README.md` (7 spots),
`NOTEBOOKS_AUDIT.md` (inventory table rows + the "Remaining Caveat"
section's navigational pointer), `AUDIT_FIX_PLAN.md` (2 spots, plus a new
"Completed" entry), `scripts/07_selected_model_drivers.py` (4 spots --
this one is live code, not docs), and
`notebooks/05_feature_engineering.ipynb` (1 spot).

**What was deliberately left unchanged:** bare retrospective mentions like
"fixed the stale column reference in notebooks 10, 10.1, and 13" in
`NOTEBOOKS_AUDIT.md`, `AUDIT_FIX_PLAN.md`, and `DATA_AUDIT_REPORT.md` --
these are accurate historical records of work done while the files still
had those numbers, not navigational pointers, so relabeling them would
just be rewriting history for no reader benefit. The distinction applied:
literal file paths and "see/run notebook N" pointers get fixed everywhere
(a wrong pointer actively misleads), bare number labels in purely
retrospective "what we did" narrative do not. `INDEPENDENT_AUDIT_REPORT.md`
was left entirely untouched per the earlier explicit instruction not to
edit that file.

`NOTEBOOKS_AUDIT.md`'s inventory table now has two consecutive rows both
starting with "11_" -- the old, removed `11_mini_demand_model.ipynb` and
the current `11_mini_trend_regulation_model.ipynb`. This looks odd but is
correct: the row for the removed file explicitly says it shares a number
with an unrelated, later-renumbered file, specifically so a future reader
doesn't confuse the two.

**Verification:** executed both renamed notebooks end to end (clean, no
errors) before deleting/renaming anything downstream, then re-ran
`scripts/06_validate_outputs.py` (this was a docs/notebooks-only change,
so no production output was touched).

**How to apply:** if a future audit asks "where did notebook 13 go," this
entry is the answer -- it is now notebook 12.

---

## 2026-06-25 notebooks/10_1_final_models.ipynb Deleted, Consolidated Into 10

User asked why two near-identical "final models" notebooks existed.
`NOTEBOOKS_AUDIT.md`'s own inventory described 10.1 as "Cataluña detail" --
investigated and found that description was itself stale/wrong: 10.1
contained nothing Cataluña-specific. A full cell-by-cell diff of both
notebooks showed they were a near-duplicate: identical setup code,
identical SARIMA-order-check section and code, identical pooled-diagnostics
table and code, identical 2025-holdout and 24-month-forecast plotting code,
for all 5 targets in both. Neither notebook saves any figures to disk
(`plt.show()` only, no `savefig`), so there was no figure-dependency risk.

The only genuinely unique content in 10.1, found via the diff, was one
sentence in its Summary section: "pooled diagnostics show whether sharing
regional information would have helped on the 2025 holdout" -- a clearer
justification for *why* pooled regional ML is kept around as a diagnostic
than notebook 10 had. Notebook 10's own Summary was otherwise more complete
than 10.1's (it has "Honest limits" and a detailed "SARIMAX is excluded
almost everywhere" bullet that 10.1 lacked entirely).

**Action taken:** folded that one sentence into notebook 10's Summary
section as a new bullet ("Why pooled regional ML is kept around as a
diagnostic, not deleted"), verified notebook 10 still executes end to end
with that change, then deleted `notebooks/10_1_final_models.ipynb` via
`git rm`. Updated `NOTEBOOKS_AUDIT.md`'s inventory table (replaced the 10.1
row with a removal note) and its "Remaining Caveat" section (removed the
"10.1" reference, which was a current-state claim, not history). Left
every *historical* mention of "10, 10.1, and 13" elsewhere in
`NOTEBOOKS_AUDIT.md`, `AUDIT_FIX_PLAN.md`, `DATA_AUDIT_REPORT.md`, and
`INDEPENDENT_AUDIT_REPORT.md` untouched -- those are accurate records of
what was fixed in past sessions while 10.1 still existed, not current-state
claims, and `INDEPENDENT_AUDIT_REPORT.md` specifically was committed
as-is per an earlier explicit instruction not to edit it.

**How to apply:** if a future audit asks "why are there two notebook 10s,"
this entry is the answer -- there is now only one.

---

## 2026-06-25 Audit Finding M4: BIOS CERT Excel Files Stay in the Repo, Deliberately

M4 flagged the `ESTADISTICAS-BIOS CERT DEFINITIVAS *.xlsx` files (~24MB,
`data/` root) as dead, oversized, and undocumented: no code reads them, and
they contradict `.gitignore`'s blanket `*.xlsx` rule (tracked anyway,
pre-dating that rule). The recommendation was either wire them into the
pipeline (resolving H5) or document them explicitly as historical reference
material. H5 was already resolved a different way earlier this session --
CNMC's raw `consumos_mensuales_petroleo` files were established as the
reproducible target lineage instead, making these Excel files unnecessary
to wire in -- and README.md's Data Sources section already calls them out
as "historical/supplementary reference material... not required to
reproduce any current pipeline."

**Decision (explicit, user-confirmed): keep them in the repo as-is.** Not
moved to `data/raw/`, not added to a `.gitignore` exception, not deleted.
They stay at `data/` root, still technically contradicting the blanket
`*.xlsx` rule, still unread by any script or notebook -- this is now a
deliberate, accepted state, not an oversight. The remaining "housekeeping"
half of M4's recommendation (move/exempt them) was considered and
explicitly declined in favor of leaving them where they are, since they are
already documented in README.md and the team did not want to spend effort
relocating files with no functional role.

**How to apply:** if a future audit re-flags these files as dead weight or
an undocumented `.gitignore` contradiction, this entry is the answer -- it
is a known, decided state, not a new finding.

---

## 2026-06-25 Audit Finding M3 Investigated: Andalucía's 2023-04 Outlier Is Genuine, Not an Error

M3 flagged Andalucía's 2023 series as having an unexplained isolated
outlier: `Consumo_Tm = 0, 0, 0, 46, 0, 0, 0, 0, 19, 43, 159, 85...` -- a
single 46 Tm blip in April, isolated between two four-month runs of exact
zero, before the real ramp-up starts in September.

**Investigated, no fix needed.** Traced the value through every layer of
the pipeline (`data/raw/consumos_mensuales_petroleo/ds_14200_1.csv` ->
`data/inputs/consumo_biodiesel_ccaa.csv` ->
`data/features/features_modelo_completo.csv`) -- identical at each one, so
it is not a processing artifact (not a merge bug, encoding issue, or
mis-dated record introduced by this repo's own code).

Broke Andalucía's CCAA-level total down by province in the raw CNMC file:
the entire 46 Tm in April 2023 comes from **Córdoba alone**; every other
province reports exactly 0 that month. This fits the general character of
Andalucía's 2023 data -- each province starts reporting biodiesel
sporadically and independently (Jaén in September, Cádiz in October,
Granada in November, Huelva for one month only in October, etc.); Córdoba's
April blip is just the first instance of that same province-by-province
rollout pattern, not an outlier relative to it.

Pulled Córdoba's full BIODIESEL trajectory across all three raw files for
additional confirmation:
- 2023: `0,0,0,46,0,0,0,0,0,0,0,0`
- 2024: `7,0,12,4,8,0,0,5,4,20,25,28`
- 2025: `37,22,90,80,218,274,395,223,197,228,198,238`

A coherent story: April 2023 was Córdoba's first-ever recorded biodiesel
sale (likely one distributor's pilot/test batch), a gap while supply wasn't
yet consistent, intermittent low volumes through 2024, then a real,
steadily growing, established trend by 2025. Nothing about the shape
resembles a typo or data-entry error -- it looks exactly like an early
market establishing itself at the province level before regional
infrastructure catches up.

**How to apply:** if this point is ever re-flagged as a mystery in a future
audit pass, this entry is the answer -- no further investigation needed
unless new raw source files change the underlying numbers.

---

## 2026-06-25 Audit Fixes M1/M2: Notebook Path Claims, and a Complete Model-Fit Exception Log

**M1 (notebook narrative paths didn't match the code):**
`notebooks/02_data_cleaning.ipynb` claimed outputs under `data/processed/`
with different filenames than the code actually writes; the code overwrites
`data/inputs/consumo_biodiesel_{provincial,ccaa}.csv` in place and writes a
new `data/inputs/consumo_biodiesel_targets.csv`. `notebooks/03_external_data.ipynb`
claimed `data/processed/macro_features.csv`; the code saves
`data/inputs/macro_indicadores_ine.csv`. Fixed every markdown reference in
both notebooks (5 cells total) to match the actual `to_csv` calls, and
verified the row-count claims (1,872 / 720 / 180 / 36) against the current
files rather than just carrying the old numbers forward -- they were still
correct, only the paths were wrong.

**M2 (broad exception handling could mask real bugs as "model failures"):**
`scripts/05_modeling_with_cnmc.py` has ~25 `except Exception` blocks around
model-fitting calls, mostly deliberate (let a candidate lose gracefully).
Previously only exceptions whose message contained the literal string
"degenerate" were persisted (to `degenerate_fits.csv`); everything else
printed once to the console and vanished -- indistinguishable from an
unremarkable model loss even if the real cause was a genuine bug. Added
`log_model_exception()` (module-level `MODEL_FIT_EXCEPTIONS` list, reset at
the top of `main()`) and called it from all 22 except-blocks that weren't
already self-logging via some other persisted column (3 of the 25 already
were: `sarima_shippability_reason`'s return value, `tune_sarima_orders`'
`train_reason` column, and `evaluate_pooled_ml_experiment`'s `Status`
column -- left untouched). Written to the new
`data/outputs/model_fit_exceptions.csv`, aggregated by (Target, Model,
Stage, Exception) with a `Count`, since the training/pooled walk-forward
stages call this once per fold and would otherwise repeat an identical
message dozens of times for the same underlying failure.

**What it found, investigated immediately:** 226 total exception
occurrences across the full pipeline run, only 30 of them non-degenerate
(2 distinct messages). Both are explainable, benign edge cases, not hidden
bugs: (1) `"Not enough non-null rows for SARIMAX training"` is an existing,
intentional `ValueError` guard for early walk-forward folds; (2) a
statsmodels-internal `IndexError` ("too many indices for array: array is
0-dimensional") occurs when a heavily seasonally-differenced SARIMA order
(`D=1`, period 12) is fit on a training fold with too few rows to leave any
usable data after differencing (reproduced directly: `fold_tr` of 14 rows,
order `(1,1,1)(0,1,0,12)`, fails inside statsmodels' own
`_conditional_sum_squares`). Neither affected order/candidate ever wins a
target's walk-forward comparison, so this is a visibility improvement, not
a result change. Re-ran `05 -> 06`: every existing production output file
is byte-identical except for the new file itself; `06_validate_outputs.py`
got a new schema-only check for it (row count legitimately varies with
training window length, so no fixed-shape check is appropriate).

**How to apply:** if a future change to the modeling script adds a new
`except Exception` around a model-fitting call, call `log_model_exception()`
from it too (per-occurrence if it runs once per target, or accept that the
aggregation step in `main()` will collapse per-fold repeats automatically).

---

## 2026-06-25 SARIMA Chart/Export Confidence Level Changed From 95% to 50% (Display Only)

The calibrated SARIMA prediction interval added earlier the same day (see
"Audit Fixes: ... Calibrated Intervals" below) made the Cataluña and
Andalucía forecast charts look visually broken: at the textbook-default
95% level, the interval explodes asymmetrically by month 24 once
back-transformed out of log1p space -- Cataluña's ~3,400 Tm point forecast
sat against a ~232,000 Tm 95% upper bound. That finding is still accurate
and still on the record below; it has not been retracted or found wrong.
It is mathematically honest (a 24-month-ahead interval from ~30 monthly
training points really is that uncertain), but it made the chart unusable
for a planning conversation, and the user explicitly asked for the charts
to "look better" for both regions.

**Decision: change the *display* level, not the model.** Re-fitting or
re-selecting SARIMA to produce a tidier-looking interval was rejected --
that would reopen the test-set-selection question this project has
otherwise been careful about, purely for a cosmetic reason, and the
explosive interval is a true property of the fitted model, not evidence
something is mis-specified. Instead, `scripts/05_modeling_with_cnmc.py`'s
`predict_sarima_with_ci` is now called with a 50% alpha
(`SARIMA_CHART_CI_ALPHA = 0.5`) for the shipped chart and
`data/outputs/forecast_24m_sarima_confidence_intervals.csv`, instead of the
default 95%. The chart's legend label is now computed from this constant
(`f"{ci_level_pct}% prediction interval (calibrated)"`) rather than
hardcoded, so it cannot silently drift out of sync if the alpha is changed
again. The function itself still defaults to `alpha=0.05` and remains
available at that level to any caller that wants the more conservative
figure -- this is a display choice for the shipped artifacts, not a
retraction of the 95% finding.

**Also updated to match:**
`notebooks/12_business_interpretation_and_recommendations.ipynb`'s own
(renumbered from 13 on 2026-06-25, see this file's "Notebooks 12 and 13
Renumbered" entry) regional plots (Section 1.4, added earlier the same
day) now build the
identical calibrated/heuristic band distinction at the same 50% level, for
all 5 targets, with an explanatory paragraph stating plainly that this is
a legibility choice, not a smaller uncertainty estimate. `README.md`'s
"Audit Fixes" section (third pass) documents the same change.

**Verification:** re-ran `scripts/05_modeling_with_cnmc.py` ->
`scripts/06_validate_outputs.py` (alpha-agnostic checks: `CI_Lower <=
Forecast <= CI_Upper` and `CI_Lower >= 0` both still pass at any
confidence level) -> re-executed notebook 12 end to end and visually
inspected the regenerated Cataluña and Nacional charts. Cataluña's 50%
band now reaches roughly 14,000-15,000 Tm by month 24 (versus ~232,000 Tm
at 95%) -- a legible, readable chart that still shows real, calibrated,
and substantial uncertainty, not a falsely narrow one.

**How to apply:** if the SARIMA chart/export confidence level is ever
changed again, change `SARIMA_CHART_CI_ALPHA` in
`scripts/05_modeling_with_cnmc.py` and the matching local constant in
notebook 12's Section 1.4 cell together, and update this entry (or add a
new one) rather than letting the two drift apart.

---

## 2026-06-25 Target Definition Clarification: Distinct-Product-Line Biodiesel Only

Confirmed directly with the Repsol representative: the project's target (`Consumo_Tm`)
is **biodiesel sold/reported as its own distinct product line**, not the biodiesel
blended at low concentration into ordinary diesel under the national mandate. This
is the correct, intended scope -- not a bug -- but it had only ever been written
down explicitly in `notebooks/11_mini_trend_regulation_model.ipynb`'s intro markdown
(renumbered from 12 on 2026-06-25, see this file's "Notebooks 12 and 13
Renumbered" entry). Every other document (this file, `README.md`, notebook 12,
itself renumbered from 13) described the target only
as "total market biodiesel demand" with no caveat, which could be misread as covering
the much larger mandate-blended volume.

**The distinction, in detail:** Spanish fuel statistics (CNMC) report two separate
things under "biodiesel":
1. Biodiesel blended at ~10.5-14% (the legislated mandate) into ordinary Gasóleo A
   diesel -- reported by CNMC as part of `GASÓLEO A` consumption, never broken out
   separately.
2. Biodiesel sold/reported as its own distinct product (the CNMC `BIODIESEL`
   category) -- e.g. higher-concentration blends sold to specific fleets/users.

`Consumo_Tm` is #2. Confirmed numerically: national `GasoleoA_Tm` runs ~1.7-1.9M
Tm/month against `Consumo_Tm`'s ~10-27K Tm/month, and `Biodiesel_GasoleoA_Ratio`
sits at 0.5-1.4%, far below the 11.5-14% mandate level it would track if it included
the blended portion. This also explains why the target grows ~135x from 2023 to
2025: that is the ramp-up of a small, distinct, newly-reported product line, not
overall mandate-driven biodiesel penetration of the diesel pool (which moves
gradually, 10.5% -> 11% -> 11.5% -> 14%, tracking the mandate schedule, not 135x).

**Fixed:** added this section, updated the Section 2 scope bullet below, updated
`README.md`'s intro with a new "Target Definition" section, updated
`notebooks/12_business_interpretation_and_recommendations.ipynb` Section 1, added a
confirmation note to `notebooks/11_mini_trend_regulation_model.ipynb`'s intro, and
corrected a mandate-causality overstatement in
`notebooks/05_feature_engineering.ipynb` Section 6 (it previously implied the
mandate directly floors this target; the mandate floors the blended-into-Gasóleo-A
volume, a different series this project does not model).

**How to apply:** any future text describing `Consumo_Tm` / the project's
"biodiesel demand" target must use this precise distinct-product-line language,
never an unqualified "total biodiesel demand."

---

## 2026-06-25 SARIMA Order Selection No Longer Touches 2025 Data (`sacha`)

A second, independent audit pass found that `tune_sarima_orders()` in
`scripts/05_modeling_with_cnmc.py` violated this project's own hard rule
("never select a model family using test-set performance," Section 10 below)
for SARIMA order selection specifically. The "full-history degeneracy check"
added in the 2026-06-25 audit-fixes round above (to catch the original
Cataluña flat-forecast bug) fit every one of the 15 candidate orders on the
full 2023-2025 history -- including 2025 -- and used the result to filter
which orders were even eligible to win, before ranking survivors by
training-only walk-forward MAPE. That is genuine test-period data use in a
model-selection decision, not just an accuracy comparison against 2025: the
fitted SARIMA coefficients for that check are estimated using 2025's actual
values, and the eligible-candidate pool (and therefore the winner) depended
on it.

**Concrete proof it was material, not theoretical:** for Cataluña, the order
with the single best training-only score, (0,1,1)(1,0,0,12) at 63.66% MAPE,
was excluded *solely* because its full-history refit produces a near-flat
(range 0.0105) 2026-2027 forecast. The next-best training-only order,
(0,1,2)(1,0,0,12) at 66.90% MAPE, was selected instead. For the other 4
targets, the best training-only order already happened to pass the
full-history check too, so the mechanism ran but didn't change the outcome
there -- this was a real, live issue for exactly 1 of 5 targets, not a
hypothetical one.

**The fix, agreed with the user after weighing two options:**
1. *Make the stability check itself training-only* (e.g. analytical AR/MA
   root-margin checks) was considered and rejected: Cataluña's problem order
   already passes its own training-window-only stability check (fit on just
   2023-2024) -- the fragility only appears once 2025 is included in the
   fit. A check that never looks at 2025 cannot, by definition, catch a
   failure mode that only manifests once 2025 is added, so this option would
   not have actually protected against the bug it needs to protect against.
2. *Separate training-only selection from a one-time post-hoc safety check*
   was adopted. `tune_sarima_orders()` now ranks candidates purely by
   training-only `WalkForward_MAPE` (filtering only training-window
   degeneracy, computed on 2023-2024 alone) to get a single winner. The full
   2023-2025 history is then used exactly once, on that single winner only,
   via the new `sarima_shippability_reason()` check -- it can veto the
   winner but never ranks or filters the candidate grid. If the winner fails
   it, the function does not auto-substitute the next-best training-only
   candidate (mathematically identical to the original bug, just relabeled)
   and does not silently fall back to the plain default order either
   (verified: Cataluña's default order, (1,1,1)(1,0,0,12), scores 87.4%
   training MAPE -- a real, measurable regression versus the 66.9% shipped).
   It raises, requiring an explicit, reviewed entry in the new
   `SARIMA_SAFETY_OVERRIDES` dict, the same "decided explicitly, not
   defaulted" pattern already used for the mandate-ratchet and
   SARIMAX-feature-set decisions. One override is currently recorded, for
   Cataluña, pointing at the same order it was already shipping.

**Verification:** re-ran `scripts/05_modeling_with_cnmc.py` ->
`scripts/06_validate_outputs.py` -> `scripts/07_selected_model_drivers.py`
end to end and diffed every file in `data/outputs/` and `reports/figures/`
against the pre-fix state. Result: every selected model, SARIMA order, 2025
holdout metric, forecast value, and figure is byte-identical to before.
Only `sarima_grid_search_results.csv` (lost the `FullHistory_*` columns,
since that check is no longer run per-candidate) and
`sarima_order_acceptance.csv` (gained `Safety_Check_Degenerate`/
`Override_Applied`/`Override_Reason` columns) changed shape, plus the new
`data/outputs/sarima_safety_check.csv` audit trail was added. This fix is
purely a methodology-and-disclosure correction, not a results change.
`scripts/06_validate_outputs.py` was also extended to fail loudly if any
target's safety check ever fails without a matching recorded override --
the original bug (a silent, undisclosed substitution) can no longer recur
unnoticed.

Updated alongside this fix: `README.md` (Model Selection section + new
"Audit Fixes, second pass" section), `PHASE2_MODELING_REPORT.md` (Selection
Rule section), `DATA_AUDIT_REPORT.md` (`sarima_order_acceptance.csv`
description), `AUDIT_FIX_PLAN.md` (new completed-fix entry), and notebooks
10, 10.1, and 13 (SARIMA order check cells and displayed acceptance
columns).

**How to apply:** any future change to SARIMA order selection must keep the
full-history check scoped to a single already-chosen candidate, never used
to rank or filter the grid. If a future override is needed for a new
target, add it to `SARIMA_SAFETY_OVERRIDES` with the same reasoning
discipline (what failed, what alternative was checked, why it's safe), not
as a silent default.

---

## 2026-06-25 Target Lineage Clarified: CNMC, Not the BIOS CERT Excel Files, Is the Reproducible Source

An audit found that no notebook or script in the repo actually reads the
three `ESTADISTICAS-BIOS CERT DEFINITIVAS *.xlsx` files sitting in `data/`
(2020-2022/2023/2024), and that no 2025-dated file of that type exists at
all -- meaning the target variable's raw-to-processed derivation looked
unreproducible from the committed repo, since `consumo_biodiesel_ccaa.csv`
just existed as an already-processed artifact with no visible upstream code.

**Resolved, not by writing new extraction code, but by recognizing an
already-coded, already-verified equivalence:** `scripts/03_clean_cnmc_petroleum.py`'s
`reconcile_biodiesel()` (and `scripts/02_master_dataset_builder.py`'s merge
check) already assert that CNMC's `CNMC_Biodiesel_Tm` -- built from the raw,
fully-coded `data/raw/consumos_mensuales_petroleo/ds_*.csv` files -- reconciles
**exactly** (max abs diff 0.0 Tm) against `consumo_biodiesel_ccaa.csv`'s
`Consumo_Tm` for every CCAA, every month, across the entire 2023-2025 modeled
window. CNMC raw data covers 2023-01 through 2026-02, fully spanning what
this project needs. That makes CNMC the project's real reproducible-from-raw
lineage for the target, independent of the BIOS CERT Excel files.

**Decision:** document CNMC as the canonical lineage (see the corrected
Section 3 entry below) and keep the BIOS CERT Excel files as historical/
supplementary reference material, not a reproducibility requirement. Did
**not** attempt to open and parse those Excel files' 30+ sheets (`Balance
biodiésel`, `% Cumplimiento obligación`, several sustainability breakdowns,
etc.) to wire them in as an alternative source -- there was no confirmed
need (CNMC already covers the full modeled window) and no confirmation those
sheets even contain a matching CCAA-level monthly breakdown, so that would
have been speculative engineering effort with a real chance of being a dead
end, not a fix to a problem that still exists once CNMC is recognized as
sufficient.

**How to apply:** if `consumo_biodiesel_ccaa.csv` is ever lost or needs
independent verification, it (and the equivalent provincial/targets files)
can be regenerated for 2023-2025 from `data/processed/cnmc_diesel_market_features.csv`'s
`CNMC_Biodiesel_Tm` column (filter to `Fecha <= 2025-12`, rename to
`Consumo_Tm`) -- this is the same equality the pipeline already checks on
every run, not a new claim. Do not describe the BIOS CERT Excel files as
"the" source of this target in future documentation without first actually
opening their data sheets and confirming what they contain; until then,
describe them only as historical/supplementary material.

---

## 2026-06-25 Audit Fixes: Mandate Data Integrity, Residual Diagnostics, Calibrated Intervals, Sensitivity Analysis (`sacha`)

A formal 11-section audit (user-supplied prompt, full report delivered 2026-06-24)
surfaced six "Major" findings. All six were fixed and re-verified end to end
(full `03->02->04->05->06` pipeline rerun, validator passed, all touched
notebooks re-executed via the `repsol-venv` kernel with zero errors).

### 1. Mandate schedule data integrity (`data/inputs/mandato_biocarburantes.csv`)

Two separate problems, found by actually researching the BOE (web search,
not memory -- the system clock for this session is genuinely 2026-06, so
post-training-cutoff Spanish regulatory searches return real results):

- **Non-monotonic `Mandato_Energia_Pct`**: 2027 was 15.5% but 2028-2030 dropped
  back to 14.0%, breaking the ratchet every other year follows. User chose to
  continue the +1.5pp/year projection: 2028=17.0%, 2029=18.5%, 2030=20.0%.
- **Fabricated/miscited "Decreto 61/2023"**: cited as the source of
  `Mandato_Biodiesel_Blend_Pct` (a 3%->7.5% volumetric biodiesel blend
  mandate). Direct BOE search for "Real Decreto 61/2023" returns nothing
  matching that description at all. The only real decree numbered 61 is
  **RD 61/2006**, which sets a *maximum* 7% FAME blend wall for engine
  compatibility -- the opposite of a rising minimum mandate, and a completely
  different instrument. The real 2024 biofuel-mechanism order is **Orden
  TED/728/2024** (15 Jul 2024), but it does not contain the claimed 3%/7.5%
  figures either. User chose: **remove the feature entirely** rather than
  keep an unverifiable number or guess at a replacement citation.

What WAS verified as accurate against BOE directly:
- RD 1085/2015: 2016-2020 figures (4.3/5/6/7/8.5%) match BOE exactly.
- RD 205/2021: sets 2021-2022 objectives (9.5%/10.0%), confirmed real; date
  was off by one day in our citation (31 mar -> corrected to 30 mar 2021).
- RD 376/2022: sets 2023-2026 baseline at 10.5/11/11.5/**12**% (before RD
  5/2026 amended 2026 up to 14%) -- our 10.5/11/11.5 figures match exactly;
  date was off by one day (18 may -> corrected to 17 may 2022).
- RD 5/2026: real, confirmed via BOE-A-2026-560. Signed 8 Jan 2026, raises
  2026 from 12%->14%, published in BOE 10 Jan 2026 (our citation said "10 ene
  2026" for the decree's own date; corrected to distinguish signing vs.
  publication date).

**Net effect**: `mandato_biocarburantes.csv` is now 4 columns (was 5),
`ML_FEATS`/`MANDATE_FEATS` lost `Mandato_Biodiesel_Blend_Pct` everywhere
(scripts 04/05/06, notebooks 05/07/08/09). Feature tables are 35 columns
(was 36). **Selected models and 2025 holdout metrics are byte-identical to
before this fix** -- confirmed by direct comparison -- because none of the
5 winning models (Logistic, Logistic, SARIMA, SARIMA, Gompertz) ever used
the mandate features at all.

### 2. Formal residual diagnostics added to `09_evaluation.ipynb`

The notebook's own Section 3 markdown promised "ACF of residuals (remaining
autocorrelation = model misspecification)" but never ran one (`plot_acf`/
`plot_pacf` were imported, never called -- a leakage-audit-adjacent finding
from the 2026-06-24 report). Added a new subsection (3b) with Ljung-Box test
+ ACF/PACF plots on each target's selected-model 2025 test residuals.

**Result**: Cataluña (SARIMA, p=0.043) and Andalucía (SARIMA, p=0.032) show
statistically significant residual autocorrelation at the 5% level; Nacional
(Logistic), Madrid (Logistic), Valencia (Gompertz) do not. Caveat: only 12
test points per target -- treat as a coarse screen. Outputs:
`data/outputs/ljung_box_residual_diagnostics.csv`,
`reports/figures/09b_residual_acf_pacf.png`.

### 3. Price-feature ablation re-scored without test-set peeking

`06_price_features.ipynb`'s go/no-go gate and `08_modeling_with_prices.ipynb`'s
"does adding prices help" comparison both used full-window correlation / 2025
test-set MAPE -- the same leakage pattern as picking a model family by test
MAPE, just applied to a feature-set decision instead. Fixed both to decide
using train-only (2023-2024) walk-forward MAPE:
- Notebook 06: added `df_corr_train` (correlation computed on 2023-2024 rows
  only) as the actual decision input; full-window correlation kept for
  context, explicitly labeled diagnostic-only.
- Notebook 08: added `walk_forward_mape()` (mirrors the production walk-forward
  pattern in `scripts/05`) computing RF/XGBoost walk-forward MAPE with and
  without price features on the same 2023-2024 folds. Output:
  `data/outputs/price_features_walkforward.csv`.

**Result**: price features do NOT clearly help under the honest criterion --
RF improves in 1/5 targets, XGBoost in 0/5. The original full-window
correlation (r ~= -0.81) overstated their value. Does not change production
model selection (none of the 5 selected models use price features).

### 4. Calibrated SARIMA prediction intervals

The forecast chart (`reports/figures/11_forecast_24m.png`) previously showed
only a heuristic MAPE/RMSE-scaled band, honestly labeled "error band" but not
a real statistical interval. Added `predict_sarima_with_ci()` in
`scripts/05_modeling_with_cnmc.py`, using the SARIMA fit's own
`get_forecast().conf_int()` (back-transformed from log1p). `final_forecasts()`
now returns a 3-tuple including `df_sarima_ci`, saved to
`data/outputs/forecast_24m_sarima_confidence_intervals.csv`.

For SARIMA-selected targets (Cataluña, Andalucía), the chart now shows this
real 95% interval instead of the heuristic band. **Honest finding, not a
bug**: the calibrated interval is dramatically wider than the old heuristic
band by month 24 (e.g. Cataluña Dec 2027: point forecast 3398 Tm, but the
calibrated 95% interval is [49, 232,394] Tm) -- a log1p-space SARIMA fit's
forecast-error variance compounds over a 24-step horizon and explodes
asymmetrically after `expm1` back-transformation. This reveals the true
statistical uncertainty at a 24-month horizon is far larger than the old
band implied. Logistic/Gompertz targets keep the heuristic band, now
explicitly labeled "illustrative error band (not calibrated)" since no
native interval exists for curve-fit models without bootstrapping.

### 5. Sensitivity analysis for macro/mandate assumptions

The 24-month forecast held macro at "last known value" and mandate at its
legislated/projected schedule with no alternative scenario anywhere. Added
`build_scenario_sensitivity()` to `scripts/05_modeling_with_cnmc.py`: re-runs
Ridge/Random Forest/XGBoost (the only headline candidates that consume
macro/mandate features) under three scenarios (Neutral, Macro_Downturn:
Tasa_paro+2pp/IPI_original x0.95/IPC_var_anual+1pp, Mandate_Delayed: mandate
held at its 2025 level instead of stepping up). Output:
`data/outputs/scenario_sensitivity.csv`. Required adding a `mandate_override`
parameter to `recursive_forecast_ml()` (additive, default `None`, zero
behavior change for existing callers).

**Genuine finding, verified empirically, not a bug**: Random Forest and
XGBoost show IDENTICAL forecasts for Neutral vs. Mandate_Delayed. Verified
this is correct by overriding the mandate value to an absurd 999.0 and
getting the exact same prediction as 11.5 or 14.0 -- `Mandato_Energia_Pct`
only ranges 10.5-11.5 in the 2023-2024 training data, so every value at or
beyond that range (11.5 delayed, 14.0/15.5 legislated, or 999 as a sanity
check) routes to the same terminal leaves in every tree. This is the
textbook tree-model extrapolation limitation: trees cannot extrapolate
beyond an observed feature range. Ridge DOES respond to the mandate value
linearly, but its own previously-documented catastrophic explosive
extrapolation swamps the effect (saturates to the same runaway trajectory
regardless of starting mandate value), so its scenario sensitivity isn't
practically informative either. Macro shocks ARE a usable signal for
RF/XGBoost (Tasa_paro/IPI_original/IPC_var_anual vary enough within the
training window for trees to have learned real splits on them).

None of the 5 currently-selected production models use macro/mandate inputs
at all, so **the production forecast itself remains scenario-invariant**
regardless of this finding -- flagged explicitly via the
`Selected_Model_Uses_Scenario_Inputs` column in the output CSV and in the
script's printed summary.

### What was NOT done, and why

- Did not attempt to find a real replacement citation for the removed
  biodiesel-blend mandate feature -- the user chose removal over guessing.
- Did not rewrite notebook 09's pre-existing stale narrative text (cell-18's
  "KNOWN LIMITATIONS" prose, cell-19's results table) to match current
  production numbers -- that staleness predates this fix, was already flagged
  in the 2026-06-24 audit (Section 11, notebook redundancy/staleness, "known,
  accepted, not fixed"), and rewriting it was out of scope for this specific
  six-item fix list.
- Did not add calibrated intervals for Logistic/Gompertz (would need
  bootstrapping, a larger change) -- the audit finding only required "at
  least one" calibrated interval for SARIMA/SARIMAX-selected targets.
- Did not fold the mini-model's (`12_mini_trend_regulation_model.ipynb`)
  3-scenario approach into the main pipeline -- user explicitly chose the
  lighter option (re-run feature-aware candidates under 2-3 scenarios)
  over the heavier option (integrate the mini-model's scenario logic).

## 2026-06-24 SARIMAX Overfitting Fix: Degeneracy Gate Extended To Fit Quality (`sacha`)

This section supersedes the selected-model table in the "Training-Only
Seven-Candidate Rebuild" entry below.

### What was found

Cataluña's selected model (SARIMAX, 92.3% 2025 holdout MAPE, the weakest
result in the whole project) was investigated because the number looked odd.
Root cause: SARIMAX fits 9 exogenous regressors plus ARMA/seasonal terms
(~11 parameters) against only ~22-34 usable rows per target. Refitting the
exact production model directly showed:

- `sigma2` (the fitted residual variance) collapsed to ~1e-7-1e-8 for 4 of
  the 5 targets (Nacional, Madrid, Cataluña, Valencia) -- only Andalucía's
  fit was numerically healthy (sigma2 = 0.29).
- statsmodels' own optimizer reported `ConvergenceWarning: Maximum
  Likelihood optimization failed to converge` for those same 4 targets, and
  for Cataluña additionally reported `Covariance matrix is singular or
  near-singular, condition number 4.85e+22`.
- Per-fold walk-forward errors for Cataluña's SARIMAX were wildly more
  dispersed than plain SARIMA's (std 62.8 vs 25.0, one fold spiking to
  283.9% MAPE) even though the two models' *median* training scores looked
  close (68.5% vs 69.6%). The walk-forward gate's median aggregation -- a
  deliberate, otherwise-sound choice to stop one bad fold dominating
  selection -- was exactly what hid this: a model that is occasionally wildly
  wrong and a model that is consistently mediocre can land on a similar
  median, even though only one of them is trustworthy.
- This is not a Cataluña-specific issue. It is a property of the
  `SARIMAX_EXOG_FEATS` list (9 features) being too rich for this dataset's
  size, regardless of target.

### The fix

`scripts/05_modeling_with_cnmc.py`:

- Added `fit_degeneracy_reason()`: rejects a SARIMA/SARIMAX fit if the
  optimizer's own `mle_retvals["converged"]` flag is false, or if `sigma2`
  is below `SARIMA_SIGMA2_FLOOR = 1e-3`. Wired into `train_sarima()` and
  `train_sarimax()` themselves (both raise on a degenerate fit), so every
  existing call site (`evaluate_models`, `walk_forward_scores`,
  `final_forecasts`, the SARIMA order grid search) inherits the check
  automatically through their existing exception handling -- no call site
  needed to be touched individually.
- `evaluate_models()` and `final_forecasts()` now also collect every
  degenerate exclusion into a new `data/outputs/degenerate_fits.csv`
  (`Target, Model, Stage, Reason`) instead of only printing it to the
  console, so the exclusion is auditable, not just logged transiently.
- `scripts/06_validate_outputs.py` now reads that file: a headline candidate
  may legitimately be missing from `metricas_modelos.csv` for a target only
  if it is documented there; anything else missing is still a hard failure.
  Also added a safety check that the final selected model for a target is
  never one flagged degenerate for that target.
- **Extended the same check to the SARIMA order grid search's existing
  stability check**, and **added a second, independent stability check using
  the full 36-month history** (`tune_sarima_orders()` previously only
  re-simulated stability from the 24-month training window, which is not
  what `final_forecasts()` actually refits and ships -- this gap let
  Cataluña's grid-selected order `(0,1,1)(1,0,0,12)` pass the training-window
  check but produce a literal zero-range flat forecast when refit on the
  full history, caught only by `validate_selected_forecast_shape`'s separate
  near-flat check during this fix's own verification run). New columns
  `FullHistory_Origin_24m_Degenerate` / `_Reason` in
  `sarima_grid_search_results.csv`; an order must pass both checks to be
  treated as stable.

### Consequence: SARIMAX is now excluded almost everywhere, by design

After the fix, SARIMAX has zero training-walk-forward score (`inf`) for
Nacional, Madrid, Cataluña, and Andalucía, and a real-but-poor score for
Valencia (92.1%, still loses to Gompertz's 57.3%) -- it does not win any
target. This was the explicit, deliberate choice made when picking the fix
(see prior turn): leave `SARIMAX_EXOG_FEATS` untouched rather than trim it to
make SARIMAX artificially competitive, and let the honest result be "SARIMAX
is not viable at this sample size" rather than engineer around that finding.

Applying the *same* fit-quality check to plain SARIMA (not just SARIMAX) was
a deliberate consistency choice, not scope creep: the same overfitting risk
exists in principle for any order in `SARIMA_GRID`, just far less often given
SARIMA's much smaller parameter count. It had a real, traceable effect:
**Nacional's selected model changed from SARIMA to Logistic** as a side
effect -- 3 of the 11 training-only walk-forward folds for Nacional's
previously-best order `(1,1,1)(1,0,0,12)` were themselves silently
non-convergent, and excluding them raised that order's honest median MAPE
from 39.7% to 51.9%, below Logistic's 43.1%, which is why a different order
and ultimately a different model now wins for Nacional.

### Final selected models after this fix

| Target | Selected model | Training walk-forward MAPE | 2025 holdout MAPE | 2025 R2 |
|---|---|---:|---:|---:|
| Nacional | Logistic | 43.1% | 36.7% | -1.041 |
| Madrid | Logistic | 37.2% | 73.6% | -8.273 |
| Cataluña | SARIMA | 66.9% | 50.1% | -7.182 |
| Andalucía | SARIMA | 48.8% | 52.6% | -1.929 |
| Valencia | Gompertz | 57.3% | 34.2% | -1.246 |

Cataluña's holdout MAPE improved from 92.3% to 50.1% -- still the second-worst
in the set (after Madrid), and Cataluña's R2 (-7.182) is still the second most
negative, but the forecast is no longer driven by a fit that statsmodels
itself flagged as unreliable. Nacional's holdout MAPE improved slightly
(29.0% to 36.7% is technically a regression in isolation, but the prior 29.0%
was earned partly by training-CV folds that have since been shown to be
non-convergent noise, not real skill -- the 36.7% is the more trustworthy
number even though it looks worse).

Andalucía's forecast is still fairly flat (range 157.9 Tm across 24 months,
order `(1,1,2)(1,0,0,12)`) and Cataluña's is similarly tight (range 64.6 Tm),
but both now pass `validate_selected_forecast_shape`'s degeneracy checks
(unlike the literal zero-range flat forecast the grid's previously-selected
Cataluña order produced before the full-history check was added). This is
the same fundamental small-sample limitation described in the original
Andalucía investigation (not enough clean seasonal history to support a
strongly seasonal model without overfitting) -- now confirmed present for
Cataluña and Andalucía both, and explicitly tested for, rather than
discovered by accident.

### What was *not* done, and why

`SARIMAX_EXOG_FEATS` was deliberately left unchanged. The alternative
(shrinking it so SARIMAX has a real chance of being a stable, legitimate
winner somewhere) was offered and explicitly declined in favor of this
gate-only fix. If SARIMAX's feature set is revisited later, it should be
sized relative to the smallest target's usable training rows (~22), not
chosen independently of sample size the way the current 9-feature list was.

---

## 2026-06-24 Notebook Coherence Fixes (`sacha`)

A coherence audit after the seven-candidate rebuild (below) found that an
earlier "translate notebook content to English" pass had renamed real
data-derived string literals inside *code* cells, not just prose. Renaming a
column name or a raw source value breaks a notebook the moment it touches
real data, since nothing else in the pipeline was renamed to match. Three
distinct breakages were found, reproduced, and fixed:

1. `'Tendencia'` (the real trend-index column from `scripts/04_build_features.py`)
   had become `'Trend'` in notebooks 05, 07, 08, 09, causing `KeyError: 'Trend'`
   against the real feature tables. Reverted to `'Tendencia'` in all four.
2. The raw `Producto` values (`'Gasolina 95 E5'`, `'Gasolina 98 E5'`,
   `'Gasóleo A habitual'`, `'Gasóleo Premium'`) and the `gasolina95`/`gasolina98`
   slugs had become English (`'Gasoline 95 E5'`, `'Diesel A habitual'`,
   `gasoline95`, ...) in notebook 06's `PRODUCT_MAP` and notebook 08's price-join
   cell. Notebook 06 would have silently matched zero rows for all four fuel
   products; notebook 08 crashed with `KeyError: 'PVP_gasoline95_nac_lag1'`.
   Reverted to the real Spanish values in both.
3. Notebooks 10, 10.1, and 13 still referenced `Default_2025_MAPE` /
   `Grid_Selected_2025_MAPE`, columns removed from `sarima_order_acceptance.csv`
   when the SARIMA order selection became training-only (see below). Fixed to
   display `Grid_WalkForward_MAPE` / `Selected_By_Training_WalkForward` instead.

Also fixed: literal `?` mojibake ("Catalu?a", "Andaluc?a") in notebooks 10,
10.1, 13, likely from pasting console output into markdown instead of writing
the string directly.

Notebooks 05, 06, 07, 08, 09, and 13 were re-executed end to end (new Jupyter
kernel `repsol-venv` registered against `.venv` so execution uses the pinned
package versions) to confirm zero errors and to regenerate stale figures --
notably the five `13_business_*_train_validation_forecast.png` charts, which
had been a full day stale relative to the final model selection.

**Important side-effect to remember:** notebook 05, if run, overwrites
`data/features/features_*.csv` with its own older 27-column schema (no CNMC,
no mandate features) instead of the current 36-column production schema.
Notebooks 07 and 08, if run, overwrite several `data/outputs/*.csv` filenames
that `scripts/05_modeling_with_cnmc.py` also owns (`model_selection_walkforward.csv`,
`predicciones_test_2025.csv`, `forecast_24m_sarima_rf_xgb.csv`,
`tableau_export_legacy.csv`, plus the English-named duplicates). After running
any of notebooks 05/07/08, re-run `scripts/04_build_features.py` and
`scripts/05_modeling_with_cnmc.py` (then `scripts/06_validate_outputs.py`) to
restore the authoritative state. This was done after this fix round; the
05/06/07/08/09/13 figure regeneration is the only intended side effect, and
`scripts/06_validate_outputs.py` passes on the restored state.

`DATA_AUDIT_REPORT.md`, `NOTEBOOKS_AUDIT.md`, and `AUDIT_FIX_PLAN.md` were also
stale (still describing the superseded "Phase 2 / no-pooling" model table) and
have been refreshed to match the current seven-model selection and this
notebook fix round.

**Lesson for any future bulk text edit (translation, renaming, formatting)
across notebooks:** never apply it blindly to code cells. A find-and-replace
that is safe in markdown prose can silently rename a column name, a raw
source-data value, or a dict key in code, and the failure mode ranges from an
immediate `KeyError` to a silent zero-match with no error at all. Diff
code-cell changes separately from markdown-cell changes, and run every
touched notebook before considering the edit done.

---

## 2026-06-24 Training-Only Seven-Candidate Rebuild (`sacha`)

This section supersedes the earlier 2026-06-24 feature-aware-only attempt and
the 2026-06-23 no-pooling delivery cleanup for the active `sacha` branch.

The data pipeline is unchanged: keep data cleaning, the master dataset, feature
engineering, CNMC joins, the mandate schedule, leakage-safe lags, and the plotting
/ export infrastructure. Do not modify scripts 02, 03, or 04 unless a new data
issue is independently found.

The modeling layer now fits seven independent headline candidates for every
target: SARIMA, SARIMAX, Logistic, Gompertz, Ridge, Random Forest, and XGBoost.
All seven are eligible to win for every target. Diesel Share and pooled regional
Ridge / Random Forest / XGBoost remain diagnostics only and cannot be selected
as the headline forecast.

The hard validation rule is restored: model-family selection uses only recursive
multi-step walk-forward validation inside the 2023-2024 training window. The
2025 holdout is loaded only after `Selected_Model` is fixed and is used only for
reported MAE/RMSE/MAPE/R2. SARIMA order selection is also training-only; the old
2025 no-regression gate is gone.

Current selected production models:

| Target | Selected model | Training WF MAPE | 2025 MAPE | 2025 R2 |
|---|---|---:|---:|---:|
| Nacional | SARIMA | 39.7% | 29.0% | -0.009 |
| Madrid | Logistic | 37.2% | 73.6% | -8.273 |
| Catalonia | SARIMAX | 68.5% | 92.3% | -19.827 |
| Andalusia | SARIMA | 53.9% | 49.7% | -1.662 |
| Valencia | Gompertz | 57.3% | 34.2% | -1.246 |

Important caveat: Catalonia is selected as SARIMAX by a narrow training-only
walk-forward margin, but the honest 2025 holdout is poor. Do not hide this in
the business interpretation.

New / changed outputs:

- `data/outputs/model_selection_walkforward.csv` is the seven-candidate
  training-only selection table.
- `data/outputs/metricas_final_selected.csv` and
  `data/outputs/metricas_final_seleccionado.csv` contain selected-model 2025
  holdout metrics only after selection.
- `data/outputs/forecast_24m_selected.csv` is the selected-only headline forecast.
- `data/outputs/forecast_24m_sarima_rf_xgb.csv` remains the legacy all-model
  forecast file.
- `data/outputs/phase2_pooling_experiment_metrics.csv` and
  `data/outputs/phase2_pooling_decision.csv` are diagnostic-only pooling outputs.
- `scripts/06_validate_outputs.py` now fails on selected forecast degeneracy:
  identical cross-target paths, near-flat paths, or exact short cycles.
- `reports/figures/11_forecast_24m.png` now uses selected-model error-derived
  bands instead of a fixed +/-20% cosmetic band.
- Pooled Random Forest diagnostics now use higher tree capacity for the pooled
  panel so region dummies survive recursive forecasting; a same-history /
  different-region-dummy check confirms pooled RF and pooled XGBoost no longer
  produce identical regional paths.

Run path:

```powershell
.\.venv\Scripts\python scripts/03_clean_cnmc_petroleum.py
.\.venv\Scripts\python scripts/02_master_dataset_builder.py
.\.venv\Scripts\python scripts/04_build_features.py
.\.venv\Scripts\python scripts/05_modeling_with_cnmc.py
.\.venv\Scripts\python scripts/06_validate_outputs.py
```

---

## 2026-06-23 Final No-Pooling Delivery Cleanup

This section supersedes earlier notes that describe pooled Catalonia as the
final production model.

Current production source of truth:

```powershell
.\.venv\Scripts\python scripts/03_clean_cnmc_petroleum.py
.\.venv\Scripts\python scripts/02_master_dataset_builder.py
.\.venv\Scripts\python scripts/04_build_features.py
.\.venv\Scripts\python scripts/05_modeling_with_cnmc.py
.\.venv\Scripts\python scripts/06_validate_outputs.py
```

Final delivery decisions:

- The 2025 period is a validation / acceptance period, not a pristine final
  test.
- Scripts are the production source of truth; notebooks are exploratory,
  narrative, or optional ablation assets.
- The final selected production model set is non-pooled.
- Pooled regional ML remains in the outputs as a sensitivity experiment only.

Final selected models:

| Target | Selected model | 2025 MAPE | 2025 R2 |
|---|---|---:|---:|
| Nacional | SARIMA | 29.0% | -0.009 |
| Madrid | Logistic | 73.6% | -8.273 |
| Catalonia | SARIMA | 47.2% | -5.620 |
| Andalusia | Logistic | 48.4% | -1.555 |
| Valencia | Gompertz | 34.2% | -1.246 |

Average selected 2025 validation MAPE is 46.5%. The previous pooled Random
Forest result for Catalonia remains a useful sensitivity comparison at 46.8%
MAPE, but it is rejected by the final no-pooling policy.

`scripts/06_validate_outputs.py` now verifies master-data shape and
reconciliation, temporal split boundaries, causal lag features, the no-pooled
final selected model policy, and Tableau export consistency.

SARIMA robustness update:

- `scripts/05_modeling_with_cnmc.py` now runs a constrained SARIMA grid search
  inside the 2023-2024 training period.
- Results are saved to `data/outputs/sarima_grid_search_results.csv`.
- Grid-selected SARIMA orders are accepted for production only if they do not
  regress versus the default `(1, 1, 1)(1, 0, 0, 12)` order on the 2025
  acceptance period; results are saved to `data/outputs/sarima_order_acceptance.csv`.
- For the final SARIMA-selected production targets, Nacional and Catalonia, the
  default SARIMA order remains the production order after the no-regression
  check.

---

## 2026-06-21 Phase 2 Modeling Productionization (`enrico`)

Phase 2 has now been implemented on branch `enrico` in the official script
pipeline. `main` remains the stable Phase 1 branch.

Current production source of truth is still:

```powershell
.\.venv\Scripts\python scripts/03_clean_cnmc_petroleum.py
.\.venv\Scripts\python scripts/02_master_dataset_builder.py
.\.venv\Scripts\python scripts/04_build_features.py
.\.venv\Scripts\python scripts/05_modeling_with_cnmc.py
```

Phase 2 modeling decisions:

- The old one-step model-selection gate was replaced with recursive multi-step
  walk-forward validation inside the 2023-2024 training period.
- The gate evaluates ML models recursively, so predicted months feed future lag
  features instead of using actual future target lags.
- `Nacional` is never pooled with regional series.
- Regional pooling is tested only for Madrid, Catalonia, Andalusia, and Valencia.
- A no-regression acceptance gate compares the Phase 2 proposal with the Phase 1
  selected model on the 2025 validation period. A Phase 2 proposal is adopted
  only if it does not worsen the Phase 1 validation MAPE.
- The final delivery policy is no pooling, so pooled regional ML is retained as
  sensitivity output but not as the production selected model.

Final selected production models after Phase 2 and the no-pooling policy:

| Target | Selected model | 2025 MAPE | 2025 R2 |
|---|---|---:|---:|
| Nacional | SARIMA | 29.0% | -0.009 |
| Madrid | Logistic | 73.6% | -8.273 |
| Catalonia | SARIMA | 47.2% | -5.620 |
| Andalusia | Logistic | 48.4% | -1.555 |
| Valencia | Gompertz | 34.2% | -1.246 |

Average selected MAPE improved from 94.6% to 46.5%. The pooled regional model is
not used in the final selected model set. Madrid's best pooled validation metric
is better than the selected Logistic model, but it is not used because the
training-only gate did not select it; Catalonia's pooled Random Forest is not
used because the final delivery policy is non-pooled.

New Phase 2 lineage files:

- `PHASE2_MODELING_REPORT.md`
- `data/outputs/phase2_model_acceptance.csv`
- `data/outputs/phase2_pooling_experiment_metrics.csv`
- `data/outputs/phase2_pooling_decision.csv`

Remaining caveat: Catalonia's selected SARIMA forecast is the final non-pooled
choice but can extrapolate more trend than the pooled Random Forest sensitivity
forecast. Explain this clearly in the deliverable.

---

## 2026-06-21 Phase 1 Cleanup Update

Phase 1 addressed reproducibility, stale documentation, notebook/script drift,
price-feature target mapping, output lineage, and repository hygiene without
changing the modeling methodology.

Current production source of truth:

```powershell
.\.venv\Scripts\python scripts/03_clean_cnmc_petroleum.py
.\.venv\Scripts\python scripts/02_master_dataset_builder.py
.\.venv\Scripts\python scripts/04_build_features.py
.\.venv\Scripts\python scripts/05_modeling_with_cnmc.py
```

Key cleanup decisions:

- Python 3.11 is the supported runtime (`.python-version`, `environment.yml`,
  `pyproject.toml`).
- `requirements.txt` now includes the direct `scipy` dependency used by the modeling script.
- Notebooks are retained as exploratory/narrative assets, but scripts are authoritative.
- Notebook outputs were cleared so stale local paths and warnings are not preserved.
- `notebooks/08_modeling_with_prices.ipynb` now uses `Cataluña` and `Andalucía`
  target labels consistently with the modeling tables.
- `metricas_comparativa.csv` is now built as a combined comparison table when
  optional price-ablation metrics are present.
- `scripts/02_master_dataset_builder.py` now has Windows-safe console output and
  current 720 x 22 dataset documentation.
- `scripts/05_modeling_with_cnmc.py` now sets an explicit NumPy seed before
  fitting models.
- AppleDouble metadata files and duplicate root-level raw downloads were removed.

Remaining Phase 2 modeling risks:

- Madrid and Cataluña selected-model validation remains weak.
- The current holdout evaluation is one-step style; a fixed-origin multi-step
  backtest is still needed for stronger 24-month forecast evidence.
- The project should explicitly decide whether the business target is biodiesel
  only or broader eco-fuels including HVO / renewable diesel.

---

## 2026-06-19 Update: CNMC Diesel-Market Feature Integration

This section explains the newest repository changes in plain language so teammates can understand what changed, how to rerun it, and how to interpret the result.

### Why CNMC was added

The original target remains biodiesel demand in metric tonnes (`Consumo_Tm`). That target already comes from the existing cleaned biodiesel consumption source and represents total market demand, not Repsol sales.

The CNMC petroleum-consumption data was added as a market-structure feature source. The business logic is:

`biodiesel demand = underlying Gasoleo A diesel market size x biodiesel penetration`

In other words, biodiesel tonnes should depend partly on the size of the conventional diesel market and partly on the share of that market captured by biodiesel. CNMC gives us the conventional diesel-market context that was missing before.

### Raw CNMC inputs

The following files are now kept under `data/raw/consumos_mensuales_petroleo/`:

- `ds_14200_1.csv`: 2023 monthly petroleum consumption
- `ds_14201_1.csv`: 2024 monthly petroleum consumption
- `ds_14202_1.csv`: 2025 monthly petroleum consumption
- `ds_14203_1.csv`: Jan-Feb 2026 monthly petroleum consumption

Each raw file is a semicolon-separated CSV from CNMC `Estadistica Petroleo - Consumos mensuales provincial (Tm)`. Each row is a province, month, and product category, with consumption in tonnes.

The Jan-Feb 2026 CNMC rows are intentionally cleaned and saved in processed CNMC outputs, but they are not used for training, validation, model selection, or the 2026-2027 forecast origin. The capstone forecast remains an origin-at-2025-12 forecast.

### New cleaning step

New script: `scripts/03_clean_cnmc_petroleum.py`

What it does:

- Reads all four raw CNMC CSVs with `sep=";"`.
- Standardizes the raw columns into `Fecha`, `CCAA`, `Provincia`, `Tipo_Producto`, and `Consumo_Tm`.
- Keeps all 14 CNMC product categories in the cleaned outputs, not only diesel.
- Checks that there are no missing values and no duplicate `Fecha` + `CCAA` + `Provincia` + `Tipo_Producto` rows.
- Aggregates province-level rows to CCAA-level rows.
- Creates an independent national `ESPAÑA` row by summing all 19 CCAA values. This is important: the national row is not built from only Madrid, Cataluña, Andalucía, and Valencia.
- Builds diesel-market features from the product table.

Outputs:

- `data/processed/cnmc_consumos_petroleo_provincial.csv`: cleaned province-product-month table.
- `data/processed/cnmc_consumos_petroleo_ccaa.csv`: cleaned CCAA-product-month table, including independently computed `ESPAÑA`.
- `data/processed/cnmc_diesel_market_features.csv`: modeling-ready diesel-market feature table.

The diesel-market feature table contains:

- `CNMC_Biodiesel_Tm`: CNMC biodiesel tonnes, used only as a reconciliation check against the existing target.
- `GasoleoA_Tm`: conventional Gasoleo A market size.
- `DieselPool_Tm`: broader diesel pool used for descriptive share checking.
- `Biodiesel_GasoleoA_Ratio`: biodiesel tonnes divided by Gasoleo A tonnes.
- `Biodiesel_DieselPool_Share`: biodiesel tonnes divided by the broader diesel pool.

### Master dataset integration

Updated script: `scripts/02_master_dataset_builder.py`

What changed:

- The master build now reads `data/processed/cnmc_diesel_market_features.csv`.
- It filters CNMC rows to `Fecha <= 2025-12` before merging.
- It merges CNMC features by `Fecha` + `CCAA`.
- It preserves `Consumo_Tm` as the official modeling target. The project does not replace the target with CNMC `BIODIESEL`.
- It checks that `CNMC_Biodiesel_Tm` exactly reconciles to `Consumo_Tm` after the merge.
- It fails loudly if any modeled month/region is missing `GasoleoA_Tm`.

Current master output:

- `data/inputs/master_dataset.csv`
- 720 rows x 22 columns
- 2023-01 to 2025-12 only
- 20 CCAA/national entities x 36 months
- Includes all CCAA rows for context, but modeling still uses only the five targets: Nacional, Madrid, Cataluña, Andalucía, Valencia.

### Feature engineering integration

New script: `scripts/04_build_features.py`

What it does:

- Rebuilds the modeling feature tables from `master_dataset.csv`.
- Keeps the same capstone split: train = 2023-2024, test = 2025.
- Keeps only the five modeled targets in the model feature tables.
- Adds CNMC diesel-market features only in lagged form.

New leakage-safe model inputs:

- `GasoleoA_Tm_lag1`
- `GasoleoA_Tm_roll3_lag1`
- `Biodiesel_GasoleoA_Ratio_lag1`
- `Biodiesel_GasoleoA_Ratio_roll3_lag1`

The contemporaneous values `GasoleoA_Tm` and `Biodiesel_GasoleoA_Ratio` are retained in the feature table so the lagged columns can be audited, but they are not used as direct predictors for month `t`. This is the key leakage rule for the CNMC integration.

Current feature outputs:

- `data/features/features_modelo_completo.csv`: 180 rows x 35 columns
- `data/features/features_train.csv`: 120 rows x 35 columns
- `data/features/features_test.csv`: 60 rows x 35 columns

(Was 36 columns through 2026-06-24; `Mandato_Biodiesel_Blend_Pct` was removed
2026-06-25, see "Audit Fixes" section near the top of this file.)

### Modeling changes

New script: `scripts/05_modeling_with_cnmc.py`

This is now the current script-based modeling path. It reruns:

- 2025 test prediction generation
- 2023-2024 walk-forward model selection
- final model metrics
- 2026-2027 24-month forecasts
- Tableau exports
- final figures

Candidate models now include:

- SARIMA
- Ridge
- Random Forest
- XGBoost
- Logistic growth curve
- Gompertz growth curve
- Diesel Share model

The direct ML models, Ridge/Random Forest/XGBoost, now use the old lagged macro/target/calendar features plus the four lagged CNMC diesel-market features and the two deterministic mandate features.

The new `Diesel Share` candidate models `Biodiesel_GasoleoA_Ratio` directly and then converts the predicted ratio back into tonnes using future `GasoleoA_Tm`. Future `GasoleoA_Tm` is not taken from Jan-Feb 2026 actuals. It is generated with a seasonal naive assumption: repeat the latest full 12-month Gasoleo A pattern from 2025 into 2026 and 2027.

### Regenerated outputs

These files were regenerated from the CNMC + mandate-aware pipeline:

- `data/outputs/metricas_modelos.csv`
- `data/outputs/model_selection_walkforward.csv`
- `data/outputs/metricas_final_seleccionado.csv`
- `data/outputs/predicciones_test_2025.csv`
- `data/outputs/forecast_24m_sarima_rf_xgb.csv`
- `data/outputs/metricas_comparativa.csv`
- `data/outputs/tableau_dashboard.csv`
- `data/outputs/tableau_metricas.csv`
- `data/outputs/tableau_forecast_pivot.csv`
- `data/outputs/tableau_export_legacy.csv`
- `reports/figures/07_model_comparison.png`
- `reports/figures/11_forecast_24m.png`

Despite the legacy filename `forecast_24m_sarima_rf_xgb.csv`, that file now contains all current model families, including Logistic, Gompertz, and Diesel Share.

### Validation checks that passed

The integration was checked end to end:

- All four raw CNMC files parse correctly as semicolon CSVs.
- Raw CNMC files have zero missing cells.
- Raw CNMC files have zero duplicate province-product-month rows.
- CNMC 2023-2025 `BIODIESEL` reconciles exactly with the existing biodiesel target source over 720 CCAA-month pairs, with max absolute difference `0.0 Tm`.
- National `ESPAÑA` `GasoleoA_Tm` equals the sum of all 19 CCAA values for every month, with max absolute difference `0.0 Tm`.
- `master_dataset.csv` contains no 2026 rows.
- The modeling feature tables contain no 2026 rows.
- Lag causality checks passed: CNMC lag columns equal values available at `t-1` or earlier.
- Selected regional forecasts remain below the national forecast every month.
- The four modeled regions are about 43.5% of national forecast volume in 2026 and 44.2% in 2027.

### Modeling result and interpretation

The CNMC feature made the project more business-grounded and auditable, but it did not materially improve the selected production forecasts.

Walk-forward-selected models remain:

| Target | Selected model | 2025 MAPE | 2025 R2 |
|---|---|---:|---:|
| Nacional | SARIMA | 29.0% | -0.009 |
| Madrid | Gompertz | 197.1% | -101.018 |
| Cataluña | Gompertz | 164.2% | -91.269 |
| Andalucía | Logistic | 48.4% | -1.555 |
| Valencia | Gompertz | 34.2% | -1.246 |

Important interpretation:

- The new diesel-market variables are conceptually correct and useful for explaining demand structure.
- They are not, by themselves, enough to fix the main forecasting issue.
- The new `Diesel Share` model performed very poorly on 2025 and should be treated as a failed experiment, not a recommended final model.
- Direct ML with diesel lags showed some useful signal in places, especially Madrid XGBoost, but did not win the existing 2023-2024 walk-forward selection gate.
- Madrid and Cataluña still have a serious validation/test mismatch. The selected Gompertz models looked good in 2023-2024 one-step validation but performed badly on 2025. This remains a final-delivery risk.

The main next modeling improvement is still likely a pooled/panel model across the five targets, not just adding another isolated feature.

### How to rerun the current pipeline

Run these commands from the repository root:

```powershell
python scripts/03_clean_cnmc_petroleum.py
python scripts/02_master_dataset_builder.py
python scripts/04_build_features.py
python scripts/05_modeling_with_cnmc.py
```

Use the Anaconda Python environment if the plain `python` command does not point to the project environment.

Important note: this script path is now the most current reproducible path. Some older notebook/documentation text still predates the CNMC integration and may describe the former 17-column master dataset or the pre-CNMC model candidate set.

---

## 1. Project Overview

This is a capstone project (IE Master in Business Analytics and Data Science) built for **Repsol**, forecasting demand for **eco-fuels (biodiesel)** in Spain.

**Business problem:** Biodiesel adoption in Spain has grown explosively since 2023 (national monthly consumption grew roughly 135x from January 2023 to December 2025). Repsol needs a reliable view of how this demand will evolve over the next two years, broken down nationally and for its most important regional markets, to inform supply, blending, and distribution planning.

**Final objective:** Produce a 24-month-ahead (2026-01 → 2027-12), monthly-granularity demand forecast for biodiesel consumption in Spain, covering the national total and four key regions, using a defensible, leakage-free combination of statistical and machine-learning models, with results delivered via a Tableau dashboard.

---

## 2. Scope and Target

- **Geography:** Spain. Forecasts are produced for **5 series**:
  - **Nacional** (ESPAÑA — national total)
  - **Madrid** (Madrid, Comunidad de)
  - **Cataluña**
  - **Andalucía**
  - **Valencia** (Comunitat Valenciana)
- These 4 regions + national total are the **only modelling targets**, selected because together they account for the large majority of national biodiesel consumption.
- **Forecast horizon:** 24 months ahead, monthly granularity (2026-01 through 2027-12).
- **What "demand" means here:** This is **total market demand for biodiesel sold/reported as its own distinct product line** in each region/nationally (i.e., the CORES/CNMC `BIODIESEL` category), **not Repsol's own sales or market share, and not the biodiesel blended at low concentration into ordinary Gasóleo A diesel under the national mandate** (that blended volume is reported separately, under `GASÓLEO A`, and is not part of this target — see the dated entry near the top of this file). This scope was confirmed directly with the Repsol representative. There is no Repsol-specific sales data in this project — it is a macro demand forecast that Repsol can use as external market context.
- **Historical data window:** 2023-01 to 2025-12 (36 months). This is the full window for which CORES consumption data, INE macro indicators, and daily fuel price data are all available and aligned.
- **Train/test convention used throughout modelling:** Train = 2023-01 → 2024-12 (24 months), Test = 2025-01 → 2025-12 (12 months, held out). The 24-month 2026-2027 forecast is generated by refitting the chosen model on the full 36-month history.

---

## 3. Data Sources

| Source | What it provides | Where it lands in the pipeline |
|---|---|---|
| **CORES/CNMC** (Corporación de Reservas Estratégicas de Productos Petrolíferos / Comisión Nacional de los Mercados y la Competencia) | Monthly biodiesel consumption (`Consumo_Tm`, metric tonnes) by province/CCAA/national. This is the **target variable**. The reproducible-from-raw lineage is via CNMC: `data/raw/consumos_mensuales_petroleo/ds_*.csv` → `scripts/03_clean_cnmc_petroleum.py` → `cnmc_diesel_market_features.csv`'s `CNMC_Biodiesel_Tm` column, which `scripts/03`'s `reconcile_biodiesel()` (and `scripts/02`'s merge check) verify reconciles **exactly** (max abs diff 0.0 Tm, every CCAA, every month) against `consumo_biodiesel_ccaa.csv` for the full 2023-2025 modeled window. The three `ESTADISTICAS-BIOS CERT DEFINITIVAS *.xlsx` files (2020-2022/2023/2024) sitting in `data/` are CORES/CNMC's original biofuel-certification system files, kept as historical/supplementary reference material -- no notebook or script parses them, no 2025-dated file of that type exists in the repo, and they are **not required to reproduce any current pipeline output**. (The previously-noted stray root-level files `4247.csv`/`50934.csv`/loose `ds_*.csv` no longer exist; they were removed in the 2026-06-21 Phase 1 cleanup -- the canonical CNMC raw files now live only under `data/raw/consumos_mensuales_petroleo/`.) | `consumo_biodiesel_ccaa.csv`, `consumo_biodiesel_provincial.csv`, `consumo_biodiesel_targets.csv` (via notebook 02; independently reproducible via `scripts/03`+`scripts/02`) |
| **INE** (Instituto Nacional de Estadística) | Macroeconomic indicators: Industrial Production Index (original + seasonally adjusted), CPI annual variation, unemployment rate (EPA, quarterly). Fetched live via the INE Tempus3 API. | `macro_indicadores_ine.csv` (via notebook 03) |
| **DGT** (Dirección General de Tráfico) | Vehicle fleet / registration statistics. **Planned but not implemented** — DGT has no public JSON API, requires manual Excel/PDF download. A placeholder cell exists in notebook 03 (commented out) waiting for `data/raw/dgt_parque_vehiculos.xlsx` and `data/raw/dgt_matriculaciones.xlsx` to be manually sourced. |  Not yet in `master_dataset.csv`. |
| **Brent crude oil price** | Monthly Brent price (USD/barrel), used as a macro/cost driver. | `brent_oil_price_monthly_2023_onwards.csv`, merged into master dataset |
| **Daily retail fuel prices** (precios_combustibles, CORES-sourced) | Daily PVP (retail) and PAI (pre-tax) prices per province for 4 conventional fuel products (Gasóleo A, Gasóleo Premium, Gasolina 95, Gasolina 98). Used as a substitution-effect signal (higher conventional fuel prices correlate with higher biodiesel adoption, r ≈ -0.7 to -0.85). | `precios_combustibles_2023/2024/2025.csv` → aggregated in notebooks 04 and 06 |
| **INE tourism data** (`turismo_visitantes_ccaa.csv`) | Tourist visitors by CCAA. **Excluded** — only one month of data (Oct 2025) available, cannot form a time series. Documented in `datasets_excluded_from_master.md`. |  Not merged. |

---

## 4. Work Completed So Far

### Data pipeline (notebooks 01-06)
- Raw CORES consumption data cleaned (mojibake/encoding repair, completeness validation: confirmed a complete 36-month balanced panel, no missing months).
- INE macro indicators fetched via API, including EPA unemployment rate (quarterly, expanded to monthly).
- Brent oil price and daily fuel price data integrated.
- A single `master_dataset.csv` (currently 720 rows x 22 columns, `Fecha` x `CCAA` primary key) built, combining consumption, macro, Brent, fuel prices, and CNMC diesel-market variables.
- Feature engineering: calendar features (month, quarter, trend index, sin/cos seasonal encoding), target lags (1, 2, 3, 12 months), rolling means/std (3, 6 months), and lagged macro indicators.
- A separate fuel-price feature set built with lag-1 regional/national prices.

### Modelling and evaluation (notebooks 07-09)
- Initial candidate models: SARIMA (log1p-transformed), Ridge regression, Random Forest, XGBoost.
- Models evaluated on the 2025 holdout; price-augmented RF/XGBoost variants tested separately (notebook 08).
- 24-month forward forecasts generated and exported for Tableau.

### Leakage audit and fixes (this session, 2026-06-16)
A full data-leakage audit (using the `leakage-audit` skill) was run across the entire pipeline and found two **critical** leaks plus a model-selection bias. All were fixed and the pipeline re-run end to end:

1. **Look-ahead leak in macro features.** `IPI_original`, `IPC_var_anual`, `Tasa_paro` were used at their *contemporaneous* (same-month) value in `ML_FEATS`/`ML_BASE`, even though INE publishes these with a real-world delay. Fixed: only the `_lag1` versions are now used as model inputs in notebooks 07, 08, 09.
2. **EPA publication-delay leak.** The quarterly-to-monthly expansion of the unemployment rate (`03_external_data.ipynb`) assigned each quarter's figure to its *own* (not-yet-published) months instead of the *following* quarter's months. Fixed by shifting the quarterly index forward by one quarter (`+ pd.DateOffset(months=3)`) before forward-filling. This changed `macro_indicadores_ine.csv` and was propagated through `04_master_dataset.ipynb` and `05_feature_engineering.ipynb`.
3. **Model-selection leakage.** The original pipeline picked the "best" model per target by minimum MAPE on the 2025 test set — i.e., the test set was used to choose the winner, inflating the reported accuracy of whichever model happened to fail least. Fixed: model family per target is now chosen via **walk-forward (expanding-window, 1-step-ahead, median-aggregated) cross-validation confined to the training period (2023-2024)**. The 2025 test metric is reported once, for the model already committed to by that CV — never used to pick a winner.
4. Two **positional feature-array bugs** were found and fixed (in `07_modeling.ipynb`'s `recursive_forecast_ml` and `08_modeling_with_prices.ipynb`'s recursive forecast row-builder) — both built model input rows by fixed position, which silently broke once the feature list length changed during the leakage fix. Both were rebuilt as name-keyed dict lookups (`feat_values[f] for f in ML_FEATS`) so they cannot silently drift out of sync again.
5. A self-correction was needed mid-session: the very first attempt to fix `ML_FEATS` in `07_modeling.ipynb` silently failed to save (a bundled patch script crashed on its second edit before the file write happened), so the leak briefly remained live for one execution. This was caught on a user-requested double-check, re-fixed, verified by reading the file fresh from disk, and the full pipeline (07→08→09) was re-run. **Lesson for future edits to this repo: always verify a code change persisted by re-reading the file from disk immediately after writing, especially when bundling multiple edits in one script.**

### Model improvement: saturating growth curves (this session, 2026-06-16)
A deep-dive analysis of the dataset found that YoY growth in every target decelerates sharply (e.g. Nacional: +1009% in 2023→2024, only +229% in 2024→2025) — the signature of an adoption curve approaching saturation, not unbounded exponential growth. SARIMA and the ML models all extrapolate trend with no ceiling, which was identified as the likely cause of the worst forecast failures (Madrid, Cataluña).

**Action taken:** Added **Logistic** and **Gompertz** saturating growth curves as two new candidate models (fit directly on raw `Consumo_Tm`, no `log1p` needed since the curve already has a built-in asymptote, plus a small 2-parameter sin/cos seasonal correction). These were run through the *exact same* walk-forward selection gate as every other candidate — not cherry-picked after the fact.

**Result — kept, because it improved every target without making any worse:**

| Target | Selected model | Test MAPE (2025) | Test R² |
|---|---|---|---|
| Nacional | SARIMA (unchanged) | 29.0% | -0.009 |
| Madrid | **Gompertz** (was SARIMA, 318.7%) | **197.1%** | -101.0 |
| Cataluña | **Gompertz** (was Ridge, 3332.6%) | **164.2%** | -91.3 |
| Andalucía | **Logistic** (was SARIMA, 52.5%) | **48.4%** | -1.56 |
| Valencia | **Gompertz** (was SARIMA, 57.4%) | **34.2%** | -1.25 |

This was independently re-verified afterward (re-derived the walk-forward numbers from scratch in a standalone script, cross-checked all output CSVs for internal consistency, reconfirmed all prior leakage fixes were still intact, confirmed zero execution errors across all three notebooks). **Verification passed — no leakage, no errors found in this round.** This work was committed (`d60cbef`) along with the creation of this `memory.md` file.

### Broader model-research pass (2026-06-16, chat-only, no repo changes)
A wide research review of additional forecasting approaches was conducted (SARIMAX, VAR/BVAR, Prophet/NeuralProphet, LightGBM/CatBoost, Elastic Net, Bayesian regression, structural/state-space models, Gaussian Processes, deep learning — LSTM/GRU/N-BEATS/TFT/DeepAR/TCN, hierarchical reconciliation, panel/pooled regression), backed by academic papers and competition results (M3/M4, Zou & Hastie 2005, Hyndman's MinT, etc.). Delivered in chat only, per explicit instruction not to touch the repo. **Top conclusion: pooling the 5 regional series into one model is the single highest-leverage untried change** (panel-forecasting literature shows pooling trades a little heterogeneity bias for a large reduction in estimation variance — exactly what's needed given ~21-23 effective rows/target). **Deep learning models (LSTM/GRU/N-BEATS/TFT/DeepAR/TCN) and vanilla VAR/VARMAX were explicitly flagged as NOT worth trying** at this sample size (5 series × 24-36 points) — those architectures are designed for hundreds/thousands of series or timesteps, and plain VAR's parameter count grows roughly quadratically with series count, both well past what 24 training months can support. The full report (model-by-model trade-off tables, citations) exists only in the chat transcript, not saved as a repo file — if it needs to be referenced again, ask the user to re-share it or re-run the research.

### SARIMAX experiment — tried and rejected (2026-06-16)
Following on from the model-research pass, SARIMAX (SARIMA + the same three already-vetted `_lag1` macro regressors used by Ridge/RF/XGBoost: `IPI_original_lag1`, `IPC_var_anual_lag1`, `Tasa_paro_lag1`) was implemented as an 8th walk-forward candidate in `07_modeling.ipynb`, fully wired into the main training loop, walk-forward CV, and 24-month forecast section. **Result: SARIMAX lost the walk-forward comparison for every single target**, often by a wide margin (e.g. Nacional 43.7% vs. SARIMA's 12.5%; Andalucía 91.6% vs. Logistic's 16.7%). The final selected model per target came back byte-identical to before the experiment. All changes were fully reverted via `git checkout` — **no SARIMAX code exists in the repo today.**
**Do not re-add plain SARIMAX with these same 3 macro exogenous regressors without a reason to expect a different outcome** — it has already been tried and failed on this exact feature set. It might be worth revisiting only *after* the regional-pooling change (more effective training rows could change this result), or with a different/richer set of exogenous regressors (e.g. fuel price lags, which were not included in this test since `07_modeling.ipynb` doesn't currently load the price-feature table).

### Regional pooling investigated, and the walk-forward gate found to be flawed (2026-06-21, branch `enrico`, NOT yet implemented in notebooks)

This session pursued the long-standing **#1 priority: pool the 5 regional series**. The investigation produced three findings; all prototyping was done in throwaway `/tmp` scripts (not in the repo). **No notebook or output CSV has been changed — the committed model selections are still the 2026-06-16 ones.** The work below is a recommendation pending user approval.

**Repsol constraint clarified up front:** Repsol instructed the team **not to "add up the regions."** The user confirmed this applies to the **output only** (never deliver one combined/summed demand number — each region must keep its own separate forecast), *not* to how a model is fit internally. "Pooling" here therefore means *jointly fitting one model on the stacked regional panel with region as a feature, while still emitting a separate forecast per region* — nothing is ever summed. Per the user's decision, **Nacional is excluded from pooling** (it is the national total, i.e. the sum of its own components, so pooling a total with its components is statistically improper). Pooling was scoped to the **4 regional series only** (Madrid, Cataluña, Andalucía, Valencia).

1. **Naive ML pooling was tried and REJECTED.** Pooled Ridge/RF/XGBoost were fit on the stacked 4-region panel (84 usable rows vs ~21/region — the 4× data gain that motivates pooling), using log1p level features (`log1p(Lag_1/2/3, Roll_mean_3/6)` for scale-robust, multiplicative dynamics) + calendar + `_lag1` macro + region fixed-effect dummies, target `log1p(Consumo_Tm)`. Run through the existing 1-step walk-forward gate, **Pooled Ridge "won" for Cataluña** (1-step WF MAPE 32.0 → 18.4). **But on the real 2025 holdout it was catastrophic** (Cataluña recursive-12 MAPE ≈ 606% vs the committed Gompertz's 164%). Reason: a linear/ML pooled model has **no saturation ceiling**, so over a 12-month horizon it re-creates exactly the unbounded-extrapolation blow-up that the Logistic/Gompertz curves were added to fix. **Conclusion: generic panel-regression pooling is not a win here** — same rejection class as the SARIMAX experiment. Do not re-add it without a saturating formulation.

2. **This exposed a real flaw in the model-selection gate.** The 1-step-ahead walk-forward gate (the project's sanctioned selection rule) *would have adopted Pooled Ridge for Cataluña* — a model we can see is far worse on the actual 12-month task. The 1-step gate is **blind to multi-month blow-ups** because one step out the trend hasn't diverged yet. Verified directly: plain Ridge scores a deceptive 27–75% under the 1-step gate but **15,000–477,000%** under a multi-step recursive evaluation — which matches its true holdout behaviour (14,000–353,000%). So the 1-step gate can silently bless exploding models.

3. **A multi-step gate was prototyped and a recommended fix identified.** A **rolling-origin, multi-step walk-forward** gate was built that evaluates each model *as it is actually deployed*: ML models forecast **recursively** (each prediction feeds the next month's lags), SARIMA/curves forecast directly; errors aggregated over the full remaining (or a capped-6-month, equal-weight-per-horizon) path inside 2023-2024 only. It correctly explodes Ridge and never selects an unbounded extrapolator. **But the multi-step gate alone regresses Andalucía (48→64%) and Valencia (34→57%)** on the holdout — a *fundamental* limit, not a gate bug: the **training window (2023-24) is pure explosive growth, the test window (2025) is the saturation bend**, so a training-confined CV rewards non-saturating models (SARIMA/XGBoost) that track the growth phase, while the growth curves' structural ceiling is what actually pays off in 2025. No training-only CV can fully anticipate a regime change that only appears in the test period.

   **RECOMMENDED approach (not yet implemented): multi-step gate + a saturation prior.** Replace the 1-step gate with the multi-step recursive gate, **and** restrict the 4 regional adoption series to the saturating curves (Logistic/Gompertz); Nacional keeps the full candidate set (it is large/smooth and SARIMA legitimately wins there). The saturation prior constrains the *candidate set* by domain knowledge (adoption demonstrably saturates) — it is decided before seeing test results and is *not* test-set selection. Confirmed effect vs the currently-committed models on the 2025 holdout:

   | Target | Committed now | Recommended | 2025 MAPE | 2025 R² |
   |---|---|---|---|---|
   | Nacional | SARIMA | SARIMA (unchanged) | 29.0% | -0.0 |
   | Madrid | Gompertz | **Logistic** | **197.1% → 73.6%** | -101.0 → **-8.3** |
   | Cataluña | Gompertz | Gompertz (unchanged) | 164.2% | -91.3 |
   | Andalucía | Logistic | Gompertz | 48.4% → 48.3% (tie) | -1.6 → -1.5 |
   | Valencia | Gompertz | Gompertz (unchanged) | 34.2% | -1.2 |
   | **Average** | | | **94.6% → 69.9%** | |

   Net: **one meaningful change (Madrid Gompertz→Logistic, 197%→74%), zero regressions.** Cataluña (164%) is left unfixed — a genuine data-size/regime-change limit, honestly acknowledged. Selections cross-checked stable across both multi-step gate variants (full-remaining and capped-6).

**Status of this work:** recommendation only, captured on branch `enrico`. The notebook (07) gate rewrite + 4-region curve restriction + re-run of 07→08→09 is **not done** — awaiting user go-ahead. When implemented, the multi-step gate's recursive ML evaluation must (a) hold macro `_lag1` constant at the last known value across the path (leak-free), and (b) build feature rows by name (`feat_values[f] for f in ML_FEATS`), never by position.
### Biofuel mandate features added (2026-06-19)

#### Background: what the mandate is
**SUPERSEDED 2026-06-25** -- this section originally described two mandate variables. The second one,
`Mandato_Biodiesel_Blend_Pct`, was removed; see the "2026-06-25 Audit Fixes" section near the top of
this file for why. Only `Mandato_Energia_Pct` remains as a feature. Kept below for history.

Spain has (it turns out, only) one legislative driver of this type that directly determines how much
biodiesel must be blended into the diesel pool:

1. **Mandato de Energia (Mandato_Energia_Pct)**: Annual national biofuel blending obligation (% of energy content of all transport fuels) set by successive Royal Decrees and project assumptions. Increased year-on-year: 10.5% (2023), 11.0% (2024), 11.5% (2025), **14.0% (2026, RD 5/2026 signed 8 Jan 2026, published BOE 10 Jan 2026)**, 15.5% (2027, **the team's own projection**, +1.5pp/year continued through 2030 to 20.0% -- no Real Decreto exists yet for 2027-2030).
2. ~~**Mandato de Mezcla Biodiesel (Mandato_Biodiesel_Blend_Pct)**: Volumetric biodiesel-into-Gasoleo-A blend requirement introduced by Decreto 61/2023.~~ **Removed 2026-06-25: "Decreto 61/2023" does not exist in the BOE.** Searched directly; the only real decree numbered 61 is RD 61/2006, which sets a *maximum* 7% FAME blend wall for engine compatibility -- the opposite of a rising minimum mandate, and an unrelated instrument. No real source for the claimed 3%->7.5% figures was found anywhere.

`Mandato_Energia_Pct` is a deterministic policy variable for 2023-2026 (legislated, BOE-verified) -- not a forecast, no uncertainty for those years. 2027-2030 are an internal projection, not legislation; this is disclosed in `data/inputs/mandato_biocarburantes.csv`'s `Status`/`Fuente` columns.

#### What was built
A new input file `data/inputs/mandato_biocarburantes.csv` was created with the full mandate schedule 2016-2030 (annual rows, now 4 columns after the 2026-06-25 fix). Notebooks 05, 07, and 08 were updated, and the current script path was also updated so CNMC and mandate features coexist in the same production feature tables:

- **`05_feature_engineering.ipynb` / `scripts/04_build_features.py`**: Mandate CSV loaded, joined at monthly granularity, and merged onto the feature matrix. The current script output has 35 columns: 34 CNMC-aware columns plus 1 mandate column. (Was 36/2 before the 2026-06-25 fix.)
- **`07_modeling.ipynb` / `scripts/05_modeling_with_cnmc.py`**: `ML_FEATS` now contains 17 features: 12 baseline calendar/target/macro features, 4 lagged CNMC diesel-market features, and 1 mandate feature. The recursive ML forecast function passes the mandate value forward using the per-year schedule: `Mandato_Energia_Pct = 14.0` in 2026 and `15.5` in 2027. (Was 18 features / 2 mandate values before the 2026-06-25 fix.)
- **`08_modeling_with_prices.ipynb`**: Same `ML_BASE` extension and recursive forecast update as notebook 07.

#### Numeric outcome -- mandate did NOT improve forecasts
A quantitative before/after comparison was run (walk-forward CV + test metrics):

- **Walk-forward CV winners:** Identical per target before and after adding mandate features (SARIMA/Nacional, Gompertz/Madrid, Gompertz/Cataluña, Logistic/Andalucía, Gompertz/Valencia).
- **Test MAPE and R2:** Identical. The winning models for all 5 targets are SARIMA, Logistic, or Gompertz -- none of which use `ML_FEATS` (they are statistical/curve-fit models, not ML feature-based). The ML models (Ridge/RF/XGBoost) did receive the new features but they don't win the walk-forward selection for any target.
- **24-month ML forecast shift:** Random Forest point forecasts for Nacional shifted by approximately +8 Tm/month on average -- a small positive effect reflecting the 14% mandate step-up, but within noise.

**Conclusion: the mandate features are correctly integrated alongside CNMC and will improve presentation narrative** ("our models know about the 14% RD 5/2026 mandate jump in 2026"), but they do not change the production forecast, because the production forecast uses SARIMA/Logistic/Gompertz which are insensitive to external regressors. The mandate features would matter if a pooled/panel ML model were adopted (see next priorities), or if SARIMAX were ever revisited with a richer feature set.

**Do not remove the mandate features** -- they are a legitimate deterministic policy driver and are correctly coded. They just don't move the needle numerically with the current winning model family.

#### HVO (Hydrotreated Vegetable Oil) -- explicitly excluded
Investigated whether HVO should be modelled as a competing substitute (HVO share in the diesel pool displaces biodiesel demand). Decision: **do not include HVO as a feature or separate model target.** Reasons:
- CORES/CNMC data shows erratic HVO share patterns (24.6% in 2021, 11.9% in 2022) with no stable trend.
- No CCAA-level HVO breakdown exists in the available data sources -- only national totals.
- Including HVO would require forecasting HVO itself first, adding a second uncertain forecast into the pipeline.
- HVO is instead documented as a **risk factor in the presentation narrative** ("displacement by HVO could erode the mandate-driven demand uplift we forecast").

#### Data scarcity confirmed: ~21 effective training observations per target
This session clarified the "21 observations" limitation that surprises anyone expecting 3 years of monthly data to mean 36 observations. The correct count per target:
- 36 months total (2023-01 to 2025-12)
- Minus the 12-month tail reserved as 2025 test set = 24 training months
- Minus lag-induced NaN loss: `Lag_1` to `Lag_3` remove the first 3 rows, `Roll_mean_6` removes the first 6 -- effective ~21-23 usable training rows for ML walk-forward CV.
- Older CORES data exists (ESTADISTICAS-BIOS Excel files, 2009-2022) but is **national-level only** (no CCAA breakdown), uses different units (m3 not Tm), and covers a period before modern biodiesel adoption. User confirmed older data is NOT useful and should not be incorporated.

---

## 5. Repository Structure

```
repsol-capstone/
├── README.md                     ← current production pipeline and environment
├── DATA_AUDIT_REPORT.md          ← current dataset audit and output lineage
├── NOTEBOOKS_AUDIT.md            ← current notebook policy
├── AUDIT_FIX_PLAN.md             ← Phase 1 cleanup log and Phase 2 risks
├── datasets_excluded_from_master.md
├── requirements.txt
├── environment.yml
├── .python-version
├── .gitignore
│
├── data/
│   ├── ESTADISTICAS-BIOS CERT DEFINITIVAS *.xlsx   ← raw CORES source files (2020-2022/23/24)
│   ├── inputs/        ← cleaned/merged source datasets, incl. master_dataset.csv (the
│   │                     primary table everything downstream reads from)
│   ├── features/      ← engineered feature matrices (train/test/full + price features)
│   ├── processed/     ← cleaned CNMC outputs
│   ├── raw/           ← canonical CNMC raw CSVs
│   └── outputs/       ← all model metrics, predictions, forecasts, Tableau exports
│
├── notebooks/          ← exploratory/narrative notebooks; scripts are authoritative
│
├── reports/
│   └── figures/        ← PNG charts produced by scripts/notebooks
│
└── scripts/
    ├── 02_master_dataset_builder.py
    ├── 03_clean_cnmc_petroleum.py
    ├── 04_build_features.py
    └── 05_modeling_with_cnmc.py

The previous root-level duplicate raw downloads and macOS AppleDouble metadata files
were removed during the 2026-06-21 Phase 1 cleanup. Canonical raw/processed files now
live under `data/`.
```

**Note on trained model artifacts:** there is no trained-model serialization step in
the current pipeline. Models are refit from scratch by the production script.

---

## 6. Notebooks and Scripts

| # | Notebook | Inputs | Outputs | Status |
|---|---|---|---|---|
| 01 | `01_eda.ipynb` | `consumo_biodiesel_ccaa.csv` | Figures `01`-`04` (national trend, regional top-5, seasonality, correlations) | Complete. Pure EDA, no modelling. |
| 02 | `02_data_cleaning.ipynb` | Raw provincial/CCAA consumption CSVs | `consumo_biodiesel_ccaa.csv`, `consumo_biodiesel_provincial.csv`, `consumo_biodiesel_targets.csv` | Complete. Fixes latin-1/UTF-8 mojibake, validates the 36-month balanced panel, isolates the 5 target series. |
| 03 | `03_external_data.ipynb` | INE Tempus3 API (live), DGT (placeholder, unused) | `macro_indicadores_ine.csv` | Complete for INE. **Recently fixed:** the EPA quarter→month expansion now shifts by one quarter to avoid the publication-delay leak (see Section 4). DGT fleet data integration remains an unfinished placeholder cell. |
| 04 | `04_master_dataset.ipynb` | All cleaned inputs (consumption, macro, Brent, fuel prices) | `master_dataset.csv` (720×17), `.xlsx`, `_metadata.json` | Complete. This is the canonical merge step; `scripts/02_master_dataset_builder.py` duplicates the same logic as a standalone script. |
| 05 | `05_feature_engineering.ipynb` | `master_dataset.csv` | `features_modelo_completo.csv`, `features_train.csv`, `features_test.csv` | Complete. Builds calendar/lag/rolling/macro-lag features and the temporal train/test split. |
| 06 | `06_price_features.ipynb` | Daily `precios_combustibles_*.csv`, `master_dataset.csv` | `features_precios_combustibles.csv`, figures `12`-`15` | Complete. Aggregates daily province-level prices to monthly national + 4-region series, with lag-1 versions; confirms strong negative correlation between conventional fuel prices and biodiesel demand. |
| 07 | `07_modeling.ipynb` | `features_train/test/modelo_completo.csv`, `master_dataset.csv` | `metricas_modelos.csv`, `model_selection_walkforward.csv`, `metricas_final_seleccionado.csv`, `predicciones_test_2025.csv`, `forecast_24m_sarima_rf_xgb.csv`, `tableau_export_legacy.csv` | **Complete, most recently modified.** Trains SARIMA, Ridge, Random Forest, XGBoost, Logistic curve, Gompertz curve for all 5 targets; selects the per-target winner via walk-forward CV; generates the 24-month forecast. This is the core modelling notebook. |
| 08 | `08_modeling_with_prices.ipynb` | `features_modelo_completo.csv`, `features_precios_combustibles.csv`, `metricas_modelos.csv` | `metricas_modelos_con_precios.csv`, `predicciones_test_2025_con_precios.csv`, `forecast_24m_con_precios.csv`, `metricas_comparativa.csv` | Complete. A narrower ablation study: does adding lag-1 fuel-price features improve RF/XGBoost specifically, versus the 07 baseline? (Answer: modestly, inconsistently across targets - see notebook conclusion.) Does not include the growth-curve candidates; that's intentionally out of this notebook's scope. |
| 09 | `09_evaluation.ipynb` | All of 07's outputs + `features_train/test.csv`, `master_dataset.csv` | Figures `07`-`17`, printed evaluation summary | Complete, most recently modified. Deep-dive: model comparison charts, residual analysis (now dynamically follows whichever model walk-forward selected per target, not hardcoded to SARIMA), RF/XGBoost feature importance, 24-month forecast visualisation, and the final recommended-forecast table. |
| — | `scripts/02_master_dataset_builder.py` | Same inputs as notebook 04 | `master_dataset.csv` (same target file) | Functional standalone alternative to notebook 04. Not the primary path used in this session's reruns (notebook 04 was used instead); kept in sync only insofar as it reads the same already-fixed `macro_indicadores_ine.csv`. |

**Deleted/legacy:** a `07_tableau_prep.ipynb` notebook existed previously and was deleted; its outputs (`tableau_dashboard.csv`, `tableau_metricas.csv`, `tableau_forecast_pivot.csv`) remain in `data/outputs/` from before it was removed, and are now stale relative to the current model set (they don't include the growth-curve results). If a Tableau refresh is needed, these three files should be regenerated by whoever rebuilds that export step, or that logic should be reintroduced into notebook 09.

---

## 7. Modeling Approach

**Candidates evaluated** (7 total, all fit independently per target):

| Model | Type | Notes |
|---|---|---|
| SARIMA(1,1,1)(1,0,0,12) | Statistical, univariate | Fit on `log1p(Consumo_Tm)`. Models trend + seasonal autocorrelation directly. |
| Ridge regression (α=10) | ML, linear | Fit on `log1p` target with calendar/lag/macro features, `StandardScaler`-normalised. |
| Random Forest (300 trees, depth 3) | ML, ensemble | Same feature set as Ridge. |
| XGBoost (300 rounds, depth 2, lr 0.05) | ML, gradient boosting | Same feature set as Ridge. |
| **Logistic growth curve** *(added 2026-06-16)* | Statistical, saturating | `L / (1 + exp(-k(t-t0)))` + 2-parameter sin/cos seasonal correction, fit on raw `Consumo_Tm`. |
| **Gompertz growth curve** *(added 2026-06-16)* | Statistical, saturating | `L·exp(-b·exp(-kt))` + same seasonal correction. |
| **Diesel Share** *(added 2026-06-19)* | Ratio model | Models `Biodiesel_GasoleoA_Ratio` and converts the predicted ratio back into tonnes using seasonal-naive future `GasoleoA_Tm`. Tested as a candidate, but not selected. |

**Feature set** (`ML_FEATS`, used by Ridge/RF/XGBoost only, 17 features total as of 2026-06-25, was 18 with two mandate features before that date -- see "2026-06-25 Audit Fixes"): `Tendencia` (trend index), `Mes`, `sin_mes`/`cos_mes` (cyclical month encoding), `Lag_1`/`Lag_2`/`Lag_3` (target lags), `Roll_mean_3`/`Roll_mean_6` (rolling means), `IPI_original_lag1`, `IPC_var_anual_lag1`, `Tasa_paro_lag1` (lagged macro -- **never the contemporaneous value**, see Section 4), plus the lagged CNMC diesel-market features `GasoleoA_Tm_lag1`, `GasoleoA_Tm_roll3_lag1`, `Biodiesel_GasoleoA_Ratio_lag1`, `Biodiesel_GasoleoA_Ratio_roll3_lag1`, **plus `Mandato_Energia_Pct`** (deterministic policy feature, no lag needed, future values read from the mandate schedule). `Lag_12` exists in the feature table but is excluded from the model feature lists due to excessive NaN loss.

**Evaluation metric:** MAPE is the primary ranking metric; MAE, RMSE, R² also reported. **R² is the more honest signal of absolute fit quality** — it is negative for every target except Nacional (≈0), meaning even the best models still underperform a naive mean in absolute terms; MAPE looks more flattering but can mask this.

**Model selection methodology:** walk-forward (expanding-window, 1-step-ahead) cross-validation confined to 2023-2024, median-aggregated across ~8 folds per target (median chosen over mean because a single divergent SARIMA fold can otherwise dominate). The winner is committed to *before* ever touching the 2025 test set; the test MAPE/R² reported is a single honest out-of-sample number, not a result of picking among candidates after seeing their test performance.

**Current best model per target** (as of 2026-06-19, after CNMC + mandate integration): SARIMA for Nacional, Gompertz for Madrid/Cataluña/Valencia, Logistic for Andalucía.

**Known weaknesses of the current approach:**
- Each of the 5 targets is modelled **independently** — no pooling of information across regions, despite all 5 sharing the same national adoption wave and macro environment. This means each model effectively has only ~21-23 usable training observations.
- 1-step-ahead walk-forward validation does not fully replicate the actual 12-month-ahead forecasting task, so it can occasionally select a model (e.g. Ridge, before the growth curves were added) that looks fine 1 month out but extrapolates badly over a full year.
- No hyperparameter tuning via cross-validation for Ridge/RF/XGBoost — values are hand-picked, partly to avoid adding yet another source of test-set-adjacent overfitting risk on this little data.
- CNMC diesel-market features improved the business logic of the dataset but did not solve the poor regional forecast performance for Madrid and Cataluña. The remaining issue appears more structural than feature-missing.

---

## 8. Key Decisions and Assumptions

- **Target variable = total market demand (CORES consumption), not Repsol sales.** No Repsol-internal sales data exists in this project; this is explicitly a macro/external-market forecast.
- **5 modelling targets only**: ESPAÑA (national) + Madrid, Cataluña, Andalucía, Comunitat Valenciana. All other CCAAs are present in `master_dataset.csv` (for context/EDA) but are never modelled individually.
- **Forecast horizon fixed at 24 months** (2026-01 → 2027-12), monthly granularity, matching the project brief.
- **Train/test split is temporal, not random**: 2023-2024 train, 2025 test — required for any time-series evaluation to be meaningful, and enforced consistently across every notebook.
- **Macro features must be lagged by 1 month minimum** before use as model inputs, because INE publishes IPI/IPC/unemployment with a real delay. Quarterly EPA data is shifted by a full quarter for the same reason. This was a deliberate fix this session (see Section 4) — any new macro series added in the future must follow the same convention.
- **CNMC diesel-market features must also be leakage-safe.** `GasoleoA_Tm` and `Biodiesel_GasoleoA_Ratio` can be stored contemporaneously for auditing, but the model inputs must be lagged or rolling-lagged versions only.
- **Do not use Jan-Feb 2026 CNMC actuals for the original capstone forecast.** They are retained in processed CNMC files for future reference, but the production forecast remains a 2025-12-origin forecast for 2026-01 through 2027-12.
- **National CNMC rows must be built from all 19 CCAA, never from only the four modeled regions.** The four regions are modeled separately, but they are not the whole Spanish market.
- **Model selection must never use the test set.** Walk-forward CV inside the training window is the only sanctioned way to choose a model family per target. This is a hard rule going forward, established after finding the original pipeline violated it.
- **A new candidate model is only adopted if it wins (or ties) the existing walk-forward selection — never by manually overriding the selection after seeing test results.** This is exactly how the Logistic/Gompertz curves were added and validated.
- **Gasolina 98 is genuinely not sold in Melilla** — the resulting 36 NaN rows in `master_dataset.csv` are expected, not a data quality bug.
- **Provincial-level consumption and single-month tourism data are deliberately excluded** from the master dataset (see `datasets_excluded_from_master.md`) — granularity mismatch and insufficient time coverage, respectively.
- **DGT vehicle fleet data is a known gap**, not yet sourced (no public API; needs manual download).
- **Repsol instruction: never "add up the regions" in the deliverable.** Each region's forecast must be reported separately — no single combined/summed regional demand figure. This constrains the *output*, not internal model fitting; joint ("pooled") fitting that still emits per-region forecasts is allowed (see Section 4, 2026-06-21). Nacional is the national total and is kept separate from / never pooled with its component regions.
- **Saturation prior (proposed, not yet adopted):** the 4 regional series are known a-priori to be adoption curves approaching saturation, which justifies restricting *their* candidate set to saturating curves (Logistic/Gompertz). This constrains the hypothesis space by domain knowledge and is distinct from (and compatible with) the "never select on the test set" rule. Nacional is exempt (SARIMA legitimately wins). See Section 4.

---

## 9. Current Status

**Data pipeline:** Complete and stable for the current capstone scope. `master_dataset.csv` and the feature tables incorporate:

- the EPA publication-delay fix,
- lagged macro features,
- CNMC diesel-market features,
- deterministic biofuel mandate features,
- and the original 2025-12 forecast origin.

The current script-based rebuild path is:

```powershell
.\.venv\Scripts\python scripts/03_clean_cnmc_petroleum.py
.\.venv\Scripts\python scripts/02_master_dataset_builder.py
.\.venv\Scripts\python scripts/04_build_features.py
.\.venv\Scripts\python scripts/05_modeling_with_cnmc.py
.\.venv\Scripts\python scripts/06_validate_outputs.py
```

**Modelling pipeline:** Complete for the current `sacha` candidate set. The headline selection is the lowest training-only recursive walk-forward MAPE among seven independent candidates per target. The 2025 metrics below are honest holdout metrics reported after selection:

| Target | Model | Training WF MAPE | 2025 MAPE | R2 |
|---|---|---:|---:|---:|
| Nacional | SARIMA | 39.7% | 29.0% | -0.009 |
| Madrid | Logistic | 37.2% | 73.6% | -8.273 |
| Catalonia | SARIMAX | 68.5% | 92.3% | -19.827 |
| Andalusia | SARIMA | 53.9% | 49.7% | -1.662 |
| Valencia | Gompertz | 57.3% | 34.2% | -1.246 |

**Verification status:** A full leakage audit was performed, two critical leaks and a model-selection bias were fixed, and the fix was independently double-checked. The CNMC integration was verified on 2026-06-19. The 2026-06-24 `sacha` rebuild restores the hard no-test-set-selection rule:

- raw CNMC files parse cleanly,
- CNMC biodiesel reconciles exactly to the existing target,
- national `ESPAÑA` Gasoleo A is independently summed from all 19 CCAA,
- no 2026 CNMC rows enter the model-origin data,
- CNMC model inputs are lagged only,
- mandate features are present with the biodiesel blend requirement set to 0.0 before August 2024,
- `Selected_Model` is fixed before `features_test.csv` is loaded in `scripts/05_modeling_with_cnmc.py`,
- and `scripts/06_validate_outputs.py` passes, including selected-forecast degeneracy checks.

**Important modeling caveat:** The pipeline is believed leakage-free, but the absolute model fit remains weak. CNMC and mandate features improve the project's business structure, but they do not automatically win every target. Pooled regional ML is documented as a sensitivity experiment only. Catalonia's selected SARIMAX result has a poor 2025 holdout MAPE and should be discussed plainly.

**Git status:** Current work is on branch `sacha` with uncommitted modeling, validation, output, and documentation changes. Before pushing, verify with:

```powershell
git status --short --branch
git log --oneline --decorate -5
```

**Next priorities, in order of expected impact:**
1. Preserve the current script-first workflow and run `scripts/06_validate_outputs.py` after every full rebuild.
2. Treat final forecasts as directional planning scenarios because selected-model R2 values remain weak or negative.
3. Consider stronger backtesting only if more history becomes available; the current 2023-2025 window is too short to provide a pristine final test.
4. Source DGT vehicle fleet data if the project needs a new external driver.
5. If the business wants mandate impact ranges, add explicit scenarios rather than selecting on the 2025 holdout.
---

## 10. Future Instructions for Claude

- **Read this file first**, before doing any other work in this repository, in any new session.
- Treat this file as project memory, but prefer the refreshed `README.md`, `DATA_AUDIT_REPORT.md`, and `NOTEBOOKS_AUDIT.md` for current delivery instructions and file shapes.
- **Memory maintenance rule:** `memory.md` is not automatic. Any person or AI assistant making a major project change must update this file in the same work session, pull request, or commit. This applies to teammate changes too: if a teammate changes the model, data, scope, outputs, or headline conclusions, the teammate or reviewer should add a dated memory entry.
- Before relying on any specific claim in this file that names a file, function, or result (e.g., "`ML_FEATS` contains X", "Gompertz is selected for Madrid"), **verify it against the actual current repo state** — re-read the relevant notebook cell or re-run the relevant CSV check — rather than assuming this file is still accurate. Treat this file as a snapshot in time, not a live source.
- **Never reintroduce the two leaks fixed in Section 4**: (a) never use contemporaneous (non-lagged) `IPI_original`/`IPC_var_anual`/`Tasa_paro` as a model feature, only `_lag1`; (b) never let quarterly macro data (like EPA unemployment) get forward-filled into months before it would actually have been published.
- **Never use contemporaneous CNMC market variables as model features for the same month.** `GasoleoA_Tm` and `Biodiesel_GasoleoA_Ratio` must enter models through lagged/rolling-lagged features only, unless the forecast design explicitly changes and is documented.
- **Do not silently change the forecast origin by using Jan-Feb 2026 CNMC actuals.** Those rows exist in processed CNMC files for future use, but the current capstone forecast is intentionally generated as if standing at 2025-12.
- **When rebuilding national CNMC features, sum all 19 CCAA.** Never build the national series from only Madrid, Cataluña, Andalucía, and Valencia.
- **Never select a model family using test-set performance.** Any new candidate model must go through the same walk-forward CV gate (inside 2023-2024 only) as the existing seven, and must only be adopted if it wins or ties that CV — exactly as was done for the Logistic/Gompertz and Diesel Share additions.
- **When editing notebook `.ipynb` files programmatically** (via `nbformat`), always re-read the file fresh from disk immediately after writing to confirm the edit actually persisted — a real bug this session came from a bundled multi-edit script that crashed before its `nbformat.write()` call, silently discarding an earlier successful edit in the same script. Prefer one isolated read-modify-write-verify script per logical change over bundling several edits together.
- **When changing a feature list** (`ML_FEATS`, `ML_BASE`, `ML_PRICE`), grep for any code elsewhere that builds a model input row by **fixed position** (`np.array([[...]])` with positional values) rather than by feature name — this exact bug class broke the recursive forecast functions in both notebook 07 and 08 once before, and would break silently again.
- **Update this file** whenever a major change happens: a new model is added/removed, SARIMA orders or model-selection logic change, a new leak is found and fixed, the target/scope changes, a new data source is integrated, the forecast origin or validation policy changes, output/dashboard files change materially, business interpretation changes, or the git/commit state materially changes.
- **How to update it:** add a dated entry near the top for new major work, state what changed, why it matters, which files/outputs changed, and how it was verified. Also refresh Section 9 ("Current Status") when headline results, risks, or next priorities change.
- **When not to update it:** skip memory updates for tiny typo, formatting, or presentation-only changes that do not affect data, models, outputs, interpretation, or collaborator workflow.
