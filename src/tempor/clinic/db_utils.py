import random
import string
from typing import TYPE_CHECKING, Any, Dict, List, cast

import streamlit as st
from deta import Deta
from deta import _Base as DetaBase

from .const import DataModality, DataSample

if TYPE_CHECKING:
    from .data_def import DataDef, DataDefsCollection


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


def _get_default(data_defs: Dict[str, "DataDef"]) -> Dict[str, Dict]:
    data_sample = dict()
    for field_name, data_def in data_defs.items():
        data_sample[field_name] = data_def.get_default_value()
    return data_sample


def get_sample(key: str, db: DetaBase, data_defs: "DataDefsCollection") -> DataSample:
    raw_data = cast(Dict[DataModality, Dict[str, Dict]], db.get(key))

    static = _sort_fields(sort_key=list(data_defs.static.keys()), fields=raw_data["static"])
    temporal: Any = []  # TODO.
    event: Any = []  # TODO.

    return DataSample(static=static, temporal=temporal, event=event)


def add_sample(db: DetaBase, key: str, data_defs: "DataDefsCollection"):
    static = _get_default(data_defs=data_defs.static)
    temporal: Any = []  # TODO.
    event: Any = []  # TODO.

    data_sample = dict(DataSample(static=static, temporal=temporal, event=event))

    print(f"Adding new sample to db.\nkey: {key}\ndata:\n{data_sample}")
    db.put(data_sample, key=key)


def delete_sample(db: DetaBase, key: str):
    print(f"Deleting sample from db.\nkey: {key}")
    db.delete(key=key)


def update_sample(db: DetaBase, key: str, data_sample: DataSample):
    print(f"Adding new sample to db.\nkey: {key}\ndata:\n{data_sample}")
    db.put(dict(data_sample), key=key)
