import os
import random
import string
import time
from typing import TYPE_CHECKING, Any, Callable, Dict, List, NamedTuple, Optional, Sequence, Union, cast

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit_extras
from packaging.version import Version
from streamlit_modal import Modal
from typing_extensions import Literal, Protocol

from . import deta_utils, field_def, utils
from .app_state import AppState
from .const import DEFAULTS, DataSample

if TYPE_CHECKING:
    from deta import _Base as DetaBase


class AppSettings(NamedTuple):
    name: str
    example_name: str


if "__version__" in dir(streamlit_extras) and (
    Version(streamlit_extras.__version__) >= Version("0.2.2")  # type: ignore  # pylint: disable=no-member
):
    # pylint: disable-next=import-error,no-name-in-module
    from streamlit_extras.add_vertical_space import add_vertical_space  # type: ignore

else:

    def add_vertical_space(num_lines: int = 1):
        """Add vertical space to your Streamlit app."""
        for _ in range(num_lines):
            st.write("")


def page_config(app_settings: AppSettings, icon_path: Optional[str] = None) -> None:
    st.set_page_config(
        page_title=app_settings.name,
        page_icon=os.path.join(DEFAULTS.assets_dir, icon_path if icon_path is not None else DEFAULTS.icon),
        layout="wide",
    )


def sidebar(
    app_settings: AppSettings,
    *,
    logo_path: Optional[str] = None,
    logo_width: int = 75,
    description_html: Optional[str] = None,
    pop_up_label: Optional[str] = None,
    pop_up_content: Optional[str] = None,
    pop_up_width: int = 800,
) -> None:
    # CSS hacks necessary to give the pop-up modal a correct width and height.
    st.markdown(
        f"""
        <style>
            div[data-modal-container='true'][key='sidebar-modal'] > div:first-child {{
                width: {pop_up_width}px;
            }}
            div[data-modal-container='true'][key='sidebar-modal'] > div:first-child > div:first-child > div:first-child {{
                width: {pop_up_width}px;
                overflow-y: scroll;
                max-height: 600px;
                overflow-x: hidden;
            }}
            div[data-modal-container='true'][key='sidebar-modal'] > div > div:nth-child(2) > div {{
                width: {pop_up_width}px !important;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Sidebar content:
    with st.sidebar:
        st.image(
            os.path.join(DEFAULTS.assets_dir, logo_path if logo_path is not None else DEFAULTS.logo), width=logo_width
        )
        st.markdown(
            f"""
            # TemporAI-Clinic
            ### {app_settings.name}
            """
        )
        if description_html is not None:
            st.markdown(
                f"""
                <br/>
                <div class="custom-alert" style="
                    border: 1px solid rgba(9, 171, 59, 0.2);
                    border-radius: 0.25rem;
                    background-color: rgba(9, 171, 59, 0.2);
                    color: rgb(29, 121, 58);
                    padding: 16px;
                ">
                    {description_html}
                </div>
                """,
                unsafe_allow_html=True,
            )
        if pop_up_label is not None:
            add_vertical_space(1)
            modal = Modal(pop_up_label, key="sidebar-modal", max_width=pop_up_width)
            open_modal = st.button(label=pop_up_label)
            if open_modal:
                modal.open()
            if modal.is_open():
                with modal.container():
                    st.markdown(pop_up_content if pop_up_content is not None else "No pop-up content provided.")


def _set_current_example(app_state: AppState, sample_selector_key: str):
    app_state.current_sample = st.session_state[sample_selector_key]
    app_state.current_timestep = 0


def _delete_current_example(app_state: AppState, db: "DetaBase"):
    current_sample = app_state.current_sample
    if current_sample is None:
        raise RuntimeError("`current_sample` was `None`")
    deta_utils.delete_sample(db=db, key=current_sample)
    app_state.current_sample = None


def _add_new_sample(app_state: AppState, db: "DetaBase", key: str, field_defs: field_def.FieldDefsCollection):
    app_state.current_timestep = 0  # New sample is added with just one timestep, timestep 0.
    deta_utils.add_empty_sample(db=db, key=key, field_defs=field_defs, current_timestep=app_state.current_timestep)
    app_state.current_sample = key


StPanel = Literal["error", "warning", "info"]
PANEL_TYPES: Dict[StPanel, Callable] = {
    "error": st.error,
    "warning": st.warning,
    "info": st.info,
}


def faux_confirm_modal(
    panel_type: StPanel,
    panel_text: str,
    panel_icon: str,
    confirm_btn_on_click: Callable,
    confirm_btn_on_click_kwargs: Dict,
    confirm_btn_help: str,
    cancel_btn_on_click: Callable,
    cancel_btn_on_click_kwargs: Dict,
    cancel_btn_help: str,
    button_cols_split=(0.2, 0.2, 0.6),
):
    st.markdown("---")
    PANEL_TYPES[panel_type](panel_text, icon=panel_icon)
    col_confirm_btn, col_cancel_btn, _ = st.columns(button_cols_split)
    with col_confirm_btn:
        st.button(
            "Confirm",
            type="primary",
            on_click=confirm_btn_on_click,
            kwargs=confirm_btn_on_click_kwargs,
            help=confirm_btn_help,
        )
    with col_cancel_btn:
        st.button(
            "Cancel",
            on_click=cancel_btn_on_click,
            kwargs=cancel_btn_on_click_kwargs,
            help=cancel_btn_help,
        )
    st.markdown("---")


def _reset_interaction_state(app_state: AppState):
    app_state.interaction_state = "showing"


def _generate_new_sample_key():
    length = 12
    characters = string.ascii_lowercase + string.digits
    return "".join(random.choice(characters) for _ in range(length))  # nosec: B311


def sample_selector(
    app_settings: AppSettings,
    app_state: AppState,
    db: "DetaBase",
    field_defs: field_def.FieldDefsCollection,
    sample_keys: List[str],  # TODO: Is this needed here like this? Rethink.
) -> DataSample:
    col_patient_select, col_add, col_delete, _ = st.columns([0.8, 0.2 / 3, 0.2 / 3, 0.2 / 3])

    # Special case: no samples in database - create one. ---
    no_data_found = len(sample_keys) == 0
    if no_data_found:
        new_key = _generate_new_sample_key()
        with st.container():
            st.error(f"No data found, adding first {app_settings.example_name}, ID={new_key}...")
        _add_new_sample(app_state=app_state, db=db, key=new_key, field_defs=field_defs)
        time.sleep(3)
        st.experimental_rerun()
    # Special case: [END] ---

    with col_patient_select:
        sample_selector_key = DEFAULTS.key_sample_selector
        st.selectbox(
            label=app_settings.example_name.capitalize(),
            options=sample_keys,
            index=sample_keys.index(app_state.current_sample) if app_state.current_sample is not None else 0,
            key=sample_selector_key,
            on_change=_set_current_example,
            kwargs=dict(app_state=app_state, sample_selector_key=sample_selector_key),
        )
        if app_state.current_sample is None:
            app_state.current_sample = sample_keys[0]

        data_sample = deta_utils.get_sample(key=app_state.current_sample, db=db, field_defs=field_defs)

    with col_add:
        add_vertical_space(2)
        add_btn = st.button("➕", help=f"Add {app_settings.example_name}")
    with col_delete:
        add_vertical_space(2)
        delete_btn = st.button("❌", help=f"Delete {app_settings.example_name}")

    if add_btn:
        app_state.interaction_state = "adding_sample"
    elif delete_btn:
        app_state.interaction_state = "deleting_sample"
    else:
        app_state.interaction_state = "showing"

    if app_state.interaction_state == "deleting_sample":
        faux_confirm_modal(
            panel_type="error",
            panel_text=(
                f"This action will delete the currently selected {app_settings.example_name} "
                f"(ID: {app_state.current_sample}). "
                "It is not reversible. Please confirm."
            ),
            panel_icon="⚠️",
            confirm_btn_on_click=_delete_current_example,
            confirm_btn_on_click_kwargs=dict(app_state=app_state, db=db),
            confirm_btn_help=f"Confirm deleting {app_settings.example_name}",
            cancel_btn_on_click=_reset_interaction_state,
            cancel_btn_on_click_kwargs=dict(app_state=app_state),
            cancel_btn_help=f"Cancel deleting {app_settings.example_name}",
        )
    if app_state.interaction_state == "adding_sample":
        new_key = _generate_new_sample_key()
        faux_confirm_modal(
            panel_type="info",
            panel_text=(
                f"This action will create a new 'empty' {app_settings.example_name} with auto-generated ID: {new_key}. "
                f"You will be able to use the edit '🖊️' buttons to update the {app_settings.example_name} data. "
                "Please confirm."
            ),
            panel_icon="ℹ️",
            confirm_btn_on_click=_add_new_sample,
            confirm_btn_on_click_kwargs=dict(app_state=app_state, db=db, key=new_key, field_defs=field_defs),
            confirm_btn_help=f"Confirm adding {app_settings.example_name}",
            cancel_btn_on_click=_reset_interaction_state,
            cancel_btn_on_click_kwargs=dict(app_state=app_state),
            cancel_btn_help=f"Cancel adding {app_settings.example_name}",
        )

    return data_sample


def _update_sample_static_data(
    app_state: AppState,
    db: "DetaBase",
    field_defs: field_def.FieldDefsCollection,
    data_sample: DataSample,
    computed_only: bool = False,
):
    current_sample = app_state.current_sample
    if current_sample is None:
        raise RuntimeError("`current_sample` was `None`")

    static = field_def.update(
        field_defs=field_defs.static,
        session_state=st.session_state,
        modality="static",
        data_sample=data_sample,
        current_timestep=app_state.current_timestep,
        computed_only=computed_only,
    )

    data_sample = DataSample(static=static, temporal=data_sample.temporal, event=data_sample.event)

    deta_utils.update_sample(db=db, key=current_sample, data_sample=data_sample, field_defs=field_defs)

    app_state.interaction_state = "showing"

    # TODO: Temporal computed fields may depend on the static fields.
    # Need code to update them (all timesteps) upon static data change.


def _show_validation_error(validation_error_container: Any, msg: str):
    with validation_error_container:
        st.error(msg, icon="⛔")


def _update_sample_temporal_data(
    app_state: AppState,
    db: "DetaBase",
    field_defs: field_def.FieldDefsCollection,
    data_sample: DataSample,
    validation_error_container: Any,
):
    current_sample = app_state.current_sample
    current_timestep = app_state.current_timestep
    if current_sample is None:
        raise RuntimeError("`current_sample` was `None`")
    if current_timestep is None:
        raise RuntimeError("`current_timestep` was `None`")

    temporal = field_def.update(
        field_defs=field_defs.temporal,
        session_state=st.session_state,
        modality="temporal",
        data_sample=data_sample,
        current_timestep=current_timestep,
    )

    # --- --- ---
    # If user sets time index to a time index that is the same as the time index in another existing time-step,
    # raise a validation "error".
    time_indexes = utils.get_temporal_data_time_indexes(data_sample_temporal=data_sample.temporal)
    existing_time_indexes = utils.remove_ith_element(time_indexes, current_timestep)
    if temporal[DEFAULTS.time_index_field] in existing_time_indexes:
        validation_error_msg = f"Time index {temporal['time_index']} already exists, choose a different time index"
        _show_validation_error(validation_error_container, msg=validation_error_msg)
        return
    # --- --- ---

    data_sample.temporal[current_timestep] = temporal

    # --- --- ---
    # In case the newly added time-step is not in the same position in the array of timesteps, re-sort the timesteps.
    new_time_index = temporal[DEFAULTS.time_index_field]
    time_indexes = utils.get_temporal_data_time_indexes(data_sample_temporal=data_sample.temporal)
    time_indexes = sorted(time_indexes)
    temp_dict = {x[DEFAULTS.time_index_field]: x for x in data_sample.temporal}
    reordered = [temp_dict[ti] for ti in time_indexes]
    current_timestep = time_indexes.index(new_time_index)
    data_sample.temporal = reordered
    # --- --- ---

    data_sample = DataSample(static=data_sample.static, temporal=data_sample.temporal, event=data_sample.event)

    deta_utils.update_sample(db=db, key=current_sample, data_sample=data_sample, field_defs=field_defs)

    app_state.current_timestep = current_timestep
    app_state.interaction_state = "showing"

    # If any static fields are computed, since they may depend on the temporal data, re-compute them.
    _update_sample_static_data(
        app_state=app_state, db=db, field_defs=field_defs, data_sample=data_sample, computed_only=True
    )


def _add_sample_temporal_data(
    app_state: AppState,
    db: "DetaBase",
    field_defs: field_def.FieldDefsCollection,
    data_sample: DataSample,
    new_time_index: Any,
):
    current_sample = app_state.current_sample
    if current_sample is None:
        raise RuntimeError("`current_sample` was `None`")

    new_timestep = field_def.get_default(field_defs.temporal, modality="temporal", data_sample=data_sample)
    new_timestep[DEFAULTS.time_index_field] = new_time_index
    data_sample.temporal += [new_timestep]

    new_timestep = field_def.get_default_computed(
        field_defs=field_defs.temporal,
        modality="temporal",
        data_sample_before_computation=data_sample,
        current_timestep=app_state.current_timestep,
    )
    data_sample.temporal[-1] = new_timestep

    data_sample = DataSample(static=data_sample.static, temporal=data_sample.temporal, event=data_sample.event)

    deta_utils.update_sample(db=db, key=current_sample, data_sample=data_sample, field_defs=field_defs)

    new_timestep_idx = len(data_sample.temporal) - 1  # Last timestep is the newly-added timestep.
    app_state.current_timestep = new_timestep_idx
    app_state.interaction_state = "showing"


def _delete_sample_temporal_data(
    app_state: AppState,
    db: "DetaBase",
    field_defs: field_def.FieldDefsCollection,
    data_sample: DataSample,
):
    current_sample = app_state.current_sample
    current_timestep = app_state.current_timestep
    if current_sample is None:
        raise RuntimeError("`current_sample` was `None`")
    if current_timestep is None:
        raise RuntimeError("`current_timestep` was `None`")

    num_timesteps = len(data_sample.temporal)
    if num_timesteps == 1:
        raise RuntimeError("Cannot delete the last remaining time step")
    if current_timestep < 0 or current_timestep >= num_timesteps:
        raise RuntimeError(f"Invalid timestep to delete, index: {current_timestep}")

    del data_sample.temporal[current_timestep]

    data_sample = DataSample(static=data_sample.static, temporal=data_sample.temporal, event=data_sample.event)

    deta_utils.update_sample(db=db, key=current_sample, data_sample=data_sample, field_defs=field_defs)

    # Fall to the next or last time step after deletion:
    new_timestep_idx = min(current_timestep, len(data_sample.temporal) - 1)

    app_state.current_timestep = new_timestep_idx
    app_state.interaction_state = "showing"


def _prepare_data_table(data: Dict[str, Any], field_defs: Dict[str, field_def.FieldDef]) -> pd.DataFrame:
    sample_df_dict = {"Record": [], "Value": []}  # type: ignore [var-annotated]
    for field_name, value in data.items():
        sample_df_dict["Record"].append(field_defs[field_name].get_full_label())
        sample_df_dict["Value"].append(utils.format_with_field_formatting(value, field_defs[field_name]))
    return pd.DataFrame(sample_df_dict).set_index("Record", drop=True)


def static_data_table(
    app_settings: AppSettings,
    app_state: AppState,
    db: "DetaBase",
    field_defs: field_def.FieldDefsCollection,
    data_sample: DataSample,
    heading: str = "### Static Data",
    heading_row_columns: Sequence[Union[int, float]] = (0.3, 0.066, 0.734),
) -> None:
    col_title, col_edit, *_ = st.columns(heading_row_columns)

    with col_title:
        st.markdown(heading)
    with col_edit:
        edit_btn = st.button("🖊️", help=f"Edit {app_settings.example_name} static data")
        if edit_btn:
            app_state.interaction_state = "editing_static_data"

    if app_state.interaction_state != "editing_static_data":
        sample_df = _prepare_data_table(data=data_sample.static, field_defs=field_defs.static)
        st.table(sample_df)
    else:
        with st.form(key=DEFAULTS.key_edit_form_static):
            for field_name, dd in field_defs.static.items():
                value = data_sample.static[field_name]
                dd.render_edit_widget(value)
            st.form_submit_button(
                "Update",
                type="primary",
                on_click=_update_sample_static_data,
                kwargs=dict(app_state=app_state, db=db, field_defs=field_defs, data_sample=data_sample),
            )
        if app_state.interaction_state == "editing_static_data":
            cancel_edit_btn = st.button("Cancel", help=f"Cancel editing {app_settings.example_name} static data")
            if cancel_edit_btn:
                app_state.interaction_state = "showing"


def _set_current_timestep(app_state: AppState, data_sample: DataSample, timestep_selector_key: str):
    app_state.current_timestep = utils.get_temporal_data_time_indexes(data_sample_temporal=data_sample.temporal).index(
        st.session_state[timestep_selector_key]
    )


def _generate_new_time_index(field_defs: field_def.FieldDefsCollection, data_sample: DataSample) -> Any:
    max_time_index = max(utils.get_temporal_data_time_indexes(data_sample_temporal=data_sample.temporal))
    time_index_def = field_defs.temporal[DEFAULTS.time_index_field]
    if not isinstance(time_index_def, field_def.TimeIndexDef):
        raise RuntimeError(f"Time index field def was not an instance of {field_def.TimeIndexDef.__name__}")
    return time_index_def.get_next(max_time_index)


def _navigate_to_prev_timestep(app_state: AppState):
    if app_state.current_timestep > 0:
        app_state.current_timestep -= 1


def _navigate_to_next_timestep(app_state: AppState, n_timesteps: int):
    if app_state.current_timestep < (n_timesteps - 1):
        app_state.current_timestep += 1


def temporal_data_table(
    app_settings: AppSettings,
    app_state: AppState,
    db: "DetaBase",
    field_defs: field_def.FieldDefsCollection,
    data_sample: DataSample,
    heading: str = "### Temporal Data",
    split_heading_and_buttons: bool = False,
    heading_row_columns: Sequence[Union[int, float]] = (0.5, 0.133, 0.133, 0.134, 0.1),
    first_timestep_note: Optional[str] = None,
    last_timestep_note: Optional[str] = None,
) -> None:
    # If split_heading_and_buttons == True, the heading_row_columns should NOT include the dimensions for
    # the heading column - the hading will be on its own row.

    n_timesteps = len(data_sample.temporal)

    if not split_heading_and_buttons:
        col_title, col_edit, col_add, col_delete, *_ = st.columns(heading_row_columns)
    else:
        col_title = st.container()
        col_edit, col_add, col_delete, *_ = st.columns(heading_row_columns)
    col_left, col_select, col_right, col_steps = st.columns([0.15, 0.4, 0.15, 0.3])
    validation_error_container = st.container()

    with col_title:
        st.markdown(heading)
    with col_edit:
        edit_btn = st.button("🖊️", help=f"Edit {app_settings.example_name} time-step data")
        if edit_btn:
            app_state.interaction_state = "editing_temporal_data"
    with col_add:
        add_btn = st.button("➕", help=f"Add {app_settings.example_name} time-step")
        if add_btn:
            app_state.interaction_state = "adding_temporal_data"
    with col_delete:
        delete_btn = st.button("❌", help=f"Delete {app_settings.example_name} time-step", disabled=n_timesteps == 1)
        if delete_btn:
            app_state.interaction_state = "deleting_temporal_data"

    with col_left:
        disabled = app_state.current_timestep == 0
        st.button(
            "◀",
            help="Navigate to the previous time-step" if not disabled else None,
            disabled=app_state.current_timestep == 0,
            on_click=_navigate_to_prev_timestep,
            kwargs=dict(app_state=app_state),
        )
    with col_select:
        timestep_selector_key = "timestep_selector_key"
        st.selectbox(
            label="Select time step with time index:",
            label_visibility="collapsed",
            key=timestep_selector_key,
            options=utils.get_temporal_data_time_indexes(data_sample_temporal=data_sample.temporal),
            index=app_state.current_timestep,
            on_change=_set_current_timestep,
            kwargs=dict(app_state=app_state, data_sample=data_sample, timestep_selector_key=timestep_selector_key),
            format_func=lambda x: utils.format_with_field_formatting(x, field_defs.temporal[DEFAULTS.time_index_field]),
        )
    with col_right:
        disabled = app_state.current_timestep == (n_timesteps - 1)
        st.button(
            "▶",
            help="Navigate to the next time-step" if not disabled else None,
            disabled=app_state.current_timestep == (n_timesteps - 1),
            on_click=_navigate_to_next_timestep,
            kwargs=dict(app_state=app_state, n_timesteps=n_timesteps),
        )
    with col_steps:
        add_vertical_space(1)
        st.markdown(f"`time-step: {app_state.current_timestep + 1}/{n_timesteps}`")

    if app_state.interaction_state == "adding_temporal_data":
        new_time_index = _generate_new_time_index(field_defs=field_defs, data_sample=data_sample)
        faux_confirm_modal(
            panel_type="info",
            panel_text=(
                f"This action will create a new time-step for the {app_settings.example_name} with an auto-generated"
                f"future time index: {new_time_index}. You will be able to use the edit '🖊️' button to update the "
                "time-step data. Please confirm."
            ),
            panel_icon="ℹ️",
            confirm_btn_on_click=_add_sample_temporal_data,
            confirm_btn_on_click_kwargs=dict(
                app_state=app_state,
                db=db,
                field_defs=field_defs,
                data_sample=data_sample,
                new_time_index=new_time_index,
            ),
            confirm_btn_help="Confirm adding new time-step",
            cancel_btn_on_click=_reset_interaction_state,
            cancel_btn_on_click_kwargs=dict(app_state=app_state),
            cancel_btn_help="Cancel adding new time-step",
            button_cols_split=[0.3, 0.3, 0.4],
        )
    if app_state.interaction_state == "deleting_temporal_data":
        faux_confirm_modal(
            panel_type="error",
            panel_text=(
                "This action will delete the currently selected time-step's data (time index: "
                f"{data_sample.temporal[app_state.current_timestep]['time_index']})."
                "It is not reversible. Please confirm."
            ),
            panel_icon="⚠️",
            confirm_btn_on_click=_delete_sample_temporal_data,
            confirm_btn_on_click_kwargs=dict(
                app_state=app_state, db=db, data_sample=data_sample, field_defs=field_defs
            ),
            confirm_btn_help="Confirm deleting the time-step data",
            cancel_btn_on_click=_reset_interaction_state,
            cancel_btn_on_click_kwargs=dict(app_state=app_state),
            cancel_btn_help="Cancel deleting the time-step data",
            button_cols_split=[0.3, 0.3, 0.4],
        )

    if first_timestep_note is not None and app_state.current_timestep == 0:
        st.info(first_timestep_note)
    if last_timestep_note is not None and app_state.current_timestep == (n_timesteps - 1):
        st.info(last_timestep_note)

    if app_state.interaction_state != "editing_temporal_data":
        timestep_df = _prepare_data_table(
            data=data_sample.temporal[app_state.current_timestep], field_defs=field_defs.temporal
        )
        st.table(timestep_df)
    else:
        with st.form(key=DEFAULTS.key_edit_form_temporal):
            for field_name, dd in field_defs.temporal.items():
                value = data_sample.temporal[app_state.current_timestep][field_name]
                dd.render_edit_widget(value)
            st.form_submit_button(
                "Update",
                type="primary",
                on_click=_update_sample_temporal_data,
                kwargs=dict(
                    app_state=app_state,
                    db=db,
                    field_defs=field_defs,
                    data_sample=data_sample,
                    validation_error_container=validation_error_container,
                ),
            )
        if app_state.interaction_state == "editing_temporal_data":
            cancel_edit_btn = st.button("Cancel", help=f"Cancel editing {app_settings.example_name} temporal data")
            if cancel_edit_btn:
                app_state.interaction_state = "showing"


def temporal_data_chart(data_sample: DataSample, field_defs: field_def.FieldDefsCollection):
    feature_keys = list(field_defs.temporal.keys())
    feature_readable_names = [fd.get_full_label() for _, fd in field_defs.temporal.items()]
    selectbox_feature_keys = [feature_key for feature_key in feature_keys if feature_key != DEFAULTS.time_index_field]
    selectbox_feature_readable_names = [
        fd.get_full_label()
        for feature_key, fd in field_defs.temporal.items()
        if feature_key != DEFAULTS.time_index_field
    ]

    selected_feature_readable_name = st.selectbox(label="Time series", options=selectbox_feature_readable_names)
    selected_feature_readable_name = cast(str, selected_feature_readable_name)
    selected_feature_index = selectbox_feature_readable_names.index(selected_feature_readable_name)
    selected_feature_key = selectbox_feature_keys[selected_feature_index]

    df = utils.get_temporal_data_as_df(data_sample.temporal)
    # For debugging, preview temporal data as a table:
    # st.write(df)

    fig = px.line(
        df,
        y=selected_feature_key,
        labels={k: v for k, v in zip(feature_keys, feature_readable_names)},
    )
    st.plotly_chart(fig)


class RiskPredictionCallback(Protocol):
    def __call__(
        self,
        data_sample: DataSample,
        time_max: Any,
        time_resolution: Any,
        **kwargs,
    ) -> pd.DataFrame:
        ...


def risk_estimation_time_max_slider(min_value: Any, max_value: Any, step: Any, initial_value: Any) -> None:
    return st.slider(
        label="Prediction time limit",
        min_value=min_value,
        max_value=max_value,
        value=initial_value,
        step=step,
    )


def risk_prediction_chart(
    data_sample: DataSample,
    time_axis_title: str,
    risk_axis_title: str,
    time_max: Any,
    time_resolution: Any,
    risk_prediction_callback: RiskPredictionCallback,
    time_format: Optional[str] = None,
    risk_format: Optional[str] = None,
    **kwargs,
):
    risk_predictions = risk_prediction_callback(
        data_sample,
        time_max=time_max,
        time_resolution=time_resolution,
        **kwargs,
    )
    fig = px.area(
        risk_predictions,
        y="risk_prediction",
        color_discrete_sequence=["red"],
        range_y=(0.0, 1.0 + 0.1),  # `+ 0.1` to make sure the grid-line at y=1 gets displayed.
    )
    fig.update_traces(
        hovertemplate=(
            "<b>"
            + risk_axis_title
            + "</b>: %{y"
            + ((":" + risk_format) if risk_format is not None else "")
            + "}<br><b>"
            + time_axis_title
            + "</b>: %{x"
            + ((":" + time_format) if time_format is not None else "")
            + "}<br>"
        )
    )
    fig.update_xaxes(title=time_axis_title)
    fig.update_yaxes(title=risk_axis_title)
    fig.update_layout(yaxis_tickformat=time_format)
    fig.update_layout(yaxis_tickformat=risk_format)
    st.plotly_chart(fig, use_container_width=True)
    # For debug, show data:
    # st.write(risk_predictions)


def debug_info(
    data_sample: DataSample,
) -> None:
    st.markdown("### Session state:")
    st.write(st.session_state)
    st.markdown("### Sample data:")
    st.write(data_sample)
    # st.markdown("### Database:")
    # st.write(all_data.items)
