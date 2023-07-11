from typing import NamedTuple

from typing_extensions import Literal

ExampleStates = Literal["show", "add", "edit", "delete"]
ExampleEditStates = Literal["edit_static", "edit_temporal", "edit_event"]
ExampleAddStates = Literal["edit_static", "edit_temporal", "edit_event"]
ExampleDeleteStates = Literal["edit_static", "edit_temporal", "edit_event"]


class SessionStateKeys(NamedTuple):
    cur_example: str = "cur_example"
    example_state: str = "example_state"
    example_edit_state: str = "example_edit_state"
    data_static_field_prefix: str = "data_static"
    data_temporal_field_prefix: str = "data_temporal"
    data_event_field_prefix: str = "data_event"


class Defaults(NamedTuple):
    data_dir: str = "./data/"
    assets_dir: str = "./assets/"
    logo: str = "TemporAI_Clinic_Logo.png"
    icon: str = "TemporAI_Clinic_Logo_Icon.ico"


DEFAULTS = Defaults()
STATE_KEYS = SessionStateKeys()
