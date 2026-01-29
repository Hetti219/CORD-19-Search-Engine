"""
app.py
Flask web application providing the search interface.

This is the PRESENTATION LAYER of your search engine.
"""

import os
from flask import Flask, render_template, request
from searcher import CORD19Searcher
from whoosh.index import EmptyIndexError

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
    """
    if searcher is None:
        return render_template('setup.html')

    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)

    if not query:
        return render_template('search.html', stats=searcher.get_index_stats())

    # Execute search
    results = searcher.search(query, page=page, results_per_page=10)

    return render_template('results.html', **results)

@app.route('/about')
def about():
    """
    About page explaining the search engine (optional but nice to have).
    """
    return render_template('about.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
