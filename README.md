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
- model metrics, SARIMA grid-search diagnostics, 2025 predictions, 2026-2027 forecasts, Tableau exports, and final figures

`forecast_24m_sarima_rf_xgb.csv` is a legacy filename. It now contains all current
candidate families used by the CNMC-aware script, including SARIMA, SARIMAX, Ridge,
Random Forest, XGBoost, Logistic, Gompertz, Diesel Share, and pooled regional ML.
The clean headline forecast is exported as `forecast_24m_selected.csv`.

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
- `data/outputs/forecast_24m_sarima_rf_xgb.csv`: 1152 rows x 4 columns (fewer than
  the theoretical maximum because SARIMAX is excluded as a degenerate fit for
  4 of 5 targets; see `data/outputs/degenerate_fits.csv`)
- `data/outputs/forecast_24m_selected.csv`: 120 rows x 4 columns

## Notebooks

The notebooks are retained for exploration and narrative context. The scripts in
`scripts/` are the source of truth for final reproducible outputs. Notebook outputs
are intentionally cleared to avoid stale local paths, warnings, and old results being
mistaken for a fresh run.

`notebooks/13_business_interpretation_and_recommendations.ipynb` adds the
business-facing interpretation layer: selected-model results by region, regional
train/validation/forecast plots, model limitations, feature interpretation, Repsol
internal-data needs, and recommendations.

## Project Memory Maintenance

`memory.md` is the long-term project log. It is not updated automatically, so any
person or assistant making a major project change should update it in the same
work session, pull request, or commit.

Update `memory.md` when a change affects:

- dataset sources, coverage, merge logic, or target definitions
- feature engineering, leakage controls, or validation policy
- model families, model-selection logic, SARIMA orders, or final selected models
- output files, dashboard exports, forecast origin, or headline metrics
- business interpretation, project scope, or important caveats
- git/branch state that future collaborators need to understand

Tiny formatting edits do not need a memory update. If unsure, add a short dated
entry near the top of `memory.md` and state what changed, why it matters, and how
it was verified.

## Model Selection

The `sacha` branch rebuilds the modeling layer as an open seven-family
competition for each target. Every target independently fits and ranks:

- SARIMA
- SARIMAX, using lagged macro, lagged CNMC diesel-market, seasonal, and mandate features
- Logistic growth curve
- Gompertz growth curve
- Ridge regression on the engineered feature set
- Random Forest on the engineered feature set
- XGBoost on the engineered feature set

All seven are eligible to win for every target. Pooled regional Ridge / Random
Forest / XGBoost and Diesel Share remain in `metricas_modelos.csv` as diagnostics
and sensitivity comparisons, but they are not eligible for the headline forecast.

Selection is made only by recursive multi-step walk-forward validation inside
the 2023-2024 training window. The 2025 period is used only after the selected
model is fixed, to report honest holdout MAE/RMSE/MAPE/R2. The code path in
`scripts/05_modeling_with_cnmc.py` finalizes `Selected_Model` before loading
`features_test.csv`.

A SARIMA/SARIMAX fit is also rejected outright (treated the same as any other
training failure, never eligible to be scored or selected) if it is
numerically degenerate: the optimizer did not converge, or the fitted
residual variance has collapsed to near zero. This is the same overfitting
signature as a model having too many parameters for too few rows. SARIMAX's 9
exogenous regressors plus ARMA/seasonal terms (~11 parameters against ~22-34
training rows) hit this for 4 of the 5 targets -- it is excluded everywhere
except where the fit genuinely converges. Every exclusion is written to
`data/outputs/degenerate_fits.csv` with its target, stage, and reason.

| Target | Selected model | Training walk-forward MAPE | 2025 holdout MAPE |
|---|---|---:|---:|
| Nacional | Logistic | 43.1% | 36.7% |
| Madrid | Logistic | 37.2% | 73.6% |
| Cataluña | SARIMA | 66.9% | 50.1% |
| Andalucía | SARIMA | 48.8% | 52.6% |
| Valencia | Gompertz | 57.3% | 34.2% |

Cataluña's SARIMAX result from an earlier version of this pipeline (92.3%
holdout MAPE) is gone: that fit never converged and has been excluded, and
plain SARIMA -- a real, converged fit -- now wins on the same leak-free
training-only evidence. Nacional's selected model also changed from SARIMA to
Logistic, not because of SARIMAX, but because the same degeneracy check was
applied uniformly to plain SARIMA's order grid search too: 3 of Nacional's
11 training-only walk-forward folds for its previously-best order had
themselves been silently non-convergent, flattering its aggregated score
before this fix.

See `PHASE2_MODELING_REPORT.md` for the full seven-candidate table, diagnostic
pooled-model results, forecast-shape validation, and remaining limitations.

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
