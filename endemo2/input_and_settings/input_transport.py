from pathlib import Path

import pandas as pd

from endemo2.data_structures.containers import Datapoint
from endemo2.data_structures.conversions_unit import Unit, convert
from endemo2.data_structures.enumerations import TransportModal
from endemo2.data_structures.prediction_models import Coef
from endemo2.input_and_settings.control_parameters import ControlParameters
from endemo2 import utility as uty


class TransportInput:
    """
    CtsInput denoted input that is read from the "input/industry" folder.

    :param ControlParameters ctrl: The control parameters object.
    :param Path traffic_path: The path to the input files for the CTS sector.
    """

    tra_person_modal_split_groups = {
        TransportModal.road_rail: [TransportModal.car, TransportModal.bus, TransportModal.rail]
    }
    tra_freight_modal_split_groups = {
        TransportModal.road_rail_ship: [TransportModal.road, TransportModal.rail, TransportModal.ship]
    }

    def __init__(self, ctrl: ControlParameters, traffic_path: Path):

        ex_person_traffic = pd.ExcelFile(traffic_path / "Persontraffic.xlsx")
        ex_freight_traffic = pd.ExcelFile(traffic_path / "Freighttraffic.xlsx")

        # read person kilometres
        dict_df_person_km = dict[TransportModal, (Unit, str, pd.DataFrame)]()
        dict_df_person_km[TransportModal.road_rail] = Unit.Billion, "Mrd. pkm", \
            pd.read_excel(ex_person_traffic, sheet_name="Personkm_road_rail")
        dict_df_person_km[TransportModal.flight] = Unit.Million, "Mil. pkm", \
            pd.read_excel(ex_person_traffic, sheet_name="Passengerkm_flight")
        self.person_km = self.read_specific_km(ctrl, dict_df_person_km, desired_unit=Unit.Million)

        # read person modal splits
        dict_df_person_modal_split = dict[TransportModal, pd.DataFrame]()
        dict_df_person_modal_split[TransportModal.car] = \
            pd.read_excel(ex_person_traffic, sheet_name="ModalSplit_car_his")
        dict_df_person_modal_split[TransportModal.rail] = \
            pd.read_excel(ex_person_traffic, sheet_name="ModalSplit_rail_his")
        dict_df_person_modal_split[TransportModal.bus] = \
            pd.read_excel(ex_person_traffic, sheet_name="ModalSplit_bus_his")
        self.person_modal_split = self.read_modal_split_sheets(ctrl, dict_df_person_modal_split)

        # read person user defined split
        # todo

        # read freight kilometres
        dict_df_freight_km = dict[TransportModal, (Unit, str, pd.DataFrame)]()
        dict_df_freight_km[TransportModal.road_rail_ship] = Unit.Million, "Mil. tkm", \
            pd.read_excel(ex_freight_traffic, sheet_name="Tonnekm_road_rail_ship")
        dict_df_freight_km[TransportModal.flight] = Unit.Standard, "tonne_km", \
            pd.read_excel(ex_freight_traffic, sheet_name="Tonnekm_flight")
        self.freight_km = self.read_specific_km(ctrl, dict_df_freight_km, desired_unit=Unit.Million, reference_year=2018)

        # read freight modal splits
        dict_df_freight_modal_split = dict[TransportModal, pd.DataFrame]()
        dict_df_freight_modal_split[TransportModal.road] = \
            pd.read_excel(ex_freight_traffic, sheet_name="ModalSplit_road_his")
        dict_df_freight_modal_split[TransportModal.rail] = \
            pd.read_excel(ex_freight_traffic, sheet_name="ModalSplit_rail_his")
        dict_df_freight_modal_split[TransportModal.ship] = \
            pd.read_excel(ex_freight_traffic, sheet_name="ModalSplit_ship_his")
        self.freight_modal_split = self.read_modal_split_sheets(ctrl, dict_df_freight_modal_split)

        # read freight user defined split
        # todo

    @classmethod
    def read_specific_km(cls, ctrl, dict_specific_km: dict[TransportModal, (Unit, pd.DataFrame)], desired_unit: Unit,
                         reference_year: int = None) -> dict[str, dict[TransportModal, Coef]]:
        dict_res = dict[str, dict[TransportModal, Coef]]()

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

                coef = Coef()
                coef.set_exp(Datapoint(year, pkm), 0.0)

                if country_name not in dict_res.keys():
                    dict_res[country_name] = dict[TransportModal]()
                dict_res[country_name][TransportModal.road_rail] = coef

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


