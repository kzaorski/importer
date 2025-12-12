# Collection Formats Specification

Detailed specifications for supported API collection formats (December 2025).

## Bruno .bru Format

**Version**: Ohm.js grammar (latest)
**Reference**: https://docs.usebruno.com/bru-lang/overview

### Structure

```
my-collection/
├── bruno.json           # Collection metadata
├── environments/
│   └── dev.bru          # Environment variables
├── auth/
│   └── login.bru        # Request file
└── users/
    ├── get-user.bru
    └── create-user.bru
```

### Request File (.bru)

```bru
meta {
  name: Get User
  type: http
  seq: 1
}

get {
  url: {{base_url}}/users/{{user_id}}
  body: none
  auth: bearer
}

headers {
  Content-Type: application/json
}

auth:bearer {
  token: {{auth_token}}
}

script:pre-request {
  bru.setVar('timestamp', Date.now());
}

script:post-response {
  bru.setVar('user_id', res.body.id);
}
```

### Environment File (.bru)

```bru
vars {
  base_url: https://api.example.com
  auth_token: secret_value
  ~disabled_var: not_used
}
```

### Mapping to pt_scenario.yaml

| Bruno | pt_scenario |
|-------|-------------|
| meta.name | step.name |
| get/post/etc + url | step.endpoint |
| headers {} | step.headers |
| body:json {} | step.payload |
| auth:bearer | step.headers.Authorization |
| script:pre-request | # comment |
| script:post-response | # comment |
| vars {} | variables: |

---

## Postman Collection v2.1

**Version**: Collection Format v2.1.0, SDK 5.2.0
**Reference**: https://schema.postman.com/json/collection/v2.1.0/docs/index.html

### Structure

```json
{
  "info": {
    "name": "My Collection",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Auth",
      "item": [
        {
          "name": "Login",
          "request": {
            "method": "POST",
            "header": [...],
            "body": {...},
            "url": {...}
          }
        }
      ]
    }
  ],
  "variable": [...]
}
```

### Request Object

```json
{
  "name": "Get User",
  "request": {
    "method": "GET",
    "header": [
      {"key": "Authorization", "value": "Bearer {{token}}"}
    ],
    "url": {
      "raw": "{{base_url}}/users/{{user_id}}",
      "host": ["{{base_url}}"],
      "path": ["users", "{{user_id}}"]
    }
  }
}
```

### Mapping to pt_scenario.yaml

| Postman | pt_scenario |
|---------|-------------|
| item.name | step.name (with folder prefix) |
| request.method + url.raw | step.endpoint |
| request.header[] | step.headers |
| request.body.raw | step.payload |
| auth.bearer | step.headers.Authorization |
| variable[] | variables: |

---

## Insomnia v4 JSON

**Version**: v4 JSON (recommended), Core 12.1.0
**Reference**: https://developer.konghq.com/insomnia/import-export/

### Structure

```json
{
  "_type": "export",
  "__export_format": 4,
  "resources": [
    {
      "_type": "request",
      "_id": "req_xxx",
      "parentId": "fld_xxx",
      "name": "Get User",
      "method": "GET",
      "url": "{{base_url}}/users/{{user_id}}",
      "headers": [...],
      "body": {...}
    },
    {
      "_type": "request_group",
      "_id": "fld_xxx",
      "name": "Users"
    },
    {
      "_type": "environment",
      "_id": "env_xxx",
      "data": {"base_url": "..."}
    }
  ]
}
```

### Mapping to pt_scenario.yaml

| Insomnia | pt_scenario |
|----------|-------------|
| resource.name | step.name (with folder prefix) |
| method + url | step.endpoint |
| headers[] | step.headers |
| body.text | step.payload |
| environment.data | variables: |

---

## Variable Syntax Compatibility

All formats use `{{variable}}` syntax - directly compatible with pt_scenario.yaml `${variable}` after conversion.

| Format | Syntax | Conversion |
|--------|--------|------------|
| Bruno | `{{var}}` | `${var}` |
| Postman | `{{var}}` | `${var}` |
| Insomnia | `{{var}}` or `_.var` | `${var}` |
| pt_scenario | `${var}` | native |

---

## Correlations (Variable Extraction)

Collection Importer automatically extracts variable correlations from post-response scripts and converts them to JMeter JSONPostProcessor elements.

### Bruno

```javascript
script:post-response {
  const data = res.body;
  bru.setVar('user_id', data.id);
  bru.setVar('token', data.auth.token);
  bru.setVar('item_id', data.items[0].id);
}
```

Supported patterns:
- `bru.setVar('varName', data.path)`
- `bru.setVar('varName', res.body.path)`
- `bru.setVar('varName', res.getBody().path)`

### Postman

```javascript
var jsonData = pm.response.json();
pm.environment.set('user_id', jsonData.id);
pm.globals.set('auth_token', jsonData.auth.token);
pm.collectionVariables.set('session', jsonData.session_id);
```

Supported patterns:
- `pm.environment.set('varName', jsonData.path)`
- `pm.globals.set('varName', jsonData.path)`
- `pm.collectionVariables.set('varName', data.path)`

### Insomnia

```javascript
const data = await insomnia.response.json();
insomnia.setEnvironmentVariable('user_id', data.id);
insomnia.setEnvironmentVariable('token', data.auth.token);
```

Supported patterns:
- `insomnia.setEnvironmentVariable('varName', data.path)`
- `insomnia.setEnvironmentVariable('varName', response.path)`

### Conversion to JMeter

Each detected pattern is converted to a JSONPostProcessor element:

| Script | JSONPath | JMeter Variable |
|--------|----------|-----------------|
| `bru.setVar('id', data.user.id)` | `$.user.id` | `${id}` |
| `pm.environment.set('token', jsonData.auth.token)` | `$.auth.token` | `${token}` |
| `bru.setVar('first', data.items[0].name)` | `$.items[0].name` | `${first}` |

### Limitations

The following patterns cannot be automatically converted:

- Scripts with conditional logic (if/else)
- Dynamic property access: `data[variable]`
- Function calls: `data.items.map(...)`
- Multiple assignments to the same variable
- Complex transformations

For unsupported patterns, the original script is preserved as a JSR223 PostProcessor (Groovy).
