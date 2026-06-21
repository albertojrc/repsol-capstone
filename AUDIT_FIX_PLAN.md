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

## Completed In Phase 2 On `enrico`

- Preserved the Phase 1 cleanup from `main` on the `enrico` branch.
- Replaced the one-step model-selection gate with a recursive multi-step
  walk-forward gate inside the 2023-2024 training period.
- Tested pooled regional ML models in the official script pipeline.
- Kept `Nacional` separate from pooled regional modeling.
- Added a no-regression acceptance gate versus the Phase 1 selected models.
- Accepted Phase 2 changes only for Madrid and Catalonia:
  - Madrid: Gompertz -> Logistic, MAPE 197.1% -> 73.6%.
  - Catalonia: Gompertz -> Pooled Random Forest, MAPE 164.2% -> 46.8%.
- Rejected Phase 2 proposals for Nacional, Andalusia, and Valencia because they
  did not improve the Phase 1 selected holdout result.
- Added `PHASE2_MODELING_REPORT.md` and `data/outputs/phase2_*.csv` lineage
  files documenting the production decision.

## Still Open After Phase 2

- Add automated tests around dataset shapes, target mappings, and output lineage.
- Explain the Catalonia pooled Random Forest as a conservative plateau forecast;
  tree models do not extrapolate structural growth curves.
- Keep HVO / renewable diesel outside the target unless new usable regional data
  becomes available.
