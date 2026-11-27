"""
test_security.py
Regression tests for the security fixes in the CORD-19 Search Engine.

These cover the vulnerabilities found during code review:

- Reflected XSS: query parameters were interpolated into inline JavaScript
  event handlers, where an HTML-escaped quote still terminates the script
  string once the browser decodes the attribute.
- Stored XSS: the results template rendered titles and abstracts as safe
  markup, but the searcher's fallback path returned the raw indexed text
  whenever a field contained none of the query terms.
- Unsafe URL schemes: the dataset's ``url`` column was rendered straight
  into an ``href``, so a ``javascript:`` value became clickable script.
- Missing security headers, in particular a Content-Security-Policy that
  would have blocked both injection paths.
"""

import re
from urllib.parse import quote

import pandas as pd
import pytest

from indexer import create_index
from preprocessor import preprocess_cord19
from searcher import CORD19Searcher, escape_html, safe_url


# ---------------------------------------------------------------------------
# Hostile sample data
# ---------------------------------------------------------------------------

HOSTILE_PAPERS = [
    {
        # Benign control document.
        "cord_uid": "uid001",
        "title": "COVID-19 vaccine efficacy in clinical trials",
        "abstract": "A randomised study of covid vaccines and their efficacy.",
        "authors": "Smith, J",
        "journal": "Lancet",
        "publish_time": "2021-03-15",
        "url": "https://example.com/paper1",
    },
    {
        # Markup in a field that the highlighter does format: Whoosh escapes
        # it, and it must stay escaped.
        "cord_uid": "uid002",
        "title": "COVID-19 <script>alert('title')</script> study",
        "abstract": "A covid study about transmission.",
        "authors": "Brown, K",
        "journal": "Nature",
        "publish_time": "2020-11-01",
        "url": "https://example.com/paper2",
    },
    {
        # Markup in the abstract, which contains none of the query terms, so
        # the searcher falls back to the raw indexed text.
        "cord_uid": "uid003",
        "title": "COVID-19 hospitalisation rates",
        "abstract": "<script>alert('abstract')</script> no query term in this text",
        "authors": "Lee, M",
        "journal": "Science",
        "publish_time": "2021-01-20",
        "url": "https://example.com/paper3",
    },
    {
        # Markup in the title, which contains none of the query terms, so the
        # searcher falls back to the raw indexed text.
        "cord_uid": "uid004",
        "title": "<img src=x onerror=alert('title-fallback')> unrelated title",
        "abstract": "A covid abstract that does match the query.",
        "authors": "Chen, W",
        "journal": "BMJ",
        "publish_time": "2020-08-10",
        "url": "https://example.com/paper4",
    },
    {
        # A hostile URL scheme in the dataset.
        "cord_uid": "uid005",
        "title": "COVID-19 face mask efficacy",
        "abstract": "A covid study about face masks.",
        "authors": "Garcia, R",
        "journal": "JAMA",
        "publish_time": "2021-05-22",
        "url": "javascript:alert('url')",
    },
]


@pytest.fixture
def hostile_index_dir(tmp_path):
    """Build a small index containing hostile documents."""
    csv_path = tmp_path / "metadata.csv"
    pd.DataFrame(HOSTILE_PAPERS).to_csv(csv_path, index=False)

    processed_path = tmp_path / "processed" / "papers.csv"
    preprocess_cord19(str(csv_path), str(processed_path))

    index_dir = tmp_path / "index"
    create_index(str(processed_path), str(index_dir))
    return index_dir


@pytest.fixture
def hostile_client(hostile_index_dir):
    """Flask test client wired to the hostile index."""
    import app as app_module

    original = app_module.searcher
    app_module.searcher = CORD19Searcher(str(hostile_index_dir))
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        yield client
    app_module.searcher = original


# ── safe_url() ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("url,expected", [
    ("https://example.com/paper", "https://example.com/paper"),
    ("http://example.com/paper", "http://example.com/paper"),
    ("javascript:alert(1)", ""),
    ("JaVaScRiPt:alert(1)", ""),
    ("  javascript:alert(1)", ""),
    ("data:text/html;base64,PHNjcmlwdD4=", ""),
    ("vbscript:msgbox(1)", ""),
    ("file:///etc/passwd", ""),
    ("//evil.example.com/x", ""),
    ("", ""),
    (None, ""),
])
def test_safe_url_rejects_unsafe_schemes(url, expected):
    """Only http(s) URLs survive; everything else becomes an empty string."""
    assert safe_url(url) == expected


def test_escape_html_neutralises_markup():
    """escape_html turns markup into inert entities."""
    assert "<script>" not in escape_html("<script>alert(1)</script>")
    assert "&lt;script&gt;" in escape_html("<script>alert(1)</script>")
    assert '"' not in escape_html('" onmouseover="alert(1)')


# ── Reflected XSS ──────────────────────────────────────────────────────────

def test_results_page_has_no_inline_event_handlers(hostile_client):
    """User input must never be interpolated into an inline script."""
    resp = hostile_client.get("/search?q=covid")
    html = resp.data.decode()

    assert resp.status_code == 200
    assert "onchange=" not in html
    assert "onclick=" not in html
    assert "onload=" not in html


def test_reflected_xss_payload_is_neutralised(hostile_client):
    """A crafted date_from must not survive into the document unescaped."""
    payload = '";alert(1);//'
    resp = hostile_client.get("/search?q=covid&date_from=" + quote(payload, safe=""))
    html = resp.data.decode()

    # The raw payload must not appear anywhere in the served document.
    assert payload not in html
    # It is reflected HTML-escaped in the form field (Jinja escapes a quote
    # as &#34;) and URL-encoded in the filter links, so neither form is
    # executable.
    assert "&#34;" in html
    assert "%22" in html


def test_reflected_xss_payload_in_date_to_is_neutralised(hostile_client):
    """The same protection applies to date_to."""
    payload = '";alert(1);//'
    resp = hostile_client.get("/search?q=covid&date_to=" + quote(payload, safe=""))
    html = resp.data.decode()

    assert payload not in html
    assert "&#34;" in html


def test_results_page_has_only_the_external_script(hostile_client):
    """Exactly one script element, and it loads an external file."""
    html = hostile_client.get("/search?q=covid").data.decode()

    scripts = re.findall(r"<script\b[^>]*>", html)
    assert len(scripts) == 1
    assert "src=" in scripts[0]
    assert ">" not in scripts[0][:-1].replace("/>", "")


def test_sort_control_uses_external_script(hostile_client):
    """The sort control is wired up by static/js/search.js instead."""
    html = hostile_client.get("/search?q=covid").data.decode()

    assert 'id="sort-select"' in html
    assert "/static/js/search.js" in html


def test_static_script_is_served(hostile_client):
    """The replacement script is actually reachable."""
    resp = hostile_client.get("/static/js/search.js")

    assert resp.status_code == 200
    assert b"navigateWithParam" in resp.data


def test_static_script_does_not_embed_user_data(hostile_client):
    """The script builds URLs from location.search, not from server output."""
    resp = hostile_client.get("/static/js/search.js")
    script = resp.data.decode()

    assert "location.search" in script
    # No template delimiters: the file is served verbatim, so nothing that
    # a user controls can ever be interpolated into it.
    assert "{{" not in script
    assert "{%" not in script


# ── Stored XSS ─────────────────────────────────────────────────────────────

def test_stored_xss_in_title_is_escaped(hostile_client):
    """A document title containing markup is never served as live markup."""
    html = hostile_client.get("/search?q=covid").data.decode()

    assert "<img src=x onerror=" not in html
    assert "&lt;img src=x onerror=" in html


def test_stored_xss_in_abstract_is_escaped(hostile_client):
    """A document abstract containing markup is never served as live markup."""
    html = hostile_client.get("/search?q=covid").data.decode()

    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_searcher_escapes_the_fallback_title(hostile_index_dir):
    """The raw-text fallback path escapes the title it returns."""
    searcher = CORD19Searcher(str(hostile_index_dir))
    results = searcher.search("covid")
    by_uid = {r["cord_uid"]: r for r in results["results"]}

    # uid004 matched on its abstract, so the title takes the fallback path.
    assert "<img" not in by_uid["uid004"]["title"]
    assert "&lt;img" in by_uid["uid004"]["title"]


def test_searcher_escapes_the_fallback_abstract(hostile_index_dir):
    """The raw-text fallback path escapes the abstract it returns."""
    searcher = CORD19Searcher(str(hostile_index_dir))
    results = searcher.search("covid")
    by_uid = {r["cord_uid"]: r for r in results["results"]}

    # uid003 matched on its title, so the abstract takes the fallback path.
    assert "<script" not in by_uid["uid003"]["abstract"]
    assert "&lt;script" in by_uid["uid003"]["abstract"]


def test_highlighted_text_stays_escaped(hostile_index_dir):
    """The highlighter path keeps escaping the document text."""
    searcher = CORD19Searcher(str(hostile_index_dir))
    results = searcher.search("covid")
    by_uid = {r["cord_uid"]: r for r in results["results"]}

    assert "<script" not in by_uid["uid002"]["title"]
    assert "&lt;script" in by_uid["uid002"]["title"]
    # The <mark> tags the template relies on are still produced.
    assert "<mark" in by_uid["uid002"]["title"]


# ── Unsafe URL schemes ────────────────────────────────────────────────────

def test_javascript_url_is_not_rendered_as_a_link(hostile_client):
    """A javascript: URL must never reach an href."""
    html = hostile_client.get("/search?q=covid").data.decode()

    assert "javascript:" not in html


def test_searcher_drops_unsafe_urls(hostile_index_dir):
    """The searcher blanks out URLs with an unsafe scheme."""
    searcher = CORD19Searcher(str(hostile_index_dir))
    results = searcher.search("covid")
    by_uid = {r["cord_uid"]: r for r in results["results"]}

    assert by_uid["uid005"]["url"] == ""
    assert by_uid["uid001"]["url"] == "https://example.com/paper1"


# ── Link hardening ────────────────────────────────────────────────────────

@pytest.mark.parametrize("path", ["/", "/search?q=covid", "/about"])
def test_target_blank_links_carry_noopener(hostile_client, path):
    """Links opening a new tab must not leak window.opener."""
    html = hostile_client.get(path).data.decode()

    for tag in re.findall(r"<a\b[^>]*target=\"_blank\"[^>]*>", html):
        assert 'rel="noopener noreferrer"' in tag


# ── Security headers ───────────────────────────────────────────────────────

def test_security_headers_are_present(hostile_client):
    """Every response carries the hardening headers."""
    resp = hostile_client.get("/search?q=covid")

    csp = resp.headers["Content-Security-Policy"]
    assert "script-src 'self'" in csp
    assert "style-src 'self'" in csp
    assert "object-src 'none'" in csp
    assert "base-uri 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "unsafe-inline" not in csp
    assert "unsafe-eval" not in csp

    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_security_headers_present_on_error_pages(hostile_client):
    """The headers are applied to every route, not just the results page."""
    for path in ["/", "/about", "/nonexistent"]:
        resp = hostile_client.get(path)
        assert "Content-Security-Policy" in resp.headers
        assert resp.headers["X-Content-Type-Options"] == "nosniff"


def test_csp_does_not_break_the_results_page(hostile_client):
    """The page still renders normally under the new policy."""
    resp = hostile_client.get("/search?q=covid")

    assert resp.status_code == 200
    assert b"COVID" in resp.data
    assert b"sort-select" in resp.data
