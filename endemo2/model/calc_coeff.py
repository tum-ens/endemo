import numpy as np
import math
from scipy.optimize import curve_fit
from itertools import combinations_with_replacement
from sklearn.linear_model import LinearRegression


def calc_coef_const_last(X : list, y: list):
    if not y:
        raise ValueError("Data cannot be empty.")

        # Get the last y value from the data
    k0 = y[-1]  # Extract the y value of the last data point
    equation = "y = k0"
    # Return as a list [k0]
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

    k0 = 0 # constant term is defined as zero
    k1 = y[-1]/math.prod(X[-1])  # Linear term - Extract the last data point y and divide with the drivers
    equation = "y = 0 + k1*x1*x2..."
    # Return as a list [k0]
    return [k0, k1], equation


def calc_coef_lin_multivariable_sklearn(X: list, y: list):
    """
    Generate multivariate linear regression coefficients using scikit-learn with significant figures limitation.

    Parameters:
    - X: list of  (independent variables) [[X1_1,X2_1],[X1_2,X2_2]...]
    - y: list (dependent variable) [Y1,Y2....]

    Returns:
    - result: list of coefficients formatted to sigfigs [intercept, coef1, coef2, ...]
    - equation: str, the regression equation
    """
    sigfigs = 6 #  - sigfigs: int, number of significant figures to round to (default: 4)
    # Convert X and y to numpy arrays
    X = np.array(X)
    y = np.array(y).T
    # Initialize and fit the linear regression model
    model = LinearRegression()
    model.fit(X, y)
    # Extract coefficients and intercept
    # coefficients = model.coef_  # Coefficients for each independent variable
    # intercept = model.intercept_  # Intercept (k0)
    # Format to significant figures without losing precision
    def format_to_sigfigs(num, sigfigs):
        return float(f"{num:.{sigfigs}g}")
    intercept = format_to_sigfigs(float(model.intercept_), sigfigs)
    coefficients = [format_to_sigfigs(coef, sigfigs) for coef in model.coef_]
    equation = f"y = k0 + k1*x1+k2*x2+…"
    # Combine coefficients and intercept into a single list
    result = [intercept] + coefficients
    return result, equation # Return coefficients and intercept

def calc_coef_exp_multivariable(X: np.ndarray, y: np.ndarray):
    """
    Generate coefficients for the exponential multivariable regression model:
    y = k0 + kn * exp(k1 * X1 + k2 * X2 + ... + kn-1 * Xn-1)

    :param X: Independent variable data as a 2D NumPy array (shape: [n_samples, n_features]).
    :param y: Dependent variable data as a 1D NumPy array (shape: [n_samples]).
    :return: List of coefficients [k0, kn, k1, k2, ..., kn-1].
    """
    if X.ndim != 2 or y.ndim != 1:
        raise ValueError("X must be a 2D array and y must be a 1D array.")
    if X.shape[0] != y.shape[0]:
        raise ValueError("Number of samples in X and y must match.")

    # Define the model function (vectorized to handle multiple samples)
    def exponential_model(X_flat, k0, kn, *coeffs):
        X_reshaped = X_flat.reshape(-1, len(coeffs))  # Reshape back into original feature dimensions
        linear_combination = np.dot(X_reshaped, coeffs)  # Compute k1 * X1 + k2 * X2 + ...
        return k0 + kn * np.exp(linear_combination)

    # Initial guess for the parameters
    n_features = X.shape[1]
    initial_guess = [1.0] * (2 + n_features)  # [k0, kn, k1, k2, ..., kn-1]
    # Flatten X before passing to curve_fit
    popt, _ = curve_fit(exponential_model, X.flatten(), y, p0=initial_guess) #TODO
    equation = "y = k0 + kn * exp(k1 * X1 + k2 * X2 + ... + kn-1 * Xn-1)"
    return popt.tolist(), equation

def calc_coef_quadratic_multivariable(X : list, y: list):
    # Quadratic Multivariate: y = k1*x1^2 + k2*x2^2 + ... + kn*x1 + km*x2 + k0
    X = np.array(X)
    y = np.array(y)

    # Create quadratic terms and add bias term
    X_quad = np.hstack([X ** 2, X, np.ones((X.shape[0], 1))])
    coeffs, _, _, _ = np.linalg.lstsq(X_quad, y, rcond=None)
    return coeffs  # [k1, k2, ..., kn, km, k0]


def calc_coef_polynom_multivariable(X : list, y: list, degree: int):
    # Polynomial Multivariate: Generalization for any degree

    X = np.array(X)
    y = np.array(y)

    # Generate all polynomial terms up to the given degree
    n_features = X.shape[1]
    terms = []
    for d in range(1, degree + 1):
        terms.extend(combinations_with_replacement(range(n_features), d)) #TODO

    X_poly = np.ones((X.shape[0], len(terms) + 1))  # Include k0 (bias term)
    for i, term in enumerate(terms):
        X_poly[:, i] = np.prod(X[:, term], axis=1)

    coeffs, _, _, _ = np.linalg.lstsq(X_poly, y, rcond=None)
    return coeffs  # Polynomial coefficients [k1, k2, ..., kn, k0]



def calc_coef_log_multivariable(X: list, y: list):
    """
    Generate multivariate logarithmic regression coefficients.
    Logarithmic Multivariate: y = k1*log(x1) + k2*log(x2) + ... + k0
    :param X: List of independent variables.
    :param y: List of dependent variable values.
    :return: Coefficients and equation string.
    """
    # Convert X and y to numpy arrays
    X = np.array(X).T
    y = np.array(y)

    # Take the natural log of X
    X_log = np.log(X)

    # Initialize and fit the linear regression model
    model = LinearRegression()
    model.fit(X_log, y)

    # Extract coefficients and intercept
    coefficients = model.coef_
    intercept = model.intercept_

    # Format the equation
    terms = [f"{coeff:.7f}*log(x{i + 1})" for i, coeff in enumerate(coefficients)]
    equation = " + ".join(terms)
    equation += f" + {intercept:.7f}"

    # Combine coefficients and intercept into a single list
    result = [intercept] + coefficients.tolist()
    print(result)
    return f"y = {equation}", result


def calc_coef_lin_share(X, y):

    X = np.array(X).T
    y = np.array(y)

    DDr2 = X[1] #the second DDr
    var_share_hist = y / DDr2
    DDr1 = np.array(X[0])[:, np.newaxis]

    coef_lin, equation = calc_coef_lin_multivariable_sklearn(DDr1,var_share_hist) # coef_lin [k1,k2]
    coef = [0] + coef_lin
    return coef, equation

