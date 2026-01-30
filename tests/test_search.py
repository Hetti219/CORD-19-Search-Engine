"""
test_search.py
Example searches for report documentation.

This script runs test queries against the search engine and
outputs results in a format suitable for inclusion in the report.
"""

import sys
import os

# Add parent directory to path so we can import from src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from searcher import CORD19Searcher


def run_test_searches():
    """
    Run example searches and display results for report.
    """
    # Initialize searcher
    index_path = os.path.join(os.path.dirname(__file__), '..', 'index')
    searcher = CORD19Searcher(index_path)

    # Get index statistics
    stats = searcher.get_index_stats()
    print("=" * 70)
    print("CORD-19 SEARCH ENGINE - TEST RESULTS")
    print("=" * 70)
    print(f"\nIndex Statistics:")
    print(f"  Total Documents: {stats['total_documents']}")
    print(f"  Indexed Fields: {', '.join(stats['fields'])}")

    # Example searches to include in report
    # Simple keyword queries
    test_queries = [
        "COVID-19 vaccine efficacy",
        "SARS-CoV-2 transmission",
        "coronavirus treatment remdesivir",
        "long COVID symptoms",
        "pandemic lockdown mental health"
    ]

    # Advanced queries (boolean and phrase)
    # These demonstrate the query parser's support for complex search operators
    advanced_queries = [
        '"vaccine efficacy" AND pfizer',           # Phrase + Boolean AND: exact phrase combined with keyword
        'vaccine OR immunization',                  # Boolean OR: matches either term
        'treatment NOT hydroxychloroquine',         # Boolean NOT: excludes specific term
        '"asymptomatic transmission"',              # Exact phrase: matches exact word sequence
        'mask AND (efficacy OR effectiveness)'      # Nested boolean: parentheses for precedence
    ]

    # Combine all queries for testing
    all_queries = test_queries + advanced_queries

    print("\n" + "=" * 70)
    print("EXAMPLE SEARCHES FOR REPORT")
    print("=" * 70)
    print("\nThis includes:")
    print("  - Basic keyword searches (5 queries)")
    print("  - Advanced boolean queries: AND, OR, NOT (3 queries)")
    print("  - Phrase searches using quotes (2 queries)")
    print("  - Nested boolean with parentheses (1 query)")
    print("\nAll searches use BM25F ranking across title and abstract fields.")

    for query in all_queries:
        print(f"\n{'─' * 70}")
        print(f"Query: '{query}'")
        print("─" * 70)

        results = searcher.search(query, page=1, results_per_page=5)

        print(f"Total Results: {results['total']}")
        print(f"\nTop 5 Results:")

        for i, r in enumerate(results['results'], 1):
            print(f"\n  {i}. Title: {r['title'][:70]}{'...' if len(r['title']) > 70 else ''}")
            print(f"     Authors: {r['authors'][:50]}{'...' if len(r['authors']) > 50 else ''}")
            print(f"     Journal: {r['journal']}")
            print(f"     Date: {r['publish_time']}")
            print(f"     BM25 Score: {r['score']:.4f}")

    print("\n" + "=" * 70)
    print("END OF TEST RESULTS")
    print("=" * 70)


def generate_report_table():
    """
    Generate a markdown table of search results for the report.
    """
    index_path = os.path.join(os.path.dirname(__file__), '..', 'index')
    searcher = CORD19Searcher(index_path)

    test_queries = [
        "COVID-19 vaccine efficacy",
        "SARS-CoV-2 transmission",
        "coronavirus treatment remdesivir",
        "long COVID symptoms",
        "pandemic lockdown mental health"
    ]

    advanced_queries = [
        '"vaccine efficacy" AND pfizer',
        'vaccine OR immunization',
        'treatment NOT hydroxychloroquine',
        '"asymptomatic transmission"',
        'mask AND (efficacy OR effectiveness)'
    ]

    print("\n## Search Results Table (for Report)\n")
    print("### Basic Keyword Searches\n")
    print("| Query | Total Results | Top Result | BM25 Score |")
    print("|-------|---------------|------------|------------|")

    for query in test_queries:
        results = searcher.search(query, page=1, results_per_page=1)
        total = results['total']
        if results['results']:
            top_title = results['results'][0]['title'][:40] + "..."
            top_score = f"{results['results'][0]['score']:.2f}"
        else:
            top_title = "No results"
            top_score = "N/A"
        print(f"| {query} | {total} | {top_title} | {top_score} |")

    print("\n### Advanced Boolean & Phrase Searches\n")
    print("| Query Type | Query | Total Results | BM25 Score |")
    print("|------------|-------|---------------|------------|")

    query_types = [
        "Phrase + AND",
        "Boolean OR",
        "Boolean NOT",
        "Exact Phrase",
        "Nested Boolean"
    ]

    for qtype, query in zip(query_types, advanced_queries):
        results = searcher.search(query, page=1, results_per_page=1)
        total = results['total']
        if results['results']:
            top_score = f"{results['results'][0]['score']:.2f}"
        else:
            top_score = "N/A"
        print(f"| {qtype} | `{query}` | {total} | {top_score} |")


if __name__ == "__main__":
    try:
        run_test_searches()
        print("\n")
        generate_report_table()
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure you have:")
        print("1. Preprocessed the CORD-19 data (python src/preprocessor.py)")
        print("2. Built the search index (python src/indexer.py)")
