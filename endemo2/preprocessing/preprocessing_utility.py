import itertools

from endemo2.data_structures.containers import Interval, EH
from endemo2.data_structures.prediction_models import Timeseries


def energy_carrier_to_energy_consumption(efficiency: dict[str, EH],
                                         dict_ec_his: dict[str, [(float, float)]]) -> (Timeseries, Timeseries):
    """
    Convert the energy carriers to electricity and heat with efficiency and sum them up.

    :param efficiency: The efficiency of each energy carrier of the form {energy_carrier_name -> efficiency_tuple}
    :param dict_ec_his: The energy carrier consumption of form {energy_carrier_name -> consumption_amount_data}
    :return: sum of energy consumption and sum of heat consumption.
        Of form (energy_consumption_sum, heat_consumption_sum)
    """
    electricity_demand_sum = Timeseries([])
    heat_demand_sum = Timeseries([])

    for energy_carrier_name, ec_his_am in dict_ec_his.items():
        ts_historical_energy_carrier_amount = Timeseries(ec_his_am)
        energy_carrier_efficiency_electricity = efficiency[energy_carrier_name].electricity
        energy_carrier_efficiency_heat = efficiency[energy_carrier_name].heat

        # multipy with efficiency of energy carrier to get demand
        energy_carrier_electricity = \
            Timeseries.map_y(ts_historical_energy_carrier_amount,
                             lambda x: x * energy_carrier_efficiency_electricity)
        energy_carrier_heat = \
            Timeseries.map_y(ts_historical_energy_carrier_amount,
                             lambda x: x * energy_carrier_efficiency_heat)

        # sum total demand over all energy carriers
        electricity_demand_sum.add(energy_carrier_electricity)
        heat_demand_sum.add(energy_carrier_heat)

    return electricity_demand_sum, heat_demand_sum

