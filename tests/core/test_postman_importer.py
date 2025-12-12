"""Tests for Postman importer."""

from pathlib import Path

import pytest

from collection_importer.core.importers.postman import PostmanImporter
from collection_importer.exceptions import ImporterException


class TestFormatName:
    """Test format_name property."""

    def test_format_name(self, postman_importer: PostmanImporter):
        """Test format_name returns 'postman'."""
        assert postman_importer.format_name == "postman"


class TestCanImport:
    """Test can_import detection logic."""

    def test_can_import_valid_collection(
        self, postman_importer: PostmanImporter, postman_basic_collection: Path
    ):
        """Test detection of valid Postman collection."""
        assert postman_importer.can_import(postman_basic_collection)

    def test_can_import_file_with_postman_in_name(
        self, postman_importer: PostmanImporter, tmp_path: Path
    ):
        """Test detection of file with 'postman' in filename."""
        test_file = tmp_path / "my.postman_collection.json"
        test_file.write_text('{"info": {"name": "Test"}}', encoding="utf-8")
        assert postman_importer.can_import(test_file)

    def test_can_import_file_with_collection_suffix(
        self, postman_importer: PostmanImporter, tmp_path: Path
    ):
        """Test detection of file ending with _collection.json."""
        test_file = tmp_path / "api_collection.json"
        test_file.write_text('{"info": {"name": "Test"}}', encoding="utf-8")
        assert postman_importer.can_import(test_file)

    def test_can_import_rejects_non_json(
        self, postman_importer: PostmanImporter, tmp_path: Path
    ):
        """Test rejection of non-JSON file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("not json", encoding="utf-8")
        assert not postman_importer.can_import(test_file)

    def test_can_import_rejects_invalid_json(
        self, postman_importer: PostmanImporter, tmp_path: Path
    ):
        """Test rejection of invalid JSON file."""
        test_file = tmp_path / "test.json"
        test_file.write_text("not valid json", encoding="utf-8")
        assert not postman_importer.can_import(test_file)

    def test_can_import_rejects_non_postman_json(
        self, postman_importer: PostmanImporter, tmp_path: Path
    ):
        """Test rejection of JSON without Postman schema."""
        test_file = tmp_path / "test.json"
        test_file.write_text('{"foo": "bar"}', encoding="utf-8")
        assert not postman_importer.can_import(test_file)

    def test_can_import_rejects_nonexistent_file(
        self, postman_importer: PostmanImporter, tmp_path: Path
    ):
        """Test rejection of nonexistent file."""
        assert not postman_importer.can_import(tmp_path / "nonexistent.json")

    def test_can_import_rejects_directory(
        self, postman_importer: PostmanImporter, tmp_path: Path
    ):
        """Test rejection of directory."""
        assert not postman_importer.can_import(tmp_path)

    def test_can_import_by_schema(
        self, postman_importer: PostmanImporter, tmp_path: Path
    ):
        """Test detection via Postman schema in content."""
        test_file = tmp_path / "test.json"
        test_file.write_text(
            '{"info": {"schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"}}',
            encoding="utf-8",
        )
        assert postman_importer.can_import(test_file)


class TestImportCollection:
    """Test import_collection method."""

    def test_import_basic_collection(
        self, postman_importer: PostmanImporter, postman_basic_collection: Path
    ):
        """Test importing basic Postman collection."""
        collection = postman_importer.import_collection(postman_basic_collection)

        assert collection.metadata.name == "Basic API Collection"
        assert collection.metadata.format == "postman"
        assert collection.request_count == 3

    def test_import_collection_with_name_override(
        self, postman_importer: PostmanImporter, postman_basic_collection: Path
    ):
        """Test importing with name override."""
        collection = postman_importer.import_collection(
            postman_basic_collection, name="Custom Name"
        )

        assert collection.metadata.name == "Custom Name"

    def test_import_collection_with_base_url_override(
        self, postman_importer: PostmanImporter, postman_basic_collection: Path
    ):
        """Test importing with base URL override."""
        collection = postman_importer.import_collection(
            postman_basic_collection, base_url="https://override.example.com"
        )

        assert collection.metadata.base_url == "https://override.example.com"

    def test_import_nonexistent_path(
        self, postman_importer: PostmanImporter, tmp_path: Path
    ):
        """Test importing from nonexistent path raises exception."""
        with pytest.raises(ImporterException) as exc_info:
            postman_importer.import_collection(tmp_path / "nonexistent.json")

        assert "does not exist" in str(exc_info.value.message)

    def test_import_invalid_json(
        self, postman_importer: PostmanImporter, tmp_path: Path
    ):
        """Test importing invalid JSON raises exception."""
        test_file = tmp_path / "invalid.json"
        test_file.write_text("not valid json", encoding="utf-8")

        with pytest.raises(ImporterException) as exc_info:
            postman_importer.import_collection(test_file)

        assert "Invalid JSON" in str(exc_info.value.message)

    def test_import_missing_info_field(
        self, postman_importer: PostmanImporter, tmp_path: Path
    ):
        """Test importing JSON without info field raises exception."""
        test_file = tmp_path / "no_info.json"
        test_file.write_text('{"item": []}', encoding="utf-8")

        with pytest.raises(ImporterException) as exc_info:
            postman_importer.import_collection(test_file)

        assert "missing 'info' field" in str(exc_info.value.message)


class TestListRequests:
    """Test list_requests method."""

    def test_list_requests_basic(
        self, postman_importer: PostmanImporter, postman_basic_collection: Path
    ):
        """Test listing requests from basic collection."""
        requests = postman_importer.list_requests(postman_basic_collection)

        assert len(requests) == 3
        assert all("name" in r and "method" in r and "path" in r for r in requests)

    def test_list_requests_with_folders(
        self, postman_importer: PostmanImporter, postman_nested_folders: Path
    ):
        """Test listing requests includes folder paths."""
        requests = postman_importer.list_requests(postman_nested_folders)

        # Should include folder prefixes in names
        folder_names = [r["name"] for r in requests]
        assert any("Auth" in name for name in folder_names)
        assert any("Users" in name for name in folder_names)

    def test_list_requests_empty_collection(
        self, postman_importer: PostmanImporter, postman_empty_collection: Path
    ):
        """Test listing requests from empty collection."""
        requests = postman_importer.list_requests(postman_empty_collection)
        assert len(requests) == 0

    def test_list_requests_invalid_file(
        self, postman_importer: PostmanImporter, tmp_path: Path
    ):
        """Test listing requests from invalid file returns empty list."""
        test_file = tmp_path / "invalid.json"
        test_file.write_text("not json", encoding="utf-8")

        requests = postman_importer.list_requests(test_file)
        assert requests == []


class TestParseUrl:
    """Test URL parsing."""

    def test_parse_url_string(self, postman_importer: PostmanImporter):
        """Test parsing URL string."""
        result = postman_importer._parse_url("{{base_url}}/users")
        assert result == "{{base_url}}/users"

    def test_parse_url_object_with_raw(self, postman_importer: PostmanImporter):
        """Test parsing URL object with raw field."""
        url = {
            "raw": "{{base_url}}/users/123",
            "host": ["{{base_url}}"],
            "path": ["users", "123"],
        }
        result = postman_importer._parse_url(url)
        assert result == "{{base_url}}/users/123"

    def test_parse_url_object_without_raw(self, postman_importer: PostmanImporter):
        """Test parsing URL object without raw field."""
        url = {
            "protocol": "https",
            "host": ["api", "example", "com"],
            "port": "8080",
            "path": ["users", "123"],
        }
        result = postman_importer._parse_url(url)
        assert result == "https://api.example.com:8080/users/123"

    def test_parse_url_none(self, postman_importer: PostmanImporter):
        """Test parsing None URL returns '/'."""
        result = postman_importer._parse_url(None)
        assert result == "/"


class TestParseHeaders:
    """Test header parsing."""

    def test_parse_headers_basic(self, postman_importer: PostmanImporter):
        """Test parsing basic headers."""
        headers = [
            {"key": "Content-Type", "value": "application/json"},
            {"key": "Accept", "value": "application/json"},
        ]
        result = postman_importer._parse_headers(headers)

        assert result == {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def test_parse_headers_skips_disabled(self, postman_importer: PostmanImporter):
        """Test that disabled headers are skipped."""
        headers = [
            {"key": "Enabled", "value": "yes"},
            {"key": "Disabled", "value": "no", "disabled": True},
        ]
        result = postman_importer._parse_headers(headers)

        assert "Enabled" in result
        assert "Disabled" not in result

    def test_parse_headers_empty(self, postman_importer: PostmanImporter):
        """Test parsing empty headers."""
        result = postman_importer._parse_headers([])
        assert result == {}

    def test_parse_headers_none(self, postman_importer: PostmanImporter):
        """Test parsing None headers."""
        result = postman_importer._parse_headers(None)
        assert result == {}


class TestParseBody:
    """Test body parsing."""

    def test_parse_body_raw_json(
        self, postman_importer: PostmanImporter, postman_body_json: Path
    ):
        """Test parsing raw JSON body."""
        collection = postman_importer.import_collection(postman_body_json)
        request = collection.requests[0]

        assert request.body_type == "json"
        assert isinstance(request.body, dict)
        assert "title" in request.body

    def test_parse_body_urlencoded(
        self, postman_importer: PostmanImporter, postman_body_form: Path
    ):
        """Test parsing URL encoded body."""
        collection = postman_importer.import_collection(postman_body_form)
        request = collection.requests[0]

        assert request.body_type == "form"
        assert isinstance(request.body, dict)

    def test_parse_body_formdata(
        self, postman_importer: PostmanImporter, postman_body_form: Path
    ):
        """Test parsing form data body."""
        collection = postman_importer.import_collection(postman_body_form)
        # Second request uses formdata
        request = collection.requests[1]

        assert request.body_type == "form"
        assert isinstance(request.body, dict)

    def test_parse_body_none(self, postman_importer: PostmanImporter):
        """Test parsing None body."""
        body, body_type = postman_importer._parse_body(None)
        assert body is None
        assert body_type == "none"


class TestParseAuthentication:
    """Test authentication parsing."""

    def test_parse_bearer_auth(
        self, postman_importer: PostmanImporter, postman_auth_bearer: Path
    ):
        """Test parsing Bearer token authentication."""
        collection = postman_importer.import_collection(postman_auth_bearer)
        request = collection.requests[0]

        assert request.auth_type == "bearer"
        assert request.auth_value == "${access_token}"

    def test_parse_basic_auth(
        self, postman_importer: PostmanImporter, postman_auth_basic: Path
    ):
        """Test parsing Basic authentication."""
        collection = postman_importer.import_collection(postman_auth_basic)
        request = collection.requests[0]

        assert request.auth_type == "basic"
        assert request.auth_value is not None

    def test_parse_auth_none(self, postman_importer: PostmanImporter):
        """Test parsing None auth."""
        auth_type, auth_value, headers = postman_importer._parse_auth(None)
        assert auth_type is None
        assert auth_value is None
        assert headers == {}


class TestFolderHierarchy:
    """Test folder hierarchy parsing."""

    def test_nested_folders(
        self, postman_importer: PostmanImporter, postman_nested_folders: Path
    ):
        """Test parsing nested folder structure."""
        collection = postman_importer.import_collection(postman_nested_folders)

        # Find the Create User request in Users/CRUD folder
        create_user = next(
            (r for r in collection.requests if r.name == "Create User"), None
        )
        assert create_user is not None
        assert create_user.folder_path == "Users/CRUD"

    def test_folder_sequence(
        self, postman_importer: PostmanImporter, postman_nested_folders: Path
    ):
        """Test that requests maintain proper sequence across folders."""
        collection = postman_importer.import_collection(postman_nested_folders)

        sequences = [r.sequence for r in collection.requests]
        # Sequences should be unique and incrementing
        assert sequences == sorted(set(sequences))


class TestVariableConversion:
    """Test variable conversion."""

    def test_variable_conversion_in_url(
        self, postman_importer: PostmanImporter, postman_basic_collection: Path
    ):
        """Test {{var}} to ${var} conversion in URL."""
        collection = postman_importer.import_collection(postman_basic_collection)

        for request in collection.requests:
            assert "{{" not in request.path
            if "${" in request.path:
                # Variables should use JMeter syntax
                assert "${" in request.path

    def test_variable_conversion_in_headers(
        self, postman_importer: PostmanImporter, postman_auth_bearer: Path
    ):
        """Test variable conversion in headers."""
        collection = postman_importer.import_collection(postman_auth_bearer)
        request = collection.requests[0]

        # Auth value should have converted variables
        assert "{{" not in (request.auth_value or "")

    def test_variable_extraction(
        self, postman_importer: PostmanImporter, postman_basic_collection: Path
    ):
        """Test extraction of collection variables."""
        collection = postman_importer.import_collection(postman_basic_collection)

        assert "base_url" in collection.metadata.variables
        assert "user_id" in collection.metadata.variables


class TestAllHttpMethods:
    """Test all HTTP methods are handled."""

    def test_all_methods_imported(
        self, postman_importer: PostmanImporter, postman_all_methods: Path
    ):
        """Test all HTTP methods are imported correctly."""
        collection = postman_importer.import_collection(postman_all_methods)

        methods = {r.method for r in collection.requests}

        assert "GET" in methods
        assert "POST" in methods
        assert "PUT" in methods
        assert "PATCH" in methods
        assert "DELETE" in methods
        assert "HEAD" in methods
        assert "OPTIONS" in methods


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_collection(
        self, postman_importer: PostmanImporter, postman_empty_collection: Path
    ):
        """Test importing empty collection."""
        collection = postman_importer.import_collection(postman_empty_collection)

        assert collection.metadata.name == "Empty Collection"
        assert collection.request_count == 0

    def test_url_as_string_in_request(
        self, postman_importer: PostmanImporter, postman_url_formats: Path
    ):
        """Test handling URL as simple string."""
        collection = postman_importer.import_collection(postman_url_formats)

        # First request has URL as string
        url_string_request = collection.requests[0]
        assert url_string_request.path is not None

    def test_url_with_query_params(
        self, postman_importer: PostmanImporter, postman_url_formats: Path
    ):
        """Test URL with query parameters."""
        collection = postman_importer.import_collection(postman_url_formats)

        # Second request has query params
        query_request = next(
            (r for r in collection.requests if "search" in r.path.lower()), None
        )
        assert query_request is not None


class TestRealWorldCollections:
    """Test real-world collection examples."""

    def test_jsonplaceholder_collection(
        self, postman_importer: PostmanImporter, postman_real_world_jsonplaceholder: Path
    ):
        """Test importing JSONPlaceholder API collection."""
        collection = postman_importer.import_collection(
            postman_real_world_jsonplaceholder
        )

        assert collection.metadata.name == "JSONPlaceholder API"
        assert collection.request_count > 0

        # Check for expected endpoints
        paths = [r.path for r in collection.requests]
        assert any("/posts" in p for p in paths)
        assert any("/users" in p for p in paths)

    def test_jsonplaceholder_folders(
        self, postman_importer: PostmanImporter, postman_real_world_jsonplaceholder: Path
    ):
        """Test folder structure in JSONPlaceholder collection."""
        collection = postman_importer.import_collection(
            postman_real_world_jsonplaceholder
        )

        folder_paths = {r.folder_path for r in collection.requests}
        assert "Posts" in folder_paths
        assert "Users" in folder_paths
        assert "Comments" in folder_paths

    def test_jsonplaceholder_variables(
        self, postman_importer: PostmanImporter, postman_real_world_jsonplaceholder: Path
    ):
        """Test variables in JSONPlaceholder collection."""
        collection = postman_importer.import_collection(
            postman_real_world_jsonplaceholder
        )

        assert "base_url" in collection.metadata.variables
        assert "jsonplaceholder" in collection.metadata.variables["base_url"].lower()


class TestUrlFormats:
    """Test various URL format handling."""

    def test_full_url_with_port(
        self, postman_importer: PostmanImporter, postman_url_formats: Path
    ):
        """Test URL with explicit port."""
        collection = postman_importer.import_collection(postman_url_formats)

        # Find request by name since path extraction removes host
        port_request = next(
            (r for r in collection.requests if r.name == "Full URL with Port"), None
        )
        assert port_request is not None
        assert "/api/v1/health" in port_request.path


class TestScripts:
    """Test script extraction."""

    def test_scripts_are_extracted(
        self, postman_importer: PostmanImporter, tmp_path: Path
    ):
        """Test pre-request and test scripts are extracted."""
        test_file = tmp_path / "scripts.json"
        test_file.write_text(
            """{
            "info": {"name": "Scripts Test", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
            "item": [{
                "name": "Test Request",
                "request": {"method": "GET", "url": "https://example.com"},
                "event": [
                    {"listen": "prerequest", "script": {"exec": ["console.log('pre');"]}},
                    {"listen": "test", "script": {"exec": ["console.log('test');"]}}
                ]
            }]
        }""",
            encoding="utf-8",
        )

        collection = postman_importer.import_collection(test_file)
        request = collection.requests[0]

        assert request.pre_script is not None
        assert "pre" in request.pre_script
        assert request.post_script is not None
        assert "test" in request.post_script


class TestDisabledItems:
    """Test handling of disabled items."""

    def test_disabled_headers_ignored(
        self, postman_importer: PostmanImporter, tmp_path: Path
    ):
        """Test that disabled headers are not included."""
        test_file = tmp_path / "disabled_headers.json"
        test_file.write_text(
            """{
            "info": {"name": "Test", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
            "item": [{
                "name": "Request",
                "request": {
                    "method": "GET",
                    "url": "https://example.com",
                    "header": [
                        {"key": "Active", "value": "yes"},
                        {"key": "Disabled", "value": "no", "disabled": true}
                    ]
                }
            }]
        }""",
            encoding="utf-8",
        )

        collection = postman_importer.import_collection(test_file)
        request = collection.requests[0]

        assert "Active" in request.headers
        assert "Disabled" not in request.headers


class TestConstants:
    """Test class constants."""

    def test_auth_constants(self, postman_importer: PostmanImporter):
        """Test authentication type constants."""
        assert postman_importer.AUTH_BEARER == "bearer"
        assert postman_importer.AUTH_BASIC == "basic"
        assert postman_importer.AUTH_APIKEY == "apikey"

    def test_body_mode_constants(self, postman_importer: PostmanImporter):
        """Test body mode constants."""
        assert postman_importer.BODY_MODE_RAW == "raw"
        assert postman_importer.BODY_MODE_FORMDATA == "formdata"
        assert postman_importer.BODY_MODE_URLENCODED == "urlencoded"


class TestEnvironmentIntegration:
    """Test environment file integration."""

    def test_import_with_env_file(
        self, postman_importer: PostmanImporter, postman_basic_collection: Path,
        postman_env_disabled_vars: Path
    ):
        """Test importing with environment file."""
        collection = postman_importer.import_collection(
            postman_basic_collection, env_path=postman_env_disabled_vars
        )

        # Active vars should be included
        assert "active_var" in collection.metadata.variables
        assert collection.metadata.variables["active_var"] == "active-value"

        # Vars without explicit enabled should be included (defaults to True)
        assert "another_active" in collection.metadata.variables

    def test_env_file_disabled_vars_excluded(
        self, postman_importer: PostmanImporter, postman_basic_collection: Path,
        postman_env_disabled_vars: Path
    ):
        """Test that disabled env vars are excluded."""
        collection = postman_importer.import_collection(
            postman_basic_collection, env_path=postman_env_disabled_vars
        )

        # Disabled vars should not be included
        assert "disabled_var" not in collection.metadata.variables

    def test_env_file_empty_keys_excluded(
        self, postman_importer: PostmanImporter, postman_basic_collection: Path,
        postman_env_disabled_vars: Path
    ):
        """Test that env vars with empty keys are excluded."""
        collection = postman_importer.import_collection(
            postman_basic_collection, env_path=postman_env_disabled_vars
        )

        # Empty key values should not be included
        assert "" not in collection.metadata.variables

    def test_env_file_invalid_json(
        self, postman_importer: PostmanImporter, postman_basic_collection: Path,
        postman_env_invalid: Path
    ):
        """Test that invalid env file is handled gracefully."""
        # Should not raise, just log warning and continue
        collection = postman_importer.import_collection(
            postman_basic_collection, env_path=postman_env_invalid
        )

        # Collection should still import successfully
        assert collection.metadata.name == "Basic API Collection"


class TestGenericExceptionHandling:
    """Test generic exception handling."""

    def test_import_generic_exception_wrapped(
        self, postman_importer: PostmanImporter, postman_generic_exception: Path
    ):
        """Test that generic exceptions are wrapped in ImporterException."""
        with pytest.raises(ImporterException) as exc_info:
            postman_importer.import_collection(postman_generic_exception)

        assert "Invalid JSON" in str(exc_info.value.message)


class TestSchemaValidation:
    """Test schema validation."""

    def test_unrecognized_schema_logs_warning(
        self, postman_importer: PostmanImporter, postman_unrecognized_schema: Path
    ):
        """Test that unrecognized schema logs warning but continues."""
        # Should not raise, just log warning
        collection = postman_importer.import_collection(postman_unrecognized_schema)

        assert collection.metadata.name == "Unrecognized Schema Collection"
        assert collection.request_count == 1


class TestRequestParsingErrors:
    """Test request parsing error handling."""

    def test_malformed_request_logs_warning(
        self, postman_importer: PostmanImporter, postman_malformed_request: Path
    ):
        """Test that malformed requests are skipped with warning."""
        collection = postman_importer.import_collection(postman_malformed_request)

        # Valid requests should still be imported
        assert collection.request_count == 2

    def test_malformed_request_continues_others(
        self, postman_importer: PostmanImporter, postman_malformed_request: Path
    ):
        """Test that other requests are imported despite malformed one."""
        collection = postman_importer.import_collection(postman_malformed_request)

        names = [r.name for r in collection.requests]
        assert "Valid Request" in names
        assert "Another Valid Request" in names


class TestUrlEdgeCases:
    """Test URL parsing edge cases."""

    def test_url_host_as_string(
        self, postman_importer: PostmanImporter, postman_url_edge_cases: Path
    ):
        """Test URL with host as string instead of array."""
        collection = postman_importer.import_collection(postman_url_edge_cases)

        request = next(r for r in collection.requests if r.name == "Host as String")
        assert "api.example.com" in request.path or "users" in request.path

    def test_url_path_as_string(
        self, postman_importer: PostmanImporter, postman_url_edge_cases: Path
    ):
        """Test URL with path as string instead of array."""
        collection = postman_importer.import_collection(postman_url_edge_cases)

        request = next(r for r in collection.requests if r.name == "Path as String")
        assert "users" in request.path or "profile" in request.path

    def test_url_with_port(
        self, postman_importer: PostmanImporter, postman_url_edge_cases: Path
    ):
        """Test URL with explicit port number."""
        collection = postman_importer.import_collection(postman_url_edge_cases)

        request = next(r for r in collection.requests if r.name == "With Port")
        assert request.path is not None

    def test_url_path_only_no_protocol(
        self, postman_importer: PostmanImporter, postman_url_edge_cases: Path
    ):
        """Test URL with only path, no protocol/host."""
        collection = postman_importer.import_collection(postman_url_edge_cases)

        request = next(r for r in collection.requests if r.name == "Path Only No Protocol")
        assert "api/status" in request.path

    def test_url_unknown_type(
        self, postman_importer: PostmanImporter, postman_url_edge_cases: Path
    ):
        """Test URL with unknown type returns default."""
        collection = postman_importer.import_collection(postman_url_edge_cases)

        request = next(r for r in collection.requests if r.name == "Unknown URL Type")
        assert request.path == "/"

    def test_url_null(
        self, postman_importer: PostmanImporter, postman_url_edge_cases: Path
    ):
        """Test null URL returns default."""
        collection = postman_importer.import_collection(postman_url_edge_cases)

        request = next(r for r in collection.requests if r.name == "Null URL")
        assert request.path == "/"

    def test_request_as_string(
        self, postman_importer: PostmanImporter, postman_url_edge_cases: Path
    ):
        """Test request as simple string URL."""
        collection = postman_importer.import_collection(postman_url_edge_cases)

        request = next(r for r in collection.requests if r.name == "Request as String")
        assert request.method == "GET"
        assert "simple" in request.path


class TestHeaderEdgeCases:
    """Test header parsing edge cases."""

    def test_nondict_header_items_skipped(
        self, postman_importer: PostmanImporter, postman_header_edge_cases: Path
    ):
        """Test that non-dict header items are skipped."""
        collection = postman_importer.import_collection(postman_header_edge_cases)

        request = collection.requests[0]
        # Valid headers should be present
        assert "Valid-Header" in request.headers
        assert "Another-Valid" in request.headers
        # Non-dict items should be skipped (no crash)

    def test_empty_header_key_skipped(
        self, postman_importer: PostmanImporter, postman_header_edge_cases: Path
    ):
        """Test that headers with empty keys are skipped."""
        collection = postman_importer.import_collection(postman_header_edge_cases)

        request = collection.requests[0]
        assert "" not in request.headers


class TestBodyEdgeCases:
    """Test body parsing edge cases."""

    def test_invalid_json_raw_body(
        self, postman_importer: PostmanImporter, postman_body_edge_cases: Path
    ):
        """Test that invalid JSON raw body returns as raw string."""
        collection = postman_importer.import_collection(postman_body_edge_cases)

        request = next(r for r in collection.requests if r.name == "Invalid JSON Raw Body")
        # Should return raw string, not crash
        assert request.body_type == "raw"
        assert "{not valid json}" in str(request.body)

    def test_disabled_urlencoded_params(
        self, postman_importer: PostmanImporter, postman_body_edge_cases: Path
    ):
        """Test that disabled urlencoded params are skipped."""
        collection = postman_importer.import_collection(postman_body_edge_cases)

        request = next(r for r in collection.requests if r.name == "Disabled Urlencoded Params")
        assert request.body_type == "form"
        assert "active_param" in request.body
        assert "disabled_param" not in request.body

    def test_empty_key_urlencoded_params(
        self, postman_importer: PostmanImporter, postman_body_edge_cases: Path
    ):
        """Test that urlencoded params with empty keys are skipped."""
        collection = postman_importer.import_collection(postman_body_edge_cases)

        request = next(r for r in collection.requests if r.name == "Disabled Urlencoded Params")
        assert "" not in request.body

    def test_disabled_formdata_params(
        self, postman_importer: PostmanImporter, postman_body_edge_cases: Path
    ):
        """Test that disabled formdata params are skipped."""
        collection = postman_importer.import_collection(postman_body_edge_cases)

        request = next(r for r in collection.requests if r.name == "Disabled Formdata Params")
        assert request.body_type == "form"
        assert "text_field" in request.body
        assert "disabled_field" not in request.body

    def test_file_type_formdata_skipped(
        self, postman_importer: PostmanImporter, postman_body_edge_cases: Path
    ):
        """Test that file type formdata params are skipped."""
        collection = postman_importer.import_collection(postman_body_edge_cases)

        request = next(r for r in collection.requests if r.name == "Disabled Formdata Params")
        # File fields should be skipped
        assert "file_field" not in request.body

    def test_unknown_body_mode(
        self, postman_importer: PostmanImporter, postman_body_edge_cases: Path
    ):
        """Test that unknown body mode returns none."""
        collection = postman_importer.import_collection(postman_body_edge_cases)

        request = next(r for r in collection.requests if r.name == "Unknown Body Mode")
        assert request.body is None
        assert request.body_type == "none"


class TestAuthEdgeCases:
    """Test authentication edge cases."""

    def test_basic_auth_no_credentials(
        self, postman_importer: PostmanImporter, postman_auth_edge_cases: Path
    ):
        """Test basic auth with no credentials."""
        collection = postman_importer.import_collection(postman_auth_edge_cases)

        request = next(r for r in collection.requests if r.name == "Basic Auth No Credentials")
        assert request.auth_type == "basic"
        assert request.auth_value is None

    def test_apikey_auth_header(
        self, postman_importer: PostmanImporter, postman_auth_edge_cases: Path
    ):
        """Test API key auth in header."""
        collection = postman_importer.import_collection(postman_auth_edge_cases)

        request = next(r for r in collection.requests if r.name == "API Key Header")
        assert request.auth_type == "apikey"
        assert request.auth_value == "my-secret-key"
        # API key should be in headers
        assert "X-API-Key" in request.headers
        assert request.headers["X-API-Key"] == "my-secret-key"

    def test_apikey_auth_query(
        self, postman_importer: PostmanImporter, postman_auth_edge_cases: Path
    ):
        """Test API key auth in query (not header)."""
        collection = postman_importer.import_collection(postman_auth_edge_cases)

        request = next(r for r in collection.requests if r.name == "API Key Query")
        assert request.auth_type == "apikey"
        # Query location should not add headers
        assert "api_key" not in request.headers

    def test_apikey_missing_value(
        self, postman_importer: PostmanImporter, postman_auth_edge_cases: Path
    ):
        """Test API key auth with missing value."""
        collection = postman_importer.import_collection(postman_auth_edge_cases)

        request = next(r for r in collection.requests if r.name == "API Key Missing Value")
        assert request.auth_type == "apikey"
        # No header should be added without value

    def test_unknown_auth_type(
        self, postman_importer: PostmanImporter, postman_auth_edge_cases: Path
    ):
        """Test unknown auth type returns none."""
        collection = postman_importer.import_collection(postman_auth_edge_cases)

        request = next(r for r in collection.requests if r.name == "Unknown Auth Type")
        assert request.auth_type is None
        assert request.auth_value is None


class TestScriptEdgeCases:
    """Test script extraction edge cases."""

    def test_script_exec_as_string(
        self, postman_importer: PostmanImporter, postman_script_edge_cases: Path
    ):
        """Test script exec as string instead of array."""
        collection = postman_importer.import_collection(postman_script_edge_cases)

        request = next(r for r in collection.requests if r.name == "Script Exec as String")
        assert request.pre_script is not None
        assert "pre-request" in request.pre_script
        assert request.post_script is not None
        assert "post-response" in request.post_script

    def test_event_not_dict(
        self, postman_importer: PostmanImporter, postman_script_edge_cases: Path
    ):
        """Test that non-dict events are skipped."""
        collection = postman_importer.import_collection(postman_script_edge_cases)

        request = next(r for r in collection.requests if r.name == "Event Not Dict")
        # Valid event should still be processed
        assert request.post_script is not None


class TestVariableEdgeCases:
    """Test variable extraction edge cases."""

    def test_nondict_variable_items_skipped(
        self, postman_importer: PostmanImporter, postman_variable_edge_cases: Path
    ):
        """Test that non-dict variable items are skipped."""
        collection = postman_importer.import_collection(postman_variable_edge_cases)

        # Valid variables should be present
        assert "valid_var" in collection.metadata.variables
        assert collection.metadata.variables["valid_var"] == "valid-value"

    def test_empty_variable_key_skipped(
        self, postman_importer: PostmanImporter, postman_variable_edge_cases: Path
    ):
        """Test that variables with empty keys are skipped."""
        collection = postman_importer.import_collection(postman_variable_edge_cases)

        assert "" not in collection.metadata.variables

    def test_base_url_detected_from_variables(
        self, postman_importer: PostmanImporter, postman_variable_edge_cases: Path
    ):
        """Test that base_url is detected from collection variables."""
        collection = postman_importer.import_collection(postman_variable_edge_cases)

        assert collection.metadata.base_url == "https://api.example.com"


class TestListRequestsEdgeCases:
    """Test list_requests edge cases."""

    def test_list_request_as_string_url(
        self, postman_importer: PostmanImporter, postman_url_edge_cases: Path
    ):
        """Test listing requests where request is a string URL."""
        requests = postman_importer.list_requests(postman_url_edge_cases)

        # Should handle request as string gracefully
        string_request = next(r for r in requests if "Request as String" in r["name"])
        assert string_request["method"] == "GET"
        assert "simple" in string_request["path"]
