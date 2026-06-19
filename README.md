# Repsol Eco-Fuels Demand Forecasting

## Project Overview
This project forecasts the demand for eco-fuels (renewable diesel) in Spain for the next 24 months using machine learning and statistical models.

## Current Reproducible Pipeline

The current production path includes the CNMC diesel-market feature integration plus deterministic biofuel mandate features, and is script-based:

```powershell
python scripts/03_clean_cnmc_petroleum.py
python scripts/02_master_dataset_builder.py
python scripts/04_build_features.py
python scripts/05_modeling_with_cnmc.py
```

This rebuilds:
- `data/processed/cnmc_*.csv`
- `data/inputs/master_dataset.csv`
- `data/features/features_modelo_completo.csv`
- `data/features/features_train.csv`
- `data/features/features_test.csv`
- model metrics, 2025 predictions, 2026-2027 forecasts, Tableau exports, and final figures in `data/outputs/` and `reports/figures/`.

The target remains total market biodiesel demand (`Consumo_Tm`), not Repsol sales. CNMC `GasoleoA_Tm` and biodiesel/Gasoleo A ratio are used only through lagged, leakage-safe features. `Mandato_Energia_Pct` and `Mandato_Biodiesel_Blend_Pct` are deterministic policy features from the mandate schedule. Jan-Feb 2026 CNMC data is cleaned and retained in processed files, but not used in model training, validation, or the original 2026-2027 forecast origin.

## Objectives
- Forecast demand at national level
- Forecast demand at regional level (Madrid, Andalucía, Cataluña, Valencia)
- Monthly granularity
- Using mathematical, statistical, and ML models

## Data Sources
- CORES: Eco-fuel demand data
- INE: Macroeconomic indicators
- DGT: Vehicle statistics

## Technologies
- Python 3.9+
- Pandas, NumPy
- Scikit-learn, XGBoost, Statsmodels
- Matplotlib, Seaborn
- Jupyter Lab

## Project Structure
repsol-capstone/
├── data/
│   ├── raw/
│   └── processed/
├── notebooks/
├── models/
├── reports/
│   └── figures/
├── src/
├── requirements.txt
└── README.md
