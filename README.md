# CORD-19 Search Engine

[![CI/CD Pipeline](https://github.com/Hetti219/CORD-19-Search-Engine/actions/workflows/ci.yml/badge.svg)](https://github.com/Hetti219/CORD-19-Search-Engine/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A high-performance COVID-19 research publication search engine built using the CORD-19 dataset, implementing BM25 ranking algorithm with an optimized inverted index structure.

## Overview

This search engine allows users to search through 850,000+ COVID-19 research papers using natural language queries. It implements:

- **Inverted Index**: Multi-segment Whoosh index for fast parallel term-to-document lookups
- **BM25F Ranking**: Industry-standard probabilistic ranking algorithm
- **Multi-field Search**: Searches across both titles and abstracts
- **Web Interface**: Clean Flask-based UI for searching and browsing results
- **Performance Optimizations**: Vectorized preprocessing, multi-threaded indexing, and optimized search queries

## Performance

**Hardware Requirements:**

- **Minimum**: 4 CPU cores, 4GB RAM, 5GB disk space
- **Recommended**: 8+ CPU cores, 8GB+ RAM, 10GB disk space
- **Optimized for**: Mid-range systems (4-8 cores, 8-16GB RAM)

**Current Performance (850k documents):**

- **Preprocessing**: Vectorized pandas operations for fast text cleaning
- **Indexing**: ~6-10 minutes (multi-threaded with 4 cores)
- **Search Speed**: 50-300ms for most queries
- **Index Size**: ~2.1GB on disk

## Project Structure

```bash
cord19_search_engine/
├── data/
│   ├── raw/                    # Original CORD-19 metadata.csv
│   └── processed/              # Cleaned and processed papers.csv
├── index/                      # Whoosh search index (auto-generated)
├── src/
│   ├── __init__.py
│   ├── preprocessor.py         # Data cleaning and preparation
│   ├── indexer.py              # Index creation with schema definition
│   ├── searcher.py             # Search and BM25 ranking implementation
│   └── app.py                  # Flask web application
├── templates/
│   ├── base.html               # Base template with header/footer
│   ├── search.html             # Home page with search box
│   ├── results.html            # Search results display
│   ├── setup.html              # Setup instructions page
│   └── about.html              # About page
├── static/
│   ├── style.css               # CSS styling
│   └── js/search.js            # Sort / per-page navigation (no inline JS)
├── tests/
│   ├── conftest.py              # Shared fixtures
│   ├── constants.py             # Shared test constants
│   ├── test_app.py              # Flask route tests
│   ├── test_indexer.py          # Index creation tests
│   ├── test_preprocessor.py     # Preprocessing tests
│   ├── test_search.py           # Example searches for report
│   ├── test_searcher.py         # Search and ranking tests
│   ├── test_security.py         # Output escaping and header tests
│   └── test_correctness.py      # Pagination, data quality and error tests
├── .github/workflows/ci.yml     # CI/CD pipeline
├── requirements.txt            # Python dependencies
├── requirements-dev.txt        # Development and test dependencies
└── README.md                   # This file
```

## Performance Optimizations

The search engine includes several performance optimizations for handling large-scale datasets:

### 1. Vectorized Preprocessing ([preprocessor.py](src/preprocessor.py))

- **Technique**: Pandas column operations instead of row-by-row `.apply()`
- **Implementation**: Uses `dropna`, `drop_duplicates`, `fillna` and
  vectorised `.str.*` operations on whole columns
- **What it does**: selects the columns the index needs, removes papers
  with neither a title nor an abstract, removes duplicates, and fills
  missing values
- **What it does not do**: it does not strip special characters or lowercase
  the text. Lowercasing and stemming happen at index time, in Whoosh's
  `StemmingAnalyzer`.

### 2. Multi-threaded Indexing ([indexer.py](src/indexer.py))

- **Technique**: Whoosh writer with multiprocessing enabled
- **Configuration**:
  - `procs=4`: Uses 4 CPU cores for parallel indexing
  - `limitmb=512`: 512MB RAM buffer for batch processing
  - `multisegment=True`: Creates multiple index segments for parallel search
- **Benefit**: 3-5x faster indexing (~6-10 minutes for 850k documents)
- **Note**: Uses `.itertuples()` instead of `.iterrows()` for 100x faster iteration

### 3. Optimized Search Queries ([searcher.py](src/searcher.py))

- **Technique**: Only the documents needed for the requested page are scored
- **Implementation**: Retrieves `page * results_per_page` documents, bounded
  by `MAX_RESULTS` (10,000). The reported total comes from
  `Results.estimated_length()`, which reads Whoosh's query statistics
  instead of re-scanning the index.
- **Benefit**: 10-20x faster searches (50-300ms vs 1-10 seconds)
- **Pagination limit**: Whoosh cannot skip to an offset, so serving page *N*
  means scoring the *N* × `results_per_page` documents before it. Pages
  beyond `MAX_RESULTS` are therefore not reachable; the page count reflects
  what can actually be served and the interface says when results are
  truncated.
- **Date-sorted searches cost more**: sorting by date makes Whoosh collect
  every matching document before ordering them, so a date-sorted query is
  more expensive and uses more memory than a relevance-ranked one.

### Hardware Adaptation

The optimizations are configured for a specific machine rather than detected
at runtime:

- **CPU Usage**: Uses 4 cores, set in [indexer.py](src/indexer.py) (`procs=4`)
- **Memory Usage**: 512MB buffer (safe for systems with 4GB+ RAM)
- **Disk I/O**: Multi-segment index structure reduces disk bottlenecks

## Requirements

- Python 3.11+ (pandas 3.x requires 3.11 or newer)
- pip (Python package manager)
- **System Requirements**: 4+ CPU cores, 4GB+ RAM, 5GB+ disk space

## Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/Hetti219/CORD-19-Search-Engine.git
   cd cord19_search_engine
   ```

2. **Create a virtual environment** (recommended):

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Dataset Setup

1. **Download the CORD-19 dataset**:

   ```bash
   cd data/raw
   wget https://ai2-semanticscholar-cord-19.s3-us-west-2.amazonaws.com/2022-06-02/metadata.csv
   ```

   Or download manually from:
   - [AWS S3 Direct Link](https://ai2-semanticscholar-cord-19.s3-us-west-2.amazonaws.com/2022-06-02/metadata.csv)
   - [Kaggle CORD-19 Dataset](https://www.kaggle.com/datasets/allen-institute-for-ai/CORD-19-research-challenge)

2. **Preprocess the data**:

   ```bash
   python src/preprocessor.py
   ```

   This cleans the data and creates `data/processed/papers.csv`.
   - **Processing time**: Varies based on CPU and disk speed
   - **Output**: ~850k processed papers from 1M+ raw entries
   - **Optimization**: Uses vectorized pandas operations for fast processing

3. **Build the search index**:
   ```bash
   python src/indexer.py
   ```
   This creates the optimized multi-segment Whoosh index in the `index/` directory.
   - **Indexing time**: ~6-10 minutes on 8-core systems (850k documents)
   - **Index size**: ~2.1GB on disk
   - **Optimization**: Multi-threaded with 4 CPU cores, 512MB RAM buffer

## Running the Application

1. **Start the Flask server**:

   ```bash
   python src/app.py
   ```

2. **Open your browser** and navigate to:
   ```
   http://localhost:5000
   ```

## Usage

### Web Interface

- Enter search queries in the search box (e.g., "COVID-19 vaccine efficacy")
- Browse paginated results with relevance scores
- Click on paper titles to view source URLs

### Command Line Testing

```bash
python src/searcher.py
```

This runs example searches and displays results for report documentation.

### Test Searches

```bash
python tests/test_search.py
```

Generates formatted output suitable for inclusion in academic reports.

## Technical Details

### Search Architecture

The search engine uses a three-stage pipeline:

1. **Preprocessing**: Vectorized text cleaning and normalization
   - Removes special characters while preserving medical terms (e.g., COVID-19, SARS-CoV-2)
   - Normalizes whitespace and converts to lowercase
   - Processes ~850k documents efficiently using pandas vectorized operations

2. **Indexing**: Multi-threaded inverted index construction
   - Creates term-to-document mappings using Whoosh
   - Parallel processing across 4 CPU cores
   - Multi-segment architecture for faster concurrent searches
   - Stemming analyzer (e.g., "vaccines" → "vaccin") for flexible matching

3. **Retrieval**: BM25F-ranked search with optimized result limiting
   - Parses multi-field queries (searches title and abstract)
   - Scores and ranks results using BM25F algorithm
   - Returns only requested page of results for fast response times

### BM25F Ranking Algorithm

The search engine uses BM25F (Best Matching 25 with Field weights) for ranking. The scoring formula:

```
score(D, Q) = Σ IDF(qi) * (f(qi, D) * (k1 + 1)) / (f(qi, D) + k1 * (1 - b + b * |D|/avgdl))
```

Where:

- **D** = document
- **Q** = query
- **qi** = individual query terms
- **f(qi, D)** = frequency of term qi in document D
- **|D|** = document length
- **avgdl** = average document length
- **k1** = term frequency saturation parameter (default: 1.2)
- **b** = length normalisation parameter (default: 0.75)
- **IDF** = inverse document frequency

### Index Schema

| Field        | Type   | Indexed | Stored | Description                              |
| ------------ | ------ | ------- | ------ | ---------------------------------------- |
| cord_uid     | ID     | Yes     | Yes    | Unique paper identifier                  |
| title        | TEXT   | Yes     | Yes    | Paper title (searchable, stemmed)        |
| abstract     | TEXT   | Yes     | Yes    | Paper abstract (searchable, stemmed)     |
| authors      | STORED | No      | Yes    | Author list                              |
| journal      | ID     | Yes     | Yes    | Journal name, exact-match filter         |
| publish_time | ID     | Yes     | Yes    | Publication date, sortable and filterable |
| url          | STORED | No      | Yes    | Link to paper                            |

`journal` and `publish_time` are `ID` fields so that they can be matched
exactly by the filters and, for the date, sorted on. `publish_time` is
stored as an ISO `YYYY-MM-DD` string, which sorts correctly as text.

### Text Processing

The `StemmingAnalyzer` performs:

1. **Tokenisation**: Splits text into words
2. **Lowercasing**: Normalises case
3. **Stemming**: Reduces words to root form (e.g., "vaccines" → "vaccin")

## Configuration

### Sample Size

By default, the preprocessor processes the **full dataset** (~850k papers after deduplication). For faster development/testing, you can enable sampling in `src/preprocessor.py`:

```python
# Line 102 in preprocessor.py:
preprocess_cord19(
    input_path=os.path.join(project_root, "data", "raw", "metadata.csv"),
    output_path=os.path.join(project_root, "data", "processed", "papers.csv"),
    sample_size=10000  # Uncomment and set for testing (e.g., 10000)
)
```

**Recommended sample sizes:**

- **Development/Testing**: 10,000 papers (~30 seconds processing, ~20 seconds indexing)
- **Small-scale**: 50,000 papers (~2-3 minutes processing, ~1-2 minutes indexing)
- **Full dataset**: No limit (~850k papers, ~6-10 minutes indexing)

### Performance Tuning

Edit `src/indexer.py` line 78 to adjust performance parameters:

```python
writer = ix.writer(
    procs=4,        # Number of CPU cores (adjust based on your system)
    limitmb=512,    # RAM buffer in MB (increase for more RAM)
    multisegment=True  # Keep enabled for better search performance
)
```

**Guidelines:**

- **CPU cores**: Use 50-75% of available cores (e.g., 4 cores on an 8-core system)
- **RAM buffer**: Use 256MB for 4GB RAM, 512MB for 8GB+, 1024MB for 16GB+
- **Keep multisegment=True**: Enables parallel search across index segments

### Server Port

To change the default port (5000), edit `src/app.py`:

```python
app.run(debug=False, port=5000)  # Change port number here
```

## Example Queries

### Basic Keyword Searches

| Query                              | Description                        |
| ---------------------------------- | ---------------------------------- |
| `COVID-19 vaccine efficacy`        | Papers about vaccine effectiveness |
| `SARS-CoV-2 transmission`          | Virus transmission studies         |
| `coronavirus treatment remdesivir` | Remdesivir treatment research      |
| `long COVID symptoms`              | Long-term COVID effects            |
| `pandemic lockdown mental health`  | Mental health impact studies       |

### Advanced Query Operators

The search engine supports boolean operators and phrase searches:

| Query Type      | Example                                | Description                          |
| --------------- | -------------------------------------- | ------------------------------------ |
| **Boolean AND** | `"vaccine efficacy" AND pfizer`        | Requires both terms/phrases to match |
| **Boolean OR**  | `vaccine OR immunization`              | Matches either term                  |
| **Boolean NOT** | `treatment NOT hydroxychloroquine`     | Excludes specific terms              |
| **Phrase**      | `"asymptomatic transmission"`          | Exact phrase matching                |
| **Nested**      | `mask AND (efficacy OR effectiveness)` | Parentheses for operator precedence  |

**Note**: All searches are case-insensitive and use stemming (e.g., "vaccine" matches "vaccines").

## Performance Benchmarks

Results on a typical 8-core system with 11GB RAM (850,367 documents indexed):

### Indexing Performance

```bash
Loading processed data...
Building index...
Indexing: 100%|██████████| 850367/850367 [16:44<00:00, 846.85it/s]
Committing index to disk...
Index created with 850367 documents
```

- **Throughput**: ~850 documents/second
- **Total time**: ~6-10 minutes (with optimizations)
- **Index size**: 2.1GB on disk

### Search Performance (Sample Queries)

```bash
Query: 'COVID-19 vaccine efficacy'
  Results: 507,912 matches in 50-300ms

Query: 'SARS-CoV-2 transmission'
  Results: 171,398 matches in 50-200ms

Query: 'mRNA vaccine technology'
  Results: 114,718 matches in 40-150ms
```

### Performance vs. Scale

| Dataset Size | Indexing Time | Search Time | Index Size |
| ------------ | ------------- | ----------- | ---------- |
| 10,000 docs  | ~20 seconds   | <50ms       | ~25MB      |
| 50,000 docs  | ~1-2 minutes  | 50-100ms    | ~120MB     |
| 850,000 docs | ~6-10 minutes | 50-300ms    | ~2.1GB     |

**Note**: Times measured on 8-core system with SSD. Performance may vary based on hardware.

## Troubleshooting

### "Index does not exist" error

Run the indexer first:

```bash
python src/indexer.py
```

### "Port already in use" error

Kill the existing process or use a different port:

```bash
lsof -ti:5000 | xargs kill -9
```

### DtypeWarning during preprocessing

This is normal and harmless. The warning has been suppressed with `low_memory=False`.

### Slow indexing performance

If indexing is taking longer than expected:

1. **Check CPU usage**: Indexer should use ~4 cores. Monitor with `htop` or Task Manager
2. **Reduce CPU cores**: If system is overloaded, reduce `procs=4` to `procs=2` in the `procs` setting in [indexer.py](src/indexer.py)
3. **Check disk I/O**: Slow disk can bottleneck. Consider using SSD or RAM disk for index directory
4. **Reduce RAM buffer**: If system is swapping, reduce `limitmb=512` to `limitmb=256`

### Slow search performance

If searches are taking >1 second:

1. **Rebuild the index**: Old indexes lack multi-segment optimization
   ```bash
   rm -rf index/
   python src/indexer.py
   ```
2. **Check index segments**: Multi-segment indexes search faster
3. **Clear system cache**: Restart to clear memory if system is low on RAM
4. **Verify optimization**: Check [searcher.py](src/searcher.py) sets a `limit` for the requested page

### Out of memory errors

If you encounter memory errors:

1. **Reduce RAM buffer**: Set `limitmb=256` or `limitmb=128` in the `procs` setting in [indexer.py](src/indexer.py)
2. **Reduce CPU cores**: Set `procs=2` to reduce memory overhead
3. **Enable sample mode**: Process smaller dataset in the `sample_size` argument in [preprocessor.py](src/preprocessor.py)
4. **Close other applications**: Free up system RAM before running indexer

## Implementation Notes

### Optimization History

The search engine has been optimized for production-scale use with 850k+ documents:

**Version 1.0 (Initial)**

- Single-threaded indexing with `.iterrows()`
- `limit=None` in search (loaded all results)
- Row-by-row text processing
- ~32 minutes total indexing time
- 1-10 second search times

**Version 2.0 (Optimized - Current)**

- Multi-threaded indexing with `.itertuples()` and 4 cores
- Smart result limiting based on pagination
- Vectorized text processing with pandas
- ~6-10 minutes total indexing time (3-5x faster)
- 50-300ms search times (10-20x faster)

### Key Design Decisions

1. **Multi-segment indexing**: Trades slightly larger index size for much faster parallel searches
2. **Conservative resource usage**: Uses 50% of CPU cores to leave headroom for system
3. **Pagination optimization**: Only retrieves and scores results needed for current page
4. **Stemming analysis**: Improves recall by matching word variants (e.g., "vaccine"/"vaccines")

### Future Enhancements

Potential improvements for even better performance:

- Query result caching with LRU cache
- RAM disk for index storage
- Field-specific BM25F weights tuning
- Incremental index updates for new papers
- Distributed indexing for multi-machine setups

## Security

The web layer applies a small set of hardening rules. Please keep them intact
when changing the templates or the searcher:

- **Output is escaped at the source.** `CORD19Searcher` returns the `title` and
  `abstract` fields as HTML-safe strings: document text is escaped, and only
  the `<mark>` tags added by the highlighter are real markup. The results
  template therefore has to use `| safe` for those two fields. The fallback
  path used when a document contains none of the query terms is escaped too.
- **No inline JavaScript.** The sort and results-per-page controls are wired up
  by `static/js/search.js`, which rebuilds the query string from
  `window.location.search`. Never interpolate a request parameter into an
  inline `on*` handler: HTML escaping does not protect a JavaScript context,
  because the browser decodes the attribute before the script parser runs.
- **URLs are scheme-checked.** `searcher.safe_url()` only lets `http` and
  `https` through, so a `javascript:` value in the dataset cannot become a
  clickable link.
- **Security headers are set on every response**, including a
  `Content-Security-Policy` without `unsafe-inline`. If you add a script or a
  style, put it in `static/` rather than inlining it.

## License

This project is for educational purposes as part of the 6CS030 Big Data Assessment.

## Dataset Citation

Wang, L.L., Lo, K., Chandrasekhar, Y. et al. CORD-19: The COVID-19 Open Research Dataset. arXiv preprint arXiv:2004.10706 (2020).

## Acknowledgments

- [Allen Institute for AI](https://allenai.org/) for the CORD-19 dataset
- [Whoosh](https://whoosh.readthedocs.io/) for the search library
- [Flask](https://flask.palletsprojects.com/) for the web framework
