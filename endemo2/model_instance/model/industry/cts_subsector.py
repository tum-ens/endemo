from endemo2.data_structures.containers import Demand, SpecConsum, Heat


class CtsSubsector:

    def __init__(self, subsector_name: str, cts_pp: CtsPreprocessed):
        self.subsector_name = subsector_name

    def calculate_demand(self) -> Demand:

        # get values from instance filter
        specific_consumption: SpecConsum = SpecConsum(0, 0, 0)    # todo per country
        employees_perc_of_population: float = 0.0   # todo per subsector
        population_country: float = 0.0  # todo per country
        heat_levels: Heat = Heat()  # todo CTS

        # calculate demand
        electricity = employees_perc_of_population * specific_consumption.electricity * population_country
        heat = employees_perc_of_population * specific_consumption.heat * population_country

        # split heat levels
        heat = heat_levels.copy_multiply_scalar(heat)

        # final demand
        demand = Demand(electricity, heat, 0.0)

        return demand

    def calculate_demand_distributed_by_nuts2(self) -> dict[str, Demand]:

        # get values from instance filter
        specific_consumption: SpecConsum = SpecConsum(0, 0, 0)  # todo per country
        employees_perc_nuts2: dict[str, float] = dict()    # todo per nuts2 per subsector
        population_nuts2: dict[str, float] = dict()    # todo per nuts2
        heat_levels: Heat = Heat()  # todo CTS

        # calculate per nuts2 region
        demand_nuts2 = dict[str, Demand]()

        for region_name, employee_perc_region in employees_perc_nuts2.items():
            # calculate demand
            population_region = population_nuts2[region_name]
            electricity = employee_perc_region * specific_consumption.electricity * population_region
            heat = employee_perc_region * specific_consumption.heat * population_region

            # split heat levels
            heat = heat_levels.copy_multiply_scalar(heat)

            # final demand
            demand = Demand(electricity, heat, 0.0)
            demand_nuts2[region_name] = demand

        return demand_nuts2


    def calculate_hourly_demand(self) -> [Demand]:
        pass

    def calculate_hourly_demand_distributed_by_nuts2(self) -> dict[str, [Demand]]:
        pass





