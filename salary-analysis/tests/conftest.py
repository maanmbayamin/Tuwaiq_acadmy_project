import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PAGE_SCRIPT = """
import os, sys
sys.path.insert(0, {root!r})
os.chdir({root!r})
import streamlit as st
import app
app.PAGES.update(app.build_pages())
st.navigation(list(app.PAGES.values()), position="top")
app.{page}()
"""


@pytest.fixture
def open_page():
    """Return a function that renders one app page in Streamlit's test runner."""

    def _open(page: str) -> AppTest:
        at = AppTest.from_string(PAGE_SCRIPT.format(root=str(ROOT), page=page), default_timeout=180)
        return at.run()

    return _open
