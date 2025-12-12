# Contributing to Collection Importer

Thank you for your interest in contributing to Collection Importer! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and constructive in all interactions. We welcome contributors of all experience levels.

## Getting Started

### Development Setup

1. Clone the repository:
```bash
git clone https://github.com/your-org/collection-importer.git
cd collection-importer
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install in development mode:
```bash
pip install -e ".[dev]"
```

4. Verify the installation:
```bash
collection-importer --version
pytest
```

## Development Workflow

### Branching Strategy

- `main` - Stable release branch
- `develop` - Integration branch for features
- `feature/*` - New features
- `fix/*` - Bug fixes
- `docs/*` - Documentation updates

### Making Changes

1. Create a feature branch from `develop`:
```bash
git checkout develop
git pull origin develop
git checkout -b feature/my-new-feature
```

2. Make your changes following our [code style guidelines](#code-style)

3. Write tests for new functionality

4. Run the test suite:
```bash
pytest --cov=collection_importer
```

5. Ensure code quality:
```bash
ruff check .
ruff format .
mypy collection_importer/
```

6. Commit your changes:
```bash
git add .
git commit -m "feat: add my new feature"
```

### Commit Message Format

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, no logic changes)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

Examples:
```
feat: add OAuth 2.0 authentication support
fix: handle empty request body in Bruno importer
docs: update JMX format reference
test: add unit tests for variable_manager
```

## Code Style

### Python Standards

- **Python Version**: 3.11+ required
- **Formatter**: Ruff (replaces Black)
- **Linter**: Ruff
- **Type Checker**: mypy with strict mode

### Type Hints

All public methods must have complete type hints:

```python
def parse_collection(self, path: Path) -> ParsedCollection:
    """Parse collection and return structured data."""
    ...
```

### Docstrings

Use Google-style docstrings for all public methods:

```python
def generate(
    self,
    collection: ParsedCollection,
    output_path: str,
    threads: int = 1,
) -> dict:
    """Generate JMeter JMX file from parsed collection.

    Args:
        collection: Parsed collection data.
        output_path: Path where to save JMX file.
        threads: Number of virtual users (default: 1).

    Returns:
        Generation result with success status and metadata.

    Raises:
        JMXGenerationException: If generation fails.
    """
```

### Error Handling

- Use custom exception hierarchy (all inherit from `CollectionImporterException`)
- Provide context in error messages
- Core modules raise exceptions; CLI/MCP layers catch and format them

### Testing Requirements

- **Minimum coverage**: 80% for all core modules
- Write tests for new functionality
- Include edge cases and error scenarios
- Use fixtures in `tests/conftest.py` for shared test data

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=collection_importer --cov-report=html

# Run specific test file
pytest tests/core/test_bruno_importer.py -v

# Run specific test class
pytest tests/core/test_jmx_generator.py::TestJMXGeneratorValidation -v

# Run with verbose output
pytest -v --tb=short
```

### Writing Tests

Follow the existing test structure:

```python
class TestMyNewFeature:
    """Tests for my new feature."""

    @pytest.fixture
    def my_fixture(self) -> MyClass:
        """Create instance for testing."""
        return MyClass()

    def test_basic_functionality(self, my_fixture: MyClass) -> None:
        """Test basic functionality works correctly."""
        result = my_fixture.do_something()
        assert result == expected_value

    def test_error_handling(self, my_fixture: MyClass) -> None:
        """Test error handling."""
        with pytest.raises(MyException, match="expected message"):
            my_fixture.do_something_invalid()
```

## Pull Request Process

1. Ensure all tests pass
2. Update documentation if needed
3. Add entry to CHANGELOG.md (if applicable)
4. Create a pull request to `develop` branch
5. Fill out the PR template
6. Wait for code review

### PR Template

```markdown
## Summary
Brief description of changes.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring

## Testing
- [ ] All existing tests pass
- [ ] New tests added for new functionality
- [ ] Coverage maintained at 80%+

## Checklist
- [ ] Code follows project style guidelines
- [ ] Type hints added for new code
- [ ] Docstrings added for new public methods
- [ ] CHANGELOG.md updated (if applicable)
```

## Adding New Features

### Adding a New Importer

1. Create a new importer in `collection_importer/core/importers/`:

```python
from collection_importer.core.importers.base import BaseImporter

class MyImporter(BaseImporter):
    """Importer for My Format collections."""

    format_name = "myformat"

    def import_collection(
        self,
        path: Path,
        env_path: Optional[Path] = None,
        base_url: Optional[str] = None,
    ) -> ParsedCollection:
        # Implementation
        ...

    def list_requests(self, path: Path) -> list[dict]:
        # Implementation
        ...
```

2. Register the importer in `collection_analyzer.py`
3. Add format detection logic
4. Write comprehensive tests

### Adding JMX Elements

1. Add a creation method to `JMXGenerator`:

```python
def _create_my_element(self, param1: str, param2: int) -> ET.Element:
    """Create MyElement for specific purpose.

    Args:
        param1: Description of param1.
        param2: Description of param2.

    Returns:
        MyElement XML element.
    """
    element = ET.Element(
        "MyElement",
        {
            "guiclass": "MyElementGui",
            "testclass": "MyElement",
            "testname": "My Element Name",
            "enabled": "true",
        },
    )
    # Add child elements
    return element
```

2. Integrate into the `generate()` method
3. Add unit tests

## Documentation

### Documentation Standards

- **No Emojis**: Technical documentation must be professional and emoji-free
- **English Only**: All documentation in English
- **Keep Updated**: Update docs when changing functionality

### Documentation Files

- `README.md` - Project overview and quick start
- `QUICKSTART.md` - Detailed getting started guide
- `ARCHITECTURE.md` - System architecture and design
- `docs/reference/` - Format specifications and references
- `CHANGELOG.md` - Version history
- `CONTRIBUTING.md` - This file

## Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create a release PR to `main`
4. After merge, create a GitHub release
5. CI/CD will publish to PyPI

## Getting Help

- Open an issue for bugs or feature requests
- Check existing issues before creating new ones
- Provide detailed reproduction steps for bugs

## License

By contributing, you agree that your contributions will be licensed under the project's MIT License.
