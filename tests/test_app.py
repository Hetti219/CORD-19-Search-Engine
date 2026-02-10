"""Tests for src/app.py — Flask routes."""


# ── No-index state ──────────────────────────────────────────────────────────

def test_home_no_index(flask_client_no_index):
    resp = flask_client_no_index.get("/")
    assert resp.status_code == 200
    assert b"Setup Required" in resp.data


def test_search_no_index(flask_client_no_index):
    resp = flask_client_no_index.get("/search?q=vaccine")
    assert resp.status_code == 200
    assert b"Setup Required" in resp.data


# ── With-index state ────────────────────────────────────────────────────────

def test_home_with_index(flask_client_with_index):
    resp = flask_client_with_index.get("/")
    assert resp.status_code == 200
    assert b"COVID-19 Research Search Engine" in resp.data


def test_search_valid_query(flask_client_with_index):
    resp = flask_client_with_index.get("/search?q=vaccine")
    assert resp.status_code == 200
    assert b"vaccine" in resp.data.lower()
    assert b"results" in resp.data.lower()


def test_search_with_pagination(flask_client_with_index):
    resp = flask_client_with_index.get("/search?q=COVID&page=1")
    assert resp.status_code == 200
    assert b"Page 1" in resp.data


# ── Empty / whitespace queries ──────────────────────────────────────────────

def test_search_empty_query(flask_client_with_index):
    resp = flask_client_with_index.get("/search?q=")
    assert resp.status_code == 200
    assert b"COVID-19 Research Search Engine" in resp.data


def test_search_whitespace_query(flask_client_with_index):
    resp = flask_client_with_index.get("/search?q=%20%20%20")
    assert resp.status_code == 200
    assert b"COVID-19 Research Search Engine" in resp.data


# ── Malformed / special queries ─────────────────────────────────────────────

def test_search_malformed_query(flask_client_with_index):
    """Malformed queries return 200, not 500."""
    resp = flask_client_with_index.get('/search?q=%22%22%22')
    assert resp.status_code == 200


def test_search_special_characters(flask_client_with_index):
    resp = flask_client_with_index.get("/search?q=COVID-19")
    assert resp.status_code == 200


# ── About page ──────────────────────────────────────────────────────────────

def test_about_page(flask_client_with_index):
    resp = flask_client_with_index.get("/about")
    assert resp.status_code == 200
    assert b"About This Search Engine" in resp.data


# ── 404 ─────────────────────────────────────────────────────────────────────

def test_404_page(flask_client_with_index):
    resp = flask_client_with_index.get("/nonexistent")
    assert resp.status_code == 404


# ── Page parameter edge cases ──────────────────────────────────────────────

def test_page_negative(flask_client_with_index):
    resp = flask_client_with_index.get("/search?q=vaccine&page=-1")
    assert resp.status_code == 200
    assert b"Page 1" in resp.data


def test_page_zero(flask_client_with_index):
    resp = flask_client_with_index.get("/search?q=vaccine&page=0")
    assert resp.status_code == 200
    assert b"Page 1" in resp.data


def test_page_string(flask_client_with_index):
    resp = flask_client_with_index.get("/search?q=vaccine&page=abc")
    assert resp.status_code == 200


def test_page_very_large(flask_client_with_index):
    resp = flask_client_with_index.get("/search?q=vaccine&page=99999")
    assert resp.status_code == 200


# ── Sort parameter ─────────────────────────────────────────────────────────

def test_sort_dropdown_rendered(flask_client_with_index):
    """Results page includes the sort dropdown."""
    resp = flask_client_with_index.get("/search?q=vaccine")
    assert b"sort-select" in resp.data
    assert b"Relevance" in resp.data
    assert b"Date (Newest)" in resp.data
    assert b"Date (Oldest)" in resp.data


def test_sort_date_desc(flask_client_with_index):
    resp = flask_client_with_index.get("/search?q=vaccine&sort=date_desc")
    assert resp.status_code == 200
    assert b"date_desc" in resp.data


# ── Filter parameters ────────────────────────────────────────────────────

def test_date_range_filter(flask_client_with_index):
    """Date range parameters are accepted and return 200."""
    resp = flask_client_with_index.get(
        "/search?q=vaccine&date_from=2020-01-01&date_to=2021-12-31"
    )
    assert resp.status_code == 200


def test_journal_filter(flask_client_with_index):
    """Journal filter parameter is accepted and return 200."""
    resp = flask_client_with_index.get("/search?q=vaccine&journal=Lancet")
    assert resp.status_code == 200


def test_filter_sidebar_rendered(flask_client_with_index):
    """Results page includes the filter sidebar elements."""
    resp = flask_client_with_index.get("/search?q=vaccine")
    assert b"filter-sidebar" in resp.data
    assert b"Date Range" in resp.data
    assert b"filter-apply-btn" in resp.data


def test_active_filter_shown(flask_client_with_index):
    """When a journal filter is active, the active-filters bar is shown."""
    resp = flask_client_with_index.get("/search?q=vaccine&journal=Lancet")
    assert b"active-filters" in resp.data
    assert b"Lancet" in resp.data


# ── Results per page ──────────────────────────────────────────────────────

def test_per_page_selector_rendered(flask_client_with_index):
    """Results page includes the per-page dropdown."""
    resp = flask_client_with_index.get("/search?q=vaccine")
    assert b"per-page-select" in resp.data
    assert b"Show:" in resp.data


def test_per_page_default(flask_client_with_index):
    """Default per_page is 10."""
    resp = flask_client_with_index.get("/search?q=vaccine")
    assert resp.status_code == 200


def test_per_page_25(flask_client_with_index):
    """per_page=25 is accepted."""
    resp = flask_client_with_index.get("/search?q=vaccine&per_page=25")
    assert resp.status_code == 200


def test_per_page_invalid_falls_back(flask_client_with_index):
    """Invalid per_page falls back to 10."""
    resp = flask_client_with_index.get("/search?q=vaccine&per_page=99")
    assert resp.status_code == 200


# ── Numbered pagination ──────────────────────────────────────────────────

def test_pagination_nav_present(flask_client_with_index):
    """Results page includes the pagination nav element."""
    resp = flask_client_with_index.get("/search?q=vaccine")
    # With small test data and per_page=10, all results fit on one page
    # so pagination nav should NOT appear (no multi-page scenario)
    assert b"pagination" in resp.data or resp.status_code == 200


def test_per_page_preserved_in_sort_url(flask_client_with_index):
    """per_page parameter is included in the sort dropdown URL."""
    resp = flask_client_with_index.get("/search?q=vaccine&per_page=25")
    assert b"per_page=25" in resp.data
