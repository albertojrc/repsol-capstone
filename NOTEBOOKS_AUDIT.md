# Notebooks Audit

Refreshed: 2026-06-21

## Current Policy

The production source of truth is the script pipeline documented in `README.md`.
The notebooks are retained for exploration, explanation, and optional ablation work.
Notebook outputs and execution counts have been cleared to avoid preserving stale
local paths, warnings, or old results.

Each notebook now starts with a production note directing users to the script
pipeline for reproducible final artifacts.

## Inventory

| Notebook | Current Status | Notes |
|---|---|---|
| `01_eda.ipynb` | Exploratory | EDA figures only. Not part of the production rebuild. |
| `02_data_cleaning.ipynb` | Historical / exploratory | Original target-cleaning workflow. Production inputs are already committed. |
| `03_external_data.ipynb` | Historical / exploratory | INE / external-data notes. DGT remains planned, not implemented. |
| `04_master_dataset.ipynb` | Superseded by script | Use `scripts/02_master_dataset_builder.py` for production. |
| `05_feature_engineering.ipynb` | Superseded by script | Use `scripts/04_build_features.py` for the CNMC-aware 36-column feature table. |
| `06_price_features.ipynb` | Optional ablation support | Builds optional price features for notebook 08. |
| `07_modeling.ipynb` | Superseded by script | Use `scripts/05_modeling_with_cnmc.py` for current CNMC-aware modeling outputs. |
| `08_modeling_with_prices.ipynb` | Optional ablation support | Price-region mapping bug fixed. It is not the production modeling path. |
| `09_evaluation.ipynb` | Superseded by script | Script now writes the final production figures and dashboard outputs. |

## Fixes Applied In Phase 1

- Cleared all notebook cell outputs and execution counts.
- Added a production note to all notebooks.
- Fixed `08_modeling_with_prices.ipynb` so `TARGET_PRICE_SUFFIX` uses the same
  accented target labels as `features_modelo_completo.csv`:
  `Cataluña` and `Andalucía`.
- Kept notebook methodology unchanged.

## Main-Branch Phase 2 Note

The non-pooling Phase 2 validation upgrade was implemented in
`scripts/05_modeling_with_cnmc.py`, not in notebook 07. Notebook 07 remains a
historical/exploratory artifact; use `PHASE2_NON_POOLING_REPORT.md` and the
script outputs for current main-branch results.

## Remaining Caveat

The notebooks should not be used as the authoritative final pipeline unless they are
fully refactored to mirror the scripts. For final delivery, use:

```powershell
.\.venv\Scripts\python scripts/03_clean_cnmc_petroleum.py
.\.venv\Scripts\python scripts/02_master_dataset_builder.py
.\.venv\Scripts\python scripts/04_build_features.py
.\.venv\Scripts\python scripts/05_modeling_with_cnmc.py
```
