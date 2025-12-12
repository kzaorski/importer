"""Pytest configuration and fixtures for Collection Importer tests."""

from pathlib import Path
from typing import Any

import pytest

from collection_importer.core.importers.bruno import BrunoImporter
from collection_importer.core.importers.insomnia import InsomniaImporter
from collection_importer.core.importers.postman import PostmanImporter

# Test fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"
COLLECTIONS_DIR = FIXTURES_DIR / "collections"


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to test fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture
def bruno_collection_dir() -> Path:
    """Return path to Bruno test collection."""
    return COLLECTIONS_DIR / "bruno"


@pytest.fixture
def postman_collection_file() -> Path:
    """Return path to basic Postman test collection."""
    return COLLECTIONS_DIR / "postman" / "basic" / "collection.json"


@pytest.fixture
def insomnia_collection_file() -> Path:
    """Return path to Insomnia test collection."""
    return COLLECTIONS_DIR / "insomnia" / "basic" / "export.json"


@pytest.fixture
def sample_parsed_request() -> dict[str, Any]:
    """Return a sample parsed request dict."""
    return {
        "name": "Get User",
        "method": "GET",
        "path": "/users/${user_id}",
        "headers": {"Authorization": "Bearer ${token}"},
        "body": None,
        "body_type": "none",
        "auth_type": None,
        "auth_value": None,
        "folder_path": "users",
        "sequence": 1,
        "pre_script": None,
        "post_script": None,
    }


@pytest.fixture
def sample_collection_metadata() -> dict[str, Any]:
    """Return sample collection metadata."""
    return {
        "name": "Test Collection",
        "description": "A test collection",
        "base_url": "http://localhost:8080",
        "variables": {"api_key": "test123"},
        "format": "bruno",
    }


# Bruno Importer fixtures


@pytest.fixture
def bruno_importer() -> BrunoImporter:
    """Return a fresh BrunoImporter instance."""
    return BrunoImporter()


@pytest.fixture
def bruno_real_world_jsonplaceholder() -> Path:
    """Return path to JSONPlaceholder Bruno collection."""
    return COLLECTIONS_DIR / "bruno" / "real-world" / "jsonplaceholder"


@pytest.fixture
def bruno_real_world_github() -> Path:
    """Return path to GitHub API Bruno collection."""
    return COLLECTIONS_DIR / "bruno" / "real-world" / "github-api"


@pytest.fixture
def bruno_with_environments() -> Path:
    """Return path to Bruno collection with environments folder."""
    return COLLECTIONS_DIR / "bruno"


@pytest.fixture
def bruno_auth_fixtures() -> Path:
    """Return path to Bruno auth fixtures folder."""
    return COLLECTIONS_DIR / "bruno" / "auth"


@pytest.fixture
def bruno_methods_fixtures() -> Path:
    """Return path to Bruno methods fixtures folder."""
    return COLLECTIONS_DIR / "bruno" / "methods"


@pytest.fixture
def bruno_scripts_fixtures() -> Path:
    """Return path to Bruno scripts fixtures folder."""
    return COLLECTIONS_DIR / "bruno" / "scripts"


@pytest.fixture
def bruno_edge_cases_fixtures() -> Path:
    """Return path to Bruno edge-cases fixtures folder."""
    return COLLECTIONS_DIR / "bruno" / "edge-cases"


@pytest.fixture
def bruno_nested_fixtures() -> Path:
    """Return path to Bruno nested folder fixtures."""
    return COLLECTIONS_DIR / "bruno" / "nested"


@pytest.fixture
def single_bru_file() -> Path:
    """Return path to single standalone .bru file."""
    return COLLECTIONS_DIR / "bruno" / "single-file" / "standalone.bru"


# Insomnia Importer fixtures


@pytest.fixture
def insomnia_importer() -> InsomniaImporter:
    """Return a fresh InsomniaImporter instance."""
    return InsomniaImporter()


@pytest.fixture
def insomnia_basic_collection() -> Path:
    """Return path to basic Insomnia collection."""
    return COLLECTIONS_DIR / "insomnia" / "basic" / "export.json"


@pytest.fixture
def insomnia_auth_bearer() -> Path:
    """Return path to Insomnia bearer auth fixture."""
    return COLLECTIONS_DIR / "insomnia" / "auth" / "bearer-auth.json"


@pytest.fixture
def insomnia_auth_basic() -> Path:
    """Return path to Insomnia basic auth fixture."""
    return COLLECTIONS_DIR / "insomnia" / "auth" / "basic-auth.json"


@pytest.fixture
def insomnia_body_json() -> Path:
    """Return path to Insomnia JSON body fixture."""
    return COLLECTIONS_DIR / "insomnia" / "body-types" / "json-body.json"


@pytest.fixture
def insomnia_body_form() -> Path:
    """Return path to Insomnia form body fixture."""
    return COLLECTIONS_DIR / "insomnia" / "body-types" / "form-body.json"


@pytest.fixture
def insomnia_body_raw() -> Path:
    """Return path to Insomnia raw body fixture."""
    return COLLECTIONS_DIR / "insomnia" / "body-types" / "raw-body.json"


@pytest.fixture
def insomnia_nested_folders() -> Path:
    """Return path to Insomnia nested folders fixture."""
    return COLLECTIONS_DIR / "insomnia" / "nested-folders" / "export.json"


@pytest.fixture
def insomnia_unicode() -> Path:
    """Return path to Insomnia unicode content fixture."""
    return COLLECTIONS_DIR / "insomnia" / "edge-cases" / "unicode-content.json"


@pytest.fixture
def insomnia_empty_collection() -> Path:
    """Return path to Insomnia empty collection fixture."""
    return COLLECTIONS_DIR / "insomnia" / "edge-cases" / "empty-collection.json"


@pytest.fixture
def insomnia_missing_fields() -> Path:
    """Return path to Insomnia missing fields fixture."""
    return COLLECTIONS_DIR / "insomnia" / "edge-cases" / "missing-fields.json"


@pytest.fixture
def insomnia_all_methods() -> Path:
    """Return path to Insomnia all HTTP methods fixture."""
    return COLLECTIONS_DIR / "insomnia" / "edge-cases" / "all-methods.json"


@pytest.fixture
def insomnia_real_world_jsonplaceholder() -> Path:
    """Return path to JSONPlaceholder Insomnia collection."""
    return COLLECTIONS_DIR / "insomnia" / "real-world" / "jsonplaceholder" / "export.json"


@pytest.fixture
def insomnia_empty_resources() -> Path:
    """Return path to Insomnia empty resources fixture."""
    return COLLECTIONS_DIR / "insomnia" / "edge-cases" / "empty-resources.json"


@pytest.fixture
def insomnia_no_workspace() -> Path:
    """Return path to Insomnia no workspace fixture."""
    return COLLECTIONS_DIR / "insomnia" / "edge-cases" / "no-workspace.json"


@pytest.fixture
def insomnia_malformed_request() -> Path:
    """Return path to Insomnia malformed request fixture."""
    return COLLECTIONS_DIR / "insomnia" / "edge-cases" / "malformed-request.json"


@pytest.fixture
def insomnia_disabled_headers() -> Path:
    """Return path to Insomnia disabled headers fixture."""
    return COLLECTIONS_DIR / "insomnia" / "edge-cases" / "disabled-headers.json"


@pytest.fixture
def insomnia_body_edge_cases() -> Path:
    """Return path to Insomnia body edge cases fixture."""
    return COLLECTIONS_DIR / "insomnia" / "edge-cases" / "body-edge-cases.json"


@pytest.fixture
def insomnia_auth_edge_cases() -> Path:
    """Return path to Insomnia auth edge cases fixture."""
    return COLLECTIONS_DIR / "insomnia" / "edge-cases" / "auth-edge-cases.json"


@pytest.fixture
def insomnia_orphaned_requests() -> Path:
    """Return path to Insomnia orphaned requests fixture."""
    return COLLECTIONS_DIR / "insomnia" / "edge-cases" / "orphaned-requests.json"


@pytest.fixture
def insomnia_post_script_correlations() -> Path:
    """Return path to Insomnia post-script correlations fixture."""
    return COLLECTIONS_DIR / "insomnia" / "edge-cases" / "post-script-correlations.json"


@pytest.fixture
def insomnia_env_plain() -> Path:
    """Return path to plain JSON environment file."""
    return COLLECTIONS_DIR / "insomnia" / "edge-cases" / "env-plain.json"


@pytest.fixture
def insomnia_env_insomnia_export() -> Path:
    """Return path to Insomnia export format environment file."""
    return COLLECTIONS_DIR / "insomnia" / "edge-cases" / "env-insomnia-export.json"


@pytest.fixture
def insomnia_env_invalid() -> Path:
    """Return path to invalid JSON environment file."""
    return COLLECTIONS_DIR / "insomnia" / "edge-cases" / "env-invalid.json"


# Postman Importer fixtures


@pytest.fixture
def postman_importer() -> PostmanImporter:
    """Return a fresh PostmanImporter instance."""
    return PostmanImporter()


@pytest.fixture
def postman_basic_collection() -> Path:
    """Return path to basic Postman collection."""
    return COLLECTIONS_DIR / "postman" / "basic" / "collection.json"


@pytest.fixture
def postman_auth_bearer() -> Path:
    """Return path to Postman bearer auth fixture."""
    return COLLECTIONS_DIR / "postman" / "auth" / "bearer-auth.json"


@pytest.fixture
def postman_auth_basic() -> Path:
    """Return path to Postman basic auth fixture."""
    return COLLECTIONS_DIR / "postman" / "auth" / "basic-auth.json"


@pytest.fixture
def postman_body_json() -> Path:
    """Return path to Postman JSON body fixture."""
    return COLLECTIONS_DIR / "postman" / "body-types" / "json-body.json"


@pytest.fixture
def postman_body_form() -> Path:
    """Return path to Postman form body fixture."""
    return COLLECTIONS_DIR / "postman" / "body-types" / "form-body.json"


@pytest.fixture
def postman_nested_folders() -> Path:
    """Return path to Postman nested folders fixture."""
    return COLLECTIONS_DIR / "postman" / "nested-folders" / "collection.json"


@pytest.fixture
def postman_empty_collection() -> Path:
    """Return path to Postman empty collection fixture."""
    return COLLECTIONS_DIR / "postman" / "edge-cases" / "empty-collection.json"


@pytest.fixture
def postman_all_methods() -> Path:
    """Return path to Postman all HTTP methods fixture."""
    return COLLECTIONS_DIR / "postman" / "edge-cases" / "all-methods.json"


@pytest.fixture
def postman_url_formats() -> Path:
    """Return path to Postman URL formats fixture."""
    return COLLECTIONS_DIR / "postman" / "edge-cases" / "url-formats.json"


@pytest.fixture
def postman_real_world_jsonplaceholder() -> Path:
    """Return path to JSONPlaceholder Postman collection."""
    return COLLECTIONS_DIR / "postman" / "real-world" / "jsonplaceholder.json"


@pytest.fixture
def postman_env_disabled_vars() -> Path:
    """Return path to Postman environment with disabled vars fixture."""
    return COLLECTIONS_DIR / "postman" / "edge-cases" / "environment-disabled-vars.json"


@pytest.fixture
def postman_env_invalid() -> Path:
    """Return path to invalid Postman environment fixture."""
    return COLLECTIONS_DIR / "postman" / "edge-cases" / "environment-invalid.json"


@pytest.fixture
def postman_unrecognized_schema() -> Path:
    """Return path to Postman unrecognized schema fixture."""
    return COLLECTIONS_DIR / "postman" / "edge-cases" / "unrecognized-schema.json"


@pytest.fixture
def postman_malformed_request() -> Path:
    """Return path to Postman malformed request fixture."""
    return COLLECTIONS_DIR / "postman" / "edge-cases" / "malformed-request.json"


@pytest.fixture
def postman_url_edge_cases() -> Path:
    """Return path to Postman URL edge cases fixture."""
    return COLLECTIONS_DIR / "postman" / "edge-cases" / "url-edge-cases.json"


@pytest.fixture
def postman_header_edge_cases() -> Path:
    """Return path to Postman header edge cases fixture."""
    return COLLECTIONS_DIR / "postman" / "edge-cases" / "header-edge-cases.json"


@pytest.fixture
def postman_body_edge_cases() -> Path:
    """Return path to Postman body edge cases fixture."""
    return COLLECTIONS_DIR / "postman" / "edge-cases" / "body-edge-cases.json"


@pytest.fixture
def postman_auth_edge_cases() -> Path:
    """Return path to Postman auth edge cases fixture."""
    return COLLECTIONS_DIR / "postman" / "edge-cases" / "auth-edge-cases.json"


@pytest.fixture
def postman_script_edge_cases() -> Path:
    """Return path to Postman script edge cases fixture."""
    return COLLECTIONS_DIR / "postman" / "edge-cases" / "script-edge-cases.json"


@pytest.fixture
def postman_variable_edge_cases() -> Path:
    """Return path to Postman variable edge cases fixture."""
    return COLLECTIONS_DIR / "postman" / "edge-cases" / "variable-edge-cases.json"


@pytest.fixture
def postman_generic_exception() -> Path:
    """Return path to Postman generic exception fixture."""
    return COLLECTIONS_DIR / "postman" / "edge-cases" / "generic-exception.json"
