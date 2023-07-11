import abc
from typing import Any, Callable, ClassVar, Dict, List, Optional

import streamlit as st
from pydantic import BaseModel
from typing_extensions import Literal

from tempor.clinic.const import STATE_KEYS

DataType = Literal["int", "float", "categorical", "binary"]


class DataDef(BaseModel, abc.ABC):
    data_type: ClassVar[DataType]

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

    # def render_add_widget(self) -> Any:
    #     default = self._get_default_value()
    #     return self._render_widget(value=default)

    def process_db_to_input(self, value: Any) -> Any:
        if self.transform_db_to_input is not None:
            value = self.transform_db_to_input(value)
        return self._default_transform_db_to_input(value)

    def process_input_to_db(self, value: Any) -> Any:
        if self.transform_input_to_db is not None:
            value = self.transform_input_to_db(value)
        return self._default_transform_input_to_db(value)


class IntDef(DataDef):
    data_type: ClassVar[DataType] = "int"

    min_value: Optional[int] = None
    max_value: Optional[int] = None
    step: Optional[int] = None

    def _render_widget(self, value: int) -> Any:
        return st.number_input(
            label=self.readable_name,
            key=f"{STATE_KEYS.data_static_field_prefix}_{self.feature_name}",
            min_value=self.min_value,
            max_value=self.max_value,
            step=self.step,
            value=value,
        )

    def get_default_value(self) -> Any:
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
            key=f"{STATE_KEYS.data_static_field_prefix}_{self.feature_name}",
            min_value=self.min_value,
            max_value=self.max_value,
            step=self.step,
            value=value,
        )

    def get_default_value(self) -> Any:
        return self.min_value if self.min_value is not None else 0

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
            key=f"{STATE_KEYS.data_static_field_prefix}_{self.feature_name}",
            options=self.options,
            index=self.options.index(value),
        )

    def get_default_value(self) -> Any:
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
            key=f"{STATE_KEYS.data_static_field_prefix}_{self.feature_name}",
            value=value,
        )

    def get_default_value(self) -> Any:
        return False

    def _default_transform_db_to_input(self, value: Any) -> bool:
        return bool(value)

    def _default_transform_input_to_db(self, value: Any) -> bool:
        return bool(value)


def parse_data_defs(data_defs: Dict[str, Dict]) -> Dict[str, DataDef]:
    parsed: Dict[str, DataDef] = dict()
    for feature_name, data_def in data_defs.items():
        if data_def["data_type"] == "int":
            parsed[feature_name] = IntDef(feature_name=feature_name, **data_def)
        elif data_def["data_type"] == "float":
            parsed[feature_name] = FloatDef(feature_name=feature_name, **data_def)
        elif data_def["data_type"] == "categorical":
            parsed[feature_name] = CategoricalDef(feature_name=feature_name, **data_def)
        elif data_def["data_type"] == "binary":
            parsed[feature_name] = BinaryDef(feature_name=feature_name, **data_def)
    return parsed
