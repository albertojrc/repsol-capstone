# Notebooks Audit
## Repsol Diesel Nexa — Capstone Project

**Generated:** 2026-06-10  
**Total notebooks:** 10  
**Pipeline order:** 01 → 02 → 03 → 10 → 04 → 05 → 06 → 07 → 08 → 09

---

## Notebook Inventory

| # | Notebook | Primary inputs | Primary outputs | Uses master_dataset | Hardcoded paths removed |
|---|----------|---------------|-----------------|---------------------|------------------------|
| 01 | `01_eda.ipynb` | consumo_biodiesel_ccaa.csv | figures 01–04 | No (EDA only) | N/A |
| 02 | `02_cleaning.ipynb` | consumo_biodiesel_ccaa.csv | consumo_biodiesel_targets.csv | No | N/A |
| 03 | `03_external_data.ipynb` | brent + macro raw | macro_indicadores_ine.csv, brent csv | No | N/A |
| 10 | `10_master_dataset.ipynb` | All inputs | **master_dataset.csv** | Builds it | N/A |
| 04 | `04_feature_engineering.ipynb` | master_dataset.csv | features_*.csv | **Yes** | Yes |
| 05 | `05_modeling.ipynb` | features_*.csv, master_dataset.csv | metricas_modelos.csv, predictions, forecast | **Yes** | Yes |
| 06 | `06_evaluation.ipynb` | outputs + features, master_dataset.csv | figures 07–11 | **Yes** | Yes |
| 07 | `07_tableau_prep.ipynb` | master_dataset.csv, outputs | tableau_dashboard.csv, metrics, pivot | **Yes** | Yes |
| 08 | `08_price_features.ipynb` | precios_combustibles_*.csv, master_dataset.csv | features_precios_combustibles.csv | **Yes** | Yes |
| 09 | `09_modeling_with_prices.ipynb` | features_*.csv, master_dataset.csv, outputs | metricas_*_con_precios.csv, forecast | **Yes** | Yes |

---

## Detailed Notebook Descriptions

### `01_eda.ipynb` — Exploratory Data Analysis
- **Inputs:** `data/inputs/consumo_biodiesel_ccaa.csv`
- **Outputs:** Figures `01_consumo_nacional.png`, `02_consumo_regional.png`, `03_estacionalidad_tendencia.png`, `04_correlaciones.png`
- **master_dataset:** Not applicable (EDA predates master dataset construction)
- **Path variables:** Uses `DATA_INPUTS`, `FIGURES`
- **Status:** No changes needed

---

### `02_cleaning.ipynb` — Data Cleaning
- **Inputs:** Raw consumption data
- **Outputs:** `consumo_biodiesel_targets.csv`, `consumo_biodiesel_ccaa.csv`
- **master_dataset:** Not applicable (produces inputs for master)
- **Status:** No changes needed

---

### `03_external_data.ipynb` — External Data Integration
- **Inputs:** Raw Brent price data, INE macro downloads
- **Outputs:** `brent_oil_price_monthly_2023_onwards.csv`, `macro_indicadores_ine.csv`
- **master_dataset:** Not applicable (produces inputs for master)
- **Status:** No changes needed

---

### `10_master_dataset.ipynb` — Master Dataset Builder ⭐
- **Inputs:** All 6 input CSVs (consumption + macro + Brent + fuel prices)
- **Outputs:** `data/inputs/master_dataset.csv` (720 × 17)
- **Key logic:**
  - Builds Fecha×CCAA base (720 = 19 CCAAs + ESPAÑA + Melilla + Ceuta × 36 months)
  - Joins macro (ESPAÑA rows only, broadcast to all CCAAs)
  - Joins Brent price
  - Aggregates fuel prices from daily×province → monthly×CCAA via 52-province mapping
  - Pivots 4 products × 2 price types → 8 wide columns
  - Target flag: 1 for ESPAÑA, Andalucía, Cataluña, Madrid Comunidad de, Comunitat Valenciana
- **Known gaps:** 36 NaN rows for Gasolina98 (Melilla — expected)
- **Status:** Complete. Also exists as script: `scripts/02_master_dataset_builder.py`

---

### `04_feature_engineering.ipynb` — Feature Engineering ✅ UPDATED
- **Inputs:** `master_dataset.csv` (updated from `consumo_biodiesel_targets.csv` + `macro_indicadores_ine.csv`)
- **Outputs:** `features_modelo_completo.csv`, `features_train.csv`, `features_test.csv`
- **Changes made:** Cell-4 now loads targets and macro from `master_dataset.csv` using TARGET_LABEL dict
- **TARGET_LABEL mapping:**
  ```python
  'ESPAÑA' → 'Nacional', 'Madrid, Comunidad de' → 'Madrid',
  'Comunitat Valenciana' → 'Valencia', others match directly
  ```
- **Status:** Complete

---

### `05_modeling.ipynb` — Modelling (SARIMA + ML) ✅ UPDATED
- **Inputs:** `features_train.csv`, `features_test.csv`, `features_modelo_completo.csv`, `master_dataset.csv`
- **Outputs:** `metricas_modelos.csv`, `predicciones_test_2025.csv`, `forecast_24m_sarima_rf_xgb.csv`, `tableau_export_legacy.csv`
- **Changes made:** Cell-4 now reads `df_macro` from `master_dataset.csv` filtered to `CCAA == "ESPAÑA"`
- **Models:** SARIMA(1,1,1)(1,0,0,12), Ridge, Random Forest, XGBoost — all on log1p-transformed target
- **Status:** Complete

---

### `06_evaluation.ipynb` — Model Evaluation ✅ UPDATED
- **Inputs:** `metricas_modelos.csv`, `predicciones_test_2025.csv`, `forecast_24m_sarima_rf_xgb.csv`, `features_train.csv`, `features_test.csv`, `master_dataset.csv`
- **Outputs:** Figures `07_model_comparison.png` through `11_forecast_24m.png`
- **Changes made:**
  - Cell-2: replaced `DATA = REPO_ROOT / 'data' / 'processed'` with proper `DATA_INPUTS`, `DATA_FEATURES`, `DATA_OUTPUTS` definitions
  - Cell-2: `df_macro` now reads from `master_dataset.csv`
  - Cell-18: summary cell updated to use `DATA_OUTPUTS` with correct filenames
- **Status:** Complete

---

### `07_tableau_prep.ipynb` — Tableau Export Preparation ✅ UPDATED
- **Inputs:** `master_dataset.csv`, `predicciones_test_2025.csv`, `forecast_24m_sarima_rf_xgb.csv`, `metricas_modelos.csv`
- **Outputs:** `tableau_dashboard.csv` (720×10), `tableau_metricas.csv` (15×9), `tableau_forecast_pivot.csv` (24×9)
- **Changes made:**
  - Cell-2: replaced `DATA = REPO_ROOT / 'data' / 'processed'` with proper path variables
  - Cell-2: `df_hist` now built from `master_dataset.csv` (Target==1, CCAA→Target label mapping) instead of `consumo_biodiesel_targets.csv`
- **Status:** Complete

---

### `08_price_features.ipynb` — Fuel Price Feature Engineering ✅ UPDATED
- **Inputs:** `precios_combustibles_2023/24/25.csv`, `master_dataset.csv`
- **Outputs:** `features_precios_combustibles.csv`, figures `12–15`
- **Changes made:** (done in previous session)
  - Cell-2: Added missing `DATA_FEATURES` definition
  - Cell-14: reads demand data from `master_dataset.csv` with TARGET_LABEL mapping
  - Cell-18: regional correlation heatmap uses `df_demand` from master
- **Status:** Complete

---

### `09_modeling_with_prices.ipynb` — Price-Augmented Modelling ✅ UPDATED
- **Inputs:** `features_modelo_completo.csv`, `features_precios_combustibles.csv`, `metricas_modelos.csv`, `master_dataset.csv`
- **Outputs:** `metricas_modelos_con_precios.csv`, `predicciones_test_2025_con_precios.csv`, `forecast_24m_con_precios.csv`, `metricas_comparativa.csv`
- **Changes made:**
  - Cell-2: replaced `DATA = REPO_ROOT / 'data' / 'processed'` with proper path variables + `DATA_INPUTS` / `DATA_FEATURES` / `DATA_OUTPUTS`
  - Cell-2: `df_macro` now reads from `master_dataset.csv`
  - Cell-14: output verification loop updated to use `DATA_OUTPUTS` with correct filenames
- **Status:** Complete

---

## Path Variable Convention (all notebooks)

All notebooks now use the following standard path variables defined in the setup cell:

```python
NOTEBOOK_DIR  = Path().resolve()
REPO_ROOT     = NOTEBOOK_DIR.parent
DATA_INPUTS   = REPO_ROOT / 'data' / 'inputs'
DATA_FEATURES = REPO_ROOT / 'data' / 'features'
DATA_OUTPUTS  = REPO_ROOT / 'data' / 'outputs'
FIGS          = REPO_ROOT / 'reports' / 'figures'
```

**Removed:** `DATA = REPO_ROOT / 'data' / 'processed'` — this was a leftover path from a prior folder structure that no longer exists.

---

## Duplication Audit

| Duplicated logic | Where it appears | Recommendation |
|-----------------|-----------------|----------------|
| `df_macro` load from macro_indicadores_ine.csv | Notebooks 05, 06, 09 | Replaced with master_dataset in all three |
| `TARGET_LABEL` dict | Notebooks 04, 07, 08 | Defined locally in each (consistent) |
| `PROVINCE_CCAA` mapping | Notebook 10 + script 02 | Defined in both (intentional) |
| Feature list `ML_FEATS` / `ML_BASE` | Notebooks 05, 06, 09 | Defined locally in each (consistent) |
