"""
preprocessor.py
Cleans and prepares CORD-19 data for indexing.

Key operations:
1. Load metadata.csv
2. Remove duplicates
3. Handle missing values
4. Extract relevant fields
5. Save processed data
"""

import os
import pandas as pd

def preprocess_cord19(input_path, output_path, sample_size=None):
    """
    Main preprocessing function.

    Args:
        input_path: Path to metadata.csv
        output_path: Path to save processed CSV
        sample_size: Optional limit for testing (use 10000 for development)

    Returns:
        DataFrame of processed papers
    """
    print("Loading CORD-19 metadata...")
    df = pd.read_csv(input_path, low_memory=False)

    # Optional: Sample for faster development
    if sample_size:
        df = df.sample(n=min(sample_size, len(df)), random_state=42)

    print(f"Processing {len(df)} papers...")

    # Select relevant columns (these are what you'll index and display)
    columns_needed = [
        'cord_uid',       # Unique identifier
        'title',          # Paper title
        'abstract',       # Paper abstract
        'authors',        # Author list
        'publish_time',   # Publication date
        'journal',        # Journal name
        'url'             # Link to paper
    ]

    # Keep only columns that exist
    columns_present = [c for c in columns_needed if c in df.columns]
    df = df[columns_present].copy()

    # Remove papers without title or abstract (not useful for search)
    df = df.dropna(subset=['title', 'abstract'], how='all')

    # Remove duplicates based on title
    df = df.drop_duplicates(subset=['title'], keep='first')

    # Fill missing values
    df['authors'] = df['authors'].fillna('Unknown')
    df['journal'] = df['journal'].fillna('Unknown')
    df['publish_time'] = df['publish_time'].fillna('Unknown')
    df['url'] = df['url'].fillna('')

    # Save processed data
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Saved {len(df)} processed papers to {output_path}")

    return df

if __name__ == "__main__":
    # Use absolute paths relative to script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    preprocess_cord19(
        input_path=os.path.join(project_root, "data", "raw", "metadata.csv"),
        output_path=os.path.join(project_root, "data", "processed", "papers.csv"),
        #sample_size=50000  # Start with 50k for development, remove for full dataset
    )
