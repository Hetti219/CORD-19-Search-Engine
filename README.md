# CORD-19 Search Engine

A COVID-19 research publication search engine built using the CORD-19 dataset, implementing BM25 ranking algorithm with an inverted index structure.

## Overview

This search engine allows users to search through COVID-19 research papers using natural language queries. It implements:

- **Inverted Index**: Built using Whoosh for fast term-to-document lookups
- **BM25F Ranking**: Industry-standard probabilistic ranking algorithm
- **Multi-field Search**: Searches across both titles and abstracts
- **Web Interface**: Clean Flask-based UI for searching and browsing results

## Project Structure

```
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
│   └── style.css               # CSS styling
├── tests/
│   └── test_search.py          # Example searches for report
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## Requirements

- Python 3.8+
- pip (Python package manager)

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

3. **Build the search index**:
   ```bash
   python src/indexer.py
   ```
   This creates the Whoosh index in the `index/` directory.

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

| Field        | Type   | Indexed | Stored | Description                 |
| ------------ | ------ | ------- | ------ | --------------------------- |
| cord_uid     | ID     | No      | Yes    | Unique paper identifier     |
| title        | TEXT   | Yes     | Yes    | Paper title (searchable)    |
| abstract     | TEXT   | Yes     | Yes    | Paper abstract (searchable) |
| authors      | STORED | No      | Yes    | Author list                 |
| journal      | STORED | No      | Yes    | Journal name                |
| publish_time | STORED | No      | Yes    | Publication date            |
| url          | STORED | No      | Yes    | Link to paper               |

### Text Processing

The `StemmingAnalyzer` performs:

1. **Tokenisation**: Splits text into words
2. **Lowercasing**: Normalises case
3. **Stemming**: Reduces words to root form (e.g., "vaccines" → "vaccin")

## Configuration

### Sample Size

By default, the preprocessor uses 50,000 papers for faster development. To use the full dataset (~1M papers), edit `src/preprocessor.py`:

```python
# Change this line:
sample_size=50000  # Current setting

# To:
sample_size=None   # Full dataset
```

### Server Port

To change the default port (5000), edit `src/app.py`:

```python
app.run(debug=True, port=5000)  # Change port number here
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

| Query Type      | Example                                | Description                            |
| --------------- | -------------------------------------- | -------------------------------------- |
| **Boolean AND** | `"vaccine efficacy" AND pfizer`        | Requires both terms/phrases to match   |
| **Boolean OR**  | `vaccine OR immunization`              | Matches either term                    |
| **Boolean NOT** | `treatment NOT hydroxychloroquine`     | Excludes specific terms                |
| **Phrase**      | `"asymptomatic transmission"`          | Exact phrase matching                  |
| **Nested**      | `mask AND (efficacy OR effectiveness)` | Parentheses for operator precedence    |

**Note**: All searches are case-insensitive and use stemming (e.g., "vaccine" matches "vaccines").

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

## License

This project is for educational purposes as part of the 6CS030 Big Data Assessment.

## Dataset Citation

Wang, L.L., Lo, K., Chandrasekhar, Y. et al. CORD-19: The COVID-19 Open Research Dataset. arXiv preprint arXiv:2004.10706 (2020).

## Acknowledgments

- [Allen Institute for AI](https://allenai.org/) for the CORD-19 dataset
- [Whoosh](https://whoosh.readthedocs.io/) for the search library
- [Flask](https://flask.palletsprojects.com/) for the web framework
