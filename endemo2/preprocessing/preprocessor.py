"""
This module contains all things shared by the different preprocessing stages.
"""
from endemo2.data_structures.enumerations import SectorIdentifier
from endemo2.preprocessing.preproccessing_step_two import GroupManager
from endemo2.input_and_settings.input_manager import InputManager
from endemo2.preprocessing import preprocessing_step_one as pp1


class Preprocessor:
    """
    The preprocessor controls the execution of the different preprocessing stages.
    """

    def __init__(self, input_manager: InputManager):

        self.countries_pp = dict[str, pp1.CountryPreprocessed]()

        # preprocess stage 1
        for country_name in input_manager.ctrl.general_settings.active_countries:
            self.countries_pp[country_name] = pp1.CountryPreprocessed(country_name, input_manager)
            
        # preprocess stage 2
        if SectorIdentifier.INDUSTRY in input_manager.ctrl.general_settings.get_active_sectors():
            self.group_manager = GroupManager(input_manager, self.countries_pp)

