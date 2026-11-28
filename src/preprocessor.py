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

# Columns the indexer expects to find in the processed CSV.
COLUMNS_NEEDED = [
    'cord_uid',       # Unique identifier
    'title',          # Paper title
    'abstract',       # Paper abstract
    'authors',        # Author list
    'publish_time',   # Publication date
    'journal',        # Journal name
    'url'             # Link to paper
]

# Placeholder written for a publication date that is not known. It sorts
# after every real date, so the searcher can keep such papers out of a
# date-sorted result set.
UNKNOWN_PUBLISH_TIME = 'Unknown'

# Titles shorter than this are not distinctive enough to identify a
# paper. Two different papers called "Editorial" or "Introduction" are
# common in the dataset and must not be treated as duplicates.
MIN_DISTINCTIVE_TITLE_LENGTH = 30


def _normalised_titles(series):
    """Return a normalised form of a title column for duplicate detection.

    Case and whitespace differences are removed so that the same paper
    deposited as "COVID-19" and "covid-19 " is recognised as one entry.
    Missing titles become an empty string so they are not all collapsed
    into a single group.
    """
    return (series.fillna('')
            .astype(str)
            .str.lower()
            .str.replace(r'\s+', ' ', regex=True)
            .str.strip())


def _remove_duplicates(df):
    """Remove duplicate papers from the frame.

    The same paper is sometimes deposited more than once, sometimes under
    a different cord_uid, so titles are normalised before they are
    compared. Identical identifiers are removed first, and titles that
    are too short to identify a paper are left alone so that unrelated
    papers sharing a generic title are both kept.
    """
    if 'cord_uid' in df.columns:
        has_uid = df['cord_uid'].notna()
        df = df[~(has_uid & df['cord_uid'].duplicated(keep='first'))]

    if 'title' in df.columns:
        title_key = _normalised_titles(df['title'])
        distinctive = title_key.str.len() >= MIN_DISTINCTIVE_TITLE_LENGTH
        duplicate = distinctive & title_key.duplicated(keep='first')
        df = df[~duplicate]

    return df


def _fill_missing_values(df):
    """Fill missing values and give unidentifiable papers an identifier.

    Titles and abstracts are filled with an empty string: leaving them as
    NaN would make the indexer store the text "nan" as the paper's title
    or abstract.
    """
    # A paper without an identifier cannot be referred to later, so a
    # surrogate one is generated for it. The DataFrame index is unique, so
    # the generated identifiers are too.
    if 'cord_uid' in df.columns:
        missing_uid = (df['cord_uid'].isna()
                       | (df['cord_uid'].astype(str).str.strip() == ''))
        if missing_uid.any():
            df.loc[missing_uid, 'cord_uid'] = (
                'missing-' + df.index[missing_uid].astype(str))

    defaults = {
        'abstract': '',
        'authors': 'Unknown',
        'journal': 'Unknown',
        'publish_time': UNKNOWN_PUBLISH_TIME,
        'url': '',
    }
    for column, default in defaults.items():
        if column in df.columns:
            df[column] = df[column].fillna(default)
        else:
            df[column] = default
    df['title'] = df['title'].fillna('')

    return df


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
    columns_present = [c for c in COLUMNS_NEEDED if c in df.columns]
    missing = [c for c in COLUMNS_NEEDED if c not in df.columns]
    if 'title' in missing:
        raise ValueError(
            "metadata.csv must contain a 'title' column "
            f"(missing: {', '.join(missing)})")
    if missing:
        print(f"Warning: metadata.csv is missing column(s): {', '.join(missing)}")
    df = df[columns_present].copy()

    # Remove papers without title or abstract (not useful for search).
    # Only columns that are actually present can be checked here.
    usable = [c for c in ('title', 'abstract') if c in df.columns]
    if usable:
        df = df.dropna(subset=usable, how='all')

    df = _remove_duplicates(df)
    df = _fill_missing_values(df)

    # Save processed data
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
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
        # sample_size=50000  # Start with 50k for development, remove for full dataset
    )
