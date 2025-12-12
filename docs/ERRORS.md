# Error Reference

This document describes all exception types and common error scenarios in Collection Importer.

## Exception Hierarchy

```
CollectionImporterException (base)
├── ImporterException       - Collection parsing errors
├── JMXGenerationException  - JMX generation errors
└── ValidationException     - Validation errors
```

## Exception Types

### CollectionImporterException

Base exception for all Collection Importer errors.

**Attributes:**
- `message` - Human-readable error description
- `details` - Optional technical details

**Example:**
```python
from collection_importer.exceptions import CollectionImporterException

try:
    # operation
except CollectionImporterException as e:
    print(f"Error: {e.message}")
    if e.details:
        print(f"Details: {e.details}")
```

### ImporterException

Raised when collection import fails.

**Common causes:**
- File or directory not found
- Invalid collection format
- Missing required fields
- Unsupported collection version
- Malformed JSON/YAML

**Examples:**

| Error | Cause | Solution |
|-------|-------|----------|
| "Path does not exist" | File/folder not found | Check path is correct |
| "Invalid Postman collection" | Missing `info` field | Export as Postman v2.1 |
| "Cannot detect format" | Unknown collection type | Use `--format` flag |
| "No requests found" | Empty collection | Add requests to collection |

### JMXGenerationException

Raised when JMX file generation fails.

**Common causes:**
- Invalid configuration values
- File write permission denied
- XML generation errors
- Missing base URL

**Examples:**

| Error | Cause | Solution |
|-------|-------|----------|
| "Output directory does not exist" | Invalid path | Create directory first |
| "Invalid base_url" | Malformed URL | Use format `http://host:port` |
| "Threads must be 1-100000" | Value out of range | Use valid thread count |
| "Duration must be 1-86400" | Value out of range | Use 1 second to 24 hours |

### ValidationException

Raised when validation fails.

**Common causes:**
- Invalid JMX structure
- Missing required elements
- Configuration errors

## CLI Error Messages

### Import Errors

```
Error: Importer for 'unknown' not found. Supported: bruno, postman, insomnia
```
**Solution:** Use one of the supported formats or specify with `--format`.

```
Error: Could not detect collection format
```
**Solution:** Ensure collection has valid format markers (bruno.json, .postman_collection.json, etc.)

### Generation Errors

```
Error: Base URL is required but not found in collection
```
**Solution:** Use `--base-url` flag or add base URL to collection variables.

```
Error: No requests to generate
```
**Solution:** Ensure collection contains at least one request.

## MCP Server Errors

MCP tools return errors as text content:

```json
{
  "type": "text",
  "text": "Error: Could not detect collection format for ./unknown"
}
```

## Debugging Tips

### Enable Verbose Output

Currently not available via CLI. Check exception `details` attribute for more info.

### Common Issues

1. **Wrong file path**: Use absolute paths or paths relative to current directory
2. **Format not detected**: File naming matters - use standard naming conventions
3. **Variables not converted**: Ensure variables use `{{name}}` syntax
4. **Missing authentication**: Check auth blocks in source collection

## Error Handling in Code

### Catching Specific Exceptions

```python
from collection_importer.exceptions import (
    ImporterException,
    JMXGenerationException,
)

try:
    collection = importer.import_collection(path)
    generator.generate(collection, output)
except ImporterException as e:
    print(f"Import failed: {e.message}")
except JMXGenerationException as e:
    print(f"Generation failed: {e.message}")
```

### Catching All Errors

```python
from collection_importer.exceptions import CollectionImporterException

try:
    # operations
except CollectionImporterException as e:
    print(f"Operation failed: {e}")
```
