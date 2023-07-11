import random
import string
from typing import TYPE_CHECKING, Any, Dict, List, cast

import streamlit as st
from deta import Deta
from deta import _Base as DetaBase

if TYPE_CHECKING:
    from .data_def import DataDef


def connect_to_db(secret_env_var_name: str, db_name: str) -> DetaBase:
    deta = Deta(st.secrets[secret_env_var_name])
    return deta.Base(db_name)


def get_all_sample_keys(db: DetaBase) -> List[str]:
    # TODO: This is inefficient. Needs to be improved.
    all_data = db.fetch()
    if all_data.count == 0:
        raise RuntimeError("No data found")
    if all_data.last is not None:
        raise RuntimeError("Too many data rows. Supported max rows is 1000.")
    return [example["key"] for example in all_data.items]


def generate_new_sample_key():
    length = 12
    characters = string.ascii_lowercase + string.digits
    return "".join(random.choice(characters) for _ in range(length))  # nosec: B311


def get_sample(key: str, db: DetaBase, data_defs: Dict[str, "DataDef"]) -> Dict[str, Any]:
    raw_data = cast(Dict[str, Any], db.get(key))

    # Sort the fields in data_defs order (the fields in the DB are in random order):
    sorted_data: Dict[str, Any] = dict()
    for key in data_defs.keys():
        sorted_data[key] = raw_data[key]

    return sorted_data


def add_sample(db: DetaBase, key: str, data_defs: Dict[str, "DataDef"]):
    sample_data = dict()
    for field_name, data_def in data_defs.items():
        sample_data[field_name] = data_def.get_default_value()

    print(f"Adding new sample to db.\nkey: {key}\ndata:\n{sample_data}")
    db.put(sample_data, key=key)


def delete_sample(db: DetaBase, key: str):
    print(f"Deleting sample from db.\nkey: {key}")
    db.delete(key=key)


def update_sample(db: DetaBase, key: str, sample_data: Dict[str, Any]):
    print(f"Adding new sample to db.\nkey: {key}\ndata:\n{sample_data}")
    db.put(sample_data, key=key)
