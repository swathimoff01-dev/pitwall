"""Test text is shortened from FIA stewards' decision documents (2023 season, fia.com)."""

from datetime import date

import pytest

from pitwall.decision_parser import (
    classify_penalty,
    extract_articles,
    match_driver_name,
    parse_decision_text,
)

RUSSELL_MONACO = """Document
51
Date
28 May 2023
Time
16:39
No / Driver
63 - George Russell
Competitor
Mercedes-AMG PETRONAS F1 Team
Time
16:15
Session
Race
Fact
Left and rejoined the track in an unsafe manner at turn 5.
Infringment Breach of Appendix L, Chapter IV, Article 2 c) of the International Sporting Code.
Decision
5 second time penalty.
2 penalty points (total of 6 for the 12 month period)
Reason
Rejoined the track in an unsafe manner, causing a collision.
Competitors are reminded that they have the right to appeal.
Tim Mayer"""

DE_VRIES_BAHRAIN = """Document
15
Date
03 March 2023
Time
20:10
2023 BAHRAIN GRAND PRIX
No / Driver
21 - Nyck de Vries
Competitor
Scuderia AlphaTauri
Time
18:25
Session
Practice 2
Fact
Alleged unsafe release.
Offence
Alleged breach of Article 34.14 a) of the FIA Formula One Sporting Regulations.
Decision
No further action.
Reason
Both drivers reacted in an appropriate manner.
Competitors are reminded that they have the right to appeal."""


# ---- whole documents ----

def test_penalty_decision_fields():
    d = parse_decision_text(RUSSELL_MONACO)
    assert (d.doc_no, d.doc_date) == (51, date(2023, 5, 28))
    assert (d.car_no, d.driver, d.session) == (63, "George Russell", "Race")
    assert d.articles == ["ISC App L Ch IV Art 2 c)"]
    assert (d.penalty_type, d.time_penalty_s, d.penalty_points) == ("time_penalty", 5, 2)
    assert d.reason == "Rejoined the track in an unsafe manner, causing a collision."
    assert d.parse_status == "full"


def test_no_further_action_with_offence_label():
    d = parse_decision_text(DE_VRIES_BAHRAIN)
    assert d.articles == ["SR 34.14 a)"]
    assert d.session == "Practice 2"
    assert (d.penalty_type, d.penalty_points) == ("no_further_action", None)


def test_label_glued_to_value():
    text = ("Competitor\nScuderia Ferrari\nFact\nPit lane speeding.\n"
            "InfringementBreach of Article 34.7 of the FIA Formula One Sporting Regulations.\n"
            "Decision\n5 second time penalty.")
    assert parse_decision_text(text).articles == ["SR 34.7"]


def test_non_breaking_spaces_and_long_dashes():
    pdf_like = RUSSELL_MONACO.replace(" ", "\xa0").replace("63 - ", "63 – ")
    d = parse_decision_text(pdf_like)
    assert (d.car_no, d.driver) == (63, "George Russell")
    assert d.articles == ["ISC App L Ch IV Art 2 c)"]
    assert (d.penalty_type, d.penalty_points) == ("time_penalty", 2)


# ---- pieces ----

def test_penalty_classification():
    assert classify_penalty("5 place grid penalty.")[0] == "grid_penalty"
    assert classify_penalty("The competitor is fined €10,000.")[0] == "fine"
    assert classify_penalty("Drive through penalty.")[0] == "drive_through"
    assert classify_penalty("10 second time penalty.") == ("time_penalty", 10)


def test_driver_name_matching():
    candidates = [("de_vries", "de Vries"), ("zhou", "Zhou"), ("perez", "Pérez")]
    assert match_driver_name(candidates, "Nyck de Vries") == "de_vries"
    assert match_driver_name(candidates, "Zhou Guanyu") == "zhou"
    assert match_driver_name(candidates, "Sergio Perez") == "perez"


# ---- every citation phrasing found in the real 2023 documents ----

ARTICLE_CASES = [
    ("Breach of Appendix L, Chapter III , Article 5 of the FIA International Sporting Code.",
     ["ISC App L Ch III Art 5"]),
    ("Alleged breach of Article 33.4 and 37.5 of the FIA Formula One Sporting Regulations.",
     ["SR 33.4", "SR 37.5"]),
    ("Breach of Article 34.7 of the FIA Formula One Sporting Regulation and non- compliance "
     "with Race Director's Event Note", ["SR 34.7"]),
    ("Alleged breach of Articles 35.1 b) of the FIA Formula One Sporting Regulations.",
     ["SR 35.1 b)"]),
    ("Breach of Article 54.4 (c) of the FIA Formula One Sporting Regulations", ["SR 54.4 c)"]),
    ("Alleged breach of Article 54.4(c) of the FIA Formula One Sporting Regulations.",
     ["SR 54.4 c)"]),
    ("Breach of Article 2b Chapter IV, Appendix L of the FIA International Sporting Code.",
     ["ISC App L Ch IV Art 2 b)"]),
    ("Breach of Article 12.2.1 i) of the International Sporting Code.", ["ISC 12.2.1 i)"]),
    ("Breach of Article 12.2.1.l of the of the FIA International Sporting Code.",
     ["ISC 12.2.1 l)"]),
    ("Breach of Article 6.5.2 of the FIA Formula One Technical Regulations.", ["TR 6.5.2"]),
    ("Breach of Art. 34.14 of the FIA Formula One Sporting Regulations Breach of Art. 26.6 "
     "and Art 26.7 of the FIA Formula One Sporting Regulations.",
     ["SR 34.14", "SR 26.6", "SR 26.7"]),
    ("Breaches of Articles 28.2, 29.2, 40.3 and 40.9 of the FIA Formula One Sporting Regulations.",
     ["SR 28.2", "SR 29.2", "SR 40.3", "SR 40.9"]),
]


@pytest.mark.parametrize("text, expected", ARTICLE_CASES)
def test_extract_articles(text, expected):
    assert extract_articles(text) == expected