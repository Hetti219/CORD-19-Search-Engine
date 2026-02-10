"""
searcher.py
Implements search functionality with BM25 ranking.

BM25 (Best Matching 25) is the ranking algorithm used.
This is the core RETRIEVAL FUNCTION for your search engine.
"""

from collections import Counter

from whoosh import index
from whoosh.qparser import MultifieldParser, OrGroup
from whoosh.query import Term, TermRange, And
from whoosh.scoring import BM25F
from whoosh.sorting import FieldFacet
from whoosh.highlight import Highlighter, SentenceFragmenter, WholeFragmenter, HtmlFormatter

VALID_SORT_OPTIONS = ("relevance", "date_desc", "date_asc")
VALID_PER_PAGE_OPTIONS = (10, 25, 50)

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

        # Configure highlighters for query term highlighting in results
        # SentenceFragmenter produces complete sentences containing query terms
        # (like Google Scholar/PubMed) instead of cutting mid-sentence
        formatter = HtmlFormatter(tagname="mark", classname="highlight", between=" ... ")
        self.abstract_highlighter = Highlighter(
            fragmenter=SentenceFragmenter(maxchars=300),
            formatter=formatter
        )
        self.title_highlighter = Highlighter(
            fragmenter=WholeFragmenter(),
            formatter=formatter
        )

    def search(self, query_string, page=1, results_per_page=10, sort_by="relevance",
               date_from=None, date_to=None, journal=None):
        """
        Execute a search query and return ranked results.

        Args:
            query_string: User's search query
            page: Page number for pagination (1-indexed)
            results_per_page: Number of results per page
            sort_by: Sort order — "relevance" (BM25F score, default),
                     "date_desc" (newest first), or "date_asc" (oldest first)
            date_from: Start date for filtering (ISO format YYYY-MM-DD)
            date_to: End date for filtering (ISO format YYYY-MM-DD)
            journal: Exact journal name to filter by

        Returns:
            dict containing:
                - results: List of result dictionaries
                - total: Total number of matches
                - page: Current page number
                - total_pages: Total number of pages
                - sort: Active sort option
                - date_from/date_to: Active date filter values
                - journal: Active journal filter
                - facets: Dict with top journals and years

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

        if sort_by not in VALID_SORT_OPTIONS:
            sort_by = "relevance"

        # Parse the query string
        query = self.parser.parse(query_string)

        # Open a searcher with BM25F scoring
        with self.ix.searcher(weighting=BM25F()) as searcher:
            # OPTIMIZATION: Only retrieve what we need instead of all results
            # Calculate how many results we need for this page
            # Add buffer of 1000 to ensure accurate counts for reasonable pagination
            needed = page * results_per_page
            limit = max(needed, 100)  # Minimum 100 for good count estimates

            # For very deep pagination (page > 100), cap limit to avoid memory issues
            if limit > 10000:
                limit = 10000

            # Determine sort order
            sort_facet = None
            if sort_by == "date_desc":
                sort_facet = FieldFacet("publish_time", reverse=True)
            elif sort_by == "date_asc":
                sort_facet = FieldFacet("publish_time", reverse=False)

            # Build filter query from active filters
            filter_query = self._build_filter_query(date_from, date_to, journal)

            # Execute search with optimized limit
            results = searcher.search(query, limit=limit, sortedby=sort_facet,
                                      filter=filter_query)

            # Use scored (actual retrieved) count for pagination so every
            # page is guaranteed to have results — estimated_length() can
            # vastly overcount when limit caps the result set, creating
            # empty "phantom" pages at the end.
            total = len(results)
            total_pages = (total + results_per_page - 1) // results_per_page

            # Calculate slice for current page
            start = (page - 1) * results_per_page
            end = start + results_per_page

            # Compute facets from top results for the sidebar
            facets = self._extract_facets(results, min(total, 200))

            # Extract results for current page with highlighted query terms
            result_list = []
            for hit in results[start:end]:
                # Sentence-aware highlighted abstract snippets
                highlighted_abstract = self.abstract_highlighter.highlight_hit(hit, "abstract", top=3)
                if not highlighted_abstract:
                    abstract = hit.get('abstract', 'No abstract')
                    highlighted_abstract = self._truncate_at_sentence(abstract)

                # Highlighted title (full text with matching terms marked)
                highlighted_title = self.title_highlighter.highlight_hit(hit, "title")
                if not highlighted_title:
                    highlighted_title = hit.get('title', 'No title')

                result_list.append({
                    'cord_uid': hit.get('cord_uid', ''),
                    'title': highlighted_title,
                    'abstract': highlighted_abstract,
                    'authors': hit.get('authors', 'Unknown'),
                    'journal': hit.get('journal', 'Unknown'),
                    'publish_time': hit.get('publish_time', 'Unknown'),
                    'url': hit.get('url', ''),
                    'score': hit.score if isinstance(hit.score, (int, float)) else 0.0
                })

            return {
                'results': result_list,
                'total': total,
                'page': page,
                'total_pages': total_pages,
                'results_per_page': results_per_page,
                'page_range': self._compute_page_range(page, total_pages),
                'query': query_string,
                'sort': sort_by,
                'date_from': date_from or '',
                'date_to': date_to or '',
                'journal': journal or '',
                'facets': facets
            }

    @staticmethod
    def _build_filter_query(date_from, date_to, journal):
        """Build a Whoosh filter query from active filter parameters.

        Returns a combined And query, or None if no filters are active.
        """
        filters = []
        if date_from or date_to:
            filters.append(TermRange("publish_time", date_from, date_to))
        if journal:
            filters.append(Term("journal", journal))
        if not filters:
            return None
        return filters[0] if len(filters) == 1 else And(filters)

    @staticmethod
    def _extract_facets(results, sample_size):
        """Extract journal and year facet counts from the top search results.

        Args:
            results: Whoosh Results object
            sample_size: Number of results to sample for facet counting

        Returns:
            dict with 'journals' (list of {name, count}) and
            'years' (list of {year, count}), both sorted by count descending.
        """
        journal_counts = Counter()
        year_counts = Counter()
        for hit in results[0:sample_size]:
            j = hit.get("journal", "") or ""
            if j and j.lower() not in ("unknown", "nan", ""):
                journal_counts[j] += 1
            pt = hit.get("publish_time", "") or ""
            if len(pt) >= 4 and pt[:4].isdigit():
                year_counts[pt[:4]] += 1
        return {
            "journals": [{"name": n, "count": c} for n, c in journal_counts.most_common(10)],
            "years": [{"year": y, "count": c} for y, c in sorted(year_counts.items(), reverse=True)],
        }

    @staticmethod
    def _compute_page_range(page, total_pages, window=2):
        """Compute page numbers for Google-style pagination with ellipsis gaps.

        Returns a list of ints and None values (None = ellipsis placeholder).
        Example for page 6 of 20: [1, None, 4, 5, 6, 7, 8, None, 20]
        """
        if total_pages <= 1:
            return []
        pages = {1, total_pages}
        for p in range(max(1, page - window), min(total_pages, page + window) + 1):
            pages.add(p)
        sorted_pages = sorted(pages)
        result = []
        for i, p in enumerate(sorted_pages):
            if i > 0 and p - sorted_pages[i - 1] > 1:
                result.append(None)
            result.append(p)
        return result

    @staticmethod
    def _truncate_at_sentence(text, max_length=300):
        """Truncate text at the nearest sentence boundary within max_length.

        Falls back to word boundary if no sentence end is found.
        """
        if len(text) <= max_length:
            return text
        truncated = text[:max_length]
        # Find the last sentence-ending punctuation followed by a space
        last_boundary = -1
        for i in range(len(truncated) - 1, max_length // 3, -1):
            if truncated[i] in '.!?' and (i + 1 >= len(truncated) or truncated[i + 1] == ' '):
                last_boundary = i
                break
        if last_boundary > 0:
            return text[:last_boundary + 1]
        # Fallback: truncate at last word boundary
        last_space = truncated.rfind(' ')
        if last_space > 0:
            return truncated[:last_space] + '...'
        return truncated + '...'

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
    import os

    # Use absolute path relative to script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    index_path = os.path.join(project_root, "index")

    searcher = CORD19Searcher(index_path)

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
