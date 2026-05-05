import numpy as np
import math
import ast
import operator as _op
from typing import Any, Dict
from scipy.spatial import distance
# Allowed names for user_function (used by safe_eval_expr)
ALLOWED_USER_FUNCTIONS = {
    "min": min,
    "max": max,
    "abs": abs,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "pow": pow,
    "floor": math.floor,
    "ceil": math.ceil,
}

ALLOWED_USER_FUNCTION_NAMES = list(ALLOWED_USER_FUNCTIONS.keys())

"""
This module contains the different functions for the forecast
"""

# -----------------------------------------------------------------------------
# User-defined function support (ForecastMethod.USER_FUNCTION)
# -----------------------------------------------------------------------------

ALLOWED_BINOPS = {
    ast.Add: _op.add,
    ast.Sub: _op.sub,
    ast.Mult: _op.mul,
    ast.Div: _op.truediv,
    ast.Pow: _op.pow,
    ast.Mod: _op.mod,
}
_ALLOWED_UNARYOPS = {
    ast.UAdd: _op.pos,
    ast.USub: _op.neg,
}
_ALLOWED_FUNCS: Dict[str, Any] = ALLOWED_USER_FUNCTIONS


def _normalize_equation(expr: Any) -> str:
    s = "" if expr is None else str(expr).strip()
    if not s:
        return ""
    if "=" in s:
        left, right = s.split("=", 1)
        if left.strip().lower() == "y":
            s = right.strip()
    return s.replace("^", "**")


def safe_eval_expr(expr: str, context: Dict[str, float]) -> float:
    def _eval(node):
        if isinstance(node, ast.Constant):  # py>=3.8
            if isinstance(node.value, (int, float)):
                return float(node.value)
            raise ValueError("Only numeric constants are allowed in user_function.")
        if isinstance(node, ast.Num):  # pragma: no cover (older py)
            return float(node.n)
        if isinstance(node, ast.Name):
            if node.id not in context:
                raise ValueError(f"Unknown name '{node.id}' in user_function.")
            return float(context[node.id])
        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in ALLOWED_BINOPS:
                raise ValueError(f"Operator '{op_type.__name__}' not allowed in user_function.")
            left = _eval(node.left)
            right = _eval(node.right)
            return float(ALLOWED_BINOPS[op_type](left, right))
        if isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in _ALLOWED_UNARYOPS:
                raise ValueError(f"Unary operator '{op_type.__name__}' not allowed in user_function.")
            return float(_ALLOWED_UNARYOPS[op_type](_eval(node.operand)))
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("Only direct function calls are allowed in user_function.")
            fn_name = node.func.id
            fn = _ALLOWED_FUNCS.get(fn_name)
            if fn is None:
                raise ValueError(f"Function '{fn_name}' not allowed in user_function.")
            if node.keywords:
                raise ValueError("Keyword arguments are not allowed in user_function.")
            args = [_eval(a) for a in node.args]
            return float(fn(*args))
        raise ValueError(f"Expression element '{type(node).__name__}' not allowed in user_function.")

    tree = ast.parse(expr, mode="eval")
    return float(_eval(tree.body))


def calc_user_function(coef, x_values: list) -> float:
    """
    Evaluate a user-provided equation (stored in coef.equation) with a restricted AST.

    Available names inside the equation:
      - TIME (if TIME is part of demand_drivers_names)
      - DDr1..DDrN (dependencies exactly in configured order, including TIME if configured)
      - dependency names directly (e.g. GDP, POP, ...)
      - k0..kN (missing coefficients default to 0.0)
    """
    expr = _normalize_equation(getattr(coef, "equation", None))
    if not expr:
        raise ValueError("user_function selected but Equation is empty.")

    names = list(getattr(coef, "demand_drivers_names", []) or [])
    context: Dict[str, float] = {}

    for dep_idx, (name, raw_val) in enumerate(zip(names, x_values), start=1):
        try:
            val = float(raw_val)
        except Exception:
            val = float("nan")
        context[f"DDr{dep_idx}"] = val
        name_str = str(name)
        context[name_str] = val
        if name_str == "TIME":
            context["TIME"] = val

    coeffs = list(getattr(coef, "coefficients", []) or [])
    for i, v in enumerate(coeffs):
        context[f"k{i}"] = float(v) if v is not None else 0.0
    # Ensure at least k0..k4 exist for convenience (default 0.0)
    for i in range(5):
        context.setdefault(f"k{i}", 0.0)

    return safe_eval_expr(expr, context)


def calc_constant(coef, x_values) -> float:
    """
    Predict using the last constant value method.

    :return: The last known value (constant prediction).
    """
    if coef is None:
        raise ValueError("Constant prediction cannot be performed. Offset (constant value) is not set.")
    return coef.coefficients[0]

def calc_constant_mean(coef, x_values) -> float:
    """
    Predict using the constant mean value method.

    :return: The mean value (constant mean prediction).
    """
    if coef.coefficients is None:
        raise ValueError("Mean prediction cannot be performed. Offset (constant value) is not set.")
    return coef.coefficients[0]

def calc_lin(coef, x_values: list) -> float:
    """
    Perform prediction using the provided coefficients and independent variables.

    :param x_values: List of independent variable values.
    :return: Predicted value.
    """
    x_values = [float(x) for x in x_values]

    coefficients_x = coef.coefficients[1:]  # Exclude the intercept (`k0`)
    offset = coef.coefficients[0]  # Retrieve the intercept (`k0`)

    if len(coefficients_x) != len(x_values):
        raise ValueError("Mismatch between the number of coefficients and independent variables.")

    return offset + sum(c * x for c, x in zip(coefficients_x, x_values))


def calc_log_sum(coef, x_values: list) -> float:
    x_values = [float(x) for x in x_values]
    coefficients_x = coef.coefficients[1:]
    offset = coef.coefficients[0]

    if len(coefficients_x) != len(x_values):
        raise ValueError("Mismatch between the number of coefficients and independent variables.")
    if any(x <= 0 for x in x_values):
        raise ValueError("LOG_SUM requires strictly positive input values.")

    return offset + sum(c * math.log(x) for c, x in zip(coefficients_x, x_values))


def calc_exp_sum(coef, x_values: list) -> float:
    x_values = [float(x) for x in x_values]
    expected_len = 1 + 2 * len(x_values)
    if len(coef.coefficients) != expected_len:
        raise ValueError(f"EXP_SUM requires exactly {expected_len} coefficients.")

    result = float(coef.coefficients[0])
    for idx, x in enumerate(x_values):
        amplitude = float(coef.coefficients[1 + 2 * idx])
        exponent_factor = float(coef.coefficients[2 + 2 * idx])
        result += amplitude * math.exp(exponent_factor * x)
    return result


def calc_power_sum(coef, x_values: list) -> float:
    x_values = [float(x) for x in x_values]
    expected_len = 1 + 2 * len(x_values)
    if len(coef.coefficients) != expected_len:
        raise ValueError(f"POWER_SUM requires exactly {expected_len} coefficients.")
    if any(x <= 0 for x in x_values):
        raise ValueError("POWER_SUM requires strictly positive input values.")

    result = float(coef.coefficients[0])
    for idx, x in enumerate(x_values):
        amplitude = float(coef.coefficients[1 + 2 * idx])
        exponent = float(coef.coefficients[2 + 2 * idx])
        result += amplitude * (x ** exponent)
    return result


def calc_base_exp_sum(coef, x_values: list) -> float:
    x_values = [float(x) for x in x_values]
    expected_len = 1 + 2 * len(x_values)
    if len(coef.coefficients) != expected_len:
        raise ValueError(f"BASE_EXP_SUM requires exactly {expected_len} coefficients.")

    result = float(coef.coefficients[0])
    for idx, x in enumerate(x_values):
        base = float(coef.coefficients[1 + 2 * idx])
        exponent_factor = float(coef.coefficients[2 + 2 * idx])
        if base <= 0:
            raise ValueError("BASE_EXP_SUM requires strictly positive bases.")
        result += math.exp(math.log(base) * (x * exponent_factor))
    return result

def calc_lin_interpolation(points, point_x):
    point_x = point_x[0]

    # No support points -> undefined interpolation value.
    if not points:
        return np.nan

    # Outside the provided interpolation range, keep value undefined.
    # This avoids auto-filling gaps before/after user-provided points.
    if point_x < points[0][0] or point_x > points[-1][0]:
        return np.nan

    # Exact boundary points keep their explicit values.
    if point_x == points[0][0]:
        return points[0][1]
    if point_x == points[-1][0]:
        return points[-1][1]

    # Find the two points between which point_x lies.
    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]

        if x0 <= point_x <= x1:
            # Linear interpolation formula
            t = (point_x - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)

    return np.nan

def calc_exp (coef, x_values: list) -> float:
    """
    Perform calculation based on the formula: k0 + k1 * ((1 + k2 / 100) ^ (X1 - k3))

    :param coef: Coefficient object containing the coefficients [k0, k1, k2, k3].
    :param x_values: List of independent variable values [X1].
    :return: Calculated result.
    """
    if len(x_values) != 1:
        raise ValueError("DDr must contain exactly one element for the calc_exp function")

    X1 = float(x_values[0])  # Ensure all inputs are floats
    if len(coef.coefficients) != 4:
        raise ValueError("EXP requires exactly four coefficients: k0, k1, k2, k3.")
    k0, k1, k2, k3 = coef.coefficients

    growth_factor = (1 + k2 / 100)**(X1 - k3)  # Calculate the growth factor
    return k0 + k1 * growth_factor

def calc_mult(coef, x_values: list) -> float:
    """
    Perform prediction using the provided coefficients and independent variables.

    :param x_values: List of independent variable values.
    :return: Predicted value.
    """
    x_values = [float(x) for x in x_values]
    return coef.coefficients[0] + coef.coefficients[1]*math.prod(x_values)

def calc_const_mult_div(coef,x_values: list) -> float:
    """
    Calculates the result of the formula K0 * (X1 / X2).

    :param coef: Coefficient value (K0).
    :param values: A list containing two values [X1, X2].
    :return: The calculated result or raises an exception for invalid inputs.
    """
    if len(x_values) != 2:
        raise ValueError("DDr must be a list of exactly two elements: [X1, X2]. const_mult_div")
    offset = coef.coefficients[0]  # Retrieve the intercept (`k0`)
    X1, X2 = x_values
    if X2 == 0:
        raise ValueError("DDr cannot be zero to avoid division by zero. const_mult_div")

    return offset * (X1 / X2)

def calc_lin_mult_div(coef, x_values: list) -> float:
    """
    Perform calculation based on the formula: (k0 + k1 * X1) * X2 / X3.

    :param coef: Coefficient object containing intercept and slope.
    :param x_values: List of independent variable values [X1, X2, X3].
    :return: Calculated result.
    """
    if len(x_values) != 3:
        print("DDr must contain exactly three elements: [X1, X2, X3].lin_mult_div")

    X1, X2, X3 = map(float, x_values)  # Ensure all inputs are floats

    if X3 == 0:
        raise ValueError("X3 cannot be zero to avoid division by zero.lin_mult_div")

    coefficients = coef.coefficients  # Extract only k0 and k1
    if len(coefficients) != 3:
        print("LIN_MULT_DIV requires exactly three coefficients: k0, k1, k3 ")

    k0, k1, k2 = coefficients
    return k0 + ((k1 + k2 * X1) * X2) / X3

def calc_exp_mult_div(coef, x_values: list) -> float:
    """
    Perform calculation based on the formula: k0 + k1 * ((1 + k2 / 100) ^ (X1 - k3)) * X2 / X3.

    :param coef: Coefficient object containing the coefficients [k0, k1, k2, k3].
    :param x_values: List of independent variable values [X1, X2, X3].
    :return: Calculated result.
    """
    if len(x_values) != 3:
        raise ValueError("DDr must contain exactly three elements: [X1, X2, X3].exp_mult_div")

    X1, X2, X3 = map(float, x_values)  # Ensure all inputs are floats

    if X3 == 0:
        raise ValueError("X3 cannot be zero to avoid division by zero. exp_mult_div")

    coefficients = coef.coefficients  # Extract only k0, k1, k2, k3
    if len(coefficients) != 4:
        raise ValueError("EXP_MULT_DIV requires exactly four coefficients: k0, k1, k2, k3.")

    k0, k1, k2, k3 = coefficients

    growth_factor = (1 + k2 / 100) ** (X1 - k3)  # Calculate the growth factor
    return k0 + k1 * growth_factor * (X2 / X3)

#-----------------------------------------------------------
def calc_exp_multivariable(coef, x_values: list) -> float:
    """
    Perform exponential multivariable calculation.
    Formula: y = k0 + kn * exp(k1 * X1 + k2 * X2 + ... + kn-1 * Xn-1)

    :param coef: Coefficient object containing the coefficients [k0, kn, k1, k2, ..., kn-1].
    :param x_values: List of independent variable values [X1, X2, ..., Xn-1].
    :return: Calculated result.
    """
    coefficients = coef.coefficients  # Retrieve all coefficients
    k0 = coefficients[0]  # Intercept (k0)
    kn = coefficients[1]#exponential scaling factor (kn)
    kn_minus_1 = coefficients[2:]  # Remaining coefficients [k1, k2, ..., kn-1]

    if len(kn_minus_1) != len(x_values):
        raise ValueError("Mismatch between the number of coefficients and independent variables.")

    # Compute the linear combination in the exponent
    exponent = sum(k * x for k, x in zip(kn_minus_1, x_values))

    # Compute the final result
    return k0 + kn * np.exp(exponent)

def multivariable_lin_interpolation(points, point):
    """
        Perform n-dimensional linear interpolation. Inverse Distance Weighting
        Parameters:
            points: A list of tuples [(coord1, coord2, ..., value), ...]
                    where coord1, coord2, ... are the coordinates, and value is the function value at that point.
            point: A tuple of coordinates (x, y, z, ...) where interpolation is desired.

        Returns:
            Interpolated value at the given point.
        """
    # Extract coordinates and values
    coords = np.array([p[:-1] for p in points])  # All coordinates (without values)
    values = np.array([p[-1] for p in points])  # Corresponding values

    # Ensure the point is within bounds
    mins = coords.min(axis=0)
    maxs = coords.max(axis=0)
    if not np.all((mins <= point) & (point <= maxs)):
        ValueError(f"Point {point} is out of bounds.")
        return multivariable_lin_interpolation_ignore_bounds(points,point)

    # Find the distances of all points to the target point
    distances = np.linalg.norm(coords - np.array(point), axis=1)

    # If the point matches exactly, return the value directly
    if np.isclose(distances.min(), 0.0):
        return values[np.argmin(distances)]

    # Compute weights as the inverse of distance
    weights = 1 / distances
    weights /= weights.sum()  # Normalize weights

    # Perform weighted sum of values
    interpolated_value = np.sum(weights * values)

    return interpolated_value

def multivariable_lin_interpolation_ignore_bounds(points, point):
    """
    Perform n-dimensional linear interpolation using Inverse Distance Weighting (IDW),
    ignoring bounds for extrapolation.

    Parameters:
        points: List of tuples [(coord1, coord2, ..., value), ...]
        point: Tuple of coordinates (x, y, ...)
    Returns:
        Interpolated value at the target point.
    """
    # Extract coordinates and values
    coords = np.array([p[:-1] for p in points])  # All coordinates (without values)
    values = np.array([p[-1] for p in points])  # Corresponding values

    # Calculate distances between target point and all known points
    distances = np.linalg.norm(coords - np.array(point), axis=1)
    # Handle exact match case
    if np.isclose(distances.min(), 0.0):
        return values[np.argmin(distances)]

    # Compute weights as the inverse of the distances
    weights = 1 / distances
    weights /= weights.sum()  # Normalize the weights

    # Perform weighted sum of values
    interpolated_value = np.sum(weights * values)

    return interpolated_value

def calc_lin_share(coef, x_values) -> float:
    """
    Perform calculation based on the formula: k0 + (k1+k2*DDr1)*DDr2.
    :param coef: Coefficient object containing intercept and slope fpr share function
    :param x_values: List of independent variable values [X1, X2]. [time, pop]
    :return: Calculated result.
    """
    if len(x_values) != 2:
        raise ValueError("DDr must contain exactly two elements: [X1, X2].lin_share")
    X1, X2= map(float, x_values)  # Ensure all inputs are floats
    k0, k1, k2 = coef.coefficients  # Extract only k0 and k1
    return k0 + (k1+k2*X1)*X2
