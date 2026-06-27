[DATA_DICTIONARY.md](https://github.com/user-attachments/files/29422294/DATA_DICTIONARY.md)
# Data Dictionary

Reference for the two canonical tables in the pipeline:

- **`data/inputs/master_dataset.csv`** — 720 rows × 22 columns. One row per
  month × autonomous community (CCAA). Monthly coverage 2023-01 → 2025-12,
  20 CCAA/national entities. Primary key: (`Fecha`, `CCAA`).
- **`data/features/features_modelo_completo.csv`** — 180 rows × 35 columns.
  The five modeled target series × 36 months. Built from the master dataset by
  the feature-engineering step.

Units, ranges, and sources below are read directly from the current files.

---

## 1. Keys and identifiers

| Column | Type | Description | Example |
|---|---|---|---|
| `Fecha` | string | Month, `YYYY-MM` format. | `2023-01` |
| `CCAA` | string | Autonomous community, standardized name (`ESPAÑA` = national total). | `Andalucía` |

---

## 2. Target / demand

| Column | Type | Units | Description | Source |
|---|---|---|---|---|
| `Consumo_Tm` | integer | metric tons | Monthly biodiesel consumption. Represents biodiesel reported as its own product line, **not** the biodiesel fraction blended into conventional diesel. Range 0 – 27,001. | CNMC petroleum consumption |
| `Target` *(master)* | integer | flag | 1 if the row is one of the five modeled series, else 0. | derived |
| `Target` *(features)* | string | — | **Different meaning in the feature table:** holds the series name (`Nacional`, `Madrid`, `Cataluña`, `Andalucía`, `Valencia`) rather than a 0/1 flag. | derived |

> Note the `Target` column name is reused with different content in the two
> files. In `master_dataset.csv` it is a 0/1 membership flag; in
> `features_modelo_completo.csv` it labels which of the five series the row
> belongs to.

---

## 3. Macroeconomic context

Source: **INE** (Instituto Nacional de Estadística), Tempus3 API. Same value
applied across all CCAA for a given month (national indicators).

| Column | Type | Units | Description | Range |
|---|---|---|---|---|
| `IPI_original` | float | index | Industrial Production Index, original (non-adjusted). | 78.4 – 113.7 |
| `IPI_ajustado` | float | index | Industrial Production Index, seasonally/calendar adjusted. | 99.2 – 104.4 |
| `IPC_var_anual` | float | % | Consumer Price Index, year-on-year variation (inflation). | 1.5 – 6.0 |
| `Tasa_paro` | float | % | Unemployment rate (EPA survey, quarterly value expanded to monthly). | 9.93 – 13.38 |

---

## 4. Energy and fuel prices

Brent: monthly crude price. Fuel prices: aggregated from daily province-level
retail data to monthly regional means. `PVP` = retail price (price to public);
`PAI` = pre-tax price. All fuel prices in €/litre.

| Column | Type | Units | Description | Source |
|---|---|---|---|---|
| `Precio_Brent_USD` | float | USD/barrel | Monthly Brent crude oil price. Range 62.5 – 93.7. | Brent series |
| `PVP_Gasoleo_A` | float | €/litre | Retail price, Diesel A (standard). | Daily fuel prices (CORES-sourced) |
| `PVP_Gasoleo_Premium` | float | €/litre | Retail price, Diesel Premium. | " |
| `PVP_Gasolina95` | float | €/litre | Retail price, Gasoline 95 E5. | " |
| `PVP_Gasolina98` | float | €/litre | Retail price, Gasoline 98 E5. **Null for Melilla** (not sold there) — 36 null rows. | " |
| `PAI_Gasoleo_A` | float | €/litre | Pre-tax price, Diesel A. | " |
| `PAI_Gasoleo_Premium` | float | €/litre | Pre-tax price, Diesel Premium. | " |
| `PAI_Gasolina95` | float | €/litre | Pre-tax price, Gasoline 95 E5. | " |
| `PAI_Gasolina98` | float | €/litre | Pre-tax price, Gasoline 98 E5. **Null for Melilla** — 36 null rows. | " |

> National fuel-price rows are simple monthly means across CCAA, not
> demand-weighted.

---

## 5. Diesel-market context (CNMC)

Source: **CNMC** petroleum consumption. Provides the broader diesel-pool context
the biodiesel series sits within.

| Column | Type | Units | Description |
|---|---|---|---|
| `CNMC_Biodiesel_Tm` | float | metric tons | Biodiesel consumption from CNMC; reconciles exactly to `Consumo_Tm` for the target series. |
| `GasoleoA_Tm` | float | metric tons | Diesel A consumption (broader diesel market volume). |
| `DieselPool_Tm` | float | metric tons | Total diesel-pool consumption. |
| `Biodiesel_GasoleoA_Ratio` | float | ratio | `CNMC_Biodiesel_Tm` ÷ `GasoleoA_Tm`. Biodiesel relative to Diesel A. |
| `Biodiesel_DieselPool_Share` | float | ratio | `CNMC_Biodiesel_Tm` ÷ `DieselPool_Tm`. Biodiesel share of the total diesel pool. |

---

## 6. Calendar features *(feature table only)*

Derived deterministically from `Fecha`.

| Column | Type | Description | Range |
|---|---|---|---|
| `Mes` | integer | Month number. | 1 – 12 |
| `Trimestre` | integer | Quarter. | 1 – 4 |
| `Año` | integer | Year. | 2023 – 2025 |
| `Tendencia` | integer | Linear time index (month counter from start). | 1 – 36 |
| `sin_mes` | float | Sine seasonal encoding of month. | −1 – 1 |
| `cos_mes` | float | Cosine seasonal encoding of month. | −1 – 1 |

---

## 7. Policy feature *(feature table only)*

| Column | Type | Units | Description | Source |
|---|---|---|---|---|
| `Mandato_Energia_Pct` | float | % | Legislated renewable-energy mandate for transport fuels, by year. Range 10.5 – 11.5 in the modeled window. | `mandato_biocarburantes.csv` (BOE-verified through 2026; 2027–2030 are a team projection — see that file's `Status`/`Fuente` columns) |

---

## 8. Lag and rolling features *(feature table only)*

Built **per series** (grouped by target) on `Consumo_Tm`, shifted so each row only
uses information available **before** its own month (no look-ahead). Early months
are null by construction — counts shown.

| Column | Type | Description | Nulls |
|---|---|---|---|
| `Lag_1` | float | Demand 1 month prior. | 5 |
| `Lag_2` | float | Demand 2 months prior. | 10 |
| `Lag_3` | float | Demand 3 months prior. | 15 |
| `Lag_12` | float | Demand 12 months prior (year-ago). | 60 |
| `Roll_mean_3` | float | Trailing 3-month mean of demand (shifted). | 10 |
| `Roll_mean_6` | float | Trailing 6-month mean of demand (shifted). | 15 |
| `Roll_std_3` | float | Trailing 3-month standard deviation of demand. | 10 |

---

## 9. Lagged exogenous features *(feature table only)*

External drivers entered at **lag-1** so the model only sees values that would
have been published before the forecasted month (publication-delay-correct).

| Column | Type | Description |
|---|---|---|
| `IPI_original_lag1` | float | `IPI_original`, 1 month prior. |
| `IPI_ajustado_lag1` | float | `IPI_ajustado`, 1 month prior. |
| `IPC_var_anual_lag1` | float | `IPC_var_anual`, 1 month prior. |
| `Tasa_paro_lag1` | float | `Tasa_paro`, 1 month prior. |
| `GasoleoA_Tm_lag1` | float | `GasoleoA_Tm`, 1 month prior. |
| `GasoleoA_Tm_roll3_lag1` | float | Trailing 3-month mean of `GasoleoA_Tm`, lagged. |
| `Biodiesel_GasoleoA_Ratio_lag1` | float | `Biodiesel_GasoleoA_Ratio`, 1 month prior. |
| `Biodiesel_GasoleoA_Ratio_roll3_lag1` | float | Trailing 3-month mean of the ratio, lagged. |

---

## Related files

- `data/features/features_train.csv` (120×35) — 2023-01 → 2024-12 training split.
- `data/features/features_test.csv` (60×35) — 2025-01 → 2025-12 holdout split.
- `data/features/features_precios_combustibles.csv` (36×81) — optional
  price-ablation features (per-region PVP/PAI plus lag-1 versions).

*Source attribution per `README.md`, `DATA_AUDIT_REPORT.md`, and the report's
Data Sources section. Types and ranges read from the current CSV files.*
