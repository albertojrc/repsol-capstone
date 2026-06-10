# Data Audit Report
## Repsol Diesel Nexa — Capstone Project

**Generated:** 2026-06-10  
**Scope:** All CSV files in `data/inputs/`, `data/features/`, `data/outputs/`  
**Total datasets audited:** 25

---

## 1. Input Datasets (`data/inputs/`)

### 1.1 `master_dataset.csv` — PRIMARY SOURCE
| Attribute | Value |
|-----------|-------|
| Shape | 720 rows × 17 columns |
| Date range | 2023-01 → 2025-12 |
| Primary key | `Fecha` + `CCAA` |
| Null % | 0.6% (36 NaN rows in Gasolina98 — Melilla only, expected) |
| Built by | `notebooks/10_master_dataset.ipynb` |

**Columns:**

| Column | Type | Description | Source |
|--------|------|-------------|--------|
| Fecha | str (YYYY-MM) | Month | — |
| CCAA | str | Comunidad Autónoma (19 + ESPAÑA + Melilla + Ceuta) | — |
| Consumo_Tm | float | Monthly biodiesel consumption in metric tonnes | consumo_biodiesel_ccaa.csv |
| Target | int (0/1) | 1 for 5 modelling targets (ESPAÑA, Andalucía, Cataluña, Madrid, Valencia) | derived |
| IPI_original | float | Industrial Production Index (original series) | macro_indicadores_ine.csv |
| IPI_ajustado | float | IPI seasonally adjusted | macro_indicadores_ine.csv |
| IPC_var_anual | float | CPI annual variation % | macro_indicadores_ine.csv |
| Tasa_paro | float | Unemployment rate % | macro_indicadores_ine.csv |
| Precio_Brent_USD | float | Brent crude oil price (USD/barrel) | brent_oil_price_monthly_2023_onwards.csv |
| PVP_Gasoleo_A | float | Retail price Gasóleo A (€/L) — CCAA monthly mean | precios_combustibles_*.csv |
| PVP_Gasoleo_Premium | float | Retail price Gasóleo Premium (€/L) | precios_combustibles_*.csv |
| PVP_Gasolina95 | float | Retail price Gasolina 95 E5 (€/L) | precios_combustibles_*.csv |
| PVP_Gasolina98 | float | Retail price Gasolina 98 (€/L) | precios_combustibles_*.csv |
| PAI_Gasoleo_A | float | Net (pre-tax) price Gasóleo A (€/L) | precios_combustibles_*.csv |
| PAI_Gasoleo_Premium | float | Net price Gasóleo Premium (€/L) | precios_combustibles_*.csv |
| PAI_Gasolina95 | float | Net price Gasolina 95 E5 (€/L) | precios_combustibles_*.csv |
| PAI_Gasolina98 | float | Net price Gasolina 98 (€/L) | precios_combustibles_*.csv |

**Known issues:**
- `PVP_Gasolina98` and `PAI_Gasolina98` have 36 NaN rows (all for Melilla) — Gasolina 98 is not sold in Melilla. This is expected and documented.
- ESPAÑA rows for fuel price columns are filled with the national mean across all CCAAs (province-level price data has no "ESPAÑA" entry).

---

### 1.2 `consumo_biodiesel_ccaa.csv`
| Attribute | Value |
|-----------|-------|
| Shape | 720 rows × 3 columns |
| Date range | 2023-01 → 2025-12 |
| Columns | Fecha, CCAA, Consumo_Tm |
| Null % | 0% |
| Description | Monthly biodiesel consumption by CCAA (all 19 + ESPAÑA + Melilla + Ceuta) |
| Used in | `notebooks/10_master_dataset.ipynb` (merged into master_dataset) |

---

### 1.3 `consumo_biodiesel_targets.csv`
| Attribute | Value |
|-----------|-------|
| Shape | 180 rows × 4 columns |
| Date range | 2023-01 → 2025-12 |
| Columns | Fecha, CCAA, Consumo_Tm, Target |
| Null % | 0% |
| Description | Consumption for the 5 modelling targets with short Target labels (Nacional/Madrid/Cataluña/Andalucía/Valencia) |
| Used in | `notebooks/04_feature_engineering.ipynb`, `notebooks/08_price_features.ipynb` |
| Note | Superseded by `master_dataset.csv` for data loading. Target column contains short labels. |

---

### 1.4 `consumo_biodiesel_provincial.csv`
| Attribute | Value |
|-----------|-------|
| Shape | 1872 rows × 5 columns |
| Date range | 2023-01 → 2025-12 |
| Columns | Fecha, Provincia, CCAA, Consumo_Tm, Porcentaje_CCAA |
| Null % | 0% |
| Description | Monthly biodiesel consumption by province (52 provinces) |
| Merged into master | NO — province-level granularity not compatible with CCAA-level master |
| Used in | Not used in current modelling pipeline. Available for future provincial analysis. |

---

### 1.5 `macro_indicadores_ine.csv`
| Attribute | Value |
|-----------|-------|
| Shape | 36 rows × 5 columns |
| Date range | 2023-01 → 2025-12 |
| Columns | Fecha, IPI_original, IPI_ajustado, IPC_var_anual, Tasa_paro |
| Null % | 0% |
| Description | National macroeconomic indicators from INE (National Statistics Institute) |
| Merged into master | YES — joined to all CCAA rows (same national values repeated per CCAA) |
| Note | Superseded by `master_dataset.csv` for data loading. |

---

### 1.6 `brent_oil_price_monthly_2023_onwards.csv`
| Attribute | Value |
|-----------|-------|
| Shape | 41 rows × 5 columns |
| Date range | 2023-01 → 2026-05 |
| Columns | Date, Price, Open, High, Low (USD/barrel) |
| Null % | 0% |
| Description | Monthly Brent crude oil price |
| Merged into master | YES — joined as `Precio_Brent_USD` |
| Note | Has 5 extra months beyond master_dataset date range (2026-01 to 2026-05) |

---

### 1.7 `precios_combustibles_2023.csv` / `2024.csv` / `2025.csv`
| Attribute | Value |
|-----------|-------|
| Shape | ~75,500 rows × 5 columns each (daily × station × product) |
| Date range | 2023-01-01 → 2025-12-31 |
| Columns | Fecha, Provincia, Producto, PVP, PAI |
| Null % | 0% |
| Description | Daily retail fuel prices by gas station province and product type |
| Merged into master | YES — aggregated to monthly×CCAA via province→CCAA mapping, then pivoted wide |
| Products tracked | Gasóleo A habitual, Gasóleo Premium, Gasolina 95 E5, Gasolina 98 |
| Aggregation | daily×province → monthly×CCAA (mean PVP and PAI), ESPAÑA filled with national mean |

---

### 1.8 `turismo_visitantes_ccaa.csv`
| Attribute | Value |
|-----------|-------|
| Shape | 15 rows × 9 columns |
| Date range | 2025-10 only (single month) |
| Null % | 0% |
| Description | Tourist visitors by CCAA for October 2025 |
| Merged into master | NO — single month, cannot form a time series |
| Used in | Not yet integrated. Reserved for future multi-year tourism dataset. |

---

## 2. Feature Datasets (`data/features/`)

### 2.1 `features_modelo_completo.csv`
| Attribute | Value |
|-----------|-------|
| Shape | 180 rows × 25 columns |
| Date range | 2023-01 → 2025-12 |
| Null % | 3.2% (lag features are NaN for first months) |
| Description | Full feature matrix for all 5 targets — lag features, rolling means, macro lags, sin/cos seasonality |
| Built by | `notebooks/04_feature_engineering.ipynb` |

---

### 2.2 `features_train.csv` / `features_test.csv`
| Attribute | Value |
|-----------|-------|
| Shapes | 120 × 25 (train) / 60 × 25 (test) |
| Split | Train: 2023-01 → 2024-12 / Test: 2025-01 → 2025-12 |
| Null % | 4.8% train / 0% test |
| Built by | `notebooks/04_feature_engineering.ipynb` |

---

### 2.3 `features_precios_combustibles.csv`
| Attribute | Value |
|-----------|-------|
| Shape | 36 rows × 81 columns |
| Date range | 2023-01 → 2025-12 |
| Null % | 0% |
| Description | Monthly fuel price features with regional lag_1 columns (81 price series) |
| Built by | `notebooks/08_price_features.ipynb` |
| Note | Must be read with explicit `sep=','` — comma in column names can confuse auto-detection |

---

## 3. Output Datasets (`data/outputs/`)

### 3.1 `metricas_modelos.csv`
| Shape | 15 × 5 | Models × Targets, columns: Target, Model, MAE, RMSE, MAPE |

### 3.2 `predicciones_test_2025.csv`
| Shape | 180 × 5 | All model predictions on 2025 test set (all 5 targets × 3 models × 12 months) |

### 3.3 `forecast_24m_sarima_rf_xgb.csv`
| Shape | 360 × 4 | 24-month forecasts (2026-01 → 2027-12), all 5 targets × 4 models |

### 3.4 `metricas_modelos_con_precios.csv`
| Shape | 10 × 5 | Price-augmented ML model metrics (RF+Precios, XGB+Precios) |

### 3.5 `predicciones_test_2025_con_precios.csv`
| Shape | 120 × 5 | Price-augmented model predictions (2025 test set) |

### 3.6 `forecast_24m_con_precios.csv`
| Shape | 240 × 4 | 24-month forecasts from price-augmented ML models |

### 3.7 `metricas_comparativa.csv`
| Shape | 25 × 5 | Side-by-side comparison: baseline vs price-augmented vs SARIMA |

### 3.8 `tableau_dashboard.csv`
| Shape | 720 × 10 | Flat file for Tableau: historical + test + forecasts, all models |

### 3.9 `tableau_metricas.csv`
| Shape | 15 × 9 | Model metrics enriched with Rank, Mejor_Modelo, label columns |

### 3.10 `tableau_forecast_pivot.csv`
| Shape | 24 × 9 | SARIMA 24-month forecast pivoted (months × regions) |

### 3.11 `tableau_export_legacy.csv`
| Shape | 300 × 5 | Historical + SARIMA forecast (long format, legacy export) |

---

## 4. Data Quality Summary

| Issue | Affected file | Rows | Action |
|-------|--------------|------|--------|
| Gasolina98 NaN (Melilla) | master_dataset.csv | 36 | Expected — no Gasolina 98 in Melilla. Documented. |
| ESPAÑA missing from price raw data | precios_combustibles_*.csv | — | Filled with national mean across CCAAs per month. |
| Single-month tourism data | turismo_visitantes_ccaa.csv | 15 | Cannot merge — reserved for future use. |
| Provincial consumption (wrong granularity) | consumo_biodiesel_provincial.csv | 1872 | Cannot merge — CCAA-level master only. |

---

## 5. Dataset Lineage

```
RAW INPUTS
├── consumo_biodiesel_ccaa.csv        ─┐
├── macro_indicadores_ine.csv          ├── 10_master_dataset.ipynb → master_dataset.csv
├── brent_oil_price_monthly_*.csv      │
└── precios_combustibles_2023/24/25   ─┘

master_dataset.csv
└── 04_feature_engineering.ipynb → features_modelo_completo.csv
                                     features_train.csv
                                     features_test.csv
└── 05_modeling.ipynb → metricas_modelos.csv
                         predicciones_test_2025.csv
                         forecast_24m_sarima_rf_xgb.csv
└── 06_evaluation.ipynb (reads outputs, produces figures)
└── 07_tableau_prep.ipynb → tableau_dashboard.csv
                              tableau_metricas.csv
                              tableau_forecast_pivot.csv
└── 08_price_features.ipynb → features_precios_combustibles.csv
└── 09_modeling_with_prices.ipynb → metricas_modelos_con_precios.csv
                                     predicciones_test_2025_con_precios.csv
                                     forecast_24m_con_precios.csv
                                     metricas_comparativa.csv

NOT MERGED (see datasets_excluded_from_master.md)
├── consumo_biodiesel_provincial.csv
└── turismo_visitantes_ccaa.csv
```
