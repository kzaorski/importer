# Importer Implementation Guide

This guide explains how to implement new collection format importers for Collection Importer.

## Overview

All importers inherit from `BaseImporter` and produce `ParsedCollection` objects. The base class provides shared utilities for variable conversion and request building.

## Architecture

```
BaseImporter (ABC)
    |
    +-- BrunoImporter     (Implemented)
    +-- PostmanImporter   (Implemented)
    +-- InsomniaImporter  (Implemented)
    +-- YourImporter      (New)
```

## Step-by-Step Implementation

### Step 1: Create the Importer File

Create a new file in `collection_importer/core/importers/`:

```python
# collection_importer/core/importers/yourformat.py

"""YourFormat collection importer.

Parses YourFormat collections and converts them to ParsedCollection.
"""

import json
from pathlib import Path
from typing import Optional

from collection_importer.core.data_types import ParsedCollection
from collection_importer.core.importers.base import BaseImporter
from collection_importer.exceptions import ImporterException


class YourFormatImporter(BaseImporter):
    """Import YourFormat collections."""

    @property
    def format_name(self) -> str:
        """Return format identifier."""
        return "yourformat"

    def can_import(self, path: Path) -> bool:
        """Check if path is a YourFormat collection."""
        # Implement detection logic
        pass

    def import_collection(
        self,
        path: Path,
        env_path: Optional[Path] = None,
        name: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> ParsedCollection:
        """Import YourFormat collection."""
        # Implement import logic
        pass

    def list_requests(self, path: Path) -> list[dict[str, str]]:
        """List requests in collection (preview mode)."""
        # Implement preview logic
        pass
```

### Step 2: Implement `format_name`

Return a unique lowercase identifier:

```python
@property
def format_name(self) -> str:
    """Return format identifier."""
    return "yourformat"  # Used for detection and CLI
```

### Step 3: Implement `can_import`

Detection logic to identify your format:

```python
def can_import(self, path: Path) -> bool:
    """Check if path is a YourFormat collection.

    Args:
        path: Path to check.

    Returns:
        True if path is a YourFormat collection.
    """
    if not path.exists():
        return False

    if path.is_file():
        # Check file extension
        if path.suffix.lower() != ".yourext":
            return False

        # Optionally check file content
        try:
            content = json.loads(path.read_text(encoding="utf-8"))
            return content.get("_type") == "yourformat"
        except (json.JSONDecodeError, KeyError):
            return False

    if path.is_dir():
        # Check for marker files
        return (path / "yourformat.json").exists()

    return False
```

### Step 4: Implement `import_collection`

Main import logic:

```python
def import_collection(
    self,
    path: Path,
    env_path: Optional[Path] = None,
    name: Optional[str] = None,
    base_url: Optional[str] = None,
) -> ParsedCollection:
    """Import YourFormat collection.

    Args:
        path: Path to collection file or folder.
        env_path: Optional environment file.
        name: Override collection name.
        base_url: Override base URL.

    Returns:
        ParsedCollection with parsed requests.

    Raises:
        ImporterException: If import fails.
    """
    if not path.exists():
        raise ImporterException(f"Path does not exist: {path}")

    # Load and parse the collection
    try:
        raw_data = self._load_collection(path)
    except Exception as e:
        raise ImporterException(
            "Failed to load collection",
            details=str(e),
        )

    # Extract metadata
    collection_name = name or raw_data.get("name", path.stem)
    collection_base_url = base_url or raw_data.get("base_url")
    variables = self._extract_variables(raw_data)

    # Parse requests
    requests = []
    for idx, item in enumerate(raw_data.get("items", [])):
        request = self._parse_request(item, idx)
        requests.append(request)

    # Build metadata using base class helper
    metadata = self._build_metadata(
        name=collection_name,
        source_path=str(path),
        description=raw_data.get("description", ""),
        base_url=collection_base_url,
        variables=variables,
    )

    return ParsedCollection(metadata=metadata, requests=requests)
```

### Step 5: Implement `list_requests`

Lightweight preview without full parsing:

```python
def list_requests(self, path: Path) -> list[dict[str, str]]:
    """List requests in collection (preview mode).

    Args:
        path: Path to collection.

    Returns:
        List of request summaries with name, method, path.
    """
    requests: list[dict[str, str]] = []

    try:
        raw_data = self._load_collection(path)

        for item in raw_data.get("items", []):
            # Extract minimal info
            requests.append({
                "name": item.get("name", "Unnamed"),
                "method": item.get("method", "GET").upper(),
                "path": self._extract_path(item.get("url", "/")),
            })

    except Exception:
        # Return empty list on error in preview mode
        pass

    return requests
```

### Step 6: Implement Helper Methods

Add format-specific parsing helpers:

```python
def _load_collection(self, path: Path) -> dict:
    """Load collection from path.

    Args:
        path: Path to collection.

    Returns:
        Raw collection data.
    """
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    elif path.is_dir():
        manifest = path / "yourformat.json"
        return json.loads(manifest.read_text(encoding="utf-8"))
    raise ImporterException(f"Invalid path: {path}")

def _extract_variables(self, data: dict) -> dict[str, str]:
    """Extract collection variables.

    Args:
        data: Raw collection data.

    Returns:
        Dict of variable name -> value.
    """
    variables: dict[str, str] = {}
    for var in data.get("variables", []):
        name = var.get("key") or var.get("name")
        value = var.get("value", "")
        if name:
            variables[name] = value
    return variables

def _parse_request(self, item: dict, sequence: int):
    """Parse a single request item.

    Args:
        item: Raw request data.
        sequence: Request order index.

    Returns:
        CollectionRequest instance.
    """
    # Extract headers
    headers: dict[str, str] = {}
    for header in item.get("headers", []):
        name = header.get("name") or header.get("key")
        value = header.get("value", "")
        if name and not header.get("disabled"):
            headers[name] = value

    # Extract body
    body = None
    body_type = "none"
    if "body" in item:
        raw_body = item["body"]
        if isinstance(raw_body, dict):
            mode = raw_body.get("mode", "raw")
            if mode == "raw":
                body = raw_body.get("raw", "")
                body_type = "raw"
            elif mode == "json":
                body = raw_body.get("json", {})
                body_type = "json"
        else:
            body = raw_body
            body_type = "raw"

    # Use base class helper for variable conversion
    return self._build_request(
        name=item.get("name", "Unnamed"),
        method=item.get("method", "GET"),
        url=item.get("url", "/"),
        headers=headers if headers else None,
        body=body,
        body_type=body_type,
        auth_type=item.get("auth", {}).get("type"),
        auth_value=item.get("auth", {}).get("value"),
        folder_path=item.get("folder", ""),
        sequence=sequence,
        pre_script=item.get("preScript"),
        post_script=item.get("postScript"),
    )
```

### Step 7: Register the Importer

Update `collection_analyzer.py` to include your importer:

```python
# In CollectionAnalyzer.__init__()

from collection_importer.core.importers.yourformat import YourFormatImporter

self._importers: list[BaseImporter] = [
    BrunoImporter(),
    PostmanImporter(),
    InsomniaImporter(),
    YourFormatImporter(),  # Add your importer
]
```

Update format detection patterns if needed:

```python
# In CollectionAnalyzer.detect_format()

YOURFORMAT_PATTERNS = [
    "*.yourext",
    "*_yourformat.json",
]
```

### Step 8: Update CLI and MCP

Update `cli.py` to handle your format:

```python
# In import_collection() command

elif format_name == "yourformat":
    importer = YourFormatImporter()
```

Update `mcp_server.py` similarly:

```python
# In _import_collection()

elif format_name == "yourformat":
    importer = YourFormatImporter()
```

### Step 9: Create Test Fixtures

Create test collection files in `tests/fixtures/collections/yourformat/`:

```
tests/fixtures/collections/yourformat/
├── yourformat.json           # Collection manifest
├── simple_request.yourext    # Simple request
└── with_body.yourext         # Request with body
```

Add fixtures to `tests/conftest.py`:

```python
@pytest.fixture
def yourformat_collection_dir() -> Path:
    """Return path to YourFormat test collection."""
    return COLLECTIONS_DIR / "yourformat"
```

### Step 10: Write Tests

Create `tests/core/test_yourformat_importer.py`:

```python
"""Tests for YourFormat importer."""

from pathlib import Path

import pytest

from collection_importer.core.importers.yourformat import YourFormatImporter


class TestYourFormatImporter:
    """Test YourFormatImporter class."""

    def test_format_name(self):
        """Test format_name property."""
        importer = YourFormatImporter()
        assert importer.format_name == "yourformat"

    def test_can_import_valid_file(self, yourformat_collection_dir: Path):
        """Test detection of valid collection."""
        importer = YourFormatImporter()
        assert importer.can_import(yourformat_collection_dir)

    def test_can_import_invalid_file(self, tmp_path: Path):
        """Test rejection of invalid path."""
        importer = YourFormatImporter()
        invalid_file = tmp_path / "invalid.txt"
        invalid_file.write_text("not a collection")
        assert not importer.can_import(invalid_file)

    def test_import_collection(self, yourformat_collection_dir: Path):
        """Test full collection import."""
        importer = YourFormatImporter()
        collection = importer.import_collection(yourformat_collection_dir)

        assert collection.metadata.format == "yourformat"
        assert collection.request_count > 0

    def test_list_requests(self, yourformat_collection_dir: Path):
        """Test preview mode."""
        importer = YourFormatImporter()
        requests = importer.list_requests(yourformat_collection_dir)

        assert len(requests) > 0
        assert all("name" in r for r in requests)
        assert all("method" in r for r in requests)
        assert all("path" in r for r in requests)

    def test_variable_conversion(self, yourformat_collection_dir: Path):
        """Test {{var}} to ${var} conversion."""
        importer = YourFormatImporter()
        collection = importer.import_collection(yourformat_collection_dir)

        # Check that variables are converted
        for request in collection.requests:
            assert "{{" not in request.path
            for value in request.headers.values():
                assert "{{" not in value

    def test_base_url_override(self, yourformat_collection_dir: Path):
        """Test base URL override parameter."""
        importer = YourFormatImporter()
        collection = importer.import_collection(
            yourformat_collection_dir,
            base_url="https://override.example.com",
        )

        assert collection.metadata.base_url == "https://override.example.com"
```

## Base Class Utilities

### Variable Conversion

The base class provides automatic variable conversion:

```python
# Convert single string
text = self._convert_variables("{{base_url}}/users")
# Result: "${base_url}/users"

# Convert nested payload
payload = self._convert_payload({"user": "{{name}}"})
# Result: {"user": "${name}"}

# Extract path from URL
path = self._extract_path("{{base_url}}/users/{{id}}")
# Result: "/users/${id}"
```

### Building Requests

Use `_build_request()` for consistent request creation:

```python
request = self._build_request(
    name="Get User",
    method="GET",
    url="{{base_url}}/users/{{id}}",  # Variables are auto-converted
    headers={"Authorization": "Bearer {{token}}"},  # Auto-converted
    body={"name": "{{username}}"},  # Auto-converted
    body_type="json",
    auth_type="bearer",
    auth_value="{{access_token}}",  # Auto-converted
    folder_path="users",
    sequence=0,
    pre_script=None,
    post_script=None,
)
```

### Building Metadata

Use `_build_metadata()` for consistent metadata creation:

```python
metadata = self._build_metadata(
    name="My Collection",
    source_path="/path/to/collection",
    description="Collection description",
    base_url="https://api.example.com",
    variables={"api_key": "{{secret}}"},  # Auto-converted
)
```

## Complete Example: Bruno Importer

The Bruno importer (`bruno.py`) is a complete reference implementation:

**Key Features:**
1. Handles both folder collections and single files
2. Parses `.bru` file format with regex
3. Auto-detects environment files
4. Sorts requests by sequence number
5. Handles nested folders
6. Supports bearer and basic auth

**Code Highlights:**

```python
# Detection logic
def can_import(self, path: Path) -> bool:
    if path.is_dir():
        if (path / "bruno.json").exists():
            return True
        return any(path.rglob("*.bru"))
    return path.suffix == ".bru"

# Block extraction with regex
def _extract_block(self, content: str, block_name: str) -> Optional[str]:
    escaped_name = re.escape(block_name)
    pattern = rf"{escaped_name}\s*\{{([\s\S]*?)\n\}}"
    match = re.search(pattern, content)
    return match.group(1) if match else None

# Request file sorting
def _find_request_files(self, path: Path) -> list[Path]:
    files = list(path.rglob("*.bru"))
    files = [f for f in files if "environments" not in f.parts]

    def sort_key(file: Path) -> tuple[str, int, str]:
        folder = self._get_folder_path(file, path)
        seq = self._extract_sequence(file)
        return (folder, seq, file.name)

    return sorted(files, key=sort_key)
```

## Postman Importer Guide

Postman v2.1 JSON structure:

```json
{
  "info": {
    "name": "Collection Name",
    "_postman_id": "uuid",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Folder",
      "item": [
        {
          "name": "Request",
          "request": {
            "method": "GET",
            "header": [{"key": "Auth", "value": "{{token}}"}],
            "url": {
              "raw": "{{base_url}}/users",
              "host": ["{{base_url}}"],
              "path": ["users"]
            }
          }
        }
      ]
    }
  ],
  "variable": [
    {"key": "base_url", "value": "https://api.example.com"}
  ]
}
```

**Implementation Notes:**
1. Parse `info.name` for collection name
2. Recursively process `item[]` (can contain folders or requests)
3. Handle `url` as object (with host/path) or string (raw)
4. Extract `variable[]` as collection variables
5. Process `header[]` with disabled flag support
6. Handle `body.mode`: raw, json, formdata, urlencoded

## Insomnia Importer Guide

Insomnia v4 export structure:

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
      "name": "Get Users",
      "method": "GET",
      "url": "{{ _.base_url }}/users",
      "headers": [{"name": "Auth", "value": "{{ _.token }}"}],
      "parentId": "fld_456"
    },
    {
      "_id": "env_abc",
      "_type": "environment",
      "data": {"base_url": "https://api.example.com"}
    }
  ]
}
```

**Implementation Notes:**
1. Filter `resources[]` by `_type`
2. Build parent hierarchy from `parentId` references
3. Handle Insomnia's `{{ _.var }}` syntax (convert to `${var}`)
4. Extract environment from `_type: "environment"` resources
5. Handle body types: text, json, file, graphql

## Testing Checklist

Before submitting your importer:

- [ ] `format_name` returns unique identifier
- [ ] `can_import` correctly identifies format
- [ ] `can_import` rejects other formats
- [ ] `import_collection` parses all request fields
- [ ] `list_requests` works in preview mode
- [ ] Variables are converted (`{{var}}` -> `${var}`)
- [ ] Headers are properly parsed
- [ ] Body types are handled (json, raw, form)
- [ ] Auth types are supported
- [ ] Folder structure is preserved
- [ ] Sequence ordering works
- [ ] Environment files are supported
- [ ] Base URL override works
- [ ] Name override works
- [ ] Error handling with ImporterException
- [ ] Unit tests achieve >80% coverage
- [ ] Integration test with JMX generator passes
