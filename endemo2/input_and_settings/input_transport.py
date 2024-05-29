from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from endemo2.data_structures.containers import Datapoint, Demand
from endemo2.data_structures.conversions_string import map_tra_modal_to_string
from endemo2.data_structures.conversions_unit import Unit, convert
from endemo2.data_structures.enumerations import TransportModal, TrafficType, DemandType
from endemo2.input_and_settings.control_parameters import ControlParameters
from endemo2 import utility as uty


class TransportInput:
    """
    CtsInput denoted input that is read from the "input/industry" folder.

    :param ControlParameters ctrl: The control parameters object.
    :param Path traffic_path: The path to the input files for the CTS sector.

    :ivar dict[TrafficType, dict[str, dict[TransportModal, Datapoint]]] kilometres: The number of (million) kilometres
        travelled in one year by one unit of traffic type.
        Is of form {traffic_type -> country_name -> transport_modal -> datapoint}.
    :ivar dict[TrafficType, dict[str, dict[TransportModal, [Datapoint]]]] modal_split_his: The historical data on model
        splits for each traffic type.
    :ivar dict[TrafficType, dict[str, dict[TransportModal, [Datapoint]]]] modal_split_user_def: The user defined model
        split points for each traffic type.

    :ivar dict[TrafficType, dict[TransportModal, Demand]] modal_ukm_energy_consumption: The energy consumption for each
        pkm or tkm and each transport modal.
    :ivar dict[TrafficType, dict[TransportModal, dict[DemandType, [Datapoint]]]] demand_split_reference:
        How demand should be split over time. Reference from real data.
    :ivar dict[TrafficType, dict[TransportModal, dict[DemandType, [Datapoint]]]] demand_split_user:
    How demand should be split over time. Defined by user.
    """

    tra_traffic_types = [TrafficType.PERSON, TrafficType.FREIGHT]

    tra_modal_lists = {
        TrafficType.PERSON: [
            TransportModal.car,
            TransportModal.bus,
            TransportModal.rail,
            TransportModal.flight
        ],
        TrafficType.FREIGHT: [
            TransportModal.road,
            TransportModal.rail,
            TransportModal.ship,
            TransportModal.flight
        ]
    }

    tra_modal_split_groups = {
        TrafficType.PERSON: {
            TransportModal.road_rail: [TransportModal.car, TransportModal.bus, TransportModal.rail]
        },
        TrafficType.FREIGHT: {
            TransportModal.road_rail_ship: [TransportModal.road, TransportModal.rail, TransportModal.ship]
        }
    }

    def __init__(self, ctrl: ControlParameters, traffic_path: Path):

        ex_person_traffic = pd.ExcelFile(traffic_path / "Persontraffic.xlsx")
        ex_freight_traffic = pd.ExcelFile(traffic_path / "Freighttraffic.xlsx")
        ex_person_energy_sources = pd.ExcelFile(traffic_path / "Pt_FinalEnergySources.xlsx")
        ex_freight_energy_sources = pd.ExcelFile(traffic_path / "Ft_FinalEnergySources.xlsx")

        self.kilometres = dict[TrafficType, dict[str, dict[TransportModal, Datapoint]]]()
        self.modal_split_his = dict()
        self.modal_split_user_def = dict()

        # read person kilometres
        dict_df_person_km = dict[TransportModal, (Unit, str, pd.DataFrame)]()
        dict_df_person_km[TransportModal.road_rail] = Unit.Billion, "Mrd. pkm", \
            pd.read_excel(ex_person_traffic, sheet_name="Personkm_road_rail")
        dict_df_person_km[TransportModal.flight] = Unit.Million, "Mil. pkm", \
            pd.read_excel(ex_person_traffic, sheet_name="Passengerkm_flight")
        self.kilometres[TrafficType.PERSON] = self.read_specific_km(ctrl, dict_df_person_km, desired_unit=Unit.Standard)

        # read person modal splits
        dict_df_person_modal_split_his = dict[TransportModal, pd.DataFrame]()
        dict_df_person_modal_split_his[TransportModal.car] = \
            pd.read_excel(ex_person_traffic, sheet_name="ModalSplit_car_his")
        dict_df_person_modal_split_his[TransportModal.rail] = \
            pd.read_excel(ex_person_traffic, sheet_name="ModalSplit_rail_his")
        dict_df_person_modal_split_his[TransportModal.bus] = \
            pd.read_excel(ex_person_traffic, sheet_name="ModalSplit_bus_his")
        self.modal_split_his[TrafficType.PERSON] = self.read_modal_split_sheets(ctrl, dict_df_person_modal_split_his)

        # read person user defined split
        dict_df_person_modal_split_user = dict[TransportModal, pd.DataFrame]()
        dict_df_person_modal_split_his[TransportModal.car] = \
            pd.read_excel(ex_person_traffic, sheet_name="ModalSplit_car_user")
        dict_df_person_modal_split_his[TransportModal.rail] = \
            pd.read_excel(ex_person_traffic, sheet_name="ModalSplit_rail_user")
        dict_df_person_modal_split_his[TransportModal.bus] = \
            pd.read_excel(ex_person_traffic, sheet_name="ModalSplit_bus_user")
        self.modal_split_user_def[TrafficType.PERSON] = \
            self.read_modal_split_sheets(ctrl, dict_df_person_modal_split_user)

        # read freight kilometres
        dict_df_freight_km = dict[TransportModal, (Unit, str, pd.DataFrame)]()
        dict_df_freight_km[TransportModal.road_rail_ship] = Unit.Million, "Mil. tkm", \
            pd.read_excel(ex_freight_traffic, sheet_name="Tonnekm_road_rail_ship")
        dict_df_freight_km[TransportModal.flight] = Unit.Standard, "tonne_km", \
            pd.read_excel(ex_freight_traffic, sheet_name="Tonnekm_flight")
        self.kilometres[TrafficType.FREIGHT] = \
            self.read_specific_km(ctrl, dict_df_freight_km, desired_unit=Unit.Standard, reference_year=2018)

        # read freight modal splits
        dict_df_freight_modal_split_his = dict[TransportModal, pd.DataFrame]()
        dict_df_freight_modal_split_his[TransportModal.road] = \
            pd.read_excel(ex_freight_traffic, sheet_name="ModalSplit_road_his")
        dict_df_freight_modal_split_his[TransportModal.rail] = \
            pd.read_excel(ex_freight_traffic, sheet_name="ModalSplit_rail_his")
        dict_df_freight_modal_split_his[TransportModal.ship] = \
            pd.read_excel(ex_freight_traffic, sheet_name="ModalSplit_ship_his")
        self.modal_split_his[TrafficType.FREIGHT] = \
            self.read_modal_split_sheets(ctrl, dict_df_freight_modal_split_his)

        # read freight user defined split
        dict_df_freight_modal_split_user = dict[TransportModal, pd.DataFrame]()
        dict_df_freight_modal_split_user[TransportModal.road] = \
            pd.read_excel(ex_freight_traffic, sheet_name="ModalSplit_road_user")
        dict_df_freight_modal_split_user[TransportModal.rail] = \
            pd.read_excel(ex_freight_traffic, sheet_name="ModalSplit_rail_user")
        dict_df_freight_modal_split_user[TransportModal.ship] = \
            pd.read_excel(ex_freight_traffic, sheet_name="ModalSplit_ship_user")
        self.modal_split_user_def[TrafficType.FREIGHT] = \
            self.read_modal_split_sheets(ctrl, dict_df_person_modal_split_user)

        # read transport demand conversion input
        self.modal_ukm_energy_consumption = dict[TrafficType, dict[TransportModal, Demand]]()
        self.demand_split_reference = dict[TrafficType, dict[TransportModal, dict[DemandType, [Datapoint]]]]()
        self.demand_split_user = dict[TrafficType, dict[TransportModal, dict[DemandType, [Datapoint]]]]()

        # read final energy sources
        df_energy_per_source_person = pd.read_excel(ex_person_energy_sources, sheet_name="EnergyperSource")
        df_energy_per_source_freight = pd.read_excel(ex_freight_energy_sources, sheet_name="EnergyperSource")

        self.modal_ukm_energy_consumption[TrafficType.PERSON] = \
            TransportInput.read_energy_per_source(TrafficType.PERSON, df_energy_per_source_person)
        self.modal_ukm_energy_consumption[TrafficType.FREIGHT] = \
            TransportInput.read_energy_per_source(TrafficType.FREIGHT, df_energy_per_source_freight)

        # read percentages
        self.modal_energy_split_ref = \
            dict[TrafficType, dict[TransportModal, dict[DemandType, dict[str, [Datapoint]]]]]()
        self.modal_energy_split_user = \
            dict[TrafficType, dict[TransportModal, dict[DemandType, dict[str, [Datapoint]]]]]()

        for traffic_type, modals in TransportInput.tra_modal_lists.items():
            for modal_id in modals:
                str_modal = map_tra_modal_to_string[modal_id]

                sheet_name_elec_ref = "elec_" + str_modal + "_ref"
                sheet_name_elec_user = "elec_" + str_modal + "_user"

                sheet_name_h2_ref = "h2_" + str_modal + "_ref"
                sheet_name_h2_user = "h2_" + str_modal + "_user"

                ex_energy_sources = None
                if traffic_type == TrafficType.PERSON:
                    ex_energy_sources = ex_person_energy_sources
                elif traffic_type == TrafficType.FREIGHT:
                    ex_energy_sources = ex_freight_energy_sources

                df_elec_ref = pd.read_excel(ex_energy_sources, sheet_name=sheet_name_elec_ref)
                df_elec_user = pd.read_excel(ex_energy_sources, sheet_name=sheet_name_elec_user)

                df_h2_ref = pd.read_excel(ex_energy_sources, sheet_name=sheet_name_h2_ref)
                df_h2_user = pd.read_excel(ex_energy_sources, sheet_name=sheet_name_h2_user)

                if traffic_type not in self.modal_energy_split_ref.keys():
                    self.modal_energy_split_ref[traffic_type] = \
                        dict[TransportModal, dict[DemandType, dict[str, [Datapoint]]]]()
                if traffic_type not in self.modal_energy_split_user.keys():
                    self.modal_energy_split_user[traffic_type] = \
                        dict[TransportModal, dict[DemandType, dict[str, [Datapoint]]]]()
                if modal_id not in self.modal_energy_split_ref[traffic_type].keys():
                    self.modal_energy_split_ref[traffic_type][modal_id] = dict[DemandType, dict[str, [Datapoint]]]()
                if modal_id not in self.modal_energy_split_user[traffic_type].keys():
                    self.modal_energy_split_user[traffic_type][modal_id] = dict[DemandType, dict[str, [Datapoint]]]()

                self.modal_energy_split_ref[traffic_type][modal_id][DemandType.ELECTRICITY] = \
                    TransportInput.read_timeline_perc(ctrl, df_elec_ref)
                self.modal_energy_split_ref[traffic_type][modal_id][DemandType.HYDROGEN] = \
                    TransportInput.read_timeline_perc(ctrl, df_h2_ref)
                self.modal_energy_split_user[traffic_type][modal_id][DemandType.ELECTRICITY] = \
                    TransportInput.read_timeline_perc(ctrl, df_elec_user)
                self.modal_energy_split_user[traffic_type][modal_id][DemandType.HYDROGEN] = \
                    TransportInput.read_timeline_perc(ctrl, df_h2_user)

        # read load profile
        if ctrl.general_settings.toggle_hourly_forecast:
            ex_load_profile = pd.ExcelFile(traffic_path / "tra_timeseries.xlsx")
            df_load_profile = pd.read_excel(ex_load_profile, sheet_name="timeseries_LoadingProfile")
            df_load_profile_ukm = pd.read_excel(ex_load_profile, sheet_name="timeseries_MobilityProfile")

            self.load_profile = dict[(TrafficType, TransportModal, DemandType), Any]()
            self.load_profile[(TrafficType.FREIGHT, TransportModal.road, DemandType.ELECTRICITY)] \
                = np.array(df_load_profile["ft.road.elec"][1:])
            self.load_profile[(TrafficType.FREIGHT, TransportModal.road, DemandType.HYDROGEN)] \
                = np.array(df_load_profile["ft.road.hydrogen"][1:])
            self.load_profile[(TrafficType.PERSON, TransportModal.road, DemandType.ELECTRICITY)] \
                = np.array(df_load_profile["pt.road.elec"][1:])
            self.load_profile[(TrafficType.PERSON, TransportModal.road, DemandType.HYDROGEN)] \
                = np.array(df_load_profile["pt.road.hydrogen"][1:])
            self.load_profile[(TrafficType.FREIGHT, TransportModal.rail, DemandType.ELECTRICITY)] \
                = np.array(df_load_profile["ft.rail.elec"][1:])
            self.load_profile[(TrafficType.FREIGHT, TransportModal.rail, DemandType.HYDROGEN)] \
                = np.array(df_load_profile["ft.rail.hydrogen"][1:])
            self.load_profile[(TrafficType.PERSON, TransportModal.rail, DemandType.ELECTRICITY)] \
                = np.array(df_load_profile["pt.rail.elec"][1:])
            self.load_profile[(TrafficType.PERSON, TransportModal.rail, DemandType.HYDROGEN)] \
                = np.array(df_load_profile["pt.rail.hydrogen"][1:])
            self.load_profile[(TrafficType.FREIGHT, TransportModal.ship, DemandType.ELECTRICITY)] \
                = np.array(df_load_profile["ship.elec"][1:])
            self.load_profile[(TrafficType.FREIGHT, TransportModal.ship, DemandType.HYDROGEN)] \
                = np.array(df_load_profile["ship.hydrogen"][1:])
            self.load_profile[(TrafficType.BOTH, TransportModal.flight, DemandType.ELECTRICITY)] \
                = np.array(df_load_profile["flight.elec"][1:])
            self.load_profile[(TrafficType.BOTH, TransportModal.flight, DemandType.HYDROGEN)] \
                = np.array(df_load_profile["flight.hydrogen"][1:])

            self.load_profile_ukm = dict[(TrafficType, TransportModal, DemandType), Any]()
            self.load_profile_ukm[(TrafficType.PERSON, TransportModal.rail)] \
                = np.array(df_load_profile_ukm["pt.rail"][1:])
            self.load_profile_ukm[(TrafficType.PERSON, TransportModal.car)] \
                = np.array(df_load_profile_ukm["pt.car"][1:])
            self.load_profile_ukm[(TrafficType.PERSON, TransportModal.bus)] \
                = np.array(df_load_profile_ukm["pt.bus"][1:])
            self.load_profile_ukm[(TrafficType.PERSON, TransportModal.flight)] \
                = np.array(df_load_profile_ukm["pt.flight"][1:])
            self.load_profile_ukm[(TrafficType.PERSON, TransportModal.ship)] \
                = np.array(df_load_profile_ukm["pt.ship"][1:])
            self.load_profile_ukm[(TrafficType.FREIGHT, TransportModal.rail)] \
                = np.array(df_load_profile_ukm["ft.rail"][1:])
            self.load_profile_ukm[(TrafficType.FREIGHT, TransportModal.road)] \
                = np.array(df_load_profile_ukm["ft.road"][1:])
            self.load_profile_ukm[(TrafficType.FREIGHT, TransportModal.flight)] \
                = np.array(df_load_profile_ukm["ft.flight"][1:])
            self.load_profile_ukm[(TrafficType.FREIGHT, TransportModal.ship)] \
                = np.array(df_load_profile_ukm["ft.ship"][1:])
        else:
            self.load_profile = None
            self.load_profile_ukm = None


    @classmethod
    def read_timeline_perc(cls, ctrl, df) -> dict[str, [Datapoint]]:
        """ Read a simple timeline of percentage values. Convert to %/100. """
        dict_res = dict[str, [Datapoint]]()

        years = df.columns[1:]
        for _, row in df.iterrows():
            country_name = row["Country"]
            if country_name not in ctrl.general_settings.active_countries:
                # skip inactive countries and invalid entries
                continue

            data = row[1:]
            his_data = uty.float_lists_to_datapoint_list(years, data)
            his_data = uty.filter_out_nan_and_inf(his_data)
            his_data = uty.map_data_y(his_data, lambda x: x / 100)
            dict_res[country_name] = his_data

        return dict_res

    @classmethod
    def read_specific_km(cls, ctrl, dict_specific_km: dict[TransportModal, (Unit, pd.DataFrame)], desired_unit: Unit,
                         reference_year: int = None) -> dict[str, dict[TransportModal, Datapoint]]:
        """ Read the specific kilometers and convert unit to desired unit.  """
        dict_res = dict[str, dict[TransportModal, Datapoint]]()

        for modal_id, (curr_unit, value_column, df_specific_km) in dict_specific_km.items():
            for _, row in df_specific_km.iterrows():
                country_name = row["Country"]
                if country_name not in ctrl.general_settings.active_countries:
                    # skip inactive countries and invalid entries
                    continue

                if reference_year is not None:
                    year = reference_year
                else:
                    year = int(row["year"])

                pkm = convert(curr_unit, desired_unit, row[value_column])

                if country_name not in dict_res.keys():
                    dict_res[country_name] = dict[TransportModal]()
                dict_res[country_name][modal_id] = Datapoint(year, pkm)

        return dict_res

    @classmethod
    def read_modal_split_sheets(cls, ctrl, dict_df_modal_split: dict[TransportModal, pd.DataFrame]) \
            -> dict[str, dict[TransportModal, [Datapoint]]]:
        """ Reads the modal split sheets. """

        dict_res = dict[str, dict[TransportModal, [Datapoint]]]()

        for modal_id, df_sheet in dict_df_modal_split.items():
            years = df_sheet.columns[1:]
            for _, row in df_sheet.iterrows():
                country_name = row["Country"]
                if country_name not in ctrl.general_settings.active_countries:
                    # skip inactive countries and invalid entries
                    continue

                data = row[1:]
                his_data = uty.float_lists_to_datapoint_list(years, data)

                if country_name not in dict_res.keys():
                    dict_res[country_name] = dict[TransportModal]()
                dict_res[country_name][modal_id] = his_data

        return dict_res

    @classmethod
    def read_energy_per_source(cls, traffic_type, df_energy_per_source) -> dict[TransportModal, Demand]:
        """ Reads the energy per source sheet. """
        result = dict[TransportModal, Demand]()

        str_energy_consumption_column_name = ""
        if traffic_type == TrafficType.PERSON:
            str_energy_consumption_column_name = "Energy consumption MJ/pkm"
        elif traffic_type == TrafficType.FREIGHT:
            str_energy_consumption_column_name = "Energy consumption MJ/tkm"

        for modal_id in TransportInput.tra_modal_lists[traffic_type]:
            str_modal = map_tra_modal_to_string[modal_id]
            electricity = \
                df_energy_per_source[
                    df_energy_per_source[
                        str_energy_consumption_column_name] == "Electricity"].get(str_modal).iloc[0]
            hydrogen = \
                df_energy_per_source[
                    df_energy_per_source[
                        str_energy_consumption_column_name] == "Hydrogen"].get(str_modal).iloc[0]

            fuel = df_energy_per_source[
                df_energy_per_source[
                    str_energy_consumption_column_name] == "Diesel"].get(str_modal).iloc[0]
            if modal_id == TransportModal.flight:
                fuel = df_energy_per_source[
                    df_energy_per_source[
                        str_energy_consumption_column_name] == "Kerosine"].get(str_modal).iloc[0]

            electricity = convert(Unit.MJ, Unit.kWh, electricity)
            hydrogen = convert(Unit.MJ, Unit.kWh, hydrogen)
            fuel = convert(Unit.MJ, Unit.kWh, fuel)

            result[modal_id] = Demand(electricity=electricity, hydrogen=hydrogen, fuel=fuel)

        return result
