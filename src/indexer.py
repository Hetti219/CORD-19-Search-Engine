"""
indexer.py
Creates a Whoosh search index from processed CORD-19 data.

This implements the INDEXING component of the search engine.
The index is an inverted index structure that maps terms to documents.
"""

import os
import pandas as pd
from whoosh import index
from whoosh.fields import Schema, TEXT, ID, STORED
from whoosh.analysis import StemmingAnalyzer
from tqdm import tqdm

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
        cord_uid=ID(stored=True, unique=True),
        url=STORED(),

        # TEXT fields: indexed and searchable
        # stored=True means we can retrieve the original text
        title=TEXT(stored=True, analyzer=analyzer),
        abstract=TEXT(stored=True, analyzer=analyzer),

        # STORED fields: returned in results but not searchable
        authors=STORED(),
        journal=STORED(),
        publish_time=STORED()
    )

    return schema

def create_index(processed_data_path, index_dir):
    """
    Build the search index from processed data.

    This is computationally intensive - runs once, then index is reused.

    Args:
        processed_data_path: Path to processed papers.csv
        index_dir: Directory to store the index
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

    # Write documents to index
    print("Building index...")
    writer = ix.writer()

    for _, row in tqdm(df.iterrows(), total=len(df), desc="Indexing"):
        writer.add_document(
            cord_uid=str(row.get('cord_uid', '')),
            title=str(row.get('title', '')),
            abstract=str(row.get('abstract', '')),
            authors=str(row.get('authors', '')),
            journal=str(row.get('journal', '')),
            publish_time=str(row.get('publish_time', '')),
            url=str(row.get('url', ''))
        )

    # Commit writes to disk
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
