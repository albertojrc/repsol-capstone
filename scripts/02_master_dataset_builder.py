"""
Build master_dataset.csv (and .xlsx + _metadata.json) from raw input files.

Inputs  (data/inputs/):
    consumo_biodiesel_ccaa.csv
    macro_indicadores_ine.csv
    brent_oil_price_monthly_2023_onwards.csv
    precios_combustibles_2023.csv
    precios_combustibles_2024.csv
    precios_combustibles_2025.csv

Outputs (data/inputs/):
    master_dataset.csv          — 720 rows × 17 columns (primary)
    master_dataset.xlsx         — same data + metadata sheet
    master_dataset_metadata.json — variable dictionary

Run from repo root:
    python scripts/02_master_dataset_builder.py
"""

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO_ROOT   = Path(__file__).resolve().parent.parent
DATA_INPUTS = REPO_ROOT / "data" / "inputs"
DATA_PROCESSED = REPO_ROOT / "data" / "processed"

# ── Province → CCAA mapping (all 52 provinces) ────────────────────────────────
PROVINCE_CCAA = {
    "Albacete":              "Castilla - La Mancha",
    "Alicante/Alacant":      "Comunitat Valenciana",
    "Almería":               "Andalucía",
    "Araba/Álava":           "País Vasco",
    "Asturias":              "Asturias, Principado de",
    "Badajoz":               "Extremadura",
    "Balears, Illes":        "Balears, Illes",
    "Barcelona":             "Cataluña",
    "Bizkaia":               "País Vasco",
    "Burgos":                "Castilla y León",
    "Cantabria":             "Cantabria",
    "Castellón/Castelló":    "Comunitat Valenciana",
    "Ceuta":                 "Ceuta",
    "Ciudad Real":           "Castilla - La Mancha",
    "Coruña, A":             "Galicia",
    "Cuenca":                "Castilla - La Mancha",
    "Cáceres":               "Extremadura",
    "Cádiz":                 "Andalucía",
    "Córdoba":               "Andalucía",
    "Gipuzkoa":              "País Vasco",
    "Girona":                "Cataluña",
    "Granada":               "Andalucía",
    "Guadalajara":           "Castilla - La Mancha",
    "Huelva":                "Andalucía",
    "Huesca":                "Aragón",
    "Jaén":                  "Andalucía",
    "León":                  "Castilla y León",
    "Lleida":                "Cataluña",
    "Lugo":                  "Galicia",
    "Madrid":                "Madrid, Comunidad de",
    "Melilla":               "Melilla",
    "Murcia":                "Murcia, Región de",
    "Málaga":                "Andalucía",
    "Navarra":               "Navarra, Comunidad Foral de",
    "Ourense":               "Galicia",
    "Palencia":              "Castilla y León",
    "Palmas, Las":           "Canarias",
    "Pontevedra":            "Galicia",
    "Rioja, La":             "Rioja, La",
    "Salamanca":             "Castilla y León",
    "Santa Cruz de Tenerife": "Canarias",
    "Segovia":               "Castilla y León",
    "Sevilla":               "Andalucía",
    "Soria":                 "Castilla y León",
    "Tarragona":             "Cataluña",
    "Teruel":                "Aragón",
    "Toledo":                "Castilla - La Mancha",
    "Valencia/València":     "Comunitat Valenciana",
    "Valladolid":            "Castilla y León",
    "Zamora":                "Castilla y León",
    "Zaragoza":              "Aragón",
    "Ávila":                 "Castilla y León",
}

# Maps raw Producto strings to short column slugs
PRODUCT_SLUG = {
    "Gasóleo A habitual":  "Gasoleo_A",
    "Gasóleo Premium":     "Gasoleo_Premium",
    "Gasolina 95 E5":      "Gasolina95",
    "Gasolina 98 E5":      "Gasolina98",
}

TARGET_CCAAS = {
    "ESPAÑA",
    "Andalucía",
    "Cataluña",
    "Madrid, Comunidad de",
    "Comunitat Valenciana",
}


def load_consumption() -> pd.DataFrame:
    df = pd.read_csv(DATA_INPUTS / "consumo_biodiesel_ccaa.csv")
    df["Fecha"] = df["Fecha"].astype(str).str[:7]
    return df[["Fecha", "CCAA", "Consumo_Tm"]]


def load_macro() -> pd.DataFrame:
    df = pd.read_csv(DATA_INPUTS / "macro_indicadores_ine.csv")
    df["Fecha"] = df["Fecha"].astype(str).str[:7]
    return df[["Fecha", "IPI_original", "IPI_ajustado", "IPC_var_anual", "Tasa_paro"]]


def load_brent() -> pd.DataFrame:
    df = pd.read_csv(DATA_INPUTS / "brent_oil_price_monthly_2023_onwards.csv")
    date_col  = next(c for c in df.columns if "date" in c.lower() or "fecha" in c.lower())
    price_col = next(c for c in df.columns if "price" in c.lower() or "brent" in c.lower())
    df["Fecha"] = pd.to_datetime(df[date_col]).dt.to_period("M").astype(str)
    return df[["Fecha", price_col]].rename(columns={price_col: "Precio_Brent_USD"})


def load_cnmc_diesel_market_features() -> pd.DataFrame:
    """Load CNMC diesel-market features through the original 2025-12 forecast origin."""
    path = DATA_PROCESSED / "cnmc_diesel_market_features.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run scripts/03_clean_cnmc_petroleum.py first."
        )
    cols = [
        "Fecha",
        "CCAA",
        "CNMC_Biodiesel_Tm",
        "GasoleoA_Tm",
        "DieselPool_Tm",
        "Biodiesel_GasoleoA_Ratio",
        "Biodiesel_DieselPool_Share",
    ]
    df = pd.read_csv(path, usecols=cols)
    df["Fecha"] = df["Fecha"].astype(str).str[:7]
    return df[df["Fecha"] <= "2025-12"].copy()


def load_and_aggregate_prices() -> pd.DataFrame:
    frames = []
    for year in [2023, 2024, 2025]:
        path = DATA_INPUTS / f"precios_combustibles_{year}.csv"
        if not path.exists():
            print(f"  Warning: {path.name} not found — skipping year {year}")
            continue
        chunk = pd.read_csv(path, sep=None, engine="python", decimal=",", thousands=".")
        # Normalise column names regardless of exact wording
        col_map = {}
        for col in chunk.columns:
            cl = col.lower()
            if "fecha" in cl or "date" in cl:
                col_map[col] = "Fecha"
            elif "provincia" in cl:
                col_map[col] = "Provincia"
            elif "producto" in cl:
                col_map[col] = "Producto"
            elif "pai" in cl:
                col_map[col] = "PAI"
            elif "pvp" in cl:
                col_map[col] = "PVP"
        chunk = chunk.rename(columns=col_map)[["Fecha", "Provincia", "Producto", "PAI", "PVP"]]
        # Convert price columns if they are strings with comma decimals
        for pc in ["PAI", "PVP"]:
            if chunk[pc].dtype == object:
                chunk[pc] = chunk[pc].str.replace(",", ".").astype(float)
        frames.append(chunk)

    raw = pd.concat(frames, ignore_index=True)

    raw["Fecha"] = pd.to_datetime(raw["Fecha"]).dt.to_period("M").astype(str)
    raw["CCAA"] = raw["Provincia"].map(PROVINCE_CCAA)
    raw["Slug"] = raw["Producto"].map(PRODUCT_SLUG)

    raw = raw.dropna(subset=["CCAA", "Slug"])

    monthly = (
        raw.groupby(["Fecha", "CCAA", "Slug"])[["PVP", "PAI"]]
        .mean()
        .reset_index()
    )

    pvp_wide = monthly.pivot_table(index=["Fecha", "CCAA"], columns="Slug", values="PVP")
    pvp_wide.columns = [f"PVP_{c}" for c in pvp_wide.columns]

    pai_wide = monthly.pivot_table(index=["Fecha", "CCAA"], columns="Slug", values="PAI")
    pai_wide.columns = [f"PAI_{c}" for c in pai_wide.columns]

    prices = pvp_wide.join(pai_wide).reset_index()

    # Fill ESPAÑA rows with national mean per month
    price_cols = [c for c in prices.columns if c not in ("Fecha", "CCAA")]
    national_mean = (
        prices[prices["CCAA"] != "ESPAÑA"]
        .groupby("Fecha")[price_cols]
        .mean()
        .reset_index()
        .assign(CCAA="ESPAÑA")
    )

    prices = prices[prices["CCAA"] != "ESPAÑA"]
    prices = pd.concat([prices, national_mean], ignore_index=True)

    return prices


def build_master() -> pd.DataFrame:
    print("Loading consumption data...")
    consumo = load_consumption()

    print("Loading macro indicators...")
    macro = load_macro()

    print("Loading Brent price...")
    brent = load_brent()

    print("Aggregating fuel prices (daily×province → monthly×CCAA)...")
    prices = load_and_aggregate_prices()

    print("Loading CNMC diesel-market features...")
    cnmc = load_cnmc_diesel_market_features()

    print("Building master dataset...")
    master = consumo.copy()
    master["Target"] = master["CCAA"].isin(TARGET_CCAAS).astype(int)

    master = master.merge(macro, on="Fecha", how="left")
    master = master.merge(brent, on="Fecha", how="left")
    master = master.merge(prices, on=["Fecha", "CCAA"], how="left")
    master = master.merge(cnmc, on=["Fecha", "CCAA"], how="left")

    if master["GasoleoA_Tm"].isna().any():
        missing = master.loc[master["GasoleoA_Tm"].isna(), ["Fecha", "CCAA"]].head(20)
        raise ValueError(
            "Missing CNMC diesel-market features after master merge:\n"
            + missing.to_string(index=False)
        )

    biodiesel_diff = (
        master["Consumo_Tm"].astype(float) - master["CNMC_Biodiesel_Tm"].astype(float)
    ).abs().max()
    if biodiesel_diff > 1e-9:
        raise ValueError(
            "CNMC_Biodiesel_Tm does not reconcile to Consumo_Tm after merge. "
            f"Max abs diff: {biodiesel_diff}"
        )

    col_order = [
        "Fecha", "CCAA", "Consumo_Tm", "Target",
        "IPI_original", "IPI_ajustado", "IPC_var_anual", "Tasa_paro",
        "Precio_Brent_USD",
        "PVP_Gasoleo_A", "PVP_Gasoleo_Premium", "PVP_Gasolina95", "PVP_Gasolina98",
        "PAI_Gasoleo_A", "PAI_Gasoleo_Premium", "PAI_Gasolina95", "PAI_Gasolina98",
        "CNMC_Biodiesel_Tm", "GasoleoA_Tm", "DieselPool_Tm",
        "Biodiesel_GasoleoA_Ratio", "Biodiesel_DieselPool_Share",
    ]
    col_order = [c for c in col_order if c in master.columns]
    master = master[col_order].sort_values(["Fecha", "CCAA"]).reset_index(drop=True)

    return master


METADATA = {
    "dataset": "master_dataset",
    "description": "Monthly biodiesel demand + macroeconomic + Brent + fuel price + CNMC diesel-market variables by CCAA (2023-01 to 2025-12)",
    "primary_key": ["Fecha", "CCAA"],
    "rows": 720,
    "columns": 22,
    "date_range": {"start": "2023-01", "end": "2025-12"},
    "known_nulls": "36 NaN rows in PVP_Gasolina98 / PAI_Gasolina98 — Melilla does not sell Gasolina 98",
    "variables": {
        "Fecha": {"type": "str", "format": "YYYY-MM", "description": "Month"},
        "CCAA": {"type": "str", "description": "Comunidad Autónoma (19 + ESPAÑA + Melilla + Ceuta = 20 units)"},
        "Consumo_Tm": {"type": "float", "unit": "metric tonnes", "description": "Monthly biodiesel consumption"},
        "Target": {"type": "int", "values": [0, 1], "description": "1 for 5 modelling targets: ESPAÑA, Andalucía, Cataluña, Madrid Comunidad de, Comunitat Valenciana"},
        "IPI_original": {"type": "float", "source": "INE", "description": "Industrial Production Index — original series"},
        "IPI_ajustado": {"type": "float", "source": "INE", "description": "Industrial Production Index — seasonally adjusted"},
        "IPC_var_anual": {"type": "float", "unit": "%", "source": "INE", "description": "CPI annual variation"},
        "Tasa_paro": {"type": "float", "unit": "%", "source": "INE", "description": "Unemployment rate"},
        "Precio_Brent_USD": {"type": "float", "unit": "USD/barrel", "description": "Monthly Brent crude oil price"},
        "PVP_Gasoleo_A": {"type": "float", "unit": "€/L", "description": "Retail price Gasóleo A habitual — CCAA monthly mean"},
        "PVP_Gasoleo_Premium": {"type": "float", "unit": "€/L", "description": "Retail price Gasóleo Premium — CCAA monthly mean"},
        "PVP_Gasolina95": {"type": "float", "unit": "€/L", "description": "Retail price Gasolina 95 E5 — CCAA monthly mean"},
        "PVP_Gasolina98": {"type": "float", "unit": "€/L", "description": "Retail price Gasolina 98 — CCAA monthly mean (NaN for Melilla)"},
        "PAI_Gasoleo_A": {"type": "float", "unit": "€/L", "description": "Net (pre-tax) price Gasóleo A — CCAA monthly mean"},
        "PAI_Gasoleo_Premium": {"type": "float", "unit": "€/L", "description": "Net price Gasóleo Premium — CCAA monthly mean"},
        "PAI_Gasolina95": {"type": "float", "unit": "€/L", "description": "Net price Gasolina 95 E5 — CCAA monthly mean"},
        "PAI_Gasolina98": {"type": "float", "unit": "€/L", "description": "Net price Gasolina 98 — CCAA monthly mean (NaN for Melilla)"},
        "CNMC_Biodiesel_Tm": {"type": "float", "unit": "metric tonnes", "source": "CNMC", "description": "CNMC biodiesel consumption, reconciled to Consumo_Tm"},
        "GasoleoA_Tm": {"type": "float", "unit": "metric tonnes", "source": "CNMC", "description": "Monthly Gasoleo A market consumption by CCAA/national total"},
        "DieselPool_Tm": {"type": "float", "unit": "metric tonnes", "source": "CNMC", "description": "Biodiesel + Gasoleo A/B/C + Otros Gasoleos consumption"},
        "Biodiesel_GasoleoA_Ratio": {"type": "float", "source": "CNMC", "description": "Biodiesel consumption divided by Gasoleo A consumption"},
        "Biodiesel_DieselPool_Share": {"type": "float", "source": "CNMC", "description": "Biodiesel consumption divided by the diesel-pool proxy"},
    },
}


def save_outputs(master: pd.DataFrame) -> None:
    csv_path  = DATA_INPUTS / "master_dataset.csv"
    xlsx_path = DATA_INPUTS / "master_dataset.xlsx"
    json_path = DATA_INPUTS / "master_dataset_metadata.json"

    print(f"Saving CSV → {csv_path.name}")
    master.to_csv(csv_path, index=False)

    print(f"Saving XLSX → {xlsx_path.name}")
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        master.to_excel(writer, sheet_name="master_dataset", index=False)

        meta_rows = []
        for col, info in METADATA["variables"].items():
            row = {"Column": col}
            row.update(info)
            meta_rows.append(row)
        pd.DataFrame(meta_rows).to_excel(writer, sheet_name="metadata", index=False)

    print(f"Saving JSON metadata → {json_path.name}")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(METADATA, f, ensure_ascii=False, indent=2)


def main() -> None:
    print("=" * 60)
    print("MASTER DATASET BUILDER")
    print("=" * 60)

    master = build_master()

    print(f"\nMaster dataset: {master.shape[0]} rows × {master.shape[1]} columns")
    null_count = master.isnull().sum().sum()
    null_pct   = null_count / master.size * 100
    print(f"Null values: {null_count} ({null_pct:.1f}%)")

    if null_count > 0:
        print("\nNull breakdown by column:")
        for col in master.columns:
            n = master[col].isnull().sum()
            if n > 0:
                print(f"  {col}: {n} nulls")

    save_outputs(master)

    print("\nDone.")
    print(f"  CSV  : {DATA_INPUTS / 'master_dataset.csv'}")
    print(f"  XLSX : {DATA_INPUTS / 'master_dataset.xlsx'}")
    print(f"  JSON : {DATA_INPUTS / 'master_dataset_metadata.json'}")


if __name__ == "__main__":
    main()
