# Collection Importer

Convert API collections (Bruno, Postman, Insomnia) to JMeter JMX test plans.

## Features

- **Bruno Support**: Import .bru collections with folders, environments, and scripts
- **Postman Support**: Import v2.1 JSON collections with folders and variables
- **Insomnia Support**: Import v4 JSON exports with folder hierarchy
- **Direct JMX Output**: Generate ready-to-use JMeter test plans
- **Variable Conversion**: Automatic `{{var}}` to `${var}` conversion
- **Automatic Correlation Extraction**: Convert post-response scripts to JSONPostProcessor
- **CLI Interface**: Simple command-line tool
- **MCP Server**: Integration with AI assistants

## Installation

```bash
pip install collection-importer
```

Or install from source:

```bash
pip install -e ".[dev]"
```

## Quick Start

```bash
# Discover collections (with interactive import prompt)
collection-importer analyze

# Import Bruno collection
collection-importer import ./my-collection -o test.jmx

# Import Postman collection
collection-importer import collection.postman_collection.json

# Import Insomnia export
collection-importer import insomnia-export.json

# Preview requests without generating
collection-importer import ./collection --preview

# Import with load test configuration
collection-importer import ./collection --threads 50 --rampup 10 --duration 300
```

## CLI Commands

### analyze

Discover API collections in a project directory.

```bash
collection-importer analyze [--path .]
```

### import

Import a collection and generate JMX file.

```bash
collection-importer import <PATH> [OPTIONS]

Options:
  -o, --output PATH     Output JMX file (default: test.jmx)
  -f, --format FORMAT   Force format: bruno, postman, insomnia
  -e, --env PATH        Environment file path
  --base-url URL        Override base URL
  --threads N           Number of virtual users (default: 1)
  --rampup N            Ramp-up period in seconds (default: 0)
  --duration N          Test duration in seconds
  --preview             List requests without generating
  -v, --verbose         Enable verbose output with debug information
```

### mcp

Start MCP server for AI assistant integration.

```bash
collection-importer mcp
```

## Supported Formats

### Bruno

- Folder structure with `bruno.json` metadata
- `.bru` files for each request
- Environment files in `environments/` folder
- Supports: headers, JSON body, bearer/basic auth, pre/post scripts

### Postman

- JSON collection format v2.1
- Nested folder structure via `item[]`
- Collection variables
- Supports: headers, body, auth, pre-request scripts

### Insomnia

- JSON export format v4
- Folder hierarchy via `parentId` references
- Environment data
- Supports: headers, body, authentication

## Format Support

| Feature | Bruno | Postman | Insomnia |
|---------|-------|---------|----------|
| Format Detection | Yes | Yes | Yes |
| CLI Import | Yes | Yes | Yes |
| MCP Import | Yes | Yes | Yes |
| Environment Files | Yes | Yes | Yes |
| Variable Conversion | Yes | Yes | Yes |

## MCP Server Integration

Configure VS Code for GitHub Copilot:

```json
{
  "github.copilot.chat.mcp.servers": {
    "collection-importer": {
      "command": "collection-importer",
      "args": ["mcp"]
    }
  }
}
```

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `analyze_project_for_collections` | Discover collections in project directory |
| `import_collection_to_jmx` | Import collection and generate JMX |
| `list_collection_requests` | Preview requests without generating |

## Documentation

Detailed documentation is available in the `docs/` folder:

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, data flow, design patterns |
| [CORE_MODULES.md](docs/CORE_MODULES.md) | Detailed module specifications and API reference |
| [DEVELOPMENT.md](docs/DEVELOPMENT.md) | Setup, testing, debugging guide |
| [IMPORTER_GUIDE.md](docs/IMPORTER_GUIDE.md) | How to implement new format importers |

### Reference Materials

| Document | Description |
|----------|-------------|
| [JMX_FORMAT_REFERENCE.md](docs/reference/JMX_FORMAT_REFERENCE.md) | JMeter JMX XML structure |
| [COLLECTION_FORMATS.md](docs/reference/COLLECTION_FORMATS.md) | Bruno, Postman, Insomnia format specs |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=collection_importer --cov-report=html

# Lint code
ruff check .

# Auto-fix lint issues
ruff check --fix .

# Format code
ruff format .

# Type checking
mypy collection_importer/
```

## Project Structure

```
collection_importer/
├── cli.py                  # CLI commands (Click)
├── mcp_server.py           # MCP server for AI assistants
├── exceptions.py           # Custom exceptions
└── core/
    ├── data_types.py       # Dataclasses
    ├── variable_manager.py # Variable conversion
    ├── collection_analyzer.py  # Format detection
    ├── jmx_generator.py    # JMX generation
    └── importers/
        ├── base.py         # Abstract base class
        ├── bruno.py        # Bruno importer
        ├── postman.py      # Postman importer
        └── insomnia.py     # Insomnia importer
```

## License

MIT
