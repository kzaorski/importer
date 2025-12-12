"""Tests for InsomniaImporter class."""

import base64
from pathlib import Path

import pytest

from collection_importer.core.importers.insomnia import InsomniaImporter
from collection_importer.exceptions import ImporterException


class TestFormatName:
    """Tests for InsomniaImporter.format_name property."""

    def test_format_name_returns_insomnia(self, insomnia_importer: InsomniaImporter):
        """format_name should return 'insomnia'."""
        assert insomnia_importer.format_name == "insomnia"


class TestCanImport:
    """Tests for InsomniaImporter.can_import() method."""

    def test_can_import_valid_insomnia_export(
        self, insomnia_importer: InsomniaImporter, insomnia_basic_collection: Path
    ):
        """can_import should return True for valid Insomnia export."""
        assert insomnia_importer.can_import(insomnia_basic_collection) is True

    def test_can_import_filename_with_insomnia(
        self, insomnia_importer: InsomniaImporter, tmp_path: Path
    ):
        """can_import should detect files with 'insomnia' in filename."""
        insomnia_file = tmp_path / "my-insomnia-export.json"
        insomnia_file.write_text('{"_type": "export"}')
        assert insomnia_importer.can_import(insomnia_file) is True

    def test_cannot_import_nonexistent_path(self, insomnia_importer: InsomniaImporter):
        """can_import should return False for nonexistent path."""
        assert insomnia_importer.can_import(Path("/nonexistent/path.json")) is False

    def test_cannot_import_directory(
        self, insomnia_importer: InsomniaImporter, tmp_path: Path
    ):
        """can_import should return False for directories."""
        assert insomnia_importer.can_import(tmp_path) is False

    def test_cannot_import_non_json_file(
        self, insomnia_importer: InsomniaImporter, tmp_path: Path
    ):
        """can_import should return False for non-JSON files."""
        text_file = tmp_path / "test.txt"
        text_file.write_text("not json")
        assert insomnia_importer.can_import(text_file) is False

    def test_cannot_import_invalid_json(
        self, insomnia_importer: InsomniaImporter, tmp_path: Path
    ):
        """can_import should return False for invalid JSON."""
        invalid_json = tmp_path / "invalid.json"
        invalid_json.write_text("{not valid json}")
        assert insomnia_importer.can_import(invalid_json) is False

    def test_cannot_import_non_export_json(
        self, insomnia_importer: InsomniaImporter, tmp_path: Path
    ):
        """can_import should return False for JSON without _type: export."""
        regular_json = tmp_path / "regular.json"
        regular_json.write_text('{"name": "test"}')
        assert insomnia_importer.can_import(regular_json) is False

    def test_can_import_export_format_4(
        self, insomnia_importer: InsomniaImporter, tmp_path: Path
    ):
        """can_import should detect v4 export format."""
        export_file = tmp_path / "export.json"
        export_file.write_text('{"_type": "export", "__export_format": 4}')
        assert insomnia_importer.can_import(export_file) is True


class TestImportCollection:
    """Tests for InsomniaImporter.import_collection() method."""

    def test_import_basic_collection(
        self, insomnia_importer: InsomniaImporter, insomnia_basic_collection: Path
    ):
        """import_collection should parse basic collection successfully."""
        result = insomnia_importer.import_collection(insomnia_basic_collection)

        assert result is not None
        assert result.metadata.name == "Test Collection"
        assert result.metadata.format == "insomnia"
        assert len(result.requests) > 0

    def test_import_collection_metadata(
        self, insomnia_importer: InsomniaImporter, insomnia_basic_collection: Path
    ):
        """import_collection should extract metadata correctly."""
        result = insomnia_importer.import_collection(insomnia_basic_collection)

        assert result.metadata.name == "Test Collection"
        assert result.metadata.description == "A test Insomnia collection for unit tests"
        assert str(insomnia_basic_collection) in result.metadata.source_path

    def test_import_collection_name_override(
        self, insomnia_importer: InsomniaImporter, insomnia_basic_collection: Path
    ):
        """import_collection should respect name parameter."""
        result = insomnia_importer.import_collection(
            insomnia_basic_collection, name="Custom Name"
        )
        assert result.metadata.name == "Custom Name"

    def test_import_collection_base_url_override(
        self, insomnia_importer: InsomniaImporter, insomnia_basic_collection: Path
    ):
        """import_collection should respect base_url parameter."""
        result = insomnia_importer.import_collection(
            insomnia_basic_collection, base_url="https://custom.api.com"
        )
        assert result.metadata.base_url == "https://custom.api.com"

    def test_import_collection_environment_variables(
        self, insomnia_importer: InsomniaImporter, insomnia_basic_collection: Path
    ):
        """import_collection should extract environment variables."""
        result = insomnia_importer.import_collection(insomnia_basic_collection)

        assert "base_url" in result.metadata.variables
        assert result.metadata.variables["base_url"] == "https://api.example.com"
        assert "token" in result.metadata.variables

    def test_import_collection_detected_base_url(
        self, insomnia_importer: InsomniaImporter, insomnia_basic_collection: Path
    ):
        """import_collection should detect base_url from environment."""
        result = insomnia_importer.import_collection(insomnia_basic_collection)
        assert result.metadata.base_url == "https://api.example.com"

    def test_import_request_count(
        self, insomnia_importer: InsomniaImporter, insomnia_basic_collection: Path
    ):
        """import_collection should import correct number of requests."""
        result = insomnia_importer.import_collection(insomnia_basic_collection)
        # basic/export.json has 4 requests
        assert len(result.requests) == 4

    def test_import_request_name(
        self, insomnia_importer: InsomniaImporter, insomnia_basic_collection: Path
    ):
        """import_collection should preserve request names."""
        result = insomnia_importer.import_collection(insomnia_basic_collection)
        names = [r.name for r in result.requests]
        assert "Get Users" in names

    def test_import_request_method(
        self, insomnia_importer: InsomniaImporter, insomnia_basic_collection: Path
    ):
        """import_collection should parse HTTP methods correctly."""
        result = insomnia_importer.import_collection(insomnia_basic_collection)

        methods = {r.method for r in result.requests}
        assert "GET" in methods
        assert "POST" in methods

    def test_import_request_path(
        self, insomnia_importer: InsomniaImporter, insomnia_basic_collection: Path
    ):
        """import_collection should extract request paths."""
        result = insomnia_importer.import_collection(insomnia_basic_collection)

        paths = [r.path for r in result.requests]
        assert "/users" in paths

    def test_import_request_headers(
        self, insomnia_importer: InsomniaImporter, insomnia_basic_collection: Path
    ):
        """import_collection should parse request headers."""
        result = insomnia_importer.import_collection(insomnia_basic_collection)

        # Find Create User request
        create_user = next((r for r in result.requests if r.name == "Create User"), None)
        assert create_user is not None
        assert "Content-Type" in create_user.headers
        assert create_user.headers["Content-Type"] == "application/json"

    def test_import_request_folder_path(
        self, insomnia_importer: InsomniaImporter, insomnia_basic_collection: Path
    ):
        """import_collection should assign correct folder paths."""
        result = insomnia_importer.import_collection(insomnia_basic_collection)

        users_requests = [r for r in result.requests if r.folder_path == "Users"]
        assert len(users_requests) > 0

    def test_import_nonexistent_path_raises(
        self, insomnia_importer: InsomniaImporter
    ):
        """import_collection should raise for nonexistent path."""
        with pytest.raises(ImporterException) as exc_info:
            insomnia_importer.import_collection(Path("/nonexistent/path.json"))
        assert "does not exist" in str(exc_info.value)

    def test_import_invalid_json_raises(
        self, insomnia_importer: InsomniaImporter, tmp_path: Path
    ):
        """import_collection should raise for invalid JSON."""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("{invalid json}")

        with pytest.raises(ImporterException) as exc_info:
            insomnia_importer.import_collection(invalid_file)
        assert "Invalid JSON" in str(exc_info.value)

    def test_import_non_export_raises(
        self, insomnia_importer: InsomniaImporter, tmp_path: Path
    ):
        """import_collection should raise for non-export JSON."""
        non_export = tmp_path / "test.json"
        non_export.write_text('{"name": "test"}')

        with pytest.raises(ImporterException) as exc_info:
            insomnia_importer.import_collection(non_export)
        assert "Not a valid Insomnia export" in str(exc_info.value)


class TestListRequests:
    """Tests for InsomniaImporter.list_requests() method."""

    def test_list_requests_returns_list(
        self, insomnia_importer: InsomniaImporter, insomnia_basic_collection: Path
    ):
        """list_requests should return a list."""
        result = insomnia_importer.list_requests(insomnia_basic_collection)
        assert isinstance(result, list)

    def test_list_requests_dict_keys(
        self, insomnia_importer: InsomniaImporter, insomnia_basic_collection: Path
    ):
        """list_requests should return dicts with name, method, path keys."""
        result = insomnia_importer.list_requests(insomnia_basic_collection)
        assert len(result) > 0

        for item in result:
            assert "name" in item
            assert "method" in item
            assert "path" in item

    def test_list_requests_method_uppercase(
        self, insomnia_importer: InsomniaImporter, insomnia_basic_collection: Path
    ):
        """list_requests should return uppercase methods."""
        result = insomnia_importer.list_requests(insomnia_basic_collection)

        for item in result:
            assert item["method"] == item["method"].upper()

    def test_list_requests_includes_folder_prefix(
        self, insomnia_importer: InsomniaImporter, insomnia_basic_collection: Path
    ):
        """list_requests should include folder prefix in names."""
        result = insomnia_importer.list_requests(insomnia_basic_collection)

        # Check for folder/name format
        folder_names = [r["name"] for r in result if "/" in r["name"]]
        assert len(folder_names) > 0

    def test_list_requests_empty_for_nonexistent(
        self, insomnia_importer: InsomniaImporter
    ):
        """list_requests should return empty list for nonexistent path."""
        result = insomnia_importer.list_requests(Path("/nonexistent/path.json"))
        assert result == []

    def test_list_requests_empty_collection(
        self, insomnia_importer: InsomniaImporter, insomnia_empty_collection: Path
    ):
        """list_requests should return empty list for collection with no requests."""
        result = insomnia_importer.list_requests(insomnia_empty_collection)
        assert result == []


class TestParseAuthentication:
    """Tests for authentication parsing."""

    def test_bearer_auth_adds_header(
        self, insomnia_importer: InsomniaImporter, insomnia_auth_bearer: Path
    ):
        """Bearer auth should add Authorization header."""
        result = insomnia_importer.import_collection(insomnia_auth_bearer)

        protected = next((r for r in result.requests if r.name == "Protected Resource"), None)
        assert protected is not None
        assert "Authorization" in protected.headers
        assert protected.headers["Authorization"].startswith("Bearer ")

    def test_bearer_auth_type_set(
        self, insomnia_importer: InsomniaImporter, insomnia_auth_bearer: Path
    ):
        """Bearer auth should set auth_type."""
        result = insomnia_importer.import_collection(insomnia_auth_bearer)

        protected = next((r for r in result.requests if r.name == "Protected Resource"), None)
        assert protected is not None
        assert protected.auth_type == "bearer"

    def test_bearer_auth_variable_conversion(
        self, insomnia_importer: InsomniaImporter, insomnia_auth_bearer: Path
    ):
        """Bearer auth should convert {{var}} to ${var}."""
        result = insomnia_importer.import_collection(insomnia_auth_bearer)

        protected = next((r for r in result.requests if r.name == "Protected Resource"), None)
        assert protected is not None
        assert "${auth_token}" in protected.headers["Authorization"]

    def test_basic_auth_adds_header(
        self, insomnia_importer: InsomniaImporter, insomnia_auth_basic: Path
    ):
        """Basic auth should add Authorization header."""
        result = insomnia_importer.import_collection(insomnia_auth_basic)

        protected = next((r for r in result.requests if r.name == "Basic Protected"), None)
        assert protected is not None
        assert "Authorization" in protected.headers
        assert protected.headers["Authorization"].startswith("Basic ")

    def test_basic_auth_base64_encoding(
        self, insomnia_importer: InsomniaImporter, insomnia_auth_basic: Path
    ):
        """Basic auth should Base64 encode credentials."""
        result = insomnia_importer.import_collection(insomnia_auth_basic)

        static_basic = next((r for r in result.requests if r.name == "Static Basic Auth"), None)
        assert static_basic is not None

        auth_header = static_basic.headers.get("Authorization", "")
        assert auth_header.startswith("Basic ")

        # Decode and verify
        encoded = auth_header.replace("Basic ", "")
        decoded = base64.b64decode(encoded).decode()
        assert decoded == "admin:secret"

    def test_basic_auth_type_set(
        self, insomnia_importer: InsomniaImporter, insomnia_auth_basic: Path
    ):
        """Basic auth should set auth_type."""
        result = insomnia_importer.import_collection(insomnia_auth_basic)

        protected = next((r for r in result.requests if r.name == "Basic Protected"), None)
        assert protected is not None
        assert protected.auth_type == "basic"


class TestParseBody:
    """Tests for body parsing."""

    def test_json_body_parsed_as_dict(
        self, insomnia_importer: InsomniaImporter, insomnia_body_json: Path
    ):
        """JSON body should be parsed as dict."""
        result = insomnia_importer.import_collection(insomnia_body_json)

        simple_json = next((r for r in result.requests if r.name == "Simple JSON"), None)
        assert simple_json is not None
        assert simple_json.body_type == "json"
        assert isinstance(simple_json.body, dict)
        assert simple_json.body["name"] == "John"
        assert simple_json.body["age"] == 30

    def test_json_body_with_variables(
        self, insomnia_importer: InsomniaImporter, insomnia_body_json: Path
    ):
        """JSON body should have variables converted."""
        result = insomnia_importer.import_collection(insomnia_body_json)

        nested_json = next((r for r in result.requests if r.name == "Nested JSON"), None)
        assert nested_json is not None
        assert isinstance(nested_json.body, dict)
        assert nested_json.body["user"]["name"] == "${user_name}"
        assert nested_json.body["user"]["email"] == "${user_email}"

    def test_form_body_urlencoded(
        self, insomnia_importer: InsomniaImporter, insomnia_body_form: Path
    ):
        """URL-encoded form body should be parsed."""
        result = insomnia_importer.import_collection(insomnia_body_form)

        form_req = next((r for r in result.requests if r.name == "URL Encoded Form"), None)
        assert form_req is not None
        assert form_req.body_type == "form"
        assert isinstance(form_req.body, dict)
        assert "username" in form_req.body
        assert "password" in form_req.body

    def test_form_body_variable_conversion(
        self, insomnia_importer: InsomniaImporter, insomnia_body_form: Path
    ):
        """Form body should have variables converted."""
        result = insomnia_importer.import_collection(insomnia_body_form)

        form_req = next((r for r in result.requests if r.name == "URL Encoded Form"), None)
        assert form_req is not None
        assert form_req.body["username"] == "${username}"
        assert form_req.body["password"] == "${password}"

    def test_raw_body_text(
        self, insomnia_importer: InsomniaImporter, insomnia_body_raw: Path
    ):
        """Raw text body should be preserved."""
        result = insomnia_importer.import_collection(insomnia_body_raw)

        plain_text = next((r for r in result.requests if r.name == "Plain Text"), None)
        assert plain_text is not None
        assert plain_text.body_type == "raw"
        assert isinstance(plain_text.body, str)
        assert "plain text content" in plain_text.body

    def test_raw_body_xml(
        self, insomnia_importer: InsomniaImporter, insomnia_body_raw: Path
    ):
        """XML body should be parsed as raw."""
        result = insomnia_importer.import_collection(insomnia_body_raw)

        xml_req = next((r for r in result.requests if r.name == "XML Body"), None)
        assert xml_req is not None
        assert xml_req.body_type == "raw"
        assert "<?xml" in xml_req.body

    def test_no_body(
        self, insomnia_importer: InsomniaImporter, insomnia_body_raw: Path
    ):
        """Request without body should have body_type 'none'."""
        result = insomnia_importer.import_collection(insomnia_body_raw)

        no_body = next((r for r in result.requests if r.name == "No Body"), None)
        assert no_body is not None
        assert no_body.body_type == "none"
        assert no_body.body is None


class TestFolderHierarchy:
    """Tests for folder path resolution."""

    def test_root_level_request(
        self, insomnia_importer: InsomniaImporter, insomnia_nested_folders: Path
    ):
        """Root level requests should have empty folder_path."""
        result = insomnia_importer.import_collection(insomnia_nested_folders)

        root_req = next((r for r in result.requests if r.name == "Root Level Request"), None)
        assert root_req is not None
        assert root_req.folder_path == ""

    def test_single_folder_request(
        self, insomnia_importer: InsomniaImporter, insomnia_basic_collection: Path
    ):
        """Requests in single folder should have folder name in path."""
        result = insomnia_importer.import_collection(insomnia_basic_collection)

        users_req = next((r for r in result.requests if r.name == "Get Users"), None)
        assert users_req is not None
        assert users_req.folder_path == "Users"

    def test_deeply_nested_folders(
        self, insomnia_importer: InsomniaImporter, insomnia_nested_folders: Path
    ):
        """Deeply nested requests should have full folder path."""
        result = insomnia_importer.import_collection(insomnia_nested_folders)

        deep_req = next((r for r in result.requests if r.name == "Deep Request"), None)
        assert deep_req is not None
        assert deep_req.folder_path == "api/v1/users"

    def test_mid_level_folder(
        self, insomnia_importer: InsomniaImporter, insomnia_nested_folders: Path
    ):
        """Mid-level folder requests should have correct path."""
        result = insomnia_importer.import_collection(insomnia_nested_folders)

        v1_req = next((r for r in result.requests if r.name == "V1 Level Request"), None)
        assert v1_req is not None
        assert v1_req.folder_path == "api/v1"


class TestVariableConversion:
    """Tests for {{var}} to ${var} conversion."""

    def test_convert_url_variables(
        self, insomnia_importer: InsomniaImporter, insomnia_basic_collection: Path
    ):
        """URL variables should be converted."""
        result = insomnia_importer.import_collection(insomnia_basic_collection)

        # Get User by ID uses {{user_id}}
        get_user = next((r for r in result.requests if r.name == "Get User by ID"), None)
        assert get_user is not None
        assert "${user_id}" in get_user.path

    def test_convert_body_variables(
        self, insomnia_importer: InsomniaImporter, insomnia_basic_collection: Path
    ):
        """Body variables should be converted."""
        result = insomnia_importer.import_collection(insomnia_basic_collection)

        create_user = next((r for r in result.requests if r.name == "Create User"), None)
        assert create_user is not None
        assert isinstance(create_user.body, dict)
        assert create_user.body["name"] == "${user_name}"
        assert create_user.body["email"] == "${user_email}"


class TestAllHttpMethods:
    """Tests for all HTTP method support."""

    def test_import_all_methods(
        self, insomnia_importer: InsomniaImporter, insomnia_all_methods: Path
    ):
        """All HTTP methods should be imported correctly."""
        result = insomnia_importer.import_collection(insomnia_all_methods)

        methods = {r.method for r in result.requests}
        assert "GET" in methods
        assert "POST" in methods
        assert "PUT" in methods
        assert "PATCH" in methods
        assert "DELETE" in methods
        assert "HEAD" in methods
        assert "OPTIONS" in methods


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_unicode_content(
        self, insomnia_importer: InsomniaImporter, insomnia_unicode: Path
    ):
        """Unicode content should be preserved."""
        result = insomnia_importer.import_collection(insomnia_unicode)

        # Check Polish folder name
        polish_req = next((r for r in result.requests if "Pobierz" in r.name), None)
        assert polish_req is not None
        assert polish_req.folder_path == "Polskie znaki"

        # Check Unicode in body
        assert isinstance(polish_req.body, dict)

    def test_unicode_in_headers(
        self, insomnia_importer: InsomniaImporter, insomnia_unicode: Path
    ):
        """Unicode in headers should be preserved."""
        result = insomnia_importer.import_collection(insomnia_unicode)

        polish_req = next((r for r in result.requests if "Pobierz" in r.name), None)
        assert polish_req is not None
        assert "X-Custom-Header" in polish_req.headers

    def test_missing_optional_fields(
        self, insomnia_importer: InsomniaImporter, insomnia_missing_fields: Path
    ):
        """Missing optional fields should use defaults."""
        result = insomnia_importer.import_collection(insomnia_missing_fields)

        assert result is not None
        assert len(result.requests) == 2

        minimal = next((r for r in result.requests if r.name == "Minimal Request"), None)
        assert minimal is not None
        assert minimal.method == "GET"
        assert minimal.headers == {}

    def test_empty_collection(
        self, insomnia_importer: InsomniaImporter, insomnia_empty_collection: Path
    ):
        """Empty collection should import without errors."""
        result = insomnia_importer.import_collection(insomnia_empty_collection)

        assert result is not None
        assert result.metadata.name == "Empty Collection"
        assert len(result.requests) == 0


class TestRealWorldCollections:
    """Tests using real-world collection fixtures."""

    def test_jsonplaceholder_collection(
        self, insomnia_importer: InsomniaImporter, insomnia_real_world_jsonplaceholder: Path
    ):
        """JSONPlaceholder collection should import correctly."""
        result = insomnia_importer.import_collection(insomnia_real_world_jsonplaceholder)

        assert result.metadata.name == "JSONPlaceholder API"
        assert len(result.requests) > 0

        # Check environment variables
        assert "base_url" in result.metadata.variables
        assert "jsonplaceholder.typicode.com" in result.metadata.variables["base_url"]

    def test_jsonplaceholder_folder_structure(
        self, insomnia_importer: InsomniaImporter, insomnia_real_world_jsonplaceholder: Path
    ):
        """JSONPlaceholder collection should have correct folders."""
        result = insomnia_importer.import_collection(insomnia_real_world_jsonplaceholder)

        folders = {r.folder_path for r in result.requests}
        assert "Posts" in folders
        assert "Users" in folders

    def test_jsonplaceholder_crud_operations(
        self, insomnia_importer: InsomniaImporter, insomnia_real_world_jsonplaceholder: Path
    ):
        """JSONPlaceholder collection should have CRUD operations."""
        result = insomnia_importer.import_collection(insomnia_real_world_jsonplaceholder)

        methods = {r.method for r in result.requests}
        assert "GET" in methods
        assert "POST" in methods
        assert "PUT" in methods
        assert "DELETE" in methods


class TestErrorHandling:
    """Tests for error handling paths."""

    def test_import_empty_resources_raises(
        self, insomnia_importer: InsomniaImporter, insomnia_empty_resources: Path
    ):
        """import_collection should raise for export with empty resources."""
        with pytest.raises(ImporterException) as exc_info:
            insomnia_importer.import_collection(insomnia_empty_resources)
        assert "No resources found" in str(exc_info.value)

    def test_import_no_workspace_raises(
        self, insomnia_importer: InsomniaImporter, insomnia_no_workspace: Path
    ):
        """import_collection should raise for export with no workspace."""
        with pytest.raises(ImporterException) as exc_info:
            insomnia_importer.import_collection(insomnia_no_workspace)
        assert "No workspace resource found" in str(exc_info.value)

    def test_import_malformed_request_continues(
        self, insomnia_importer: InsomniaImporter, insomnia_malformed_request: Path
    ):
        """import_collection should continue when a request fails to parse."""
        # The malformed request has an invalid method which will fail validation
        # but the valid request should still be imported
        result = insomnia_importer.import_collection(insomnia_malformed_request)

        # Should have imported at least the valid request
        assert len(result.requests) >= 1
        # The valid request should be present
        names = [r.name for r in result.requests]
        assert "Valid Request" in names

    def test_parse_non_utf8_file_raises(
        self, insomnia_importer: InsomniaImporter, tmp_path: Path
    ):
        """import_collection should raise for non-UTF-8 encoded file."""
        # Create a file with Latin-1 encoding containing invalid UTF-8 bytes
        non_utf8 = tmp_path / "non_utf8.json"
        non_utf8.write_bytes(b'{"_type": "export", "data": "\xff\xfe"}')

        with pytest.raises(ImporterException) as exc_info:
            insomnia_importer.import_collection(non_utf8)
        assert "UTF-8" in str(exc_info.value)

    def test_list_requests_exception_returns_empty(
        self, insomnia_importer: InsomniaImporter, tmp_path: Path
    ):
        """list_requests should return empty list on exception."""
        # Create invalid JSON file
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("{not valid json}")

        result = insomnia_importer.list_requests(invalid_file)
        assert result == []


class TestHeaderParsingEdgeCases:
    """Tests for header parsing edge cases."""

    def test_disabled_headers_skipped(
        self, insomnia_importer: InsomniaImporter, insomnia_disabled_headers: Path
    ):
        """Disabled headers should be skipped."""
        result = insomnia_importer.import_collection(insomnia_disabled_headers)

        request = result.requests[0]
        assert "Active-Header" in request.headers
        assert "Disabled-Header" not in request.headers
        assert "Another-Active" in request.headers

    def test_empty_header_name_skipped(
        self, insomnia_importer: InsomniaImporter, insomnia_disabled_headers: Path
    ):
        """Headers with empty names should be skipped."""
        result = insomnia_importer.import_collection(insomnia_disabled_headers)

        request = result.requests[0]
        # Empty name header value should not appear
        assert "" not in request.headers
        assert "empty-name-value" not in request.headers.values()

    def test_nondict_headers_skipped(
        self, insomnia_importer: InsomniaImporter, insomnia_disabled_headers: Path
    ):
        """Non-dict header items should be skipped without error."""
        result = insomnia_importer.import_collection(insomnia_disabled_headers)

        # Should still have valid headers parsed
        request = result.requests[0]
        assert len(request.headers) == 2  # Active-Header and Another-Active


class TestBodyParsingEdgeCases:
    """Tests for body parsing edge cases."""

    def test_empty_mimetype_returns_none(
        self, insomnia_importer: InsomniaImporter, insomnia_body_edge_cases: Path
    ):
        """Body with empty mimeType should return None."""
        result = insomnia_importer.import_collection(insomnia_body_edge_cases)

        empty_mime = next((r for r in result.requests if r.name == "Empty MimeType"), None)
        assert empty_mime is not None
        assert empty_mime.body is None
        assert empty_mime.body_type == "none"

    def test_invalid_json_body_returns_raw(
        self, insomnia_importer: InsomniaImporter, insomnia_body_edge_cases: Path
    ):
        """Invalid JSON body should be returned as raw string."""
        result = insomnia_importer.import_collection(insomnia_body_edge_cases)

        invalid_json = next((r for r in result.requests if r.name == "Invalid JSON Body"), None)
        assert invalid_json is not None
        assert invalid_json.body_type == "raw"
        assert isinstance(invalid_json.body, str)
        assert "{not valid json" in invalid_json.body

    def test_disabled_form_params_skipped(
        self, insomnia_importer: InsomniaImporter, insomnia_body_edge_cases: Path
    ):
        """Disabled form params should be skipped."""
        result = insomnia_importer.import_collection(insomnia_body_edge_cases)

        form_req = next(
            (r for r in result.requests if r.name == "Form With Disabled Params"), None
        )
        assert form_req is not None
        assert form_req.body_type == "form"
        assert isinstance(form_req.body, dict)
        assert "active_field" in form_req.body
        assert "disabled_field" not in form_req.body
        assert "another_active" in form_req.body

    def test_all_disabled_form_params_returns_none(
        self, insomnia_importer: InsomniaImporter, insomnia_body_edge_cases: Path
    ):
        """Form with all disabled params should return None."""
        result = insomnia_importer.import_collection(insomnia_body_edge_cases)

        all_disabled = next(
            (r for r in result.requests if r.name == "All Disabled Form Params"), None
        )
        assert all_disabled is not None
        assert all_disabled.body is None
        assert all_disabled.body_type == "none"

    def test_nondict_form_params_skipped(
        self, insomnia_importer: InsomniaImporter, insomnia_body_edge_cases: Path
    ):
        """Non-dict form params should be skipped without error."""
        result = insomnia_importer.import_collection(insomnia_body_edge_cases)

        form_req = next(
            (r for r in result.requests if r.name == "Form With Disabled Params"), None
        )
        assert form_req is not None
        # Should have parsed valid params despite the "not_a_dict_param" string
        assert len(form_req.body) == 2

    def test_unknown_mimetype_no_text_returns_none(
        self, insomnia_importer: InsomniaImporter, insomnia_body_edge_cases: Path
    ):
        """Unknown mimeType with no text should return None."""
        result = insomnia_importer.import_collection(insomnia_body_edge_cases)

        unknown_mime = next(
            (r for r in result.requests if r.name == "Unknown MimeType No Text"), None
        )
        assert unknown_mime is not None
        assert unknown_mime.body is None
        assert unknown_mime.body_type == "none"


class TestAuthParsingEdgeCases:
    """Tests for authentication parsing edge cases."""

    def test_empty_auth_type_returns_none(
        self, insomnia_importer: InsomniaImporter, insomnia_auth_edge_cases: Path
    ):
        """Empty auth type should return no auth."""
        result = insomnia_importer.import_collection(insomnia_auth_edge_cases)

        empty_auth = next(
            (r for r in result.requests if r.name == "Empty Auth Type"), None
        )
        assert empty_auth is not None
        assert empty_auth.auth_type is None
        assert "Authorization" not in empty_auth.headers

    def test_bearer_without_token_returns_none(
        self, insomnia_importer: InsomniaImporter, insomnia_auth_edge_cases: Path
    ):
        """Bearer auth without token should return no auth."""
        result = insomnia_importer.import_collection(insomnia_auth_edge_cases)

        bearer_no_token = next(
            (r for r in result.requests if r.name == "Bearer Without Token"), None
        )
        assert bearer_no_token is not None
        assert bearer_no_token.auth_type is None
        assert "Authorization" not in bearer_no_token.headers

    def test_unrecognized_auth_type_returns_none(
        self, insomnia_importer: InsomniaImporter, insomnia_auth_edge_cases: Path
    ):
        """Unrecognized auth type should return no auth."""
        result = insomnia_importer.import_collection(insomnia_auth_edge_cases)

        unknown_auth = next(
            (r for r in result.requests if r.name == "Unknown Auth Type"), None
        )
        assert unknown_auth is not None
        assert unknown_auth.auth_type is None
        assert "Authorization" not in unknown_auth.headers


class TestFolderHierarchyEdgeCases:
    """Tests for folder hierarchy edge cases."""

    def test_orphaned_parent_id_returns_empty_path(
        self, insomnia_importer: InsomniaImporter, insomnia_orphaned_requests: Path
    ):
        """Request with orphaned parentId should have empty folder path."""
        result = insomnia_importer.import_collection(insomnia_orphaned_requests)

        orphaned = next((r for r in result.requests if r.name == "Orphaned Request"), None)
        assert orphaned is not None
        assert orphaned.folder_path == ""

    def test_valid_folder_path_still_works(
        self, insomnia_importer: InsomniaImporter, insomnia_orphaned_requests: Path
    ):
        """Valid requests should still have correct folder paths."""
        result = insomnia_importer.import_collection(insomnia_orphaned_requests)

        valid_req = next((r for r in result.requests if r.name == "Valid Request"), None)
        assert valid_req is not None
        assert valid_req.folder_path == "Real Folder"


class TestCorrelationExtraction:
    """Tests for correlation extraction from post-response scripts."""

    def test_post_script_with_correlations(
        self, insomnia_importer: InsomniaImporter, insomnia_post_script_correlations: Path
    ):
        """Post-response script with correlations should extract them."""
        result = insomnia_importer.import_collection(insomnia_post_script_correlations)

        request = result.requests[0]
        assert request.post_script is not None
        assert len(request.correlations) >= 1

        # Check that correlation was extracted
        var_names = [c["variable_name"] for c in request.correlations]
        assert "auth_token" in var_names or "user_id" in var_names


class TestEnvironmentFile:
    """Tests for external environment file parsing."""

    def test_import_with_env_file_plain_json(
        self, insomnia_importer: InsomniaImporter,
        insomnia_basic_collection: Path,
        insomnia_env_plain: Path,
    ):
        """import_collection with plain JSON env file should load variables."""
        result = insomnia_importer.import_collection(
            insomnia_basic_collection, env_path=insomnia_env_plain
        )

        assert "api_key" in result.metadata.variables
        assert result.metadata.variables["api_key"] == "test-key-123"

    def test_import_with_env_file_insomnia_export(
        self, insomnia_importer: InsomniaImporter,
        insomnia_basic_collection: Path,
        insomnia_env_insomnia_export: Path,
    ):
        """import_collection with Insomnia export env file should load variables."""
        result = insomnia_importer.import_collection(
            insomnia_basic_collection, env_path=insomnia_env_insomnia_export
        )

        assert "token" in result.metadata.variables
        assert result.metadata.variables["token"] == "env-token-xyz"

    def test_import_with_invalid_env_file(
        self, insomnia_importer: InsomniaImporter,
        insomnia_basic_collection: Path,
        insomnia_env_invalid: Path,
    ):
        """import_collection with invalid env file should continue without error."""
        # Should not raise, just log warning and continue
        result = insomnia_importer.import_collection(
            insomnia_basic_collection, env_path=insomnia_env_invalid
        )

        # Should still have the collection's own variables
        assert result.metadata.name == "Test Collection"
        assert "base_url" in result.metadata.variables

    def test_env_file_null_values_converted_to_empty_string(
        self, insomnia_importer: InsomniaImporter,
        insomnia_basic_collection: Path,
        insomnia_env_plain: Path,
    ):
        """Null values in env file should be converted to empty string."""
        result = insomnia_importer.import_collection(
            insomnia_basic_collection, env_path=insomnia_env_plain
        )

        assert "null_value" in result.metadata.variables
        assert result.metadata.variables["null_value"] == ""


class TestInsomniaEnvironmentHierarchy:
    """Tests for Insomnia environment inheritance and base URL detection."""

    def test_is_valid_url_with_scheme(self, insomnia_importer: InsomniaImporter):
        """Test _is_valid_url returns True for URLs with http/https scheme."""
        assert insomnia_importer._is_valid_url("http://example.com") is True
        assert insomnia_importer._is_valid_url("https://api.example.com/v1") is True

    def test_is_valid_url_without_scheme(self, insomnia_importer: InsomniaImporter):
        """Test _is_valid_url returns False for URLs without scheme."""
        assert insomnia_importer._is_valid_url("example.com") is False
        assert insomnia_importer._is_valid_url("/api/v1") is False

    def test_is_valid_url_with_template_variables(
        self, insomnia_importer: InsomniaImporter
    ):
        """Test _is_valid_url returns False for URLs with unresolved templates."""
        assert insomnia_importer._is_valid_url("{{ scheme }}://{{ host }}") is False
        assert insomnia_importer._is_valid_url("{{base_url}}/api") is False
        assert insomnia_importer._is_valid_url("https://{{host}}/api") is False

    def test_extract_flat_variables_skips_nested_objects(
        self, insomnia_importer: InsomniaImporter
    ):
        """Test _extract_flat_variables skips nested dict objects."""
        data = {
            "host": "https://api.example.com",
            "timeout": "30",
            "credentials": {"username": "user", "password": "pass"},
        }
        result = insomnia_importer._extract_flat_variables(data)
        assert result == {"host": "https://api.example.com", "timeout": "30"}
        assert "credentials" not in result

    def test_detect_base_url_priority_order(self, insomnia_importer: InsomniaImporter):
        """Test _detect_base_url checks keys in priority order."""
        # base_url takes priority
        vars1 = {"base_url": "http://base.com", "host": "http://host.com"}
        assert insomnia_importer._detect_base_url(vars1) == "http://base.com"

        # host is fallback when no base_url
        vars2 = {"host": "http://host.com", "url": "http://url.com"}
        assert insomnia_importer._detect_base_url(vars2) == "http://host.com"

        # url is last resort
        vars3 = {"url": "http://url.com", "other": "value"}
        assert insomnia_importer._detect_base_url(vars3) == "http://url.com"

    def test_detect_base_url_case_insensitive(
        self, insomnia_importer: InsomniaImporter
    ):
        """Test _detect_base_url handles case variations."""
        vars1 = {"BASE_URL": "http://example.com"}
        assert insomnia_importer._detect_base_url(vars1) == "http://example.com"

        vars2 = {"Host": "http://example.com"}
        assert insomnia_importer._detect_base_url(vars2) == "http://example.com"

    def test_child_environment_overrides_parent(
        self, insomnia_importer: InsomniaImporter
    ):
        """Test that child environment variables override parent values."""
        resources = [
            {"_id": "wrk_1", "_type": "workspace"},
            {
                "_id": "env_base",
                "_type": "environment",
                "parentId": "wrk_1",
                "data": {"host": "http://base.example.com", "timeout": "30"},
            },
            {
                "_id": "env_child",
                "_type": "environment",
                "parentId": "env_base",
                "data": {"host": "https://child.example.com"},
            },
        ]
        variables, base_url = insomnia_importer._build_environment_hierarchy(
            resources, "wrk_1"
        )
        assert base_url == "https://child.example.com"
        assert variables["host"] == "https://child.example.com"
        assert variables["timeout"] == "30"  # Inherited from parent

    def test_skip_unresolved_template_base_url(
        self, insomnia_importer: InsomniaImporter
    ):
        """Test that base_url with unresolved templates is skipped."""
        resources = [
            {"_id": "wrk_1", "_type": "workspace"},
            {
                "_id": "env_base",
                "_type": "environment",
                "parentId": "wrk_1",
                "data": {"base_url": "{{ scheme }}://{{ host }}"},
            },
            {
                "_id": "env_child",
                "_type": "environment",
                "parentId": "env_base",
                "data": {"host": "https://api.example.com"},
            },
        ]
        variables, base_url = insomnia_importer._build_environment_hierarchy(
            resources, "wrk_1"
        )
        assert base_url == "https://api.example.com"

    def test_fallback_to_host_variable(self, insomnia_importer: InsomniaImporter):
        """Test fallback to 'host' when no base_url exists."""
        resources = [
            {"_id": "wrk_1", "_type": "workspace"},
            {
                "_id": "env_base",
                "_type": "environment",
                "parentId": "wrk_1",
                "data": {"host": "https://api.example.com/v1"},
            },
        ]
        variables, base_url = insomnia_importer._build_environment_hierarchy(
            resources, "wrk_1"
        )
        assert base_url == "https://api.example.com/v1"

    def test_no_base_url_when_all_invalid(self, insomnia_importer: InsomniaImporter):
        """Test returns None base_url when all URLs are invalid."""
        resources = [
            {"_id": "wrk_1", "_type": "workspace"},
            {
                "_id": "env_base",
                "_type": "environment",
                "parentId": "wrk_1",
                "data": {"base_url": "{{ scheme }}://{{ host }}{{ base_path }}"},
            },
            {
                "_id": "env_child",
                "_type": "environment",
                "parentId": "env_base",
                "data": {"other_var": "value"},
            },
        ]
        variables, base_url = insomnia_importer._build_environment_hierarchy(
            resources, "wrk_1"
        )
        assert base_url is None

    def test_empty_resources_returns_empty(self, insomnia_importer: InsomniaImporter):
        """Test empty resources returns empty variables and None base_url."""
        variables, base_url = insomnia_importer._build_environment_hierarchy([], "wrk_1")
        assert variables == {}
        assert base_url is None

    def test_no_base_environment_returns_empty(
        self, insomnia_importer: InsomniaImporter
    ):
        """Test returns empty when no base environment exists."""
        resources = [
            {"_id": "wrk_1", "_type": "workspace"},
            {
                "_id": "env_orphan",
                "_type": "environment",
                "parentId": "other_workspace",
                "data": {"host": "https://example.com"},
            },
        ]
        variables, base_url = insomnia_importer._build_environment_hierarchy(
            resources, "wrk_1"
        )
        assert variables == {}
        assert base_url is None
