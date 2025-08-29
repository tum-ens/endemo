from __future__ import annotations
from endemo2.data_structures.enumerations import ForecastMethod

# Mapping ForecastPrediction Enum to strings for method selections
map_forecast_method_to_string = {
    ForecastMethod.LIN: "lin",
    ForecastMethod.EXP: "exp",
    ForecastMethod.LOG: "log",
    ForecastMethod.CONST_MEAN: "const_mean",
    ForecastMethod.CONST_LAST: "const_last",
    ForecastMethod.CONST: "const",
    ForecastMethod.QUADR: "quadr",
    ForecastMethod.POLY: "poly",
    ForecastMethod.LIN_MULT_DIV: "lin_mult_div",
    ForecastMethod.EXP_MULT_DIV: "exp_mult_div",
    ForecastMethod.CONST_MULT_DIV: "const_mult_div",
    ForecastMethod.INTERP_LIN: "interp_lin",
    ForecastMethod.MULT: "mult",
    ForecastMethod.MULT_K0_ZERO: "mult_k0_zero",
    ForecastMethod.LIN_SHARE: "lin_share"
}

region_colors = {
            'Belgium': '#FF7F0E',  # Orange
            'Bulgaria': '#1F77B4',  # Blue
            'Czechia': '#2CA02C',  # Green
            'Denmark': '#D62728',  # Red
            'Germany': '#9467BD',  # Purple
            'Ireland': '#8C564B',  # Brown
            'Greece': '#E377C2',  # Pink
            'Spain': '#7F7F7F',  # Gray
            'France': '#BCBD22',  # Lime
            'Croatia': '#17BECF',  # Cyan
            'Italy': '#F08080',  # Light Coral
            'Latvia': '#00CED1',  # Dark Turquoise
            'Luxembourg': '#DAA520',  # Goldenrod
            'Hungary': '#8A2BE2',  # Blue Violet
            'Netherlands': '#5F9EA0',  # Cadet Blue
            'Austria': '#FF1493',  # Deep Pink
            'Poland': '#ADFF2F',  # Green Yellow
            'Portugal': '#FF4500',  # Orange Red
            'Romania': '#7FFF00',  # Chartreuse
            'Slovenia': '#40E0D0',  # Turquoise
            'Slovakia': '#9ACD32',  # Yellow Green
            'Finland': '#FFD700',  # Gold
            'Sweden': '#DC143C',  # Crimson
            'United Kingdom': '#4682B4',  # Steel Blue
            'Norway': '#00FA9A',  # Medium Spring Green
            'Switzerland': '#B22222',  # Firebrick
            'Montenegro': '#9932CC',  # Dark Orchid
            'North Macedonia': '#556B2F',  # Dark Olive Green
            'Albania': '#6495ED',  # Cornflower Blue
            'Serbia': '#DB7093',  # Pale Violet Red
            'Bosnia and Herzegovina': '#20B2AA',  # Light Sea Green
            'Iceland': '#FF6347',  # Tomato
            'Lithuania': '#6A5ACD',  # Slate Blue
            'Estonia': '#66CDAA'  # Medium Aquamarine
        }



