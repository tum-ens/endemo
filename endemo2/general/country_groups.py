import enum


class CountryGroupType(enum.Enum):
    JOINED = 0
    JOINED_DIVERSIFIED = 1

class CountryGroup:
    def __init__(self, group_type: CountryGroupType, included_countries: [str]):
        self.type = group_type
        self.included_countries = included_countries


class CountryGroupJoined(CountryGroup):
    def __init__(self):
        self.type = CountryGroupType.JOINED


class CountryGroupJoinedDiversified(CountryGroup):
    def __init__(self):
        self.type = CountryGroupType.JOINED_DIVERSIFIED

    def calc_delta_regression(self):
        pass


