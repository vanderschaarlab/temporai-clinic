from typing import Optional

import streamlit as st

from . import const

# from typing import TYPE_CHECKING


class AppState:
    def __init__(self) -> None:
        if const.STATE_KEYS.current_sample not in st.session_state:
            st.session_state[const.STATE_KEYS.current_sample] = None
        if const.STATE_KEYS.current_timestep not in st.session_state:
            st.session_state[const.STATE_KEYS.current_timestep] = 0
        if const.STATE_KEYS.interaction_state not in st.session_state:
            st.session_state[const.STATE_KEYS.interaction_state] = "showing"

    @property
    def current_sample(self) -> Optional[str]:
        return st.session_state[const.STATE_KEYS.current_sample]

    @current_sample.setter
    def current_sample(self, value: Optional[str]) -> None:
        st.session_state[const.STATE_KEYS.current_sample] = value

    @property
    def current_timestep(self) -> int:
        return st.session_state[const.STATE_KEYS.current_timestep]

    @current_timestep.setter
    def current_timestep(self, value: int) -> None:
        st.session_state[const.STATE_KEYS.current_timestep] = value

    @property
    def interaction_state(self) -> const.InteractionState:
        return st.session_state[const.STATE_KEYS.interaction_state]

    @interaction_state.setter
    def interaction_state(self, value: const.InteractionState) -> None:
        st.session_state[const.STATE_KEYS.interaction_state] = value
