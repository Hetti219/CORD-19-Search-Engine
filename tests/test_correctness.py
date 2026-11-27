"""
test_correctness.py
Regression tests for the correctness fixes in the CORD-19 Search Engine.

These cover the bugs found during code review:

- Pagination promised pages that could not be served, so pages past the
  retrieval cap rendered empty while the header still counted them, and
  the result count was recomputed with a full index scan on every query.
- A failure inside the search was reported as "0 results", which is
  indistinguishable from a query that legitimately matched nothing.
- Papers without an abstract were indexed with the literal text "nan",
  so a search for "nan" matched them.
- Papers without a publication date sorted to the top of a "newest
  first" result set.
- De-duplication collapsed unrelated papers that shared a generic title,
  and papers that had no title at all were collapsed into a single row.
- A missing column in the input crashed the preprocessor with a
  KeyError, and the indexer silently produced an index full of empty
  identifiers instead of reporting the problem.
"""

import datetime

import pandas as pd
import pytest

import searcher as searcher_module
from indexer import create_index
from preprocessor import MIN_DISTINCTIVE_TITLE_LENGTH, preprocess_cord19
from searcher import CORD19Searcher


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _papers(count, prefix="p", title_suffix="of covid vaccine studies"):
    """Build a list of distinct paper rows."""
    papers = []
    for i in range(count):
        date = datetime.date(2020, 1, 1) + datetime.timedelta(days=i % 900)
        papers.append({
            "cord_uid": f"{prefix}{i}",
            "title": f"covid paper number {i} {title_suffix}",
            "abstract": f"An abstract for covid paper {i} about vaccines.",
            "authors": "Smith, J",
            "journal": "Lancet" if i % 2 == 0 else "Nature",
            "publish_time": date.isoformat(),
            "url": f"https://example.com/{prefix}{i}",
        })
    return papers


@pytest.fixture
def build_index(tmp_path):
    """Return a helper that builds an index from a list of paper rows."""
    def _build(papers, name="index"):
        csv_path = tmp_path / f"{name}-metadata.csv"
        pd.DataFrame(papers).to_csv(csv_path, index=False)
        processed_path = tmp_path / f"{name}-processed" / "papers.csv"
        preprocess_cord19(str(csv_path), str(processed_path))
        index_dir = tmp_path / f"{name}-index"
        create_index(str(processed_path), str(index_dir))
        return str(index_dir)
    return _build


@pytest.fixture
def many_searcher(build_index):
    """A searcher over an index large enough to page through."""
    return CORD19Searcher(build_index(_papers(60)))


# ── Pagination ─────────────────────────────────────────────────────────────

def test_total_pages_never_exceeds_what_can_be_served(many_searcher, monkeypatch):
    """The page count must not promise pages beyond the retrieval cap.

    Previously the header counted every match, so a query with 15,000
    matches claimed 1,500 pages while only the first 1,000 could be
    served. Pages 1001 to 1500 rendered empty.
    """
    monkeypatch.setattr(searcher_module, "MAX_RESULTS", 30)
    result = many_searcher.search("covid", results_per_page=10)

    assert result["total"] == 60
    assert result["total_pages"] == 3          # 30 reachable results / 10
    assert result["limited"] is True


def test_pages_within_the_cap_are_not_empty(many_searcher, monkeypatch):
    """Every page the header counts must actually contain results."""
    monkeypatch.setattr(searcher_module, "MAX_RESULTS", 30)
    for page in (1, 2, 3):
        result = many_searcher.search("covid", page=page, results_per_page=10)
        assert len(result["results"]) == 10, f"page {page} was empty"


def test_page_beyond_the_cap_is_clamped_to_the_last_page(many_searcher, monkeypatch):
    """A page past the end serves the last reachable page, not an empty one."""
    monkeypatch.setattr(searcher_module, "MAX_RESULTS", 30)
    result = many_searcher.search("covid", page=9999, results_per_page=10)

    assert result["page"] == result["total_pages"]
    assert len(result["results"]) == 10


def test_page_is_clamped_to_the_last_page_when_all_results_fit(many_searcher):
    """Without a cap, a page past the end still lands on the last page."""
    result = many_searcher.search("covid", page=9999, results_per_page=10)

    assert result["page"] == result["total_pages"]
    assert result["results"]


def test_limited_flag_is_false_when_everything_is_reachable(many_searcher):
    """The "results are limited" note only appears when it applies."""
    result = many_searcher.search("covid", results_per_page=10)

    assert result["limited"] is False


def test_total_counts_every_match(many_searcher):
    """The reported total is the number of matching documents."""
    result = many_searcher.search("covid", results_per_page=10)
    assert result["total"] == 60


def test_total_respects_the_active_filter(many_searcher):
    """A filtered search reports the filtered count, not the raw one."""
    result = many_searcher.search("covid", journal="Lancet", results_per_page=10)

    assert result["total"] == 30


def test_empty_result_has_no_pages(many_searcher):
    """A query with no matches reports zero pages."""
    result = many_searcher.search("xyznonexistentterm")

    assert result["total"] == 0
    assert result["total_pages"] == 0
    assert result["results"] == []


# ── Searcher input validation ──────────────────────────────────────────────

def test_page_below_one_is_clamped(many_searcher):
    """A page number below one is treated as the first page."""
    result = many_searcher.search("covid", page=0, results_per_page=10)

    assert result["page"] == 1
    assert result["results"]


def test_negative_page_is_clamped(many_searcher):
    """A negative page number cannot produce a slice from the end."""
    result = many_searcher.search("covid", page=-5, results_per_page=10)

    assert result["page"] == 1
    assert len(result["results"]) == 10


def test_zero_results_per_page_is_rejected(many_searcher):
    """A page size of zero would divide by zero when counting pages."""
    with pytest.raises(ValueError):
        many_searcher.search("covid", results_per_page=0)


# ── Missing publication dates ──────────────────────────────────────────────

@pytest.fixture
def undated_searcher(build_index):
    """An index containing one dated and one undated paper."""
    papers = _papers(2)
    papers[0]["publish_time"] = "2021-01-01"
    papers[1]["publish_time"] = "Unknown"
    return CORD19Searcher(build_index(papers, name="undated"))


def test_undated_papers_are_not_first_in_a_newest_first_sort(undated_searcher):
    """A paper with no date has no place at the top of a date sort.

    The placeholder used for a missing date sorts after every real
    date, so under a descending sort it used to be shown first.
    """
    result = undated_searcher.search("covid", sort_by="date_desc")

    dates = [r["publish_time"] for r in result["results"]]
    assert dates == sorted(dates, reverse=True)
    assert "Unknown" not in dates


def test_undated_papers_are_excluded_from_date_sorts(undated_searcher):
    """Date-sorted results contain only papers that have a date."""
    for sort_by in ("date_desc", "date_asc"):
        result = undated_searcher.search("covid", sort_by=sort_by)
        assert all(r["publish_time"] != "Unknown" for r in result["results"])


def test_undated_papers_are_still_found_by_a_relevance_search(undated_searcher):
    """Excluding them from date sorts must not remove them from the index."""
    result = undated_searcher.search("covid", sort_by="relevance")

    assert result["total"] == 2


def test_date_filter_still_selects_a_date_window(build_index):
    """The date range filter keeps working after the change."""
    papers = _papers(2)
    papers[0]["publish_time"] = "2020-01-01"
    papers[1]["publish_time"] = "2021-06-01"
    searcher = CORD19Searcher(build_index(papers, name="window"))

    result = searcher.search("covid", date_from="2021-01-01", date_to="2021-12-31")

    assert result["total"] == 1
    assert result["results"][0]["publish_time"] == "2021-06-01"


# ── Missing values ─────────────────────────────────────────────────────────

def test_missing_abstract_is_indexed_as_empty_not_nan(build_index):
    """A paper with no abstract must not be indexed as the text "nan"."""
    papers = _papers(2)
    papers[0]["abstract"] = None
    searcher = CORD19Searcher(build_index(papers, name="noabstract"))

    result = searcher.search("covid", results_per_page=10)
    for hit in result["results"]:
        assert hit["abstract"] != "nan"


def test_searching_for_nan_does_not_match_missing_abstracts(build_index):
    """The literal text "nan" must not be searchable."""
    papers = _papers(2)
    papers[0]["abstract"] = None
    searcher = CORD19Searcher(build_index(papers, name="nannan"))

    result = searcher.search("nan", results_per_page=10)

    assert result["total"] == 0


def test_missing_title_is_indexed_as_empty_not_nan(build_index):
    """A paper with no title must not be indexed as the text "nan"."""
    papers = _papers(2)
    papers[0]["title"] = None
    searcher = CORD19Searcher(build_index(papers, name="notitle"))

    result = searcher.search("covid", results_per_page=10)
    for hit in result["results"]:
        assert hit["title"] != "nan"


def test_paper_without_an_identifier_gets_a_surrogate_one(build_index):
    """A paper with no identifier is still indexed, with a usable one."""
    papers = _papers(2)
    papers[0]["cord_uid"] = None
    searcher = CORD19Searcher(build_index(papers, name="nouid"))

    result = searcher.search("covid", results_per_page=10)
    uids = [r["cord_uid"] for r in result["results"]]

    assert len(uids) == 2
    assert all(uid for uid in uids)


# ── De-duplication ─────────────────────────────────────────────────────────

def test_papers_sharing_a_generic_title_are_both_kept(tmp_path):
    """Two unrelated papers called "Editorial" are two papers.

    De-duplicating on the raw title alone silently dropped one of them.
    """
    csv_path = tmp_path / "metadata.csv"
    pd.DataFrame([
        {"cord_uid": "u1", "title": "Editorial", "abstract": "first editorial",
         "authors": "A", "journal": "L", "publish_time": "2020-01-01", "url": ""},
        {"cord_uid": "u2", "title": "Editorial", "abstract": "second editorial",
         "authors": "B", "journal": "L", "publish_time": "2020-01-02", "url": ""},
    ]).to_csv(csv_path, index=False)

    df = preprocess_cord19(str(csv_path), str(tmp_path / "out" / "papers.csv"))

    assert len(df) == 2
    assert set(df["cord_uid"]) == {"u1", "u2"}


def test_the_same_paper_in_a_different_case_is_deduplicated(tmp_path):
    """A title that differs only in case or spacing is the same paper."""
    title = "A distinctive study of covid vaccine efficacy in clinical trials"
    csv_path = tmp_path / "metadata.csv"
    pd.DataFrame([
        {"cord_uid": "u1", "title": title, "abstract": "one",
         "authors": "A", "journal": "L", "publish_time": "2020-01-01", "url": ""},
        {"cord_uid": "u2", "title": title.upper(), "abstract": "two",
         "authors": "B", "journal": "L", "publish_time": "2020-01-02", "url": ""},
    ]).to_csv(csv_path, index=False)

    df = preprocess_cord19(str(csv_path), str(tmp_path / "out" / "papers.csv"))

    assert len(df) == 1
    assert df.iloc[0]["cord_uid"] == "u1"


def test_papers_without_a_title_are_not_collapsed(tmp_path):
    """Unrelated untitled papers must not be merged into one row."""
    csv_path = tmp_path / "metadata.csv"
    pd.DataFrame([
        {"cord_uid": "u1", "title": None, "abstract": "first untitled paper",
         "authors": "A", "journal": "L", "publish_time": "2020-01-01", "url": ""},
        {"cord_uid": "u2", "title": None, "abstract": "second untitled paper",
         "authors": "B", "journal": "L", "publish_time": "2020-01-02", "url": ""},
    ]).to_csv(csv_path, index=False)

    df = preprocess_cord19(str(csv_path), str(tmp_path / "out" / "papers.csv"))

    assert len(df) == 2


def test_distinctive_title_length_threshold():
    """The threshold that decides whether a title identifies a paper."""
    assert MIN_DISTINCTIVE_TITLE_LENGTH == 30


# ── Missing columns ────────────────────────────────────────────────────────

def test_preprocessor_tolerates_a_missing_abstract_column(tmp_path):
    """A metadata file without abstracts is processed, not crashed on."""
    csv_path = tmp_path / "metadata.csv"
    pd.DataFrame([
        {"cord_uid": "u1", "title": "A covid paper", "authors": "A",
         "journal": "L", "publish_time": "2020-01-01", "url": ""},
    ]).to_csv(csv_path, index=False)

    df = preprocess_cord19(str(csv_path), str(tmp_path / "out" / "papers.csv"))

    assert len(df) == 1
    assert df.iloc[0]["abstract"] == ""


def test_preprocessor_reports_a_missing_title_column(tmp_path):
    """A metadata file without titles is rejected with a clear message."""
    csv_path = tmp_path / "metadata.csv"
    pd.DataFrame([
        {"cord_uid": "u1", "abstract": "no title here", "authors": "A",
         "journal": "L", "publish_time": "2020-01-01", "url": ""},
    ]).to_csv(csv_path, index=False)

    with pytest.raises(ValueError, match="title"):
        preprocess_cord19(str(csv_path), str(tmp_path / "out" / "papers.csv"))


def test_preprocessor_accepts_an_output_path_without_a_directory(tmp_path):
    """Writing "papers.csv" in the working directory must work."""
    csv_path = tmp_path / "metadata.csv"
    pd.DataFrame(_papers(1)).to_csv(csv_path, index=False)
    output = tmp_path / "papers.csv"

    preprocess_cord19(str(csv_path), str(output))

    assert output.exists()


def test_indexer_reports_a_missing_required_column(tmp_path):
    """An index built from a CSV without a required column is refused."""
    csv_path = tmp_path / "papers.csv"
    pd.DataFrame([{"cord_uid": "u1", "title": "A covid paper"}]).to_csv(
        csv_path, index=False)

    with pytest.raises(ValueError, match="missing required column"):
        create_index(str(csv_path), str(tmp_path / "index"))


def test_indexer_reports_duplicate_identifiers(tmp_path):
    """Two papers cannot share an identifier."""
    csv_path = tmp_path / "papers.csv"
    pd.DataFrame([
        {"cord_uid": "u1", "title": "A covid paper", "abstract": "a",
         "authors": "A", "journal": "L", "publish_time": "2020-01-01", "url": ""},
        {"cord_uid": "u1", "title": "Another covid paper", "abstract": "b",
         "authors": "B", "journal": "L", "publish_time": "2020-01-02", "url": ""},
    ]).to_csv(csv_path, index=False)

    with pytest.raises(ValueError, match="duplicate paper identifiers"):
        create_index(str(csv_path), str(tmp_path / "index"))


def test_indexer_reports_papers_without_an_identifier(tmp_path):
    """A paper with an empty identifier is refused."""
    csv_path = tmp_path / "papers.csv"
    pd.DataFrame([
        {"cord_uid": "", "title": "A covid paper", "abstract": "a",
         "authors": "A", "journal": "L", "publish_time": "2020-01-01", "url": ""},
    ]).to_csv(csv_path, index=False)

    with pytest.raises(ValueError, match="without an identifier"):
        create_index(str(csv_path), str(tmp_path / "index"))


# ── Error reporting ────────────────────────────────────────────────────────

def test_a_failing_search_is_reported_not_shown_as_no_results(many_searcher):
    """A failure inside the search must not look like an empty result set."""
    import app as app_module

    class FailingSearcher:
        def get_index_stats(self):
            return {"total_documents": 0, "fields": []}

        def search(self, *args, **kwargs):
            raise RuntimeError("index unavailable")

    original = app_module.searcher
    app_module.searcher = FailingSearcher()
    app_module.app.config["TESTING"] = True
    try:
        with app_module.app.test_client() as client:
            resp = client.get("/search?q=covid")
            html = resp.data.decode()
    finally:
        app_module.searcher = original

    assert resp.status_code == 200
    assert "could not be completed" in html
    assert "No results found" not in html


def test_a_query_with_no_matches_is_not_reported_as_an_error(many_searcher):
    """A genuine zero-hit search still says so, without an error."""
    import app as app_module

    original = app_module.searcher
    app_module.searcher = many_searcher
    app_module.app.config["TESTING"] = True
    try:
        with app_module.app.test_client() as client:
            resp = client.get("/search?q=xyznonexistentterm")
            html = resp.data.decode()
    finally:
        app_module.searcher = original

    assert resp.status_code == 200
    assert "No results found" in html
    assert "could not be completed" not in html
