import os
from typing import Optional

import streamlit as st

from .const import DEFAULTS


def sidebar(
    app_title: str,
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
            ### {app_title}
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
