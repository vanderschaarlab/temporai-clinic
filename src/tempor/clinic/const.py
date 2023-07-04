from typing import NamedTuple


class Defaults(NamedTuple):
    data_dir: str = "./data/"
    assets_dir: str = "./assets/"
    logo: str = "TemporAI_Clinic_Logo.png"


DEFAULTS = Defaults()
