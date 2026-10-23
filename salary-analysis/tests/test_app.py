"""Renders every page of the Streamlit app and exercises its main controls."""

import pytest

from src import features as F

PAGES = ["page_overview", "page_data", "page_explore", "page_saudi", "page_model", "page_estimate"]


@pytest.mark.parametrize("page", PAGES)
def test_page_renders_without_errors(open_page, page):
    at = open_page(page)
    assert not at.exception, [e.value for e in at.exception]
    assert at.title, "every page has a title"
    assert at.markdown or at.caption, "every page explains itself"


def test_overview_unit_switch_changes_the_hero_sentence(open_page):
    at = open_page("page_overview")
    assert "$150,000 a year" in " ".join(h.proto.body for h in at.get("html"))
    at.segmented_control(key="unit_overview").set_value("SAR / month").run()
    assert not at.exception
    assert "46,875 SAR a month" in " ".join(h.proto.body for h in at.get("html"))


def test_overview_role_pills_update_the_answer(open_page):
    at = open_page("page_overview")
    at.pills(key="hero_role").set_value("Data Engineer").run()
    assert not at.exception
    assert "Data Engineers earn a median of $140,000" in " ".join(h.proto.body for h in at.get("html"))


def test_explore_filters_update_the_numbers(open_page):
    at = open_page("page_explore")
    assert at.metric[0].value == "13,972"
    at.pills(key="f_exp").set_value(["Executive"]).run()
    assert not at.exception
    expected = int((F.load_clean().experience_level == "EX").sum())
    assert at.metric[0].value == f"{expected:,}"


def test_explore_empty_selection_shows_a_message(open_page):
    at = open_page("page_explore")
    at.slider(key="f_years").set_value((2020, 2020)).run()
    at.multiselect(key="f_region").set_value(["Oceania"]).run()
    at.pills(key="f_exp").set_value(["Executive"]).run()
    assert not at.exception
    assert any("No salaries match" in i.value for i in at.info)
    assert not at.metric


def test_explore_world_map_and_mean_views(open_page):
    at = open_page("page_explore")
    at.segmented_control(key="ex_loc_view").set_value("World map").run()
    at.segmented_control(key="ex_stat").set_value("Mean").run()
    assert not at.exception


def test_saudi_page_switches_role(open_page):
    at = open_page("page_saudi")
    at.segmented_control(key="sa_role").set_value("Data Analyst").run()
    assert not at.exception


def test_estimate_for_saudi_arabia_shows_a_warning(open_page):
    at = open_page("page_estimate")
    at.selectbox(key="es_country").set_value("Saudi Arabia").run()
    assert not at.exception
    assert any("only 2 salaries from Saudi companies" in w.value for w in at.warning)


def test_estimate_changes_with_experience(open_page):
    at = open_page("page_estimate")
    def estimate(at_):
        return next(h.proto.body for h in at_.get("html") if "big-estimate" in h.proto.body)
    senior = estimate(at)
    at.segmented_control(key="es_level").set_value("Entry").run()
    assert not at.exception
    assert estimate(at) != senior
