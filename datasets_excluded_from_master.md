# Datasets Excluded From The Master Dataset

Refreshed: 2026-06-21

The production master dataset uses `Fecha` x `CCAA` as its primary key. Two tracked
input datasets are intentionally excluded from `master_dataset.csv`.

## `consumo_biodiesel_provincial.csv`

Reason: granularity mismatch.

This file is province-level (`Fecha` x `Provincia`) and contains 1872 rows. Aggregating
it to CCAA level reproduces the CCAA totals already present in
`consumo_biodiesel_ccaa.csv`, so merging it into the master table would duplicate the
target rather than add independent signal.

Potential future use:

- Province-level demand analysis.
- Spatial/logistics analysis.
- Province-to-CCAA share diagnostics.

## `turismo_visitantes_ccaa.csv`

Reason: insufficient time coverage.

This file contains a single month only, October 2025, for 15 CCAA rows. A monthly
forecasting model needs a time series, so this cannot be used as a model feature
without creating a one-month-only artifact.

Potential future use:

- Add monthly tourism data covering the full modeling window, at least 2023-2025.
- Merge by `Fecha` x `CCAA` only after the tourism source has full regional and
  temporal coverage.

## Summary

| Dataset | Rows | Excluded Reason | Future Use |
|---|---:|---|---|
| `consumo_biodiesel_provincial.csv` | 1872 | Province granularity does not match CCAA master key | Provincial or spatial analysis |
| `turismo_visitantes_ccaa.csv` | 15 | Single month only | Add if full monthly regional series is sourced |
