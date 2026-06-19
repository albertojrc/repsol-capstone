# Project Memory — Repsol Eco-Fuels Demand Forecasting Capstone

**Last updated:** 2026-06-19
**Maintainer note:** This file is the long-term source of truth for this project. See [Section 10](#10-future-instructions-for-claude) for how Claude should use and maintain it.

---

## 2026-06-19 Update: CNMC Diesel-Market Feature Integration

The CNMC `Estadistica Petroleo - Consumos mensuales provincial (Tm)` files have now been integrated as a leakage-safe diesel-market feature source.

New raw files under `data/raw/consumos_mensuales_petroleo/`:
- `ds_14200_1.csv` through `ds_14203_1.csv`
- 2023-01 to 2025-12 plus Jan-Feb 2026 CNMC data
- Jan-Feb 2026 is cleaned and retained in processed CNMC files, but is not used in `master_dataset.csv`, feature training/test sets, model selection, or final 2026-2027 forecast generation.

New scripts:
- `scripts/03_clean_cnmc_petroleum.py`: cleans CNMC provincial data, writes provincial/CCAA diesel-market tables, and validates reconciliation against the existing biodiesel target.
- `scripts/04_build_features.py`: rebuilds the modeling feature tables with leakage-safe lagged CNMC features.
- `scripts/05_modeling_with_cnmc.py`: reruns model evaluation, walk-forward selection, 2025 test predictions, 2026-2027 forecasts, figures, and Tableau exports with the new diesel-market features.

New processed CNMC outputs:
- `data/processed/cnmc_consumos_petroleo_provincial.csv`
- `data/processed/cnmc_consumos_petroleo_ccaa.csv`
- `data/processed/cnmc_diesel_market_features.csv`

Current master/feature state:
- `data/inputs/master_dataset.csv`: 720 rows x 22 columns, still 2023-01 to 2025-12 only.
- `data/features/features_modelo_completo.csv`: 180 rows x 34 columns, still only the 5 modeled targets.
- Added CNMC model inputs are lagged only: `GasoleoA_Tm_lag1`, `GasoleoA_Tm_roll3_lag1`, `Biodiesel_GasoleoA_Ratio_lag1`, `Biodiesel_GasoleoA_Ratio_roll3_lag1`.
- Contemporaneous `GasoleoA_Tm` and contemporaneous biodiesel/Gasoleo A ratio are retained for audit and lag construction, but are not used as direct ML features for month `t`.

Verification passed:
- All four raw CNMC files parse as semicolon CSVs with zero missing cells and zero duplicate province-product-month rows.
- CNMC 2023-2025 `BIODIESEL` reconciles exactly against `data/inputs/consumo_biodiesel_ccaa.csv` over 720 CCAA-month pairs, max absolute difference 0.0 Tm.
- National `ESPAÑA` `GasoleoA_Tm` equals the sum of all 19 CCAA values for every month, max absolute difference 0.0 Tm.
- No 2026 CNMC rows enter master, features, training, validation, walk-forward selection, or final production forecast origin.
- Lagged diesel-market feature causality checks passed to floating-point tolerance.
- Selected regional forecasts remain below the national forecast every month; the four modeled regions are about 43.5% of national forecast volume in 2026 and 44.2% in 2027.

Modeling result:
- The new feature did not materially improve the selected production models.
- Walk-forward-selected models remain: Nacional = SARIMA, Madrid = Gompertz, Cataluña = Gompertz, Andalucia = Logistic, Valencia = Gompertz.
- The new `Diesel Share` candidate was added as requested, but performed very badly in 2025 test metrics and should be treated as a failed experiment, not a recommended model.
- Direct ML models with the new diesel lags showed some useful signal in places (notably Madrid XGBoost test MAPE around 60%), but did not win the existing 2023-2024 walk-forward selection gate.
- Important business/modeling caveat: Madrid and Cataluña still have a serious validation/test mismatch. The walk-forward-selected Gompertz models looked strong in 2023-2024 one-step validation but have very poor 2025 test MAPE (Madrid 197.1%, Cataluña 164.2%). This is not solved by the CNMC feature and remains a final-delivery risk.

Updated outputs regenerated:
- `data/outputs/metricas_modelos.csv`
- `data/outputs/model_selection_walkforward.csv`
- `data/outputs/metricas_final_seleccionado.csv`
- `data/outputs/predicciones_test_2025.csv`
- `data/outputs/forecast_24m_sarima_rf_xgb.csv`
- `data/outputs/tableau_dashboard.csv`
- `data/outputs/tableau_metricas.csv`
- `data/outputs/tableau_forecast_pivot.csv`
- `data/outputs/tableau_export_legacy.csv`
- `reports/figures/07_model_comparison.png`
- `reports/figures/11_forecast_24m.png`

Pipeline order for the current script path:
1. Run `scripts/03_clean_cnmc_petroleum.py`.
2. Run `scripts/02_master_dataset_builder.py`.
3. Run `scripts/04_build_features.py`.
4. Run `scripts/05_modeling_with_cnmc.py`.

Important note: the script path above is now the most current reproducible path. Some older notebook/documentation text still predates this CNMC integration and may describe the former 17-column master dataset or the pre-CNMC model candidate set.

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
- **What "demand" means here:** This is **total market demand** for biodiesel in each region/nationally (i.e., CORES-reported aggregate consumption), **not Repsol's own sales or market share**. There is no Repsol-specific sales data in this project — it is a macro demand forecast that Repsol can use as external market context.
- **Historical data window:** 2023-01 to 2025-12 (36 months). This is the full window for which CORES consumption data, INE macro indicators, and daily fuel price data are all available and aligned.
- **Train/test convention used throughout modelling:** Train = 2023-01 → 2024-12 (24 months), Test = 2025-01 → 2025-12 (12 months, held out). The 24-month 2026-2027 forecast is generated by refitting the chosen model on the full 36-month history.

---

## 3. Data Sources

| Source | What it provides | Where it lands in the pipeline |
|---|---|---|
| **CORES** (Corporación de Reservas Estratégicas de Productos Petrolíferos) | Monthly biodiesel consumption (`Consumo_Tm`, metric tonnes) by province/CCAA/national. This is the **target variable**. Original raw certification files (`ESTADISTICAS-BIOS CERT DEFINITIVAS *.xlsx`) sit in `data/`; CORES is also the likely origin of the stray root-level files (`4247.csv`, `50934.csv`, `ds_14200_1.csv`, `ds_14201_1.csv`, `ds_14202_1.csv`, `ESTADISTICA*-BIOS*.xls/xlsx`) which appear to be early manual downloads, not yet wired into the automated notebook pipeline. | `consumo_biodiesel_ccaa.csv`, `consumo_biodiesel_provincial.csv`, `consumo_biodiesel_targets.csv` (via notebook 02) |
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
- A single `master_dataset.csv` (720 rows × 17 columns, `Fecha`×`CCAA` primary key) built, combining consumption + macro + Brent + fuel prices.
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

---

## 5. Repository Structure

```
repsol-capstone/
├── memory.md                     ← this file
├── README.md                     ← project overview (NOTE: describes an OLDER folder layout —
│                                     mentions data/raw/, data/processed/, models/, src/, which
│                                     no longer exist in the same form; see actual layout below)
├── DATA_AUDIT_REPORT.md          ← dataset-by-dataset audit, generated 2026-06-10 — PARTIALLY
│                                     STALE: predates the leakage fixes and growth-curve work
│                                     below (still accurate for data/inputs and data/features,
│                                     but data/outputs row counts and model lists are outdated)
├── NOTEBOOKS_AUDIT.md            ← notebook-by-notebook audit, generated 2026-06-10 — also
│                                     PARTIALLY STALE for the same reason; useful for the file
│                                     renaming history but not for current model list/results
├── datasets_excluded_from_master.md  ← explains why provincial & tourism data weren't merged
├── requirements.txt              ← pandas 2.0.3, numpy 1.24.3, scikit-learn 1.3.0,
│                                     statsmodels 0.14.0, xgboost 2.0.0, matplotlib, seaborn,
│                                     jupyter(lab), openpyxl, requests, python-dotenv
├── .gitignore                    ← ignores data/raw/, data/processed/ (old layout), most
│                                     *.csv/*.xlsx EXCEPT inside data/inputs|features|outputs
│
├── data/
│   ├── ESTADISTICAS-BIOS CERT DEFINITIVAS *.xlsx   ← raw CORES source files (2020-2022/23/24)
│   ├── inputs/        ← cleaned/merged source datasets, incl. master_dataset.csv (the
│   │                     primary table everything downstream reads from)
│   ├── features/      ← engineered feature matrices (train/test/full + price features)
│   └── outputs/       ← all model metrics, predictions, forecasts, Tableau exports
│
├── notebooks/          ← 01 through 09, the full pipeline (see Section 6)
│
├── reports/
│   └── figures/        ← all PNG charts produced by notebooks 01, 02, 03, 05, 06, 07, 09
│
└── scripts/
    └── 02_master_dataset_builder.py   ← standalone script duplicating 04_master_dataset.ipynb's
                                          logic (reads the same inputs incl. macro_indicadores_ine.csv,
                                          so it automatically inherits the EPA leak fix); appears to
                                          be a legacy/alternate path to the same output, not actively
                                          maintained in parallel with the notebook

Also present at repo root (tracked in git, not part of the automated pipeline):
4247.csv, 50934.csv, ds_14200_1.csv, ds_14201_1.csv, ds_14202_1.csv,
ESTADISTICA-BIOS_2020.xlsx, ESTADISTICAS_BIOS_2022.xlsx, ESTADISTICA_BIOS_2021.xls
  — likely early manual CORES/INE downloads, predating the notebook pipeline. No notebook or
    script currently reads them directly.
```

**Note on `models/` and `src/` folders:** the README describes a `models/` and `src/` directory; neither currently exists in the working tree (only stray macOS `._models` / `._src` resource-fork artifacts remain, suggesting they existed at some point on a Mac collaborator's machine and were later removed). There is no trained-model serialization step anywhere in the current pipeline — models are refit from scratch inside each notebook run.

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
| 08 | `08_modeling_with_prices.ipynb` | `features_modelo_completo.csv`, `features_precios_combustibles.csv`, `metricas_modelos.csv` | `metricas_modelos_con_precios.csv`, `predicciones_test_2025_con_precios.csv`, `forecast_24m_con_precios.csv`, `metricas_comparativa.csv` | Complete. A narrower ablation study: does adding lag-1 fuel-price features improve RF/XGBoost specifically, versus the 07 baseline? (Answer: modestly, inconsistently across targets — see notebook conclusion.) Does not include the growth-curve candidates; that's intentionally out of this notebook's scope. |
| 09 | `09_evaluation.ipynb` | All of 07's outputs + `features_train/test.csv`, `master_dataset.csv` | Figures `07`-`17`, printed evaluation summary | Complete, most recently modified. Deep-dive: model comparison charts, residual analysis (now dynamically follows whichever model walk-forward selected per target, not hardcoded to SARIMA), RF/XGBoost feature importance, 24-month forecast visualisation, and the final recommended-forecast table. |
| — | `scripts/02_master_dataset_builder.py` | Same inputs as notebook 04 | `master_dataset.csv` (same target file) | Functional standalone alternative to notebook 04. Not the primary path used in this session's reruns (notebook 04 was used instead); kept in sync only insofar as it reads the same already-fixed `macro_indicadores_ine.csv`. |

**Deleted/legacy:** a `07_tableau_prep.ipynb` notebook existed previously and was deleted; its outputs (`tableau_dashboard.csv`, `tableau_metricas.csv`, `tableau_forecast_pivot.csv`) remain in `data/outputs/` from before it was removed, and are now stale relative to the current model set (they don't include the growth-curve results). If a Tableau refresh is needed, these three files should be regenerated by whoever rebuilds that export step, or that logic should be reintroduced into notebook 09.

---

## 7. Modeling Approach

**Candidates evaluated** (6 total, all fit independently per target):

| Model | Type | Notes |
|---|---|---|
| SARIMA(1,1,1)(1,0,0,12) | Statistical, univariate | Fit on `log1p(Consumo_Tm)`. Models trend + seasonal autocorrelation directly. |
| Ridge regression (α=10) | ML, linear | Fit on `log1p` target with calendar/lag/macro features, `StandardScaler`-normalised. |
| Random Forest (300 trees, depth 3) | ML, ensemble | Same feature set as Ridge. |
| XGBoost (300 rounds, depth 2, lr 0.05) | ML, gradient boosting | Same feature set as Ridge. |
| **Logistic growth curve** *(added 2026-06-16)* | Statistical, saturating | `L / (1 + exp(-k(t-t0)))` + 2-parameter sin/cos seasonal correction, fit on raw `Consumo_Tm`. |
| **Gompertz growth curve** *(added 2026-06-16)* | Statistical, saturating | `L·exp(-b·exp(-kt))` + same seasonal correction. |

**Feature set** (`ML_FEATS`, used by Ridge/RF/XGBoost only): `Tendencia` (trend index), `Mes`, `sin_mes`/`cos_mes` (cyclical month encoding), `Lag_1`/`Lag_2`/`Lag_3` (target lags), `Roll_mean_3`/`Roll_mean_6` (rolling means), `IPI_original_lag1`, `IPC_var_anual_lag1`, `Tasa_paro_lag1` (lagged macro — **never the contemporaneous value**, see Section 4). `Lag_12` exists in the feature table but is excluded from the model feature lists due to excessive NaN loss.

**Evaluation metric:** MAPE is the primary ranking metric; MAE, RMSE, R² also reported. **R² is the more honest signal of absolute fit quality** — it is negative for every target except Nacional (≈0), meaning even the best models still underperform a naive mean in absolute terms; MAPE looks more flattering but can mask this.

**Model selection methodology:** walk-forward (expanding-window, 1-step-ahead) cross-validation confined to 2023-2024, median-aggregated across ~8 folds per target (median chosen over mean because a single divergent SARIMA fold can otherwise dominate). The winner is committed to *before* ever touching the 2025 test set; the test MAPE/R² reported is a single honest out-of-sample number, not a result of picking among candidates after seeing their test performance.

**Current best model per target** (as of 2026-06-16, see Section 4 table): SARIMA for Nacional, Gompertz for Madrid/Cataluña/Valencia, Logistic for Andalucía.

**Known weaknesses of the current approach:**
- Each of the 5 targets is modelled **independently** — no pooling of information across regions, despite all 5 sharing the same national adoption wave and macro environment. This means each model effectively has only ~21-23 usable training observations.
- 1-step-ahead walk-forward validation does not fully replicate the actual 12-month-ahead forecasting task, so it can occasionally select a model (e.g. Ridge, before the growth curves were added) that looks fine 1 month out but extrapolates badly over a full year.
- No hyperparameter tuning via cross-validation for Ridge/RF/XGBoost — values are hand-picked, partly to avoid adding yet another source of test-set-adjacent overfitting risk on this little data.

---

## 8. Key Decisions and Assumptions

- **Target variable = total market demand (CORES consumption), not Repsol sales.** No Repsol-internal sales data exists in this project; this is explicitly a macro/external-market forecast.
- **5 modelling targets only**: ESPAÑA (national) + Madrid, Cataluña, Andalucía, Comunitat Valenciana. All other CCAAs are present in `master_dataset.csv` (for context/EDA) but are never modelled individually.
- **Forecast horizon fixed at 24 months** (2026-01 → 2027-12), monthly granularity, matching the project brief.
- **Train/test split is temporal, not random**: 2023-2024 train, 2025 test — required for any time-series evaluation to be meaningful, and enforced consistently across every notebook.
- **Macro features must be lagged by 1 month minimum** before use as model inputs, because INE publishes IPI/IPC/unemployment with a real delay. Quarterly EPA data is shifted by a full quarter for the same reason. This was a deliberate fix this session (see Section 4) — any new macro series added in the future must follow the same convention.
- **Model selection must never use the test set.** Walk-forward CV inside the training window is the only sanctioned way to choose a model family per target. This is a hard rule going forward, established after finding the original pipeline violated it.
- **A new candidate model is only adopted if it wins (or ties) the existing walk-forward selection — never by manually overriding the selection after seeing test results.** This is exactly how the Logistic/Gompertz curves were added and validated.
- **Gasolina 98 is genuinely not sold in Melilla** — the resulting 36 NaN rows in `master_dataset.csv` are expected, not a data quality bug.
- **Provincial-level consumption and single-month tourism data are deliberately excluded** from the master dataset (see `datasets_excluded_from_master.md`) — granularity mismatch and insufficient time coverage, respectively.
- **DGT vehicle fleet data is a known gap**, not yet sourced (no public API; needs manual download).

---

## 9. Current Status

**Data pipeline:** Complete and stable. `master_dataset.csv` and the feature tables are correct and incorporate the EPA publication-delay fix.

**Modelling pipeline:** Complete for the current candidate set (6 models). The walk-forward-selected model per target, and its honestly-reported 2025 test metric, are:

| Target | Model | MAPE | R² |
|---|---|---|---|
| Nacional | SARIMA | 29.0% | -0.009 |
| Madrid | Gompertz | 197.1% | -101.0 |
| Cataluña | Gompertz | 164.2% | -91.3 |
| Andalucía | Logistic | 48.4% | -1.56 |
| Valencia | Gompertz | 34.2% | -1.25 |

**Verification status:** A full leakage audit was performed, two critical leaks and a model-selection bias were fixed, and the fix was independently double-checked (catching and correcting one mid-session regression). The growth-curve addition was independently re-verified for leakage and reproducibility on 2026-06-16. **As of now, the pipeline is believed leakage-free and error-free**, with the explicit caveat that absolute model fit (R²) remains poor for Madrid and Cataluña — this is a data-size limitation, not a known bug.

**Git status:** Local `main` branch is **2 commits ahead of `origin/main`**, neither pushed yet:
- `37ead38` — the leakage-fix + walk-forward-selection commit.
- `d60cbef` — the Logistic/Gompertz growth-curve addition + creation of this `memory.md`.
The subsequent SARIMAX experiment (see Section 4) was fully reverted and never committed, so it left no trace — the working tree as of this update matches `d60cbef` exactly, plus this edit to `memory.md` itself.

**Outstanding documentation debt:** `DATA_AUDIT_REPORT.md` and `NOTEBOOKS_AUDIT.md` (both dated 2026-06-10) predate this session's fixes and the growth-curve work; their model lists and row counts are stale. They have not been regenerated — this `memory.md` file is the current source of truth until they are.

**Next priorities (not yet started), in order of expected impact:**
1. **Pool the 5 regional series into one model** instead of fitting each independently — directly targets the small-effective-sample-size problem (~21-23 rows/target today) that's the most fundamental constraint on model quality. Confirmed as the top recommendation by both the original deep-dive analysis *and* the later external model-research pass (Section 4) — not yet implemented. **This is the current single highest-priority next step.**
2. **Reduce feature collinearity for Ridge** (`Tendencia`/`Lag_1`/`Lag_2`/`Lag_3`/`Roll_mean_3`/`Roll_mean_6` were found pairwise-correlated at 0.84-1.00) — e.g. switch to Elastic Net, which the model-research pass flagged as a near-zero-cost fix for exactly this problem. Lower priority than #1 since the growth curves already made Ridge's worst failure modes moot in practice, but the underlying collinearity is still unaddressed.
3. SARIMAX has already been tried (plain macro exogenous regressors) and rejected — see Section 4. Don't repeat that exact test; if exogenous-variable modelling is revisited, do it after #1 (pooling) or with a richer regressor set (e.g. fuel prices).
4. Source DGT vehicle fleet data (currently a placeholder).
5. Regenerate the Tableau export step (`tableau_dashboard.csv` etc. are stale relative to the current model set) — the notebook that built them (`07_tableau_prep.ipynb`) was deleted; this logic needs to be reintroduced or rebuilt, likely as an addition to notebook 09.
6. Decide whether/when to push the 2 pending local commits to `origin/main`.

---

## 10. Future Instructions for Claude

- **Read this file first**, before doing any other work in this repository, in any new session.
- Treat this file as the **source of truth** for project state, decisions, and conventions — prefer it over `README.md`, `DATA_AUDIT_REPORT.md`, and `NOTEBOOKS_AUDIT.md` where they conflict, since those three are known to be partially stale (see Sections 5, 6, 9).
- Before relying on any specific claim in this file that names a file, function, or result (e.g., "`ML_FEATS` contains X", "Gompertz is selected for Madrid"), **verify it against the actual current repo state** — re-read the relevant notebook cell or re-run the relevant CSV check — rather than assuming this file is still accurate. Treat this file as a snapshot in time, not a live source.
- **Never reintroduce the two leaks fixed in Section 4**: (a) never use contemporaneous (non-lagged) `IPI_original`/`IPC_var_anual`/`Tasa_paro` as a model feature, only `_lag1`; (b) never let quarterly macro data (like EPA unemployment) get forward-filled into months before it would actually have been published.
- **Never select a model family using test-set performance.** Any new candidate model must go through the same walk-forward CV gate (inside 2023-2024 only) as the existing six, and must only be adopted if it wins or ties that CV — exactly as was done for the Logistic/Gompertz addition.
- **When editing notebook `.ipynb` files programmatically** (via `nbformat`), always re-read the file fresh from disk immediately after writing to confirm the edit actually persisted — a real bug this session came from a bundled multi-edit script that crashed before its `nbformat.write()` call, silently discarding an earlier successful edit in the same script. Prefer one isolated read-modify-write-verify script per logical change over bundling several edits together.
- **When changing a feature list** (`ML_FEATS`, `ML_BASE`, `ML_PRICE`), grep for any code elsewhere that builds a model input row by **fixed position** (`np.array([[...]])` with positional values) rather than by feature name — this exact bug class broke the recursive forecast functions in both notebook 07 and 08 once before, and would break silently again.
- **Update this file** whenever a major change happens: a new model is added/removed, a new leak is found and fixed, the target/scope changes, a new data source is integrated, or the git/commit state materially changes. Keep Section 9 ("Current Status") especially current, since it's the section most likely to go stale fastest.
