"""
Validate the rebuilt production artifacts.

This is a lightweight regression gate for the capstone deliverables. It checks
dataset lineage, temporal split integrity, causal lag features, final model
selection policy, and dashboard export consistency after the scripts pipeline
has been rerun.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_INPUTS = REPO_ROOT / "data" / "inputs"
DATA_FEATURES = REPO_ROOT / "data" / "features"
DATA_OUTPUTS = REPO_ROOT / "data" / "outputs"

TARGETS = ["Nacional", "Madrid", "Cataluña", "Andalucía", "Valencia"]
HEADLINE_FINAL_MODELS = {
    "SARIMA",
    "SARIMAX",
    "Logistic",
    "Gompertz",
    "Ridge",
    "Random Forest",
    "XGBoost",
}
TARGET_LABEL = {
    "ESPAÑA": "Nacional",
    "Madrid, Comunidad de": "Madrid",
    "Cataluña": "Cataluña",
    "Andalucía": "Andalucía",
    "Comunitat Valenciana": "Valencia",
}
MODEL_FEATURES = [
    "Tendencia",
    "Mes",
    "sin_mes",
    "cos_mes",
    "Lag_1",
    "Lag_2",
    "Lag_3",
    "Roll_mean_3",
    "Roll_mean_6",
    "IPI_original_lag1",
    "IPC_var_anual_lag1",
    "Tasa_paro_lag1",
    "GasoleoA_Tm_lag1",
    "GasoleoA_Tm_roll3_lag1",
    "Biodiesel_GasoleoA_Ratio_lag1",
    "Biodiesel_GasoleoA_Ratio_roll3_lag1",
    "Mandato_Energia_Pct",
    "Mandato_Biodiesel_Blend_Pct",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read_csv(path: Path) -> pd.DataFrame:
    require(path.exists(), f"Missing expected file: {path.relative_to(REPO_ROOT)}")
    return pd.read_csv(path)


def assert_close(actual: pd.Series, expected: pd.Series, label: str, tolerance: float = 0.05) -> None:
    diff = (actual.sort_index() - expected.sort_index()).abs().max()
    require(float(diff) <= tolerance, f"{label} reconciliation mismatch. Max diff: {diff}")


def is_repeating_cycle(values: np.ndarray, max_period: int = 12, tolerance: float = 0.05) -> tuple[bool, int | None]:
    for period in range(1, min(max_period, len(values) - 1) + 1):
        if np.allclose(values[period:], values[:-period], rtol=1e-6, atol=tolerance):
            return True, period
    return False, None


def validate_selected_forecast_shape(selected_forecasts: pd.DataFrame) -> None:
    for target in TARGETS:
        path = selected_forecasts[selected_forecasts["Target"].eq(target)].sort_values("Fecha")
        require(len(path) == 24, f"Selected forecast for {target} should contain 24 months")
        values = path["Forecast"].astype(float).values
        mean_level = max(float(np.mean(np.abs(values))), 1.0)
        path_range = float(np.max(values) - np.min(values))
        require(
            path_range > max(1.0, 0.005 * mean_level),
            f"Selected forecast for {target} is near-flat; range={path_range:.4f}",
        )
        repeats, period = is_repeating_cycle(values)
        require(
            not repeats,
            f"Selected forecast for {target} repeats with period {period}; recursive forecast may be degenerate",
        )

    paths = {
        target: selected_forecasts[selected_forecasts["Target"].eq(target)]
        .sort_values("Fecha")["Forecast"]
        .astype(float)
        .values
        for target in TARGETS
    }
    for i, target_a in enumerate(TARGETS):
        for target_b in TARGETS[i + 1 :]:
            require(
                not np.allclose(paths[target_a], paths[target_b], rtol=1e-6, atol=0.05),
                f"Selected forecasts for {target_a} and {target_b} are identical/near-identical",
            )


def validate_master_dataset() -> None:
    master = read_csv(DATA_INPUTS / "master_dataset.csv")
    require(master.shape == (720, 22), f"Unexpected master_dataset shape: {master.shape}")

    master["Fecha"] = master["Fecha"].astype(str).str[:7]
    require(master["Fecha"].min() == "2023-01", "master_dataset starts before/after 2023-01")
    require(master["Fecha"].max() == "2025-12", "master_dataset does not end at 2025-12")
    require(master["Fecha"].nunique() == 36, "master_dataset should contain 36 monthly periods")
    require(master["CCAA"].nunique() == 20, "master_dataset should contain 19 CCAA rows plus ESPAÑA")
    require(not master.duplicated(["Fecha", "CCAA"]).any(), "Duplicate Fecha + CCAA rows in master_dataset")
    require(not (master["Fecha"] >= "2026-01").any(), "master_dataset contains 2026 rows")

    expected_targets = set(TARGET_LABEL)
    actual_targets = set(master.loc[master["Target"] == 1, "CCAA"].unique())
    require(actual_targets == expected_targets, f"Unexpected target CCAA set: {sorted(actual_targets)}")

    non_null_exceptions = {"PVP_Gasolina98": 36, "PAI_Gasolina98": 36}
    null_counts = master.isna().sum()
    unexpected_nulls = {
        col: int(count)
        for col, count in null_counts.items()
        if count and non_null_exceptions.get(col) != int(count)
    }
    require(not unexpected_nulls, f"Unexpected master_dataset nulls: {unexpected_nulls}")

    for col in non_null_exceptions:
        rows = master[master[col].isna()]
        require(
            rows["CCAA"].nunique() == 1 and rows["CCAA"].iloc[0] == "Melilla",
            f"{col} nulls should only belong to Melilla",
        )

    national = master[master["CCAA"] == "ESPAÑA"].set_index("Fecha")
    regional = master[master["CCAA"] != "ESPAÑA"].groupby("Fecha")
    for col in ["Consumo_Tm", "CNMC_Biodiesel_Tm", "GasoleoA_Tm", "DieselPool_Tm"]:
        assert_close(national[col], regional[col].sum(), f"National {col}")


def validate_feature_tables() -> None:
    full = read_csv(DATA_FEATURES / "features_modelo_completo.csv")
    train = read_csv(DATA_FEATURES / "features_train.csv")
    test = read_csv(DATA_FEATURES / "features_test.csv")

    require(full.shape == (180, 36), f"Unexpected full feature shape: {full.shape}")
    require(train.shape == (120, 36), f"Unexpected train feature shape: {train.shape}")
    require(test.shape == (60, 36), f"Unexpected test feature shape: {test.shape}")
    require(set(full["Target"].unique()) == set(TARGETS), "features_modelo_completo target set mismatch")
    require(not full.duplicated(["Fecha", "Target"]).any(), "Duplicate Fecha + Target rows in full features")
    require(train["Fecha"].max() == "2024-12", "features_train must end at 2024-12")
    require(test["Fecha"].min() == "2025-01", "features_test must start at 2025-01")
    require(train["Fecha"].max() < test["Fecha"].min(), "Train/test temporal split overlaps")
    require(not (full["Fecha"] >= "2026-01").any(), "features_modelo_completo contains 2026 rows")

    missing_model_features = [col for col in MODEL_FEATURES if col not in full.columns]
    require(not missing_model_features, f"Missing model feature columns: {missing_model_features}")
    require(not test[MODEL_FEATURES].isna().any().any(), "features_test has nulls in model-used features")

    for target, grp in full.groupby("Target"):
        grp = grp.sort_values("Fecha").reset_index(drop=True)
        for lag in [1, 2, 3, 12]:
            expected = grp["Consumo_Tm"].shift(lag)
            actual = grp[f"Lag_{lag}"]
            ok = np.allclose(actual.fillna(-1), expected.fillna(-1), atol=1e-8)
            require(ok, f"Lag_{lag} is not causal for {target}")
        for col in ["GasoleoA_Tm", "Biodiesel_GasoleoA_Ratio"]:
            expected = grp[col].shift(1)
            actual = grp[f"{col}_lag1"]
            ok = np.allclose(actual.fillna(-1), expected.fillna(-1), atol=1e-8)
            require(ok, f"{col}_lag1 is not causal for {target}")


def validate_model_outputs() -> None:
    final = read_csv(DATA_OUTPUTS / "metricas_final_seleccionado.csv")
    metrics = read_csv(DATA_OUTPUTS / "metricas_modelos.csv")
    acceptance = read_csv(DATA_OUTPUTS / "phase2_model_acceptance.csv")
    pooling = read_csv(DATA_OUTPUTS / "phase2_pooling_decision.csv")
    sarima_grid = read_csv(DATA_OUTPUTS / "sarima_grid_search_results.csv")
    sarima_acceptance = read_csv(DATA_OUTPUTS / "sarima_order_acceptance.csv")
    forecasts = read_csv(DATA_OUTPUTS / "forecast_24m_sarima_rf_xgb.csv")
    selected_forecasts = read_csv(DATA_OUTPUTS / "forecast_24m_selected.csv")
    pivot = read_csv(DATA_OUTPUTS / "tableau_forecast_pivot.csv")
    degenerate = read_csv(DATA_OUTPUTS / "degenerate_fits.csv")

    selected = dict(zip(final["Target"], final["Model"]))
    require(set(selected) == set(TARGETS), f"Final selected target set mismatch: {selected}")
    invalid_models = sorted(set(final["Model"]) - HEADLINE_FINAL_MODELS)
    require(not invalid_models, f"Final selected models must be one of the 7 headline candidates, found: {invalid_models}")

    # A candidate may legitimately be missing from metricas_modelos.csv for a
    # given target if its fit was degenerate (sigma2 collapsed to near zero,
    # or the optimizer never converged -- the signature of too many
    # parameters for too few rows, observed for SARIMAX on 4 of 5 targets).
    # Any OTHER missing candidate is a real bug, not an intentional exclusion.
    for target in TARGETS:
        target_models = set(metrics.loc[metrics["Target"].eq(target), "Model"])
        missing_headline = sorted(HEADLINE_FINAL_MODELS - target_models)
        documented_degenerate = set(
            degenerate.loc[
                degenerate["Target"].eq(target) & degenerate["Stage"].eq("2025_holdout_evaluation"),
                "Model",
            ]
        )
        undocumented_missing = sorted(set(missing_headline) - documented_degenerate)
        require(
            not undocumented_missing,
            f"{target} missing headline candidate metrics with no degeneracy record: {undocumented_missing}",
        )

    # The model actually selected for production must never be one we
    # ourselves flagged as a degenerate fit -- selection happens upstream of
    # evaluate_models in scripts/05, so this also catches any future
    # regression where that ordering is broken.
    selected_degenerate = degenerate[degenerate["Stage"].eq("2025_holdout_evaluation")].merge(
        final[["Target", "Model"]], on=["Target", "Model"], how="inner"
    )
    require(
        selected_degenerate.empty,
        f"Selected model is flagged as a degenerate fit: {selected_degenerate.to_dict('records')}",
    )

    required_sarima_cols = {"Target", "p", "d", "q", "P", "D", "Q", "m", "WalkForward_MAPE", "Selected"}
    missing_sarima_cols = required_sarima_cols.difference(sarima_grid.columns)
    require(not missing_sarima_cols, f"sarima_grid_search_results missing columns: {sorted(missing_sarima_cols)}")
    require(set(sarima_grid["Target"].unique()) == set(TARGETS), "SARIMA grid target set mismatch")
    selected_sarima_counts = sarima_grid.groupby("Target")["Selected"].sum().to_dict()
    require(
        selected_sarima_counts == {target: 1 for target in TARGETS},
        f"Expected one selected SARIMA order per target, got {selected_sarima_counts}",
    )
    required_sarima_acceptance_cols = {
        "Target",
        "Grid_Selected_Order",
        "Grid_Selected_Seasonal_Order",
        "Grid_WalkForward_MAPE",
        "Production_Order",
        "Production_Seasonal_Order",
        "Selected_By_Training_WalkForward",
        "Decision",
    }
    missing_sarima_acceptance_cols = required_sarima_acceptance_cols.difference(sarima_acceptance.columns)
    require(
        not missing_sarima_acceptance_cols,
        f"sarima_order_acceptance missing columns: {sorted(missing_sarima_acceptance_cols)}",
    )
    require(set(sarima_acceptance["Target"].unique()) == set(TARGETS), "SARIMA acceptance target set mismatch")
    require(len(sarima_acceptance) == len(TARGETS), "SARIMA acceptance should have one row per target")

    required_acceptance_cols = {
        "Target",
        "Final_Eligibility_Rule",
        "Eligible_Final_Models",
        "Selected_Model",
        "Selected_Model_Training_WalkForward_MAPE",
        "Final_Selection_Source",
        "Decision",
    }
    missing_cols = required_acceptance_cols.difference(acceptance.columns)
    require(not missing_cols, f"phase2_model_acceptance missing columns: {sorted(missing_cols)}")
    require(
        set(acceptance["Selected_Model"]).issubset(HEADLINE_FINAL_MODELS),
        "All final selections must be one of the 7 headline candidates",
    )

    require("Final_Selection_Allows_Pooled_ML" in pooling.columns, "phase2_pooling_decision missing pooled-allowed flag")
    require(not pooling["Final_Selection_Allows_Pooled_ML"].any(), "Pooled ML should remain diagnostic-only")

    require(forecasts["Fecha"].min() == "2026-01", "Forecast output must start at 2026-01")
    require(forecasts["Fecha"].max() == "2027-12", "Forecast output must end at 2027-12")
    require(forecasts["Fecha"].nunique() == 24, "Forecast output should contain 24 months")
    require(not forecasts.duplicated(["Fecha", "Target", "Model"]).any(), "Duplicate forecast rows")
    selected_forecast_rows = sum(
        len(forecasts[(forecasts["Target"] == target) & (forecasts["Model"] == model)])
        for target, model in selected.items()
    )
    require(selected_forecast_rows == 24 * len(TARGETS), "Selected forecast rows should be 120")
    require(selected_forecasts.shape[0] == 24 * len(TARGETS), "Selected-only forecast should have 120 rows")
    selected_only_pairs = selected_forecasts[["Target", "Model"]].drop_duplicates()
    require(len(selected_only_pairs) == len(TARGETS), "Selected-only forecast should have one model per target")
    selected_only = dict(zip(selected_only_pairs["Target"], selected_only_pairs["Model"]))
    require(selected_only == selected, f"Selected-only forecast model set mismatch: {selected_only} vs {selected}")
    validate_selected_forecast_shape(selected_forecasts)

    require(pivot.shape[0] == 24, f"tableau_forecast_pivot should have 24 rows, got {pivot.shape[0]}")
    missing_pivot_targets = [target for target in TARGETS if target not in pivot.columns]
    require(not missing_pivot_targets, f"tableau_forecast_pivot missing targets: {missing_pivot_targets}")


def main() -> None:
    validate_master_dataset()
    validate_feature_tables()
    validate_model_outputs()
    print("All production artifact validation checks passed.")


if __name__ == "__main__":
    main()
