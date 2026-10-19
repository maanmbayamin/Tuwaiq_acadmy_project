"""The hand-built phone UI (components/phone/index.html), declared once from an importable module."""
import streamlit.components.v1 as components

from munjiz import config

phone = components.declare_component("munjiz_phone", path=str(config.ROOT / "components" / "phone"))
