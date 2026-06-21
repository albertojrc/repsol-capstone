# Audit Fix Plan

Created: 2026-06-21

## Phase 1 Scope

Requested scope: fix reproducibility, broken/stale docs, notebook/script
inconsistencies, price-feature regional bug, output lineage, and repo cleanup.

Explicitly out of scope for Phase 1: changing the modeling methodology.

## Completed In Phase 1

- Declared Python 3.11 as the supported runtime via `.python-version`.
- Added `pyproject.toml` with the supported Python range so environment tools do
  not inherit an incompatible Python 3.14 project requirement.
- Added `environment.yml` for Conda-compatible environment creation.
- Added missing direct dependency `scipy` to `requirements.txt`.
- Updated `.gitignore` for `.venv/` and AppleDouble metadata files.
- Removed tracked AppleDouble files and duplicate root-level raw downloads.
- Refreshed `README.md`, `DATA_AUDIT_REPORT.md`, `NOTEBOOKS_AUDIT.md`, and
  `datasets_excluded_from_master.md`.
- Cleared stale notebook outputs and execution counts.
- Added a production note to all notebooks.
- Fixed the target-label mismatch in `notebooks/08_modeling_with_prices.ipynb`.
- Made `scripts/02_master_dataset_builder.py` console output Windows-safe and
  corrected its stale header from 17 to 22 columns.
- Fixed `scripts/05_modeling_with_cnmc.py` so `metricas_comparativa.csv` combines
  current metrics with optional price-ablation metrics instead of duplicating
  `metricas_modelos.csv`.
- Added an explicit NumPy seed in the production modeling script.
- Rebuilt the production artifacts from the script path through feature
  generation and modeling outputs.

## Still Open For Phase 2

- Improve weak regional forecasts for Madrid and Catalonia.
- Replace one-step holdout evaluation with fixed-origin multi-step backtesting.
- Decide whether the business target should remain biodiesel only or expand to a
  broader eco-fuels definition that includes HVO / renewable diesel.
- Consider pooled or panel models across the five targets.
- Add automated tests around dataset shapes, target mappings, and output lineage.
