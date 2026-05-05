from endemo2.Modeling.Methods.prediction_methods import ForecastMethod, Method
from endemo2.Modeling.Methods import calc_functions as ff, calc_coeff as cg

"""
Mapps the different calculations methods together. Is used by the forecast.
"""

forecast_methods_map = {
    ForecastMethod.CONST: {
        "generate_coef": cg.calc_coef_const_last,
        "min_points": 1,
        "save_coef": Method.save_coef,
        "predict_function": ff.calc_constant,
        "get_eqaution_user": "y = const = k0"
    },
    ForecastMethod.CONST_LAST: {
        "generate_coef": cg.calc_coef_const_last,
        "min_points": 1,
        "save_coef": Method.save_coef,
        "predict_function": ff.calc_constant,
        "get_eqaution_user": "y = const = y(t_hist)"
    },
    ForecastMethod.CONST_MEAN: {
        "generate_coef": cg.calc_coef_const_mean,
        "min_points": 1,
        "save_coef": Method.save_coef,
        "predict_function": ff.calc_constant_mean,
        "get_eqaution_user": "y = const = avg of all y(t_hist))"
    },
    ForecastMethod.LIN: {
        "generate_coef": cg.calc_coef_lin_multivariable_sklearn,
        "min_points": 2,
        "save_coef": Method.save_coef,
        "predict_function": ff.calc_lin,
        "get_eqaution_user": "y = k0 + k1*DDr1 + k2*DDr2 + ..."
    },
    ForecastMethod.EXP: {
        "generate_coef": cg.calc_coef_exp_multivariable,
        "min_points": 2,
        "save_coef": Method.save_coef,
        "predict_function": ff.calc_exp,
        "get_eqaution_user": "y = k0 + k1 * ((1 + k2 / 100) ^ (DDr1 - k3))"
    },
    ForecastMethod.LOG: {
        "generate_coef": cg.calc_coef_log_multivariable,
        "min_points": 2,
        "save_coef": Method.save_coef,
        "get_eqaution_user": "y = ...."
    },
    ForecastMethod.LOG_SUM: {
        "generate_coef": cg.calc_coef_log_sum,
        "min_points": lambda n_features: max(2, n_features + 1),
        "save_coef": Method.save_coef,
        "predict_function": ff.calc_log_sum,
        "get_eqaution_user": "y = k0 + k1*log(DDr1) + k2*log(DDr2) + ..."
    },
    ForecastMethod.EXP_SUM: {
        "generate_coef": cg.calc_coef_exp_sum,
        "min_points": lambda n_features: max(3, 1 + 2 * n_features),
        "save_coef": Method.save_coef,
        "predict_function": ff.calc_exp_sum,
        "get_eqaution_user": "y = k0 + k1*e^(k2*DDr1) + k3*e^(k4*DDr2) + ..."
    },
    ForecastMethod.POWER_SUM: {
        "generate_coef": cg.calc_coef_power_sum,
        "min_points": lambda n_features: max(3, 1 + 2 * n_features),
        "save_coef": Method.save_coef,
        "predict_function": ff.calc_power_sum,
        "get_eqaution_user": "y = k0 + k1*DDr1^k2 + k3*DDr2^k4 + ..."
    },
    ForecastMethod.BASE_EXP_SUM: {
        "generate_coef": cg.calc_coef_base_exp_sum,
        "min_points": lambda n_features: max(2, n_features + 1),
        "save_coef": Method.save_coef,
        "predict_function": ff.calc_base_exp_sum,
        "get_eqaution_user": "y = k0 + k1^(DDr1*k2) + k3^(DDr2*k4) + ..."
    },
    ForecastMethod.USER_FUNCTION: {
        "generate_coef": "",
        "min_points": "",
        "save_coef": Method.save_coef,
        "predict_function": ff.calc_user_function,
        "get_eqaution_user": "y = <user_function>"
    },
    ForecastMethod.INTERP_LIN: {
        "generate_coef": "",
        "min_points": "",
        "save_coef": "",
        "predict_function": ff.calc_lin_interpolation,
        "get_eqaution_user": "linear interpolation"
    },
    ForecastMethod.QUADR: {
        "generate_coef": cg.calc_coef_quadratic_multivariable,
        "min_points": 3,
        "save_coef": Method.save_coef,
        "get_eqaution_user": "y = ...."
    },
    ForecastMethod.POLY: {
        "generate_coef": lambda X, y: cg.calc_coef_polynom_multivariable(X, y, degree=3),
        "min_points": 3,
        "save_coef": Method.save_coef,
        "get_eqaution_user": "y = ...."
    },
    ForecastMethod.MULT: {
        "generate_coef": "",
        "min_points": "",
        "save_coef": Method.save_coef,
        "predict_function": ff.calc_mult,
        "get_eqaution_user": "y = k0 + k1 *DDr1*DDr2*DDr3..."
    },
    ForecastMethod.MULT_K0_ZERO: {
        "generate_coef": cg.calc_coef_mult_k0_zero,
        "min_points": 1,
        "save_coef": Method.save_coef,
        "predict_function": ff.calc_mult,
        "get_eqaution_user": "y = k0 + k1*DDr1*DDr2*DDr3..."
    },
    ForecastMethod.CONST_MULT_DIV: {
        "generate_coef": "",
        "min_points": "",
        "save_coef": Method.save_coef,
        "predict_function": ff.calc_const_mult_div,
        "get_eqaution_user": "y = k0 * (DDr1 / DDr2)"
    },
    ForecastMethod.LIN_MULT_DIV: {
        "generate_coef": "",
        "min_points": "",
        "save_coef": Method.save_coef,
        "predict_function": ff.calc_lin_mult_div,
        "get_eqaution_user": "y = k0 + (k1 + k2*DDr1)*DDr2/DDr3"
    },
    ForecastMethod.EXP_MULT_DIV: {
        "generate_coef": "",
        "min_points": "",
        "save_coef": Method.save_coef,
        "predict_function": ff.calc_exp_mult_div,
        "get_eqaution_user": "y = k0 + k1 * ((1 + k2 / 100) ^ (DDr1 - k3)) * DDr2/DDr3"
    },
    ForecastMethod.LIN_SHARE: {
        "generate_coef": cg.calc_coef_lin_share,
        "min_points": 2,
        "save_coef": Method.save_coef,
        "predict_function": ff.calc_lin_share,
        "get_eqaution_user": "y = k0 + (k1 + k2*DDr1) * DDr2"
    },
}
