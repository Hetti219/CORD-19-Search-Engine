"""
indexer.py
Creates a Whoosh search index from processed CORD-19 data.

This implements the INDEXING component of the search engine.
The index is an inverted index structure that maps terms to documents.
"""

import math
import os
import pandas as pd
from whoosh import index
from whoosh.fields import Schema, TEXT, ID, STORED
from whoosh.analysis import StemmingAnalyzer
from tqdm import tqdm

# Columns the processed CSV has to provide.
REQUIRED_COLUMNS = [
    'cord_uid',       # Unique identifier
    'title',          # Paper title
    'abstract',       # Paper abstract
    'authors',        # Author list
    'publish_time',   # Publication date
    'journal',        # Journal name
    'url'             # Link to paper
]


def create_schema():
    """
    Define the index schema.

    Schema determines:
    - What fields are indexed (searchable)
    - What fields are stored (returned in results)
    - How text is analysed (tokenisation, stemming)

    The StemmingAnalyzer handles:
    - Tokenisation: "COVID-19 vaccines" → ["covid", "19", "vaccin"]
    - Lowercasing: "SARS" → "sars"
    - Stemming: "vaccines" → "vaccin" (so "vaccine" matches "vaccines")
    """
    analyzer = StemmingAnalyzer()

    schema = Schema(
        # ID fields: stored but not tokenised
        cord_uid=ID(stored=True),
        url=STORED(),

        # TEXT fields: indexed and searchable
        # stored=True means we can retrieve the original text
        title=TEXT(stored=True, analyzer=analyzer),
        abstract=TEXT(stored=True, analyzer=analyzer),

        # STORED fields: returned in results but not searchable
        authors=STORED(),
        # ID with stored=True enables exact-match journal filtering for faceted search
        journal=ID(stored=True),
        # ID with sortable=True enables sort-by-date (ISO dates sort lexicographically)
        publish_time=ID(stored=True, sortable=True)
    )

    return schema


def _as_text(value):
    """Return a value as a string, mapping missing values to an empty string.

    ``str(float('nan'))`` is the three character text ``"nan"``, so a
    missing title or abstract would otherwise be indexed as the literal
    word "nan" and match a search for it.
    """
    if value is None:
        return ''
    if isinstance(value, float) and math.isnan(value):
        return ''
    return str(value)


def create_index(processed_data_path, index_dir):
    """
    Build the search index from processed data.

    This is computationally intensive - runs once, then index is reused.

    Args:
        processed_data_path: Path to processed papers.csv
        index_dir: Directory to store the index

    Raises:
        ValueError: If the processed CSV is missing a required column or
            contains duplicate paper identifiers.
    """
    # Create index directory if it doesn't exist
    if not os.path.exists(index_dir):
        os.makedirs(index_dir)

    # Create index with our schema
    schema = create_schema()
    ix = index.create_in(index_dir, schema)

    # Load processed data
    print("Loading processed data...")
    df = pd.read_csv(processed_data_path)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            "Processed data is missing required column(s): "
            f"{', '.join(missing)}. "
            "Re-run src/preprocessor.py to regenerate it.")

    # A missing or repeated identifier makes the index ambiguous, so it is
    # reported rather than silently accepted.
    empty_ids = df['cord_uid'].isna() | (df['cord_uid'].astype(str).str.strip() == '')
    if empty_ids.any():
        raise ValueError(
            "Processed data contains papers without an identifier "
            f"({int(empty_ids.sum())} of {len(df)} rows). "
            "Re-run src/preprocessor.py to regenerate it.")

    duplicated = df['cord_uid'].duplicated()
    if duplicated.any():
        raise ValueError(
            "Processed data contains duplicate paper identifiers "
            f"({int(duplicated.sum())} of {len(df)} rows). "
            "Re-run src/preprocessor.py to regenerate it.")

    # Write documents to index
    print("Building index...")
    # Optimize writer for performance:
    # - procs=4: Use 4 CPU cores (leaving 4 free for system)
    # - limitmb=512: Use up to 512MB RAM buffer (safe for 11GB system)
    # - multisegment=True: Create multiple segments for parallel processing
    writer = ix.writer(procs=4, limitmb=512, multisegment=True)

    # Use itertuples() instead of iterrows() - 100x faster!
    # itertuples() returns named tuples instead of Series objects
    try:
        for row in tqdm(df.itertuples(), total=len(df), desc="Indexing"):
            writer.add_document(
                cord_uid=_as_text(row.cord_uid),
                title=_as_text(row.title),
                abstract=_as_text(row.abstract),
                authors=_as_text(row.authors),
                journal=_as_text(row.journal),
                publish_time=_as_text(row.publish_time),
                url=_as_text(row.url)
            )
    except Exception:
        # Release the writer without committing a half-built index
        writer.cancel()
        raise

    # Commit writes to disk (optimized with multisegment)
    print("Committing index to disk...")
    writer.commit()

    print(f"Index created with {ix.doc_count()} documents")
    return ix


if __name__ == "__main__":
    # Use absolute paths relative to script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    create_index(
        processed_data_path=os.path.join(project_root, "data", "processed", "papers.csv"),
        index_dir=os.path.join(project_root, "index")
    )
