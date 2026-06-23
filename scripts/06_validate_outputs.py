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
FINAL_MODEL_POLICY = {
    "Nacional": "SARIMA",
    "Madrid": "Logistic",
    "Cataluña": "SARIMA",
    "Andalucía": "Logistic",
    "Valencia": "Gompertz",
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
    acceptance = read_csv(DATA_OUTPUTS / "phase2_model_acceptance.csv")
    pooling = read_csv(DATA_OUTPUTS / "phase2_pooling_decision.csv")
    forecasts = read_csv(DATA_OUTPUTS / "forecast_24m_sarima_rf_xgb.csv")
    pivot = read_csv(DATA_OUTPUTS / "tableau_forecast_pivot.csv")

    selected = dict(zip(final["Target"], final["Model"]))
    require(selected == FINAL_MODEL_POLICY, f"Final selected models violate policy: {selected}")
    require(not final["Model"].str.startswith("Pooled").any(), "Final selection contains a pooled model")

    required_acceptance_cols = {
        "Target",
        "Phase1_Model",
        "Phase2_Proposed_Model",
        "Non_Pooled_Final_Model",
        "Selected_Model",
        "Final_Selection_Source",
        "Decision",
    }
    missing_cols = required_acceptance_cols.difference(acceptance.columns)
    require(not missing_cols, f"phase2_model_acceptance missing columns: {sorted(missing_cols)}")
    cat = acceptance[acceptance["Target"] == "Cataluña"].iloc[0]
    require(cat["Selected_Model"] == "SARIMA", "Cataluña final model should be SARIMA")
    require(
        cat["Decision"] == "selected_non_pooled_final_policy",
        "Cataluña acceptance decision should document the no-pooling final policy",
    )

    require("No_Pooling_Final_Policy" in pooling.columns, "phase2_pooling_decision missing no-pooling policy flag")
    cat_pool = pooling[pooling["Target"] == "Cataluña"].iloc[0]
    require(bool(cat_pool["No_Pooling_Final_Policy"]), "Cataluña pooling decision should be policy-flagged")
    require(
        cat_pool["Decision"] == "rejected_by_non_pooled_final_policy",
        "Cataluña pooled model should be rejected by final policy",
    )

    require(forecasts["Fecha"].min() == "2026-01", "Forecast output must start at 2026-01")
    require(forecasts["Fecha"].max() == "2027-12", "Forecast output must end at 2027-12")
    require(forecasts["Fecha"].nunique() == 24, "Forecast output should contain 24 months")
    require(not forecasts.duplicated(["Fecha", "Target", "Model"]).any(), "Duplicate forecast rows")
    selected_forecast_rows = sum(
        len(forecasts[(forecasts["Target"] == target) & (forecasts["Model"] == model)])
        for target, model in FINAL_MODEL_POLICY.items()
    )
    require(selected_forecast_rows == 24 * len(TARGETS), "Selected forecast rows should be 120")

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
