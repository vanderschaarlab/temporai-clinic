import io
import os
import zipfile
from typing import Any, Dict, List, Optional, Tuple, cast

import streamlit as st
from deta import Deta
from deta import _Base as DetaBase
from deta import _Drive as DetaDrive

from . import field_def
from .const import DataDefsCollectionDict, DataSample


def connect_to_db(
    deta_key_secret: str, base_name_env_var: str, drive_name_env_var: Optional[str] = None
) -> Tuple[Deta, DetaBase, Optional[DetaDrive]]:
    deta = Deta(st.secrets[deta_key_secret])
    base = deta.Base(st.secrets[base_name_env_var])
    drive: Optional[DetaDrive] = None
    if drive_name_env_var:
        drive = deta.Drive(st.secrets[drive_name_env_var])
    return deta, base, drive


def download_zipped_dir(drive: DetaDrive, zip_file: str = "data.zip", local_dir: str = "./data") -> None:
    # NOTE: Will only download and extract if the local directory does not exist.
    directory = os.path.realpath(local_dir)
    if not os.path.exists(directory):
        print(f"Local directory {local_dir} does not exist, creating")
        os.makedirs(directory)
        # Get zip file from Deta Drive.
        print(f"Downloading {zip_file} from Deta Drive")
        # For debug:
        # print(drive.list())
        file = drive.get(zip_file)
        if file is None:
            raise RuntimeError(f"File {zip_file} not found on Deta Drive")
        print(f"Unzipping {zip_file} to {local_dir}")
        bytes_ = file.read()
        with zipfile.ZipFile(io.BytesIO(bytes_), "r") as zip_ref:
            zip_ref.extractall(directory)
        print("Downloading and extracting zip file finished")


def get_all_sample_keys(db: DetaBase) -> List[str]:
    # TODO: This is inefficient. Needs to be improved.
    all_data = db.fetch()
    # if all_data.count == 0:
    #     raise RuntimeError("No data found")
    if all_data.last is not None:
        raise RuntimeError("Too many data rows. Supported max rows is 1000.")
    return [example["key"] for example in all_data.items]


def _sort_fields(sort_key: List[str], fields: Dict[str, Dict]) -> Dict[str, Dict]:
    # Sort the fields in field_defs order (the fields in the DB are in random order).
    sorted_fields: Dict[str, Any] = dict()
    for key in sort_key:
        sorted_fields[key] = fields[key]
    return sorted_fields


def _sort_fields_in_array(sort_key: List[str], array_of_fields: List[Dict[str, Dict]]) -> List[Dict[str, Dict]]:
    sorted_array_of_fields: List[Dict[str, Dict]] = []
    for fields in array_of_fields:
        sorted_array_of_fields.append(_sort_fields(sort_key=sort_key, fields=fields))
    return sorted_array_of_fields


def get_sample(key: str, db: DetaBase, field_defs: "field_def.FieldDefsCollection") -> DataSample:
    raw_data = cast(DataDefsCollectionDict, db.get(key))

    static = _sort_fields(sort_key=list(field_defs.static.keys()), fields=raw_data["static"])
    temporal = _sort_fields_in_array(sort_key=list(field_defs.temporal.keys()), array_of_fields=raw_data["temporal"])
    event = _sort_fields_in_array(sort_key=list(field_defs.event.keys()), array_of_fields=raw_data["event"])

    static = field_def.process_db_to_input(field_defs=field_defs.static, data=static)
    temporal = [field_def.process_db_to_input(field_defs=field_defs.temporal, data=x) for x in temporal]
    event = [field_def.process_db_to_input(field_defs=field_defs.event, data=x) for x in event]

    return DataSample(static=static, temporal=temporal, event=event)


def add_empty_sample(db: DetaBase, key: str, field_defs: "field_def.FieldDefsCollection"):
    static = field_def.get_default(field_defs=field_defs.static) if field_defs.static else {}
    temporal: Any = [field_def.get_default(field_defs=field_defs.temporal)] if field_defs.temporal else []
    event: Any = [field_def.get_default(field_defs=field_defs.event)] if field_defs.event else []

    static = field_def.process_input_to_db(field_defs=field_defs.static, data=static)
    temporal = [field_def.process_input_to_db(field_defs=field_defs.temporal, data=x) for x in temporal]
    event = [field_def.process_input_to_db(field_defs=field_defs.event, data=x) for x in event]

    data_sample = dict(DataSample(static=static, temporal=temporal, event=event))

    print(f"Adding new sample to db.\nkey: {key}\ndata:\n{data_sample}")
    db.put(data_sample, key=key)


def delete_sample(db: DetaBase, key: str):
    print(f"Deleting sample from db.\nkey: {key}")
    db.delete(key=key)


def update_sample(db: DetaBase, key: str, data_sample: DataSample, field_defs: "field_def.FieldDefsCollection"):
    static = field_def.process_input_to_db(field_defs=field_defs.static, data=data_sample.static)
    temporal = [field_def.process_input_to_db(field_defs=field_defs.temporal, data=x) for x in data_sample.temporal]
    event = [field_def.process_input_to_db(field_defs=field_defs.event, data=x) for x in data_sample.event]

    data_sample_processed = dict(DataSample(static=static, temporal=temporal, event=event))

    print(f"Adding new sample to db.\nkey: {key}\ndata:\n{data_sample_processed}")
    db.put(dict(data_sample_processed), key=key)
