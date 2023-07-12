import random
import string
from typing import Any, Dict, List, cast

import streamlit as st
from deta import Deta
from deta import _Base as DetaBase

from . import data_def
from .const import DataDefsCollectionDict, DataSample


def connect_to_db(secret_env_var_name: str, db_name: str) -> DetaBase:
    deta = Deta(st.secrets[secret_env_var_name])
    return deta.Base(db_name)


def get_all_sample_keys(db: DetaBase) -> List[str]:
    # TODO: This is inefficient. Needs to be improved.
    all_data = db.fetch()
    # if all_data.count == 0:
    #     raise RuntimeError("No data found")
    if all_data.last is not None:
        raise RuntimeError("Too many data rows. Supported max rows is 1000.")
    return [example["key"] for example in all_data.items]


def generate_new_sample_key():
    length = 12
    characters = string.ascii_lowercase + string.digits
    return "".join(random.choice(characters) for _ in range(length))  # nosec: B311


def _sort_fields(sort_key: List[str], fields: Dict[str, Dict]) -> Dict[str, Dict]:
    # Sort the fields in data_defs order (the fields in the DB are in random order).
    sorted_fields: Dict[str, Any] = dict()
    for key in sort_key:
        sorted_fields[key] = fields[key]
    return sorted_fields


def _sort_fields_in_array(sort_key: List[str], array_of_fields: List[Dict[str, Dict]]) -> List[Dict[str, Dict]]:
    sorted_array_of_fields: List[Dict[str, Dict]] = []
    for fields in array_of_fields:
        sorted_array_of_fields.append(_sort_fields(sort_key=sort_key, fields=fields))
    return sorted_array_of_fields


def get_sample(key: str, db: DetaBase, data_defs: "data_def.DataDefsCollection") -> DataSample:
    raw_data = cast(DataDefsCollectionDict, db.get(key))

    static = _sort_fields(sort_key=list(data_defs.static.keys()), fields=raw_data["static"])
    temporal: Any = _sort_fields_in_array(
        sort_key=list(data_defs.temporal.keys()), array_of_fields=raw_data["temporal"]
    )
    event: Any = _sort_fields_in_array(sort_key=list(data_defs.event.keys()), array_of_fields=raw_data["event"])

    return DataSample(static=static, temporal=temporal, event=event)


def add_empty_sample(db: DetaBase, key: str, data_defs: "data_def.DataDefsCollection"):
    static = data_def.get_default(data_defs=data_defs.static) if data_defs.static else {}
    temporal: Any = [data_def.get_default(data_defs=data_defs.temporal)] if data_defs.temporal else []
    event: Any = [data_def.get_default(data_defs=data_defs.event)] if data_defs.event else []

    data_sample = dict(DataSample(static=static, temporal=temporal, event=event))

    print(f"Adding new sample to db.\nkey: {key}\ndata:\n{data_sample}")
    db.put(data_sample, key=key)


def delete_sample(db: DetaBase, key: str):
    print(f"Deleting sample from db.\nkey: {key}")
    db.delete(key=key)


def update_sample(db: DetaBase, key: str, data_sample: DataSample):
    print(f"Adding new sample to db.\nkey: {key}\ndata:\n{data_sample}")
    db.put(dict(data_sample), key=key)
