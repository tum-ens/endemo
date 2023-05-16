import pandas as pd

from product import Product
from sector import Sector


class Industry(Sector):
    # static part of class start----------------------------------------
    products = dict()
    product_hierarchy = dict()

    @classmethod
    def __init__(cls, input_path):
        Industry.input_path = input_path

    @classmethod
    def load_production_data(cls, product_names, data_access_spec):

        for product_name in product_names:
            excel = data_access_spec[product_name].sheet_transform(
                pd.read_excel(Industry.input_path / data_access_spec[product_name].file_name,
                              sheet_name=data_access_spec[product_name].sheet_name))
            print(product_name + str(excel))
            specific_demand = pd.read_excel(Industry.input_path / "Specific_Consumption.xlsx",
                              sheet_name=product_name)
            Industry.products[product_name] = Product(product_name, excel, specific_demand)
            Industry.add_to_hierarchy(product_name, Industry.products[product_name])

    @classmethod
    def add_to_hierarchy(cls, product_name: str, obj: Product):
        tag = ""
        spec = ""
        if "_" in product_name:
            name_hierarchy = product_name.split("_")
            tag = name_hierarchy[0]     # main name of product
            spec = name_hierarchy[1]    # either prim, sec or classic
        else:
            tag = product_name
            spec = ""

        if not tag in Industry.product_hierarchy:
            Industry.product_hierarchy[tag] = {spec: obj}
        else:
            Industry.product_hierarchy[tag][spec] = obj
        print(str(Industry.product_hierarchy))

    # static part of class end------------------------------------------
    # instantiated part of class start----------------------------------



    def calculate(self) -> int:
        # calculate industry sector
        print("Calculating industry sector...")
        pass
