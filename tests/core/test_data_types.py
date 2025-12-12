"""Unit tests for data_types module."""

import pytest

from collection_importer.core.data_types import (
    CollectionMetadata,
    CollectionRequest,
    ParsedCollection,
)


class TestCollectionRequest:
    """Tests for CollectionRequest dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic request creation with minimal fields."""
        request = CollectionRequest(
            name="Get User",
            method="GET",
            path="/users/1",
        )
        assert request.name == "Get User"
        assert request.method == "GET"
        assert request.path == "/users/1"
        assert request.headers == {}
        assert request.body is None
        assert request.body_type == "none"
        assert request.auth_type is None
        assert request.auth_value is None
        assert request.folder_path == ""
        assert request.sequence == 0
        assert request.pre_script is None
        assert request.post_script is None

    def test_full_creation(self) -> None:
        """Test request creation with all fields."""
        request = CollectionRequest(
            name="Create User",
            method="POST",
            path="/users",
            headers={"Content-Type": "application/json"},
            body={"name": "John"},
            body_type="json",
            auth_type="bearer",
            auth_value="token123",
            folder_path="users",
            sequence=1,
            pre_script="console.log('pre')",
            post_script="console.log('post')",
        )
        assert request.name == "Create User"
        assert request.method == "POST"
        assert request.headers == {"Content-Type": "application/json"}
        assert request.body == {"name": "John"}
        assert request.body_type == "json"
        assert request.auth_type == "bearer"
        assert request.auth_value == "token123"
        assert request.folder_path == "users"
        assert request.sequence == 1
        assert request.pre_script == "console.log('pre')"
        assert request.post_script == "console.log('post')"

    # Method validation tests

    def test_method_normalized_to_uppercase(self) -> None:
        """Test that method is normalized to uppercase."""
        request = CollectionRequest(name="Test", method="get", path="/test")
        assert request.method == "GET"

    def test_method_mixed_case_normalized(self) -> None:
        """Test mixed case method normalization."""
        request = CollectionRequest(name="Test", method="pOsT", path="/test")
        assert request.method == "POST"

    @pytest.mark.parametrize(
        "method",
        ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    )
    def test_valid_methods(self, method: str) -> None:
        """Test all valid HTTP methods are accepted."""
        request = CollectionRequest(name="Test", method=method, path="/test")
        assert request.method == method

    def test_invalid_method_raises_error(self) -> None:
        """Test that invalid method raises ValueError."""
        with pytest.raises(ValueError, match="Invalid HTTP method"):
            CollectionRequest(name="Test", method="INVALID", path="/test")

    def test_invalid_method_connect_raises_error(self) -> None:
        """Test that CONNECT method raises ValueError."""
        with pytest.raises(ValueError, match="Invalid HTTP method"):
            CollectionRequest(name="Test", method="CONNECT", path="/test")

    # Path validation tests

    def test_path_empty_normalized_to_slash(self) -> None:
        """Test empty path is normalized to /."""
        request = CollectionRequest(name="Test", method="GET", path="")
        assert request.path == "/"

    def test_path_whitespace_normalized_to_slash(self) -> None:
        """Test whitespace path is normalized to /."""
        request = CollectionRequest(name="Test", method="GET", path="   ")
        assert request.path == "/"

    def test_path_without_leading_slash_gets_slash(self) -> None:
        """Test path without leading slash gets one added."""
        request = CollectionRequest(name="Test", method="GET", path="users")
        assert request.path == "/users"

    def test_path_with_leading_slash_unchanged(self) -> None:
        """Test path with leading slash is unchanged."""
        request = CollectionRequest(name="Test", method="GET", path="/users")
        assert request.path == "/users"

    def test_path_with_variables(self) -> None:
        """Test path with variables is preserved."""
        request = CollectionRequest(
            name="Test", method="GET", path="/users/${user_id}"
        )
        assert request.path == "/users/${user_id}"

    # Body type validation tests

    @pytest.mark.parametrize("body_type", ["json", "form", "raw", "none"])
    def test_valid_body_types(self, body_type: str) -> None:
        """Test all valid body types are accepted."""
        request = CollectionRequest(
            name="Test", method="POST", path="/test", body_type=body_type
        )
        assert request.body_type == body_type

    def test_invalid_body_type_raises_error(self) -> None:
        """Test that invalid body type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid body_type"):
            CollectionRequest(
                name="Test", method="POST", path="/test", body_type="xml"
            )

    # Auth type validation tests

    @pytest.mark.parametrize("auth_type", ["bearer", "basic", "apikey"])
    def test_valid_auth_types(self, auth_type: str) -> None:
        """Test all valid auth types are accepted."""
        request = CollectionRequest(
            name="Test", method="GET", path="/test", auth_type=auth_type
        )
        assert request.auth_type == auth_type

    def test_auth_type_none_is_valid(self) -> None:
        """Test that None auth_type is valid."""
        request = CollectionRequest(
            name="Test", method="GET", path="/test", auth_type=None
        )
        assert request.auth_type is None

    def test_invalid_auth_type_raises_error(self) -> None:
        """Test that invalid auth type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid auth_type"):
            CollectionRequest(
                name="Test", method="GET", path="/test", auth_type="oauth2"
            )

    # Property tests

    def test_full_name_without_folder(self) -> None:
        """Test full_name returns just name when no folder."""
        request = CollectionRequest(name="Get User", method="GET", path="/users")
        assert request.full_name == "Get User"

    def test_full_name_with_folder(self) -> None:
        """Test full_name includes folder path."""
        request = CollectionRequest(
            name="Get User", method="GET", path="/users", folder_path="auth/users"
        )
        assert request.full_name == "auth/users/Get User"

    def test_has_body_false_when_body_none(self) -> None:
        """Test has_body is False when body is None."""
        request = CollectionRequest(name="Test", method="GET", path="/test")
        assert request.has_body is False

    def test_has_body_false_when_body_type_none(self) -> None:
        """Test has_body is False when body_type is none."""
        request = CollectionRequest(
            name="Test",
            method="POST",
            path="/test",
            body={"data": "value"},
            body_type="none",
        )
        assert request.has_body is False

    def test_has_body_true_with_json_body(self) -> None:
        """Test has_body is True with JSON body."""
        request = CollectionRequest(
            name="Test",
            method="POST",
            path="/test",
            body={"name": "John"},
            body_type="json",
        )
        assert request.has_body is True

    def test_has_body_true_with_raw_body(self) -> None:
        """Test has_body is True with raw body."""
        request = CollectionRequest(
            name="Test",
            method="POST",
            path="/test",
            body="raw data",
            body_type="raw",
        )
        assert request.has_body is True

    def test_has_body_true_with_form_body(self) -> None:
        """Test has_body is True with form body."""
        request = CollectionRequest(
            name="Test",
            method="POST",
            path="/test",
            body={"field": "value"},
            body_type="form",
        )
        assert request.has_body is True


class TestCollectionMetadata:
    """Tests for CollectionMetadata dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic metadata creation with minimal fields."""
        metadata = CollectionMetadata(name="Test Collection")
        assert metadata.name == "Test Collection"
        assert metadata.description == ""
        assert metadata.base_url is None
        assert metadata.variables == {}
        assert metadata.format == "unknown"
        assert metadata.source_path == ""

    def test_full_creation(self) -> None:
        """Test metadata creation with all fields."""
        metadata = CollectionMetadata(
            name="API Collection",
            description="My API tests",
            base_url="http://localhost:8080",
            variables={"api_key": "secret123"},
            format="bruno",
            source_path="/path/to/collection",
        )
        assert metadata.name == "API Collection"
        assert metadata.description == "My API tests"
        assert metadata.base_url == "http://localhost:8080"
        assert metadata.variables == {"api_key": "secret123"}
        assert metadata.format == "bruno"
        assert metadata.source_path == "/path/to/collection"

    def test_variables_default_factory(self) -> None:
        """Test variables uses default factory (not shared instance)."""
        meta1 = CollectionMetadata(name="Test1")
        meta2 = CollectionMetadata(name="Test2")
        meta1.variables["key"] = "value"
        assert "key" not in meta2.variables


class TestParsedCollection:
    """Tests for ParsedCollection dataclass."""

    @pytest.fixture
    def sample_requests(self) -> list[CollectionRequest]:
        """Create sample requests for testing."""
        return [
            CollectionRequest(
                name="Get Users",
                method="GET",
                path="/users",
                folder_path="",
                sequence=0,
            ),
            CollectionRequest(
                name="Create User",
                method="POST",
                path="/users",
                folder_path="users",
                sequence=1,
            ),
            CollectionRequest(
                name="Get User",
                method="GET",
                path="/users/${id}",
                folder_path="users",
                sequence=2,
            ),
            CollectionRequest(
                name="Login",
                method="POST",
                path="/auth/login",
                folder_path="auth",
                sequence=3,
            ),
        ]

    @pytest.fixture
    def sample_collection(
        self, sample_requests: list[CollectionRequest]
    ) -> ParsedCollection:
        """Create sample collection for testing."""
        return ParsedCollection(
            metadata=CollectionMetadata(
                name="Test API",
                base_url="http://localhost:8080",
                variables={"api_key": "test123"},
            ),
            requests=sample_requests,
        )

    def test_basic_creation(self) -> None:
        """Test basic collection creation."""
        collection = ParsedCollection(
            metadata=CollectionMetadata(name="Test"),
            requests=[],
        )
        assert collection.metadata.name == "Test"
        assert collection.requests == []

    def test_request_count_empty(self) -> None:
        """Test request_count with empty collection."""
        collection = ParsedCollection(
            metadata=CollectionMetadata(name="Test"),
            requests=[],
        )
        assert collection.request_count == 0

    def test_request_count(
        self, sample_collection: ParsedCollection
    ) -> None:
        """Test request_count with requests."""
        assert sample_collection.request_count == 4

    def test_get_requests_by_folder_empty(self) -> None:
        """Test get_requests_by_folder with empty collection."""
        collection = ParsedCollection(
            metadata=CollectionMetadata(name="Test"),
            requests=[],
        )
        assert collection.get_requests_by_folder() == {}

    def test_get_requests_by_folder(
        self, sample_collection: ParsedCollection
    ) -> None:
        """Test get_requests_by_folder groups correctly."""
        groups = sample_collection.get_requests_by_folder()

        assert "" in groups
        assert len(groups[""]) == 1
        assert groups[""][0].name == "Get Users"

        assert "users" in groups
        assert len(groups["users"]) == 2
        assert groups["users"][0].name == "Create User"
        assert groups["users"][1].name == "Get User"

        assert "auth" in groups
        assert len(groups["auth"]) == 1
        assert groups["auth"][0].name == "Login"

    def test_get_all_variables_empty(self) -> None:
        """Test get_all_variables with no variables."""
        collection = ParsedCollection(
            metadata=CollectionMetadata(name="Test"),
            requests=[
                CollectionRequest(name="Test", method="GET", path="/test"),
            ],
        )
        assert collection.get_all_variables() == set()

    def test_get_all_variables_from_path(self) -> None:
        """Test get_all_variables extracts from path."""
        collection = ParsedCollection(
            metadata=CollectionMetadata(name="Test"),
            requests=[
                CollectionRequest(
                    name="Test", method="GET", path="/users/${user_id}"
                ),
            ],
        )
        assert collection.get_all_variables() == {"user_id"}

    def test_get_all_variables_from_headers(self) -> None:
        """Test get_all_variables extracts from headers."""
        collection = ParsedCollection(
            metadata=CollectionMetadata(name="Test"),
            requests=[
                CollectionRequest(
                    name="Test",
                    method="GET",
                    path="/test",
                    headers={"Authorization": "Bearer ${token}"},
                ),
            ],
        )
        assert collection.get_all_variables() == {"token"}

    def test_get_all_variables_from_string_body(self) -> None:
        """Test get_all_variables extracts from string body."""
        collection = ParsedCollection(
            metadata=CollectionMetadata(name="Test"),
            requests=[
                CollectionRequest(
                    name="Test",
                    method="POST",
                    path="/test",
                    body='{"name": "${username}"}',
                    body_type="raw",
                ),
            ],
        )
        assert collection.get_all_variables() == {"username"}

    def test_get_all_variables_from_dict_body(self) -> None:
        """Test get_all_variables extracts from dict body."""
        collection = ParsedCollection(
            metadata=CollectionMetadata(name="Test"),
            requests=[
                CollectionRequest(
                    name="Test",
                    method="POST",
                    path="/test",
                    body={"name": "${username}", "email": "${email}"},
                    body_type="json",
                ),
            ],
        )
        variables = collection.get_all_variables()
        assert "username" in variables
        assert "email" in variables

    def test_get_all_variables_multiple_sources(
        self, sample_collection: ParsedCollection
    ) -> None:
        """Test get_all_variables from multiple sources."""
        # Add request with variables in different places
        sample_collection.requests.append(
            CollectionRequest(
                name="Complex",
                method="POST",
                path="/api/${version}/users/${user_id}",
                headers={"Authorization": "Bearer ${token}"},
                body={"data": "${payload}"},
                body_type="json",
            )
        )
        variables = sample_collection.get_all_variables()
        assert "id" in variables  # from existing /users/${id}
        assert "version" in variables
        assert "user_id" in variables
        assert "token" in variables
        assert "payload" in variables

    def test_requests_default_factory(self) -> None:
        """Test requests uses default factory (not shared instance)."""
        col1 = ParsedCollection(metadata=CollectionMetadata(name="Test1"))
        col2 = ParsedCollection(metadata=CollectionMetadata(name="Test2"))
        col1.requests.append(
            CollectionRequest(name="Test", method="GET", path="/test")
        )
        assert len(col2.requests) == 0
