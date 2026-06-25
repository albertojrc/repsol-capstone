"""
Extract interpretable driver detail for whichever model is currently selected
per target: SARIMA coefficient significance, or growth-curve (Logistic /
Gompertz) shape parameters and seasonal decomposition.

scripts/05_modeling_with_cnmc.py already refits the selected model on the
full 2023-2025 history to produce the shipped 2026-2027 forecast
(final_forecasts()), but it only keeps the forecast values, not the fitted
coefficients themselves. This script reuses the exact same production
fitting functions (train_sarima, train_growth_curve) on the exact same
production order/curve choice, purely to expose that already-computed detail
for interpretation. It does not change model selection or any forecast value.
"""

from __future__ import annotations

import ast
import importlib.util
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

warnings.filterwarnings("ignore")

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_FEATURES = REPO_ROOT / "data" / "features"
DATA_OUTPUTS = REPO_ROOT / "data" / "outputs"

_spec = importlib.util.spec_from_file_location(
    "modeling_with_cnmc", REPO_ROOT / "scripts" / "05_modeling_with_cnmc.py"
)
modeling = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(modeling)

SARIMA_TERM_MEANING = {
    "ar.L1": "Autoregressive: this month's (differenced) demand vs. last month's",
    "ar.L2": "Autoregressive: this month's (differenced) demand vs. 2 months ago",
    "ma.L1": "Moving-average: correction from last month's forecast error (shock)",
    "ma.L2": "Moving-average: correction from the forecast error 2 months ago",
    "ar.S.L12": "Seasonal autoregressive: this month vs. the same month last year",
    "ma.S.L12": "Seasonal moving-average: shock from the same month last year",
    "sigma2": "Residual variance (fit quality, not a structural driver)",
}


def sarima_driver_rows(target: str) -> list[dict]:
    acceptance = pd.read_csv(DATA_OUTPUTS / "sarima_order_acceptance.csv")
    row = acceptance.loc[acceptance["Target"].eq(target)].iloc[0]
    order = ast.literal_eval(row["Production_Order"])
    seasonal_order = ast.literal_eval(row["Production_Seasonal_Order"])

    df_all = pd.read_csv(DATA_FEATURES / "features_modelo_completo.csv")
    full = df_all[df_all["Target"].eq(target)].sort_values("Fecha")
    result = modeling.train_sarima(full["Consumo_Tm"].values, order, seasonal_order)

    rows = []
    for term, coef, std_err, pvalue in zip(
        result.param_names, result.params, result.bse, result.pvalues
    ):
        rows.append(
            {
                "Target": target,
                "Production_Order": str(order),
                "Production_Seasonal_Order": str(seasonal_order),
                "Term": term,
                "Meaning": SARIMA_TERM_MEANING.get(term, term),
                "Coefficient": round(float(coef), 4),
                "Std_Err": round(float(std_err), 4),
                "P_Value": round(float(pvalue), 4),
                "Significant_5pct": bool(pvalue < 0.05),
            }
        )
    return rows


def curve_driver_rows(target: str, curve_type: str) -> tuple[list[dict], list[dict]]:
    df_all = pd.read_csv(DATA_FEATURES / "features_modelo_completo.csv")
    full = df_all[df_all["Target"].eq(target)].sort_values("Fecha")
    t = full["Tendencia"].values.astype(float)
    y = full["Consumo_Tm"].values.astype(float)
    mes = full["Mes"].values.astype(float)
    y_max = float(np.max(y))

    curve = modeling.train_growth_curve(t, y, mes, curve_type)
    popt = curve["params"]
    if curve_type == "Logistic":
        trend_pred = modeling._logistic_fn(t, *popt)
        param_names = ["L", "k", "t0"]
        param_meaning = {
            "L": "Asymptote: long-run saturation level the curve approaches (Tm/month)",
            "k": "Steepness: how fast demand approaches the asymptote",
            "t0": "Inflection point: month-index of fastest growth",
        }
    else:
        trend_pred = modeling._gompertz_fn(t, *popt)
        param_names = ["L", "b", "k"]
        param_meaning = {
            "L": "Asymptote: long-run saturation level the curve approaches (Tm/month)",
            "b": "Displacement: how far the curve starts below its asymptote",
            "k": "Growth rate: how fast the curve closes the gap to its asymptote",
        }

    param_rows = []
    for name, value in zip(param_names, popt):
        param_rows.append(
            {
                "Target": target,
                "Curve_Type": curve_type,
                "Parameter": name,
                "Meaning": param_meaning[name],
                "Value": round(float(value), 4),
            }
        )
    param_rows.append(
        {
            "Target": target,
            "Curve_Type": curve_type,
            "Parameter": "Observed_Max_Tm",
            "Meaning": "Highest Consumo_Tm actually observed in 2023-2025",
            "Value": round(y_max, 1),
        }
    )
    param_rows.append(
        {
            "Target": target,
            "Curve_Type": curve_type,
            "Parameter": "Asymptote_to_Observed_Max_Ratio",
            "Meaning": "L divided by the observed historical maximum",
            "Value": round(float(popt[0]) / y_max, 3),
        }
    )

    sin_mes = np.sin(2 * np.pi * mes / 12)
    cos_mes = np.cos(2 * np.pi * mes / 12)
    resid = y - trend_pred
    X = sm.add_constant(np.column_stack([sin_mes, cos_mes]))
    seasonal_fit = sm.OLS(resid, X).fit()
    const_c, sin_a, cos_b = seasonal_fit.params
    const_p, sin_p, cos_p = seasonal_fit.pvalues

    months = np.arange(1, 13)
    seasonal_by_month = (
        sin_a * np.sin(2 * np.pi * months / 12) + cos_b * np.cos(2 * np.pi * months / 12) + const_c
    )
    peak_month = int(months[np.argmax(seasonal_by_month)])
    trough_month = int(months[np.argmin(seasonal_by_month)])
    amplitude = float(np.sqrt(sin_a**2 + cos_b**2))

    seasonal_rows = [
        {
            "Target": target,
            "Curve_Type": curve_type,
            "Sin_Coef": round(float(sin_a), 3),
            "Sin_P_Value": round(float(sin_p), 4),
            "Cos_Coef": round(float(cos_b), 3),
            "Cos_P_Value": round(float(cos_p), 4),
            "Const_Offset_Tm": round(float(const_c), 1),
            "Const_P_Value": round(float(const_p), 4),
            "Any_Seasonal_Term_Significant_5pct": bool(min(sin_p, cos_p) < 0.05),
            "Seasonal_R2": round(float(seasonal_fit.rsquared), 3),
            "Amplitude_Tm": round(amplitude, 1),
            "Peak_Month": peak_month,
            "Trough_Month": trough_month,
        }
    ]
    return param_rows, seasonal_rows


def mini_model_curve_selection(target: str) -> dict:
    """
    Replicate notebooks/12_mini_trend_regulation_model.ipynb's curve choice
    exactly: fit both Logistic and Gompertz on the full history and keep
    whichever has the higher in-sample R2 (notebook 12's own selection rule,
    not the production walk-forward gate). Reuses scripts/05's own curve
    functions so the math is identical to both notebooks, not re-derived.
    """
    df_all = pd.read_csv(DATA_FEATURES / "features_modelo_completo.csv")
    full = df_all[df_all["Target"].eq(target)].sort_values("Fecha")
    t = full["Tendencia"].values.astype(float)
    y = full["Consumo_Tm"].values.astype(float)
    mes = full["Mes"].values.astype(float)

    r2_by_curve: dict[str, float] = {}
    for curve_type in ["Logistic", "Gompertz"]:
        curve = modeling.train_growth_curve(t, y, mes, curve_type)
        fn = modeling._logistic_fn if curve_type == "Logistic" else modeling._gompertz_fn
        trend_pred = fn(t, *curve["params"])
        a, b, c = curve["seasonal_coef"]
        fitted = np.maximum(
            trend_pred + a * np.sin(2 * np.pi * mes / 12) + b * np.cos(2 * np.pi * mes / 12) + c, 0
        )
        sst = float(np.sum((y - y.mean()) ** 2))
        r2_by_curve[curve_type] = float(1 - np.sum((y - fitted) ** 2) / sst)

    chosen = max(r2_by_curve, key=r2_by_curve.get)
    return {
        "Target": target,
        "Mini_InSample_R2_Logistic": round(r2_by_curve["Logistic"], 4),
        "Mini_InSample_R2_Gompertz": round(r2_by_curve["Gompertz"], 4),
        "Mini_Chosen_Curve": chosen,
    }


def build_mini_model_cross_check() -> pd.DataFrame:
    final = pd.read_csv(DATA_OUTPUTS / "metricas_final_selected.csv")
    selected_fc = pd.read_csv(DATA_OUTPUTS / "forecast_24m_selected.csv")
    mini_path = DATA_OUTPUTS / "mini_model_scenarios.csv"
    if not mini_path.exists():
        print(f"Skipping mini-model cross-check: {mini_path} not found (run notebooks/12 first)")
        return pd.DataFrame()
    mini = pd.read_csv(mini_path)

    production_total = selected_fc.groupby("Target")["Forecast"].sum()
    mini_total = mini.groupby(["Serie", "Scenario"])["Forecast_Tm"].sum().unstack()

    rows = []
    for target, production_model in zip(final["Target"], final["Model"]):
        selection = mini_model_curve_selection(target)
        same_family = bool(
            production_model in ("Logistic", "Gompertz") and production_model == selection["Mini_Chosen_Curve"]
        )
        rows.append(
            {
                "Target": target,
                "Production_Model": production_model,
                "Production_24m_Total_Tm": round(float(production_total.get(target, np.nan)), 1),
                "Mini_Conservative_24m_Total_Tm": round(float(mini_total.loc[target, "Conservative"]), 1),
                "Mini_Central_24m_Total_Tm": round(float(mini_total.loc[target, "Central"]), 1),
                "Mini_Optimistic_24m_Total_Tm": round(float(mini_total.loc[target, "Optimistic"]), 1),
                "Mini_Chosen_Curve": selection["Mini_Chosen_Curve"],
                "Mini_InSample_R2_Logistic": selection["Mini_InSample_R2_Logistic"],
                "Mini_InSample_R2_Gompertz": selection["Mini_InSample_R2_Gompertz"],
                "Same_Curve_Family_As_Production": same_family,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    final = pd.read_csv(DATA_OUTPUTS / "metricas_final_selected.csv")
    selected = dict(zip(final["Target"], final["Model"]))

    sarima_rows: list[dict] = []
    curve_param_rows: list[dict] = []
    curve_seasonal_rows: list[dict] = []
    for target, model in selected.items():
        if model == "SARIMA":
            sarima_rows.extend(sarima_driver_rows(target))
        elif model in ("Logistic", "Gompertz"):
            params, seasonal = curve_driver_rows(target, model)
            curve_param_rows.extend(params)
            curve_seasonal_rows.extend(seasonal)
        else:
            print(f"No driver extraction implemented for {target} / {model} (not SARIMA/Logistic/Gompertz)")

    df_sarima = pd.DataFrame(sarima_rows)
    df_curve_params = pd.DataFrame(curve_param_rows)
    df_curve_seasonal = pd.DataFrame(curve_seasonal_rows)

    df_sarima.to_csv(DATA_OUTPUTS / "selected_model_sarima_drivers.csv", index=False, encoding="utf-8")
    df_curve_params.to_csv(DATA_OUTPUTS / "selected_model_curve_parameters.csv", index=False, encoding="utf-8")
    df_curve_seasonal.to_csv(DATA_OUTPUTS / "selected_model_curve_seasonal.csv", index=False, encoding="utf-8")

    df_mini_check = build_mini_model_cross_check()
    if not df_mini_check.empty:
        df_mini_check.to_csv(DATA_OUTPUTS / "mini_model_cross_check.csv", index=False, encoding="utf-8")

    print("Selected model per target:", selected)
    print("\nSARIMA driver coefficients (selected-model targets only):")
    print(df_sarima.to_string(index=False) if not df_sarima.empty else "  none")
    print("\nGrowth-curve shape parameters (selected-model targets only):")
    print(df_curve_params.to_string(index=False) if not df_curve_params.empty else "  none")
    print("\nGrowth-curve seasonal decomposition (selected-model targets only):")
    print(df_curve_seasonal.to_string(index=False) if not df_curve_seasonal.empty else "  none")
    print("\nMini trend model (notebook 12) cross-check:")
    print(df_mini_check.to_string(index=False) if not df_mini_check.empty else "  skipped (mini_model_scenarios.csv not found)")


if __name__ == "__main__":
    main()
