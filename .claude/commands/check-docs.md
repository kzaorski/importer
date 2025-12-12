---
description: Check documentation consistency with code
model: haiku
---

## Task

Check documentation consistency with the Collection Importer source code.

## Reference Files

Project documentation:
@CLAUDE.md
@README.md
@QUICKSTART.md

Core modules documentation:
@docs/CORE_MODULES.md

Version sources:
@pyproject.toml
@collection_importer/__init__.py
@CHANGELOG.md

Data types:
@collection_importer/core/data_types.py

CLI:
@collection_importer/cli.py

## What to Check

### 1. Version Numbers
Compare version numbers in:
- `pyproject.toml` (`version` field)
- `collection_importer/__init__.py` (`__version__`)
- `CHANGELOG.md` (latest `## [X.Y.Z]` header, not `[Unreleased]`)

### 2. CLI Options
Compare Click options in `collection_importer/cli.py` with documentation in:
- `README.md`
- `QUICKSTART.md`
- `CLAUDE.md` (Common Commands section)

Check: option names, short flags, default values, descriptions.

### 3. Dataclass Fields
Compare dataclasses in `collection_importer/core/data_types.py`:
- `CollectionRequest`
- `CollectionMetadata`
- `ParsedCollection`

With documentation in:
- `docs/CORE_MODULES.md`
- `CLAUDE.md` (Key Data Structures section)

Check: field names, types, default values.

### 4. Function Signatures
Compare public methods in `collection_importer/core/` modules with `docs/CORE_MODULES.md`.

Check: method names, parameters and their types, return types.

## Report Format

```
## Documentation Consistency Report

### Version Check
| Location | Version | Status |
|----------|---------|--------|
| pyproject.toml | X.Y.Z | ... |
| __init__.py | X.Y.Z | ... |
| CHANGELOG.md | X.Y.Z | ... |

### CLI Options (import command)
| Option | cli.py | README.md | Status |
|--------|--------|-----------|--------|
| --output | default="test.jmx" | ... | OK/MISMATCH |

### Dataclass Fields
| Class | Code | Documentation | Status |
|-------|------|---------------|--------|
| CollectionRequest | 13 fields | ... | OK/MISSING |

### Summary
- Issues found: N
- Files to update: [list]
```

If everything is consistent, confirm that all checks passed.
