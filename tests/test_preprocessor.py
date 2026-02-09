"""Tests for src/preprocessor.py"""

import pandas as pd

from preprocessor import preprocess_cord19
from constants import EXPECTED_DOC_COUNT


# ── Basic processing ────────────────────────────────────────────────────────

def test_basic_preprocessing(sample_csv, tmp_path):
    """Preprocessor outputs a CSV with the expected columns and row count."""
    output = tmp_path / "out" / "papers.csv"
    df = preprocess_cord19(str(sample_csv), str(output))

    assert output.exists()
    assert list(df.columns) == [
        "cord_uid", "title", "abstract", "authors",
        "publish_time", "journal", "url",
    ]
    assert len(df) == EXPECTED_DOC_COUNT


def test_return_value_is_dataframe(sample_csv, tmp_path):
    """Return value is a DataFrame matching the written CSV."""
    output = tmp_path / "papers.csv"
    df = preprocess_cord19(str(sample_csv), str(output))

    assert isinstance(df, pd.DataFrame)
    df_disk = pd.read_csv(output)
    assert len(df) == len(df_disk)


# ── Deduplication ───────────────────────────────────────────────────────────

def test_deduplication(sample_csv, tmp_path):
    """Duplicate titles are removed, keeping the first occurrence."""
    output = tmp_path / "papers.csv"
    df = preprocess_cord19(str(sample_csv), str(output))

    dup_title = "COVID-19 vaccine efficacy in clinical trials"
    matches = df[df["title"] == dup_title]
    assert len(matches) == 1
    assert matches.iloc[0]["cord_uid"] == "uid001"


# ── NaN handling ────────────────────────────────────────────────────────────

def test_dropna_removes_all_nan_rows(sample_csv, tmp_path):
    """Rows where both title AND abstract are NaN are dropped."""
    output = tmp_path / "papers.csv"
    df = preprocess_cord19(str(sample_csv), str(output))

    assert "uid009" not in df["cord_uid"].values


def test_dropna_keeps_partial_nan_rows(sample_csv, tmp_path):
    """Rows with title but NaN abstract survive (how='all')."""
    output = tmp_path / "papers.csv"
    df = preprocess_cord19(str(sample_csv), str(output))

    assert "uid007" in df["cord_uid"].values


def test_fillna_defaults(sample_csv, tmp_path):
    """Missing authors/journal/publish_time filled with 'Unknown', url with ''."""
    output = tmp_path / "papers.csv"
    df = preprocess_cord19(str(sample_csv), str(output))

    row = df[df["cord_uid"] == "uid007"].iloc[0]
    assert row["authors"] == "Unknown"
    assert row["journal"] == "Unknown"
    assert row["publish_time"] == "Unknown"
    assert row["url"] == ""


# ── Sampling ────────────────────────────────────────────────────────────────

def test_sample_size(sample_csv, tmp_path):
    """sample_size limits the input before processing."""
    output = tmp_path / "papers.csv"
    df = preprocess_cord19(str(sample_csv), str(output), sample_size=4)

    assert len(df) <= 4


# ── Filesystem ──────────────────────────────────────────────────────────────

def test_output_directory_created(sample_csv, tmp_path):
    """Nested output directory is created automatically."""
    output = tmp_path / "deep" / "nested" / "dir" / "papers.csv"
    preprocess_cord19(str(sample_csv), str(output))

    assert output.exists()
