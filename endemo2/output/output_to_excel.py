from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from datetime import datetime
from collections import defaultdict
import os
import time
from endemo2.output.grapthical_output import GraphDataPreparer, Visualizer

class ExcelWriter:
    def __init__(self, data):
        # Create a timestamped output directory
        self.data = data
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.output_path = self._create_output_directory(data.input_manager)
        os.makedirs(self.output_path, exist_ok=True)
        # Data collection structures
        self.sector_forecasts = defaultdict(list)
        self.ue_sector_data = defaultdict(list)
        self.fe_sector_data = defaultdict(list)
        self.timeseries_data = defaultdict(list)
        self.efficiency = defaultdict(list)
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
        self._write_sector_forecasts()
        self._write_ue_sector_data()
        self._write_fe_sector_data()
        self._write_timeseries_data()

    def collect_ue_data(self, regions):
        """Collect useful energy data from model_useful_energy structure"""
        for region in regions:
            if not region.energy_ue.empty:
                self._process_region_ue(region)

    def collect_fe_data(self, regions):
        """Collect final energy data from model_useful_energy structure"""
        for region in regions:
            if region.energy_fe is not None and not region.energy_fe.empty:
                self._process_region_fe(region)

    def _process_region_ue(self, region):
        """Process region-level UE data"""
        df = region.energy_ue
        # Prepare sector-level data
        for sector_name, sector_df in df.groupby('Sector'):
            self.ue_sector_data[sector_name].append(sector_df)

    def _process_region_fe(self, region):
        """Process region-level UE data"""
        df = region.energy_fe
        # Prepare sector-level data
        for sector_name, sector_df in df.groupby('Sector'):
            self.fe_sector_data[sector_name].append(sector_df)

    def collect_sector_forecasts(self, data):
        """Collect forecast data from model_forecast structure"""
        if data.efficiency_data:
            v1, v2 = data.efficiency_data
            forecast_eff = v1.forecast
            forecast_share = v2.forecast
            self.efficiency[v1.name].append(forecast_eff)
            self.efficiency[v2.name].append(forecast_share)
        for region in data.regions:
            for sector in region.sectors:
                for subsector in sector.subsectors:
                    self._process_subsector_data(region, sector, subsector)

    def _process_subsector_data(self, region, sector, subsector):
        """Process subsector-level data"""
        # Handle ECU forecast
        if subsector.ecu.forecast is not None:
            self._add_forecast_entry(
                region, sector, subsector,
                subsector.ecu, None
            )
        # Handle technology forecasts
        for tech in subsector.technologies:
            for var in tech.ddets:
                if var.forecast is not None:
                    self._add_forecast_entry(
                        region, sector, subsector,
                        var, tech.name
                    )

    def _add_forecast_entry(self, region, sector, subsector, variable, technology):
        """Format and store a forecast entry"""
        # Use conditional assignment instead of insert
        df = variable.forecast.copy()
        df.columns = df.columns.astype(str)
        # df = df.assign(
        #     Region=region.region_name,
        #     Subsector=subsector.name,
        #     Variable=variable.name,
        #     Technology=technology
        # )
        # # Reorder columns if needed (safer than insert)
        column_order = ["Region",'Subsector', 'Variable',"Technology","UE_Type","FE_Type","Temp_level","Subtech","Drive"] + \
                       [col for col in df.columns if col not in ["Region",'Subsector', 'Variable',"Technology","UE_Type","FE_Type","Temp_level","Subtech","Drive"]]
        self.sector_forecasts[sector.name].append(df[column_order])

    def _write_sector_forecasts(self):
        """Handle sector forecast writing"""
        sector_dir = self.output_path / "sector_forecasts"
        sector_dir.mkdir(exist_ok=True)
        for sector_name, dfs in self.sector_forecasts.items():
            if dfs:
                combined = pd.concat(dfs, ignore_index=True)
                file_path = sector_dir / f"predictions_{sector_name}.xlsx"
                combined.to_excel(file_path, index=False)

        for name, df in self.efficiency.items():
            if not all(x is None for x in df):# if df is not None and df:
                combined = pd.concat(df, ignore_index=True)
                file_path = sector_dir / f"predictions_{name}.xlsx"
                combined.to_excel(file_path, index=False)

    def _write_timeseries_data(self):
        if self.data.input_manager.general_settings.timeseries_forecast == 0:
            return
        print("Starting timeseries export...")
        start_time = time.time()
        self._write_timeseries_results()
        if self.data.input_manager.general_settings.timeseries_per_region == 1:
            directory = self.output_path / "timeseries"
            directory.mkdir(exist_ok=True)
            self._write_per_region_timeseries(directory)
        print(f"Timeseries export completed in {time.time() - start_time:.2f}s")

    def _write_timeseries_results(self):
        output_path = self.output_path / "timeseries_total.xlsx"
        metadata = []
        yearly_data = {}  # {year: {header: [values]}}
        for region in self.data.regions:
            if not hasattr(region, 'timeseries_results') or not region.timeseries_results['profiles']:
                continue
            for pid, pdata in region.timeseries_results['profiles'].items():
                comp = pdata['components']
                # Add to metadata sheet (unchanged)
                metadata.append({
                    'Region': region.code,
                    'Profile ID': pid,
                    **comp,
                    'Sectors': ', '.join(pdata['contributors']['sectors']),
                    'Subsectors': ', '.join(pdata['contributors']['subsectors']),
                    'Techs': ', '.join(pdata['contributors']['technologies']),
                    'Subtechs': ', '.join(pdata['contributors']['subtechs']),
                    'Drives': ', '.join(pdata['contributors']['drives'])
                })
                # Process yearly data in column format
                for yr, ydata in pdata['years'].items():
                    if yr not in yearly_data:
                        yearly_data[yr] = {}
                    # Create column header
                    ue_type = comp['ue_type'].capitalize()
                    if ue_type == "Heat":
                        header = f"{region.code}.{ue_type}_{comp['temp_level']}"
                    else:
                        header = f"{region.code}.{ue_type}"
                    # Create column data
                    column_data = [
                        ydata['annual_energy']  # Third row: annual value
                    ]
                    # Add hourly values (8760 rows)
                    column_data.extend(ydata['hourly_values'])
                    yearly_data[yr][header] = column_data
            # Write to Excel
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Write metadata sheet
            if metadata:
                pd.DataFrame(metadata).to_excel(writer, sheet_name="Metadata", index=False)
            # Write yearly sheets
            for year, columns in yearly_data.items():
                # Create DataFrame
                max_length = max(len(col) for col in columns.values())
                data = {header: col + [None] * (max_length - len(col))
                        for header, col in columns.items()}
                df = pd.DataFrame(data)
                new_column = ["total"] + [str(i) for i in range(1, 8761)]
                df.insert(0, "Country_code.Commodity", new_column)
                # Write to sheet named after the year
                df.to_excel(writer, sheet_name=str(year), index=False)


    def _write_per_region_timeseries(self,directory):
        def process_region(region):
            if not any(getattr(s, 'timeseries_results', {}).get('profiles') for s in region.sectors):
                return
            output_path = directory / f"{region.region_name}.xlsx"
            metadata = []
            timeseries_data = []
            for sector in region.sectors:
                if not getattr(sector, 'timeseries_results', {}).get('profiles'):
                    continue
                for pid, pdata in sector.timeseries_results['profiles'].items():
                    # Use pre-parsed components if available
                    comp = pdata['components']
                    metadata.append({
                        'Sector': sector.name,
                        'Profile ID': pid,
                        **comp,
                        'Subsectors': ', '.join(pdata['contributors']['subsectors']),
                        'Techs': ', '.join(pdata['contributors']['technologies']),
                        'Subtechs': ', '.join(pdata['contributors']['subtechs']),
                        'Drives': ', '.join(pdata['contributors']['drives'])
                    })
                    # Process data in bulk per profile
                    for yr, ydata in pdata['years'].items():
                        hours = range(1, len(ydata['hourly_values']) + 1)
                        for hour in hours:
                            timeseries_data.append({
                                'Sector': sector.name,
                                'Profile': pid,
                                'Hour': hour,
                                'Year': yr,
                                'Value': ydata['hourly_values'][hour - 1],
                                **comp
                            })
                        # Annual total
                        timeseries_data.append({
                            'Sector': sector.name,
                            'Profile': pid,
                            'Hour': 'Annual Total',
                            'Year': yr,
                            'Value': ydata['annual_energy'],
                            **comp
                        })
            # Write to Excel
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                if metadata:
                    pd.DataFrame(metadata).to_excel(writer, sheet_name="Metadata", index=False)
                if timeseries_data:
                    df = pd.DataFrame(timeseries_data)
                    self._write_large_excel(df, writer, "Timeseries")
        # Parallel execution
        with ThreadPoolExecutor(max_workers=min(4, os.cpu_count())) as executor:
            list(executor.map(process_region, self.data.regions))

    def _write_large_excel(self, df, writer, base_sheet_name):
        """Modified writer that handles unsorted data"""
        max_rows = 1_000_000
        chunks = (len(df) // max_rows) + 1
        for i in range(chunks):
            chunk = df.iloc[i * max_rows: (i + 1) * max_rows]
            sheet_name = f"{base_sheet_name}_part{i + 1}" if chunks > 1 else base_sheet_name
            # Ensure header only on first chunk
            chunk.to_excel(
                writer,
                sheet_name=sheet_name[:31],
                index=False,
                header=(i == 0),
                startrow=0 if i == 0 else 1
            )

    def _write_ue_sector_data(self):
        """Handle sector-level UE data writing"""
        for sector_name, dfs in self.ue_sector_data.items():
            if dfs:
                combined = pd.concat(dfs, ignore_index=True)
                file_path = self.output_path / f"UE_{sector_name}.xlsx"
                with pd.ExcelWriter(file_path) as writer:
                    combined.to_excel(writer, sheet_name="UE_all")
                    combined.groupby(['UE_Type', "Temp_level", "Region"]).sum(numeric_only=True).to_excel(
                        writer, sheet_name="Aggregated_by_Sector_per_Region")
                    combined.groupby(['UE_Type', "Temp_level", 'Subsector', 'Technology']).sum(
                        numeric_only=True).to_excel(
                        writer, sheet_name="Aggregated_by_Technology")
                    combined.groupby(['UE_Type', "Temp_level", 'Subsector']).sum(numeric_only=True).to_excel(
                        writer, sheet_name="Aggregated_by_Subsector")
                    combined.groupby(['UE_Type', "Temp_level", 'Sector']).sum(numeric_only=True).to_excel(
                        writer, sheet_name="Aggregated_by_Sector")

    def _write_fe_sector_data(self):
        """Handle sector-level UE data writing"""
        for sector_name, dfs in self.fe_sector_data.items():
            if dfs:
                combined = pd.concat(dfs, ignore_index=True)
                column_order = ["Region", 'Subsector',"Technology", "UE_Type", "FE_Type", "Temp_level", "Subtech",
                                "Drive"] + \
                               [col for col in combined.columns if
                                col not in ["Region", 'Subsector', "Technology", "UE_Type", "FE_Type",
                                            "Temp_level",
                                            "Subtech", "Drive"]]
                combined =combined[column_order]
                file_path = self.output_path / f"FE_{sector_name}.xlsx"
                with pd.ExcelWriter(file_path) as writer:
                    combined.to_excel(writer, sheet_name="FE_all")
                    combined.groupby(["FE_Type", 'UE_Type', "Temp_level", "Region"]).sum(numeric_only=True).to_excel(
                        writer, sheet_name="Aggregated_by_Sector_per_Region")
                    combined.groupby(["FE_Type", 'UE_Type',"Temp_level", 'Subsector', 'Technology']).sum(
                        numeric_only=True).to_excel(
                        writer, sheet_name="Aggregated_by_Technology")
                    combined.groupby(["FE_Type", 'UE_Type', "Temp_level", 'Subsector']).sum(numeric_only=True).to_excel(
                        writer, sheet_name="Aggregated_by_Subsector")
                    combined.groupby(["FE_Type", 'UE_Type', "Temp_level", 'Sector']).sum(numeric_only=True).to_excel(
                        writer, sheet_name="Aggregated_by_Sector")

    def _write_diagrams(self):
        """Generate and save Sankey diagrams"""
        # Prepare data
        plot_data_preparer = GraphDataPreparer(self.data)
        plot_data = plot_data_preparer.prepare_data()
        # Create visualizations
        visualizer = Visualizer(plot_data)
        visualizer.create_interactive_dashboard()