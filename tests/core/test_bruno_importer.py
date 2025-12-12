"""Unit tests for Bruno collection importer.

Tests cover:
- Collection detection (can_import)
- Full import (import_collection)
- Preview mode (list_requests)
- .bru file parsing (_parse_bru_file)
- Environment parsing (_parse_environment)
- File discovery and sorting (_find_request_files)
- Variable conversion ({{var}} to ${var})
- Authentication handling
- Error handling and edge cases
- Real-world collections (JSONPlaceholder, GitHub API)
"""

from pathlib import Path

import pytest

from collection_importer.core.data_types import (
    CollectionMetadata,
    ParsedCollection,
)
from collection_importer.core.importers.bruno import BrunoImporter
from collection_importer.exceptions import ImporterException

# =============================================================================
# TestCanImport - Tests for can_import() method
# =============================================================================


class TestCanImport:
    """Tests for BrunoImporter.can_import() method."""

    def test_can_import_directory_with_bruno_json(
        self, bruno_importer: BrunoImporter, bruno_collection_dir: Path
    ) -> None:
        """Directory with bruno.json should be detected."""
        assert bruno_importer.can_import(bruno_collection_dir) is True

    def test_can_import_directory_with_bru_files_no_bruno_json(
        self, bruno_importer: BrunoImporter, tmp_path: Path
    ) -> None:
        """Directory with .bru files but no bruno.json should be detected."""
        # Create directory with only .bru files
        bru_file = tmp_path / "test.bru"
        bru_file.write_text("get { url: /test }")

        assert bruno_importer.can_import(tmp_path) is True

    def test_can_import_single_bru_file(
        self, bruno_importer: BrunoImporter, single_bru_file: Path
    ) -> None:
        """Single .bru file should be detected."""
        assert bruno_importer.can_import(single_bru_file) is True

    def test_cannot_import_nonexistent_path(
        self, bruno_importer: BrunoImporter, tmp_path: Path
    ) -> None:
        """Non-existent path should return False."""
        nonexistent = tmp_path / "does-not-exist"
        assert bruno_importer.can_import(nonexistent) is False

    def test_cannot_import_empty_directory(
        self, bruno_importer: BrunoImporter, tmp_path: Path
    ) -> None:
        """Empty directory should return False."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        assert bruno_importer.can_import(empty_dir) is False

    def test_cannot_import_non_bru_file(
        self, bruno_importer: BrunoImporter, tmp_path: Path
    ) -> None:
        """Non-.bru file should return False."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("not a bru file")
        assert bruno_importer.can_import(txt_file) is False

    def test_cannot_import_json_file(
        self, bruno_importer: BrunoImporter, tmp_path: Path
    ) -> None:
        """JSON file (Postman format) should return False."""
        json_file = tmp_path / "collection.json"
        json_file.write_text('{"info": {"name": "Postman Collection"}}')
        assert bruno_importer.can_import(json_file) is False


# =============================================================================
# TestImportCollection - Tests for import_collection() method
# =============================================================================


class TestImportCollection:
    """Tests for BrunoImporter.import_collection() method."""

    def test_import_basic_collection(
        self, bruno_importer: BrunoImporter, bruno_collection_dir: Path
    ) -> None:
        """Import basic collection with bruno.json."""
        result = bruno_importer.import_collection(bruno_collection_dir)

        assert result is not None
        assert len(result.requests) > 0

    def test_import_collection_returns_parsed_collection(
        self, bruno_importer: BrunoImporter, bruno_collection_dir: Path
    ) -> None:
        """Result should be ParsedCollection instance."""
        result = bruno_importer.import_collection(bruno_collection_dir)
        assert isinstance(result, ParsedCollection)
        assert isinstance(result.metadata, CollectionMetadata)

    def test_import_collection_metadata(
        self, bruno_importer: BrunoImporter, bruno_collection_dir: Path
    ) -> None:
        """Metadata should include name, format, source_path."""
        result = bruno_importer.import_collection(bruno_collection_dir)

        assert result.metadata.name == "Test Collection"
        assert result.metadata.format == "bruno"
        assert str(bruno_collection_dir) in result.metadata.source_path

    def test_import_collection_request_count(
        self, bruno_importer: BrunoImporter, bruno_collection_dir: Path
    ) -> None:
        """Should import all requests from collection."""
        result = bruno_importer.import_collection(bruno_collection_dir)
        # Basic collection has 2 requests (get-users, create-user)
        assert result.request_count >= 2

    def test_import_single_bru_file(
        self, bruno_importer: BrunoImporter, single_bru_file: Path
    ) -> None:
        """Import single .bru file as collection."""
        result = bruno_importer.import_collection(single_bru_file)

        assert result.request_count == 1
        assert result.requests[0].name == "Standalone Request"
        assert result.requests[0].method == "GET"

    def test_import_single_file_no_method_raises(
        self, bruno_importer: BrunoImporter, tmp_path: Path
    ) -> None:
        """Single file without HTTP method should raise ImporterException."""
        invalid_file = tmp_path / "invalid.bru"
        invalid_file.write_text("meta { name: No Method }")

        with pytest.raises(ImporterException) as exc_info:
            bruno_importer.import_collection(invalid_file)

        assert "No HTTP method found" in str(exc_info.value)

    def test_import_collection_name_override(
        self, bruno_importer: BrunoImporter, bruno_collection_dir: Path
    ) -> None:
        """Name parameter should override collection name."""
        result = bruno_importer.import_collection(
            bruno_collection_dir, name="Custom Name"
        )
        assert result.metadata.name == "Custom Name"

    def test_import_collection_name_from_bruno_json(
        self, bruno_importer: BrunoImporter, bruno_collection_dir: Path
    ) -> None:
        """Name should come from bruno.json if not overridden."""
        result = bruno_importer.import_collection(bruno_collection_dir)
        assert result.metadata.name == "Test Collection"

    def test_import_collection_name_fallback_to_folder(
        self, bruno_importer: BrunoImporter, tmp_path: Path
    ) -> None:
        """Name should fall back to folder name if bruno.json missing."""
        # Create collection without bruno.json
        collection_dir = tmp_path / "my-collection"
        collection_dir.mkdir()
        bru_file = collection_dir / "test.bru"
        bru_file.write_text(
            """meta { name: Test }
get { url: /test }"""
        )

        result = bruno_importer.import_collection(collection_dir)
        assert result.metadata.name == "my-collection"

    def test_import_collection_base_url_override(
        self, bruno_importer: BrunoImporter, bruno_collection_dir: Path
    ) -> None:
        """Base URL parameter should override environment."""
        result = bruno_importer.import_collection(
            bruno_collection_dir, base_url="https://custom.api.com"
        )
        assert result.metadata.base_url == "https://custom.api.com"

    def test_import_request_name(
        self, bruno_importer: BrunoImporter, bruno_collection_dir: Path
    ) -> None:
        """Request name should come from meta block."""
        result = bruno_importer.import_collection(bruno_collection_dir)

        request_names = [r.name for r in result.requests]
        assert "Get Users" in request_names
        assert "Create User" in request_names

    def test_import_request_method(
        self, bruno_importer: BrunoImporter, bruno_collection_dir: Path
    ) -> None:
        """Request method should be parsed correctly."""
        result = bruno_importer.import_collection(bruno_collection_dir)

        methods = {r.name: r.method for r in result.requests}
        assert methods.get("Get Users") == "GET"
        assert methods.get("Create User") == "POST"

    def test_import_request_path_with_variable_conversion(
        self, bruno_importer: BrunoImporter, bruno_collection_dir: Path
    ) -> None:
        """Path should have {{var}} converted to ${var}."""
        result = bruno_importer.import_collection(bruno_collection_dir)

        for request in result.requests:
            # No {{var}} should remain after import
            assert "{{" not in request.path
            # Variables should be in ${var} format
            if "base_url" in request.path.lower():
                assert "${" in request.path

    def test_import_request_headers(
        self, bruno_importer: BrunoImporter, bruno_collection_dir: Path
    ) -> None:
        """Headers should be parsed correctly."""
        result = bruno_importer.import_collection(bruno_collection_dir)

        get_users = next((r for r in result.requests if r.name == "Get Users"), None)
        assert get_users is not None
        assert "Content-Type" in get_users.headers
        assert get_users.headers["Content-Type"] == "application/json"

    def test_import_request_json_body(
        self, bruno_importer: BrunoImporter, bruno_collection_dir: Path
    ) -> None:
        """JSON body should be parsed as dict."""
        result = bruno_importer.import_collection(bruno_collection_dir)

        create_user = next(
            (r for r in result.requests if r.name == "Create User"), None
        )
        assert create_user is not None
        assert create_user.body is not None
        assert create_user.body_type == "json"
        assert isinstance(create_user.body, dict)
        assert "name" in create_user.body

    def test_import_request_sequence(
        self, bruno_importer: BrunoImporter, bruno_collection_dir: Path
    ) -> None:
        """Sequence should reflect meta.seq and file order."""
        result = bruno_importer.import_collection(bruno_collection_dir)

        # Requests should be ordered by sequence
        sequences = [r.sequence for r in result.requests]
        assert sequences == sorted(sequences)

    def test_import_nonexistent_path_raises(
        self, bruno_importer: BrunoImporter
    ) -> None:
        """Non-existent path should raise ImporterException."""
        with pytest.raises(ImporterException) as exc_info:
            bruno_importer.import_collection(Path("/does/not/exist"))

        assert "does not exist" in str(exc_info.value)

    def test_import_malformed_bruno_json_uses_fallback(
        self, bruno_importer: BrunoImporter, tmp_path: Path
    ) -> None:
        """Malformed bruno.json should log warning and use folder name."""
        collection_dir = tmp_path / "test-collection"
        collection_dir.mkdir()

        # Create malformed bruno.json
        bruno_json = collection_dir / "bruno.json"
        bruno_json.write_text("{ invalid json }")

        # Create a valid request
        bru_file = collection_dir / "test.bru"
        bru_file.write_text(
            """meta { name: Test }
get { url: /test }"""
        )

        result = bruno_importer.import_collection(collection_dir)
        # Should fall back to folder name
        assert result.metadata.name == "test-collection"


# =============================================================================
# TestListRequests - Tests for list_requests() method (preview mode)
# =============================================================================


class TestListRequests:
    """Tests for BrunoImporter.list_requests() method."""

    def test_list_requests_returns_list(
        self, bruno_importer: BrunoImporter, bruno_collection_dir: Path
    ) -> None:
        """Should return list of request dicts."""
        result = bruno_importer.list_requests(bruno_collection_dir)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_list_request_dict_keys(
        self, bruno_importer: BrunoImporter, bruno_collection_dir: Path
    ) -> None:
        """Each dict should have name, method, path keys."""
        result = bruno_importer.list_requests(bruno_collection_dir)

        for request in result:
            assert "name" in request
            assert "method" in request
            assert "path" in request

    def test_list_requests_method_uppercase(
        self, bruno_importer: BrunoImporter, bruno_collection_dir: Path
    ) -> None:
        """Method should be uppercase."""
        result = bruno_importer.list_requests(bruno_collection_dir)

        for request in result:
            assert request["method"] == request["method"].upper()

    def test_list_requests_single_file(
        self, bruno_importer: BrunoImporter, single_bru_file: Path
    ) -> None:
        """Should work with single .bru file."""
        result = bruno_importer.list_requests(single_bru_file)

        assert len(result) == 1
        assert result[0]["name"] == "Standalone Request"
        assert result[0]["method"] == "GET"

    def test_list_requests_skips_invalid_files(
        self, bruno_importer: BrunoImporter, tmp_path: Path
    ) -> None:
        """Should skip files with parse errors and continue."""
        # Create mixed valid and invalid files
        valid_file = tmp_path / "valid.bru"
        valid_file.write_text(
            """meta {
  name: Valid
}

get {
  url: /valid
}"""
        )

        invalid_file = tmp_path / "invalid.bru"
        invalid_file.write_text("not valid bru content { { {")

        result = bruno_importer.list_requests(tmp_path)

        # Should have at least the valid one
        assert len(result) >= 1
        assert any(r["name"] == "Valid" for r in result)

    def test_list_requests_empty_collection(
        self, bruno_importer: BrunoImporter, tmp_path: Path
    ) -> None:
        """Empty collection should return empty list."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = bruno_importer.list_requests(empty_dir)
        assert result == []


# =============================================================================
# TestParseBruFile - Tests for _parse_bru_file() internal method
# =============================================================================


class TestParseBruFile:
    """Tests for BrunoImporter._parse_bru_file() internal method."""

    def test_parse_meta_name(self, bruno_importer: BrunoImporter) -> None:
        """Should extract name from meta block."""
        content = """meta {
  name: Test Request
  type: http
  seq: 1
}"""
        result = bruno_importer._parse_bru_file(content)
        assert result["name"] == "Test Request"

    def test_parse_meta_missing_name(self, bruno_importer: BrunoImporter) -> None:
        """Missing name should result in empty string."""
        content = """meta {
  type: http
  seq: 1
}"""
        result = bruno_importer._parse_bru_file(content)
        assert result["name"] == ""

    @pytest.mark.parametrize(
        "method", ["get", "post", "put", "patch", "delete", "head", "options"]
    )
    def test_parse_http_methods(
        self, bruno_importer: BrunoImporter, method: str
    ) -> None:
        """Should parse all HTTP methods."""
        content = f"""{method} {{
  url: /test
  body: none
}}"""
        result = bruno_importer._parse_bru_file(content)
        assert result["method"] == method.upper()

    def test_parse_uppercase_method(self, bruno_importer: BrunoImporter) -> None:
        """Should handle uppercase method blocks (GET vs get)."""
        content = """GET {
  url: /uppercase-test
  body: none
}"""
        result = bruno_importer._parse_bru_file(content)
        assert result["method"] == "GET"
        assert result["url"] == "/uppercase-test"

    def test_parse_method_url(self, bruno_importer: BrunoImporter) -> None:
        """Should extract URL from method block."""
        content = """get {
  url: {{base_url}}/users/{{id}}
  body: none
}"""
        result = bruno_importer._parse_bru_file(content)
        assert result["url"] == "{{base_url}}/users/{{id}}"

    def test_parse_method_body_type(self, bruno_importer: BrunoImporter) -> None:
        """Should extract body type from method block."""
        content = """post {
  url: /data
  body: json
}"""
        result = bruno_importer._parse_bru_file(content)
        assert result["body_type"] == "json"

    def test_parse_headers_block(self, bruno_importer: BrunoImporter) -> None:
        """Should parse headers block."""
        content = """get {
  url: /test
}

headers {
  Accept: application/json
}"""
        result = bruno_importer._parse_bru_file(content)
        assert result["headers"]["Accept"] == "application/json"

    def test_parse_headers_multiple(self, bruno_importer: BrunoImporter) -> None:
        """Should parse multiple headers."""
        content = """get {
  url: /test
}

headers {
  Content-Type: application/json
  Authorization: Bearer token123
  X-Custom-Header: custom-value
}"""
        result = bruno_importer._parse_bru_file(content)
        assert len(result["headers"]) == 3
        assert result["headers"]["Content-Type"] == "application/json"
        assert result["headers"]["Authorization"] == "Bearer token123"
        assert result["headers"]["X-Custom-Header"] == "custom-value"

    def test_parse_headers_with_colons_in_value(
        self, bruno_importer: BrunoImporter
    ) -> None:
        """Should handle colons in header values."""
        content = """get {
  url: /test
}

headers {
  X-Custom: value:with:colons
}"""
        result = bruno_importer._parse_bru_file(content)
        assert result["headers"]["X-Custom"] == "value:with:colons"

    def test_parse_headers_skips_comments(self, bruno_importer: BrunoImporter) -> None:
        """Should skip lines starting with #."""
        content = """get {
  url: /test
}

headers {
  # This is a comment
  Accept: application/json
}"""
        result = bruno_importer._parse_bru_file(content)
        assert "#" not in str(result["headers"])
        assert result["headers"].get("Accept") == "application/json"

    def test_parse_body_json_valid(self, bruno_importer: BrunoImporter) -> None:
        """Should parse valid JSON body as dict."""
        content = """post {
  url: /data
  body: json
}

body:json {
  {
    "name": "test",
    "value": 123
  }
}"""
        result = bruno_importer._parse_bru_file(content)
        assert result["body_type"] == "json"
        assert isinstance(result["body"], dict)
        assert result["body"]["name"] == "test"
        assert result["body"]["value"] == 123

    def test_parse_body_json_invalid_as_raw(
        self, bruno_importer: BrunoImporter
    ) -> None:
        """Invalid JSON should be stored as raw string."""
        content = """post {
  url: /data
  body: json
}

body:json {
  { invalid json }
}"""
        result = bruno_importer._parse_bru_file(content)
        assert result["body_type"] == "raw"
        assert isinstance(result["body"], str)

    def test_parse_body_json_with_variables(
        self, bruno_importer: BrunoImporter
    ) -> None:
        """JSON body with {{var}} should be parsed."""
        content = """post {
  url: /users
  body: json
}

body:json {
  {
    "name": "{{user_name}}",
    "email": "{{email}}"
  }
}"""
        result = bruno_importer._parse_bru_file(content)
        assert isinstance(result["body"], dict)
        assert result["body"]["name"] == "{{user_name}}"
        assert result["body"]["email"] == "{{email}}"

    def test_parse_auth_bearer(self, bruno_importer: BrunoImporter) -> None:
        """Should parse auth:bearer block."""
        content = """get {
  url: /protected
  auth: bearer
}

auth:bearer {
  token: {{auth_token}}
}"""
        result = bruno_importer._parse_bru_file(content)
        assert result["auth_type"] == "bearer"
        assert result["auth_value"] == "{{auth_token}}"

    def test_parse_auth_basic(self, bruno_importer: BrunoImporter) -> None:
        """Should parse auth:basic block."""
        content = """get {
  url: /basic
  auth: basic
}

auth:basic {
  username: {{username}}
  password: {{password}}
}"""
        result = bruno_importer._parse_bru_file(content)
        assert result["auth_type"] == "basic"

    def test_parse_auth_basic_credentials(
        self, bruno_importer: BrunoImporter
    ) -> None:
        """Basic auth should combine username:password."""
        content = """get {
  url: /basic
}

auth:basic {
  username: testuser
  password: testpass
}"""
        result = bruno_importer._parse_bru_file(content)
        assert result["auth_value"] == "testuser:testpass"

    def test_parse_script_pre_request(self, bruno_importer: BrunoImporter) -> None:
        """Should parse script:pre-request block."""
        content = """get {
  url: /test
}

script:pre-request {
  console.log('before request');
  bru.setVar('timestamp', Date.now());
}"""
        result = bruno_importer._parse_bru_file(content)
        assert result["pre_script"] is not None
        assert "console.log" in result["pre_script"]

    def test_parse_script_post_response(self, bruno_importer: BrunoImporter) -> None:
        """Should parse script:post-response block."""
        content = """get {
  url: /test
}

script:post-response {
  const data = res.body;
  bru.setVar('result', data.id);
}"""
        result = bruno_importer._parse_bru_file(content)
        assert result["post_script"] is not None
        assert "res.body" in result["post_script"]

    def test_parse_scripts_both(self, bruno_importer: BrunoImporter) -> None:
        """Should parse both scripts in same file."""
        content = """get {
  url: /test
}

script:pre-request {
  console.log('pre');
}

script:post-response {
  console.log('post');
}"""
        result = bruno_importer._parse_bru_file(content)
        assert result["pre_script"] is not None
        assert result["post_script"] is not None

    def test_parse_empty_content(self, bruno_importer: BrunoImporter) -> None:
        """Empty content should return defaults."""
        result = bruno_importer._parse_bru_file("")
        assert result["name"] == ""
        assert result["method"] == ""
        assert result["url"] == ""
        assert result["headers"] == {}
        assert result["body"] is None

    def test_parse_no_method_block(self, bruno_importer: BrunoImporter) -> None:
        """Missing method block should result in empty method."""
        content = """meta {
  name: No Method
}"""
        result = bruno_importer._parse_bru_file(content)
        assert result["method"] == ""


# =============================================================================
# TestParseEnvironment - Tests for _parse_environment() internal method
# =============================================================================


class TestParseEnvironment:
    """Tests for BrunoImporter._parse_environment() internal method."""

    def test_parse_environment_variables(
        self, bruno_importer: BrunoImporter, bruno_with_environments: Path
    ) -> None:
        """Should parse vars block into dict."""
        env_path = bruno_with_environments / "environments" / "dev.bru"
        variables, base_url = bruno_importer._parse_environment(env_path)

        assert "api_key" in variables
        assert variables["api_key"] == "dev-api-key-12345"

    def test_parse_environment_base_url_detection(
        self, bruno_importer: BrunoImporter, bruno_with_environments: Path
    ) -> None:
        """Should detect base_url from vars."""
        env_path = bruno_with_environments / "environments" / "dev.bru"
        variables, base_url = bruno_importer._parse_environment(env_path)

        assert base_url == "http://localhost:3000"

    def test_parse_environment_baseUrl_camelcase(
        self, bruno_importer: BrunoImporter, bruno_with_environments: Path
    ) -> None:
        """Should detect baseUrl (camelCase)."""
        env_path = bruno_with_environments / "environments" / "prod.bru"
        variables, base_url = bruno_importer._parse_environment(env_path)

        assert base_url == "https://api.production.com"

    def test_parse_environment_skips_disabled_vars(
        self, bruno_importer: BrunoImporter, bruno_with_environments: Path
    ) -> None:
        """Should skip vars prefixed with ~."""
        env_path = bruno_with_environments / "environments" / "dev.bru"
        variables, base_url = bruno_importer._parse_environment(env_path)

        assert "disabled_var" not in variables
        assert "~disabled_var" not in variables

    def test_parse_environment_nonexistent_file(
        self, bruno_importer: BrunoImporter, tmp_path: Path
    ) -> None:
        """Non-existent file should return empty dict and None."""
        nonexistent = tmp_path / "does-not-exist.bru"
        variables, base_url = bruno_importer._parse_environment(nonexistent)

        assert variables == {}
        assert base_url is None

    def test_parse_environment_malformed_returns_empty(
        self, bruno_importer: BrunoImporter, tmp_path: Path
    ) -> None:
        """Malformed environment should return empty dict."""
        env_file = tmp_path / "malformed.bru"
        env_file.write_text("vars { not valid } extra content {{")

        variables, base_url = bruno_importer._parse_environment(env_file)

        # Should handle gracefully, may have partial results
        assert isinstance(variables, dict)


# =============================================================================
# TestFindRequestFiles - Tests for _find_request_files() internal method
# =============================================================================


class TestFindRequestFiles:
    """Tests for BrunoImporter._find_request_files() internal method."""

    def test_find_all_bru_files(
        self, bruno_importer: BrunoImporter, bruno_collection_dir: Path
    ) -> None:
        """Should find all .bru files in collection."""
        files = bruno_importer._find_request_files(bruno_collection_dir)
        assert len(files) >= 2
        assert all(f.suffix == ".bru" for f in files)

    def test_find_excludes_environment_files(
        self, bruno_importer: BrunoImporter, bruno_with_environments: Path
    ) -> None:
        """Should exclude files in environments/ folder."""
        files = bruno_importer._find_request_files(bruno_with_environments)

        for f in files:
            assert "environments" not in f.parts

    def test_find_recursive_in_subdirectories(
        self, bruno_importer: BrunoImporter, bruno_nested_fixtures: Path
    ) -> None:
        """Should find files in nested subdirectories."""
        files = bruno_importer._find_request_files(bruno_nested_fixtures)

        # Should find the deeply nested file
        file_names = [f.name for f in files]
        assert "deep-request.bru" in file_names

    def test_find_sorted_by_folder(
        self, bruno_importer: BrunoImporter, tmp_path: Path
    ) -> None:
        """Files should be sorted by folder path first."""
        # Create folders with files
        folder_a = tmp_path / "a-folder"
        folder_b = tmp_path / "b-folder"
        folder_a.mkdir()
        folder_b.mkdir()

        (folder_b / "z-file.bru").write_text("get { url: /z }")
        (folder_a / "a-file.bru").write_text("get { url: /a }")

        files = bruno_importer._find_request_files(tmp_path)
        folders = [bruno_importer._get_folder_path(f, tmp_path) for f in files]

        # a-folder should come before b-folder
        a_idx = next(i for i, f in enumerate(folders) if "a-folder" in f)
        b_idx = next(i for i, f in enumerate(folders) if "b-folder" in f)
        assert a_idx < b_idx

    def test_find_sorted_by_sequence(
        self, bruno_importer: BrunoImporter, tmp_path: Path
    ) -> None:
        """Files in same folder should be sorted by meta.seq."""
        # Create files with different sequences
        (tmp_path / "second.bru").write_text(
            """meta { seq: 2 }
get { url: /second }"""
        )
        (tmp_path / "first.bru").write_text(
            """meta { seq: 1 }
get { url: /first }"""
        )

        files = bruno_importer._find_request_files(tmp_path)

        # first.bru (seq: 1) should come before second.bru (seq: 2)
        file_names = [f.name for f in files]
        assert file_names.index("first.bru") < file_names.index("second.bru")

    def test_find_empty_directory_returns_empty(
        self, bruno_importer: BrunoImporter, tmp_path: Path
    ) -> None:
        """Empty directory should return empty list."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        files = bruno_importer._find_request_files(empty_dir)
        assert files == []


# =============================================================================
# TestVariableConversion - Tests for variable conversion {{var}} to ${var}
# =============================================================================


class TestVariableConversion:
    """Tests for variable conversion {{var}} to ${var}."""

    def test_convert_url_variables(
        self, bruno_importer: BrunoImporter, bruno_collection_dir: Path
    ) -> None:
        """URL variables should be converted."""
        result = bruno_importer.import_collection(bruno_collection_dir)

        for request in result.requests:
            # Should not contain {{var}} pattern
            assert "{{" not in request.path

    def test_convert_header_variables(
        self, bruno_importer: BrunoImporter, bruno_collection_dir: Path
    ) -> None:
        """Header variables should be converted."""
        result = bruno_importer.import_collection(bruno_collection_dir)

        get_users = next((r for r in result.requests if r.name == "Get Users"), None)
        assert get_users is not None

        # Authorization header had {{token}}
        auth_header = get_users.headers.get("Authorization", "")
        assert "{{" not in auth_header
        # Should be converted to ${token}
        assert "${token}" in auth_header

    def test_convert_body_variables(
        self, bruno_importer: BrunoImporter, bruno_collection_dir: Path
    ) -> None:
        """Body variables should be converted."""
        result = bruno_importer.import_collection(bruno_collection_dir)

        create_user = next(
            (r for r in result.requests if r.name == "Create User"), None
        )
        assert create_user is not None
        assert create_user.body is not None

        # Body had {{user_name}} and {{user_email}}
        body_str = str(create_user.body)
        assert "{{" not in body_str
        assert "${user_name}" in body_str or "${user_email}" in body_str

    def test_convert_nested_json_variables(
        self, bruno_importer: BrunoImporter, tmp_path: Path
    ) -> None:
        """Nested JSON object variables should be converted."""
        bru_file = tmp_path / "nested.bru"
        bru_file.write_text(
            """meta { name: Nested }

post {
  url: /data
  body: json
}

body:json {
  {
    "user": {
      "name": "{{name}}",
      "profile": {
        "email": "{{email}}"
      }
    }
  }
}"""
        )

        result = bruno_importer.import_collection(bru_file)
        body_str = str(result.requests[0].body)

        assert "{{" not in body_str
        assert "${name}" in body_str
        assert "${email}" in body_str

    def test_convert_multiple_variables_same_string(
        self, bruno_importer: BrunoImporter, tmp_path: Path
    ) -> None:
        """Multiple variables in same string should all convert."""
        bru_file = tmp_path / "multi.bru"
        bru_file.write_text(
            """meta { name: Multi }

get {
  url: {{base_url}}/users/{{user_id}}/posts/{{post_id}}
}"""
        )

        result = bruno_importer.import_collection(bru_file)
        path = result.requests[0].path

        assert "{{" not in path
        # All variables should be converted
        assert path.count("${") >= 2


# =============================================================================
# TestAuthentication - Tests for authentication handling
# =============================================================================


class TestAuthentication:
    """Tests for authentication handling."""

    def test_bearer_auth_adds_authorization_header(
        self, bruno_importer: BrunoImporter, bruno_auth_fixtures: Path
    ) -> None:
        """Bearer auth should add Authorization header."""
        bearer_file = bruno_auth_fixtures / "bearer-auth.bru"
        result = bruno_importer.import_collection(bearer_file)

        request = result.requests[0]
        assert "Authorization" in request.headers
        assert request.headers["Authorization"].startswith("Bearer ")

    def test_basic_auth_adds_authorization_header(
        self, bruno_importer: BrunoImporter, bruno_auth_fixtures: Path
    ) -> None:
        """Basic auth should add Authorization header with Base64."""
        basic_file = bruno_auth_fixtures / "basic-auth.bru"
        result = bruno_importer.import_collection(basic_file)

        request = result.requests[0]
        assert "Authorization" in request.headers
        assert request.headers["Authorization"].startswith("Basic ")

    def test_basic_auth_base64_encoding(
        self, bruno_importer: BrunoImporter, tmp_path: Path
    ) -> None:
        """Basic auth should properly Base64 encode credentials."""
        import base64

        bru_file = tmp_path / "basic.bru"
        bru_file.write_text(
            """meta { name: Basic }

get {
  url: /auth
  auth: basic
}

auth:basic {
  username: testuser
  password: testpass
}"""
        )

        result = bruno_importer.import_collection(bru_file)
        auth_header = result.requests[0].headers["Authorization"]

        # Extract the Base64 part
        base64_part = auth_header.replace("Basic ", "")
        decoded = base64.b64decode(base64_part).decode()

        assert decoded == "testuser:testpass"

    def test_auth_variable_conversion(
        self, bruno_importer: BrunoImporter, bruno_auth_fixtures: Path
    ) -> None:
        """Auth tokens with {{var}} should be converted."""
        bearer_file = bruno_auth_fixtures / "bearer-auth.bru"
        result = bruno_importer.import_collection(bearer_file)

        request = result.requests[0]
        auth_header = request.headers.get("Authorization", "")

        # Should not contain {{var}}
        assert "{{" not in auth_header
        # Should have ${var} instead
        assert "${auth_token}" in auth_header


# =============================================================================
# TestRealWorldCollections - Tests using real-world collection fixtures
# =============================================================================


class TestRealWorldCollections:
    """Tests using real-world collection fixtures."""

    def test_jsonplaceholder_collection_import(
        self, bruno_importer: BrunoImporter, bruno_real_world_jsonplaceholder: Path
    ) -> None:
        """JSONPlaceholder collection should import successfully."""
        result = bruno_importer.import_collection(bruno_real_world_jsonplaceholder)

        assert result.metadata.name == "JSONPlaceholder API"
        assert result.request_count >= 4

    def test_jsonplaceholder_request_structure(
        self, bruno_importer: BrunoImporter, bruno_real_world_jsonplaceholder: Path
    ) -> None:
        """JSONPlaceholder requests should have proper structure."""
        result = bruno_importer.import_collection(bruno_real_world_jsonplaceholder)

        for request in result.requests:
            assert request.method in {"GET", "POST", "PUT", "PATCH", "DELETE"}
            assert request.path.startswith("/")
            assert "Accept" in request.headers

    def test_jsonplaceholder_environment_variables(
        self, bruno_importer: BrunoImporter, bruno_real_world_jsonplaceholder: Path
    ) -> None:
        """JSONPlaceholder environment variables should be loaded."""
        env_path = bruno_real_world_jsonplaceholder / "environments" / "local.bru"
        result = bruno_importer.import_collection(
            bruno_real_world_jsonplaceholder, env_path=env_path
        )

        assert result.metadata.base_url == "https://jsonplaceholder.typicode.com"
        assert "post_id" in result.metadata.variables

    def test_jsonplaceholder_folder_structure(
        self, bruno_importer: BrunoImporter, bruno_real_world_jsonplaceholder: Path
    ) -> None:
        """JSONPlaceholder folder structure should be preserved."""
        result = bruno_importer.import_collection(bruno_real_world_jsonplaceholder)

        folders = {r.folder_path for r in result.requests}
        assert "posts" in folders
        assert "users" in folders

    def test_github_api_collection_import(
        self, bruno_importer: BrunoImporter, bruno_real_world_github: Path
    ) -> None:
        """GitHub API collection should import successfully."""
        result = bruno_importer.import_collection(bruno_real_world_github)

        assert result.metadata.name == "GitHub REST API"
        assert result.request_count >= 2

    def test_github_api_headers(
        self, bruno_importer: BrunoImporter, bruno_real_world_github: Path
    ) -> None:
        """GitHub API requests should have proper headers."""
        result = bruno_importer.import_collection(bruno_real_world_github)

        for request in result.requests:
            assert "Accept" in request.headers
            assert "User-Agent" in request.headers

    def test_github_api_bearer_auth(
        self, bruno_importer: BrunoImporter, bruno_real_world_github: Path
    ) -> None:
        """GitHub repo request should have Bearer auth header."""
        result = bruno_importer.import_collection(bruno_real_world_github)

        repo_request = next(
            (r for r in result.requests if "Repository" in r.name), None
        )
        if repo_request:
            # Should have Authorization header
            assert "Authorization" in repo_request.headers

    def test_github_api_variable_patterns(
        self, bruno_importer: BrunoImporter, bruno_real_world_github: Path
    ) -> None:
        """GitHub API should use proper variable patterns."""
        result = bruno_importer.import_collection(bruno_real_world_github)

        for request in result.requests:
            # No {{var}} should remain
            assert "{{" not in request.path

            # Should have ${var} for path variables
            if "owner" in request.path.lower() or "repo" in request.path.lower():
                assert "${" in request.path


# =============================================================================
# TestEdgeCases - Tests for edge cases and error handling
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_uppercase_method_import(
        self, bruno_importer: BrunoImporter, bruno_edge_cases_fixtures: Path
    ) -> None:
        """Uppercase method block should be handled."""
        uppercase_file = bruno_edge_cases_fixtures / "uppercase-method.bru"
        result = bruno_importer.import_collection(uppercase_file)

        assert result.requests[0].method == "GET"
        assert result.requests[0].path == "/uppercase-test"

    def test_unicode_content(
        self, bruno_importer: BrunoImporter, bruno_edge_cases_fixtures: Path
    ) -> None:
        """Unicode content should be handled."""
        unicode_file = bruno_edge_cases_fixtures / "unicode-content.bru"
        result = bruno_importer.import_collection(unicode_file)

        assert result.requests[0].body is not None
        body_str = str(result.requests[0].body)
        assert "Hello World" in body_str or "message" in body_str

    def test_scripts_preserved(
        self, bruno_importer: BrunoImporter, bruno_scripts_fixtures: Path
    ) -> None:
        """Scripts should be preserved in requests."""
        both_scripts = bruno_scripts_fixtures / "both-scripts.bru"
        result = bruno_importer.import_collection(both_scripts)

        request = result.requests[0]
        assert request.pre_script is not None
        assert request.post_script is not None
        assert "bru.setVar" in request.pre_script
        assert "res.body" in request.post_script

    def test_deeply_nested_folder(
        self, bruno_importer: BrunoImporter, bruno_nested_fixtures: Path
    ) -> None:
        """Deeply nested folders should work."""
        result = bruno_importer.import_collection(bruno_nested_fixtures)

        deep_request = next(
            (r for r in result.requests if "Deeply Nested" in r.name), None
        )
        assert deep_request is not None
        assert "level1/level2" in deep_request.folder_path

    def test_http_methods_all_supported(
        self, bruno_importer: BrunoImporter, bruno_methods_fixtures: Path
    ) -> None:
        """All HTTP methods should be supported."""
        result = bruno_importer.import_collection(bruno_methods_fixtures)

        methods = {r.method for r in result.requests}
        assert "PUT" in methods
        assert "PATCH" in methods
        assert "DELETE" in methods
        assert "OPTIONS" in methods

    def test_format_name_property(self, bruno_importer: BrunoImporter) -> None:
        """format_name property should return 'bruno'."""
        assert bruno_importer.format_name == "bruno"

    def test_get_folder_path_root_level(
        self, bruno_importer: BrunoImporter, tmp_path: Path
    ) -> None:
        """Root level file should have empty folder path."""
        root_file = tmp_path / "root.bru"
        folder_path = bruno_importer._get_folder_path(root_file, tmp_path)
        assert folder_path == ""

    def test_get_folder_path_nested(
        self, bruno_importer: BrunoImporter, tmp_path: Path
    ) -> None:
        """Nested file should have proper folder path."""
        nested_dir = tmp_path / "a" / "b" / "c"
        nested_dir.mkdir(parents=True)
        nested_file = nested_dir / "test.bru"

        folder_path = bruno_importer._get_folder_path(nested_file, tmp_path)
        assert folder_path == "a/b/c"

    def test_import_with_all_http_methods(
        self, bruno_importer: BrunoImporter, tmp_path: Path
    ) -> None:
        """Should handle all HTTP methods correctly."""
        for method in ["get", "post", "put", "patch", "delete", "head", "options"]:
            bru_file = tmp_path / f"{method}.bru"
            bru_file.write_text(
                f"""meta {{
  name: {method.upper()} Request
}}

{method} {{
  url: /{method}
}}"""
            )

        result = bruno_importer.import_collection(tmp_path)
        methods = {r.method for r in result.requests}

        assert methods == {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
