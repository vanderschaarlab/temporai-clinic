from typing import TYPE_CHECKING, Any, Dict, List

import pandas as pd

from .const import DEFAULTS

if TYPE_CHECKING:
    from . import field_def


def get_temporal_data_time_indexes(data_sample_temporal: List[Dict[str, Any]]) -> List:
    return [x[DEFAULTS.time_index_field] for x in data_sample_temporal]


def get_temporal_data_as_df(data_sample_temporal: List[Dict[str, Any]]) -> pd.DataFrame:
    df_dict = dict()
    if len(data_sample_temporal) < 1:
        raise ValueError("Temporal data list must contain at least one element")
    feature_keys = data_sample_temporal[0].keys()
    for feature_key in feature_keys:
        df_dict[feature_key] = [x[feature_key] for x in data_sample_temporal]
    return pd.DataFrame(df_dict).set_index(DEFAULTS.time_index_field, drop=True)


def format_with_field_formatting(value: Any, fd: "field_def.FieldDef") -> str:
    return ("{0" + fd.get_formatting() + "}").format(value)


def remove_ith_element(lst: List, i: int):
    return lst[:i] + lst[i + 1 :]
