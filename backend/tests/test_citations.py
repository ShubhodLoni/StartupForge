from app.citations import build_citations, clean_markers, clean_model
from app.schemas import ResearchFindings, Source
from tests.conftest import RESEARCH


def src(i):
    return Source(id=i, title=f"S{i}", url=f"https://example.org/{i}", snippet="text", query="q")


def test_keeps_valid_markers():
    assert clean_markers("Claim [1].", {1}) == ("Claim [1].", {1})


def test_removes_unknown_markers():
    assert clean_markers("Claim [9].", {1}) == ("Claim.", set())


def test_filters_mixed_markers():
    assert clean_markers("Claim [3, 1, 9].", {1, 3}) == ("Claim [1, 3].", {1, 3})


def test_removes_all_markers_when_no_sources():
    assert clean_markers("A [1] and B [2].", set()) == ("A and B.", set())


def test_clean_model_walks_all_string_fields():
    cleaned, used = clean_model(RESEARCH, [src(1)])
    assert isinstance(cleaned, ResearchFindings)
    assert cleaned.pain_points == ["Phone-based booking wastes staff time [1]"]
    assert cleaned.key_trends == ["Patients increasingly expect online booking"]
    assert used == {1}


def test_build_citations_only_includes_cited_sources():
    citations = build_citations([src(1), src(2), src(3)], RESEARCH)
    assert [c.id for c in citations] == [1, 2]
    assert citations[0].url == "https://example.org/1"
