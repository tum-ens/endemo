from pathlib import Path

import pandas as pd

from endemo2.data_structures.containers import Datapoint
from endemo2.data_structures.conversions_unit import Unit, convert
from endemo2.data_structures.enumerations import TransportModal, TrafficType
from endemo2.input_and_settings.control_parameters import ControlParameters
from endemo2 import utility as uty


class TransportInput:
    """
    CtsInput denoted input that is read from the "input/industry" folder.

    :param ControlParameters ctrl: The control parameters object.
    :param Path traffic_path: The path to the input files for the CTS sector.

    :ivar dict[TrafficType, dict[str, dict[TransportModal, Datapoint]]] specific_km: The number of (million) kilometres
        travelled in one year by one unit of traffic type.
        Is of form {traffic_type -> country_name -> transport_modal -> datapoint}.
    :ivar dict[TrafficType, dict[str, dict[TransportModal, [Datapoint]]]] modal_split_his: The historical data on model
        splits for each traffic type.
    :ivar dict[TrafficType, dict[str, dict[TransportModal, [Datapoint]]]] modal_split_user_def: The user defined model
        split points for each traffic type.
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

    def __init__(self, ctrl: ControlParameters, traffic_path: Path, input_generated_path: Path):

        ex_person_traffic = pd.ExcelFile(traffic_path / "Persontraffic.xlsx")
        ex_freight_traffic = pd.ExcelFile(traffic_path / "Freighttraffic.xlsx")

        # read freight rail_road_ship tons from model-generated input
        ref_year = ctrl.transport_settings.ind_production_reference_year
        ex_ind_product_amount = \
            pd.ExcelFile(input_generated_path / ("ind_product_amount_forecast_" + str(ref_year) + ".xlsx"))

        self.kilometres = dict[TrafficType, dict[str, dict[TransportModal, Datapoint]]]()
        self.modal_split_his = dict()
        self.modal_split_user_def = dict()

        # read person kilometres
        dict_df_person_km = dict[TransportModal, (Unit, str, pd.DataFrame)]()
        dict_df_person_km[TransportModal.road_rail] = Unit.Billion, "Mrd. pkm", \
            pd.read_excel(ex_person_traffic, sheet_name="Personkm_road_rail")
        dict_df_person_km[TransportModal.flight] = Unit.Million, "Mil. pkm", \
            pd.read_excel(ex_person_traffic, sheet_name="Passengerkm_flight")
        self.kilometres[TrafficType.PERSON] = self.read_specific_km(ctrl, dict_df_person_km, desired_unit=Unit.Million)

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
        dict_df_freight_km[TransportModal.road_rail_ship] = Unit.kilo, "Amount [kt]", \
            pd.read_excel(ex_ind_product_amount, sheet_name="IND")
        self.kilometres[TrafficType.FREIGHT] = \
            self.read_specific_km(ctrl, dict_df_freight_km, desired_unit=Unit.Million, reference_year=2018)

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


    @classmethod
    def read_specific_km(cls, ctrl, dict_specific_km: dict[TransportModal, (Unit, pd.DataFrame)], desired_unit: Unit,
                         reference_year: int = None) -> dict[str, dict[TransportModal, Datapoint]]:
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
                    year = row["year"]

                pkm = convert(curr_unit, desired_unit, row[value_column])

                if country_name not in dict_res.keys():
                    dict_res[country_name] = dict[TransportModal]()
                dict_res[country_name][TransportModal.road_rail] = Datapoint(year, pkm)

        return dict_res

    @classmethod
    def read_modal_split_sheets(cls, ctrl, dict_df_modal_split: dict[TransportModal, pd.DataFrame]) \
            -> dict[str, dict[TransportModal, [Datapoint]]]:

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


