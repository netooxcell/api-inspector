"""
Ensemble de los 4 modelos (logistic, random_forest, gradient_boosting,
poisson), con pesos determinados por optimización sobre las predicciones
walk-forward (fuera de muestra) del backtest — nunca asignados a mano.

Se minimiza el log loss multiclase de la combinación convexa:
    P_ensemble = sum_m  w_m * P_m         sujeto a  w_m >= 0,  sum(w_m) = 1

usando SLSQP (scipy.optimize.minimize). Esto es exactamente lo que pide el
enunciado: "los pesos deben determinarse usando datos históricos y
validación", no una elección arbitraria.
"""
import numpy as np
from scipy.optimize import minimize
from sklearn.metrics import log_loss

CLASS_ORDER = ["A", "D", "H"]


def _model_proba_matrix(df, model_name):
    return df[[f"{model_name}_{c}" for c in CLASS_ORDER]].to_numpy()


def fit_ensemble_weights(backtest_df, model_names):
    y_true = backtest_df["result"].to_numpy()
    proba_by_model = {m: _model_proba_matrix(backtest_df, m) for m in model_names}

    def neg_log_loss_for_weights(weights):
        weights = np.clip(weights, 0, None)
        weights = weights / weights.sum()
        combined = sum(w * proba_by_model[m] for w, m in zip(weights, model_names))
        combined = combined / combined.sum(axis=1, keepdims=True)
        return log_loss(y_true, combined, labels=CLASS_ORDER)

    n = len(model_names)
    x0 = np.ones(n) / n
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    bounds = [(0.0, 1.0)] * n

    result = minimize(
        neg_log_loss_for_weights, x0, method="SLSQP",
        bounds=bounds, constraints=constraints,
        options={"maxiter": 200, "ftol": 1e-9},
    )
    weights = np.clip(result.x, 0, None)
    weights = weights / weights.sum()
    return dict(zip(model_names, weights)), result.fun


def combine_probabilities(model_probs, weights):
    """
    model_probs: dict {model_name: np.array shape (n, 3)} in CLASS_ORDER.
    weights: dict {model_name: weight}.
    """
    combined = None
    for m, w in weights.items():
        contrib = w * model_probs[m]
        combined = contrib if combined is None else combined + contrib
    combined = combined / combined.sum(axis=1, keepdims=True)
    return combined
