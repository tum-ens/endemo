"""
This module contains the functions for forecast
"""
import numpy as np
import math
from scipy.spatial import distance

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

def calc_lin_interpolation(points, point_x):
    point_x = point_x[0]

    # Check if point_x is outside the known x-values
    if point_x < points[0][0] or point_x > points[-1][0]:
        raise ValueError("point_x is out of bounds of the given points")

    # Find the two points between which point_x lies
    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]

        if x0 <= point_x <= x1:
            # Linear interpolation formula
            t = (point_x - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)

    # If point_x exactly matches the last point's x
    if point_x == points[-1][0]:
        return points[-1][1]

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

