"""
app.py
Flask web application providing the search interface.

This is the PRESENTATION LAYER of your search engine.
"""

import os
import sys
from flask import Flask, render_template, request
from whoosh.index import EmptyIndexError

# Add src directory to path for robust imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from searcher import CORD19Searcher

app = Flask(__name__, template_folder='../templates', static_folder='../static')

# Try to initialise the searcher (loads the index)
searcher = None
index_path = os.path.join(os.path.dirname(__file__), '..', 'index')

try:
    if os.path.exists(index_path) and os.listdir(index_path):
        searcher = CORD19Searcher(index_path)
except (EmptyIndexError, Exception) as e:
    print(f"Warning: Could not load search index: {e}")
    searcher = None

@app.route('/')
def home():
    """
    Home page with search box.
    """
    if searcher is None:
        return render_template('setup.html')

    stats = searcher.get_index_stats()
    return render_template('search.html', stats=stats)

@app.route('/search')
def search():
    """
    Search results page.

    Query parameters:
        q: Search query string
        page: Page number (default: 1)
        sort: Sort order — relevance, date_desc, date_asc (default: relevance)
        date_from: Start date filter (YYYY-MM-DD)
        date_to: End date filter (YYYY-MM-DD)
        journal: Exact journal name filter
    """
    if searcher is None:
        return render_template('setup.html')

    query = request.args.get('q', '').strip()
    page = max(1, request.args.get('page', 1, type=int))
    sort = request.args.get('sort', 'relevance')
    date_from = request.args.get('date_from', '').strip() or None
    date_to = request.args.get('date_to', '').strip() or None
    journal = request.args.get('journal', '').strip() or None

    if not query:
        return render_template('search.html', stats=searcher.get_index_stats())

    # Execute search with error handling for malformed queries
    try:
        results = searcher.search(query, page=page, results_per_page=10,
                                  sort_by=sort, date_from=date_from,
                                  date_to=date_to, journal=journal)
    except Exception:
        return render_template('results.html', results=[], total=0, page=1,
                               total_pages=0, query=query, sort='relevance',
                               date_from='', date_to='', journal='',
                               facets={'journals': [], 'years': []})

    return render_template('results.html', **results)

@app.route('/about')
def about():
    """
    About page explaining the search engine (optional but nice to have).
    """
    return render_template('about.html')

if __name__ == '__main__':
    app.run(debug=False, port=5000)
