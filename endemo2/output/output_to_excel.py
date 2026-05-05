from pathlib import Path
from datetime import datetime
from collections import defaultdict
import os

from endemo2.output.writers import (
    OutputCommonMixin,
    SectorEnergyOutputMixin,
    SubregionalOutputMixin,
    TimeseriesOutputMixin,
    DiagramOutputMixin,
)


class ExcelWriter(
    OutputCommonMixin,
    SectorEnergyOutputMixin,
    SubregionalOutputMixin,
    TimeseriesOutputMixin,
    DiagramOutputMixin,
):
    def __init__(self, data):
        # Create a timestamped output directory
        self.data = data
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        existing_output_path = getattr(data, "runtime_output_path", None)
        self.output_path = Path(existing_output_path) if existing_output_path else self._create_output_directory(data.input_manager)
        os.makedirs(self.output_path, exist_ok=True)
        # Data collection structures
        self.sector_forecasts = defaultdict(list)
        self.ue_sector_data = defaultdict(list)
        self.fe_sector_data = defaultdict(list)
        self.timeseries_data = defaultdict(list)
        self.efficiency = defaultdict(list)
        self._subregion_distribution_errors = set()
        self.process_all(data)

    def _create_output_directory(self, input_manager) -> Path:
        """Create timestamped output directory using existing InputManager paths"""
        base_path = Path(input_manager.output_path)
        timestamped_path = base_path / self.timestamp
        timestamped_path.mkdir(parents=True, exist_ok=True)
        return timestamped_path

    def process_all(self, data):
        """Single method to handle full workflow"""
        self.collect_sector_forecasts(data)
        if data.input_manager.general_settings.UE_marker == 1:
            self.collect_ue_data(data.regions)
        if data.input_manager.general_settings.FE_marker == 1:
            self.collect_fe_data(data.regions)
        self.write_all_outputs()
        if self.data.input_manager.general_settings.graphical_out == 1:
            self._write_diagrams()

    def write_all_outputs(self):
        """Final method to write all collected data to Excel"""
        subregional_on = self._is_enabled(self.data.input_manager.general_settings.subregional_resolution)
        self._write_sector_forecasts()
        self._write_ue_sector_data()
        self._write_fe_sector_data()
        self._write_combined_aggregate_workbook()
        if subregional_on:
            self._write_ue_subregions()
            self._write_ecu_subregions()
            if self._is_enabled(self.data.input_manager.general_settings.FE_marker):
                self._write_fe_subregions()
        self._write_timeseries_data()
        self._write_dependent_ddrs()
        if subregional_on:
            self._write_subregion_division_forecast()
