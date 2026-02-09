"""
Shared fixtures for the CORD-19 Search Engine test suite.

Provides sample data and reusable fixtures that build a small temporary
Whoosh index (8 documents) for fast, self-contained integration tests.
"""

import numpy as np
import pandas as pd
import pytest

from preprocessor import preprocess_cord19
from indexer import create_index
from searcher import CORD19Searcher


# ---------------------------------------------------------------------------
# Sample test data: 10 papers, 8 survive preprocessing
# ---------------------------------------------------------------------------

SAMPLE_PAPERS = [
    {
        "cord_uid": "uid001",
        "title": "COVID-19 vaccine efficacy in clinical trials",
        "abstract": (
            "This study evaluates the efficacy of COVID-19 vaccines in randomized "
            "clinical trials across multiple countries. The results demonstrate "
            "significant protection against severe disease and hospitalisation. "
            "Participants received two doses of the vaccine and were monitored over "
            "a period of six months for adverse effects and immune response. "
            "The findings support widespread vaccination as a public health measure "
            "to control the pandemic and reduce transmission rates globally."
        ),  # 468 chars — triggers truncation
        "authors": "Smith, J; Jones, A",
        "journal": "Lancet",
        "publish_time": "2021-03-15",
        "url": "https://example.com/paper1",
    },
    {
        "cord_uid": "uid002",
        "title": "SARS-CoV-2 transmission dynamics in indoor environments",
        "abstract": "Airborne transmission of SARS-CoV-2 poses significant risks in indoor settings.",
        "authors": "Brown, K",
        "journal": "Nature",
        "publish_time": "2020-11-01",
        "url": "https://example.com/paper2",
    },
    {
        "cord_uid": "uid003",
        "title": "Development of mRNA vaccines for coronavirus prevention",
        "abstract": (
            "This paper reviews the development of mRNA vaccines and their "
            "mechanism of action against coronavirus infections."
        ),
        "authors": "Lee, M",
        "journal": "Science",
        "publish_time": "2021-01-20",
        "url": "https://example.com/paper3",
    },
    {
        "cord_uid": "uid004",
        "title": "Coronavirus treatment options and therapeutic approaches",
        "abstract": (
            "A comprehensive review of treatment options for coronavirus disease, "
            "including antiviral drugs and supportive care strategies."
        ),
        "authors": "Chen, W",
        "journal": "BMJ",
        "publish_time": "2020-08-10",
        "url": "https://example.com/paper4",
    },
    {
        "cord_uid": "uid005",
        "title": "Pandemic lockdown effects on mental health",
        "abstract": (
            "This study examines the impact of pandemic lockdown measures on "
            "mental health outcomes across different demographic groups."
        ),
        "authors": "Garcia, R",
        "journal": "JAMA",
        "publish_time": "2021-05-22",
        "url": "https://example.com/paper5",
    },
    {
        "cord_uid": "uid006",
        "title": "Face mask efficacy and effectiveness against COVID-19",
        "abstract": (
            "Evaluating the efficacy and effectiveness of face masks in reducing "
            "COVID-19 transmission in community settings."
        ),
        "authors": "Taylor, S",
        "journal": "NEJM",
        "publish_time": "2020-12-05",
        "url": "https://example.com/paper6",
    },
    {
        # uid007: has title but NO abstract — survives dropna(how='all')
        "cord_uid": "uid007",
        "title": "Antibody response patterns in recovered patients",
        "abstract": np.nan,
        "authors": np.nan,
        "journal": np.nan,
        "publish_time": np.nan,
        "url": np.nan,
    },
    {
        # uid008: duplicate title of uid001 — removed by drop_duplicates
        "cord_uid": "uid008",
        "title": "COVID-19 vaccine efficacy in clinical trials",
        "abstract": "Different abstract text from a different study.",
        "authors": "Other, A",
        "journal": "Other Journal",
        "publish_time": "2021-06-01",
        "url": "https://example.com/paper8",
    },
    {
        # uid009: both title and abstract NaN — removed by dropna(how='all')
        "cord_uid": "uid009",
        "title": np.nan,
        "abstract": np.nan,
        "authors": "Nobody, X",
        "journal": "Unknown Journal",
        "publish_time": "2020-01-01",
        "url": "",
    },
    {
        "cord_uid": "uid010",
        "title": "Hydroxychloroquine treatment controversy and clinical evidence",
        "abstract": (
            "An analysis of the hydroxychloroquine treatment debate, examining "
            "clinical evidence for and against its use in COVID-19 patients."
        ),
        "authors": "Wilson, D",
        "journal": "Annals",
        "publish_time": "2020-07-18",
        "url": "https://example.com/paper10",
    },
]

from constants import EXPECTED_DOC_COUNT  # noqa: F401 — re-export for fixtures


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_csv(tmp_path):
    """Write sample papers to a CSV file and return its path."""
    df = pd.DataFrame(SAMPLE_PAPERS)
    csv_path = tmp_path / "metadata.csv"
    df.to_csv(csv_path, index=False)
    return csv_path


@pytest.fixture
def processed_csv(tmp_path, sample_csv):
    """Run the preprocessor on sample data and return the output path."""
    output_path = tmp_path / "processed" / "papers.csv"
    preprocess_cord19(str(sample_csv), str(output_path))
    return output_path


@pytest.fixture
def test_index_dir(tmp_path, processed_csv):
    """Build a Whoosh index from processed test data and return the directory."""
    index_dir = tmp_path / "index"
    create_index(str(processed_csv), str(index_dir))
    return index_dir


@pytest.fixture
def searcher(test_index_dir):
    """Create a CORD19Searcher from the test index."""
    return CORD19Searcher(str(test_index_dir))


@pytest.fixture
def flask_client_with_index(test_index_dir):
    """Flask test client with a working search index."""
    import app as app_module

    original = app_module.searcher
    app_module.searcher = CORD19Searcher(str(test_index_dir))
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        yield client
    app_module.searcher = original


@pytest.fixture
def flask_client_no_index():
    """Flask test client with searcher=None (no index)."""
    import app as app_module

    original = app_module.searcher
    app_module.searcher = None
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        yield client
    app_module.searcher = original
