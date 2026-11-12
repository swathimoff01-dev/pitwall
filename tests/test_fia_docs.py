from pitwall.fia_docs import parse_doc_links, parse_season_paths, safe_url

EVENT_HTML = """
<ul>
 <li><a href="/system/files/decision-document/2025_dutch_grand_prix_-_decision_-_car_16_-_alleged_causing_a_collision.pdf">
   <span>Doc 55 - Decision - Car 16 - Alleged Causing a Collision</span>
   <span>Published on 31.08.25 20:14 CET</span></a></li>
 <li><a href="/system/files/decision-document/2025_dutch_grand_prix_-_final_race_classification.pdf">
   Doc 60 - Final Race Classification Published on 31.08.25 20:55 CET</a></li>
 <li>Recalled - Doc 13 - Summons - Pit Lane Incident <span>Published on 29.08.25 17:07 CET</span></li>
 <li><a href="/some/other/page">Not a document</a></li>
</ul>
"""


def test_parses_linked_documents_only():
    links = parse_doc_links(EVENT_HTML, 2025, "Dutch Grand Prix")
    assert [link.doc_no for link in links] == [55, 60]  # recalled doc and other links skipped


def test_document_fields():
    doc = parse_doc_links(EVENT_HTML, 2025, "Dutch Grand Prix")[0]
    assert doc.category == "Decision"
    assert doc.title == "Decision - Car 16 - Alleged Causing a Collision"
    assert doc.published == "2025-08-31 20:14"
    assert doc.url.startswith("https://www.fia.com/system/files/decision-document/")


def test_category_without_dash_is_whole_title():
    assert parse_doc_links(EVENT_HTML, 2025, "Dutch Grand Prix")[1].category == "Final Race Classification"


def test_season_paths_found_in_links_or_dropdowns():
    html = ('<a href="/documents/championships/fia-formula-one-world-championship-14/season/season-2024-1111">'
            '<option value="/documents/championships/fia-formula-one-world-championship-14/season/season-2023-2222">')
    paths = parse_season_paths(html)
    assert paths[2024].endswith("season-2024-1111")
    assert paths[2023].endswith("season-2023-2222")

def test_older_pages_without_doc_numbers():
    html = ('<a href="/sites/default/files/decision-document/2023 Saudi Arabian Grand Prix - '
            'Final Race Classification.pdf">Final Race Classification Published on 19.03.23 23:15 CET</a>')
    doc = parse_doc_links(html, 2023, "Saudi Arabian Grand Prix")[0]
    assert doc.doc_no is None
    assert doc.title == "Final Race Classification"
    assert doc.published == "2023-03-19 23:15"

def test_safe_url_encodes_spaces_and_bare_percent():
    raw = "https://www.fia.com/x/2023 Saudi - within 107%.pdf"
    fixed = "https://www.fia.com/x/2023%20Saudi%20-%20within%20107%25.pdf"
    assert safe_url(raw) == fixed
    assert safe_url(fixed) == fixed  # already-encoded URLs are left as they are