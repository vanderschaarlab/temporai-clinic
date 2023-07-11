from typing import Optional

import streamlit as st

from . import const

# from typing import TYPE_CHECKING


class AppState:
    def __init__(self) -> None:
        if const.STATE_KEYS.cur_example not in st.session_state:
            st.session_state[const.STATE_KEYS.cur_example] = None
        if const.STATE_KEYS.example_state not in st.session_state:
            st.session_state[const.STATE_KEYS.example_state] = "show"

    @property
    def current_example(self) -> Optional[str]:
        return st.session_state[const.STATE_KEYS.cur_example]

    @current_example.setter
    def current_example(self, value: Optional[str]) -> None:
        st.session_state[const.STATE_KEYS.cur_example] = value

    @property
    def example_state(self) -> const.ExampleStates:
        return st.session_state[const.STATE_KEYS.example_state]

    @example_state.setter
    def example_state(self, value: const.ExampleStates) -> None:
        st.session_state[const.STATE_KEYS.example_state] = value
