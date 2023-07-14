import os
from typing import Any, Dict, List, NamedTuple

from pydantic import BaseModel
from typing_extensions import Literal

DataModality = Literal["static", "temporal", "event"]

InteractionState = Literal[
    "showing",
    "adding_sample",
    "deleting_sample",
    "editing_static_data",
    "editing_temporal_data",
    "editing_event_data",
    "adding_temporal_data",
    "adding_event_data",
    "deleting_temporal_data",
    "deleting_event_data",
]

DataDefsCollectionDict = Dict[DataModality, Any]  # Union[Dict[str, Dict], List[Dict[str, Dict]]]


class SessionStateKeys(NamedTuple):
    current_sample: str = "current_sample"
    current_timestep: str = "current_timestep"
    interaction_state: str = "interaction_state"
    # Field prefixes:
    data_field_prefix: str = "data"
    time_index_prefix: str = "time_index"


ASSETS_PATH = os.path.realpath(os.path.dirname(__file__))


class Defaults(NamedTuple):
    data_dir: str = "./data/"
    assets_dir: str = "./assets/"
    logo: str = os.path.join(ASSETS_PATH, "TemporAI_Clinic_Logo.png")
    icon: str = os.path.join(ASSETS_PATH, "TemporAI_Clinic_Logo_Icon.ico")
    # Special fields:
    time_index_field: str = "time_index"
    # Streamlit component keys:
    key_sample_selector: str = "sample_selector"
    key_edit_form_static: str = "edit_form_static"
    key_edit_form_temporal: str = "edit_form_static"


DEFAULTS = Defaults()
STATE_KEYS = SessionStateKeys()


class DataSample(BaseModel):
    static: Dict[str, Any]
    temporal: List[Dict[str, Any]]
    event: List[Dict[str, Any]]
