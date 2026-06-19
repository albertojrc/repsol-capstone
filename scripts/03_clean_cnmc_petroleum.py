"""
Clean CNMC monthly provincial petroleum-consumption data.

Inputs (data/raw/consumos_mensuales_petroleo/):
    ds_14200_1.csv ... ds_14203_1.csv

Outputs (data/processed/):
    cnmc_consumos_petroleo_provincial.csv
    cnmc_consumos_petroleo_ccaa.csv
    cnmc_diesel_market_features.csv

The cleaned feature file keeps Jan-Feb 2026 CNMC data for auditability, but the
master dataset builder only merges rows through 2025-12 to preserve the original
forecast origin.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw" / "consumos_mensuales_petroleo"
DATA_INPUTS = REPO_ROOT / "data" / "inputs"
DATA_PROCESSED = REPO_ROOT / "data" / "processed"

REQUIRED_COLUMNS = ["Fecha", "CCAA", "Provincia", "Tipo Producto", "Consumo Tm"]

PRODUCT_SLUGS = {
    "BIODIESEL": "Biodiesel",
    "BIOETANOL": "Bioetanol",
    "FUELÓLEO  BIA": "Fueloleo_BIA",
    "GASOLINA  AUTO. S/PB 95 I.O.": "Gasolina95",
    "GASOLINA  AUTO. S/PB 98 I.O.": "Gasolina98",
    "GASÓLEO A": "GasoleoA",
    "GASÓLEO B": "GasoleoB",
    "GASÓLEO C": "GasoleoC",
    "GLP": "GLP",
    "OTRAS GASOLINAS": "OtrasGasolinas",
    "OTROS FUELÓLEOS": "OtrosFueloleos",
    "OTROS GASOLEOS": "OtrosGasoleos",
    "OTROS QUEROSENOS": "OtrosQueroseno",
    "QUEROSENO AVIACIÓN": "QuerosenoAviacion",
}


def strip_accents(text: str) -> str:
    """Return an ASCII-ish version useful for tolerant comparisons only."""
    norm = unicodedata.normalize("NFKD", str(text))
    return "".join(ch for ch in norm if not unicodedata.combining(ch))


def read_raw_files() -> pd.DataFrame:
    paths = sorted(RAW_DIR.glob("ds_*.csv"))
    if not paths:
        raise FileNotFoundError(f"No CNMC source files found in {RAW_DIR}")

    frames = []
    for path in paths:
        df = pd.read_csv(path, sep=";", encoding="utf-8")
        missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            raise ValueError(f"{path.name} is missing required columns: {missing}")
        df = df[REQUIRED_COLUMNS].copy()
        df["source_file"] = path.name
        frames.append(df)

    raw = pd.concat(frames, ignore_index=True)
    raw["Fecha"] = raw["Fecha"].astype(str).str.strip().str[:7]
    raw["CCAA"] = raw["CCAA"].astype(str).str.strip()
    raw["Provincia"] = raw["Provincia"].astype(str).str.strip()
    raw["Tipo_Producto"] = raw["Tipo Producto"].astype(str).str.strip()
    raw["Producto_slug"] = raw["Tipo_Producto"].map(PRODUCT_SLUGS)
    raw["Consumo_Tm"] = pd.to_numeric(raw["Consumo Tm"], errors="raise")
    raw = raw.drop(columns=["Tipo Producto", "Consumo Tm"])

    if raw.isna().sum().sum() > 0:
        nulls = raw.isna().sum()[raw.isna().sum() > 0]
        raise ValueError(f"CNMC raw data has unexpected nulls:\n{nulls}")
    if raw["Producto_slug"].isna().any():
        unknown = sorted(raw.loc[raw["Producto_slug"].isna(), "Tipo_Producto"].unique())
        raise ValueError(f"Unmapped CNMC product names: {unknown}")

    key = ["Fecha", "CCAA", "Provincia", "Producto_slug"]
    dup_count = raw.duplicated(key).sum()
    if dup_count:
        raise ValueError(f"CNMC raw data has {dup_count} duplicate province-product-month rows")

    return raw[
        [
            "Fecha",
            "CCAA",
            "Provincia",
            "Tipo_Producto",
            "Producto_slug",
            "Consumo_Tm",
            "source_file",
        ]
    ].sort_values(["Fecha", "CCAA", "Provincia", "Producto_slug"]).reset_index(drop=True)


def build_ccaa_table(provincial: pd.DataFrame) -> pd.DataFrame:
    ccaa = (
        provincial.groupby(["Fecha", "CCAA", "Tipo_Producto", "Producto_slug"], as_index=False)
        ["Consumo_Tm"]
        .sum()
    )
    national = (
        ccaa.groupby(["Fecha", "Tipo_Producto", "Producto_slug"], as_index=False)["Consumo_Tm"]
        .sum()
        .assign(CCAA="ESPAÑA")
    )
    out = pd.concat([ccaa, national], ignore_index=True)
    return out.sort_values(["Fecha", "CCAA", "Producto_slug"]).reset_index(drop=True)


def build_diesel_market_features(ccaa: pd.DataFrame) -> pd.DataFrame:
    wide = ccaa.pivot_table(
        index=["Fecha", "CCAA"],
        columns="Producto_slug",
        values="Consumo_Tm",
        aggfunc="sum",
        fill_value=0,
    ).reset_index()
    wide.columns.name = None

    for col in ["Biodiesel", "GasoleoA", "GasoleoB", "GasoleoC", "OtrosGasoleos"]:
        if col not in wide.columns:
            wide[col] = 0.0

    diesel_pool = (
        wide["Biodiesel"]
        + wide["GasoleoA"]
        + wide["GasoleoB"]
        + wide["GasoleoC"]
        + wide["OtrosGasoleos"]
    )
    out = wide[["Fecha", "CCAA"]].copy()
    out["CNMC_Biodiesel_Tm"] = wide["Biodiesel"].astype(float)
    out["GasoleoA_Tm"] = wide["GasoleoA"].astype(float)
    out["DieselPool_Tm"] = diesel_pool.astype(float)
    out["Biodiesel_GasoleoA_Ratio"] = np.where(
        out["GasoleoA_Tm"] > 0,
        out["CNMC_Biodiesel_Tm"] / out["GasoleoA_Tm"],
        np.nan,
    )
    out["Biodiesel_DieselPool_Share"] = np.where(
        out["DieselPool_Tm"] > 0,
        out["CNMC_Biodiesel_Tm"] / out["DieselPool_Tm"],
        np.nan,
    )

    if out[["GasoleoA_Tm", "Biodiesel_GasoleoA_Ratio"]].isna().sum().sum() > 0:
        raise ValueError("CNMC diesel-market features contain unexpected nulls")

    return out.sort_values(["Fecha", "CCAA"]).reset_index(drop=True)


def reconcile_biodiesel(features: pd.DataFrame) -> None:
    existing_path = DATA_INPUTS / "consumo_biodiesel_ccaa.csv"
    if not existing_path.exists():
        print("Skipping biodiesel reconciliation: consumo_biodiesel_ccaa.csv not found")
        return

    existing = pd.read_csv(existing_path)
    existing["Fecha"] = existing["Fecha"].astype(str).str[:7]

    compare = existing.merge(
        features[features["Fecha"] <= "2025-12"][["Fecha", "CCAA", "CNMC_Biodiesel_Tm"]],
        on=["Fecha", "CCAA"],
        how="left",
    )
    missing = compare["CNMC_Biodiesel_Tm"].isna().sum()
    if missing:
        raise ValueError(f"CNMC biodiesel reconciliation has {missing} missing rows")

    diff = compare["Consumo_Tm"].astype(float) - compare["CNMC_Biodiesel_Tm"].astype(float)
    max_abs_diff = float(diff.abs().max())
    if max_abs_diff > 1e-9:
        bad = compare.loc[diff.abs() > 1e-9, ["Fecha", "CCAA", "Consumo_Tm", "CNMC_Biodiesel_Tm"]]
        raise ValueError(
            "CNMC BIODIESEL does not reconcile to existing consumo_biodiesel_ccaa.csv. "
            f"Max abs diff: {max_abs_diff}\n{bad.head(20).to_string(index=False)}"
        )

    print("CNMC BIODIESEL reconciles exactly to consumo_biodiesel_ccaa.csv for 2023-2025")


def main() -> None:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    provincial = read_raw_files()
    ccaa = build_ccaa_table(provincial)
    features = build_diesel_market_features(ccaa)
    reconcile_biodiesel(features)

    provincial_path = DATA_PROCESSED / "cnmc_consumos_petroleo_provincial.csv"
    ccaa_path = DATA_PROCESSED / "cnmc_consumos_petroleo_ccaa.csv"
    features_path = DATA_PROCESSED / "cnmc_diesel_market_features.csv"

    provincial.to_csv(provincial_path, index=False, encoding="utf-8")
    ccaa.to_csv(ccaa_path, index=False, encoding="utf-8")
    features.to_csv(features_path, index=False, encoding="utf-8")

    print(f"Saved {provincial_path} ({provincial.shape[0]} rows x {provincial.shape[1]} cols)")
    print(f"Saved {ccaa_path} ({ccaa.shape[0]} rows x {ccaa.shape[1]} cols)")
    print(f"Saved {features_path} ({features.shape[0]} rows x {features.shape[1]} cols)")
    print(f"CNMC feature date range: {features['Fecha'].min()} to {features['Fecha'].max()}")


if __name__ == "__main__":
    main()
