# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

Collection Importer - A Python CLI tool and MCP Server that converts API client collections (Bruno, Postman, Insomnia) directly to JMeter JMX test plans.

## Common Commands

### Development Setup
```bash
# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Verify installation
collection-importer --version
```

### Testing
```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=collection_importer --cov-report=html

# Run specific test file
pytest tests/core/test_bruno_importer.py -v

# View coverage report
open htmlcov/index.html
```

### Linting and Formatting
```bash
# Check linting
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .

# Type checking
mypy collection_importer/
```

### Running the Tool
```bash
# Analyze project for collections
collection-importer analyze

# Import collection and generate JMX
collection-importer import ./my-collection -o test.jmx

# Import with load test configuration
collection-importer import ./collection --threads 50 --rampup 10 --duration 300

# Preview requests without generating
collection-importer import ./collection --preview

# Import with verbose output (debug information)
collection-importer import ./collection -v

# Start MCP Server
collection-importer mcp
```

## Architecture

### Data Flow
```
Bruno/Postman/Insomnia Collection
           |
           v
    [Format Importer]  (BrunoImporter, PostmanImporter, InsomniaImporter)
           |
           +-- [CorrelationExtractor] extracts bru.setVar/pm.environment.set patterns
           |
           v
    ParsedCollection   (Dataclass with requests, metadata, and correlations)
           |
           v
    [JMXGenerator]     (Creates JMeter XML with JSONPostProcessor for correlations)
           |
           v
    JMeter JMX File
```

### Core Modules (in collection_importer/core/)

1. **data_types.py**: Dataclasses for parsed collection data
   - `CollectionRequest`: Single API request (includes `correlations` field)
   - `CollectionMetadata`: Collection-level metadata
   - `ParsedCollection`: Complete parsed collection

2. **importers/base.py**: Abstract base class for importers
   - `BaseImporter`: ABC with variable conversion helpers

3. **importers/bruno.py**: Bruno collection importer
   - Parses .bru files and bruno.json

4. **importers/postman.py**: Postman collection importer
   - Parses Postman v2.1 JSON format

5. **importers/insomnia.py**: Insomnia collection importer
   - Parses Insomnia v4 JSON export

6. **correlation_extractor.py**: Post-response script parser
   - Extracts `bru.setVar`, `pm.environment.set` patterns
   - Converts JavaScript paths to JSONPath expressions

7. **jmx_generator.py**: JMX file generation
   - Creates JMeter test plans from ParsedCollection
   - Generates JSONPostProcessor for extracted correlations

8. **collection_analyzer.py**: Project discovery
   - Auto-detects collections in project directories

9. **variable_manager.py**: Variable handling utilities
   - Converts {{var}} to ${var} syntax

## Code Standards

### Writing Style
- **No Emojis in Documentation**: Technical documentation must be professional and emoji-free.
- **English Only**: All documentation, code comments, and docstrings in English.
- Exception: Emojis in CLI output for better UX are acceptable.

### Type Hints Required
All public methods must have complete type hints. Use Python 3.11+ style:
```python
def parse_collection(self, path: Path) -> ParsedCollection:
    """Parse collection and return structured data."""
    ...
```

### Docstrings Required
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
- Use custom exception hierarchy (all inherit from CollectionImporterException)
- Provide context in error messages
- Core modules raise exceptions; CLI/MCP layers catch and format them

### Testing Requirements
- Minimum 80% code coverage
- Every core module must have unit tests
- Test error cases and edge cases
- Use fixtures in tests/conftest.py for shared test data

## Key Data Structures

### CollectionRequest
```python
@dataclass
class CollectionRequest:
    name: str                       # Request name
    method: str                     # GET, POST, PUT, DELETE
    path: str                       # /users/${id}
    headers: dict[str, str]         # Request headers
    body: Optional[dict | str]      # Request body
    body_type: str                  # json, form, raw
    auth_type: Optional[str]        # bearer, basic
    auth_value: Optional[str]       # Auth token/credentials
    folder_path: str                # Folder hierarchy
    sequence: int                   # Order in collection
    pre_script: Optional[str]       # Pre-request script
    post_script: Optional[str]      # Post-response script
    correlations: list[dict]        # Extracted correlations for JSONPostProcessor
```

### ParsedCollection
```python
@dataclass
class ParsedCollection:
    metadata: CollectionMetadata    # Name, variables, base_url
    requests: list[CollectionRequest]
```

## Supported Collection Formats

### Bruno (.bru files)
- Folder structure with bruno.json + *.bru files
- Each .bru file is a single request
- Supports: meta, HTTP methods, headers, body:json, auth, scripts

### Postman (v2.1 JSON)
- Single JSON file with nested item[] structure
- Collection variables in variable[] array
- Supports: request, header, body, auth, event scripts

### Insomnia (v4 JSON)
- Single JSON file with resources[] array
- Folder hierarchy via parentId references
- Supports: request, header, body, authentication

## JMX Generation

- **HTTP Request Defaults**: Server config at TestPlan level
- **User Defined Variables**: Collection variables
- **ThreadGroup**: Configurable threads, rampup, duration
- **HTTP Samplers**: One per request
- **Response Assertions**: Validates 2xx success codes using regex pattern

## Variable Conversion

All collection formats use {{variable}} syntax.
The importer converts to JMeter ${variable} syntax automatically.

Example:
- Input: `{{base_url}}/users/{{user_id}}`
- Output: `${base_url}/users/${user_id}`

## Reference Documentation

See `docs/reference/` for detailed specifications:
- `JMX_FORMAT_REFERENCE.md` - JMeter JMX XML structure
- `COLLECTION_FORMATS.md` - Bruno, Postman, Insomnia format specs
