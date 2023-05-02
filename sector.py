class Sector:
    def calculate(self) -> int:
        # calculate useful energy demand of sector
        # has to be overwritten by child class
        raise NotImplementedError
