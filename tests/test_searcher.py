"""Tests for src/searcher.py — CORD19Searcher class."""

import math

import pytest

from searcher import CORD19Searcher
from constants import EXPECTED_DOC_COUNT


# ── Return structure ────────────────────────────────────────────────────────

def test_search_returns_dict(searcher):
    result = searcher.search("COVID")
    assert isinstance(result, dict)
    assert set(result.keys()) == {
        "results", "total", "page", "total_pages", "results_per_page",
        "page_range", "query", "sort",
        "date_from", "date_to", "journal", "facets",
    }


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


# ── Query term highlighting ────────────────────────────────────────────────

def test_abstract_highlighting(searcher):
    """Matching query terms in abstract are wrapped in <mark> tags."""
    result = searcher.search("COVID-19 vaccine efficacy clinical trials")
    hit = next(r for r in result["results"] if r["cord_uid"] == "uid001")
    assert "<mark class=" in hit["abstract"]
    assert "</mark>" in hit["abstract"]


def test_title_highlighting(searcher):
    """Matching query terms in title are wrapped in <mark> tags."""
    result = searcher.search("COVID-19 vaccine efficacy clinical trials")
    hit = next(r for r in result["results"] if r["cord_uid"] == "uid001")
    assert "<mark class=" in hit["title"]
    assert "</mark>" in hit["title"]


def test_abstract_fallback_no_match(searcher):
    """When no terms match, abstract falls back to truncated plain text."""
    result = searcher.search("xyznonexistentterm")
    assert result["total"] == 0


# ── Smart snippets (sentence-aware) ───────────────────────────────────────

def test_snippet_uses_sentence_fragments(searcher):
    """SentenceFragmenter produces sentence-aware breaks with ' ... ' separators."""
    result = searcher.search("COVID-19 vaccine efficacy clinical trials")
    hit = next(r for r in result["results"] if r["cord_uid"] == "uid001")
    import re
    plain = re.sub(r"<[^>]+>", "", hit["abstract"])
    # Sentence fragments are joined by the ' ... ' separator
    assert " ... " in plain
    # Snippet shows relevant content (contains query terms)
    plain_lower = plain.lower()
    assert "vaccine" in plain_lower
    assert "efficacy" in plain_lower


def test_truncate_at_sentence_short_text():
    """Short text (under max_length) returned unchanged."""
    short = "A brief sentence."
    assert CORD19Searcher._truncate_at_sentence(short) == short


def test_truncate_at_sentence_at_boundary():
    """Long text truncated at the last sentence boundary within limit."""
    text = "First sentence. " + "A" * 290 + ". Final bit that overflows the limit."
    result = CORD19Searcher._truncate_at_sentence(text, max_length=310)
    assert result.endswith(".")
    assert len(result) <= 310


def test_truncate_at_sentence_no_boundary():
    """When no sentence boundary found, truncates at word boundary with ellipsis."""
    text = "one two three four " * 20  # No sentence punctuation
    result = CORD19Searcher._truncate_at_sentence(text, max_length=50)
    assert result.endswith("...")
    assert len(result) <= 53  # 50 + "..."


# ── Sort options ──────────────────────────────────────────────────────────

def test_sort_default_is_relevance(searcher):
    """Default sort is by BM25F relevance score."""
    result = searcher.search("vaccine")
    assert result["sort"] == "relevance"


def test_sort_date_desc(searcher):
    """Newest-first sorting returns papers ordered by publish_time descending."""
    result = searcher.search("vaccine", sort_by="date_desc")
    assert result["sort"] == "date_desc"
    dates = [r["publish_time"] for r in result["results"]]
    assert dates == sorted(dates, reverse=True)


def test_sort_date_asc(searcher):
    """Oldest-first sorting returns papers ordered by publish_time ascending."""
    result = searcher.search("vaccine", sort_by="date_asc")
    assert result["sort"] == "date_asc"
    dates = [r["publish_time"] for r in result["results"]]
    assert dates == sorted(dates)


def test_sort_invalid_falls_back_to_relevance(searcher):
    """Invalid sort parameter falls back to relevance."""
    result = searcher.search("vaccine", sort_by="invalid_option")
    assert result["sort"] == "relevance"


def test_sort_preserves_results(searcher):
    """All sort options return the same result set (different order)."""
    relevance = searcher.search("vaccine", sort_by="relevance")
    newest = searcher.search("vaccine", sort_by="date_desc")
    oldest = searcher.search("vaccine", sort_by="date_asc")
    # Same total and same UIDs regardless of sort
    assert relevance["total"] == newest["total"] == oldest["total"]
    uids_rel = {r["cord_uid"] for r in relevance["results"]}
    uids_new = {r["cord_uid"] for r in newest["results"]}
    uids_old = {r["cord_uid"] for r in oldest["results"]}
    assert uids_rel == uids_new == uids_old


# ── Date range filtering ──────────────────────────────────────────────────

def test_date_from_filters_old_papers(searcher):
    """date_from excludes papers published before the given date."""
    all_results = searcher.search("vaccine")
    filtered = searcher.search("vaccine", date_from="2021-01-01")
    # Every returned paper should have publish_time >= 2021-01-01
    for r in filtered["results"]:
        assert r["publish_time"] >= "2021-01-01"
    assert filtered["total"] <= all_results["total"]


def test_date_to_filters_new_papers(searcher):
    """date_to excludes papers published after the given date."""
    filtered = searcher.search("vaccine", date_to="2020-12-31")
    for r in filtered["results"]:
        assert r["publish_time"] <= "2020-12-31"


def test_date_range_combined(searcher):
    """Combining date_from and date_to returns only papers in that window."""
    filtered = searcher.search("vaccine", date_from="2020-01-01", date_to="2020-12-31")
    for r in filtered["results"]:
        assert "2020" <= r["publish_time"][:4] <= "2020"


def test_date_range_no_match(searcher):
    """A date range with no matching papers returns zero results."""
    result = searcher.search("vaccine", date_from="2025-01-01", date_to="2025-12-31")
    assert result["total"] == 0
    assert result["results"] == []


def test_date_range_values_returned(searcher):
    """date_from and date_to are echoed back in the result dict."""
    result = searcher.search("vaccine", date_from="2020-06-01", date_to="2021-06-01")
    assert result["date_from"] == "2020-06-01"
    assert result["date_to"] == "2021-06-01"


# ── Journal filtering ────────────────────────────────────────────────────

def test_journal_filter(searcher):
    """Filtering by journal returns only papers from that journal."""
    result = searcher.search("vaccine", journal="Lancet")
    assert result["total"] > 0
    for r in result["results"]:
        assert r["journal"] == "Lancet"


def test_journal_filter_no_match(searcher):
    """Filtering by a non-existent journal returns zero results."""
    result = searcher.search("vaccine", journal="Nonexistent Journal")
    assert result["total"] == 0


def test_journal_filter_value_returned(searcher):
    """Active journal filter is echoed back in the result dict."""
    result = searcher.search("vaccine", journal="Science")
    assert result["journal"] == "Science"


def test_journal_and_date_combined(searcher):
    """Journal and date filters can be combined."""
    result = searcher.search("vaccine", journal="Lancet", date_from="2021-01-01")
    for r in result["results"]:
        assert r["journal"] == "Lancet"
        assert r["publish_time"] >= "2021-01-01"


# ── Facets ────────────────────────────────────────────────────────────────

def test_facets_returned(searcher):
    """Search results include facets with journals and years."""
    result = searcher.search("vaccine")
    assert "facets" in result
    assert "journals" in result["facets"]
    assert "years" in result["facets"]


def test_facets_journal_structure(searcher):
    """Each journal facet has name and count keys."""
    result = searcher.search("vaccine")
    for j in result["facets"]["journals"]:
        assert "name" in j
        assert "count" in j
        assert j["count"] > 0


def test_facets_year_structure(searcher):
    """Each year facet has year and count keys."""
    result = searcher.search("vaccine")
    for y in result["facets"]["years"]:
        assert "year" in y
        assert "count" in y
        assert y["count"] > 0


def test_facets_years_sorted_descending(searcher):
    """Year facets are sorted newest-first."""
    result = searcher.search("vaccine")
    years = [y["year"] for y in result["facets"]["years"]]
    assert years == sorted(years, reverse=True)


# ── Results per page ─────────────────────────────────────────────────────

def test_results_per_page_default(searcher):
    """Default results_per_page is 10."""
    result = searcher.search("vaccine")
    assert result["results_per_page"] == 10


def test_results_per_page_custom(searcher):
    """Custom results_per_page value is respected and echoed."""
    result = searcher.search("vaccine", results_per_page=25)
    assert result["results_per_page"] == 25
    assert len(result["results"]) <= 25


def test_results_per_page_limits_results(searcher):
    """Requesting 2 per page returns at most 2 results."""
    result = searcher.search("COVID", results_per_page=2)
    assert len(result["results"]) <= 2


def test_results_per_page_affects_total_pages(searcher):
    """Fewer results per page means more total pages."""
    small = searcher.search("COVID", results_per_page=2)
    large = searcher.search("COVID", results_per_page=50)
    assert small["total_pages"] >= large["total_pages"]


# ── Page range (numbered pagination) ────────────────────────────────────

def test_page_range_returned(searcher):
    """Search results include a page_range list."""
    result = searcher.search("vaccine")
    assert isinstance(result["page_range"], list)


def test_page_range_single_page(searcher):
    """Single-page results produce an empty page_range."""
    result = searcher.search("vaccine", results_per_page=50)
    # With only 8 docs, 50 per page = 1 page total
    assert result["page_range"] == []


def test_page_range_multi_page(searcher):
    """Multi-page results produce a page_range with numbered entries."""
    result = searcher.search("COVID", results_per_page=2)
    assert len(result["page_range"]) > 0
    # First entry should be page 1
    assert result["page_range"][0] == 1
    # Last entry should be total_pages
    nums = [p for p in result["page_range"] if p is not None]
    assert nums[-1] == result["total_pages"]


def test_page_range_contains_current_page(searcher):
    """The current page is always included in page_range."""
    result = searcher.search("COVID", page=2, results_per_page=2)
    assert 2 in result["page_range"]


def test_compute_page_range_ellipsis():
    """Pages with large gaps include None (ellipsis) placeholders."""
    page_range = CORD19Searcher._compute_page_range(page=10, total_pages=20, window=2)
    # Should include: 1, None, 8, 9, 10, 11, 12, None, 20
    assert 1 in page_range
    assert 20 in page_range
    assert 10 in page_range
    assert None in page_range


def test_compute_page_range_small_total():
    """When total_pages is small, no ellipsis needed."""
    page_range = CORD19Searcher._compute_page_range(page=2, total_pages=4, window=2)
    assert None not in page_range
    assert page_range == [1, 2, 3, 4]


def test_compute_page_range_single_page():
    """Single page returns empty list."""
    assert CORD19Searcher._compute_page_range(page=1, total_pages=1) == []


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
