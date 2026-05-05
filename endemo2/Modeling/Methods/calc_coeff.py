import numpy as np
import math
from scipy.optimize import curve_fit
from itertools import combinations_with_replacement
from sklearn.linear_model import LinearRegression

"""
This Script contains all the different mathematical ways to compute the coefficiants.
"""


def _format_to_sigfigs(num, sigfigs=6):
    return float(f"{float(num):.{sigfigs}g}")


def _as_2d_array(X):
    arr = np.asarray(X, dtype=float)
    if arr.ndim == 1:
        if arr.size == 0:
            return arr.reshape(0, 0)
        return arr.reshape(-1, 1)
    return arr


def _as_1d_array(y):
    arr = np.asarray(y, dtype=float).reshape(-1)
    return arr


def _validate_xy(X, y):
    if X.shape[0] != y.shape[0]:
        raise ValueError("Number of samples in X and y must match.")
    if X.shape[0] == 0:
        raise ValueError("No samples available for coefficient fit.")


def calc_coef_const_last(X : list, y: list):
    if not y:
        raise ValueError("Data cannot be empty.")

    k0 = y[-1]
    equation = "y = k0"
    return [k0], equation


def calc_coef_const_mean(X : list, y: list):
    if not y:
        raise ValueError("y cannot be empty.")
    k0 = np.mean(y)
    equation = "y = k0(t_hist_mean)"
    return [k0], equation


def calc_coef_mult_k0_zero(X : list, y: list):
    if not y:
        raise ValueError("Data cannot be empty.")

    k0 = 0
    k1 = y[-1] / math.prod(X[-1])
    equation = "y = 0 + k1*x1*x2..."
    return [k0, k1], equation


def calc_coef_lin_multivariable_sklearn(X: list, y: list):
    X = _as_2d_array(X)
    y = _as_1d_array(y)
    _validate_xy(X, y)

    model = LinearRegression()
    model.fit(X, y)
    intercept = _format_to_sigfigs(float(model.intercept_))
    coefficients = [_format_to_sigfigs(coef) for coef in model.coef_]
    equation = "y = k0 + k1*x1+k2*x2+..."
    result = [intercept] + coefficients
    return result, equation


def calc_coef_exp_multivariable(X: np.ndarray, y: np.ndarray):
    X = _as_2d_array(X)
    y = _as_1d_array(y)
    _validate_xy(X, y)

    def exponential_model(X_flat, k0, kn, *coeffs):
        X_reshaped = X_flat.reshape(-1, len(coeffs))
        linear_combination = np.dot(X_reshaped, coeffs)
        return k0 + kn * np.exp(linear_combination)

    n_features = X.shape[1]
    initial_guess = [1.0] * (2 + n_features)
    popt, _ = curve_fit(exponential_model, X.flatten(), y, p0=initial_guess, maxfev=20000)
    equation = "y = k0 + kn * exp(k1 * X1 + k2 * X2 + ... + kn-1 * Xn-1)"
    return popt.tolist(), equation


def calc_coef_quadratic_multivariable(X : list, y: list):
    X = _as_2d_array(X)
    y = _as_1d_array(y)
    X_quad = np.hstack([X ** 2, X, np.ones((X.shape[0], 1))])
    coeffs, _, _, _ = np.linalg.lstsq(X_quad, y, rcond=None)
    return coeffs


def calc_coef_polynom_multivariable(X : list, y: list, degree: int):
    X = _as_2d_array(X)
    y = _as_1d_array(y)

    n_features = X.shape[1]
    terms = []
    for d in range(1, degree + 1):
        terms.extend(combinations_with_replacement(range(n_features), d))

    X_poly = np.ones((X.shape[0], len(terms) + 1))
    for i, term in enumerate(terms):
        X_poly[:, i] = np.prod(X[:, term], axis=1)

    coeffs, _, _, _ = np.linalg.lstsq(X_poly, y, rcond=None)
    return coeffs


def calc_coef_log_multivariable(X: list, y: list):
    X = np.array(X).T
    y = np.array(y)
    X_log = np.log(X)
    model = LinearRegression()
    model.fit(X_log, y)
    coefficients = model.coef_
    intercept = model.intercept_
    terms = [f"{coeff:.7f}*log(x{i + 1})" for i, coeff in enumerate(coefficients)]
    equation = " + ".join(terms)
    equation += f" + {intercept:.7f}"
    result = [intercept] + coefficients.tolist()
    print(result)
    return f"y = {equation}", result


def calc_coef_log_sum(X: list, y: list):
    X = _as_2d_array(X)
    y = _as_1d_array(y)
    _validate_xy(X, y)
    if np.any(X <= 0):
        raise ValueError("LOG_SUM requires strictly positive input values.")

    X_log = np.log(X)
    model = LinearRegression()
    model.fit(X_log, y)
    intercept = _format_to_sigfigs(float(model.intercept_))
    coefficients = [_format_to_sigfigs(coef) for coef in model.coef_]
    equation = "y = k0 + " + " + ".join(f"k{i}*log(x{i})" for i in range(1, len(coefficients) + 1))
    return [intercept] + coefficients, equation


def calc_coef_exp_sum(X: list, y: list):
    X = _as_2d_array(X)
    y = _as_1d_array(y)
    _validate_xy(X, y)
    n_features = X.shape[1]

    def model(X_flat, k0, *params):
        X_reshaped = X_flat.reshape(-1, n_features)
        result = np.full(X_reshaped.shape[0], k0, dtype=float)
        for idx in range(n_features):
            amplitude = params[2 * idx]
            exponent_factor = params[2 * idx + 1]
            result += amplitude * np.exp(exponent_factor * X_reshaped[:, idx])
        return result

    baseline = float(np.nanmedian(y)) if y.size else 0.0
    span = float(np.nanmax(y) - np.nanmin(y)) if y.size else 1.0
    if not np.isfinite(span) or span == 0:
        span = 1.0
    initial = [baseline]
    for _ in range(n_features):
        initial.extend([span / max(1, n_features), 0.01])

    popt, _ = curve_fit(model, X.flatten(), y, p0=initial, maxfev=50000)
    coeffs = [_format_to_sigfigs(v) for v in popt]
    equation = "y = k0 + " + " + ".join(
        f"k{2*i-1}*exp(k{2*i}*x{i})" for i in range(1, n_features + 1)
    )
    return coeffs, equation


def calc_coef_power_sum(X: list, y: list):
    X = _as_2d_array(X)
    y = _as_1d_array(y)
    _validate_xy(X, y)
    if np.any(X <= 0):
        raise ValueError("POWER_SUM requires strictly positive input values.")
    n_features = X.shape[1]

    def model(X_flat, k0, *params):
        X_reshaped = X_flat.reshape(-1, n_features)
        result = np.full(X_reshaped.shape[0], k0, dtype=float)
        for idx in range(n_features):
            amplitude = params[2 * idx]
            exponent = params[2 * idx + 1]
            result += amplitude * np.power(X_reshaped[:, idx], exponent)
        return result

    baseline = float(np.nanmedian(y)) if y.size else 0.0
    span = float(np.nanmax(y) - np.nanmin(y)) if y.size else 1.0
    if not np.isfinite(span) or span == 0:
        span = 1.0
    initial = [baseline]
    for _ in range(n_features):
        initial.extend([span / max(1, n_features), 1.0])

    popt, _ = curve_fit(model, X.flatten(), y, p0=initial, maxfev=50000)
    coeffs = [_format_to_sigfigs(v) for v in popt]
    equation = "y = k0 + " + " + ".join(
        f"k{2*i-1}*x{i}^k{2*i}" for i in range(1, n_features + 1)
    )
    return coeffs, equation


def calc_coef_base_exp_sum(X: list, y: list):
    X = _as_2d_array(X)
    y = _as_1d_array(y)
    _validate_xy(X, y)
    n_features = X.shape[1]

    # Historical fit is canonicalized to base e because a^(x*b) = exp((ln(a)*b) * x)
    # and a,b are not separately identifiable from historical data.
    def model(X_flat, k0, *slopes):
        X_reshaped = X_flat.reshape(-1, n_features)
        result = np.full(X_reshaped.shape[0], k0, dtype=float)
        for idx in range(n_features):
            result += np.exp(slopes[idx] * X_reshaped[:, idx])
        return result

    baseline = float(np.nanmedian(y)) if y.size else 0.0
    initial = [baseline] + [0.01] * n_features
    popt, _ = curve_fit(model, X.flatten(), y, p0=initial, maxfev=50000)

    coeffs = [_format_to_sigfigs(popt[0])]
    for slope in popt[1:]:
        coeffs.extend([_format_to_sigfigs(math.e), _format_to_sigfigs(slope)])
    equation = "y = k0 + " + " + ".join(
        f"e^(x{i}*k{2*i})" for i in range(1, n_features + 1)
    )
    return coeffs, equation


def calc_coef_lin_share(X, y):
    X = np.array(X).T
    y = np.array(y)

    DDr2 = X[1]
    var_share_hist = y / DDr2
    DDr1 = np.array(X[0])[:, np.newaxis]

    coef_lin, equation = calc_coef_lin_multivariable_sklearn(DDr1, var_share_hist)
    coef = [0] + coef_lin
    return coef, equation
