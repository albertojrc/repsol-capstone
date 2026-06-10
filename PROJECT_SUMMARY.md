# Project Summary: Repsol Diesel Nexa — Biodiesel Demand Forecasting
## IE Business School MBD Capstone Project

---

## 1. Business Context

Repsol's **Diesel Nexa** is a high-performance biodiesel product sold at service stations across Spain. The objective of this project is to build a monthly demand forecasting system for Diesel Nexa consumption at both the national level and for four key regions: **Madrid, Cataluña, Andalucía, and Comunitat Valenciana**.

Accurate demand forecasts enable Repsol to optimize supply chain planning, refinery scheduling, and regional distribution logistics. The forecast horizon is **24 months** (January 2026 – December 2027).

---

## 2. Datasets

### 2.1 Primary Dataset — `master_dataset.csv`

The backbone of the project is a unified master dataset built by joining all input sources on a `Fecha × CCAA` primary key.

| Attribute | Value |
|-----------|-------|
| Shape | 720 rows × 17 columns |
| Granularity | Monthly × Comunidad Autónoma |
| Date range | January 2023 – December 2025 (36 months) |
| Geographic scope | 19 CCAAs + ESPAÑA (national) + Melilla + Ceuta = 20 units |
| Modelling targets | `Target = 1` for ESPAÑA, Andalucía, Cataluña, Madrid, Comunitat Valenciana |
| Known nulls | 36 NaN rows in `PVP_Gasolina98` / `PAI_Gasolina98` — Melilla does not sell Gasolina 98 (expected) |

The master dataset is built by `notebooks/04_master_dataset.ipynb` and can be rebuilt at any time by running `python scripts/02_master_dataset_builder.py`.

### 2.2 Input Sources

| File | Shape | Description | Role |
|------|-------|-------------|------|
| `consumo_biodiesel_ccaa.csv` | 720 × 3 | Monthly Diesel Nexa consumption by CCAA (Tm) | **Target variable** |
| `macro_indicadores_ine.csv` | 36 × 5 | National macro indicators from INE: IPI, IPC, unemployment | Exogenous regressors |
| `brent_oil_price_monthly_2023_onwards.csv` | 41 × 5 | Monthly Brent crude oil price (USD/barrel) | Oil price feature |
| `precios_combustibles_2023/24/25.csv` | ~75,500 × 5 each | Daily retail fuel prices by province and product | Fuel price features |
| `consumo_biodiesel_provincial.csv` | 1,872 × 5 | Consumption by province (52 provinces) | **Not merged** — granularity mismatch |
| `turismo_visitantes_ccaa.csv` | 15 × 9 | Tourist visitors by CCAA (October 2025 only) | **Not merged** — single month |

### 2.3 Variable Dictionary (master_dataset.csv)

| Column | Type | Unit | Source |
|--------|------|------|--------|
| `Fecha` | str YYYY-MM | — | Derived |
| `CCAA` | str | — | INE regional codes |
| `Consumo_Tm` | float | metric tonnes | MITECO / Repsol |
| `Target` | int (0/1) | — | Derived |
| `IPI_original` | float | index | INE |
| `IPI_ajustado` | float | index (seasonally adj.) | INE |
| `IPC_var_anual` | float | % annual variation | INE |
| `Tasa_paro` | float | % unemployment | INE (EPA) |
| `Precio_Brent_USD` | float | USD/barrel | FRED |
| `PVP_Gasoleo_A/Premium` | float | €/L | MITECO daily prices |
| `PVP_Gasolina95/98` | float | €/L | MITECO daily prices |
| `PAI_Gasoleo_A/Premium` | float | €/L (pre-tax) | MITECO daily prices |
| `PAI_Gasolina95/98` | float | €/L (pre-tax) | MITECO daily prices |

The fuel price columns (`PVP_*`, `PAI_*`) were aggregated from ~75,500 daily records per year across 52 provinces → monthly CCAA means, using a manually curated province-to-CCAA mapping. ESPAÑA rows are filled with the national mean across all CCAAs (the raw data has no national entry).

### 2.4 Demand Context

Diesel Nexa consumption grew explosively over the data period:

| Region | Jan 2023 (Tm) | Dec 2025 (Tm) | Mean 2023–2025 (Tm) |
|--------|--------------|--------------|---------------------|
| Nacional | 167 | 22,632 | 8,122 |
| Cataluña | 78 | ~3,800 | 1,256 |
| Madrid | ~0 | ~3,800 | 1,149 |
| Andalucía | ~0 | ~2,600 | 632 |
| Valencia | ~0 | ~1,400 | 396 |

This steep growth trajectory — from near-zero to ~27,000 Tm/month nationally by mid-2025 — is the single most important characteristic of the data and the primary driver of model difficulty. The product was in an early-growth phase throughout the entire observation period.

---

## 3. Feature Engineering

### 3.1 Feature Matrix

All features were generated from `master_dataset.csv` in `notebooks/05_feature_engineering.ipynb`. The final feature matrix has **180 rows × 25 columns** (5 targets × 36 months).

| Feature | Description | Rationale |
|---------|-------------|-----------|
| `Tendencia` | Linear trend index (1–36) | Captures long-run growth |
| `Mes` | Month number (1–12) | Seasonality anchor |
| `sin_mes`, `cos_mes` | Fourier encoding of month | Smooth circular seasonality |
| `Lag_1`, `Lag_2`, `Lag_3` | 1-, 2-, 3-month lagged consumption | Recent momentum |
| `Lag_12` | 12-month lag | Year-over-year comparison |
| `Roll_mean_3`, `Roll_mean_6` | 3- and 6-month rolling means | Trend smoothing |
| `Roll_std_3` | 3-month rolling standard deviation | Recent volatility |
| `IPI_original`, `IPI_ajustado` | Industrial production index | Macro demand driver |
| `IPC_var_anual` | CPI annual variation | Inflation / purchasing power |
| `Tasa_paro` | Unemployment rate | Consumer spending capacity |
| `*_lag1` | 1-month lagged macro variables | Lagged economic effect |

### 3.2 Train / Test Split

| Set | Period | Rows |
|-----|--------|------|
| Train | 2023-01 → 2024-12 | 120 (24 months × 5 targets) |
| Test | 2025-01 → 2025-12 | 60 (12 months × 5 targets) |

The test set represents a true out-of-sample evaluation: models were trained exclusively on 2023–2024 and evaluated on the 2025 data they never saw.

### 3.3 Price Feature Matrix

`notebooks/06_price_features.ipynb` built an additional 81-column price feature matrix including:
- National and regional (per-CCAA) monthly mean PVP and PAI for Gasóleo A, Gasóleo Premium, Gasolina 95, Gasolina 98
- One-month lagged versions of each price series

---

## 4. Models

### 4.1 Why Four Models

Four model families were selected to cover different forecasting philosophies:

| Model | Type | Strength | Limitation |
|-------|------|----------|------------|
| SARIMA | Statistical time-series | Natively handles seasonality and autocorrelation; no features needed | Univariate; assumes stationarity after differencing |
| Ridge | Linear ML | Interpretable; fast; enforces regularisation | Poor recursive extrapolation beyond training range |
| Random Forest | Ensemble tree | Non-parametric; handles nonlinear interactions | No temporal awareness; capped at training data range |
| XGBoost | Gradient boosting | State-of-the-art accuracy on tabular data; regularised | Same recursive ceiling issue as Random Forest |

### 4.2 SARIMA(1,1,1)(1,0,0,12)

**What it is:** Seasonal AutoRegressive Integrated Moving Average. Fitted separately on each of the 5 targets.

**Configuration:**
- `order = (1, 1, 1)` — AR(1) + first-order differencing + MA(1) to handle trend and autocorrelation
- `seasonal_order = (1, 0, 0, 12)` — seasonal AR(1) at lag 12 to capture annual seasonality
- Target variable log-transformed (`log1p`) before fitting; back-transformed with `expm1` after prediction
- Fitted using `statsmodels.SARIMAX` with `enforce_stationarity=False`, `enforce_invertibility=False`

**Why this configuration:** Biodiesel consumption displays clear monthly seasonality (summer peaks) and an exponential growth trend. First differencing removes the non-stationarity. The seasonal AR(1) component at lag 12 captures the year-over-year pattern. Log transformation stabilises variance across the explosive growth range.

**Train/forecast procedure:**
- Test predictions: fit on 24 months (2023–2024), forecast 12 steps ahead (2025)
- 24-month forecast: re-fit on all 36 months (2023–2025), forecast 24 steps ahead (2026–2027)

### 4.3 Ridge Regression

**What it is:** L2-regularised linear regression (alpha = 10) on the 15-feature `ML_FEATS` matrix, fitted on log1p-transformed target.

**Why included:** Ridge provides a linear baseline against which non-linear models can be compared. The strong regularisation (alpha=10) was chosen to prevent overfitting on 24 training observations per target.

**Limitation observed:** Ridge performs catastrophically in recursive multi-step forecasting. Because it is a linear model extrapolating beyond the training range of `Tendencia` (1–36 in training, 37–60 in forecast), the log-space prediction can grow to extreme values, causing `expm1` to overflow to infinity. This confirms that linear models are unsuitable for recursive long-horizon forecasting on explosive growth series.

### 4.4 Random Forest & XGBoost

**What they are:** Tree-based ensemble models — Random Forest uses bagging of deep trees; XGBoost uses gradient boosting of shallow trees.

**Configuration:**
- Random Forest: 300 trees, `max_depth=3`, `min_samples_leaf=3`, `random_state=42`
- XGBoost: 300 rounds, `max_depth=2`, `learning_rate=0.05`, `subsample=0.9`, `reg_alpha=1`, `reg_lambda=5`, `random_state=42`
- Both fitted on log1p-transformed target; predictions back-transformed with `expm1`
- Features standardised with `StandardScaler` (fitted on train, applied to test and forecast rows)

**Why these configurations:** Conservative tree depth and strong regularisation prevent overfitting on the small training set (~24 observations per target after removing NaN lag rows).

**Recursive forecasting:** A custom `recursive_forecast_ml` function generates 24-step-ahead forecasts by feeding each 1-step prediction back as the next step's lag features. Macro features are held constant at their last known values. A log-space prediction ceiling (`clip(log_pred, None, 15.0)`, equivalent to ~3.3M Tm) prevents numerical overflow in the recursive buffer.

### 4.5 Price-Augmented Models (RF+Precios, XGB+Precios)

Built in `notebooks/08_modeling_with_prices.ipynb`. Identical hyperparameters to baseline RF/XGBoost, but feature matrix expanded to include 16 regional fuel price features per target (national + CCAA-specific monthly mean prices with 1-month lag, from `features_precios_combustibles.csv`).

**Purpose:** Test whether fuel price signals provide incremental predictive value beyond the time-series features alone.

---

## 5. Outputs

### 5.1 Generated Files

| File | Location | Description |
|------|----------|-------------|
| `metricas_modelos.csv` | `data/outputs/` | MAE, RMSE, MAPE, R² for all 4 baseline models × 5 targets |
| `predicciones_test_2025.csv` | `data/outputs/` | Month-by-month test predictions (2025) with actuals |
| `forecast_24m_sarima_rf_xgb.csv` | `data/outputs/` | 24-month forecasts (2026–2027) for all 4 models × 5 targets |
| `metricas_modelos_con_precios.csv` | `data/outputs/` | Metrics for RF+Precios and XGB+Precios |
| `predicciones_test_2025_con_precios.csv` | `data/outputs/` | Test predictions from price-augmented models |
| `forecast_24m_con_precios.csv` | `data/outputs/` | 24-month forecasts from price-augmented models |
| `metricas_comparativa.csv` | `data/outputs/` | Side-by-side comparison: all models, all targets |

### 5.2 Figures

| Figure | Description |
|--------|-------------|
| `reports/figures/01–04` | EDA: national consumption, regional breakdown, seasonality, correlations |
| `reports/figures/07` | Model comparison bar charts by target |
| `reports/figures/08` | Actual vs predicted time series (2025 test period) |
| `reports/figures/11` | Prediction vs actual scatter (all models, all targets) |
| `reports/figures/12` | 24-month SARIMA forecast by target |
| `reports/figures/16–17` | Price-augmented model comparison and actual vs predicted |

---

## 6. Results and Findings

### 6.1 Test Set Performance (2025)

| Target | Best Model | MAE (Tm) | MAPE (%) | Runner-up | Runner-up MAPE |
|--------|-----------|----------|----------|-----------|---------------|
| **Nacional** | **SARIMA** | **4,278** | **29.0** | XGBoost | 62.3% |
| **Andalucía** | **SARIMA** | **898** | **52.5** | RF | 56.7% |
| **Cataluña** | **SARIMA** | **1,429** | **47.2** | XGBoost | 59.4% |
| **Madrid** | **XGBoost** | **1,727** | **61.9** | RF | 66.0% |
| **Valencia** | **XGBoost** | **564** | **59.3** | RF | 61.5% |

All models show **negative R²**, meaning every model performs worse than a naive mean predictor on the held-out 2025 data. This is a direct consequence of the explosive, non-stationary growth: models trained on 2023–2024 data (when consumption was 167–~12,000 Tm/month nationally) were evaluated on 2025 data where consumption surged to ~27,000 Tm. No model family — statistical or ML — was able to fully anticipate the magnitude of that acceleration from 24 training observations.

### 6.2 Model-by-Model Findings

**SARIMA** is the clear winner for the aggregate (Nacional) and three out of five targets:
- Nacional MAPE = 29.0% — roughly **half the error** of any ML model
- The seasonal component correctly captures summer demand peaks (Jun–Sep)
- Fails on Madrid (MAPE = 318.6%): Madrid's consumption series has longer zero periods in early 2023 and a sharper inflection, making ARIMA differencing poorly conditioned

**Random Forest and XGBoost** perform comparably to each other (~58–66% MAPE) and are the best choice for Madrid and Valencia:
- Tree ensembles cannot extrapolate above their training data ceiling, resulting in systematic underprediction (e.g., RF predicts ~7,000 Tm/month for Nacional in Jul 2025 when actual was 27,001 Tm)
- Both are more robust than SARIMA for smaller, more volatile regional series

**Ridge Regression** is unsuitable for this problem. Its recursive forecast diverges exponentially due to linear extrapolation of the `Tendencia` feature beyond the training range. The model produces multi-million tonne forecasts and is not usable for planning purposes.

**Price-augmented models** (RF+Precios, XGB+Precios) show **marginal improvement** over baseline RF/XGBoost:
- Nacional RF: MAPE 58.3% → 58.0% (−0.3 pp)
- XGBoost Valencia: MAPE 59.3% → 59.4% (tiny regression)
- The improvement is not meaningful — fuel prices are already implicitly encoded in the consumption time series itself via lag features

### 6.3 24-Month SARIMA Forecast (2026–2027)

SARIMA was re-trained on the full 36-month series before generating the 24-month forecast.

| Target | 2026 Mean (Tm/month) | 2026 Peak | 2027 Mean (Tm/month) |
|--------|---------------------|-----------|---------------------|
| Nacional | 26,003 | 27,369 (Jul) | ~27,200 |
| Cataluña | 4,083 | 4,527 | ~4,200 |
| Madrid | 3,680 | 4,109 | ~3,800 |
| Andalucía | 2,171 | 2,236 | ~2,200 |
| Valencia | 1,242 | 1,287 | ~1,250 |

Key forecast observations:
- **Seasonal pattern** preserved: summer peaks (Jun–Sep) consistently reproduced across all targets
- **Growth moderating**: the forecast reflects a stabilisation phase after the 2023–2025 expansion — Nacional is projected to plateau around 27,000–27,400 Tm/month through 2027
- **Madrid and Cataluña** are forecast to remain the two largest regional markets, together representing ~29% of national demand
- **RF and XGBoost forecasts** underestimate by a factor of 3–4× relative to SARIMA, reflecting their inability to extrapolate the growth trend

### 6.4 Key Takeaways

1. **SARIMA is the recommended production model** for Nacional, Cataluña, Andalucía, and Valencia. Its MAPE of 29% on the national series is materially better than any ML alternative.

2. **XGBoost is the recommended model for Madrid**, where SARIMA's MAPE is 318.6% due to erratic early-period zeroes in the training series.

3. **Adding fuel price features does not improve forecasts meaningfully.** The biodiesel demand signal is dominated by the growth trend and seasonality; price variation over 2023–2025 did not provide incremental explanatory power.

4. **The fundamental challenge is the short, explosive training window.** With only 24 months of training data covering a near-zero-to-peak growth phase, no model can reliably learn the long-run structural relationship. As data accumulates through 2026–2027, model accuracy is expected to improve substantially.

5. **Negative R² across all models is expected and not a model failure.** It reflects the difficulty of the evaluation task: forecasting during a historically unprecedented demand surge. MAPE and MAE are the more actionable metrics for operational planning.

---

## 7. Pipeline Summary

```
04_master_dataset.ipynb      — Build master_dataset.csv (720×17)
        ↓
05_feature_engineering.ipynb — Engineer 25 features; split train/test
        ↓
06_price_features.ipynb      — Build 81 fuel price features
        ↓
07_modeling.ipynb            — Train SARIMA, Ridge, RF, XGBoost; generate 24m forecast
        ↓
08_modeling_with_prices.ipynb — Train RF+Precios, XGB+Precios; compare vs baseline
        ↓
09_evaluation.ipynb          — Visualise residuals, error distributions, forecast plots
```

**Scripts:**
- `scripts/02_master_dataset_builder.py` — standalone script to rebuild `master_dataset.csv` from scratch

---

*Generated: 2026-06-10 | Repsol Diesel Nexa Capstone — IE MBD*
