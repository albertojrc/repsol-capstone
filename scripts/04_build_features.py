"""
Build model-ready features from master_dataset.csv.

This script mirrors the notebook feature-engineering flow, with the CNMC
diesel-market features added as lagged variables only.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_INPUTS = REPO_ROOT / "data" / "inputs"
DATA_FEATURES = REPO_ROOT / "data" / "features"

TRAIN_END = "2024-12"
TEST_START = "2025-01"

TARGET_LABEL = {
    "ESPAÑA": "Nacional",
    "Andalucía": "Andalucía",
    "Cataluña": "Cataluña",
    "Madrid, Comunidad de": "Madrid",
    "Comunitat Valenciana": "Valencia",
}

BASE_LAGS = [1, 2, 3, 12]
MACRO_COLS = ["IPI_original", "IPI_ajustado", "IPC_var_anual", "Tasa_paro"]
DIESEL_MARKET_COLS = ["GasoleoA_Tm", "Biodiesel_GasoleoA_Ratio"]


def load_targets(master: pd.DataFrame) -> pd.DataFrame:
    df = (
        master[master["Target"] == 1]
        .copy()
        .assign(Target=lambda d: d["CCAA"].map(TARGET_LABEL))
    )
    if df["Target"].isna().any():
        missing = sorted(df.loc[df["Target"].isna(), "CCAA"].unique())
        raise ValueError(f"Missing target label mapping for: {missing}")
    return df.sort_values(["Target", "Fecha"]).reset_index(drop=True)


def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    fecha_dt = pd.to_datetime(out["Fecha"])
    out["Mes"] = fecha_dt.dt.month
    out["Trimestre"] = fecha_dt.dt.quarter
    out["Año"] = fecha_dt.dt.year
    out["Tendencia"] = out.groupby("Target").cumcount() + 1
    out["sin_mes"] = np.sin(2 * np.pi * out["Mes"] / 12)
    out["cos_mes"] = np.cos(2 * np.pi * out["Mes"] / 12)
    return out


def add_target_lags(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values(["Target", "Fecha"]).reset_index(drop=True).copy()
    for lag in BASE_LAGS:
        out[f"Lag_{lag}"] = out.groupby("Target")["Consumo_Tm"].shift(lag)
    return out


def add_rolling_target_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values(["Target", "Fecha"]).reset_index(drop=True).copy()
    for _, grp in out.groupby("Target"):
        idx = grp.index
        shifted = grp["Consumo_Tm"].shift(1)
        out.loc[idx, "Roll_mean_3"] = shifted.rolling(window=3, min_periods=2).mean()
        out.loc[idx, "Roll_mean_6"] = shifted.rolling(window=6, min_periods=3).mean()
        out.loc[idx, "Roll_std_3"] = shifted.rolling(window=3, min_periods=2).std()
    return out


def add_lagged_exogenous_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values(["Target", "Fecha"]).reset_index(drop=True).copy()
    for col in MACRO_COLS:
        out[f"{col}_lag1"] = out.groupby("Target")[col].shift(1)

    for col in DIESEL_MARKET_COLS:
        shifted = out.groupby("Target")[col].shift(1)
        out[f"{col}_lag1"] = shifted
        out[f"{col}_roll3_lag1"] = (
            shifted.groupby(out["Target"]).rolling(window=3, min_periods=2).mean()
            .reset_index(level=0, drop=True)
        )
    return out


def build_features() -> pd.DataFrame:
    master = pd.read_csv(DATA_INPUTS / "master_dataset.csv")
    master["Fecha"] = master["Fecha"].astype(str).str[:7]

    required = [
        "Fecha",
        "CCAA",
        "Consumo_Tm",
        "Target",
        *MACRO_COLS,
        "CNMC_Biodiesel_Tm",
        "GasoleoA_Tm",
        "DieselPool_Tm",
        "Biodiesel_GasoleoA_Ratio",
        "Biodiesel_DieselPool_Share",
    ]
    missing = [col for col in required if col not in master.columns]
    if missing:
        raise ValueError(f"master_dataset.csv is missing required columns: {missing}")

    df = load_targets(master[required].copy())
    df = add_calendar_features(df)
    df = add_target_lags(df)
    df = add_rolling_target_features(df)
    df = add_lagged_exogenous_features(df)
    return df.sort_values(["Target", "Fecha"]).reset_index(drop=True)


def validate_features(df: pd.DataFrame) -> None:
    if df.duplicated(["Fecha", "Target"]).any():
        raise ValueError("features_modelo_completo has duplicate Fecha + Target rows")

    # Verify lag features are causal within each target.
    for target, grp in df.groupby("Target"):
        grp = grp.sort_values("Fecha")
        for lag in [1, 2, 3, 12]:
            expected = grp["Consumo_Tm"].shift(lag)
            actual = grp[f"Lag_{lag}"]
            if not actual.fillna(-999999).round(10).equals(expected.fillna(-999999).round(10)):
                raise ValueError(f"Lag_{lag} mismatch for {target}")
        for col in DIESEL_MARKET_COLS:
            expected = grp[col].shift(1)
            actual = grp[f"{col}_lag1"]
            if not actual.fillna(-999999).round(10).equals(expected.fillna(-999999).round(10)):
                raise ValueError(f"{col}_lag1 mismatch for {target}")


def main() -> None:
    DATA_FEATURES.mkdir(parents=True, exist_ok=True)
    df_feat = build_features()
    validate_features(df_feat)

    df_train = df_feat[df_feat["Fecha"] <= TRAIN_END].copy()
    df_test = df_feat[df_feat["Fecha"] >= TEST_START].copy()

    df_feat.to_csv(DATA_FEATURES / "features_modelo_completo.csv", index=False, encoding="utf-8")
    df_train.to_csv(DATA_FEATURES / "features_train.csv", index=False, encoding="utf-8")
    df_test.to_csv(DATA_FEATURES / "features_test.csv", index=False, encoding="utf-8")

    print(f"Saved features_modelo_completo.csv {df_feat.shape}")
    print(f"Saved features_train.csv {df_train.shape}")
    print(f"Saved features_test.csv {df_test.shape}")
    print("Feature date range:", df_feat["Fecha"].min(), "to", df_feat["Fecha"].max())
    print("Diesel lag feature null counts:")
    diesel_cols = [
        "GasoleoA_Tm_lag1",
        "GasoleoA_Tm_roll3_lag1",
        "Biodiesel_GasoleoA_Ratio_lag1",
        "Biodiesel_GasoleoA_Ratio_roll3_lag1",
    ]
    print(df_feat[diesel_cols].isna().sum().to_string())


if __name__ == "__main__":
    main()
