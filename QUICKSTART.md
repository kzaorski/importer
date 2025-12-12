# Quick Start Guide

Collection Importer converts API collections from Bruno, Postman, and Insomnia to JMeter JMX test plans. This guide covers everything you need to start generating load tests from your existing API collections.

## Installation

```bash
pip install collection-importer
```

Verify the installation:

```bash
collection-importer --version
```

## Format Support

| Format | Detection | Preview | CLI Import | MCP Import |
|--------|-----------|---------|------------|------------|
| Bruno | Yes | Yes | Yes | Yes |
| Postman | Yes | Yes | Yes | Yes |
| Insomnia | Yes | Yes | Yes | Yes |

All three formats are fully supported for detection, preview, and JMX generation.

## Typical Workflow

### Step 1: Discover Collections

Scan your project directory to find API collections:

```bash
collection-importer analyze
```

Output example:
```
Found Collections
┏━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ # ┃ Format   ┃ Path                             ┃ Requests ┃
┡━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ 1 │ BRUNO    │ ./api-tests/                     │       12 │
│ 2 │ BRUNO    │ ./microservices/auth/            │        5 │
│ 3 │ POSTMAN  │ ./legacy/api-collection.json     │        8 │
└───┴──────────┴──────────────────────────────────┴──────────┘

Select collection to import (0 to skip) [1]: 2

Import 'auth' to microservices-auth.jmx? [Y/n]:
```

You can select which collection to import by entering its number. If a file with the generated name already exists, you'll be prompted to overwrite, rename, or cancel.

### Step 2: Preview Requests

Before generating a JMX file, preview what will be imported:

```bash
collection-importer import ./api-tests --preview
```

This lists all requests that will be included without creating any files.

### Step 3: Generate JMX

Import the collection and generate a JMeter test plan:

```bash
collection-importer import ./api-tests -o load-test.jmx
```

### Step 4: Run in JMeter

Open the generated JMX file in JMeter GUI or run from command line:

```bash
jmeter -n -t load-test.jmx -l results.jtl
```

## CLI Commands Reference

### analyze

Discover API collections in a project directory.

```bash
# Scan current directory
collection-importer analyze

# Scan specific path
collection-importer analyze --path ./my-project
```

### import

Import a collection and generate a JMX file. This is the main command.

```bash
collection-importer import <PATH> [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `-o, --output PATH` | Output JMX file path | `test.jmx` |
| `-f, --format FORMAT` | Force format: `bruno`, `postman`, `insomnia` | Auto-detect |
| `-e, --env PATH` | Environment file path | None |
| `--base-url URL` | Override base URL | From collection |
| `--threads N` | Number of virtual users | 1 |
| `--rampup N` | Ramp-up period in seconds | 0 |
| `--duration N` | Test duration in seconds | None (single iteration) |
| `--preview` | List requests without generating | False |
| `-v, --verbose` | Enable verbose output with debug information | False |

**Examples:**

```bash
# Basic import with auto-detection
collection-importer import ./bruno-collection

# Specify output file
collection-importer import ./collection -o user-api-test.jmx

# Force format detection
collection-importer import ./mixed-folder --format postman

# Use environment file
collection-importer import ./collection -e ./environments/staging.json

# Override base URL
collection-importer import ./collection --base-url http://localhost:8080

# Configure load test
collection-importer import ./collection --threads 50 --rampup 10 --duration 300
```

## Load Testing Configuration

Configure load test parameters when importing:

### Threads (Virtual Users)

The `--threads` option sets the number of concurrent virtual users.

```bash
# 100 concurrent users
collection-importer import ./collection --threads 100
```

### Ramp-up Period

The `--rampup` option defines how long (in seconds) to gradually start all threads.

```bash
# Start 100 users over 60 seconds (gradual load increase)
collection-importer import ./collection --threads 100 --rampup 60
```

### Duration

The `--duration` option sets the total test duration in seconds.

```bash
# Run for 5 minutes
collection-importer import ./collection --threads 50 --duration 300
```

### Example Configurations

**Smoke Test** - Quick validation:
```bash
collection-importer import ./collection --threads 1
```

**Load Test** - Typical production load:
```bash
collection-importer import ./collection --threads 50 --rampup 30 --duration 300
```

**Stress Test** - Find breaking points:
```bash
collection-importer import ./collection --threads 200 --rampup 60 --duration 600
```

**Spike Test** - Sudden load increase:
```bash
collection-importer import ./collection --threads 100 --rampup 1 --duration 120
```

## Supported Collection Formats

### Format Comparison

| Feature | Bruno | Postman | Insomnia |
|---------|-------|---------|----------|
| File Format | `.bru` files in folder | Single JSON file | Single JSON file |
| Version Supported | N/A | v2.1 | v4 |
| HTTP Methods | All | All | All |
| Headers | Yes | Yes | Yes |
| JSON Body | Yes | Yes | Yes |
| Form Data | Yes | Yes | Yes |
| Basic Auth | Yes | Yes | Yes |
| Bearer Token | Yes | Yes | Yes |
| Variables | `{{var}}` | `{{var}}` | `{{ _.var }}` |
| Environments | Yes | Yes | Yes |
| Pre-request Scripts | Yes | Yes | Yes |
| Post-response Scripts | Yes | Yes | Yes |
| Folder Structure | Native folders | Nested `item[]` | `parentId` refs |

### Bruno Collections

Bruno collections are folder-based with individual `.bru` files for each request.

**Structure:**
```
my-collection/
├── bruno.json           # Collection metadata
├── environments/
│   ├── dev.bru
│   └── prod.bru
├── users/
│   ├── get-users.bru
│   └── create-user.bru
└── orders/
    └── get-orders.bru
```

**Import:**
```bash
collection-importer import ./my-collection
```

### Postman Collections

Postman collections are single JSON files exported from Postman (v2.1 format).

**Export from Postman:**
1. Right-click collection in Postman
2. Select "Export"
3. Choose "Collection v2.1"
4. Save as JSON file

**Import:**
```bash
collection-importer import ./collection.postman_collection.json
```

### Insomnia Collections

Insomnia collections are JSON exports from Insomnia (v4 format).

**Export from Insomnia:**
1. Go to Application > Preferences > Data
2. Click "Export Data"
3. Select "Insomnia v4 (JSON)"
4. Save file

**Import:**
```bash
collection-importer import ./insomnia-export.json
```

## MCP Server Integration

Collection Importer includes an MCP (Model Context Protocol) server for integration with AI assistants like GitHub Copilot and Claude.

### What is MCP?

MCP allows AI assistants to interact with external tools directly. With Collection Importer's MCP server, you can use natural language to:
- Discover collections in your project
- Generate JMX files from any supported collection format
- Preview requests in collections

### VS Code / GitHub Copilot Setup

Add to your VS Code `settings.json`:

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

### Claude Code Setup

Add to your Claude Code MCP configuration:

```json
{
  "mcpServers": {
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
| `analyze_project_for_collections` | Scan project directory and list found collections |
| `import_collection_to_jmx` | Import collection and generate JMX file |
| `list_collection_requests` | Preview requests in a collection |

### Example Usage with AI Assistant

After configuring the MCP server, you can ask your AI assistant:

- "Find API collections in this project"
- "Generate a JMX file from the Bruno collection in ./api-tests with 50 threads"
- "Show me the requests in the Postman collection"

## Variable Handling

### Automatic Conversion

Collection Importer automatically converts collection variables to JMeter format:

| Collection Format | Syntax | JMeter Format |
|-------------------|--------|---------------|
| Bruno | `{{base_url}}` | `${base_url}` |
| Postman | `{{base_url}}` | `${base_url}` |
| Insomnia | `{{ _.base_url }}` | `${base_url}` |

### Sensitive Variable Detection

Variables with sensitive names are detected and can be masked in logs:

- `token`, `secret`, `password`, `key`
- `auth`, `api_key`, `apikey`
- `credential`, `private`

### Using Environment Files

Load environment-specific variables during import:

**Bruno environment file** (`environments/staging.bru`):
```
vars {
  base_url: https://staging-api.example.com
  api_key: staging-key-123
}
```

**Import with environment:**
```bash
collection-importer import ./collection -e ./environments/staging.bru
```

### Overriding Base URL

Override the base URL regardless of collection settings:

```bash
collection-importer import ./collection --base-url http://localhost:8080
```

This is useful for:
- Local development testing
- Pointing to different environments
- Using mock servers

## Automatic Correlation Extraction

Collection Importer automatically detects variable extraction patterns in post-response scripts and converts them to JMeter JSONPostProcessor elements.

### Supported Patterns

**Bruno:**
```javascript
script:post-response {
  const data = res.body;
  bru.setVar('user_id', data.id);
  bru.setVar('token', data.auth.token);
}
```

**Postman:**
```javascript
var jsonData = pm.response.json();
pm.environment.set('user_id', jsonData.id);
pm.globals.set('token', jsonData.auth.token);
```

**Insomnia:**
```javascript
const data = await insomnia.response.json();
insomnia.setEnvironmentVariable('user_id', data.id);
```

### How It Works

1. When importing a collection, the tool scans post-response scripts
2. Detects `bru.setVar()`, `pm.environment.set()`, and similar patterns
3. Converts JavaScript property paths to JSONPath expressions
4. Generates JSONPostProcessor elements instead of non-functional JSR223 scripts

### JSONPath Conversion

| Script | JSONPath |
|--------|----------|
| `bru.setVar('id', data.user.id)` | `$.user.id` |
| `pm.environment.set('token', jsonData.auth.token)` | `$.auth.token` |
| `bru.setVar('first', data.items[0].name)` | `$.items[0].name` |

### Limitations

Complex scripts with conditional logic (if/else), loops, or function calls cannot be automatically converted. In these cases, the original script is preserved as a JSR223 PostProcessor.

---

## Tips and Best Practices

### Organize Requests in Folders

Group related requests in folders for better organization in the generated JMX:

```
collection/
├── auth/
│   ├── login.bru
│   └── logout.bru
├── users/
│   ├── get-user.bru
│   └── update-user.bru
└── orders/
    └── create-order.bru
```

### Use Meaningful Request Names

Request names become sampler names in JMeter. Use descriptive names:

- Good: `Get User by ID`, `Create New Order`
- Bad: `Request 1`, `Test`

### Test with Preview First

Always preview before generating to verify correct requests are included:

```bash
collection-importer import ./collection --preview
```

### Start with Low Thread Count

Begin with a small number of threads to verify test behavior:

```bash
# First run - verify functionality
collection-importer import ./collection --threads 1

# After verification - increase load
collection-importer import ./collection --threads 50 --rampup 30 --duration 300
```

### Use Version Control for Collections

Keep your API collections in version control alongside your code. This ensures:
- Consistent test generation across environments
- History of API changes
- Collaboration with team members

## Next Steps

For more detailed information, refer to:

| Document | Description |
|----------|-------------|
| [README.md](README.md) | Project overview and features |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design and data flow |
| [docs/CORE_MODULES.md](docs/CORE_MODULES.md) | Detailed module API reference |
| [docs/reference/COLLECTION_FORMATS.md](docs/reference/COLLECTION_FORMATS.md) | Detailed format specifications |
| [docs/reference/JMX_FORMAT_REFERENCE.md](docs/reference/JMX_FORMAT_REFERENCE.md) | JMeter JMX structure reference |
