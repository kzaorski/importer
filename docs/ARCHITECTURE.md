# Architecture

This document describes the system architecture of Collection Importer.

## Overview

Collection Importer is a Python tool that converts API collections (Bruno, Postman, Insomnia) to JMeter JMX test plans. It follows a clean architecture with clear separation between interface layers and core business logic.

## System Architecture

```
+------------------+     +------------------+
|       CLI        |     |    MCP Server    |
|   (cli.py)       |     | (mcp_server.py)  |
+--------+---------+     +--------+---------+
         |                        |
         +------------------------+
                    |
         +----------v-----------+
         |     Core Logic       |
         |  (collection_importer/core/)  |
         +----------+-----------+
                    |
    +---------------+---------------+
    |               |               |
+---v---+     +-----v-----+   +-----v-----+
|Importers|   |JMXGenerator|  |Analyzer   |
+---+---+     +-----------+   +-----------+
    |
+---+---+---+---+
|   |   |   |
Bruno Postman Insomnia
```

## Component Responsibilities

### Interface Layer

#### CLI (`cli.py`)
- Command-line interface using Click framework
- Rich console output for user feedback
- Commands: `analyze`, `import`, `mcp`
- Handles user input validation and error display

#### MCP Server (`mcp_server.py`)
- Model Context Protocol server for AI assistant integration
- Exposes 3 tools for programmatic access
- Async implementation using `anyio`
- JSON-based communication

### Core Layer

#### Collection Analyzer (`collection_analyzer.py`)
- Project directory scanning
- Format auto-detection (Bruno, Postman, Insomnia)
- Collection discovery and metadata extraction

#### Importers (`importers/`)
- Abstract base class defining importer interface
- Format-specific implementations:
  - `BrunoImporter`: Parses `.bru` files and `bruno.json`
  - `PostmanImporter`: Parses Postman v2.1 JSON collections
  - `InsomniaImporter`: Parses Insomnia v4 JSON exports

#### JMX Generator (`jmx_generator.py`)
- Converts `ParsedCollection` to JMeter JMX XML
- Creates complete test plan structure
- Handles HTTP Request Defaults pattern
- Generates response assertions

#### Variable Manager (`variable_manager.py`)
- Variable syntax conversion (`{{var}}` -> `${var}`)
- Environment variable handling

#### Data Types (`data_types.py`)
- Core dataclasses: `CollectionRequest`, `CollectionMetadata`, `ParsedCollection`
- Type-safe data transfer between components

## Data Flow

### Import Flow

```
1. User Input (collection path)
        |
        v
2. CollectionAnalyzer.detect_format()
        |
        v
3. FormatImporter.import_collection()
        |
        v
4. ParsedCollection (dataclass)
        |
        v
5. JMXGenerator.generate()
        |
        v
6. JMX File Output
```

### Detailed Data Transformation

```
Bruno Collection:
  bruno.json + *.bru files
        |
        v
  BrunoImporter._parse_bru_file()
        |
        v
  list[CollectionRequest]
        |
        v
  ParsedCollection(metadata, requests)
        |
        v
  JMXGenerator._create_test_plan()
  JMXGenerator._create_http_defaults()
  JMXGenerator._create_thread_group()
  JMXGenerator._create_http_sampler() (per request)
        |
        v
  XML ElementTree
        |
        v
  Formatted JMX file
```

## Key Design Patterns

### 1. Template Method Pattern (Importers)

The `BaseImporter` abstract class defines the skeleton of the import algorithm:

```python
class BaseImporter(ABC):
    @abstractmethod
    def can_import(self, path: Path) -> bool:
        """Check if this importer can handle the given path."""
        pass

    @abstractmethod
    def import_collection(self, path: Path, ...) -> ParsedCollection:
        """Import collection and return parsed data."""
        pass

    def _convert_variables(self, text: str) -> str:
        """Shared variable conversion logic."""
        return self._var_manager.convert_variable_syntax(text)
```

### 2. Strategy Pattern (Format Detection)

`CollectionAnalyzer` uses strategy-like format detection:

```python
def detect_format(self, path: str) -> str:
    p = Path(path)
    if self._is_bruno(p):
        return "bruno"
    elif self._is_postman(p):
        return "postman"
    elif self._is_insomnia(p):
        return "insomnia"
    return "unknown"
```

### 3. Builder Pattern (JMX Generation)

`JMXGenerator` builds complex XML structures step by step:

```python
def generate(self, collection, output_path, ...):
    root = self._create_root()
    test_plan = self._create_test_plan(collection.metadata.name)
    http_defaults = self._create_http_defaults(domain, port, protocol)
    thread_group = self._create_thread_group(...)
    for request in collection.requests:
        sampler = self._create_http_sampler(request)
        # ... build tree
```

### 4. Facade Pattern (CLI/MCP)

CLI and MCP act as facades to core logic:

```python
# CLI simplified interface
@cli.command("import")
def import_collection(collection_path, output, ...):
    importer = BrunoImporter()
    collection = importer.import_collection(path)
    generator = JMXGenerator()
    result = generator.generate(collection, output)
```

## HTTP Request Defaults Pattern

A key architectural decision is using JMeter's HTTP Request Defaults element:

```xml
<ConfigTestElement testname="HTTP Request Defaults">
  <stringProp name="HTTPSampler.domain">api.example.com</stringProp>
  <stringProp name="HTTPSampler.port">80</stringProp>
  <stringProp name="HTTPSampler.protocol">http</stringProp>
</ConfigTestElement>
```

Individual samplers inherit these defaults and only specify path/method:

```xml
<HTTPSamplerProxy testname="GET /users">
  <stringProp name="HTTPSampler.domain"/>  <!-- empty, inherited -->
  <stringProp name="HTTPSampler.path">/users</stringProp>
  <stringProp name="HTTPSampler.method">GET</stringProp>
</HTTPSamplerProxy>
```

Benefits:
- Single point of configuration for server details
- Easy to change base URL without editing each sampler
- Cleaner JMX structure

## Module Dependencies

```
exceptions.py          <-- No dependencies (base module)
     ^
     |
data_types.py         <-- No dependencies
     ^
     |
variable_manager.py   <-- No dependencies
     ^
     |
importers/base.py     <-- data_types, variable_manager, exceptions
     ^
     |
importers/bruno.py    <-- base, data_types
importers/postman.py  <-- base, data_types
importers/insomnia.py <-- base, data_types
     ^
     |
collection_analyzer.py <-- importers, data_types
     ^
     |
jmx_generator.py      <-- data_types, variable_manager, exceptions
     ^
     |
cli.py / mcp_server.py <-- All core modules
```

## Threading Model

### CLI Mode
- Single-threaded synchronous execution
- Sequential processing of requests
- Blocking I/O for file operations
- All core modules run synchronously

### MCP Server Mode
- Async/await pattern using `anyio`
- Non-blocking I/O for stdio communication
- Each tool call is processed asynchronously
- Core modules still run synchronously (wrapped in async handlers)

### Why Two Modes?

**CLI**: Simple, predictable execution. Users expect blocking behavior.

**MCP Server**: Required for Model Context Protocol integration. AI assistants
communicate via stdio which requires async handling to prevent deadlocks.

### Script Handling Note

Pre-request and post-response scripts from collections are parsed and stored
in `CollectionRequest` objects but are **not executed** during JMX generation.
They are preserved for reference only.

## Error Handling Strategy

### Exception Hierarchy

```
CollectionImporterException (base)
    |
    +-- ImportException
    |       Import-related errors
    |
    +-- JMXGenerationException
    |       JMX generation errors
    |
    +-- ValidationException
            Validation errors
```

### Error Flow

1. Core modules raise specific exceptions with context
2. CLI catches and formats for user display (Rich console)
3. MCP Server catches and returns as TextContent error message

## Configuration

### Runtime Configuration

No configuration files required. All options passed via:
- CLI arguments
- MCP tool parameters

### Default Values

| Parameter | Default | Description |
|-----------|---------|-------------|
| threads | 1 | Virtual users |
| rampup | 0 | Ramp-up seconds |
| duration | None | Test duration (loop mode if None) |
| output | test.jmx | Output file path |

## Extension Points

### Adding New Import Format

1. Create new importer class in `importers/`
2. Inherit from `BaseImporter`
3. Implement required abstract methods
4. Register in `CollectionAnalyzer.detect_format()`
5. Add to CLI/MCP tool handlers

### Adding New JMX Elements

1. Add helper method in `JMXGenerator`
2. Follow existing XML building pattern
3. Reference `docs/reference/JMX_FORMAT_REFERENCE.md`

## File Organization

```
collection_importer/
├── __init__.py           # Package init, version
├── cli.py                # Click CLI
├── mcp_server.py         # MCP Server
├── exceptions.py         # Custom exceptions
└── core/
    ├── __init__.py
    ├── data_types.py     # Dataclasses
    ├── variable_manager.py
    ├── collection_analyzer.py
    ├── jmx_generator.py
    └── importers/
        ├── __init__.py
        ├── base.py       # ABC
        ├── bruno.py
        ├── postman.py
        └── insomnia.py
```

## Performance Considerations

- Lazy loading of importers (only instantiate when needed)
- Single-pass parsing of collection files
- XML tree built in memory, written once
- No external API calls or network dependencies

## Security Considerations

- No credential storage
- Variables in JMX use `${var}` syntax (resolved at runtime)
- No code execution from collection scripts (pre/post scripts stored but not executed)
- File paths validated before operations
