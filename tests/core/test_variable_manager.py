"""Unit tests for variable_manager module."""

import pytest

from collection_importer.core.variable_manager import (
    VariableManager,
    convert_payload,
    convert_variables,
)


class TestVariableManagerConvertVariableSyntax:
    """Tests for VariableManager.convert_variable_syntax method."""

    @pytest.fixture
    def vm(self) -> VariableManager:
        """Create VariableManager instance."""
        return VariableManager()

    def test_basic_conversion(self, vm: VariableManager) -> None:
        """Test basic {{var}} to ${var} conversion."""
        result = vm.convert_variable_syntax("{{base_url}}/users")
        assert result == "${base_url}/users"

    def test_multiple_variables(self, vm: VariableManager) -> None:
        """Test conversion of multiple variables."""
        result = vm.convert_variable_syntax("{{base_url}}/users/{{id}}")
        assert result == "${base_url}/users/${id}"

    def test_no_variables(self, vm: VariableManager) -> None:
        """Test text without variables is unchanged."""
        result = vm.convert_variable_syntax("https://example.com/users")
        assert result == "https://example.com/users"

    def test_none_input(self, vm: VariableManager) -> None:
        """Test None input returns empty string."""
        result = vm.convert_variable_syntax(None)  # type: ignore
        assert result == ""

    def test_non_string_input_converted(self, vm: VariableManager) -> None:
        """Test non-string input is converted to string."""
        result = vm.convert_variable_syntax(123)  # type: ignore
        assert result == "123"

    def test_zero_value_not_empty(self, vm: VariableManager) -> None:
        """Test that 0 is not treated as empty."""
        result = vm.convert_variable_syntax(0)  # type: ignore
        assert result == "0"

    def test_false_value_not_empty(self, vm: VariableManager) -> None:
        """Test that False is not treated as empty."""
        result = vm.convert_variable_syntax(False)  # type: ignore
        assert result == "False"

    def test_empty_string(self, vm: VariableManager) -> None:
        """Test empty string input."""
        result = vm.convert_variable_syntax("")
        assert result == ""

    def test_already_converted_unchanged(self, vm: VariableManager) -> None:
        """Test already converted ${var} syntax is unchanged."""
        result = vm.convert_variable_syntax("${base_url}/users")
        assert result == "${base_url}/users"

    def test_mixed_syntax(self, vm: VariableManager) -> None:
        """Test mixed {{var}} and ${var} syntax."""
        result = vm.convert_variable_syntax("{{base_url}}/users/${id}")
        assert result == "${base_url}/users/${id}"

    def test_underscore_in_variable(self, vm: VariableManager) -> None:
        """Test variable with underscore."""
        result = vm.convert_variable_syntax("{{api_key}}")
        assert result == "${api_key}"

    def test_variable_at_start(self, vm: VariableManager) -> None:
        """Test variable at start of string."""
        result = vm.convert_variable_syntax("{{host}}/api")
        assert result == "${host}/api"

    def test_variable_at_end(self, vm: VariableManager) -> None:
        """Test variable at end of string."""
        result = vm.convert_variable_syntax("/users/{{id}}")
        assert result == "/users/${id}"

    def test_variable_only(self, vm: VariableManager) -> None:
        """Test string with only variable."""
        result = vm.convert_variable_syntax("{{token}}")
        assert result == "${token}"


class TestVariableManagerConvertPayloadVariables:
    """Tests for VariableManager.convert_payload_variables method."""

    @pytest.fixture
    def vm(self) -> VariableManager:
        """Create VariableManager instance."""
        return VariableManager()

    def test_dict_payload(self, vm: VariableManager) -> None:
        """Test converting dict payload."""
        payload = {"name": "{{username}}", "id": "{{user_id}}"}
        result = vm.convert_payload_variables(payload)
        assert result == {"name": "${username}", "id": "${user_id}"}

    def test_list_payload(self, vm: VariableManager) -> None:
        """Test converting list payload."""
        payload = ["{{item1}}", "{{item2}}"]
        result = vm.convert_payload_variables(payload)
        assert result == ["${item1}", "${item2}"]

    def test_nested_dict(self, vm: VariableManager) -> None:
        """Test converting nested dict."""
        payload = {"user": {"name": "{{username}}", "email": "{{email}}"}}
        result = vm.convert_payload_variables(payload)
        assert result == {"user": {"name": "${username}", "email": "${email}"}}

    def test_nested_list_in_dict(self, vm: VariableManager) -> None:
        """Test converting list nested in dict."""
        payload = {"items": ["{{item1}}", "{{item2}}"]}
        result = vm.convert_payload_variables(payload)
        assert result == {"items": ["${item1}", "${item2}"]}

    def test_dict_in_list(self, vm: VariableManager) -> None:
        """Test converting dict nested in list."""
        payload = [{"name": "{{name}}"}]
        result = vm.convert_payload_variables(payload)
        assert result == [{"name": "${name}"}]

    def test_string_payload(self, vm: VariableManager) -> None:
        """Test converting string payload."""
        result = vm.convert_payload_variables("{{username}}")
        assert result == "${username}"

    def test_non_string_values_unchanged(self, vm: VariableManager) -> None:
        """Test non-string values are unchanged."""
        payload = {"count": 10, "active": True, "items": None}
        result = vm.convert_payload_variables(payload)
        assert result == {"count": 10, "active": True, "items": None}

    def test_deeply_nested(self, vm: VariableManager) -> None:
        """Test deeply nested structure."""
        payload = {"a": {"b": {"c": {"d": "{{deep}}"}}}}
        result = vm.convert_payload_variables(payload)
        assert result == {"a": {"b": {"c": {"d": "${deep}"}}}}


class TestVariableManagerExtractVariables:
    """Tests for VariableManager.extract_variables method."""

    @pytest.fixture
    def vm(self) -> VariableManager:
        """Create VariableManager instance."""
        return VariableManager()

    def test_extract_double_brace(self, vm: VariableManager) -> None:
        """Test extracting {{var}} variables."""
        result = vm.extract_variables("{{base_url}}/users/{{id}}")
        assert result == {"base_url", "id"}

    def test_extract_dollar_brace(self, vm: VariableManager) -> None:
        """Test extracting ${var} variables."""
        result = vm.extract_variables("${base_url}/users/${id}")
        assert result == {"base_url", "id"}

    def test_extract_mixed(self, vm: VariableManager) -> None:
        """Test extracting mixed syntax variables."""
        result = vm.extract_variables("{{base_url}}/users/${id}")
        assert result == {"base_url", "id"}

    def test_extract_none_input(self, vm: VariableManager) -> None:
        """Test None input returns empty set."""
        result = vm.extract_variables(None)  # type: ignore
        assert result == set()

    def test_extract_no_variables(self, vm: VariableManager) -> None:
        """Test text without variables returns empty set."""
        result = vm.extract_variables("https://example.com/users")
        assert result == set()

    def test_extract_duplicate_variables(self, vm: VariableManager) -> None:
        """Test duplicate variables are deduplicated."""
        result = vm.extract_variables("{{id}}/{{id}}")
        assert result == {"id"}


class TestVariableManagerIsSensitiveVariable:
    """Tests for VariableManager.is_sensitive_variable method."""

    @pytest.fixture
    def vm(self) -> VariableManager:
        """Create VariableManager instance."""
        return VariableManager()

    @pytest.mark.parametrize(
        "name",
        [
            "token",
            "auth_token",
            "access_token",
            "secret",
            "client_secret",
            "password",
            "user_password",
            "key",
            "api_key",
            "apikey",
            "auth",
            "oauth_auth",
            "credential",
            "private",
            "private_key",
        ],
    )
    def test_sensitive_variables(self, vm: VariableManager, name: str) -> None:
        """Test sensitive variable names are detected."""
        assert vm.is_sensitive_variable(name) is True

    @pytest.mark.parametrize(
        "name",
        [
            "user_id",
            "username",
            "base_url",
            "host",
            "port",
            "email",
            "tokenize",  # Should not match as "token" is not a word boundary
        ],
    )
    def test_non_sensitive_variables(self, vm: VariableManager, name: str) -> None:
        """Test non-sensitive variable names are not detected."""
        assert vm.is_sensitive_variable(name) is False

    def test_case_insensitive(self, vm: VariableManager) -> None:
        """Test detection is case insensitive."""
        assert vm.is_sensitive_variable("TOKEN") is True
        assert vm.is_sensitive_variable("Auth_Token") is True
        assert vm.is_sensitive_variable("API_KEY") is True


class TestVariableManagerExtractPathFromUrl:
    """Tests for VariableManager.extract_path_from_url method."""

    @pytest.fixture
    def vm(self) -> VariableManager:
        """Create VariableManager instance."""
        return VariableManager()

    def test_full_url(self, vm: VariableManager) -> None:
        """Test extracting path from full URL."""
        result = vm.extract_path_from_url("https://api.example.com/users/123")
        assert result == "/users/123"

    def test_url_with_variables(self, vm: VariableManager) -> None:
        """Test extracting path from URL with variables."""
        result = vm.extract_path_from_url("{{base_url}}/users/{{id}}")
        assert result == "/users/${id}"

    def test_empty_url(self, vm: VariableManager) -> None:
        """Test empty URL returns /."""
        result = vm.extract_path_from_url("")
        assert result == "/"

    def test_none_url(self, vm: VariableManager) -> None:
        """Test None URL returns /."""
        result = vm.extract_path_from_url(None)  # type: ignore
        assert result == "/"

    def test_whitespace_only(self, vm: VariableManager) -> None:
        """Test whitespace-only URL returns /."""
        result = vm.extract_path_from_url("   ")
        assert result == "/"

    def test_just_variable(self, vm: VariableManager) -> None:
        """Test URL that is just a variable returns /."""
        result = vm.extract_path_from_url("{{base_url}}")
        assert result == "/"

    def test_path_only(self, vm: VariableManager) -> None:
        """Test path without host."""
        result = vm.extract_path_from_url("/users/123")
        assert result == "/users/123"

    def test_path_without_leading_slash(self, vm: VariableManager) -> None:
        """Test path without leading slash gets one added."""
        result = vm.extract_path_from_url("users/123")
        assert result == "/users/123"

    def test_url_with_port(self, vm: VariableManager) -> None:
        """Test URL with port."""
        result = vm.extract_path_from_url("http://localhost:8080/api/users")
        assert result == "/api/users"


class TestVariableManagerExtractBaseUrl:
    """Tests for VariableManager.extract_base_url method."""

    @pytest.fixture
    def vm(self) -> VariableManager:
        """Create VariableManager instance."""
        return VariableManager()

    def test_https_url(self, vm: VariableManager) -> None:
        """Test extracting base URL from HTTPS URL."""
        result = vm.extract_base_url("https://api.example.com/users")
        assert result == "https://api.example.com"

    def test_http_url(self, vm: VariableManager) -> None:
        """Test extracting base URL from HTTP URL."""
        result = vm.extract_base_url("http://localhost:8080/api/users")
        assert result == "http://localhost:8080"

    def test_no_path(self, vm: VariableManager) -> None:
        """Test URL without path."""
        result = vm.extract_base_url("https://api.example.com")
        assert result == "https://api.example.com"

    def test_no_protocol(self, vm: VariableManager) -> None:
        """Test URL without protocol returns None."""
        result = vm.extract_base_url("/users/123")
        assert result is None

    def test_variable_url(self, vm: VariableManager) -> None:
        """Test URL with variable returns None."""
        result = vm.extract_base_url("{{base_url}}/users")
        assert result is None


class TestVariableManagerMaskSensitiveValue:
    """Tests for VariableManager.mask_sensitive_value method."""

    @pytest.fixture
    def vm(self) -> VariableManager:
        """Create VariableManager instance."""
        return VariableManager()

    def test_sensitive_masked(self, vm: VariableManager) -> None:
        """Test sensitive value is masked."""
        result = vm.mask_sensitive_value("auth_token", "secret123")
        assert result == "***"

    def test_non_sensitive_unchanged(self, vm: VariableManager) -> None:
        """Test non-sensitive value is unchanged."""
        result = vm.mask_sensitive_value("user_id", "123")
        assert result == "123"

    def test_password_masked(self, vm: VariableManager) -> None:
        """Test password is masked."""
        result = vm.mask_sensitive_value("password", "mypassword")
        assert result == "***"

    def test_api_key_masked(self, vm: VariableManager) -> None:
        """Test api_key is masked."""
        result = vm.mask_sensitive_value("api_key", "key123")
        assert result == "***"


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_convert_variables(self) -> None:
        """Test convert_variables convenience function."""
        result = convert_variables("{{base_url}}/users/{{id}}")
        assert result == "${base_url}/users/${id}"

    def test_convert_payload(self) -> None:
        """Test convert_payload convenience function."""
        result = convert_payload({"name": "{{username}}"})
        assert result == {"name": "${username}"}

    def test_convert_payload_nested(self) -> None:
        """Test convert_payload with nested structure."""
        payload = {"user": {"name": "{{username}}", "token": "{{token}}"}}
        result = convert_payload(payload)
        assert result == {"user": {"name": "${username}", "token": "${token}"}}


class TestInsomniaVariableSyntax:
    """Tests for Insomnia-specific variable syntax with underscore prefix."""

    @pytest.fixture
    def vm(self) -> VariableManager:
        """Create VariableManager instance."""
        return VariableManager()

    def test_insomnia_underscore_prefix_with_spaces(self, vm: VariableManager) -> None:
        """Test {{ _.var }} conversion with spaces."""
        result = vm.convert_variable_syntax("{{ _.base_url }}/v1/user")
        assert result == "${base_url}/v1/user"

    def test_insomnia_underscore_prefix_no_spaces(self, vm: VariableManager) -> None:
        """Test {{_.var}} conversion without spaces."""
        result = vm.convert_variable_syntax("{{_.base_url}}/v1/user")
        assert result == "${base_url}/v1/user"

    def test_insomnia_multiple_variables(self, vm: VariableManager) -> None:
        """Test multiple Insomnia variables."""
        result = vm.convert_variable_syntax("{{ _.base_url }}/users/{{ _.user_id }}")
        assert result == "${base_url}/users/${user_id}"

    def test_insomnia_path_extraction(self, vm: VariableManager) -> None:
        """Test path extraction from Insomnia URL format."""
        result = vm.extract_path_from_url("{{ _.base_url }}/v1/user")
        assert result == "/v1/user"

    def test_insomnia_path_extraction_no_spaces(self, vm: VariableManager) -> None:
        """Test path extraction from Insomnia URL without spaces."""
        result = vm.extract_path_from_url("{{_.base_url}}/v1/users")
        assert result == "/v1/users"

    def test_standard_with_spaces(self, vm: VariableManager) -> None:
        """Test {{ var }} with spaces (no underscore prefix)."""
        result = vm.convert_variable_syntax("{{ base_url }}/users")
        assert result == "${base_url}/users"

    def test_mixed_insomnia_and_standard(self, vm: VariableManager) -> None:
        """Test mixing Insomnia and standard variable syntax."""
        result = vm.convert_variable_syntax("{{ _.base_url }}/users/{{id}}")
        assert result == "${base_url}/users/${id}"

    def test_insomnia_variable_only(self, vm: VariableManager) -> None:
        """Test URL that is just an Insomnia variable returns /."""
        result = vm.extract_path_from_url("{{ _.base_url }}")
        assert result == "/"
