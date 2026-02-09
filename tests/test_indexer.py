"""Tests for src/indexer.py"""

import pandas as pd
from whoosh import index
from whoosh.fields import TEXT, ID, STORED

from indexer import create_schema, create_index
from constants import EXPECTED_DOC_COUNT


# ── Schema ──────────────────────────────────────────────────────────────────

def test_schema_has_expected_fields():
    """Schema contains all 7 required fields."""
    schema = create_schema()
    assert set(schema.names()) == {
        "cord_uid", "title", "abstract",
        "authors", "journal", "publish_time", "url",
    }


def test_schema_field_types():
    """Fields have correct Whoosh types."""
    schema = create_schema()
    assert isinstance(schema["cord_uid"], type(ID(stored=True)))
    assert isinstance(schema["title"], type(TEXT(stored=True)))
    assert isinstance(schema["abstract"], type(TEXT(stored=True)))
    assert isinstance(schema["authors"], type(STORED()))


def test_schema_title_is_stored():
    """Title and abstract are stored for display in results."""
    schema = create_schema()
    assert schema["title"].stored is True
    assert schema["abstract"].stored is True


def test_schema_stemming_analyzer():
    """Title analyzer performs stemming (e.g. 'vaccines' -> 'vaccin')."""
    schema = create_schema()
    analyzer = schema["title"].analyzer
    tokens = [t.text for t in analyzer("vaccines")]
    assert "vaccin" in tokens


# ── Index creation ──────────────────────────────────────────────────────────

def test_create_index_creates_directory(processed_csv, tmp_path):
    """Index directory is created and populated."""
    index_dir = tmp_path / "new_index"
    create_index(str(processed_csv), str(index_dir))

    assert index_dir.exists()
    assert any(index_dir.iterdir())


def test_create_index_document_count(processed_csv, tmp_path):
    """Index contains the correct number of documents."""
    index_dir = tmp_path / "idx"
    ix = create_index(str(processed_csv), str(index_dir))

    assert ix.doc_count() == EXPECTED_DOC_COUNT


def test_create_index_documents_retrievable(test_index_dir):
    """Documents can be searched after indexing."""
    from whoosh.qparser import QueryParser

    ix = index.open_dir(str(test_index_dir))
    with ix.searcher() as s:
        qp = QueryParser("title", schema=ix.schema)
        results = s.search(qp.parse("COVID-19"))
        assert len(results) > 0
