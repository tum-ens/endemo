from datetime import datetime
from time import perf_counter
from pathlib import Path
import pandas as pd

from endemo2.Input.model_config import InputManager, is_truthy
from endemo2.Input.hierachy_builder import initialize_hierarchy_and_load_input
from endemo2.Modeling.dependent_ddr_forecast import forecast_dependent_ddrs
from endemo2.Modeling.subregion_division_forecast import forecast_subregion_division
from endemo2.Modeling.model_ECU_DDet import calc_ECU_DDet
from endemo2.Modeling.model_useful_energy import calculate_useful_energy
from endemo2.Modeling.model_final_energy import calculate_final_energy
from endemo2.Modeling.model_timeseries import calculate_timeseries
from endemo2.output.output_to_excel import ExcelWriter


class Endemo:
    """
    This is the whole program. From here we control what the model does on the highest level.
    """

    def __init__(self):
        self.input_manager = None
        self.data = None
        self.output_to_excel = None
        self.run_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.run_output_path = None

    @staticmethod
    def _timestamp() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _prepare_run_output_directory(self):
        self.run_output_path = Path(self.input_manager.output_path) / self.run_timestamp
        self.run_output_path.mkdir(parents=True, exist_ok=True)
        setattr(self.data, "runtime_output_path", self.run_output_path)

    def _collect_missing_forecasts(self):
        rows = []
        for region in getattr(self.data, "regions", []) or []:
            region_name = getattr(region, "region_name", None)
            for sector in getattr(region, "sectors", []) or []:
                sector_name = getattr(sector, "name", None)
                for subsector in getattr(sector, "subsectors", []) or []:
                    subsector_name = getattr(subsector, "name", None)
                    ecu = getattr(subsector, "ecu", None)
                    technologies = getattr(subsector, "technologies", []) or []
                    for technology in technologies:
                        technology_name = getattr(technology, "name", None)
                        if ecu is None or getattr(ecu, "forecast", None) is None or ecu.forecast.empty:
                            rows.append({
                                "Kind": "ECU",
                                "Region": region_name,
                                "Sector": sector_name,
                                "Subsector": subsector_name,
                                "Technology": technology_name,
                                "Variable": getattr(ecu, "name", None) if ecu is not None else None,
                                "Reason": "Missing forecast dataframe",
                            })
                        for ddet in getattr(technology, "ddets", []) or []:
                            if getattr(ddet, "forecast", None) is None or ddet.forecast.empty:
                                rows.append({
                                    "Kind": "DDet",
                                    "Region": region_name,
                                    "Sector": sector_name,
                                    "Subsector": subsector_name,
                                    "Technology": technology_name,
                                    "Variable": getattr(ddet, "name", None),
                                    "Reason": "Missing forecast dataframe",
                                })
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame(rows).drop_duplicates().sort_values(
            by=["Kind", "Region", "Sector", "Subsector", "Technology", "Variable"],
            na_position="last",
        ).reset_index(drop=True)

    def _validate_forecast_completeness(self):
        missing = self._collect_missing_forecasts()
        if missing.empty:
            return

        report_path = self.run_output_path / "validation_missing_forecasts.xlsx"
        with pd.ExcelWriter(report_path, engine="openpyxl") as writer:
            missing.to_excel(writer, sheet_name="MissingForecasts", index=False)

        ecu_count = int((missing["Kind"] == "ECU").sum())
        ddet_count = int((missing["Kind"] == "DDet").sum())
        raise ValueError(
            "[Validation] Missing forecast inputs detected after prediction step. "
            f"ECU missing: {ecu_count}, DDet missing: {ddet_count}. "
            f"See '{report_path}'."
        )

    def execute_with_preprocessing(self):

        """
        Executes the whole program from start to end.
        """
        total_start = perf_counter()
        print(f"[{self._timestamp()}] Start Endemo run")

        # Initialize Input and reads general settings
        print(f"[{self._timestamp()}] Reading settings...")
        step_start = perf_counter()
        self.input_manager = InputManager()
        print(f"[{self._timestamp()}] Settings successfully read. ({perf_counter() - step_start:.2f}s)")

        # Read input data for active_regions in active sectors and builds the region-objectss
        print(f"[{self._timestamp()}] Reading input data for active sectors...")
        step_start = perf_counter()
        self.data = initialize_hierarchy_and_load_input(self.input_manager)
        self._prepare_run_output_directory()
        print(f"[{self._timestamp()}] Input data successfully read. ({perf_counter() - step_start:.2f}s)")

        # Forecast dependent demand drivers first (so they can be used by ECU/DDet)
        subregional_on = is_truthy(self.input_manager.general_settings.subregional_resolution)
        print(f"[{self._timestamp()}] Do DDr and Subregional forecast")
        step_start = perf_counter()
        forecast_dependent_ddrs(self.data)
        # Forecast subregional division (parallel channel) only when enabled
        if subregional_on:
            forecast_subregion_division(self.data)
        print(f"[{self._timestamp()}] Forecast for DDrs and Subregions done ({perf_counter() - step_start:.2f}s)")

        # #Calculate the forecast (calculate ECUs and DDet) #noch sch�n machen!
        print(f"[{self._timestamp()}] Do Predictions...")
        step_start = perf_counter()
        calc_ECU_DDet(self.data)
        print(f"[{self._timestamp()}] Predictions successfully done ({perf_counter() - step_start:.2f}s)")

        print(f"[{self._timestamp()}] Validate forecast completeness ...")
        step_start = perf_counter()
        self._validate_forecast_completeness()
        print(f"[{self._timestamp()}] Forecast completeness successfully validated ({perf_counter() - step_start:.2f}s)")

        # Calculate useful energy
        print(f"[{self._timestamp()}] Calculate useful energy ...")
        step_start = perf_counter()
        calculate_useful_energy(self.data)
        print(f"[{self._timestamp()}] Calculate useful energy successfully done... ({perf_counter() - step_start:.2f}s)")

        # Calculate final energy
        print(f"[{self._timestamp()}] Calculate Final energy ...")
        step_start = perf_counter()
        calculate_final_energy(self.data)
        print(f"[{self._timestamp()}] Calculate Final energy successfully done... ({perf_counter() - step_start:.2f}s)")

        print(f"[{self._timestamp()}] Calculate Timeseries ...")
        step_start = perf_counter()
        calculate_timeseries(self.data)
        print(f"[{self._timestamp()}] Calculate Timeseries successfully done... ({perf_counter() - step_start:.2f}s)")

        # generate output files
        print(f"[{self._timestamp()}] Export output to excel ...")
        step_start = perf_counter()
        self.output_to_excel = ExcelWriter(self.data)
        print(f"[{self._timestamp()}] Exporting successfully done... ({perf_counter() - step_start:.2f}s)")

        print(f"[{self._timestamp()}] End Endemo run ({perf_counter() - total_start:.2f}s)")
