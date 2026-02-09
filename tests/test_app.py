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
