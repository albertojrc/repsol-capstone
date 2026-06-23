# Repsol Eco-Fuels Demand Forecasting

This repository forecasts monthly biodiesel demand in Spain for a 24-month horizon
from a forecast origin of 2025-12. The modeled target is total market biodiesel
demand (`Consumo_Tm`, metric tonnes), not Repsol sales.

The required delivery scope is:

- National demand (`Nacional`, sourced from `ESPAÑA`)
- Madrid
- Cataluña
- Andalucía
- Valencia
- Monthly forecasts for 2026-01 through 2027-12

## Reproducible Environment

Use Python 3.11. The default Python 3.14 runtime is not supported by the pinned
dependency set.

Recommended setup with `uv`:

```powershell
uv venv --python 3.11 .venv
uv pip install -r requirements.txt --python .\.venv\Scripts\python.exe
```

Conda users can also create the environment from `environment.yml`.

## Production Pipeline

Run these commands from the repository root:

```powershell
.\.venv\Scripts\python scripts/03_clean_cnmc_petroleum.py
.\.venv\Scripts\python scripts/02_master_dataset_builder.py
.\.venv\Scripts\python scripts/04_build_features.py
.\.venv\Scripts\python scripts/05_modeling_with_cnmc.py
.\.venv\Scripts\python scripts/06_validate_outputs.py
```

This rebuilds:

- `data/processed/cnmc_*.csv`
- `data/inputs/master_dataset.csv`, `.xlsx`, and metadata
- `data/features/features_modelo_completo.csv`
- `data/features/features_train.csv`
- `data/features/features_test.csv`
- model metrics, 2025 predictions, 2026-2027 forecasts, Tableau exports, and final figures

`forecast_24m_sarima_rf_xgb.csv` is a legacy filename. It now contains all current
candidate families used by the CNMC-aware script, including SARIMA, Ridge, Random
Forest, XGBoost, Logistic, Gompertz, Diesel Share, and the Phase 2 pooled regional
ML sensitivity candidates. The production selected forecast follows the final
no-pooling policy.

## Data Sources

- CNMC petroleum-consumption data: biodiesel target reconciliation and diesel-market context
- CORES / certified biofuel source files: cleaned biodiesel target inputs
- INE: macroeconomic indicators
- BOE mandate schedule: deterministic biofuel mandate features
- Fuel price files: optional price-ablation notebook outputs

The project does not currently use DGT vehicle data in the production dataset.

## Current Dataset Shapes

- `data/inputs/master_dataset.csv`: 720 rows x 22 columns
- `data/features/features_modelo_completo.csv`: 180 rows x 36 columns
- `data/features/features_train.csv`: 120 rows x 36 columns
- `data/features/features_test.csv`: 60 rows x 36 columns
- `data/outputs/forecast_24m_sarima_rf_xgb.csv`: 1128 rows x 4 columns

## Notebooks

The notebooks are retained for exploration and narrative context. The scripts in
`scripts/` are the source of truth for final reproducible outputs. Notebook outputs
are intentionally cleared to avoid stale local paths, warnings, and old results being
mistaken for a fresh run.

## Phase 2 Modeling

The `enrico` branch productionizes the Phase 2 modeling upgrade. The script now
uses a recursive multi-step walk-forward gate and a no-regression acceptance check
against the Phase 1 selected models. The 2025 period is treated as a validation
and acceptance period, not as a pristine final test. Regional pooling is tested as
a sensitivity experiment, but the final production model set is non-pooled.

| Target | Selected model | 2025 MAPE |
|---|---|---:|
| Nacional | SARIMA | 29.0% |
| Madrid | Logistic | 73.6% |
| Cataluña | SARIMA | 47.2% |
| Andalucía | Logistic | 48.4% |
| Valencia | Gompertz | 34.2% |

The average selected 2025 validation MAPE is 46.5%. See
`PHASE2_MODELING_REPORT.md` for the before/after comparison, pooling decision,
and remaining limitations.

## Repository Layout

```text
repsol-capstone/
├── data/
│   ├── inputs/
│   ├── features/
│   ├── outputs/
│   ├── processed/
│   └── raw/
├── notebooks/
├── reports/
│   └── figures/
├── scripts/
├── requirements.txt
├── environment.yml
└── README.md
```
