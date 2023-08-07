import abc
import datetime
from typing import Any, Callable, ClassVar, Dict, List, NamedTuple, Optional, Union

import streamlit as st
from pydantic import BaseModel
from typing_extensions import Literal

from tempor.clinic.const import DEFAULTS, STATE_KEYS, DataDefsCollectionDict, DataModality, DataSample

DataType = Literal["int", "float", "categorical", "binary", "str", "time_index", "computed"]
TimeIndexType = Literal["date", "int", "float"]
ComputedType = Literal["float"]

TimeStep = Union[datetime.date, float, int]


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
    default_value: Any = None
    formatting: Optional[str] = None
    info: Optional[str] = None

    transform_input_to_db: Optional[Callable] = None
    transform_db_to_input: Optional[Callable] = None

    @abc.abstractmethod
    def _render_widget(self, value: Any) -> Any:
        ...

    @abc.abstractmethod
    def _default_transform_db_to_input(self, value: Any) -> Any:
        ...

    @abc.abstractmethod
    def _default_transform_input_to_db(self, value: Any) -> Any:
        ...

    @abc.abstractmethod
    def _default_value_formatting(self) -> str:
        ...

    def get_default_value(self) -> Any:
        # NOTE: Ideally this should also ve overridden in the derived classes, in order to update type hints,
        # or add any additional logic.
        return self.default_value

    def get_formatting(self) -> str:
        if self.formatting is not None:
            return self.formatting
        else:
            return self._default_value_formatting()

    def render_edit_widget(self, value: Any) -> Any:
        # value = self.process_db_to_input(value)
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
    default_value: Optional[int] = None

    def _default_value_formatting(self) -> str:
        return ":n"

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
            help=self.info,
        )

    def get_default_value(self) -> int:
        if self.default_value is not None:
            if self.min_value is not None and self.default_value < self.min_value:
                raise ValueError(
                    f"The default value set for '{self.feature_name}', `{self.default_value}` is "
                    f"less than the minimum value set, `{self.min_value}`"
                )
            if self.max_value is not None and self.default_value > self.max_value:
                raise ValueError(
                    f"The default value set for '{self.feature_name}', `{self.default_value}` is "
                    f"greater than the maximum value set, `{self.max_value}`"
                )
        return (
            self.default_value
            if self.default_value is not None
            else (self.min_value if self.min_value is not None else 0)
        )

    def _default_transform_db_to_input(self, value: Any) -> int:
        return int(value)

    def _default_transform_input_to_db(self, value: Any) -> int:
        return int(value)


class FloatDef(FieldDef):
    data_type: ClassVar[DataType] = "float"
    default_value: Optional[float] = None

    def _default_value_formatting(self) -> str:
        return ":.2f"

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
            help=self.info,
        )

    def get_default_value(self) -> float:
        if self.default_value is not None:
            if self.min_value is not None and self.default_value < self.min_value:
                raise ValueError(
                    f"The default value set for '{self.feature_name}', `{self.default_value}` is "
                    f"less than the minimum value set, `{self.min_value}`"
                )
            if self.max_value is not None and self.default_value > self.max_value:
                raise ValueError(
                    f"The default value set for '{self.feature_name}', `{self.default_value}` is "
                    f"greater than the maximum value set, `{self.max_value}`"
                )
        return (
            self.default_value
            if self.default_value is not None
            else (self.min_value if self.min_value is not None else 0)
        )

    def _default_transform_db_to_input(self, value: Any) -> float:
        return float(value)

    def _default_transform_input_to_db(self, value: Any) -> float:
        return float(value)


class CategoricalDef(FieldDef):
    data_type: ClassVar[DataType] = "categorical"
    default_value: Optional[str] = None

    def _default_value_formatting(self) -> str:
        return ""

    options: List[str]

    def _render_widget(self, value: str) -> Any:
        return st.selectbox(
            label=self.readable_name,
            key=get_widget_st_key(self),
            options=self.options,
            index=self.options.index(value),
            help=self.info,
        )

    def get_default_value(self) -> str:
        if self.default_value is not None and self.default_value not in self.options:
            raise ValueError(
                f"The default value defined for '{self.feature_name}' was '{self.default_value}', which "
                f"is not one of the options defined ({self.options}). This is not allowed."
            )
        return self.options[0]

    def _default_transform_db_to_input(self, value: Any) -> str:
        return str(value)

    def _default_transform_input_to_db(self, value: Any) -> str:
        return str(value)


class BinaryDef(FieldDef):
    data_type: ClassVar[DataType] = "binary"
    default_value: bool = False

    def _default_value_formatting(self) -> str:
        return ""

    def _render_widget(self, value: bool) -> Any:
        return st.checkbox(label=self.readable_name, key=get_widget_st_key(self), value=value, help=self.info)

    def get_default_value(self) -> bool:
        return self.default_value

    def _default_transform_db_to_input(self, value: Any) -> bool:
        return bool(value)

    def _default_transform_input_to_db(self, value: Any) -> bool:
        return bool(value)


class StrDef(FieldDef):
    data_type: ClassVar[DataType] = "str"
    default_value: str = ""

    def _default_value_formatting(self) -> str:
        return ""

    def _render_widget(self, value: str) -> Any:
        return st.text_area(
            label=self.readable_name,
            key=get_widget_st_key(self),
            value=value,
            help=self.info,
        )

    def get_default_value(self) -> str:
        # Overridden to add type hint only.
        return super().get_default_value()

    def _default_transform_db_to_input(self, value: Any) -> str:
        return str(value)

    def _default_transform_input_to_db(self, value: Any) -> str:
        return str(value)


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


class DateTimeIndexDef(TimeIndexDef):
    time_index_type: ClassVar[TimeIndexType] = "date"

    default_value: Optional[datetime.datetime] = None

    min_value: Optional[datetime.date] = None
    max_value: Optional[datetime.date] = None

    def _default_value_formatting(self) -> str:
        return ":%Y-%m-%d"

    def _render_widget(self, value: datetime.date) -> Any:
        return st.date_input(
            label=self.readable_name,
            key=get_widget_st_key(self),
            max_value=self.max_value,
            min_value=self.min_value,
            value=value,
        )

    def get_default_value(self) -> datetime.date:
        if self.default_value is None:
            return datetime.datetime.now().date()
        else:
            return self.default_value

    def get_next(self, value: datetime.date) -> datetime.date:
        return value + datetime.timedelta(days=1)

    def _default_transform_db_to_input(self, value: str) -> datetime.date:
        return datetime.datetime.fromisoformat(value).date()

    def _default_transform_input_to_db(self, value: datetime.date) -> str:
        return value.strftime("%Y-%m-%d")


class ComputedDef(FieldDef):
    computed_type: ClassVar[ComputedType]
    data_type: ClassVar[DataType] = "computed"

    computation: Callable[[DataSample, TimeStep], Any]

    def _render_widget(self, value: float) -> Any:
        return st.markdown(
            f"{self.readable_name}:<br/>`Computed automatically`"
            + (f"<br/>*{self.info}*" if self.info is not None else ""),
            unsafe_allow_html=True,
        )

    def compute(self, data_sample: DataSample, current_timestep: TimeStep) -> Any:
        """Make whatever computation the field requires and return the computed value.

        Note:
            The computation cascades from static data, to time series data, to event data.

        Args:
            data_sample (DataSample): Sample data object, before computation.
            current_timestep (TimeStep): The currently selected time step.

        Returns:
            Any: The resultant computed value.
        """
        return self.computation(data_sample, current_timestep)


class FloatComputedDef(ComputedDef, FloatDef):
    computed_type: ClassVar[ComputedType]
    data_type: ClassVar[DataType] = "computed"


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
        elif field_def["data_type"] == "str":
            parsed[feature_name] = StrDef(feature_name=feature_name, data_modality=data_modality, **field_def)
        elif field_def["data_type"] == "time_index":
            if field_def["time_index_type"] == "int":
                parsed[feature_name] = IntTimeIndexDef(
                    feature_name=feature_name, data_modality=data_modality, **field_def
                )
            elif field_def["time_index_type"] == "float":
                parsed[feature_name] = FloatTimeIndexDef(
                    feature_name=feature_name, data_modality=data_modality, **field_def
                )
            elif field_def["time_index_type"] == "date":
                parsed[feature_name] = DateTimeIndexDef(
                    feature_name=feature_name, data_modality=data_modality, **field_def
                )
            else:
                raise TypeError(f"Unknown 'time_index_type' encountered: {field_def['time_index_type']}")
        elif field_def["data_type"] == "computed":
            if field_def["computed_type"] == "float":
                parsed[feature_name] = FloatComputedDef(
                    feature_name=feature_name, data_modality=data_modality, **field_def
                )
            else:
                raise TypeError(f"Unknown 'computed_type' encountered: {field_def['computed_type']}")
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


def get_default(field_defs: Dict[str, FieldDef]) -> Dict[str, Dict]:
    data_fields = dict()

    # Get defaults for non-computed fields:
    for field_name, field_def in field_defs.items():
        if field_def.data_type != "computed":
            data_fields[field_name] = field_def.get_default_value()

    return data_fields


def get_default_computed(
    field_defs: Dict[str, FieldDef],
    modality: DataModality,
    data_sample_before_computation: DataSample,
    current_timestep: TimeStep,
) -> Dict[str, Dict]:
    if modality == "static":
        data_fields = data_sample_before_computation.static.copy()
    elif modality == "temporal":
        data_fields = data_sample_before_computation.temporal[-1].copy()
    elif modality == "event":
        # TODO: This is to be revised.
        data_fields = data_sample_before_computation.event[-1].copy()
    else:
        raise ValueError(f"Unknown modality encountered: {modality}")

    # Compute the computed fields:
    for field_name, field_def in field_defs.items():
        if field_def.data_type == "computed":
            if not isinstance(field_def, ComputedDef):
                raise RuntimeError
            data_fields[field_name] = field_def.compute(data_sample_before_computation, current_timestep)

    return data_fields


def update(
    field_defs: Dict[str, FieldDef],
    session_state: Any,
    modality: DataModality,
    data_sample: DataSample,
    current_timestep: TimeStep,
) -> Dict[str, Dict]:
    data_fields = dict()

    # Update non-computed fields:
    for field_name, field_def in field_defs.items():
        key = get_widget_st_key(field_def)
        if field_def.data_type != "computed":
            data_fields[field_name] = session_state[key]

    if modality == "static":
        data_sample.static = data_fields
    elif modality == "temporal":
        data_sample.temporal[current_timestep] = data_fields
    elif modality == "event":
        # TODO: This is to be revised.
        data_sample.event[current_timestep] = data_fields
    else:
        raise ValueError(f"Unknown modality encountered: {modality}")

    # Update computed fields:
    for field_name, field_def in field_defs.items():
        if field_def.data_type == "computed":
            if not isinstance(field_def, ComputedDef):
                raise RuntimeError
            data_fields[field_name] = field_def.compute(data_sample, current_timestep)

    return data_fields


def process_db_to_input(field_defs: Dict[str, FieldDef], data: Dict) -> Dict:
    data_processed = dict()
    for field_name, field_def in field_defs.items():
        data_processed[field_name] = field_def.process_db_to_input(data[field_name])
    return data_processed


def process_input_to_db(field_defs: Dict[str, FieldDef], data: Dict) -> Dict:
    data_processed = dict()
    for field_name, field_def in field_defs.items():
        data_processed[field_name] = field_def.process_input_to_db(data[field_name])
    return data_processed
