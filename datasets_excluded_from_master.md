# Datasets Excluded from Master Dataset
## Repsol Diesel Nexa — Capstone Project

**Generated:** 2026-06-10

This document explains why two input datasets could **not** be merged into `master_dataset.csv` and how they are currently used.

---

## 1. `consumo_biodiesel_provincial.csv`

### Why it was excluded

**Granularity mismatch:** The master dataset has `Fecha × CCAA` as its primary key (one row per month per autonomous community). Provincial data has `Fecha × Provincia` as its primary key — a finer granularity with 52 provinces × 36 months = 1,872 rows.

Merging province-level consumption into a CCAA-level table would require aggregating to CCAA level first, which produces the same values already present in `consumo_biodiesel_ccaa.csv` (the CCAA totals). Adding it would create exact duplicate columns.

### What the file contains

| Attribute | Value |
|-----------|-------|
| Shape | 1,872 rows × 5 columns |
| Columns | Fecha, Provincia, CCAA, Consumo_Tm, Porcentaje_CCAA |
| Date range | 2023-01 → 2025-12 |
| Granularity | 52 Spanish provinces × 36 months |

`Porcentaje_CCAA` represents each province's share of its CCAA's total consumption — useful for understanding intra-regional distribution.

### How it could be used in future work

1. **Sub-regional modelling:** Train separate models per province for the highest-demand provinces (Madrid, Barcelona, Valencia city).
2. **Spatial analysis:** Map consumption intensity across Spain's 52 provinces.
3. **Logistics planning:** Identify distribution hubs based on province-level demand concentration.

---

## 2. `turismo_visitantes_ccaa.csv`

### Why it was excluded

**Insufficient time coverage:** The file contains tourist visitor data for only **one month** (October 2025). A time series model requires multiple observations to learn temporal patterns. A single row per CCAA cannot contribute meaningful features to a monthly forecasting model.

### What the file contains

| Attribute | Value |
|-----------|-------|
| Shape | 15 rows × 9 columns |
| Columns | CCAA + visitor metrics for October 2025 |
| Date range | 2025M10 only |
| Granularity | 15 CCAAs (a subset) |

### How it could be used in future work

If monthly tourist visitor data were available for 2023–2025 (36 months), it could be merged into the master dataset as additional demand-driving features. Tourism intensity correlates with transportation fuel demand — high-tourism CCAAs (Baleares, Canarias, Cataluña, Andalucía) could show demand peaks aligned with tourism seasons.

**Recommended data source:** Instituto Nacional de Estadística (INE) — Encuesta de Ocupación Hotelera provides monthly data by CCAA going back several years. If this dataset is extended to cover 2023–2025, re-run `notebooks/10_master_dataset.ipynb` to incorporate it.

---

## Summary

| Dataset | Rows | Excluded reason | Future use |
|---------|------|-----------------|------------|
| consumo_biodiesel_provincial.csv | 1,872 | Province granularity ≠ CCAA master PK | Sub-regional / spatial analysis |
| turismo_visitantes_ccaa.csv | 15 | Single month — cannot form time series | Merge when full 2023–2025 series available |
