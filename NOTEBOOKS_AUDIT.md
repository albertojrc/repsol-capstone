# Notebooks Audit

Refreshed: 2026-06-23

## Current Policy

The production source of truth is the script pipeline documented in `README.md`.
The notebooks are retained for exploration, explanation, and optional ablation
work. Notebook outputs and execution counts are cleared to avoid preserving
stale local paths, warnings, or old results.

Each notebook starts with a production note directing users to the script
pipeline for reproducible final artifacts. The current final selected model set
is non-pooled; pooled regional ML appears only as a sensitivity experiment in the
script outputs.

## Inventory

| Notebook | Current Status | Notes |
|---|---|---|
| `01_eda.ipynb` | Exploratory | EDA figures only. Not part of the production rebuild. |
| `02_data_cleaning.ipynb` | Historical / exploratory | Original target-cleaning workflow. Production inputs are already committed. |
| `03_external_data.ipynb` | Historical / exploratory | INE / external-data notes. DGT remains planned, not implemented. |
| `04_master_dataset.ipynb` | Superseded by script | Use `scripts/02_master_dataset_builder.py` for the CNMC-aware 22-column master dataset. |
| `05_feature_engineering.ipynb` | Superseded by script | Use `scripts/04_build_features.py` for the CNMC-aware 36-column feature table. |
| `06_price_features.ipynb` | Optional ablation support | Builds optional price features for notebook 08. |
| `07_modeling.ipynb` | Superseded by script | Use `scripts/05_modeling_with_cnmc.py` for current modeling outputs. |
| `08_modeling_with_prices.ipynb` | Optional ablation support | Price-region mapping bug fixed. It is not the production modeling path. |
| `09_evaluation.ipynb` | Superseded by script | Script now writes the final figures and dashboard outputs. It can rebuild CNMC-aware master/features if older exploratory notebooks leave stale feature tables behind. |
| `10_final_models.ipynb` | Narrative summary | Documents the final non-pooled selected model set, SARIMA grid-search acceptance, and 2025 validation metrics. |
| `10_1_final_models.ipynb` | Catalonia no-pooling detail | Explains why Catalonia uses SARIMA in the final selected set, including the SARIMA grid-search no-regression check, while pooled Random Forest remains a sensitivity result. |
| `11_mini_demand_model.ipynb` | Removed upstream | Superseded by notebook 12 in the latest `main`; not part of the current notebook set. |
| `12_mini_trend_regulation_model.ipynb` | Mini regulation model | Narrative regulation/trend scenario model. Not part of the production forecast selection. |
| `13_business_interpretation_and_recommendations.ipynb` | Business interpretation | Reads production outputs, restates selected results by target, shows SARIMA grid-search acceptance, generates regional train/validation/forecast plots, and documents model limitations, feature interpretation, internal Repsol data needs, and recommendations. |

## Fixes Applied

- Cleared all notebook cell outputs and execution counts.
- Added or retained production notes in notebooks.
- Fixed `08_modeling_with_prices.ipynb` so `TARGET_PRICE_SUFFIX` uses the same
  accented target labels as `features_modelo_completo.csv`: `Cataluña` and
  `Andalucía`.
- Fixed `09_evaluation.ipynb` for current pandas frequency aliases.
- Updated `09_evaluation.ipynb` to use the same CNMC-aware feature list as the
  production modeling script.
- Added a `09_evaluation.ipynb` compatibility guard that rebuilds the
  CNMC-aware master and feature tables when required feature columns are missing.
- Updated `10_final_models.ipynb` and `10_1_final_models.ipynb` to document the
  final non-pooled policy and Catalonia SARIMA selection.
- Preserved the upstream removal of `11_mini_demand_model.ipynb`, which is
  superseded by notebook 12 in the current `main` branch.
- Added `13_business_interpretation_and_recommendations.ipynb` as the
  business-facing interpretation layer.
- Added SARIMA grid-search and SARIMA order-acceptance tables to notebooks 10,
  10.1, and 13.

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
