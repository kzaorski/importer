# Core Modules Specification

This document provides detailed specifications for all core modules in Collection Importer.

## Table of Contents

1. [Data Types](#data-types)
2. [Variable Manager](#variable-manager)
3. [Correlation Extractor](#correlation-extractor)
4. [Base Importer](#base-importer)
5. [Bruno Importer](#bruno-importer)
6. [Postman Importer](#postman-importer)
7. [Insomnia Importer](#insomnia-importer)
8. [Collection Analyzer](#collection-analyzer)
9. [JMX Generator](#jmx-generator)
10. [Exceptions](#exceptions)

---

## Data Types

**Module:** `collection_importer/core/data_types.py`

Core dataclasses that define the unified data structures used throughout the application.

### CollectionRequest

Represents a single API request parsed from a collection.

```python
@dataclass
class CollectionRequest:
    name: str                    # Human-readable request name
    method: str                  # HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
    path: str                    # Request path (e.g., /users/${id})
    headers: dict[str, str]      # Request headers
    body: Optional[dict | str]   # Request body (dict for JSON, str for raw)
    body_type: str               # Body type: json, form, raw, none
    auth_type: Optional[str]     # Auth type: bearer, basic, apikey, None
    auth_value: Optional[str]    # Auth credentials
    folder_path: str             # Folder hierarchy (e.g., "auth/users")
    sequence: int                # Order in collection (0-based)
    pre_script: Optional[str]    # Pre-request script
    post_script: Optional[str]   # Post-response script
    correlations: list[dict]     # Extracted correlations for JSONPostProcessor
```

**Properties:**
- `full_name` - Returns `folder_path/name` or just `name`
- `has_body` - Returns `True` if body is present and body_type != "none"

**Post-init validation:**
- Method normalized to uppercase
- Invalid methods raise `ValueError`
- Path ensured to start with `/`

### CollectionMetadata

Metadata about the collection.

```python
@dataclass
class CollectionMetadata:
    name: str                        # Collection name
    description: str = ""            # Collection description
    base_url: Optional[str] = None   # Default base URL
    variables: dict[str, str]        # Collection-level variables
    format: str = "unknown"          # Source format (bruno, postman, insomnia)
    source_path: str = ""            # Path to original collection
```

### ParsedCollection

Complete parsed collection combining metadata and requests.

```python
@dataclass
class ParsedCollection:
    metadata: CollectionMetadata
    requests: list[CollectionRequest]
```

**Properties:**
- `request_count` - Returns length of requests list

**Methods:**
- `get_requests_by_folder()` - Groups requests by folder_path
- `get_all_variables()` - Extracts all `${var}` variable names from paths, headers, bodies

---

## Variable Manager

**Module:** `collection_importer/core/variable_manager.py`

Handles variable syntax conversion between collection formats and JMeter.

### VariableManager Class

```python
class VariableManager:
    DOUBLE_BRACE_PATTERN = re.compile(r"\{\{(\w+)\}\}")
    DOLLAR_BRACE_PATTERN = re.compile(r"\$\{(\w+)\}")
    SENSITIVE_PATTERNS = ("token", "secret", "password", "key", "auth", ...)
```

### Methods

#### convert_variable_syntax

```python
def convert_variable_syntax(self, text: str) -> str:
    """Convert {{var}} to ${var} syntax.

    Example:
        "{{base_url}}/users/{{id}}" -> "${base_url}/users/${id}"
    """
```

#### convert_payload_variables

```python
def convert_payload_variables(self, payload: dict | list | str) -> dict | list | str:
    """Recursively convert variables in a payload structure.

    Handles nested dicts and lists.

    Example:
        {"user": "{{username}}"} -> {"user": "${username}"}
    """
```

#### extract_variables

```python
def extract_variables(self, text: str) -> set[str]:
    """Extract variable names from text.

    Finds both {{var}} and ${var} patterns.

    Example:
        "{{base_url}}/users/${id}" -> {'base_url', 'id'}
    """
```

#### extract_path_from_url

```python
def extract_path_from_url(self, url: str) -> str:
    """Extract path portion from URL, preserving variables.

    Removes protocol, host, and variable prefixes.

    Example:
        "https://api.example.com/users/123" -> "/users/123"
        "{{base_url}}/users/{{id}}" -> "/users/${id}"
    """
```

#### extract_base_url

```python
def extract_base_url(self, url: str) -> str | None:
    """Extract base URL (protocol + host) from full URL.

    Example:
        "https://api.example.com/users" -> "https://api.example.com"
    """
```

#### is_sensitive_variable

```python
def is_sensitive_variable(self, name: str) -> bool:
    """Check if variable name suggests sensitive data.

    Example:
        "auth_token" -> True
        "user_id" -> False
    """
```

### Convenience Functions

```python
# Module-level functions using singleton instance
convert_variables(text: str) -> str
convert_payload(payload: Any) -> Any
```

---

## Correlation Extractor

**Module:** `collection_importer/core/correlation_extractor.py`

Extracts variable capture patterns from post-response scripts and converts them to JMeter-compatible JSONPath expressions.

### ExtractedCorrelation Dataclass

```python
@dataclass
class ExtractedCorrelation:
    variable_name: str      # Variable name to store the value (e.g., "user_id")
    json_path: str          # JSONPath expression (e.g., "$.id")
    source_format: str      # Source format: bruno, postman, insomnia
```

### CorrelationExtractor Class

```python
class CorrelationExtractor:
    # Bruno: bru.setVar('name', data.path) or bru.setVar('name', res.body.path)
    BRUNO_PATTERN = re.compile(...)

    # Postman: pm.environment.set('name', jsonData.path) or pm.globals.set(...)
    POSTMAN_PATTERN = re.compile(...)

    # Insomnia: insomnia.setEnvironmentVariable('name', data.path)
    INSOMNIA_PATTERN = re.compile(...)
```

### Methods

#### extract_correlations

```python
def extract_correlations(
    self, script: Optional[str], source_format: str
) -> list[ExtractedCorrelation]:
    """Extract correlations from a post-response script.

    Args:
        script: Post-response script content.
        source_format: Source format (bruno, postman, insomnia).

    Returns:
        List of extracted correlations.
    """
```

#### _convert_to_jsonpath

```python
def _convert_to_jsonpath(self, js_path: str) -> Optional[str]:
    """Convert JavaScript property access to JSONPath.

    Examples:
        data.id          -> $.id
        data.user.name   -> $.user.name
        data.items[0].id -> $.items[0].id
    """
```

#### has_complex_logic

```python
def has_complex_logic(self, script: Optional[str]) -> bool:
    """Check if script contains complex logic that can't be converted.

    Returns True for:
    - if/else statements
    - for/while loops
    - switch statements
    - Array methods (.map, .filter, .reduce, .forEach)
    - try/catch blocks
    """
```

### Supported Patterns

| Format | Pattern | Example |
|--------|---------|---------|
| Bruno | `bru.setVar('name', data.path)` | `bru.setVar('id', data.user.id)` |
| Bruno | `bru.setVar('name', res.body.path)` | `bru.setVar('token', res.body.auth.token)` |
| Postman | `pm.environment.set('name', jsonData.path)` | `pm.environment.set('id', jsonData.user.id)` |
| Postman | `pm.globals.set('name', jsonData.path)` | `pm.globals.set('token', jsonData.auth.token)` |
| Postman | `pm.collectionVariables.set('name', data.path)` | `pm.collectionVariables.set('key', data.api_key)` |
| Insomnia | `insomnia.setEnvironmentVariable('name', data.path)` | `insomnia.setEnvironmentVariable('id', data.id)` |

### JSONPath Conversion

| JavaScript Path | JSONPath |
|-----------------|----------|
| `data.id` | `$.id` |
| `data.user.name` | `$.user.name` |
| `data.items[0].id` | `$.items[0].id` |
| `data.results[0].nested.value` | `$.results[0].nested.value` |

### Limitations

The extractor cannot convert:
- Scripts with conditional logic (if/else)
- Dynamic property access (data[variable])
- Function calls (data.items.map(...))
- Complex transformations

In such cases, the JSR223 PostProcessor is preserved with the original script.

---

## Base Importer

**Module:** `collection_importer/core/importers/base.py`

Abstract base class for all collection importers.

### BaseImporter Class

```python
class BaseImporter(ABC):
    def __init__(self) -> None:
        self._var_manager = VariableManager()
```

### Abstract Methods (must be implemented)

#### format_name

```python
@property
@abstractmethod
def format_name(self) -> str:
    """Return format name: 'bruno', 'postman', or 'insomnia'."""
```

#### can_import

```python
@abstractmethod
def can_import(self, path: Path) -> bool:
    """Check if this importer can handle the given path."""
```

#### import_collection

```python
@abstractmethod
def import_collection(
    self,
    path: Path,
    env_path: Optional[Path] = None,
    name: Optional[str] = None,
    base_url: Optional[str] = None,
) -> ParsedCollection:
    """Import collection and return ParsedCollection.

    Args:
        path: Path to collection file or folder
        env_path: Optional environment file
        name: Override collection name
        base_url: Override base URL

    Raises:
        ImportException: If import fails
    """
```

#### list_requests

```python
@abstractmethod
def list_requests(self, path: Path) -> list[dict[str, str]]:
    """List requests without full import (preview mode).

    Returns:
        List of dicts with keys: name, method, path
    """
```

### Helper Methods (inherited)

#### _convert_variables

```python
def _convert_variables(self, text: str) -> str:
    """Convert {{var}} to ${var}."""
```

#### _convert_payload

```python
def _convert_payload(self, payload: dict | list | str) -> dict | list | str:
    """Recursively convert variables in payload."""
```

#### _extract_path

```python
def _extract_path(self, url: str) -> str:
    """Extract path from URL with variable conversion."""
```

#### _build_request

```python
def _build_request(
    self,
    name: str,
    method: str,
    url: str,
    headers: Optional[dict[str, str]] = None,
    body: Optional[dict | str] = None,
    body_type: str = "none",
    auth_type: Optional[str] = None,
    auth_value: Optional[str] = None,
    folder_path: str = "",
    sequence: int = 0,
    pre_script: Optional[str] = None,
    post_script: Optional[str] = None,
    correlations: Optional[list[dict[str, str]]] = None,
) -> CollectionRequest:
    """Build CollectionRequest with automatic variable conversion.

    The correlations parameter contains extracted variable correlations
    from post-response scripts, used to generate JSONPostProcessor elements.
    """
```

#### _build_metadata

```python
def _build_metadata(
    self,
    name: str,
    source_path: str,
    description: str = "",
    base_url: Optional[str] = None,
    variables: Optional[dict[str, str]] = None,
) -> CollectionMetadata:
    """Build CollectionMetadata with variable conversion."""
```

---

## Bruno Importer

**Module:** `collection_importer/core/importers/bruno.py`

Imports Bruno collections (.bru files).

### BrunoImporter Class

```python
class BrunoImporter(BaseImporter):
    HTTP_METHODS = ("get", "post", "put", "patch", "delete", "head", "options")
```

### Bruno File Format

Bruno uses `.bru` files with block-based syntax:

```bru
meta {
  name: Request Name
  type: http
  seq: 1
}

get {
  url: {{base_url}}/users
  body: none
}

headers {
  Content-Type: application/json
  Authorization: Bearer {{token}}
}

body:json {
  {
    "name": "{{user_name}}"
  }
}

auth:bearer {
  token: {{access_token}}
}

script:pre-request {
  // JavaScript code
}

script:post-response {
  // JavaScript code
}
```

### Methods

#### can_import

```python
def can_import(self, path: Path) -> bool:
    """Check for Bruno collection markers.

    Returns True if:
    - Directory contains bruno.json
    - Directory contains *.bru files
    - Path is a .bru file
    """
```

#### import_collection

```python
def import_collection(
    self,
    path: Path,
    env_path: Optional[Path] = None,
    name: Optional[str] = None,
    base_url: Optional[str] = None,
) -> ParsedCollection:
    """Import Bruno collection.

    Steps:
    1. Read bruno.json for collection metadata
    2. Find all .bru files (recursive)
    3. Parse each .bru file
    4. Sort by sequence number
    5. Apply base_url override if provided
    """
```

#### list_requests

```python
def list_requests(self, path: Path) -> list[dict[str, str]]:
    """Preview requests in Bruno collection.

    Returns list of:
    {
        "name": "Request Name",
        "method": "GET",
        "path": "/users"
    }
    """
```

### Internal Methods

#### _parse_bru_file

```python
def _parse_bru_file(self, content: str) -> dict:
    """Parse .bru file content.

    Returns:
    {
        "meta": {"name": str, "type": str, "seq": int},
        "method": str,
        "url": str,
        "body_type": str,
        "headers": dict,
        "body": str | None,
        "auth": {"type": str, "value": str} | None,
        "scripts": {"pre": str, "post": str}
    }
    """
```

#### _extract_block

```python
def _extract_block(self, content: str, block_name: str) -> str | None:
    """Extract content from named block.

    Handles nested braces in JSON bodies.
    """
```

#### _parse_key_value_block

```python
def _parse_key_value_block(self, block: str) -> dict[str, str]:
    """Parse block with key: value format.

    Example:
        "name: Test\ntype: http" -> {"name": "Test", "type": "http"}
    """
```

---

## Postman Importer

**Module:** `collection_importer/core/importers/postman.py`

Imports Postman v2.1 collections. **Status: Fully Implemented**

### Postman Collection Format

Postman uses JSON with nested `item` arrays:

```json
{
  "info": {
    "name": "Collection Name",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Request Name",
      "request": {
        "method": "GET",
        "header": [...],
        "url": {
          "raw": "{{base_url}}/users",
          "host": ["{{base_url}}"],
          "path": ["users"]
        }
      }
    }
  ],
  "variable": [
    {"key": "base_url", "value": "https://api.example.com"}
  ]
}
```

### PostmanImporter Class

```python
class PostmanImporter(BaseImporter):
    AUTH_BEARER = "bearer"
    AUTH_BASIC = "basic"
    AUTH_APIKEY = "apikey"

    BODY_MODE_RAW = "raw"
    BODY_MODE_FORMDATA = "formdata"
    BODY_MODE_URLENCODED = "urlencoded"
```

### Key Methods

#### import_collection

```python
def import_collection(
    self,
    path: Path,
    env_path: Optional[Path] = None,
    name: Optional[str] = None,
    base_url: Optional[str] = None,
) -> ParsedCollection:
    """Import Postman v2.1 collection.

    Args:
        path: Path to Postman collection JSON file.
        env_path: Optional path to environment file.
        name: Optional override for collection name.
        base_url: Optional override for base URL.

    Returns:
        ParsedCollection with parsed requests.
    """
```

#### list_requests

```python
def list_requests(self, path: Path) -> list[dict[str, str]]:
    """List requests in Postman collection (preview mode).

    Returns list of dicts with name, method, path keys.
    Includes folder prefix in request names.
    """
```

### Implementation Details

1. Parse JSON with `info` and `item[]` validation
2. Recursively process `item[]` array (folders have nested `item[]`, requests have `request` field)
3. Extract collection variables from `variable[]` array
4. Handle URL as object (`raw` field) or string
5. Parse body by `mode`: raw, formdata, urlencoded
6. Handle authentication: bearer, basic, apikey
7. Convert `{{var}}` to `${var}` using inherited methods
8. Preserve item order from JSON array

### Helper Methods

| Method | Description |
|--------|-------------|
| `_parse_collection()` | Parse and validate JSON |
| `_process_items()` | Recursively process item array |
| `_parse_request()` | Parse single request object |
| `_parse_url()` | Handle URL object or string |
| `_parse_headers()` | Convert header array to dict |
| `_parse_body()` | Handle body modes |
| `_parse_auth()` | Handle auth types |
| `_extract_variables()` | Get collection variables |

---

## Insomnia Importer

**Module:** `collection_importer/core/importers/insomnia.py`

Imports Insomnia v4 exports. **Status: Fully Implemented**

### Insomnia Export Format

Insomnia uses flat `resources` array with parent references:

```json
{
  "_type": "export",
  "__export_format": 4,
  "resources": [
    {
      "_id": "wrk_123",
      "_type": "workspace",
      "name": "Collection Name"
    },
    {
      "_id": "fld_456",
      "_type": "request_group",
      "name": "Folder",
      "parentId": "wrk_123"
    },
    {
      "_id": "req_789",
      "_type": "request",
      "name": "GET Users",
      "method": "GET",
      "url": "{{ base_url }}/users",
      "parentId": "fld_456"
    }
  ]
}
```

### InsomniaImporter Class

```python
class InsomniaImporter(BaseImporter):
    TYPE_WORKSPACE = "workspace"
    TYPE_REQUEST_GROUP = "request_group"
    TYPE_REQUEST = "request"
    TYPE_ENVIRONMENT = "environment"

    AUTH_BEARER = "bearer"
    AUTH_BASIC = "basic"
```

### Key Methods

#### import_collection

```python
def import_collection(
    self,
    path: Path,
    env_path: Optional[Path] = None,
    name: Optional[str] = None,
    base_url: Optional[str] = None,
) -> ParsedCollection:
    """Import Insomnia export.

    Args:
        path: Path to Insomnia export JSON file.
        env_path: Optional path to environment file.
        name: Optional override for collection name.
        base_url: Optional override for base URL.

    Returns:
        ParsedCollection with parsed requests.
    """
```

#### list_requests

```python
def list_requests(self, path: Path) -> list[dict[str, str]]:
    """List requests in Insomnia export (preview mode).

    Returns list of dicts with name, method, path keys.
    Includes folder prefix in request names.
    """
```

### Implementation Details

1. Parse JSON export with `_type: "export"` validation
2. Build folder hierarchy from `parentId` references using memoization
3. Extract environment variables from workspace-level environment resources
4. Parse headers array: `[{"name": "...", "value": "..."}]` to dict
5. Parse body by `mimeType`: JSON, form-urlencoded, multipart, raw
6. Handle authentication: bearer (with custom prefix) and basic (Base64 encoded)
7. Convert `{{var}}` to `${var}` using inherited BaseImporter methods
8. Sort requests by `metaSortKey` for consistent ordering

### Helper Methods

| Method | Description |
|--------|-------------|
| `_parse_export()` | Parse and validate JSON export |
| `_build_resource_index()` | Create _id -> resource lookup |
| `_find_workspace()` | Find workspace resource |
| `_build_folder_hierarchy()` | Map resource IDs to folder paths |
| `_parse_request()` | Parse single request resource |
| `_parse_headers()` | Convert headers array to dict |
| `_parse_body()` | Extract body content and type |
| `_parse_authentication()` | Handle bearer/basic auth |
| `_extract_environment_variables()` | Get variables from environment resources |

---

## Collection Analyzer

**Module:** `collection_importer/core/collection_analyzer.py`

Discovers and analyzes API collections in project directories.

### CollectionAnalyzer Class

```python
class CollectionAnalyzer:
    MAX_DEPTH = 7  # Maximum directory recursion depth

    POSTMAN_PATTERNS = [
        "*.postman_collection.json",
        "*_collection.json",
        "postman/*.json",
    ]

    INSOMNIA_PATTERNS = [
        "insomnia*.json",
        "*_insomnia.json",
        "insomnia/*.json",
    ]
```

### Methods

#### analyze_project

```python
def analyze_project(self, path: str = ".") -> dict:
    """Analyze project directory for API collections.

    Returns:
    {
        "collections_found": bool,
        "collections": [
            {
                "path": str,
                "format": str,  # bruno, postman, insomnia
                "name": str,
                "requests_count": int
            }
        ],
        "recommended_collection": str | None,
        "error": str | None
    }

    Priority: Bruno > Postman > Insomnia
    """
```

#### detect_format

```python
def detect_format(self, path: str) -> str:
    """Auto-detect collection format.

    Returns: 'bruno', 'postman', 'insomnia', or 'unknown'

    Detection logic:
    1. Check registered importers (can_import)
    2. Check filename patterns for Postman
    3. Check filename patterns for Insomnia
    """
```

#### get_importer

```python
def get_importer(self, format_name: str) -> Optional[BaseImporter]:
    """Get importer instance for format name."""
```

### Directory Scanning

The analyzer recursively searches directories:

```
project/
├── bruno/                  # Found: Bruno collection
│   ├── bruno.json
│   └── requests/
│       └── users.bru
├── api.postman_collection.json  # Found: Postman
├── insomnia_export.json         # Found: Insomnia
└── src/                    # Skipped (no collections)
```

Skipped directories:
- `.git`
- `node_modules`
- `__pycache__`
- `venv`
- Hidden directories (starting with `.`)

### Nested Collection Detection

The analyzer recursively searches for collections in subdirectories. For Bruno collections:
- Subdirectories with `.bru` files but no `bruno.json` are treated as part of the parent collection
- Subdirectories with their own `bruno.json` are treated as separate nested collections
- The `environments/` folder is always skipped

This allows for project structures like:

```
project/
├── main-api/
│   ├── bruno.json          # Collection 1
│   └── users/
│       └── get-user.bru    # Part of Collection 1
├── microservices/
│   ├── auth-service/
│   │   └── bruno.json      # Collection 2
│   └── user-service/
│       └── bruno.json      # Collection 3
```

The analyzer will find all 3 collections and not treat `users/` as a separate collection.

---

## JMX Generator

**Module:** `collection_importer/core/jmx_generator.py`

Generates JMeter JMX test plans from ParsedCollection.

### JMXGenerator Class

```python
class JMXGenerator:
    JMX_VERSION = "1.2"
    PROPERTIES_VERSION = "5.0"
    JMETER_VERSION = "5.6"

    DEFAULT_THREADS = 1
    DEFAULT_RAMPUP = 0
    DEFAULT_DURATION = None
```

### Methods

#### generate

```python
def generate(
    self,
    collection: ParsedCollection,
    output_path: str,
    base_url: Optional[str] = None,
    threads: int = 1,
    rampup: int = 0,
    duration: Optional[int] = None,
) -> dict:
    """Generate JMeter JMX file.

    Args:
        collection: Parsed collection data
        output_path: Output file path
        base_url: Override base URL
        threads: Virtual users
        rampup: Ramp-up seconds
        duration: Test duration (None = single loop)

    Returns:
    {
        "success": True,
        "jmx_path": str,
        "samplers_created": int,
        "threads": int,
        "rampup": int,
        "duration": int | None
    }

    Raises:
        JMXGenerationException: On failure
    """
```

### JMX Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0" jmeter="5.6">
  <hashTree>
    <TestPlan testname="Collection Name">
      <!-- Test plan properties -->
    </TestPlan>
    <hashTree>
      <!-- User Defined Variables (if any) -->
      <Arguments testname="User Defined Variables">...</Arguments>
      <hashTree/>

      <!-- HTTP Request Defaults -->
      <ConfigTestElement testname="HTTP Request Defaults">
        <stringProp name="HTTPSampler.domain">api.example.com</stringProp>
        <stringProp name="HTTPSampler.port">80</stringProp>
        <stringProp name="HTTPSampler.protocol">http</stringProp>
      </ConfigTestElement>
      <hashTree/>

      <!-- Thread Group -->
      <ThreadGroup testname="Collection Users">
        <stringProp name="ThreadGroup.num_threads">10</stringProp>
        <stringProp name="ThreadGroup.ramp_time">5</stringProp>
        <stringProp name="ThreadGroup.duration">60</stringProp>
      </ThreadGroup>
      <hashTree>
        <!-- HTTP Samplers -->
        <HTTPSamplerProxy testname="GET /users">
          <stringProp name="HTTPSampler.path">/users</stringProp>
          <stringProp name="HTTPSampler.method">GET</stringProp>
        </HTTPSamplerProxy>
        <hashTree>
          <HeaderManager>...</HeaderManager>
          <hashTree/>
          <ResponseAssertion>...</ResponseAssertion>
          <hashTree/>
        </hashTree>
      </hashTree>

      <!-- Listeners -->
      <ResultCollector testname="View Results Tree"/>
      <hashTree/>
      <ResultCollector testname="Aggregate Report"/>
      <hashTree/>
    </hashTree>
  </hashTree>
</jmeterTestPlan>
```

### Helper Methods

#### _create_root

Creates `<jmeterTestPlan>` root element with version attributes.

#### _create_test_plan

Creates `<TestPlan>` element with functional mode disabled.

#### _create_user_defined_variables

Creates `<Arguments>` element with collection variables.

#### _create_http_defaults

Creates `<ConfigTestElement>` with server configuration:
- Domain
- Port
- Protocol
- Content encoding (UTF-8)

#### _create_thread_group

Creates `<ThreadGroup>` with:
- Thread count
- Ramp-up period
- Loop controller (-1 for infinite with duration, 1 for single)
- Scheduler (enabled if duration set)

#### _create_http_sampler

Creates `<HTTPSamplerProxy>` with:
- Empty domain/port/protocol (inherited from defaults)
- Path
- Method
- Body (if present)
- Standard settings (follow redirects, keepalive, etc.)

#### _create_header_manager

Creates `<HeaderManager>` with request headers.

#### _create_response_assertion

Creates `<ResponseAssertion>` for response code validation using regex pattern `2\d{2}` to match any 2xx success code.

#### _create_json_post_processor

Creates `<JSONPostProcessor>` for extracting values from JSON responses.

```python
def _create_json_post_processor(
    self,
    variable_name: str,
    json_path: str,
    match_number: int = 1,
    default_value: str = "NOT_FOUND",
) -> ET.Element:
    """Create JSONPostProcessor element.

    Args:
        variable_name: JMeter variable name to store extracted value.
        json_path: JSONPath expression (e.g., "$.id", "$.data[0].name").
        match_number: Which match to use (1 = first, 0 = random, -1 = all).
        default_value: Value if no match found.
    """
```

This is used automatically when requests have correlations extracted from post-response scripts. Each correlation generates a separate JSONPostProcessor element.

#### _create_jsr223_pre_processor

Creates `<JSR223PreProcessor>` for pre-request scripts (Groovy).

#### _create_jsr223_post_processor

Creates `<JSR223PostProcessor>` for post-response scripts (Groovy).

Only added when no correlations were extracted from the script, as JSONPostProcessor is preferred for simple variable extraction.

#### _parse_url

Parses URL into (domain, port, protocol) tuple.

#### _prettify_xml

Pretty-prints XML with 2-space indentation.

---

## Exceptions

**Module:** `collection_importer/exceptions.py`

### Exception Hierarchy

```python
class CollectionImporterException(Exception):
    """Base exception for all collection importer errors."""
    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details

class ImporterException(CollectionImporterException):
    """Raised when collection import fails."""

class JMXGenerationException(CollectionImporterException):
    """Raised when JMX generation fails."""

class ValidationException(CollectionImporterException):
    """Raised when validation fails."""
```

### Usage

```python
from collection_importer.exceptions import ImporterException

try:
    collection = importer.import_collection(path)
except ImporterException as e:
    print(f"Import failed: {e.message}")
    if e.details:
        print(f"Details: {e.details}")
```
