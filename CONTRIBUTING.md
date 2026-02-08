# Contributing to CORD-19 Search Engine

Thank you for your interest in contributing to this project! This is an academic project, but we welcome improvements and suggestions.

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/cord19_search_engine.git
   cd cord19_search_engine
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # For development tools
   ```

4. **Download the dataset**
   ```bash
   cd data/raw
   wget https://ai2-semanticscholar-cord-19.s3-us-west-2.amazonaws.com/2022-06-02/metadata.csv
   cd ../..
   ```

5. **Build the search index**
   ```bash
   python src/preprocessor.py
   python src/indexer.py
   ```

## Code Quality Standards

This project uses automated CI/CD checks. Before submitting a pull request:

### 1. Code Formatting
```bash
# Check formatting
black --check --line-length=120 src/

# Auto-format code
black --line-length=120 src/
```

### 2. Linting
```bash
# Run flake8
flake8 src/ --max-line-length=120 --max-complexity=10

# Run pylint
pylint src/ --max-line-length=120
```

### 3. Import Tests
Ensure all modules can be imported without errors:
```bash
python -c "from src.preprocessor import preprocess_cord19"
python -c "from src.indexer import build_search_index"
python -c "from src.searcher import CORD19Searcher"
python -c "from src.app import app"
```

### 4. Security Check
```bash
safety check
```

## Submitting Changes

1. **Fork the repository** and create a new branch
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the code quality standards

3. **Test your changes**
   - Ensure all imports work
   - Test the search functionality
   - Verify the Flask app runs

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: Add your feature description"
   ```

5. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request** on GitHub

## Commit Message Format

Follow conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `perf:` Performance improvements
- `test:` Adding tests
- `chore:` Maintenance tasks

## Areas for Contribution

### High Priority
- [ ] Additional unit tests for preprocessor, indexer, and searcher
- [ ] Performance benchmarking suite
- [ ] Query suggestion/autocomplete
- [ ] Export search results to CSV/JSON

### Medium Priority
- [ ] Advanced search filters (date range, journal, author)
- [ ] Search result highlighting
- [ ] Better error handling and user feedback
- [ ] API documentation

### Nice to Have
- [ ] Docker containerization
- [ ] Alternative ranking algorithms (TF-IDF, etc.)
- [ ] Search analytics dashboard
- [ ] Multi-language support

## Questions?

For questions or discussions, please open an issue on GitHub.

## Academic Integrity

This is an academic project. If you're a student working on a similar assignment:
- Use this as a **reference** and learning resource
- Do not copy code directly
- Understand the concepts and implement your own solution
- Cite this project if it influenced your work

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
