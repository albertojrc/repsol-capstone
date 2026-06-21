# Phase 2 Non-Pooling Modeling Report

Generated: 2026-06-21

Branch: `main`

## Purpose

This report documents the Phase 2 modeling upgrade applied to `main` without
regional pooling. Pooling remains isolated on the `enrico` branch.

The target remains monthly biodiesel demand in tonnes for national Spain plus
Madrid, Catalonia, Andalusia, and Valencia.

## What Changed

The production modeling script now uses a recursive multi-step walk-forward gate
for the existing non-pooled candidate models.

The new gate:

- uses only the 2023-2024 training period for model-selection proposals;
- evaluates each fold up to 6 months ahead;
- evaluates ML models recursively, so each predicted month feeds future lag
  features;
- holds macro lag inputs constant at the last known value during recursive paths;
- does not add pooled regional models or pooled regional features.

A no-regression acceptance rule then compares the Phase 2 proposed model with the
Phase 1 selected model on the 2025 holdout. The proposal is accepted only when it
does not worsen Phase 1 MAPE.

## Final Decisions

| Target | Phase 1 Model | Phase 1 MAPE | Phase 2 Proposal | Proposal MAPE | Final Model | Decision |
|---|---|---:|---|---:|---|---|
| Nacional | SARIMA | 29.0% | Logistic | 36.7% | SARIMA | Kept Phase 1 |
| Madrid | Gompertz | 197.1% | Logistic | 73.6% | Logistic | Accepted |
| Catalonia | Gompertz | 164.2% | XGBoost | 61.6% | XGBoost | Accepted |
| Andalusia | Logistic | 48.4% | SARIMA | 52.5% | Logistic | Kept Phase 1 |
| Valencia | Gompertz | 34.2% | SARIMA | 57.4% | Gompertz | Kept Phase 1 |

Average selected 2025 MAPE improves from 94.6% to 49.4%.

## Current Selected Models

| Target | Final Model | 2025 MAPE | 2025 R2 |
|---|---|---:|---:|
| Nacional | SARIMA | 29.0% | -0.009 |
| Madrid | Logistic | 73.6% | -8.273 |
| Catalonia | XGBoost | 61.6% | -8.432 |
| Andalusia | Logistic | 48.4% | -1.555 |
| Valencia | Gompertz | 34.2% | -1.246 |

## Output Lineage

New non-pooling Phase 2 lineage file:

- `data/outputs/phase2_non_pooling_model_acceptance.csv`

Regenerated standard outputs:

- `metricas_modelos.csv`
- `model_selection_walkforward.csv`
- `metricas_final_seleccionado.csv`
- `predicciones_test_2025.csv`
- `forecast_24m_sarima_rf_xgb.csv`
- `tableau_dashboard.csv`
- `tableau_metricas.csv`
- `tableau_forecast_pivot.csv`
- `tableau_export_legacy.csv`
- `reports/figures/07_model_comparison.png`
- `reports/figures/11_forecast_24m.png`

## What Remains Only On `enrico`

The `enrico` branch contains the pooling experiment and pooled regional production
path. That branch accepts a pooled Random Forest for Catalonia. None of that
pooled-model code or pooled output lineage is included on `main`.

## Remaining Limitations

The selected models are more defensible after Phase 2, but the dataset remains
small: only 24 training months per target, with fewer usable rows for ML after
lag features. R2 remains negative for all selected targets except near-zero
national SARIMA, so the forecasts should be presented as planning scenarios
rather than high-precision operational commitments.
