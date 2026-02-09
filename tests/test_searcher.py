"""Tests for src/searcher.py — CORD19Searcher class."""

import math

import pytest

from searcher import CORD19Searcher
from constants import EXPECTED_DOC_COUNT


# ── Return structure ────────────────────────────────────────────────────────

def test_search_returns_dict(searcher):
    result = searcher.search("COVID")
    assert isinstance(result, dict)
    assert set(result.keys()) == {"results", "total", "page", "total_pages", "query"}


def test_search_query_echoed(searcher):
    result = searcher.search("vaccine efficacy")
    assert result["query"] == "vaccine efficacy"


def test_result_fields(searcher):
    result = searcher.search("vaccine")
    for r in result["results"]:
        assert set(r.keys()) == {
            "cord_uid", "title", "abstract", "authors",
            "journal", "publish_time", "url", "score",
        }


def test_result_field_values(searcher):
    """Known document uid001 returns correct metadata."""
    result = searcher.search("COVID-19 vaccine efficacy clinical trials")
    uids = [r["cord_uid"] for r in result["results"]]
    assert "uid001" in uids
    hit = next(r for r in result["results"] if r["cord_uid"] == "uid001")
    assert hit["journal"] == "Lancet"
    assert hit["authors"] == "Smith, J; Jones, A"


# ── Basic search ────────────────────────────────────────────────────────────

def test_search_finds_matching_documents(searcher):
    result = searcher.search("vaccine")
    assert result["total"] > 0
    assert len(result["results"]) > 0


def test_search_no_results(searcher):
    result = searcher.search("xyznonexistentterm")
    assert result["total"] == 0
    assert result["results"] == []
    assert result["total_pages"] == 0


# ── Multi-field search ──────────────────────────────────────────────────────

def test_search_matches_title(searcher):
    """'lockdown' appears only in uid005 title."""
    result = searcher.search("lockdown")
    assert result["total"] > 0


def test_search_matches_abstract(searcher):
    """'antiviral' appears only in uid004 abstract."""
    result = searcher.search("antiviral")
    assert result["total"] > 0


# ── BM25F ranking ───────────────────────────────────────────────────────────

def test_bm25_scores_are_positive(searcher):
    result = searcher.search("vaccine")
    for r in result["results"]:
        assert r["score"] > 0


def test_bm25_results_sorted_by_score(searcher):
    result = searcher.search("COVID-19 vaccine")
    scores = [r["score"] for r in result["results"]]
    assert scores == sorted(scores, reverse=True)


# ── Boolean queries ─────────────────────────────────────────────────────────

def test_or_query(searcher):
    result = searcher.search("vaccine OR transmission")
    uids = [r["cord_uid"] for r in result["results"]]
    # Should include vaccine papers AND transmission papers
    assert any(u in uids for u in ["uid001", "uid003"])
    assert "uid002" in uids


def test_not_query(searcher):
    """ANDNOT query excludes documents containing the negated term."""
    base = searcher.search("treatment")
    excluded = searcher.search("treatment ANDNOT hydroxychloroquine")
    assert excluded["total"] < base["total"]


def test_phrase_query(searcher):
    result = searcher.search('"vaccine efficacy"')
    assert result["total"] > 0


def test_nested_boolean_query(searcher):
    result = searcher.search("mask AND (efficacy OR effectiveness)")
    uids = [r["cord_uid"] for r in result["results"]]
    assert "uid006" in uids


# ── Stemming ────────────────────────────────────────────────────────────────

def test_stemming_singular_finds_plural(searcher):
    """Searching 'vaccine' (singular) finds papers with 'vaccines' (plural)."""
    result = searcher.search("vaccine")
    uids = [r["cord_uid"] for r in result["results"]]
    assert "uid003" in uids  # title contains "vaccines"


def test_stemming_plural_finds_singular(searcher):
    """Searching 'vaccines' finds papers with 'vaccine'."""
    result = searcher.search("vaccines")
    uids = [r["cord_uid"] for r in result["results"]]
    assert "uid001" in uids  # title contains "vaccine"


# ── Pagination ──────────────────────────────────────────────────────────────

def test_pagination_page_1(searcher):
    result = searcher.search("COVID", page=1, results_per_page=2)
    assert result["page"] == 1
    assert len(result["results"]) <= 2


def test_pagination_page_2_differs(searcher):
    p1 = searcher.search("COVID", page=1, results_per_page=2)
    p2 = searcher.search("COVID", page=2, results_per_page=2)
    if p2["results"]:
        uids1 = {r["cord_uid"] for r in p1["results"]}
        uids2 = {r["cord_uid"] for r in p2["results"]}
        assert uids1.isdisjoint(uids2)


def test_pagination_total_pages(searcher):
    result = searcher.search("COVID", results_per_page=3)
    expected = math.ceil(result["total"] / 3)
    assert result["total_pages"] == expected


def test_pagination_beyond_last_page(searcher):
    result = searcher.search("COVID", page=9999)
    assert result["results"] == []
    assert result["page"] == 9999


# ── Abstract truncation ────────────────────────────────────────────────────

def test_abstract_truncation_long(searcher):
    """uid001 has a >300 char abstract — should be truncated with '...'."""
    result = searcher.search("COVID-19 vaccine efficacy clinical trials")
    hit = next(r for r in result["results"] if r["cord_uid"] == "uid001")
    assert hit["abstract"].endswith("...")
    assert len(hit["abstract"]) == 303


def test_abstract_no_truncation_short(searcher):
    """uid002 has a <300 char abstract — no ellipsis appended."""
    result = searcher.search("SARS-CoV-2 transmission indoor")
    hit = next(r for r in result["results"] if r["cord_uid"] == "uid002")
    assert not hit["abstract"].endswith("...")


# ── get_index_stats ─────────────────────────────────────────────────────────

def test_get_index_stats(searcher):
    stats = searcher.get_index_stats()
    assert stats["total_documents"] == EXPECTED_DOC_COUNT
    assert "title" in stats["fields"]
    assert "abstract" in stats["fields"]


# ── Error handling ──────────────────────────────────────────────────────────

def test_searcher_invalid_index_dir(tmp_path):
    with pytest.raises(Exception):
        CORD19Searcher(str(tmp_path / "nonexistent"))
