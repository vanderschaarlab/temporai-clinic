import abc
from typing import Any, Callable, ClassVar, Dict, List, NamedTuple, Optional

import streamlit as st
from pydantic import BaseModel
from typing_extensions import Literal

from tempor.clinic.const import DEFAULTS, STATE_KEYS, DataDefsCollectionDict, DataModality

DataType = Literal["int", "float", "categorical", "binary", "time_index"]
TimeIndexType = Literal["date", "int", "float"]


def get_widget_st_key(field_def: "FieldDef") -> str:
    data_or_time_index = (
        STATE_KEYS.time_index_prefix
        if field_def.data_type == DEFAULTS.time_index_field
        else STATE_KEYS.data_field_prefix
    )
    return f"{data_or_time_index}_{field_def.data_modality}_{field_def.feature_name}"


class FieldDef(BaseModel, abc.ABC):
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


class FieldDefsCollection(NamedTuple):
    static: Dict[str, FieldDef]
    temporal: Dict[str, FieldDef]
    event: Dict[str, FieldDef]


class IntDef(FieldDef):
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


class FloatDef(FieldDef):
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


class CategoricalDef(FieldDef):
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


class BinaryDef(FieldDef):
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


class TimeIndexDef(FieldDef):
    time_index_type: ClassVar[TimeIndexType]
    data_type: ClassVar[DataType] = "time_index"

    @abc.abstractmethod
    def get_next(self, value: Any) -> Any:
        ...


class IntTimeIndexDef(IntDef, TimeIndexDef):
    time_index_type: ClassVar[TimeIndexType] = "int"

    def get_next(self, value: int) -> int:
        return value + 1


class FloatTimeIndexDef(FloatDef, TimeIndexDef):
    time_index_type: ClassVar[TimeIndexType] = "float"

    def get_next(self, value: float) -> float:
        return value + 1.0


# TODO: Data time index.


def _parse_field_defs_dict(field_defs: Dict[str, Dict], data_modality: DataModality) -> Dict[str, FieldDef]:
    parsed: Dict[str, FieldDef] = dict()
    for feature_name, field_def in field_defs.items():
        if field_def["data_type"] == "int":
            parsed[feature_name] = IntDef(feature_name=feature_name, data_modality=data_modality, **field_def)
        elif field_def["data_type"] == "float":
            parsed[feature_name] = FloatDef(feature_name=feature_name, data_modality=data_modality, **field_def)
        elif field_def["data_type"] == "categorical":
            parsed[feature_name] = CategoricalDef(feature_name=feature_name, data_modality=data_modality, **field_def)
        elif field_def["data_type"] == "binary":
            parsed[feature_name] = BinaryDef(feature_name=feature_name, data_modality=data_modality, **field_def)
        elif field_def["data_type"] == "time_index":
            if field_def["time_index_type"] == "int":
                parsed[feature_name] = IntTimeIndexDef(
                    feature_name=feature_name, data_modality=data_modality, **field_def
                )
            elif field_def["time_index_type"] == "float":
                parsed[feature_name] = FloatTimeIndexDef(
                    feature_name=feature_name, data_modality=data_modality, **field_def
                )
            else:
                raise TypeError(f"Unknown 'time_index_type' encountered: {field_def['time_index_type']}")
        else:
            raise TypeError(f"Unknown 'data_type' encountered: {field_def['data_type']}")
    return parsed


def parse_field_defs(field_defs_raw: DataDefsCollectionDict) -> FieldDefsCollection:
    if "temporal" in field_defs_raw:
        if DEFAULTS.time_index_field not in field_defs_raw["temporal"]:
            raise ValueError("'time_index' key must be present in field defs -> temporal")
        if (
            DEFAULTS.time_index_field in field_defs_raw["temporal"]
            and field_defs_raw["temporal"][DEFAULTS.time_index_field]["data_type"] != DEFAULTS.time_index_field
        ):
            raise ValueError("'time_index' field def must have 'data_type' == 'time_index'")
        # TODO: time index must be first in the dict.
        # TODO: time_index_type must be present.
    return FieldDefsCollection(
        static=(
            _parse_field_defs_dict(field_defs=field_defs_raw["static"], data_modality="static")
            if "static" in field_defs_raw
            else dict()
        ),
        temporal=(
            _parse_field_defs_dict(field_defs=field_defs_raw["temporal"], data_modality="temporal")
            if "temporal" in field_defs_raw
            else dict()
        ),
        event=(
            _parse_field_defs_dict(field_defs=field_defs_raw["event"], data_modality="event")
            if "event" in field_defs_raw
            else dict()
        ),
    )


def get_default(field_defs: Dict[str, "FieldDef"]) -> Dict[str, Dict]:
    data_sample = dict()
    for field_name, field_def in field_defs.items():
        data_sample[field_name] = field_def.get_default_value()
    return data_sample