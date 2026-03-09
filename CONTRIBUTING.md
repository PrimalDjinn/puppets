# Contributing to Puppets

Thank you for your interest in contributing to Puppets!

## Development Setup

```bash
# Clone the repository
git clone https://github.com/PrimalDjinn/puppets.git
cd puppets

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=puppets --cov-report=html

# Run specific test file
pytest tests/test_session.py -v

# Run tests matching a pattern
pytest -k "test_session"
```

## Code Style

We use several tools to maintain code quality:

- **Black** - Code formatting
- **mypy** - Type checking
- **pytest** - Testing

```bash
# Format code
black puppets/ tests/

# Type check
mypy puppets/

# Run all checks
pytest && black --check puppets/ && mypy puppets/
```

## Submitting Changes

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes and add tests
4. Ensure all tests pass: `pytest`
5. Format code: `black puppets/ tests/`
6. Commit your changes: `git commit -am 'Add new feature'`
7. Push to the branch: `git push origin feature/my-feature`
8. Create a Pull Request

## Issue Reporting

When reporting issues, please include:

- Python version
- Operating system
- Tor version
- Chrome/Chromium version
- Full error traceback
- Minimal reproduction steps

## Feature Requests

Feature requests are welcome! Please include:

- Clear description of the feature
- Use case / why it's needed
- Potential implementation approach
- Any relevant examples from other libraries

## License

By contributing to Puppets, you agree that your contributions will be licensed under the MIT License.