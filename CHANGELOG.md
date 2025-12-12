# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Automatic correlation extraction from post-response scripts (Bruno, Postman, Insomnia)
- JSONPostProcessor generation for `bru.setVar()`, `pm.environment.set()`, `pm.globals.set()`, `pm.collectionVariables.set()`, `insomnia.setEnvironmentVariable()` patterns
- JavaScript property access to JSONPath conversion (`data.user.id` -> `$.user.id`)
- CorrelationExtractor module for parsing post-response scripts
- Interactive import prompt in `analyze` command - after discovering collections, offers immediate import
- JSR223 PreProcessor support for pre-request scripts
- JSR223 PostProcessor support for post-response scripts (fallback when correlations cannot be extracted)
- JSONPostProcessor method for response value extraction
- `--verbose` / `-v` flag for debug output in CLI import command
- Comprehensive unit tests for all core modules (594+ tests)
- CONTRIBUTING.md with development guidelines
- defusedxml dependency for secure XML parsing (available for future use)

### Changed
- Increased MAX_DEPTH from 3 to 7 for deeper collection scanning
- JMX generator now applies pre/post scripts from imported collections
- JSR223 PostProcessor only added when no correlations could be extracted from script
- Improved test coverage to 80%+

### Changed
- Interactive import in `analyze` command now allows selecting which collection to import (when multiple found)
- JMX output filenames are now generated from collection path for better uniqueness
- File existence check with option to overwrite, rename, or cancel

### Fixed
- CollectionAnalyzer now correctly discovers nested Bruno collections (previously stopped at first collection found)
- Bruno subdirectories with `.bru` files but no `bruno.json` are correctly treated as part of parent collection

## [1.0.0] - 2024-12-08

### Added
- Initial release of Collection Importer
- Bruno collection format support
  - Parse .bru files and bruno.json
  - Support for environments, variables, and folder hierarchy
  - HTTP methods, headers, body (JSON, form, raw)
  - Bearer and Basic authentication
  - Pre-request and post-response scripts
- Postman collection format support (v2.1)
  - Parse Postman JSON export files
  - Collection variables and environments
  - Nested folder structure
  - Event scripts (pre-request, test)
- Insomnia collection format support (v4)
  - Parse Insomnia JSON export files
  - Workspace and folder hierarchy
  - Environment variables
  - Authentication (bearer, basic, api-key)
- JMeter JMX generation
  - TestPlan with configurable settings
  - HTTP Request Defaults (centralized server config)
  - User Defined Variables (collection variables)
  - ThreadGroup with configurable threads, ramp-up, duration
  - HTTPSamplerProxy for each request
  - HeaderManager for request-specific headers
  - ResponseAssertion (validates 2xx responses)
  - View Results Tree listener
  - Aggregate Report listener
- CLI commands
  - `analyze` - Discover API collections in project
  - `import` - Import collection and generate JMX
  - `mcp` - Start MCP Server for AI integration
- MCP Server integration
  - Tool for analyzing projects
  - Tool for importing collections
  - Tool for listing endpoints
- Variable syntax conversion ({{var}} to ${var})
- Auto-detection of collection format
- Environment file support for all formats
- Base URL override capability
- Preview mode for viewing requests without generating JMX
- Comprehensive documentation
  - README.md with quick start
  - QUICKSTART.md with detailed guide
  - ARCHITECTURE.md with system design
  - CLAUDE.md for AI assistant integration
  - JMX format reference
  - Collection format specifications

### Technical Details
- Python 3.11+ required
- Dependencies: click, rich, pyyaml, mcp, anyio
- Type hints on all public methods
- Google-style docstrings
- Custom exception hierarchy

[Unreleased]: https://github.com/your-org/collection-importer/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/your-org/collection-importer/releases/tag/v1.0.0
