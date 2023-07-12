import abc
from typing import Any, Callable, ClassVar, Dict, List, NamedTuple, Optional

import streamlit as st
from pydantic import BaseModel
from typing_extensions import Literal

from tempor.clinic.const import STATE_KEYS, DataDefsCollectionDict, DataModality

DataType = Literal["int", "float", "categorical", "binary", "time_index"]
TimeIndexType = Literal["date", "int", "float"]


def get_widget_st_key(data_def: "DataDef") -> str:
    data_or_time_index = (
        STATE_KEYS.time_index_prefix if data_def.data_type == "time_index" else STATE_KEYS.data_field_prefix
    )
    return f"{data_or_time_index}_{data_def.data_modality}_{data_def.feature_name}"


class DataDef(BaseModel, abc.ABC):
    data_type: ClassVar[DataType]

    data_modality: DataModality
    feature_name: str
    readable_name: str
    transform_input_to_db: Optional[Callable] = None
    transform_db_to_input: Optional[Callable] = None

    @abc.abstractmethod
    def _render_widget(self, value: Any) -> Any:
        ...

    @abc.abstractmethod
    def get_default_value(self) -> Any:
        ...

    @abc.abstractmethod
    def _default_transform_db_to_input(self, value: Any) -> Any:
        ...

    @abc.abstractmethod
    def _default_transform_input_to_db(self, value: Any) -> Any:
        ...

    def render_edit_widget(self, value: Any) -> Any:
        value = self.process_db_to_input(value)
        return self._render_widget(value=value)

    def process_db_to_input(self, value: Any) -> Any:
        if self.transform_db_to_input is not None:
            value = self.transform_db_to_input(value)
        return self._default_transform_db_to_input(value)

    def process_input_to_db(self, value: Any) -> Any:
        if self.transform_input_to_db is not None:
            value = self.transform_input_to_db(value)
        return self._default_transform_input_to_db(value)


class DataDefsCollection(NamedTuple):
    static: Dict[str, DataDef]
    temporal: Dict[str, DataDef]
    event: Dict[str, DataDef]


class IntDef(DataDef):
    data_type: ClassVar[DataType] = "int"

    min_value: Optional[int] = None
    max_value: Optional[int] = None
    step: Optional[int] = None

    def _render_widget(self, value: int) -> Any:
        return st.number_input(
            label=self.readable_name,
            key=get_widget_st_key(self),
            min_value=self.min_value,
            max_value=self.max_value,
            step=self.step,
            value=value,
        )

    def get_default_value(self) -> int:
        return self.min_value if self.min_value is not None else 0

    def _default_transform_db_to_input(self, value: Any) -> int:
        return int(value)

    def _default_transform_input_to_db(self, value: Any) -> int:
        return int(value)


class FloatDef(DataDef):
    data_type: ClassVar[DataType] = "float"

    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step: Optional[float] = None

    def _render_widget(self, value: float) -> Any:
        return st.number_input(
            label=self.readable_name,
            key=get_widget_st_key(self),
            min_value=self.min_value,
            max_value=self.max_value,
            step=self.step,
            value=value,
        )

    def get_default_value(self) -> float:
        return self.min_value if self.min_value is not None else 0.0

    def _default_transform_db_to_input(self, value: Any) -> float:
        return float(value)

    def _default_transform_input_to_db(self, value: Any) -> float:
        return float(value)


class CategoricalDef(DataDef):
    data_type: ClassVar[DataType] = "categorical"

    options: List[str]

    def _render_widget(self, value: str) -> Any:
        return st.selectbox(
            label=self.readable_name,
            key=get_widget_st_key(self),
            options=self.options,
            index=self.options.index(value),
        )

    def get_default_value(self) -> str:
        return self.options[0]

    def _default_transform_db_to_input(self, value: Any) -> str:
        return str(value)

    def _default_transform_input_to_db(self, value: Any) -> str:
        return str(value)


class BinaryDef(DataDef):
    data_type: ClassVar[DataType] = "binary"

    def _render_widget(self, value: bool) -> Any:
        return st.checkbox(
            label=self.readable_name,
            key=get_widget_st_key(self),
            value=value,
        )

    def get_default_value(self) -> bool:
        return False

    def _default_transform_db_to_input(self, value: Any) -> bool:
        return bool(value)

    def _default_transform_input_to_db(self, value: Any) -> bool:
        return bool(value)


class TimeIndexDef(DataDef):
    time_index_type: ClassVar[TimeIndexType]
    data_type: ClassVar[DataType] = "time_index"

    @abc.abstractmethod
    def get_next(self, value: Any) -> Any:
        ...


class IntTimeIndexDef(IntDef, TimeIndexDef):
    time_index_type: ClassVar[TimeIndexType] = "int"

    def get_next(self, value: int) -> int:
        return value + 1

    # min_value: Optional[int] = None
    # max_value: Optional[int] = None
    # step: Optional[int] = None

    # def _render_widget(self, value: int) -> Any:
    #     return st.number_input(
    #         label=self.readable_name,
    #         key=get_widget_st_key(self),
    #         min_value=self.min_value,
    #         max_value=self.max_value,
    #         step=self.step,
    #         value=value,
    #     )

    # def get_default_value(self) -> int:
    #     return self.min_value if self.min_value is not None else 0

    # def _default_transform_db_to_input(self, value: Any) -> int:
    #     return int(value)

    # def _default_transform_input_to_db(self, value: Any) -> int:
    #     return int(value)


class FloatTimeIndexDef(FloatDef, TimeIndexDef):
    time_index_type: ClassVar[TimeIndexType] = "float"

    def get_next(self, value: float) -> float:
        return value + 1

    # min_value: Optional[float] = None
    # max_value: Optional[float] = None
    # step: Optional[float] = None

    # def _render_widget(self, value: float) -> Any:
    #     return st.number_input(
    #         label=self.readable_name,
    #         key=get_widget_st_key(self),
    #         min_value=self.min_value,
    #         max_value=self.max_value,
    #         step=self.step,
    #         value=value,
    #     )

    # def get_default_value(self) -> float:
    #     return self.min_value if self.min_value is not None else 0.0

    # def _default_transform_db_to_input(self, value: Any) -> float:
    #     return float(value)

    # def _default_transform_input_to_db(self, value: Any) -> float:
    #     return float(value)


# TODO: Data time index.


def _parse_data_defs_dict(data_defs: Dict[str, Dict], data_modality: DataModality) -> Dict[str, DataDef]:
    parsed: Dict[str, DataDef] = dict()
    for feature_name, data_def in data_defs.items():
        if data_def["data_type"] == "int":
            parsed[feature_name] = IntDef(feature_name=feature_name, data_modality=data_modality, **data_def)
        elif data_def["data_type"] == "float":
            parsed[feature_name] = FloatDef(feature_name=feature_name, data_modality=data_modality, **data_def)
        elif data_def["data_type"] == "categorical":
            parsed[feature_name] = CategoricalDef(feature_name=feature_name, data_modality=data_modality, **data_def)
        elif data_def["data_type"] == "binary":
            parsed[feature_name] = BinaryDef(feature_name=feature_name, data_modality=data_modality, **data_def)
        elif data_def["data_type"] == "time_index":
            if data_def["time_index_type"] == "int":
                parsed[feature_name] = IntTimeIndexDef(
                    feature_name=feature_name, data_modality=data_modality, **data_def
                )
            elif data_def["time_index_type"] == "float":
                parsed[feature_name] = FloatTimeIndexDef(
                    feature_name=feature_name, data_modality=data_modality, **data_def
                )
            else:
                raise TypeError(f"Unknown 'time_index_type' encountered: {data_def['time_index_type']}")
        else:
            raise TypeError(f"Unknown 'data_type' encountered: {data_def['data_type']}")
    return parsed


def parse_data_defs(data_defs_raw: DataDefsCollectionDict) -> DataDefsCollection:
    if "temporal" in data_defs_raw:
        if "time_index" not in data_defs_raw["temporal"]:
            raise ValueError("'time_index' key must be present in data defs -> temporal")
        if (
            "time_index" in data_defs_raw["temporal"]
            and data_defs_raw["temporal"]["time_index"]["data_type"] != "time_index"
        ):
            raise ValueError("'time_index' data def must have 'data_type' == 'time_index'")
        # TODO: time index must be first in the dict.
        # TODO: time_index_type must be present.
    return DataDefsCollection(
        static=(
            _parse_data_defs_dict(data_defs=data_defs_raw["static"], data_modality="static")
            if "static" in data_defs_raw
            else dict()
        ),
        temporal=(
            _parse_data_defs_dict(data_defs=data_defs_raw["temporal"], data_modality="temporal")
            if "temporal" in data_defs_raw
            else dict()
        ),
        event=(
            _parse_data_defs_dict(data_defs=data_defs_raw["event"], data_modality="event")
            if "event" in data_defs_raw
            else dict()
        ),
    )


def get_default(data_defs: Dict[str, "DataDef"]) -> Dict[str, Dict]:
    data_sample = dict()
    for field_name, data_def in data_defs.items():
        data_sample[field_name] = data_def.get_default_value()
    return data_sample
