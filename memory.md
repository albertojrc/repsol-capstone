# Project Memory - Repsol Eco-Fuels Demand Forecasting Capstone

**Last updated:** 2026-06-23
**Maintainer note:** This file is the long-term source of truth for this project. See [Section 10](#10-future-instructions-for-claude) for how Claude should use and maintain it.

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

- `data/features/features_modelo_completo.csv`: 180 rows x 36 columns
- `data/features/features_train.csv`: 120 rows x 36 columns
- `data/features/features_test.csv`: 60 rows x 36 columns

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
Spain has two distinct legislative drivers that directly determine how much biodiesel must be blended into the diesel pool:

1. **Mandato de Energia (Mandato_Energia_Pct)**: Annual national biofuel blending obligation (% of energy content of all transport fuels) set by successive Royal Decrees and project assumptions. Increased year-on-year: 10.5% (2023), 11.0% (2024), 11.5% (2025), **14.0% (2026, RD 5/2026 signed 10 Jan 2026)**, 15.5% (2027 projected using +1.5 percentage points).
2. **Mandato de Mezcla Biodiesel (Mandato_Biodiesel_Blend_Pct)**: Volumetric biodiesel-into-Gasoleo-A blend requirement introduced by Decreto 61/2023. Activated August 2024 at 3%; rises to 7.5% from 2028. Zero before August 2024.

Both are deterministic policy variables -- not forecasts, no uncertainty -- so they can be used as features without leakage risk. Their future values are known from the legislation.

#### What was built
A new input file `data/inputs/mandato_biocarburantes.csv` was created with the full mandate schedule 2016-2030 (annual rows). Notebooks 05, 07, and 08 were updated, and the current script path was also updated so CNMC and mandate features coexist in the same production feature tables:

- **`05_feature_engineering.ipynb` / `scripts/04_build_features.py`**: Mandate CSV loaded, joined at monthly granularity (with the `Mandato_Biodiesel_Blend_Pct` set to 0.0 for all months before August 2024), and merged onto the feature matrix. The current script output has 36 columns: 34 CNMC-aware columns plus 2 mandate columns.
- **`07_modeling.ipynb` / `scripts/05_modeling_with_cnmc.py`**: `ML_FEATS` now contains 18 features: 12 baseline calendar/target/macro features, 4 lagged CNMC diesel-market features, and 2 mandate features. The recursive ML forecast function passes mandate values forward using the 2026-2027 schedule: `Mandato_Energia_Pct = 14.0` in 2026 and `15.5` in 2027, with `Mandato_Biodiesel_Blend_Pct = 3.0` (Decreto 61/2023, 3% through 2027).
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

**Feature set** (`ML_FEATS`, used by Ridge/RF/XGBoost only, 18 features total as of 2026-06-19): `Tendencia` (trend index), `Mes`, `sin_mes`/`cos_mes` (cyclical month encoding), `Lag_1`/`Lag_2`/`Lag_3` (target lags), `Roll_mean_3`/`Roll_mean_6` (rolling means), `IPI_original_lag1`, `IPC_var_anual_lag1`, `Tasa_paro_lag1` (lagged macro -- **never the contemporaneous value**, see Section 4), plus the lagged CNMC diesel-market features `GasoleoA_Tm_lag1`, `GasoleoA_Tm_roll3_lag1`, `Biodiesel_GasoleoA_Ratio_lag1`, `Biodiesel_GasoleoA_Ratio_roll3_lag1`, **plus `Mandato_Energia_Pct` and `Mandato_Biodiesel_Blend_Pct`** (deterministic policy features, no lag needed, future values read from the mandate schedule). `Lag_12` exists in the feature table but is excluded from the model feature lists due to excessive NaN loss.

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
python scripts/03_clean_cnmc_petroleum.py
python scripts/02_master_dataset_builder.py
python scripts/04_build_features.py
python scripts/05_modeling_with_cnmc.py
```

**Modelling pipeline:** Complete for the current candidate set (7 models). The walk-forward-selected model per target, and its honestly-reported 2025 test metric, are:

| Target | Model | MAPE | R² |
|---|---|---|---|
| Nacional | SARIMA | 29.0% | -0.009 |
| Madrid | Gompertz | 197.1% | -101.0 |
| Cataluña | Gompertz | 164.2% | -91.3 |
| Andalucía | Logistic | 48.4% | -1.56 |
| Valencia | Gompertz | 34.2% | -1.25 |

**Verification status:** A full leakage audit was performed, two critical leaks and a model-selection bias were fixed, and the fix was independently double-checked. The growth-curve addition was independently re-verified for leakage and reproducibility on 2026-06-16. The CNMC integration was verified on 2026-06-19:

**Git status (2026-06-21):** `main` is in sync with `origin/main` (the earlier leakage-fix, growth-curve, and SARIMAX-log commits — `37ead38`, `d60cbef`, `9f93e82` — are all pushed). Current work is on branch **`enrico`**, which so far contains only this `memory.md` update documenting the 2026-06-21 pooling investigation and the recommended multi-step-gate fix — no notebook/model changes yet.
- raw CNMC files parse cleanly,
- CNMC biodiesel reconciles exactly to the existing target,
- national `ESPAÑA` Gasoleo A is independently summed from all 19 CCAA,
- no 2026 CNMC rows enter the model-origin data,
- CNMC model inputs are lagged only,
- and mandate features are present with the biodiesel blend requirement set to 0.0 before August 2024.

**Important modeling caveat:** The pipeline is believed leakage-free, but the absolute model fit remains weak. CNMC improves the project's business structure, not the core statistical limitation. Pooled regional ML is now documented as a sensitivity experiment only; the final selected model set is non-pooled.

**Git status:** As of this update, local `main` contains unpushed commits beyond `origin/main`, including the leakage fixes, growth-curve additions, research notes, CNMC integration, and this documentation update. Before pushing, verify with:

```powershell
git status --short --branch
git log --oneline --decorate -5
```

**Outstanding documentation debt:** The current README, `DATA_AUDIT_REPORT.md`, `NOTEBOOKS_AUDIT.md`, and `PHASE2_MODELING_REPORT.md` have been refreshed for the final no-pooling policy. Older historical sections in this memory file should be treated as chronology, not current instructions.

**Next priorities, in order of expected impact:**
1. Preserve the current script-first workflow and run `scripts/06_validate_outputs.py` after every full rebuild.
2. Treat final forecasts as directional planning scenarios because selected-model R2 values remain weak or negative.
3. Consider stronger backtesting only if more history becomes available; the current 2023-2025 window is too short to provide a pristine final test.
4. Source DGT vehicle fleet data if the project needs a new external driver.
5. SARIMAX has already been tried with plain macro exogenous regressors and rejected; do not repeat that exact test without a richer regressor set or a changed design.

---

## 10. Future Instructions for Claude

- **Read this file first**, before doing any other work in this repository, in any new session.
- Treat this file as project memory, but prefer the refreshed `README.md`, `DATA_AUDIT_REPORT.md`, and `NOTEBOOKS_AUDIT.md` for current delivery instructions and file shapes.
- Before relying on any specific claim in this file that names a file, function, or result (e.g., "`ML_FEATS` contains X", "Gompertz is selected for Madrid"), **verify it against the actual current repo state** — re-read the relevant notebook cell or re-run the relevant CSV check — rather than assuming this file is still accurate. Treat this file as a snapshot in time, not a live source.
- **Never reintroduce the two leaks fixed in Section 4**: (a) never use contemporaneous (non-lagged) `IPI_original`/`IPC_var_anual`/`Tasa_paro` as a model feature, only `_lag1`; (b) never let quarterly macro data (like EPA unemployment) get forward-filled into months before it would actually have been published.
- **Never use contemporaneous CNMC market variables as model features for the same month.** `GasoleoA_Tm` and `Biodiesel_GasoleoA_Ratio` must enter models through lagged/rolling-lagged features only, unless the forecast design explicitly changes and is documented.
- **Do not silently change the forecast origin by using Jan-Feb 2026 CNMC actuals.** Those rows exist in processed CNMC files for future use, but the current capstone forecast is intentionally generated as if standing at 2025-12.
- **When rebuilding national CNMC features, sum all 19 CCAA.** Never build the national series from only Madrid, Cataluña, Andalucía, and Valencia.
- **Never select a model family using test-set performance.** Any new candidate model must go through the same walk-forward CV gate (inside 2023-2024 only) as the existing seven, and must only be adopted if it wins or ties that CV — exactly as was done for the Logistic/Gompertz and Diesel Share additions.
- **When editing notebook `.ipynb` files programmatically** (via `nbformat`), always re-read the file fresh from disk immediately after writing to confirm the edit actually persisted — a real bug this session came from a bundled multi-edit script that crashed before its `nbformat.write()` call, silently discarding an earlier successful edit in the same script. Prefer one isolated read-modify-write-verify script per logical change over bundling several edits together.
- **When changing a feature list** (`ML_FEATS`, `ML_BASE`, `ML_PRICE`), grep for any code elsewhere that builds a model input row by **fixed position** (`np.array([[...]])` with positional values) rather than by feature name — this exact bug class broke the recursive forecast functions in both notebook 07 and 08 once before, and would break silently again.
- **Update this file** whenever a major change happens: a new model is added/removed, a new leak is found and fixed, the target/scope changes, a new data source is integrated, or the git/commit state materially changes. Keep Section 9 ("Current Status") especially current, since it's the section most likely to go stale fastest.
