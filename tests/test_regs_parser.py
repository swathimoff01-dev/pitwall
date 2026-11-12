from datetime import date
from pathlib import Path

from pitwall.regs_parser import chunk_lines, clean_pages, file_metadata

LINES = [
    "53)", "SPRINT SESSION AND THE RACE",
    "53.1", "During a sprint session or the race, drivers leaving the pit lane",
    "may only do so when the light is green.",
    "54)", "INCIDENTS DURING THE SPRINT SESSION OR THE RACE",
    "54.1", "The Race Director may report any on-track incident to the stewards.",
    "The stewards may also investigate an Incident noted by themselves.",
    "54.2", "a)", "It shall be at the discretion of the stewards to decide",
    "if any driver should be penalised.",
    "b)", "If an Incident is under investigation a message will be sent.",
    "54.3 the stewards may impose penalty points.",  # wrapped cross-reference, not a heading
]


def by_no(chunks):
    return {c.article_no: c for c in chunks}


def test_one_chunk_per_sub_article():
    assert list(by_no(chunk_lines(LINES))) == ["53.1", "54.1", "54.2"]


def test_parent_title_attached():
    assert by_no(chunk_lines(LINES))["54.2"].title == "INCIDENTS DURING THE SPRINT SESSION OR THE RACE"


def test_wrapped_lines_joined():
    assert by_no(chunk_lines(LINES))["53.1"].body == (
        "During a sprint session or the race, drivers leaving the pit lane "
        "may only do so when the light is green."
    )


def test_list_items_start_new_lines():
    body = by_no(chunk_lines(LINES))["54.2"].body
    assert body.startswith(
        "a) It shall be at the discretion of the stewards to decide if any driver should be penalised.\n"
        "b) If an Incident"
    )


def test_number_inside_text_is_not_a_heading():
    assert "54.3 the stewards may impose penalty points." in by_no(chunk_lines(LINES))["54.2"].body


def test_later_occurrence_replaces_table_of_contents():
    lines = ["54)", "INCIDENTS", "54.1", "Incidents ........ 62",
             "54)", "INCIDENTS", "54.1", "Real text."]
    assert by_no(chunk_lines(lines))["54.1"].body == "Real text."


def test_headers_footers_and_page_numbers_removed():
    header = ["2025 Formula 1 Sporting Regulations", "Issue 5"]
    pages = [header + ["1/3", "a)", "text one"],
             header + ["2/3", "text two"],
             header + ["3/3", "a)", "text three"]]
    assert clean_pages(pages) == ["a)", "text one", "text two", "a)", "text three"]


def test_metadata_from_fia_filename():
    p = Path("fia_2023_formula_1_sporting_regulations_-_issue_7_-_2023-10-25-v2.pdf")
    assert file_metadata(p) == (2023, 7, date(2023, 10, 25))