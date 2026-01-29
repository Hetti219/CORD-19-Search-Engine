"""
app.py
Flask web application providing the search interface.

This is the PRESENTATION LAYER of your search engine.
"""

from flask import Flask, render_template, request
from searcher import CORD19Searcher

app = Flask(__name__, template_folder='../templates', static_folder='../static')

# Initialise the searcher (loads the index)
searcher = CORD19Searcher("../index")

@app.route('/')
def home():
    """
    Home page with search box.
    """
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
