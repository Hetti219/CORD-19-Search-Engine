"""
searcher.py
Implements search functionality with BM25 ranking.

BM25 (Best Matching 25) is the ranking algorithm used.
This is the core RETRIEVAL FUNCTION for your search engine.
"""

from whoosh import index
from whoosh.qparser import MultifieldParser, OrGroup
from whoosh.scoring import BM25F

class CORD19Searcher:
    """
    Search engine class that handles query processing and result ranking.
    """

    def __init__(self, index_dir):
        """
        Initialise the searcher with an existing index.

        Args:
            index_dir: Path to the Whoosh index directory
        """
        self.ix = index.open_dir(index_dir)

        # Configure the query parser to search multiple fields
        # OrGroup means: match if term appears in ANY field
        self.parser = MultifieldParser(
            ["title", "abstract"],  # Fields to search
            schema=self.ix.schema,
            group=OrGroup  # OR logic between terms
        )

    def search(self, query_string, page=1, results_per_page=10):
        """
        Execute a search query and return ranked results.

        Args:
            query_string: User's search query
            page: Page number for pagination (1-indexed)
            results_per_page: Number of results per page

        Returns:
            dict containing:
                - results: List of result dictionaries
                - total: Total number of matches
                - page: Current page number
                - total_pages: Total number of pages

        RANKING EXPLANATION (for report):
        -----------------------------------
        Whoosh uses BM25F by default. The score for each document is:

        score(D, Q) = Σ IDF(qi) * (f(qi, D) * (k1 + 1)) / (f(qi, D) + k1 * (1 - b + b * |D|/avgdl))

        Where:
        - D = document
        - Q = query
        - qi = individual query terms
        - f(qi, D) = frequency of term qi in document D
        - |D| = document length
        - avgdl = average document length
        - k1, b = tuning parameters (defaults: k1=1.2, b=0.75)
        - IDF = inverse document frequency = log((N - n + 0.5) / (n + 0.5))
        - N = total documents, n = documents containing term

        This balances:
        1. Term frequency (more occurrences = more relevant)
        2. Document length (normalises for long vs short documents)
        3. Term rarity (rare terms are more discriminating)
        """

        # Parse the query string
        query = self.parser.parse(query_string)

        # Open a searcher with BM25F scoring
        with self.ix.searcher(weighting=BM25F()) as searcher:
            # Execute search
            results = searcher.search(
                query,
                limit=None  # Get all results for accurate pagination
            )

            total = len(results)
            total_pages = (total + results_per_page - 1) // results_per_page

            # Calculate slice for current page
            start = (page - 1) * results_per_page
            end = start + results_per_page

            # Extract results for current page
            result_list = []
            for hit in results[start:end]:
                result_list.append({
                    'cord_uid': hit.get('cord_uid', ''),
                    'title': hit.get('title', 'No title'),
                    'abstract': hit.get('abstract', 'No abstract')[:300] + '...',
                    'authors': hit.get('authors', 'Unknown'),
                    'journal': hit.get('journal', 'Unknown'),
                    'publish_time': hit.get('publish_time', 'Unknown'),
                    'url': hit.get('url', ''),
                    'score': hit.score  # BM25 score
                })

            return {
                'results': result_list,
                'total': total,
                'page': page,
                'total_pages': total_pages,
                'query': query_string
            }

    def get_index_stats(self):
        """
        Get statistics about the index (useful for report).
        """
        return {
            'total_documents': self.ix.doc_count(),
            'fields': list(self.ix.schema.names())
        }


# Example usage and testing (include these in your report)
if __name__ == "__main__":
    searcher = CORD19Searcher("index")

    # Example searches to include in report
    test_queries = [
        "COVID-19 vaccine efficacy",
        "SARS-CoV-2 transmission",
        "coronavirus treatment remdesivir",
        "long COVID symptoms",
        "pandemic lockdown mental health"
    ]

    print("=" * 60)
    print("EXAMPLE SEARCHES FOR REPORT")
    print("=" * 60)

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        results = searcher.search(query, page=1, results_per_page=3)
        print(f"Total results: {results['total']}")
        print("Top 3 results:")
        for i, r in enumerate(results['results'], 1):
            print(f"  {i}. {r['title'][:60]}... (Score: {r['score']:.2f})")
