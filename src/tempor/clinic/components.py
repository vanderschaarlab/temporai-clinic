import os
from typing import TYPE_CHECKING, Any, Dict, List, NamedTuple, Optional

import pandas as pd
import streamlit as st
from streamlit_extras import add_vertical_space

from . import db_utils
from .app_state import AppState
from .const import DEFAULTS, STATE_KEYS

if TYPE_CHECKING:
    from deta import _Base as DetaBase

    from .data_def import DataDef


class AppSettings(NamedTuple):
    name: str
    example_name: str


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
) -> None:
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


def _set_current_example(app_state: AppState, sample_selector_key: str):
    app_state.current_example = st.session_state[sample_selector_key]


def _delete_current_example(app_state: AppState, db: "DetaBase"):
    current_sample = app_state.current_example
    if current_sample is None:
        raise RuntimeError("`current_sample` was `None`")
    db_utils.delete_sample(db=db, key=current_sample)
    app_state.current_example = None


def _add_new_sample(app_state: AppState, db: "DetaBase", key: str, data_defs: Dict[str, "DataDef"]):
    db_utils.add_sample(db=db, key=key, data_defs=data_defs)
    app_state.current_example = key


def sample_selector(
    app_settings: AppSettings,
    app_state: AppState,
    db: "DetaBase",
    data_defs: Dict[str, "DataDef"],
    sample_keys: List[str],  # TODO: Is this needed here like this? Rethink.
) -> Dict[str, Any]:
    col_patient_select, col_add, col_delete, _ = st.columns([0.8, 0.2 / 3, 0.2 / 3, 0.2 / 3])

    with col_patient_select:
        print("What's app_state.current_example", app_state.current_example)
        sample_selector_key = "sample_selector"
        st.selectbox(
            label=app_settings.example_name.capitalize(),
            options=sample_keys,
            index=sample_keys.index(app_state.current_example) if app_state.current_example is not None else 0,
            key=sample_selector_key,
            on_change=_set_current_example,
            kwargs=dict(app_state=app_state, sample_selector_key=sample_selector_key),
        )
        if app_state.current_example is None:
            app_state.current_example = sample_keys[0]

        example_data: Dict[str, Any] = db_utils.get_sample(key=app_state.current_example, db=db, data_defs=data_defs)

    with col_add:
        add_vertical_space.add_vertical_space(2)
        add_btn = st.button("➕", help=f"Add {app_settings.example_name}")
    with col_delete:
        add_vertical_space.add_vertical_space(2)
        delete_btn = st.button("❌", help=f"Delete {app_settings.example_name}")

    if add_btn:
        app_state.example_state = "add"
    elif delete_btn:
        app_state.example_state = "delete"
    else:
        app_state.example_state = "show"

    if app_state.example_state == "delete":
        st.markdown("---")
        st.error(
            f"This action will delete the currently selected {app_settings.example_name} "
            f"(ID: {app_state.current_example}). "
            "It is not reversible. Please confirm.",
            icon="⚠️",
        )
        col_confirm_deletion_btn, col_cancel_deletion_btn, _ = st.columns([0.2, 0.2, 0.6])
        with col_confirm_deletion_btn:
            st.button(
                "Confirm",
                type="primary",
                on_click=_delete_current_example,
                kwargs=dict(app_state=app_state, db=db),
            )
        with col_cancel_deletion_btn:
            cancel_delete_btn = st.button(
                "Cancel", key="cancel_delete_example", help=f"Cancel deleting {app_settings.example_name}"
            )
            if cancel_delete_btn:
                app_state.example_state = "show"
        st.markdown("---")

    if app_state.example_state == "add":
        st.markdown("---")
        new_key = db_utils.generate_new_sample_key()
        st.info(
            f"This action will create a new 'empty' {app_settings.example_name} with auto-generated ID: {new_key}. "
            f"You will be able to use the edit '🖊️' buttons to update the {app_settings.example_name} data. "
            "Please confirm.",
            icon="ℹ️",
        )
        col_confirm_addition_btn, col_cancel_addition_btn, _ = st.columns([0.2, 0.2, 0.6])
        with col_confirm_addition_btn:
            st.button(
                "Confirm",
                type="primary",
                on_click=_add_new_sample,
                kwargs=dict(app_state=app_state, db=db, key=new_key, data_defs=data_defs),
            )
        with col_cancel_addition_btn:
            cancel_add_btn = st.button(
                "Cancel", key="cancel_add_example", help=f"Cancel adding {app_settings.example_name}"
            )
            if cancel_add_btn:
                app_state.example_state = "show"
        st.markdown("---")

    return example_data


def _update_sample_static_data(app_state: AppState, db: "DetaBase", data_defs: Dict[str, "DataDef"]):
    current_sample = app_state.current_example
    if current_sample is None:
        raise RuntimeError("`current_sample` was `None`")

    sample_data = dict()
    for field_name in data_defs.keys():
        key = f"{STATE_KEYS.data_static_field_prefix}_{field_name}"
        sample_data[field_name] = st.session_state[key]

    db_utils.update_sample(db=db, key=current_sample, sample_data=sample_data)


def static_data_table(
    app_settings: AppSettings,
    app_state: AppState,
    db: "DetaBase",
    data_defs: Dict[str, "DataDef"],
    sample_data: Dict[str, Any],
) -> None:
    col_static_title, col_edit, col_cancel_edit, _ = st.columns([0.3, 0.2 / 3, 0.2, 1 - (2 * 0.2 + 0.2 / 3)])

    with col_static_title:
        st.markdown("### Static Data")
    with col_edit:
        edit_btn = st.button(
            "🖊️",
            help=f"Edit {app_settings.example_name} static data",
            disabled=True if app_state.example_state in ("delete", "add") else False,
        )
        if edit_btn:
            app_state.example_state = "edit"
    with col_cancel_edit:
        if app_state.example_state == "edit":
            cancel_edit_btn = st.button("Cancel", help=f"Cancel editing {app_settings.example_name} static data")
            if cancel_edit_btn:
                app_state.example_state = "show"

    if app_state.example_state in ("show", "delete", "add"):
        sample_df_dict = {"Record": [], "Value": []}  # type: ignore [var-annotated]
        for field_name, value in sample_data.items():
            if field_name != "key":  # Skip the record key.
                sample_df_dict["Record"].append(data_defs[field_name].readable_name)
                sample_df_dict["Value"].append(value)
        sample_df = pd.DataFrame(sample_df_dict).set_index("Record", drop=True)
        st.table(sample_df)

    elif app_state.example_state == "edit":
        with st.form("form"):
            for field_name, data_def in data_defs.items():
                value = sample_data[field_name]
                data_def.render_edit_widget(value)
            st.form_submit_button(
                "Update",
                type="primary",
                on_click=_update_sample_static_data,
                kwargs=dict(app_state=app_state, db=db, data_defs=data_defs),
            )
