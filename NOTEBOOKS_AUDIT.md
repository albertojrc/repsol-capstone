# Notebooks Audit

Refreshed: 2026-06-24 (branch `sacha`)

## Current Policy

The production source of truth is the script pipeline documented in `README.md`.
The notebooks are retained for exploration, explanation, and optional ablation
work. Notebooks 07 and 08 in particular predate the current modeling design
(no SARIMAX, no CNMC diesel-market features, no open seven-model competition)
and should not be read as describing the current production methodology --
they are kept runnable for narrative/exploratory value only.

## Bugs Found And Fixed In This Refresh

An earlier "translate notebook content to English" pass had renamed several
data-derived string literals inside code cells, not just prose. Renaming a
column name or a raw source value in code breaks the notebook the moment it
touches real data, because nothing else in the pipeline was renamed to match.
Three distinct breakages were found and fixed:

1. **`KeyError: 'Trend'`** -- `'Tendencia'` (the real trend-index column built
   by `scripts/04_build_features.py`) had been renamed to `'Trend'` inside
   notebooks 05, 07, 08, and 09. Confirmed by direct reproduction against the
   real `features_train.csv`. Fixed by reverting the literal back to
   `'Tendencia'` in all four notebooks; left all English prose untouched.
2. **Silent price-feature mismatch** -- the raw `Producto` values
   (`'Gasolina 95 E5'`, `'Gasolina 98 E5'`, `'Gasóleo A habitual'`, `'Gasóleo
   Premium'`) and the derived slugs (`gasolina95`, `gasolina98`) had been
   renamed to `'Gasoline 95 E5'` / `'Diesel A habitual'` / `gasoline95` inside
   notebook 06's `PRODUCT_MAP`, and to `PVP_gasoline95...` inside notebook 08.
   Notebook 06's mapping would have silently matched zero rows (all four
   products); notebook 08 crashed with `KeyError: 'PVP_gasoline95_nac_lag1'`.
   Fixed by reverting all of these back to the real Spanish values; the
   `labels` list used only for chart legends was left in English since it
   does not reference real data.
3. **Stale SARIMA-acceptance columns** -- notebooks 10, 10.1, and 13 still
   referenced `Default_2025_MAPE` / `Grid_Selected_2025_MAPE`, two columns
   that no longer exist in `sarima_order_acceptance.csv` after the SARIMA
   order selection was rebuilt to be training-only (see
   `PHASE2_MODELING_REPORT.md`). Fixed by displaying
   `Grid_WalkForward_MAPE` / `Selected_By_Training_WalkForward` instead, which
   are the columns the current script actually writes.

A separate, lower-severity issue (literal `?` characters in place of `ñ`/`í`
in "Catalu?a" / "Andaluc?a", likely from copy-pasting console output into
markdown) was also found and fixed in notebooks 10, 10.1, and 13.

All affected notebooks (05, 06, 07, 08, 09, 13) were re-executed end to end
after the fixes to confirm they run clean and to regenerate their figures.
Notebooks 10 and 10.1 were not re-executed (they only read existing output
CSVs and were not broken), but their column-reference fix was verified by
inspection against the current `sarima_order_acceptance.csv` schema.

**Caution for future edits:** notebook 05, if run, overwrites
`data/features/features_*.csv` with its own (older, 27-column) schema instead
of the current 36-column CNMC-and-mandate-aware schema that
`scripts/04_build_features.py` produces -- always re-run
`scripts/04_build_features.py` and `scripts/05_modeling_with_cnmc.py` (then
`scripts/06_validate_outputs.py`) after running notebook 05 to restore the
authoritative production state.

**Fixed 2026-06-25:** notebooks 07 and 08 previously wrote to several of the
same `data/outputs/*.csv` filenames that `scripts/05_modeling_with_cnmc.py`
owns (`metricas_models.csv`, `model_selection_walkforward.csv`,
`metricas_final_selected.csv`, `predicciones_test_2025.csv`,
`forecast_24m_sarima_rf_xgb.csv`, `tableau_export_legacy.csv`,
`metricas_comparativa.csv`), so running either could silently overwrite
production outputs with an older, narrower candidate set. Every colliding
output in both notebooks now writes to a `legacy_notebook07_`/
`legacy_notebook08_`-prefixed filename instead, so this can no longer
happen regardless of run order. See `AUDIT_FIX_PLAN.md`'s "Notebooks 07/08
No Longer Share Output Filenames With scripts/05" entry.

## Inventory

| Notebook | Current Status | Notes |
|---|---|---|
| `01_eda.ipynb` | Exploratory | EDA figures only. Not part of the production rebuild. Unaffected by the bugs above. |
| `02_data_cleaning.ipynb` | Historical / exploratory | Original target-cleaning workflow. Production inputs are already committed. Unaffected. |
| `03_external_data.ipynb` | Historical / exploratory | INE / external-data notes. DGT remains planned, not implemented. Unaffected. |
| `04_master_dataset.ipynb` | Superseded by script | Use `scripts/02_master_dataset_builder.py` for the CNMC-aware 22-column master dataset. Unaffected by the bugs above. |
| `05_feature_engineering.ipynb` | Superseded by script; fixed and re-verified | Use `scripts/04_build_features.py` for the CNMC-aware 36-column feature table. Fixed the `'Trend'` literal; runs clean, but still produces a smaller, older feature schema than the script -- do not let its output overwrite `data/features/`. |
| `06_price_features.ipynb` | Optional ablation support; fixed and re-verified | Builds optional price features for notebook 08. Fixed the `gasolina`/`Gasóleo` mistranslation in `PRODUCT_MAP`; re-run confirms its output is byte-identical to the existing `features_precios_combustibles.csv`. |
| `07_modeling.ipynb` | Superseded by script; fixed and re-verified | Use `scripts/05_modeling_with_cnmc.py` for current modeling outputs. Implements an older 6-candidate design (no SARIMAX, no CNMC features) -- its numbers will not match the current production selection. Fixed the `'Trend'` literal; all 6 outputs now save under a `legacy_notebook07_` prefix so it can never overwrite production outputs; runs clean. |
| `08_modeling_with_prices.ipynb` | Optional ablation support; fixed and re-verified | Price-region mapping bug fixed previously; this round fixed the `'Trend'` and `gasolina95` literals, and its one colliding output (`metricas_comparativa.csv`) now saves as `legacy_notebook08_metricas_comparativa.csv`. Not the production modeling path. |
| `09_evaluation.ipynb` | Superseded by script; fixed and re-verified | Script now writes the final figures and dashboard outputs. Fixed the `'Trend'` literal; runs clean. Its auto-rebuild guard (which reruns `scripts/02`/`scripts/04` if expected columns are missing) cannot fix a renamed-literal bug like this one, only a genuinely stale feature table -- keep that distinction in mind for any future translation-style edit. |
| `10_final_models.ipynb` | Narrative summary; fixed | Documents the current seven-model open-competition selection and 2025 holdout metrics. Fixed the stale `Default_2025_MAPE`/`Grid_Selected_2025_MAPE` column reference and the `?` mojibake. |
| `10_1_final_models.ipynb` | Cataluña detail; fixed | Same fixes as notebook 10. |
| `11_mini_demand_model.ipynb` | Removed upstream | Superseded by notebook 12 in the latest `main`; not part of the current notebook set. |
| `12_mini_trend_regulation_model.ipynb` | Mini regulation model | Narrative regulation/trend scenario model, independent of the main per-region pipeline. Not affected by the translation bugs (no `'Trend'`/`gasolina` literals found). Its own scenario forecasts are not reconciled with `forecast_24m_selected.csv` -- the two should not be confused for the same deliverable. |
| `13_business_interpretation_and_recommendations.ipynb` | Business interpretation; fixed and re-verified | Reads production outputs, restates selected results by target, shows the training-only SARIMA grid, generates regional train/validation/forecast plots, and documents model limitations, feature interpretation, internal Repsol data needs, and recommendations. Fixed the stale SARIMA-acceptance columns and the `?` mojibake; re-executed to regenerate all 5 regional figures, which were previously a day stale relative to the final model selection. |

## Fixes Applied (this refresh)

- Reverted the `'Tendencia'` -> `'Trend'` mistranslation in notebooks 05, 07, 08, 09.
- Reverted the `gasolina95`/`gasolina98`/`Gasóleo` -> `gasoline95`/`gasoline98`/`Diesel` mistranslation in notebooks 06 and 08.
- Fixed the stale `sarima_order_acceptance.csv` column references in notebooks 10, 10.1, and 13.
- Fixed literal `?` mojibake ("Catalu?a", "Andaluc?a") in notebooks 10, 10.1, and 13.
- Re-executed notebooks 05, 06, 07, 08, 09, and 13 end to end; all run with zero errors.
- Restored `data/features/*.csv` and the shared `data/outputs/*.csv` filenames to the authoritative script-produced state after the notebook runs (see caution note above).
- Regenerated all figures that depend on notebooks 06, 07, 08, 09, and 13 so they reflect the current model selection and the fixed price features.
- Removed an orphaned stale figure (`13_business_nacional_train_validation_forecast.png`) left behind when the corresponding code started writing `13_business_national_train_validation_forecast.png` instead.

## Remaining Caveat

The notebooks should not be used as the authoritative final pipeline unless they
are fully refactored to mirror the scripts. For final delivery, use:

```powershell
.\.venv\Scripts\python scripts/03_clean_cnmc_petroleum.py
.\.venv\Scripts\python scripts/02_master_dataset_builder.py
.\.venv\Scripts\python scripts/04_build_features.py
.\.venv\Scripts\python scripts/05_modeling_with_cnmc.py
.\.venv\Scripts\python scripts/06_validate_outputs.py
```

Notebooks 07 and 08 are exploratory snapshots of an earlier modeling design
(pre-SARIMAX, pre-CNMC features). They run cleanly again after this refresh,
but their candidate set and numbers should not be quoted as the current
production result -- only `scripts/05_modeling_with_cnmc.py` and notebooks 10,
10.1, and 13 reflect the current selection.
