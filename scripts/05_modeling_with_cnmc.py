"""
Train, validate, and forecast biodiesel demand with CNMC diesel-market and
biofuel mandate features.

Outputs are written to data/outputs and reports/figures, preserving the existing
CSV filenames used by the notebooks/Tableau flow while adding the new
Diesel Share candidate model.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.optimize import curve_fit
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.statespace.sarimax import SARIMAX


warnings.filterwarnings("ignore")
np.random.seed(42)

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_FEATURES = REPO_ROOT / "data" / "features"
DATA_INPUTS = REPO_ROOT / "data" / "inputs"
DATA_OUTPUTS = REPO_ROOT / "data" / "outputs"
FIGURES = REPO_ROOT / "reports" / "figures"

DATA_OUTPUTS.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

TARGETS = ["Nacional", "Madrid", "Cataluña", "Andalucía", "Valencia"]
TARGET_COLORS = {
    "Nacional": "#FF6B35",
    "Madrid": "#004E89",
    "Cataluña": "#1A936F",
    "Andalucía": "#C84B31",
    "Valencia": "#8E44AD",
}

BASE_ML_FEATS = [
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
]

DIESEL_FEATS = [
    "GasoleoA_Tm_lag1",
    "GasoleoA_Tm_roll3_lag1",
    "Biodiesel_GasoleoA_Ratio_lag1",
    "Biodiesel_GasoleoA_Ratio_roll3_lag1",
]

MANDATE_FEATS = [
    "Mandato_Energia_Pct",
    "Mandato_Biodiesel_Blend_Pct",
]

ML_FEATS = BASE_ML_FEATS + DIESEL_FEATS + MANDATE_FEATS

SHARE_FEATS = [
    "Tendencia",
    "Mes",
    "sin_mes",
    "cos_mes",
    "IPI_original_lag1",
    "IPC_var_anual_lag1",
    "Tasa_paro_lag1",
    "GasoleoA_Tm_lag1",
    "GasoleoA_Tm_roll3_lag1",
    "Biodiesel_GasoleoA_Ratio_lag1",
    "Biodiesel_GasoleoA_Ratio_roll3_lag1",
    *MANDATE_FEATS,
]

CANDIDATE_COLS = [
    "SARIMA",
    "Ridge",
    "Random Forest",
    "XGBoost",
    "Logistic",
    "Gompertz",
    "Diesel Share",
]

FORECAST_DATES = pd.date_range("2026-01-01", periods=24, freq="MS")


def load_mandate_schedule() -> pd.DataFrame:
    mandates = pd.read_csv(DATA_INPUTS / "mandato_biocarburantes.csv")
    year_col = "Año" if "Año" in mandates.columns else "AÃ±o"
    required = [year_col, *MANDATE_FEATS]
    missing = [col for col in required if col not in mandates.columns]
    if missing:
        raise ValueError(f"mandato_biocarburantes.csv is missing columns: {missing}")
    mandates = mandates[required].rename(columns={year_col: "Año"}).copy()
    mandates["Año"] = mandates["Año"].astype(int)
    for col in MANDATE_FEATS:
        mandates[col] = mandates[col].astype(float)
    return mandates


MANDATE_SCHEDULE = load_mandate_schedule()


def mandate_values_for_date(dt: pd.Timestamp) -> dict[str, float]:
    row = MANDATE_SCHEDULE[MANDATE_SCHEDULE["Año"] == int(dt.year)]
    if row.empty:
        raise ValueError(f"No mandate schedule row for year {dt.year}")
    values = row.iloc[0][MANDATE_FEATS].astype(float).to_dict()
    if dt < pd.Timestamp("2024-08-01"):
        values["Mandato_Biodiesel_Blend_Pct"] = 0.0
    return values


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    y_true = np.array(y_true, dtype=float)
    y_pred = np.maximum(np.array(y_pred, dtype=float), 0)
    mae = mean_absolute_error(y_true, y_pred)
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mask = y_true > 0
    mape = float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100) if mask.sum() else np.nan
    sst = float(np.sum((y_true - y_true.mean()) ** 2))
    r2 = float(1 - np.sum((y_true - y_pred) ** 2) / sst) if sst > 0 else np.nan
    return {"MAE": round(mae, 1), "RMSE": round(rmse, 1), "MAPE": round(mape, 1), "R2": round(r2, 3)}


def train_sarima(y_train: np.ndarray):
    model = SARIMAX(
        np.log1p(y_train),
        order=(1, 1, 1),
        seasonal_order=(1, 0, 0, 12),
        enforce_stationarity=False,
        enforce_invertibility=False,
    )
    return model.fit(disp=False)


def predict_sarima(result, n_steps: int) -> np.ndarray:
    return np.maximum(np.expm1(result.forecast(steps=n_steps)), 0)


def _logistic_fn(t, L, k, t0):
    return L / (1 + np.exp(-k * (t - t0)))


def _gompertz_fn(t, L, b, k):
    return L * np.exp(-b * np.exp(-k * t))


def train_growth_curve(t: np.ndarray, y: np.ndarray, mes: np.ndarray, curve_type: str) -> dict:
    y_max = float(np.max(y))
    if curve_type == "Logistic":
        p0 = [y_max * 3, 0.3, float(np.median(t))]
        bounds = ([y_max * 1.01, 0.01, t.min() - 24], [y_max * 60, 3.0, t.max() + 60])
        popt, _ = curve_fit(_logistic_fn, t, y, p0=p0, bounds=bounds, maxfev=20000)
        trend_pred = _logistic_fn(t, *popt)
    elif curve_type == "Gompertz":
        p0 = [y_max * 3, 5.0, 0.15]
        bounds = ([y_max * 1.01, 0.1, 0.001], [y_max * 60, 200.0, 2.0])
        popt, _ = curve_fit(_gompertz_fn, t, y, p0=p0, bounds=bounds, maxfev=20000)
        trend_pred = _gompertz_fn(t, *popt)
    else:
        raise ValueError(f"Unknown curve_type: {curve_type}")

    sin_mes = np.sin(2 * np.pi * mes / 12)
    cos_mes = np.cos(2 * np.pi * mes / 12)
    x_seasonal = np.column_stack([sin_mes, cos_mes, np.ones_like(sin_mes)])
    seas_coef, *_ = np.linalg.lstsq(x_seasonal, y - trend_pred, rcond=None)
    return {"curve_type": curve_type, "params": popt, "seasonal_coef": seas_coef}


def predict_growth_curve(model: dict, t: np.ndarray, mes: np.ndarray) -> np.ndarray:
    if model["curve_type"] == "Logistic":
        trend_pred = _logistic_fn(t, *model["params"])
    else:
        trend_pred = _gompertz_fn(t, *model["params"])
    sin_mes = np.sin(2 * np.pi * mes / 12)
    cos_mes = np.cos(2 * np.pi * mes / 12)
    a, b, c = model["seasonal_coef"]
    return np.maximum(trend_pred + a * sin_mes + b * cos_mes + c, 0)


def train_ml(x_train: np.ndarray, y_train: np.ndarray, model_name: str):
    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(x_train)
    y_log = np.log1p(y_train)
    if model_name == "Ridge":
        model = Ridge(alpha=10.0).fit(x_scaled, y_log)
    elif model_name == "RandomForest":
        model = RandomForestRegressor(
            n_estimators=300,
            max_depth=3,
            min_samples_leaf=3,
            random_state=42,
        ).fit(x_scaled, y_log)
    elif model_name == "XGBoost":
        model = xgb.XGBRegressor(
            n_estimators=300,
            max_depth=2,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.8,
            reg_alpha=1,
            reg_lambda=5,
            random_state=42,
            verbosity=0,
        ).fit(x_scaled, y_log)
    else:
        raise ValueError(f"Unknown ML model: {model_name}")
    return model, scaler


def predict_ml(model, scaler, x_test: np.ndarray) -> np.ndarray:
    log_pred = model.predict(scaler.transform(x_test))
    return np.maximum(np.expm1(np.clip(log_pred, None, 15.0)), 0)


def logit(x: np.ndarray) -> np.ndarray:
    x = np.clip(np.array(x, dtype=float), 1e-6, 0.3)
    return np.log(x / (1 - x))


def inv_logit(x: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-np.clip(x, -20, 20)))


def train_share_model(x_train: np.ndarray, ratio_train: np.ndarray):
    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(x_train)
    model = Ridge(alpha=5.0).fit(x_scaled, logit(ratio_train))
    return model, scaler


def predict_share_ratio(model, scaler, x_test: np.ndarray) -> np.ndarray:
    ratio = inv_logit(model.predict(scaler.transform(x_test)))
    return np.clip(ratio, 0, 0.3)


def latest_complete_year_gasoleo(history: pd.DataFrame) -> dict[int, float]:
    hist = history.copy()
    hist["Fecha_dt"] = pd.to_datetime(hist["Fecha"])
    hist["year"] = hist["Fecha_dt"].dt.year
    hist["month"] = hist["Fecha_dt"].dt.month
    complete_years = hist.groupby("year")["month"].nunique()
    complete_years = complete_years[complete_years == 12]
    if complete_years.empty:
        last = float(hist.sort_values("Fecha")["GasoleoA_Tm"].iloc[-1])
        return {m: last for m in range(1, 13)}
    base_year = int(complete_years.index.max())
    base = hist[hist["year"] == base_year].set_index("month")["GasoleoA_Tm"].to_dict()
    return {m: float(base[m]) for m in range(1, 13)}


def seasonal_naive_gasoleo(history: pd.DataFrame, dates: list[pd.Timestamp]) -> list[float]:
    base = latest_complete_year_gasoleo(history)
    return [base[int(dt.month)] for dt in dates]


def recursive_forecast_ml(model, scaler, history: pd.DataFrame, macro_last: dict, n_steps: int = 24) -> list[float]:
    hist_y = history["Consumo_Tm"].astype(float).tolist()
    hist_gaso = history["GasoleoA_Tm"].astype(float).tolist()
    hist_ratio = history["Biodiesel_GasoleoA_Ratio"].astype(float).tolist()
    future_dates = list(FORECAST_DATES[:n_steps])
    future_gaso = seasonal_naive_gasoleo(history, future_dates)
    forecasts = []

    start_tendencia = int(history["Tendencia"].max()) + 1
    for step, (dt, gaso_t) in enumerate(zip(future_dates, future_gaso)):
        mes = int(dt.month)
        mandate = mandate_values_for_date(dt)
        feat_values = {
            "Tendencia": start_tendencia + step,
            "Mes": mes,
            "sin_mes": np.sin(2 * np.pi * mes / 12),
            "cos_mes": np.cos(2 * np.pi * mes / 12),
            "Lag_1": hist_y[-1],
            "Lag_2": hist_y[-2],
            "Lag_3": hist_y[-3],
            "Roll_mean_3": float(np.mean(hist_y[-3:])),
            "Roll_mean_6": float(np.mean(hist_y[-6:])),
            "IPI_original_lag1": macro_last["IPI_original"],
            "IPC_var_anual_lag1": macro_last["IPC_var_anual"],
            "Tasa_paro_lag1": macro_last["Tasa_paro"],
            "GasoleoA_Tm_lag1": hist_gaso[-1],
            "GasoleoA_Tm_roll3_lag1": float(np.mean(hist_gaso[-3:])),
            "Biodiesel_GasoleoA_Ratio_lag1": hist_ratio[-1],
            "Biodiesel_GasoleoA_Ratio_roll3_lag1": float(np.mean(hist_ratio[-3:])),
            **mandate,
        }
        row = np.array([[feat_values[f] for f in ML_FEATS]])
        pred = float(predict_ml(model, scaler, row)[0])
        pred = max(pred, 0.0)
        forecasts.append(pred)
        hist_y.append(pred)
        hist_gaso.append(gaso_t)
        hist_ratio.append(pred / gaso_t if gaso_t > 0 else 0.0)
    return forecasts


def recursive_forecast_share(model, scaler, history: pd.DataFrame, macro_last: dict, n_steps: int = 24) -> list[float]:
    hist_gaso = history["GasoleoA_Tm"].astype(float).tolist()
    hist_ratio = history["Biodiesel_GasoleoA_Ratio"].astype(float).tolist()
    future_dates = list(FORECAST_DATES[:n_steps])
    future_gaso = seasonal_naive_gasoleo(history, future_dates)
    forecasts = []
    start_tendencia = int(history["Tendencia"].max()) + 1

    for step, (dt, gaso_t) in enumerate(zip(future_dates, future_gaso)):
        mes = int(dt.month)
        mandate = mandate_values_for_date(dt)
        feat_values = {
            "Tendencia": start_tendencia + step,
            "Mes": mes,
            "sin_mes": np.sin(2 * np.pi * mes / 12),
            "cos_mes": np.cos(2 * np.pi * mes / 12),
            "IPI_original_lag1": macro_last["IPI_original"],
            "IPC_var_anual_lag1": macro_last["IPC_var_anual"],
            "Tasa_paro_lag1": macro_last["Tasa_paro"],
            "GasoleoA_Tm_lag1": hist_gaso[-1],
            "GasoleoA_Tm_roll3_lag1": float(np.mean(hist_gaso[-3:])),
            "Biodiesel_GasoleoA_Ratio_lag1": hist_ratio[-1],
            "Biodiesel_GasoleoA_Ratio_roll3_lag1": float(np.mean(hist_ratio[-3:])),
            **mandate,
        }
        row = np.array([[feat_values[f] for f in SHARE_FEATS]])
        ratio = float(predict_share_ratio(model, scaler, row)[0])
        pred = max(ratio * gaso_t, 0.0)
        forecasts.append(pred)
        hist_gaso.append(gaso_t)
        hist_ratio.append(ratio)
    return forecasts


def test_gasoleo_naive(train_history: pd.DataFrame, test_dates: list[pd.Timestamp]) -> list[float]:
    return seasonal_naive_gasoleo(train_history, test_dates)


def evaluate_models(df_train: pd.DataFrame, df_test: pd.DataFrame):
    all_metrics = []
    all_preds = []

    for target in TARGETS:
        print(f"Evaluating {target}...")
        tr = df_train[df_train["Target"] == target].sort_values("Fecha")
        te = df_test[df_test["Target"] == target].sort_values("Fecha")
        y_true = te["Consumo_Tm"].values.astype(float)
        test_dates = pd.to_datetime(te["Fecha"]).tolist()

        try:
            res = train_sarima(tr["Consumo_Tm"].values)
            pred = predict_sarima(res, len(te))
            all_metrics.append({"Target": target, "Model": "SARIMA", **compute_metrics(y_true, pred)})
            for fd, actual, pv in zip(te["Fecha"], y_true, pred):
                all_preds.append({"Fecha": fd, "Target": target, "Actual": round(actual, 1), "Model": "SARIMA", "Pred": round(float(pv), 1)})
        except Exception as exc:
            print(f"  SARIMA failed for {target}: {exc}")

        for curve_type in ["Logistic", "Gompertz"]:
            try:
                curve = train_growth_curve(tr["Tendencia"].values, tr["Consumo_Tm"].values, tr["Mes"].values, curve_type)
                pred = predict_growth_curve(curve, te["Tendencia"].values, te["Mes"].values)
                all_metrics.append({"Target": target, "Model": curve_type, **compute_metrics(y_true, pred)})
                for fd, actual, pv in zip(te["Fecha"], y_true, pred):
                    all_preds.append({"Fecha": fd, "Target": target, "Actual": round(actual, 1), "Model": curve_type, "Pred": round(float(pv), 1)})
            except Exception as exc:
                print(f"  {curve_type} failed for {target}: {exc}")

        tr_ml = tr[["Fecha"] + ML_FEATS + ["Consumo_Tm"]].dropna()
        te_ml = te[["Fecha"] + ML_FEATS + ["Consumo_Tm"]].dropna()
        for model_name, label in [("Ridge", "Ridge"), ("RandomForest", "Random Forest"), ("XGBoost", "XGBoost")]:
            try:
                mdl, scaler = train_ml(tr_ml[ML_FEATS].values, tr_ml["Consumo_Tm"].values, model_name)
                pred = predict_ml(mdl, scaler, te_ml[ML_FEATS].values)
                all_metrics.append({"Target": target, "Model": label, **compute_metrics(te_ml["Consumo_Tm"].values, pred)})
                for fd, actual, pv in zip(te_ml["Fecha"], te_ml["Consumo_Tm"], pred):
                    all_preds.append({"Fecha": fd, "Target": target, "Actual": round(float(actual), 1), "Model": label, "Pred": round(float(pv), 1)})
            except Exception as exc:
                print(f"  {label} failed for {target}: {exc}")

        tr_share = tr[["Fecha"] + SHARE_FEATS + ["Biodiesel_GasoleoA_Ratio"]].dropna()
        te_share = te[["Fecha"] + SHARE_FEATS + ["Consumo_Tm"]].dropna()
        try:
            share_model, share_scaler = train_share_model(
                tr_share[SHARE_FEATS].values,
                tr_share["Biodiesel_GasoleoA_Ratio"].values,
            )
            ratio_pred = predict_share_ratio(share_model, share_scaler, te_share[SHARE_FEATS].values)
            gaso_hat = np.array(test_gasoleo_naive(tr, pd.to_datetime(te_share["Fecha"]).tolist()), dtype=float)
            pred = ratio_pred * gaso_hat
            all_metrics.append({"Target": target, "Model": "Diesel Share", **compute_metrics(te_share["Consumo_Tm"].values, pred)})
            for fd, actual, pv in zip(te_share["Fecha"], te_share["Consumo_Tm"], pred):
                all_preds.append({"Fecha": fd, "Target": target, "Actual": round(float(actual), 1), "Model": "Diesel Share", "Pred": round(float(pv), 1)})
        except Exception as exc:
            print(f"  Diesel Share failed for {target}: {exc}")

    return pd.DataFrame(all_metrics), pd.DataFrame(all_preds)


def walk_forward_scores(target_df: pd.DataFrame, min_origin: int = 15) -> dict[str, float]:
    df = target_df.sort_values("Fecha").reset_index(drop=True)
    fold_errors: dict[str, list[float]] = {col: [] for col in CANDIDATE_COLS}

    for origin in range(min_origin, len(df) - 1):
        fold_tr = df.iloc[: origin + 1].copy()
        fold_te = df.iloc[origin + 1 : origin + 2].copy()
        y_true = float(fold_te["Consumo_Tm"].iloc[0])
        if y_true <= 0:
            continue

        try:
            res = train_sarima(fold_tr["Consumo_Tm"].values)
            pred = float(predict_sarima(res, 1)[0])
            fold_errors["SARIMA"].append(abs((y_true - pred) / y_true) * 100)
        except Exception:
            pass

        for curve_type in ["Logistic", "Gompertz"]:
            try:
                curve = train_growth_curve(
                    fold_tr["Tendencia"].values,
                    fold_tr["Consumo_Tm"].values,
                    fold_tr["Mes"].values,
                    curve_type,
                )
                pred = float(predict_growth_curve(curve, fold_te["Tendencia"].values, fold_te["Mes"].values)[0])
                fold_errors[curve_type].append(abs((y_true - pred) / y_true) * 100)
            except Exception:
                pass

        tr_ml = fold_tr[ML_FEATS + ["Consumo_Tm"]].dropna()
        te_ml = fold_te[ML_FEATS + ["Consumo_Tm"]].dropna()
        if len(tr_ml) >= 5 and len(te_ml) == 1:
            for model_name, label in [("Ridge", "Ridge"), ("RandomForest", "Random Forest"), ("XGBoost", "XGBoost")]:
                try:
                    mdl, scaler = train_ml(tr_ml[ML_FEATS].values, tr_ml["Consumo_Tm"].values, model_name)
                    pred = float(predict_ml(mdl, scaler, te_ml[ML_FEATS].values)[0])
                    fold_errors[label].append(abs((y_true - pred) / y_true) * 100)
                except Exception:
                    pass

        tr_share = fold_tr[SHARE_FEATS + ["Biodiesel_GasoleoA_Ratio"]].dropna()
        te_share = fold_te[SHARE_FEATS + ["Consumo_Tm"]].dropna()
        if len(tr_share) >= 5 and len(te_share) == 1:
            try:
                share_model, share_scaler = train_share_model(
                    tr_share[SHARE_FEATS].values,
                    tr_share["Biodiesel_GasoleoA_Ratio"].values,
                )
                ratio = float(predict_share_ratio(share_model, share_scaler, te_share[SHARE_FEATS].values)[0])
                next_date = pd.to_datetime(fold_te["Fecha"].iloc[0])
                gaso_hat = seasonal_naive_gasoleo(fold_tr, [next_date])[0]
                pred = ratio * gaso_hat
                fold_errors["Diesel Share"].append(abs((y_true - pred) / y_true) * 100)
            except Exception:
                pass

    return {model: float(np.median(errors)) if errors else np.inf for model, errors in fold_errors.items()}


def run_walk_forward(df_train: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for target in TARGETS:
        scores = walk_forward_scores(df_train[df_train["Target"] == target])
        rows.append({"Target": target, **scores})
    df_wf = pd.DataFrame(rows)
    df_wf["Selected_Model"] = df_wf[CANDIDATE_COLS].idxmin(axis=1)
    return df_wf


def final_forecasts(df_all: pd.DataFrame) -> pd.DataFrame:
    rows = []
    forecast_labels = [d.strftime("%Y-%m") for d in FORECAST_DATES]
    for target in TARGETS:
        full = df_all[df_all["Target"] == target].sort_values("Fecha").copy()
        macro_last = full.iloc[-1][["IPI_original", "IPC_var_anual", "Tasa_paro"]].to_dict()

        try:
            res = train_sarima(full["Consumo_Tm"].values)
            for fecha, val in zip(forecast_labels, predict_sarima(res, len(forecast_labels))):
                rows.append({"Fecha": fecha, "Target": target, "Model": "SARIMA", "Forecast": round(float(val), 1)})
        except Exception as exc:
            print(f"Forecast SARIMA failed for {target}: {exc}")

        future_t = np.arange(int(full["Tendencia"].max()) + 1, int(full["Tendencia"].max()) + 1 + len(forecast_labels))
        future_mes = np.array([d.month for d in FORECAST_DATES])
        for curve_type in ["Logistic", "Gompertz"]:
            try:
                curve = train_growth_curve(full["Tendencia"].values, full["Consumo_Tm"].values, full["Mes"].values, curve_type)
                for fecha, val in zip(forecast_labels, predict_growth_curve(curve, future_t, future_mes)):
                    rows.append({"Fecha": fecha, "Target": target, "Model": curve_type, "Forecast": round(float(val), 1)})
            except Exception as exc:
                print(f"Forecast {curve_type} failed for {target}: {exc}")

        tr_ml = full[ML_FEATS + ["Consumo_Tm"]].dropna()
        for model_name, label in [("Ridge", "Ridge"), ("RandomForest", "Random Forest"), ("XGBoost", "XGBoost")]:
            try:
                mdl, scaler = train_ml(tr_ml[ML_FEATS].values, tr_ml["Consumo_Tm"].values, model_name)
                for fecha, val in zip(forecast_labels, recursive_forecast_ml(mdl, scaler, full, macro_last, len(forecast_labels))):
                    rows.append({"Fecha": fecha, "Target": target, "Model": label, "Forecast": round(float(val), 1)})
            except Exception as exc:
                print(f"Forecast {label} failed for {target}: {exc}")

        tr_share = full[SHARE_FEATS + ["Biodiesel_GasoleoA_Ratio"]].dropna()
        try:
            share_model, share_scaler = train_share_model(
                tr_share[SHARE_FEATS].values,
                tr_share["Biodiesel_GasoleoA_Ratio"].values,
            )
            for fecha, val in zip(forecast_labels, recursive_forecast_share(share_model, share_scaler, full, macro_last, len(forecast_labels))):
                rows.append({"Fecha": fecha, "Target": target, "Model": "Diesel Share", "Forecast": round(float(val), 1)})
        except Exception as exc:
            print(f"Forecast Diesel Share failed for {target}: {exc}")

    return pd.DataFrame(rows)


def build_final_metrics(df_metrics: pd.DataFrame, df_wf: pd.DataFrame) -> pd.DataFrame:
    selected = dict(zip(df_wf["Target"], df_wf["Selected_Model"]))
    rows = []
    for target, model in selected.items():
        row = df_metrics[(df_metrics["Target"] == target) & (df_metrics["Model"] == model)]
        if row.empty:
            raise ValueError(f"No 2025 metric for selected {target} / {model}")
        rows.append(row.iloc[0].to_dict())
    return pd.DataFrame(rows)[["Target", "Model", "MAE", "RMSE", "MAPE", "R2"]]


def build_comparison_metrics(df_metrics: pd.DataFrame) -> pd.DataFrame:
    """Combine current CNMC metrics with optional price-ablation metrics."""
    frames = [df_metrics.copy()]
    price_path = DATA_OUTPUTS / "metricas_modelos_con_precios.csv"
    if price_path.exists():
        price_metrics = pd.read_csv(price_path)
        if "R2" not in price_metrics.columns:
            price_metrics["R2"] = np.nan
        frames.append(price_metrics[["Target", "Model", "MAE", "RMSE", "MAPE", "R2"]])

    comparison = pd.concat(frames, ignore_index=True)
    comparison = comparison.drop_duplicates(["Target", "Model"], keep="last")
    return comparison.sort_values(["Target", "MAPE", "Model"]).reset_index(drop=True)


def build_tableau_outputs(df_all: pd.DataFrame, df_preds: pd.DataFrame, df_fc: pd.DataFrame, df_final: pd.DataFrame, df_metrics: pd.DataFrame) -> None:
    selected = dict(zip(df_final["Target"], df_final["Model"]))
    actual_rows = df_all[["Fecha", "Target", "Consumo_Tm"]].copy()
    actual_rows["Model"] = "Actual"
    actual_rows["Type"] = "Actual"
    actual_rows["Valor"] = actual_rows["Consumo_Tm"]
    actual_rows = actual_rows.drop(columns=["Consumo_Tm"])

    pred_rows = df_preds.copy()
    pred_rows["Type"] = "Test Prediction"
    pred_rows["Valor"] = pred_rows["Pred"]
    pred_rows = pred_rows[["Fecha", "Target", "Model", "Type", "Valor"]]

    forecast_rows = df_fc.copy()
    forecast_rows["Type"] = "Forecast"
    forecast_rows["Valor"] = forecast_rows["Forecast"]
    forecast_rows = forecast_rows[["Fecha", "Target", "Model", "Type", "Valor"]]

    tableau = pd.concat([actual_rows, pred_rows, forecast_rows], ignore_index=True)
    tableau["Fecha_Date"] = pd.to_datetime(tableau["Fecha"])
    tableau["Anyo"] = tableau["Fecha_Date"].dt.year
    tableau["Mes"] = tableau["Fecha_Date"].dt.month
    tableau["Trimestre"] = tableau["Fecha_Date"].dt.quarter
    tableau["Selected_Model"] = tableau["Target"].map(selected).fillna("")
    tableau["Is_Selected_Model"] = tableau.apply(
        lambda r: r["Model"] == r["Selected_Model"] or r["Model"] == "Actual",
        axis=1,
    )
    tableau = tableau[
        [
            "Fecha_Date",
            "Fecha",
            "Anyo",
            "Mes",
            "Trimestre",
            "Target",
            "Model",
            "Type",
            "Valor",
            "Selected_Model",
            "Is_Selected_Model",
        ]
    ]
    tableau.to_csv(DATA_OUTPUTS / "tableau_dashboard.csv", index=False, encoding="utf-8")

    metrics = df_metrics.copy()
    metrics["Rank"] = metrics.groupby("Target")["MAPE"].rank(method="first")
    metrics["Selected_Model"] = metrics["Target"].map(selected)
    metrics["Mejor_Modelo"] = metrics["Model"] == metrics["Selected_Model"]
    metrics["MAPE_Label"] = metrics["MAPE"].map(lambda x: f"{x:.1f}%")
    metrics.to_csv(DATA_OUTPUTS / "tableau_metricas.csv", index=False, encoding="utf-8")

    selected_fc = pd.concat(
        [df_fc[(df_fc["Target"] == target) & (df_fc["Model"] == model)] for target, model in selected.items()],
        ignore_index=True,
    )
    pivot = selected_fc.pivot(index="Fecha", columns="Target", values="Forecast").reset_index()
    pivot["Fecha_Date"] = pd.to_datetime(pivot["Fecha"])
    pivot["Anyo"] = pivot["Fecha_Date"].dt.year
    pivot["Mes"] = pivot["Fecha_Date"].dt.month
    pivot["Trimestre"] = pivot["Fecha_Date"].dt.quarter
    front = ["Fecha_Date", "Fecha", "Anyo", "Mes", "Trimestre"]
    target_cols = [c for c in TARGETS if c in pivot.columns]
    pivot = pivot[front + target_cols]
    pivot.to_csv(DATA_OUTPUTS / "tableau_forecast_pivot.csv", index=False, encoding="utf-8")

    legacy = pd.concat(
        [
            actual_rows[actual_rows["Target"].isin(TARGETS)],
            selected_fc.assign(Type="Forecast", Valor=selected_fc["Forecast"])[["Fecha", "Target", "Model", "Type", "Valor"]],
        ],
        ignore_index=True,
    )
    legacy.to_csv(DATA_OUTPUTS / "tableau_export_legacy.csv", index=False, encoding="utf-8")


def plot_outputs(df_all: pd.DataFrame, df_metrics: pd.DataFrame, df_preds: pd.DataFrame, df_fc: pd.DataFrame, df_final: pd.DataFrame) -> None:
    selected = dict(zip(df_final["Target"], df_final["Model"]))

    plot_metrics = df_metrics[~df_metrics["Model"].isin(["Ridge", "Diesel Share"])].copy()
    fig, axes = plt.subplots(1, 2, figsize=(18, 6))
    for ax, metric in zip(axes, ["MAPE", "MAE"]):
        pivot = plot_metrics.pivot(index="Target", columns="Model", values=metric).reindex(TARGETS)
        pivot.plot(kind="bar", ax=ax, width=0.82)
        ax.set_title(f"{metric} by model and target - Test set 2025")
        ax.set_ylabel(f"{metric} {'(%)' if metric == 'MAPE' else '(Tm)'}")
        ax.grid(True, axis="y", alpha=0.3)
        ax.legend(fontsize=8)
    fig.suptitle(
        "Model Performance Comparison - with CNMC Diesel-Market and Mandate Features\n"
        "Extreme failed candidates Ridge and Diesel Share retained in CSV metrics, omitted from this chart",
        fontweight="bold",
    )
    plt.tight_layout()
    plt.savefig(FIGURES / "07_model_comparison.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    axes = axes.flatten()
    for i, target in enumerate(TARGETS):
        ax = axes[i]
        actual = df_all[df_all["Target"] == target].copy()
        actual["Fecha_dt"] = pd.to_datetime(actual["Fecha"])
        sel = selected[target]
        pred = df_preds[(df_preds["Target"] == target) & (df_preds["Model"] == sel)].copy()
        pred["Fecha_dt"] = pd.to_datetime(pred["Fecha"])
        fc = df_fc[(df_fc["Target"] == target) & (df_fc["Model"] == sel)].copy()
        fc["Fecha_dt"] = pd.to_datetime(fc["Fecha"])

        ax.plot(actual["Fecha_dt"], actual["Consumo_Tm"], color="black", marker="o", linewidth=2, label="Historical actual")
        if not pred.empty:
            ax.plot(pred["Fecha_dt"], pred["Pred"], color=TARGET_COLORS[target], linestyle="--", linewidth=2, label=f"2025 prediction ({sel})")
        ax.plot(fc["Fecha_dt"], fc["Forecast"], color=TARGET_COLORS[target], linewidth=2.5, label=f"Forecast ({sel})")
        ax.axvline(pd.to_datetime("2026-01-01"), color="gray", linestyle=":", linewidth=1.5)
        ax.fill_between(fc["Fecha_dt"], fc["Forecast"] * 0.8, fc["Forecast"] * 1.2, color=TARGET_COLORS[target], alpha=0.12, label="±20% band")
        ax.set_title(f"{target} - selected: {sel}", color=TARGET_COLORS[target], fontweight="bold")
        ax.set_ylabel("Consumo (Tm)")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7)
    axes[-1].set_visible(False)
    fig.suptitle("Selected 24-Month Biodiesel Demand Forecast (2026-2027)", fontweight="bold")
    plt.tight_layout()
    plt.savefig(FIGURES / "11_forecast_24m.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    df_all = pd.read_csv(DATA_FEATURES / "features_modelo_completo.csv")
    df_train = pd.read_csv(DATA_FEATURES / "features_train.csv")
    df_test = pd.read_csv(DATA_FEATURES / "features_test.csv")

    missing = [col for col in ML_FEATS + SHARE_FEATS if col not in df_all.columns]
    if missing:
        raise ValueError(f"Missing required feature columns: {missing}")
    if (df_all["Fecha"] >= "2026-01").any():
        raise ValueError("features_modelo_completo contains 2026 rows; original forecast origin must stay 2025-12")

    df_metrics, df_preds = evaluate_models(df_train, df_test)
    df_wf = run_walk_forward(df_train)
    df_final = build_final_metrics(df_metrics, df_wf)
    df_fc = final_forecasts(df_all)
    df_comparison = build_comparison_metrics(df_metrics)

    df_metrics.to_csv(DATA_OUTPUTS / "metricas_modelos.csv", index=False, encoding="utf-8")
    df_wf.to_csv(DATA_OUTPUTS / "model_selection_walkforward.csv", index=False, encoding="utf-8")
    df_final.to_csv(DATA_OUTPUTS / "metricas_final_seleccionado.csv", index=False, encoding="utf-8")
    df_preds.to_csv(DATA_OUTPUTS / "predicciones_test_2025.csv", index=False, encoding="utf-8")
    df_fc.to_csv(DATA_OUTPUTS / "forecast_24m_sarima_rf_xgb.csv", index=False, encoding="utf-8")
    df_comparison.to_csv(DATA_OUTPUTS / "metricas_comparativa.csv", index=False, encoding="utf-8")

    build_tableau_outputs(df_all, df_preds, df_fc, df_final, df_metrics)
    plot_outputs(df_all, df_metrics, df_preds, df_fc, df_final)

    print("\nWalk-forward selected models:")
    print(df_wf[["Target", "Selected_Model"]].to_string(index=False))
    print("\nFinal selected test metrics:")
    print(df_final.to_string(index=False))

    selected = dict(zip(df_final["Target"], df_final["Model"]))
    selected_fc = pd.concat(
        [df_fc[(df_fc["Target"] == target) & (df_fc["Model"] == model)] for target, model in selected.items()],
        ignore_index=True,
    )
    selected_fc["year"] = selected_fc["Fecha"].str[:4].astype(int)
    annual = selected_fc.groupby(["Target", "year"])["Forecast"].sum().unstack()
    print("\nSelected forecast annual totals:")
    print(annual.to_string())


if __name__ == "__main__":
    main()
