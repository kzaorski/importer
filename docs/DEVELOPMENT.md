# Development Guide

This document covers setup, development workflows, testing, and troubleshooting for Collection Importer.

## Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- Git

## Project Setup

### Clone Repository

```bash
git clone https://github.com/kzaorski/collection-importer.git
cd collection-importer
```

### Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate (Linux/macOS)
source .venv/bin/activate

# Activate (Windows)
.venv\Scripts\activate
```

### Install Dependencies

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Verify installation
collection-importer --version
```

### Install Only Runtime Dependencies

```bash
pip install -e .
```

## Development Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| pytest | >= 7.4.0 | Test framework |
| pytest-cov | >= 4.1.0 | Coverage reporting |
| pytest-asyncio | >= 0.21.0 | Async test support |
| ruff | >= 0.1.0 | Linting and formatting |
| mypy | >= 1.5.0 | Static type checking |

## Project Structure

```
collection-importer/
├── collection_importer/     # Main package
│   ├── __init__.py
│   ├── cli.py               # CLI commands
│   ├── mcp_server.py        # MCP server
│   ├── exceptions.py        # Custom exceptions
│   └── core/                # Core logic
│       ├── data_types.py
│       ├── variable_manager.py
│       ├── collection_analyzer.py
│       ├── jmx_generator.py
│       └── importers/
│           ├── base.py
│           ├── bruno.py
│           ├── postman.py
│           └── insomnia.py
├── tests/                   # Test suite
│   ├── conftest.py          # Test fixtures
│   ├── core/                # Core module tests
│   └── fixtures/            # Test data
│       └── collections/
│           ├── bruno/
│           ├── postman/
│           └── insomnia/
├── docs/                    # Documentation
│   ├── ARCHITECTURE.md
│   ├── CORE_MODULES.md
│   ├── DEVELOPMENT.md
│   └── reference/           # Reference materials
├── pyproject.toml           # Project configuration
├── README.md
└── CLAUDE.md                # AI assistant guide
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run with Verbose Output

```bash
pytest -v
```

### Run Specific Test File

```bash
pytest tests/core/test_bruno_importer.py
```

### Run Specific Test Function

```bash
pytest tests/core/test_bruno_importer.py::test_can_import_bruno_folder -v
```

### Run Tests with Coverage

```bash
# Generate coverage report
pytest --cov=collection_importer --cov-report=html

# View HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Coverage Targets

| Module | Target | Current |
|--------|--------|---------|
| data_types.py | 90% | 100% |
| variable_manager.py | 90% | 98% |
| importers/base.py | 80% | 91% |
| importers/bruno.py | 85% | 88% |
| importers/postman.py | 85% | 78% |
| importers/insomnia.py | 85% | 75% |
| collection_analyzer.py | 80% | 86% |
| jmx_generator.py | 85% | 94% |
| cli.py | 70% | 88% |
| mcp_server.py | 70% | 92% |
| importer_factory.py | 90% | 100% |
| exceptions.py | 90% | 100% |

**Total Coverage: 86%**

### Test Files

```
tests/
├── conftest.py                    # Shared fixtures
├── test_cli.py                    # CLI command tests
├── test_mcp_server.py             # MCP server tests
├── test_integration.py            # Integration tests
├── test_exceptions.py             # Exception tests
└── core/
    ├── test_bruno_importer.py     # Bruno importer tests
    ├── test_postman_importer.py   # Postman importer tests
    ├── test_insomnia_importer.py  # Insomnia importer tests
    ├── test_jmx_generator.py      # JMX generator tests
    ├── test_collection_analyzer.py # Analyzer tests
    ├── test_data_types.py         # Data types tests
    └── test_variable_manager.py   # Variable manager tests
```

**Test Statistics:**
- Total tests: 553
- CLI tests: 29
- MCP server tests: 32
- Integration tests: 14

## Linting and Formatting

### Check for Issues

```bash
# Run linter
ruff check .

# Check specific file
ruff check collection_importer/core/bruno.py
```

### Auto-Fix Issues

```bash
ruff check --fix .
```

### Format Code

```bash
ruff format .
```

### Check Formatting

```bash
ruff format --check .
```

## Type Checking

### Run MyPy

```bash
mypy collection_importer/
```

### Check Specific Module

```bash
mypy collection_importer/core/jmx_generator.py
```

### MyPy Configuration

Type checking is configured in `pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_ignores = true
disallow_untyped_defs = true
strict = true
```

## Test Fixtures

### Location

Test fixtures are in `tests/fixtures/collections/`:

```
tests/fixtures/collections/
├── bruno/
│   ├── bruno.json           # Collection manifest
│   ├── get-users.bru        # GET request
│   └── create-user.bru      # POST request
├── postman/
│   └── collection.json      # Postman v2.1 collection
└── insomnia/
    └── export.json          # Insomnia v4 export
```

### Using Fixtures

```python
import pytest
from pathlib import Path

def test_bruno_import(bruno_collection_dir: Path):
    """Test using bruno fixture."""
    importer = BrunoImporter()
    collection = importer.import_collection(bruno_collection_dir)
    assert collection.request_count == 2
```

### Available Fixtures

| Fixture | Type | Description |
|---------|------|-------------|
| `fixtures_dir` | Path | Root fixtures directory |
| `bruno_collection_dir` | Path | Bruno collection folder |
| `postman_collection_file` | Path | Postman JSON file |
| `insomnia_collection_file` | Path | Insomnia JSON file |
| `sample_parsed_request` | dict | Sample request data |
| `sample_collection_metadata` | dict | Sample metadata |

### Creating New Fixtures

1. Add test files to appropriate `tests/fixtures/collections/` subdirectory
2. Create fixture in `tests/conftest.py`:

```python
@pytest.fixture
def my_fixture() -> Path:
    """Return path to my test fixture."""
    return COLLECTIONS_DIR / "my_fixture"
```

## CLI Testing

### Manual Testing

```bash
# Test analyze command
collection-importer analyze --path ./tests/fixtures/collections/bruno

# Test import command (preview mode)
collection-importer import ./tests/fixtures/collections/bruno --preview

# Test import command (generate JMX)
collection-importer import ./tests/fixtures/collections/bruno -o /tmp/test.jmx

# Test MCP server
collection-importer mcp
```

### CLI Test Patterns

```python
from click.testing import CliRunner
from collection_importer.cli import cli

def test_analyze_command():
    """Test analyze CLI command."""
    runner = CliRunner()
    result = runner.invoke(cli, ['analyze', '--path', './tests/fixtures/collections/bruno'])
    assert result.exit_code == 0
    assert 'bruno' in result.output.lower()
```

## MCP Server Testing

### Test with MCP Inspector

```bash
# Install MCP Inspector (if available)
npx @anthropic/mcp-inspector

# Run server
collection-importer mcp
```

### Async Test Patterns

```python
import pytest
from collection_importer.mcp_server import call_tool

@pytest.mark.asyncio
async def test_analyze_tool():
    """Test analyze MCP tool."""
    result = await call_tool(
        "analyze_project_for_collections",
        {"project_path": "./tests/fixtures/collections/bruno"}
    )
    assert len(result) > 0
    assert "bruno" in result[0].text.lower()
```

## Debugging

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Debug Import Issues

```python
from collection_importer.core.importers.bruno import BrunoImporter

importer = BrunoImporter()

# Check detection
print(importer.can_import(Path("./collection")))

# Preview requests
requests = importer.list_requests(Path("./collection"))
for req in requests:
    print(f"{req['method']} {req['path']} - {req['name']}")
```

### Debug JMX Generation

```python
from collection_importer.core.jmx_generator import JMXGenerator

generator = JMXGenerator()

# Generate JMX
result = generator.generate(collection, "/tmp/debug.jmx")
print(f"Samplers created: {result['samplers_created']}")
print(f"Output path: {result['jmx_path']}")
```

### Inspect JMX Structure

```python
import xml.etree.ElementTree as ET

tree = ET.parse("/tmp/debug.jmx")
root = tree.getroot()

# List all elements
for elem in root.iter():
    print(f"{elem.tag}: {elem.get('testname', '')}")
```

## Common Issues

### Import Not Working

**Symptom:** `can_import()` returns False

**Solutions:**
1. Check file exists: `Path(path).exists()`
2. For Bruno: verify `bruno.json` or `*.bru` files exist
3. Check file permissions

### Variable Conversion Issues

**Symptom:** `{{var}}` not converted to `${var}`

**Solutions:**
```python
from collection_importer.core.variable_manager import VariableManager

vm = VariableManager()
result = vm.convert_variable_syntax("{{base_url}}/users")
print(result)  # Should be: ${base_url}/users
```

### JMX Generation Issues

**Symptom:** Generated JMX doesn't work in JMeter

**Solutions:**
1. Open in JMeter GUI to see errors
2. Check XML structure is well-formed
3. Verify all required elements are present (TestPlan, ThreadGroup, HTTP Samplers)

### MCP Server Connection Issues

**Symptom:** MCP client cannot connect

**Solutions:**
1. Verify server starts: `collection-importer mcp`
2. Check stdio communication
3. Verify MCP SDK version compatibility

## Code Style Guidelines

### Imports

```python
# Standard library
from pathlib import Path
from typing import Any, Optional

# Third-party
import click
from rich.console import Console

# Local
from collection_importer.core.data_types import ParsedCollection
from collection_importer.exceptions import ImportException
```

### Type Hints

All public functions must have type hints:

```python
def import_collection(
    self,
    path: Path,
    env_path: Optional[Path] = None,
    name: Optional[str] = None,
    base_url: Optional[str] = None,
) -> ParsedCollection:
    """Import collection."""
```

### Docstrings

Use Google-style docstrings:

```python
def generate(self, collection: ParsedCollection, output_path: str) -> dict[str, Any]:
    """Generate JMeter JMX file from parsed collection.

    Args:
        collection: Parsed collection data.
        output_path: Path where to save JMX file.

    Returns:
        Generation result with keys: success, jmx_path, samplers_created.

    Raises:
        JMXGenerationException: If generation fails.
    """
```

### Error Handling

```python
from collection_importer.exceptions import ImportException

try:
    # Operation
except SomeError as e:
    raise ImportException(
        "Failed to import collection",
        details=str(e),
    )
```

## Contributing

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation
- `refactor/description` - Code refactoring

### Commit Messages

```
type: short description

Longer description if needed.

Closes #123
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

### Pull Request Checklist

- [ ] Tests pass: `pytest`
- [ ] Linting passes: `ruff check .`
- [ ] Type checking passes: `mypy collection_importer/`
- [ ] Documentation updated
- [ ] Coverage maintained or improved
