"""
Train, validate, and forecast biodiesel demand with CNMC diesel-market and
biofuel mandate features.

Outputs are written to data/outputs and reports/figures, preserving the existing
CSV filenames used by the notebooks/Tableau flow.

Headline model selection is a 7-family open competition for each target:
SARIMA, SARIMAX, Logistic, Gompertz, Ridge, Random Forest, and XGBoost. The
winner is selected only by recursive multi-step walk-forward validation inside
the 2023-2024 training window. The 2025 period is used only to report holdout
metrics for the already-selected model.

Diesel Share and pooled regional ML remain diagnostic/sensitivity candidates in
the metrics tables, but they are not headline-eligible.
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

HEADLINE_CANDIDATE_COLS = [
    "SARIMA",
    "SARIMAX",
    "Logistic",
    "Gompertz",
    "Ridge",
    "Random Forest",
    "XGBoost",
]
DIAGNOSTIC_CANDIDATE_COLS = [
    "Diesel Share",
]
CANDIDATE_COLS = HEADLINE_CANDIDATE_COLS + DIAGNOSTIC_CANDIDATE_COLS

REGIONAL_TARGETS = [target for target in TARGETS if target != "Nacional"]
MULTISTEP_MIN_ORIGIN = 12
MULTISTEP_MAX_HORIZON = 12
FORECAST_DEGENERACY_ATOL = 0.05
FORECAST_MIN_RANGE_FLOOR = 1.0
FORECAST_MIN_RANGE_RATIO = 0.005

# A converged SARIMA/SARIMAX fit on this project's log1p(Consumo_Tm) scale has
# sigma2 well above 0.1 in every healthy case observed (0.3-2.0). A fit with
# sigma2 below this floor has not learned a generalizable residual process --
# it has driven the in-sample error toward zero by spending almost all of its
# degrees of freedom on parameters, which is the signature of a model with too
# many regressors for too few training rows (SARIMAX's 9 exogenous features
# plus ARMA/seasonal terms against ~22-34 rows is exactly this regime for 4 of
# the 5 targets). Reject any such fit rather than let it compete on equal
# footing with a genuinely identified model.
SARIMA_SIGMA2_FLOOR = 1e-3

BASELINE_MODEL_COLS = ["SARIMA", "Logistic", "Gompertz"]
DIRECT_FEATURE_MODEL_COLS = ["SARIMAX", "Ridge", "Random Forest", "XGBoost"]

REGION_CODE_COLS = {target: f"Region_{idx}" for idx, target in enumerate(REGIONAL_TARGETS)}
POOLED_ML_BASE_FEATS = [
    "Tendencia",
    "Mes",
    "sin_mes",
    "cos_mes",
    "log_Lag_1",
    "log_Lag_2",
    "log_Lag_3",
    "log_Roll_mean_3",
    "log_Roll_mean_6",
    "IPI_original_lag1",
    "IPC_var_anual_lag1",
    "Tasa_paro_lag1",
    "log_GasoleoA_Tm_lag1",
    "log_GasoleoA_Tm_roll3_lag1",
    "Biodiesel_GasoleoA_Ratio_lag1",
    "Biodiesel_GasoleoA_Ratio_roll3_lag1",
    *MANDATE_FEATS,
]
POOLED_ML_FEATS = POOLED_ML_BASE_FEATS + list(REGION_CODE_COLS.values())
POOLED_MODELS = [
    ("Pooled Ridge", "Ridge"),
    ("Pooled Random Forest", "RandomForest"),
    ("Pooled XGBoost", "XGBoost"),
]
POOLED_LABELS = [label for label, _ in POOLED_MODELS]
ALL_MODEL_COLS = CANDIDATE_COLS + POOLED_LABELS
DIAGNOSTIC_ONLY_MODEL_COLS = DIAGNOSTIC_CANDIDATE_COLS + POOLED_LABELS

SARIMAX_EXOG_FEATS = [
    "sin_mes",
    "cos_mes",
    "IPI_original_lag1",
    "IPC_var_anual_lag1",
    "Tasa_paro_lag1",
    "GasoleoA_Tm_lag1",
    "GasoleoA_Tm_roll3_lag1",
    *MANDATE_FEATS,
]

DEFAULT_SARIMA_ORDER = (1, 1, 1)
DEFAULT_SARIMA_SEASONAL_ORDER = (1, 0, 0, 12)
SARIMA_GRID = [
    ((1, 1, 1), (1, 0, 0, 12)),
    ((0, 1, 1), (1, 0, 0, 12)),
    ((1, 1, 0), (1, 0, 0, 12)),
    ((2, 1, 1), (1, 0, 0, 12)),
    ((1, 1, 2), (1, 0, 0, 12)),
    ((0, 1, 2), (1, 0, 0, 12)),
    ((2, 1, 0), (1, 0, 0, 12)),
    ((1, 0, 1), (1, 0, 0, 12)),
    ((1, 1, 1), (0, 0, 0, 12)),
    ((0, 1, 1), (0, 0, 0, 12)),
    ((1, 1, 0), (0, 0, 0, 12)),
    ((1, 1, 1), (0, 1, 0, 12)),
    ((0, 1, 1), (0, 1, 0, 12)),
    ((1, 1, 0), (0, 1, 0, 12)),
    ((1, 1, 1), (1, 0, 1, 12)),
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


def repeating_cycle_period(values: np.ndarray, max_period: int = 12) -> int | None:
    values = np.asarray(values, dtype=float)
    if len(values) < 2:
        return 1
    for period in range(1, min(max_period, len(values) - 1) + 1):
        if np.allclose(values[period:], values[:-period], atol=FORECAST_DEGENERACY_ATOL, rtol=0):
            return period
    return None


def forecast_degeneracy_reason(values: np.ndarray) -> str:
    values = np.asarray(values, dtype=float)
    if len(values) == 0 or not np.isfinite(values).all():
        return "non_finite_or_empty"
    mean_level = max(float(np.mean(np.abs(values))), 1.0)
    value_range = float(np.max(values) - np.min(values))
    min_range = max(FORECAST_MIN_RANGE_FLOOR, FORECAST_MIN_RANGE_RATIO * mean_level)
    if value_range <= min_range:
        return f"near_flat_range_{value_range:.4f}"
    period = repeating_cycle_period(values)
    if period is not None:
        return f"repeating_cycle_{period}"
    return ""


def fit_degeneracy_reason(result) -> str:
    """Detect a SARIMA/SARIMAX fit that has not actually identified a model.

    Checks the optimizer's own convergence flag and the fitted residual
    variance (sigma2, the model's last parameter). A fit that did not
    converge, or whose sigma2 has collapsed near zero, has spent its degrees
    of freedom memorizing training noise rather than learning a
    generalizable process -- the signature of too many parameters for too
    few rows. Such a fit must not be allowed to compete on equal footing
    with a genuinely identified one, regardless of how plausible its
    in-sample MAPE looks.
    """
    converged = bool(result.mle_retvals.get("converged", True)) if hasattr(result, "mle_retvals") else True
    if not converged:
        return "mle_did_not_converge"
    sigma2 = float(result.params[-1])
    if not np.isfinite(sigma2) or sigma2 < SARIMA_SIGMA2_FLOOR:
        return f"degenerate_sigma2_{sigma2:.3g}"
    return ""


def train_sarima(
    y_train: np.ndarray,
    order: tuple[int, int, int] = DEFAULT_SARIMA_ORDER,
    seasonal_order: tuple[int, int, int, int] = DEFAULT_SARIMA_SEASONAL_ORDER,
):
    model = SARIMAX(
        np.log1p(y_train),
        order=order,
        seasonal_order=seasonal_order,
        enforce_stationarity=False,
        enforce_invertibility=False,
    )
    result = model.fit(disp=False)
    reason = fit_degeneracy_reason(result)
    if reason:
        raise ValueError(f"degenerate SARIMA fit: {reason}")
    return result


def predict_sarima(result, n_steps: int) -> np.ndarray:
    return np.maximum(np.expm1(result.forecast(steps=n_steps)), 0)


def train_sarimax(
    train_df: pd.DataFrame,
    order: tuple[int, int, int] = DEFAULT_SARIMA_ORDER,
    seasonal_order: tuple[int, int, int, int] = DEFAULT_SARIMA_SEASONAL_ORDER,
):
    tr = train_df[SARIMAX_EXOG_FEATS + ["Consumo_Tm"]].dropna().copy()
    if len(tr) < len(SARIMAX_EXOG_FEATS) + 6:
        raise ValueError("Not enough non-null rows for SARIMAX training")
    scaler = StandardScaler()
    exog = scaler.fit_transform(tr[SARIMAX_EXOG_FEATS].values)
    model = SARIMAX(
        np.log1p(tr["Consumo_Tm"].values.astype(float)),
        exog=exog,
        order=order,
        seasonal_order=seasonal_order,
        enforce_stationarity=False,
        enforce_invertibility=False,
    )
    result = model.fit(disp=False)
    reason = fit_degeneracy_reason(result)
    if reason:
        raise ValueError(f"degenerate SARIMAX fit: {reason}")
    return result, scaler


def sarima_parameter_count(order: tuple[int, int, int], seasonal_order: tuple[int, int, int, int]) -> int:
    p, _, q = order
    seasonal_p, _, seasonal_q, _ = seasonal_order
    return int(p + q + seasonal_p + seasonal_q)


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


def train_ml(x_train: np.ndarray, y_train: np.ndarray, model_name: str, pooled: bool = False):
    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(x_train)
    y_log = np.log1p(y_train)
    if model_name == "Ridge":
        model = Ridge(alpha=10.0).fit(x_scaled, y_log)
    elif model_name == "RandomForest":
        max_depth = 6 if pooled else 3
        min_samples_leaf = 1 if pooled else 3
        model = RandomForestRegressor(
            n_estimators=300,
            max_depth=max_depth,
            min_samples_leaf=min_samples_leaf,
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


def build_sarimax_future_exog(history: pd.DataFrame, future_dates: list[pd.Timestamp]) -> pd.DataFrame:
    hist_gaso = history["GasoleoA_Tm"].astype(float).tolist()
    future_dates = list(future_dates)
    future_gaso = seasonal_naive_gasoleo(history, future_dates)
    macro_last = history.iloc[-1][["IPI_original", "IPC_var_anual", "Tasa_paro"]].to_dict()
    rows = []

    for dt, gaso_t in zip(future_dates, future_gaso):
        mes = int(dt.month)
        mandate = mandate_values_for_date(dt)
        rows.append(
            {
                "sin_mes": np.sin(2 * np.pi * mes / 12),
                "cos_mes": np.cos(2 * np.pi * mes / 12),
                "IPI_original_lag1": macro_last["IPI_original"],
                "IPC_var_anual_lag1": macro_last["IPC_var_anual"],
                "Tasa_paro_lag1": macro_last["Tasa_paro"],
                "GasoleoA_Tm_lag1": hist_gaso[-1],
                "GasoleoA_Tm_roll3_lag1": float(np.mean(hist_gaso[-3:])),
                **mandate,
            }
        )
        hist_gaso.append(gaso_t)

    return pd.DataFrame(rows)[SARIMAX_EXOG_FEATS]


def predict_sarimax(result, scaler, history: pd.DataFrame, future_dates: list[pd.Timestamp]) -> np.ndarray:
    exog = build_sarimax_future_exog(history, future_dates)
    exog_scaled = scaler.transform(exog.values)
    pred_log = result.forecast(steps=len(exog), exog=exog_scaled)
    return np.maximum(np.expm1(np.clip(pred_log, None, 15.0)), 0)


def recursive_forecast_ml(
    model,
    scaler,
    history: pd.DataFrame,
    macro_last: dict,
    n_steps: int = 24,
    future_dates: list[pd.Timestamp] | None = None,
) -> list[float]:
    hist_y = history["Consumo_Tm"].astype(float).tolist()
    hist_gaso = history["GasoleoA_Tm"].astype(float).tolist()
    hist_ratio = history["Biodiesel_GasoleoA_Ratio"].astype(float).tolist()
    if future_dates is None:
        future_dates = list(FORECAST_DATES[:n_steps])
    else:
        future_dates = list(future_dates)[:n_steps]
        n_steps = len(future_dates)
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


def recursive_forecast_share(
    model,
    scaler,
    history: pd.DataFrame,
    macro_last: dict,
    n_steps: int = 24,
    future_dates: list[pd.Timestamp] | None = None,
) -> list[float]:
    hist_gaso = history["GasoleoA_Tm"].astype(float).tolist()
    hist_ratio = history["Biodiesel_GasoleoA_Ratio"].astype(float).tolist()
    if future_dates is None:
        future_dates = list(FORECAST_DATES[:n_steps])
    else:
        future_dates = list(future_dates)[:n_steps]
        n_steps = len(future_dates)
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


def evaluate_models(
    df_train: pd.DataFrame,
    df_test: pd.DataFrame,
    sarima_orders: dict[str, tuple[tuple[int, int, int], tuple[int, int, int, int]]],
):
    all_metrics = []
    all_preds = []
    degenerate_log = []

    for target in TARGETS:
        print(f"Evaluating {target}...")
        tr = df_train[df_train["Target"] == target].sort_values("Fecha")
        te = df_test[df_test["Target"] == target].sort_values("Fecha")
        y_true = te["Consumo_Tm"].values.astype(float)
        test_dates = pd.to_datetime(te["Fecha"]).tolist()
        sarima_order, sarima_seasonal_order = sarima_orders.get(
            target,
            (DEFAULT_SARIMA_ORDER, DEFAULT_SARIMA_SEASONAL_ORDER),
        )

        try:
            res = train_sarima(tr["Consumo_Tm"].values, sarima_order, sarima_seasonal_order)
            pred = predict_sarima(res, len(te))
            all_metrics.append({"Target": target, "Model": "SARIMA", **compute_metrics(y_true, pred)})
            for fd, actual, pv in zip(te["Fecha"], y_true, pred):
                all_preds.append({"Fecha": fd, "Target": target, "Actual": round(actual, 1), "Model": "SARIMA", "Pred": round(float(pv), 1)})
        except Exception as exc:
            print(f"  SARIMA failed for {target}: {exc}")
            if "degenerate" in str(exc):
                degenerate_log.append({"Target": target, "Model": "SARIMA", "Stage": "2025_holdout_evaluation", "Reason": str(exc)})

        try:
            res_x, scaler_x = train_sarimax(tr, sarima_order, sarima_seasonal_order)
            pred = predict_sarimax(res_x, scaler_x, tr, test_dates)
            all_metrics.append({"Target": target, "Model": "SARIMAX", **compute_metrics(y_true, pred)})
            for fd, actual, pv in zip(te["Fecha"], y_true, pred):
                all_preds.append({"Fecha": fd, "Target": target, "Actual": round(actual, 1), "Model": "SARIMAX", "Pred": round(float(pv), 1)})
        except Exception as exc:
            print(f"  SARIMAX failed for {target}: {exc}")
            if "degenerate" in str(exc):
                degenerate_log.append({"Target": target, "Model": "SARIMAX", "Stage": "2025_holdout_evaluation", "Reason": str(exc)})

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
        for model_name, label in [("Ridge", "Ridge"), ("RandomForest", "Random Forest"), ("XGBoost", "XGBoost")]:
            try:
                mdl, scaler = train_ml(tr_ml[ML_FEATS].values, tr_ml["Consumo_Tm"].values, model_name)
                macro_last = tr.iloc[-1][["IPI_original", "IPC_var_anual", "Tasa_paro"]].to_dict()
                pred = recursive_forecast_ml(mdl, scaler, tr, macro_last, len(te), test_dates)
                all_metrics.append({"Target": target, "Model": label, **compute_metrics(y_true, pred)})
                for fd, actual, pv in zip(te["Fecha"], y_true, pred):
                    all_preds.append({"Fecha": fd, "Target": target, "Actual": round(float(actual), 1), "Model": label, "Pred": round(float(pv), 1)})
            except Exception as exc:
                print(f"  {label} failed for {target}: {exc}")

        tr_share = tr[["Fecha"] + SHARE_FEATS + ["Biodiesel_GasoleoA_Ratio"]].dropna()
        try:
            share_model, share_scaler = train_share_model(
                tr_share[SHARE_FEATS].values,
                tr_share["Biodiesel_GasoleoA_Ratio"].values,
            )
            macro_last = tr.iloc[-1][["IPI_original", "IPC_var_anual", "Tasa_paro"]].to_dict()
            pred = recursive_forecast_share(share_model, share_scaler, tr, macro_last, len(te), test_dates)
            all_metrics.append({"Target": target, "Model": "Diesel Share", **compute_metrics(y_true, pred)})
            for fd, actual, pv in zip(te["Fecha"], y_true, pred):
                all_preds.append({"Fecha": fd, "Target": target, "Actual": round(float(actual), 1), "Model": "Diesel Share", "Pred": round(float(pv), 1)})
        except Exception as exc:
            print(f"  Diesel Share failed for {target}: {exc}")

    return pd.DataFrame(all_metrics), pd.DataFrame(all_preds), pd.DataFrame(degenerate_log)


def _append_mape_errors(errors: list[float], y_true: np.ndarray, y_pred: np.ndarray) -> None:
    y_true = np.array(y_true, dtype=float)
    y_pred = np.maximum(np.array(y_pred, dtype=float), 0)
    mask = y_true > 0
    if mask.any():
        errors.extend((np.abs((y_true[mask] - y_pred[mask]) / y_true[mask]) * 100).tolist())


def sarima_walk_forward_score(
    target_df: pd.DataFrame,
    order: tuple[int, int, int],
    seasonal_order: tuple[int, int, int, int],
    min_origin: int = MULTISTEP_MIN_ORIGIN,
    max_horizon: int = MULTISTEP_MAX_HORIZON,
) -> tuple[float, int, int]:
    df = target_df.sort_values("Fecha").reset_index(drop=True)
    errors: list[float] = []
    successful_folds = 0

    for origin in range(min_origin, len(df) - 1):
        fold_tr = df.iloc[: origin + 1].copy()
        fold_te = df.iloc[origin + 1 : min(len(df), origin + 1 + max_horizon)].copy()
        y_true = fold_te["Consumo_Tm"].values.astype(float)
        if len(fold_te) == 0 or not (y_true > 0).any():
            continue
        try:
            res = train_sarima(fold_tr["Consumo_Tm"].values, order, seasonal_order)
            pred = predict_sarima(res, len(fold_te))
            before = len(errors)
            _append_mape_errors(errors, y_true, pred)
            if len(errors) > before:
                successful_folds += 1
        except Exception:
            continue

    return (
        float(np.median(errors)) if errors else np.inf,
        len(errors),
        successful_folds,
    )


def tune_sarima_orders(
    df_train: pd.DataFrame,
    df_all: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, tuple[tuple[int, int, int], tuple[int, int, int, int]]]]:
    rows = []
    selected_orders: dict[str, tuple[tuple[int, int, int], tuple[int, int, int, int]]] = {}

    for target in TARGETS:
        target_df = df_train[df_train["Target"] == target].sort_values("Fecha")
        full_df = df_all[df_all["Target"] == target].sort_values("Fecha")
        for order, seasonal_order in SARIMA_GRID:
            score, error_count, successful_folds = sarima_walk_forward_score(target_df, order, seasonal_order)

            # Two independent stability checks. The training-window check
            # matches the 2025 holdout evaluation; the full-history check
            # matches what scripts/05's final_forecasts() actually refits and
            # ships as the 2026-2027 forecast. An order can pass one and fail
            # the other -- both must be checked, since only the full-history
            # check sees the degeneracy that the production forecast itself
            # would have shipped with.
            train_reason = ""
            try:
                stability_fit = train_sarima(target_df["Consumo_Tm"].values, order, seasonal_order)
                stability_forecast = predict_sarima(stability_fit, 24)
                train_reason = forecast_degeneracy_reason(stability_forecast)
            except Exception as exc:
                train_reason = f"stability_check_failed_{exc}"

            full_history_reason = ""
            try:
                full_history_fit = train_sarima(full_df["Consumo_Tm"].values, order, seasonal_order)
                full_history_forecast = predict_sarima(full_history_fit, 24)
                full_history_reason = forecast_degeneracy_reason(full_history_forecast)
            except Exception as exc:
                full_history_reason = f"stability_check_failed_{exc}"

            p, d, q = order
            seasonal_p, seasonal_d, seasonal_q, m = seasonal_order
            rows.append(
                {
                    "Target": target,
                    "p": p,
                    "d": d,
                    "q": q,
                    "P": seasonal_p,
                    "D": seasonal_d,
                    "Q": seasonal_q,
                    "m": m,
                    "Parameter_Count": sarima_parameter_count(order, seasonal_order),
                    "WalkForward_MAPE": round(score, 3) if np.isfinite(score) else np.inf,
                    "Error_Count": error_count,
                    "Successful_Folds": successful_folds,
                    "Training_Origin_24m_Degenerate": bool(train_reason),
                    "Training_Origin_24m_Degeneracy_Reason": train_reason,
                    "FullHistory_Origin_24m_Degenerate": bool(full_history_reason),
                    "FullHistory_Origin_24m_Degeneracy_Reason": full_history_reason,
                    "Selected": False,
                }
            )

        target_rows = pd.DataFrame([row for row in rows if row["Target"] == target])
        finite = target_rows[np.isfinite(target_rows["WalkForward_MAPE"])].copy()
        stable = finite[
            ~finite["Training_Origin_24m_Degenerate"] & ~finite["FullHistory_Origin_24m_Degenerate"]
        ].copy()
        if not stable.empty:
            finite = stable
        if finite.empty:
            selected_order = DEFAULT_SARIMA_ORDER
            selected_seasonal_order = DEFAULT_SARIMA_SEASONAL_ORDER
        else:
            best = finite.sort_values(
                ["WalkForward_MAPE", "Parameter_Count", "p", "d", "q", "P", "D", "Q", "m"]
            ).iloc[0]
            selected_order = (int(best["p"]), int(best["d"]), int(best["q"]))
            selected_seasonal_order = (int(best["P"]), int(best["D"]), int(best["Q"]), int(best["m"]))
        selected_orders[target] = (selected_order, selected_seasonal_order)

    results = pd.DataFrame(rows)
    for target, (order, seasonal_order) in selected_orders.items():
        p, d, q = order
        seasonal_p, seasonal_d, seasonal_q, m = seasonal_order
        mask = (
            results["Target"].eq(target)
            & results["p"].eq(p)
            & results["d"].eq(d)
            & results["q"].eq(q)
            & results["P"].eq(seasonal_p)
            & results["D"].eq(seasonal_d)
            & results["Q"].eq(seasonal_q)
            & results["m"].eq(m)
        )
        results.loc[mask, "Selected"] = True
    return results, selected_orders


def build_sarima_order_selection(
    df_sarima_grid: pd.DataFrame,
    grid_orders: dict[str, tuple[tuple[int, int, int], tuple[int, int, int, int]]],
) -> tuple[pd.DataFrame, dict[str, tuple[tuple[int, int, int], tuple[int, int, int, int]]]]:
    rows = []
    production_orders: dict[str, tuple[tuple[int, int, int], tuple[int, int, int, int]]] = {}

    for target in TARGETS:
        grid_order, grid_seasonal_order = grid_orders.get(
            target,
            (DEFAULT_SARIMA_ORDER, DEFAULT_SARIMA_SEASONAL_ORDER),
        )
        grid_row = df_sarima_grid[
            df_sarima_grid["Target"].eq(target) & df_sarima_grid["Selected"]
        ].iloc[0]
        rejected_degenerate = int(
            df_sarima_grid[
                df_sarima_grid["Target"].eq(target)
                & (
                    df_sarima_grid["Training_Origin_24m_Degenerate"].astype(bool)
                    | df_sarima_grid["FullHistory_Origin_24m_Degenerate"].astype(bool)
                )
            ].shape[0]
        )
        production_order = grid_order
        production_seasonal_order = grid_seasonal_order
        decision = "selected_by_training_walk_forward_grid"

        production_orders[target] = (production_order, production_seasonal_order)
        p, d, q = grid_order
        seasonal_p, seasonal_d, seasonal_q, m = grid_seasonal_order
        prod_p, prod_d, prod_q = production_order
        prod_p_seasonal, prod_d_seasonal, prod_q_seasonal, prod_m = production_seasonal_order
        rows.append(
            {
                "Target": target,
                "Default_Order": str(DEFAULT_SARIMA_ORDER),
                "Default_Seasonal_Order": str(DEFAULT_SARIMA_SEASONAL_ORDER),
                "Grid_Selected_Order": str(grid_order),
                "Grid_Selected_Seasonal_Order": str(grid_seasonal_order),
                "Grid_WalkForward_MAPE": float(grid_row["WalkForward_MAPE"]),
                "Grid_Training_Origin_24m_Degenerate": bool(grid_row["Training_Origin_24m_Degenerate"]),
                "Grid_Training_Origin_24m_Degeneracy_Reason": grid_row[
                    "Training_Origin_24m_Degeneracy_Reason"
                ],
                "Grid_FullHistory_Origin_24m_Degenerate": bool(grid_row["FullHistory_Origin_24m_Degenerate"]),
                "Grid_FullHistory_Origin_24m_Degeneracy_Reason": grid_row[
                    "FullHistory_Origin_24m_Degeneracy_Reason"
                ],
                "Degenerate_Orders_Rejected": rejected_degenerate,
                "Production_Order": str(production_order),
                "Production_Seasonal_Order": str(production_seasonal_order),
                "Production_p": prod_p,
                "Production_d": prod_d,
                "Production_q": prod_q,
                "Production_P": prod_p_seasonal,
                "Production_D": prod_d_seasonal,
                "Production_Q": prod_q_seasonal,
                "Production_m": prod_m,
                "Selected_By_Training_WalkForward": True,
                "Decision": decision,
                "Grid_p": p,
                "Grid_d": d,
                "Grid_q": q,
                "Grid_P": seasonal_p,
                "Grid_D": seasonal_d,
                "Grid_Q": seasonal_q,
                "Grid_m": m,
            }
        )

    return pd.DataFrame(rows), production_orders


def selection_candidates_for_target(target: str) -> list[str]:
    return HEADLINE_CANDIDATE_COLS


def walk_forward_scores(
    target_df: pd.DataFrame,
    sarima_order: tuple[int, int, int],
    sarima_seasonal_order: tuple[int, int, int, int],
    min_origin: int = MULTISTEP_MIN_ORIGIN,
    max_horizon: int = MULTISTEP_MAX_HORIZON,
) -> dict[str, float]:
    df = target_df.sort_values("Fecha").reset_index(drop=True)
    fold_errors: dict[str, list[float]] = {col: [] for col in CANDIDATE_COLS}

    for origin in range(min_origin, len(df) - 1):
        fold_tr = df.iloc[: origin + 1].copy()
        fold_te = df.iloc[origin + 1 : min(len(df), origin + 1 + max_horizon)].copy()
        y_true = fold_te["Consumo_Tm"].values.astype(float)
        if len(fold_te) == 0 or not (y_true > 0).any():
            continue
        future_dates = pd.to_datetime(fold_te["Fecha"]).tolist()

        try:
            res = train_sarima(fold_tr["Consumo_Tm"].values, sarima_order, sarima_seasonal_order)
            pred = predict_sarima(res, len(fold_te))
            _append_mape_errors(fold_errors["SARIMA"], y_true, pred)
        except Exception:
            pass

        try:
            res_x, scaler_x = train_sarimax(fold_tr, sarima_order, sarima_seasonal_order)
            pred = predict_sarimax(res_x, scaler_x, fold_tr, future_dates)
            _append_mape_errors(fold_errors["SARIMAX"], y_true, pred)
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
                pred = predict_growth_curve(curve, fold_te["Tendencia"].values, fold_te["Mes"].values)
                _append_mape_errors(fold_errors[curve_type], y_true, pred)
            except Exception:
                pass

        tr_ml = fold_tr[ML_FEATS + ["Consumo_Tm"]].dropna()
        if len(tr_ml) >= 5:
            for model_name, label in [("Ridge", "Ridge"), ("RandomForest", "Random Forest"), ("XGBoost", "XGBoost")]:
                try:
                    mdl, scaler = train_ml(tr_ml[ML_FEATS].values, tr_ml["Consumo_Tm"].values, model_name)
                    macro_last = fold_tr.iloc[-1][["IPI_original", "IPC_var_anual", "Tasa_paro"]].to_dict()
                    pred = recursive_forecast_ml(mdl, scaler, fold_tr, macro_last, len(fold_te), future_dates)
                    _append_mape_errors(fold_errors[label], y_true, pred)
                except Exception:
                    pass

        tr_share = fold_tr[SHARE_FEATS + ["Biodiesel_GasoleoA_Ratio"]].dropna()
        if len(tr_share) >= 5:
            try:
                share_model, share_scaler = train_share_model(
                    tr_share[SHARE_FEATS].values,
                    tr_share["Biodiesel_GasoleoA_Ratio"].values,
                )
                macro_last = fold_tr.iloc[-1][["IPI_original", "IPC_var_anual", "Tasa_paro"]].to_dict()
                pred = recursive_forecast_share(share_model, share_scaler, fold_tr, macro_last, len(fold_te), future_dates)
                _append_mape_errors(fold_errors["Diesel Share"], y_true, pred)
            except Exception:
                pass

    return {model: float(np.median(errors)) if errors else np.inf for model, errors in fold_errors.items()}


def pooled_walk_forward_scores(
    df_train: pd.DataFrame,
    min_origin: int = MULTISTEP_MIN_ORIGIN,
    max_horizon: int = MULTISTEP_MAX_HORIZON,
) -> dict[str, dict[str, float]]:
    fold_errors = {target: {label: [] for label in POOLED_LABELS} for target in REGIONAL_TARGETS}
    target_lengths = [
        len(df_train[df_train["Target"] == target].sort_values("Fecha"))
        for target in REGIONAL_TARGETS
    ]
    if not target_lengths:
        return {target: {label: np.inf for label in POOLED_LABELS} for target in REGIONAL_TARGETS}
    panel_length = min(target_lengths)

    for origin in range(min_origin, panel_length - 1):
        pooled_train_parts = []
        fold_paths = {}
        for target in REGIONAL_TARGETS:
            target_df = df_train[df_train["Target"] == target].sort_values("Fecha").reset_index(drop=True)
            fold_tr = target_df.iloc[: origin + 1].copy()
            fold_te = target_df.iloc[origin + 1 : min(len(target_df), origin + 1 + max_horizon)].copy()
            pooled_train_parts.append(fold_tr)
            fold_paths[target] = (fold_tr, fold_te)

        pooled_train = pd.concat(pooled_train_parts, ignore_index=True)
        for label, model_name in POOLED_MODELS:
            try:
                model, scaler = train_pooled_ml(pooled_train, model_name)
            except Exception:
                continue

            for target, (fold_tr, fold_te) in fold_paths.items():
                if fold_te.empty:
                    continue
                y_true = fold_te["Consumo_Tm"].values.astype(float)
                macro_last = fold_tr.iloc[-1][["IPI_original", "IPC_var_anual", "Tasa_paro"]].to_dict()
                future_dates = pd.to_datetime(fold_te["Fecha"]).tolist()
                try:
                    pred = recursive_forecast_pooled_ml(model, scaler, fold_tr, target, macro_last, future_dates)
                    _append_mape_errors(fold_errors[target][label], y_true, pred)
                except Exception:
                    pass

    return {
        target: {
            label: float(np.median(errors)) if errors else np.inf
            for label, errors in model_errors.items()
        }
        for target, model_errors in fold_errors.items()
    }


def run_walk_forward(
    df_train: pd.DataFrame,
    sarima_orders: dict[str, tuple[tuple[int, int, int], tuple[int, int, int, int]]],
) -> pd.DataFrame:
    pooled_scores = pooled_walk_forward_scores(df_train)
    rows = []
    for target in TARGETS:
        sarima_order, sarima_seasonal_order = sarima_orders.get(
            target,
            (DEFAULT_SARIMA_ORDER, DEFAULT_SARIMA_SEASONAL_ORDER),
        )
        scores = walk_forward_scores(
            df_train[df_train["Target"] == target],
            sarima_order,
            sarima_seasonal_order,
        )
        for label in POOLED_LABELS:
            scores[label] = pooled_scores.get(target, {}).get(label, np.inf)
        allowed = selection_candidates_for_target(target)
        proposed = min(allowed, key=lambda model: scores.get(model, np.inf))
        rows.append(
            {
                "Target": target,
                "Validation_Gate": f"recursive_{MULTISTEP_MAX_HORIZON}m_walk_forward",
                "Selection_Candidate_Set": "seven_independent_target_models",
                "Eligible_Final_Models": ", ".join(allowed),
                **scores,
                "Proposed_Model": proposed,
            }
        )
    df_wf = pd.DataFrame(rows)
    return df_wf


def add_pooled_ml_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ["Lag_1", "Lag_2", "Lag_3", "Roll_mean_3", "Roll_mean_6", "GasoleoA_Tm_lag1", "GasoleoA_Tm_roll3_lag1"]:
        out[f"log_{col}"] = np.log1p(out[col].clip(lower=0))
    for target, code_col in REGION_CODE_COLS.items():
        out[code_col] = (out["Target"] == target).astype(float)
    return out


def train_pooled_ml(df_train: pd.DataFrame, model_name: str):
    train_aug = add_pooled_ml_features(df_train[df_train["Target"].isin(REGIONAL_TARGETS)])
    train_aug = train_aug[POOLED_ML_FEATS + ["Consumo_Tm"]].dropna()
    if len(train_aug) < 20:
        raise ValueError("Not enough rows for pooled regional ML training")
    return train_ml(train_aug[POOLED_ML_FEATS].values, train_aug["Consumo_Tm"].values, model_name, pooled=True)


def recursive_forecast_pooled_ml(
    model,
    scaler,
    history: pd.DataFrame,
    target: str,
    macro_last: dict,
    future_dates: list[pd.Timestamp],
) -> list[float]:
    hist_y = history["Consumo_Tm"].astype(float).tolist()
    hist_gaso = history["GasoleoA_Tm"].astype(float).tolist()
    hist_ratio = history["Biodiesel_GasoleoA_Ratio"].astype(float).tolist()
    future_dates = list(future_dates)
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
            "log_Lag_1": np.log1p(max(hist_y[-1], 0.0)),
            "log_Lag_2": np.log1p(max(hist_y[-2], 0.0)),
            "log_Lag_3": np.log1p(max(hist_y[-3], 0.0)),
            "log_Roll_mean_3": np.log1p(max(float(np.mean(hist_y[-3:])), 0.0)),
            "log_Roll_mean_6": np.log1p(max(float(np.mean(hist_y[-6:])), 0.0)),
            "IPI_original_lag1": macro_last["IPI_original"],
            "IPC_var_anual_lag1": macro_last["IPC_var_anual"],
            "Tasa_paro_lag1": macro_last["Tasa_paro"],
            "log_GasoleoA_Tm_lag1": np.log1p(max(hist_gaso[-1], 0.0)),
            "log_GasoleoA_Tm_roll3_lag1": np.log1p(max(float(np.mean(hist_gaso[-3:])), 0.0)),
            "Biodiesel_GasoleoA_Ratio_lag1": hist_ratio[-1],
            "Biodiesel_GasoleoA_Ratio_roll3_lag1": float(np.mean(hist_ratio[-3:])),
            **mandate,
        }
        for region_target, code_col in REGION_CODE_COLS.items():
            feat_values[code_col] = 1.0 if region_target == target else 0.0
        row = np.array([[feat_values[f] for f in POOLED_ML_FEATS]])
        pred = float(predict_ml(model, scaler, row)[0])
        pred = max(pred, 0.0)
        forecasts.append(pred)
        hist_y.append(pred)
        hist_gaso.append(gaso_t)
        hist_ratio.append(pred / gaso_t if gaso_t > 0 else 0.0)
    return forecasts


def evaluate_pooled_ml_experiment(df_train: pd.DataFrame, df_test: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    pred_rows = []
    for label, model_name in POOLED_MODELS:
        try:
            model, scaler = train_pooled_ml(df_train, model_name)
        except Exception as exc:
            for target in REGIONAL_TARGETS:
                rows.append({"Target": target, "Model": label, "MAE": np.nan, "RMSE": np.nan, "MAPE": np.inf, "R2": np.nan, "Status": f"failed: {exc}"})
            continue

        for target in REGIONAL_TARGETS:
            tr = df_train[df_train["Target"] == target].sort_values("Fecha")
            te = df_test[df_test["Target"] == target].sort_values("Fecha")
            macro_last = tr.iloc[-1][["IPI_original", "IPC_var_anual", "Tasa_paro"]].to_dict()
            future_dates = pd.to_datetime(te["Fecha"]).tolist()
            pred = recursive_forecast_pooled_ml(model, scaler, tr, target, macro_last, future_dates)
            metrics = compute_metrics(te["Consumo_Tm"].values, pred)
            rows.append({"Target": target, "Model": label, **metrics, "Status": "tested"})
            for fd, actual, pv in zip(te["Fecha"], te["Consumo_Tm"], pred):
                pred_rows.append({"Fecha": fd, "Target": target, "Actual": round(float(actual), 1), "Model": label, "Pred": round(float(pv), 1)})
    return pd.DataFrame(rows), pd.DataFrame(pred_rows)


def build_model_acceptance(df_wf: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, wf_row in df_wf.iterrows():
        target = wf_row["Target"]
        selected = wf_row["Proposed_Model"]
        eligible = selection_candidates_for_target(target)
        selected_training_metric = float(wf_row.get(selected, np.inf))
        if selected not in eligible or not np.isfinite(selected_training_metric):
            raise ValueError(f"No finite training walk-forward selection for {target}: {selected}")

        rows.append(
            {
                "Target": target,
                "Final_Eligibility_Rule": "all_seven_independent_target_models_are_eligible",
                "Eligible_Final_Models": ", ".join(eligible),
                "Selected_Model": selected,
                "Selected_Model_Training_WalkForward_MAPE": selected_training_metric,
                "Final_Selection_Source": "training_only_recursive_walk_forward",
                "Decision": "selected_by_training_only_walk_forward",
            }
        )
    return pd.DataFrame(rows)


def build_pooling_decision(df_final: pd.DataFrame, df_pooled: pd.DataFrame) -> pd.DataFrame:
    regional_final = df_final[df_final["Target"].isin(REGIONAL_TARGETS)][["Target", "Model", "MAPE"]].rename(
        columns={"Model": "Production_Model", "MAPE": "Production_MAPE"}
    )
    best_pooled = (
        df_pooled[df_pooled["Status"] == "tested"]
        .sort_values(["Target", "MAPE", "Model"])
        .groupby("Target", as_index=False)
        .first()[["Target", "Model", "MAPE"]]
        .rename(columns={"Model": "Best_Pooled_Model", "MAPE": "Best_Pooled_MAPE"})
    )
    decision = regional_final.merge(best_pooled, on="Target", how="left")
    decision["Best_Pooled_Beats_Production"] = decision["Best_Pooled_MAPE"] < decision["Production_MAPE"]
    decision["Production_Uses_Pooled_ML"] = decision["Production_Model"].isin(POOLED_LABELS)
    decision["Final_Selection_Allows_Pooled_ML"] = False
    decision["Decision"] = np.select(
        [
            decision["Best_Pooled_Beats_Production"],
        ],
        [
            "diagnostic_only_pooled_model_not_headline_eligible",
        ],
        default="diagnostic_only_no_pooled_validation_improvement",
    )
    return decision


def final_forecasts(
    df_all: pd.DataFrame,
    sarima_orders: dict[str, tuple[tuple[int, int, int], tuple[int, int, int, int]]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    degenerate_log = []
    forecast_labels = [d.strftime("%Y-%m") for d in FORECAST_DATES]
    for target in TARGETS:
        full = df_all[df_all["Target"] == target].sort_values("Fecha").copy()
        macro_last = full.iloc[-1][["IPI_original", "IPC_var_anual", "Tasa_paro"]].to_dict()
        sarima_order, sarima_seasonal_order = sarima_orders.get(
            target,
            (DEFAULT_SARIMA_ORDER, DEFAULT_SARIMA_SEASONAL_ORDER),
        )

        try:
            res = train_sarima(full["Consumo_Tm"].values, sarima_order, sarima_seasonal_order)
            for fecha, val in zip(forecast_labels, predict_sarima(res, len(forecast_labels))):
                rows.append({"Fecha": fecha, "Target": target, "Model": "SARIMA", "Forecast": round(float(val), 1)})
        except Exception as exc:
            print(f"Forecast SARIMA failed for {target}: {exc}")
            if "degenerate" in str(exc):
                degenerate_log.append({"Target": target, "Model": "SARIMA", "Stage": "production_24m_forecast", "Reason": str(exc)})

        try:
            res_x, scaler_x = train_sarimax(full, sarima_order, sarima_seasonal_order)
            for fecha, val in zip(forecast_labels, predict_sarimax(res_x, scaler_x, full, list(FORECAST_DATES))):
                rows.append({"Fecha": fecha, "Target": target, "Model": "SARIMAX", "Forecast": round(float(val), 1)})
        except Exception as exc:
            print(f"Forecast SARIMAX failed for {target}: {exc}")
            if "degenerate" in str(exc):
                degenerate_log.append({"Target": target, "Model": "SARIMAX", "Stage": "production_24m_forecast", "Reason": str(exc)})

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

    for label, model_name in POOLED_MODELS:
        try:
            model, scaler = train_pooled_ml(df_all, model_name)
        except Exception as exc:
            print(f"Forecast {label} failed during pooled training: {exc}")
            continue

        for target in REGIONAL_TARGETS:
            full = df_all[df_all["Target"] == target].sort_values("Fecha").copy()
            macro_last = full.iloc[-1][["IPI_original", "IPC_var_anual", "Tasa_paro"]].to_dict()
            try:
                forecast = recursive_forecast_pooled_ml(model, scaler, full, target, macro_last, list(FORECAST_DATES))
                for fecha, val in zip(forecast_labels, forecast):
                    rows.append({"Fecha": fecha, "Target": target, "Model": label, "Forecast": round(float(val), 1)})
            except Exception as exc:
                print(f"Forecast {label} failed for {target}: {exc}")

    return pd.DataFrame(rows), pd.DataFrame(degenerate_log)


def build_final_metrics(df_metrics: pd.DataFrame, df_wf: pd.DataFrame) -> pd.DataFrame:
    selected = dict(zip(df_wf["Target"], df_wf["Selected_Model"]))
    rows = []
    for target, model in selected.items():
        row = df_metrics[(df_metrics["Target"] == target) & (df_metrics["Model"] == model)]
        if row.empty:
            raise ValueError(f"No 2025 metric for selected {target} / {model}")
        rows.append(row.iloc[0].to_dict())
    return pd.DataFrame(rows)[["Target", "Model", "MAE", "RMSE", "MAPE", "R2"]]


def build_selected_forecast(df_fc: pd.DataFrame, df_final: pd.DataFrame) -> pd.DataFrame:
    selected = dict(zip(df_final["Target"], df_final["Model"]))
    frames = [
        df_fc[(df_fc["Target"] == target) & (df_fc["Model"] == model)].copy()
        for target, model in selected.items()
    ]
    out = pd.concat(frames, ignore_index=True)
    expected_rows = len(TARGETS) * len(FORECAST_DATES)
    if len(out) != expected_rows:
        raise ValueError(f"Selected forecast should have {expected_rows} rows, got {len(out)}")
    return out.sort_values(["Target", "Fecha"]).reset_index(drop=True)


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
    selected_error = df_final.set_index("Target")[["MAPE", "RMSE"]].to_dict("index")

    plot_metrics = df_metrics[~df_metrics["Model"].isin(["Ridge", "Pooled Ridge", "Diesel Share"])].copy()
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
        err = selected_error.get(target, {"MAPE": 20.0, "RMSE": 0.0})
        pct_width = fc["Forecast"] * (float(err["MAPE"]) / 100.0)
        abs_width = pd.Series(float(err["RMSE"]), index=fc.index)
        band_width = np.maximum(pct_width.values, abs_width.values)
        ax.fill_between(
            fc["Fecha_dt"],
            np.maximum(fc["Forecast"].values - band_width, 0),
            fc["Forecast"].values + band_width,
            color=TARGET_COLORS[target],
            alpha=0.12,
            label="2025 error band",
        )
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

    required_features = sorted(set(ML_FEATS + SHARE_FEATS + SARIMAX_EXOG_FEATS + POOLED_ML_BASE_FEATS))
    missing = [col for col in required_features if col not in df_all.columns and not col.startswith("log_")]
    if missing:
        raise ValueError(f"Missing required feature columns: {missing}")
    if (df_all["Fecha"] >= "2026-01").any():
        raise ValueError("features_modelo_completo contains 2026 rows; original forecast origin must stay 2025-12")

    df_sarima_grid, grid_sarima_orders = tune_sarima_orders(df_train, df_all)
    df_sarima_acceptance, sarima_orders = build_sarima_order_selection(df_sarima_grid, grid_sarima_orders)
    df_wf = run_walk_forward(df_train, sarima_orders)
    df_acceptance = build_model_acceptance(df_wf)
    df_wf = df_wf.merge(
        df_acceptance[
            [
                "Target",
                "Selected_Model",
                "Selected_Model_Training_WalkForward_MAPE",
                "Decision",
            ]
        ],
        on="Target",
        how="left",
    )

    df_test = pd.read_csv(DATA_FEATURES / "features_test.csv")
    df_individual_metrics, df_individual_preds, df_degenerate_eval = evaluate_models(df_train, df_test, sarima_orders)
    df_pooled, df_pooled_preds = evaluate_pooled_ml_experiment(df_train, df_test)
    df_metrics = pd.concat([df_individual_metrics, df_pooled.drop(columns=["Status"])], ignore_index=True)
    df_preds = pd.concat([df_individual_preds, df_pooled_preds], ignore_index=True)
    df_final = build_final_metrics(df_metrics, df_wf)
    df_pooling_decision = build_pooling_decision(df_final, df_pooled)
    df_fc, df_degenerate_fc = final_forecasts(df_all, sarima_orders)
    df_selected_fc = build_selected_forecast(df_fc, df_final)
    df_comparison = build_comparison_metrics(df_metrics)
    df_degenerate = pd.concat([df_degenerate_eval, df_degenerate_fc], ignore_index=True)

    selected_degenerate = df_degenerate[df_degenerate["Stage"] == "2025_holdout_evaluation"].merge(
        df_final[["Target", "Model"]], on=["Target", "Model"], how="inner"
    )
    if not selected_degenerate.empty:
        raise ValueError(
            "Final selected model is flagged as a degenerate fit, this should "
            f"never happen: {selected_degenerate.to_dict('records')}"
        )

    df_metrics.to_csv(DATA_OUTPUTS / "metricas_modelos.csv", index=False, encoding="utf-8")
    df_metrics.to_csv(DATA_OUTPUTS / "metricas_models.csv", index=False, encoding="utf-8")
    df_sarima_grid.to_csv(DATA_OUTPUTS / "sarima_grid_search_results.csv", index=False, encoding="utf-8")
    df_sarima_acceptance.to_csv(DATA_OUTPUTS / "sarima_order_acceptance.csv", index=False, encoding="utf-8")
    df_wf.to_csv(DATA_OUTPUTS / "model_selection_walkforward.csv", index=False, encoding="utf-8")
    df_final.to_csv(DATA_OUTPUTS / "metricas_final_seleccionado.csv", index=False, encoding="utf-8")
    df_final.to_csv(DATA_OUTPUTS / "metricas_final_selected.csv", index=False, encoding="utf-8")
    df_pooled.to_csv(DATA_OUTPUTS / "phase2_pooling_experiment_metrics.csv", index=False, encoding="utf-8")
    df_pooling_decision.to_csv(DATA_OUTPUTS / "phase2_pooling_decision.csv", index=False, encoding="utf-8")
    df_acceptance.to_csv(DATA_OUTPUTS / "phase2_model_acceptance.csv", index=False, encoding="utf-8")
    df_preds.to_csv(DATA_OUTPUTS / "predicciones_test_2025.csv", index=False, encoding="utf-8")
    df_fc.to_csv(DATA_OUTPUTS / "forecast_24m_sarima_rf_xgb.csv", index=False, encoding="utf-8")
    df_selected_fc.to_csv(DATA_OUTPUTS / "forecast_24m_selected.csv", index=False, encoding="utf-8")
    df_comparison.to_csv(DATA_OUTPUTS / "metricas_comparativa.csv", index=False, encoding="utf-8")
    df_degenerate.to_csv(DATA_OUTPUTS / "degenerate_fits.csv", index=False, encoding="utf-8")

    build_tableau_outputs(df_all, df_preds, df_fc, df_final, df_metrics)
    plot_outputs(df_all, df_metrics, df_preds, df_fc, df_final)

    print("\nTraining-only multi-step walk-forward selections:")
    print(df_wf[["Target", "Selection_Candidate_Set", "Proposed_Model", "Selected_Model", "Decision"]].to_string(index=False))
    print("\nSelected SARIMA orders from training-only grid search:")
    print(
        df_sarima_grid[df_sarima_grid["Selected"]][
            ["Target", "p", "d", "q", "P", "D", "Q", "m", "WalkForward_MAPE", "Successful_Folds"]
        ].to_string(index=False)
    )
    print("\nProduction SARIMA orders selected by training-only grid:")
    print(
        df_sarima_acceptance[
            [
                "Target",
                "Grid_Selected_Order",
                "Grid_Selected_Seasonal_Order",
                "Production_Order",
                "Production_Seasonal_Order",
                "Decision",
            ]
        ].to_string(index=False)
    )
    print("\nFinal selected 2025 validation metrics:")
    print(df_final.to_string(index=False))
    print("\nPooled regional ML decision:")
    print(df_pooling_decision.to_string(index=False))
    print("\nDegenerate fits excluded (sigma2 collapse or non-convergence, never eligible to be selected):")
    print(df_degenerate.to_string(index=False) if not df_degenerate.empty else "  none")

    df_selected_fc["year"] = df_selected_fc["Fecha"].str[:4].astype(int)
    annual = df_selected_fc.groupby(["Target", "year"])["Forecast"].sum().unstack()
    print("\nSelected forecast annual totals:")
    print(annual.to_string())


if __name__ == "__main__":
    main()
