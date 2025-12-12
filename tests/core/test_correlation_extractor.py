"""Tests for correlation_extractor module.

Tests extraction of variable correlations from post-response scripts
and conversion to JSONPath expressions.
"""

import pytest

from collection_importer.core.correlation_extractor import (
    CorrelationExtractor,
    ExtractedCorrelation,
)


class TestExtractedCorrelation:
    """Tests for ExtractedCorrelation dataclass."""

    def test_basic_creation(self) -> None:
        """Test creating an ExtractedCorrelation."""
        corr = ExtractedCorrelation(
            variable_name="user_id",
            json_path="$.id",
            source_format="bruno",
        )
        assert corr.variable_name == "user_id"
        assert corr.json_path == "$.id"
        assert corr.source_format == "bruno"


class TestCorrelationExtractorBruno:
    """Tests for Bruno script correlation extraction."""

    @pytest.fixture
    def extractor(self) -> CorrelationExtractor:
        """Create extractor instance."""
        return CorrelationExtractor()

    def test_extract_simple_data_path(self, extractor: CorrelationExtractor) -> None:
        """Test extracting bru.setVar with data.path."""
        script = """
        const data = res.body;
        bru.setVar('user_id', data.id);
        """
        result = extractor.extract_correlations(script, "bruno")
        assert len(result) == 1
        assert result[0].variable_name == "user_id"
        assert result[0].json_path == "$.id"
        assert result[0].source_format == "bruno"

    def test_extract_nested_path(self, extractor: CorrelationExtractor) -> None:
        """Test extracting nested property paths."""
        script = """
        bru.setVar('auth_token', data.auth.token);
        """
        result = extractor.extract_correlations(script, "bruno")
        assert len(result) == 1
        assert result[0].variable_name == "auth_token"
        assert result[0].json_path == "$.auth.token"

    def test_extract_res_body_syntax(self, extractor: CorrelationExtractor) -> None:
        """Test extracting with res.body prefix."""
        script = """
        bru.setVar('token', res.body.access_token);
        """
        result = extractor.extract_correlations(script, "bruno")
        assert len(result) == 1
        assert result[0].variable_name == "token"
        assert result[0].json_path == "$.access_token"

    def test_extract_array_index(self, extractor: CorrelationExtractor) -> None:
        """Test extracting paths with array indices."""
        script = """
        bru.setVar('first_item', data.items[0].id);
        """
        result = extractor.extract_correlations(script, "bruno")
        assert len(result) == 1
        assert result[0].variable_name == "first_item"
        assert result[0].json_path == "$.items[0].id"

    def test_extract_multiple_correlations(
        self, extractor: CorrelationExtractor
    ) -> None:
        """Test extracting multiple correlations."""
        script = """
        const data = res.body;
        bru.setVar('user_id', data.id);
        bru.setVar('user_name', data.name);
        bru.setVar('email', data.contact.email);
        """
        result = extractor.extract_correlations(script, "bruno")
        assert len(result) == 3
        assert result[0].variable_name == "user_id"
        assert result[1].variable_name == "user_name"
        assert result[2].variable_name == "email"

    def test_extract_double_quotes(self, extractor: CorrelationExtractor) -> None:
        """Test extracting with double quotes."""
        script = '''
        bru.setVar("user_id", data.id);
        '''
        result = extractor.extract_correlations(script, "bruno")
        assert len(result) == 1
        assert result[0].variable_name == "user_id"

    def test_no_correlations_empty_script(
        self, extractor: CorrelationExtractor
    ) -> None:
        """Test no correlations extracted from empty script."""
        result = extractor.extract_correlations("", "bruno")
        assert result == []

    def test_no_correlations_none_script(
        self, extractor: CorrelationExtractor
    ) -> None:
        """Test no correlations extracted from None script."""
        result = extractor.extract_correlations(None, "bruno")
        assert result == []

    def test_no_correlations_no_setvar(self, extractor: CorrelationExtractor) -> None:
        """Test no correlations when setVar not used."""
        script = """
        console.log(data.id);
        const x = data.value;
        """
        result = extractor.extract_correlations(script, "bruno")
        assert result == []


class TestCorrelationExtractorPostman:
    """Tests for Postman script correlation extraction."""

    @pytest.fixture
    def extractor(self) -> CorrelationExtractor:
        """Create extractor instance."""
        return CorrelationExtractor()

    def test_extract_environment_set(self, extractor: CorrelationExtractor) -> None:
        """Test extracting pm.environment.set pattern."""
        script = """
        var jsonData = pm.response.json();
        pm.environment.set('user_id', jsonData.id);
        """
        result = extractor.extract_correlations(script, "postman")
        assert len(result) == 1
        assert result[0].variable_name == "user_id"
        assert result[0].json_path == "$.id"
        assert result[0].source_format == "postman"

    def test_extract_globals_set(self, extractor: CorrelationExtractor) -> None:
        """Test extracting pm.globals.set pattern."""
        script = """
        pm.globals.set('token', jsonData.auth.token);
        """
        result = extractor.extract_correlations(script, "postman")
        assert len(result) == 1
        assert result[0].variable_name == "token"
        assert result[0].json_path == "$.auth.token"

    def test_extract_collection_variables(
        self, extractor: CorrelationExtractor
    ) -> None:
        """Test extracting pm.collectionVariables.set pattern."""
        script = """
        pm.collectionVariables.set('api_key', data.key);
        """
        result = extractor.extract_correlations(script, "postman")
        assert len(result) == 1
        assert result[0].variable_name == "api_key"
        assert result[0].json_path == "$.key"

    def test_extract_nested_path(self, extractor: CorrelationExtractor) -> None:
        """Test extracting nested paths in Postman."""
        script = """
        pm.environment.set('user_name', jsonData.user.profile.name);
        """
        result = extractor.extract_correlations(script, "postman")
        assert len(result) == 1
        assert result[0].json_path == "$.user.profile.name"

    def test_extract_array_index(self, extractor: CorrelationExtractor) -> None:
        """Test extracting array indices in Postman."""
        script = """
        pm.environment.set('first_id', jsonData.results[0].id);
        """
        result = extractor.extract_correlations(script, "postman")
        assert len(result) == 1
        assert result[0].json_path == "$.results[0].id"

    def test_extract_multiple_correlations(
        self, extractor: CorrelationExtractor
    ) -> None:
        """Test extracting multiple Postman correlations."""
        script = """
        var jsonData = pm.response.json();
        pm.environment.set('id', jsonData.id);
        pm.globals.set('token', jsonData.token);
        pm.collectionVariables.set('session', jsonData.session_id);
        """
        result = extractor.extract_correlations(script, "postman")
        assert len(result) == 3

    def test_alternative_json_variables(
        self, extractor: CorrelationExtractor
    ) -> None:
        """Test extracting with alternative JSON variable names."""
        script = """
        pm.environment.set('id1', data.id);
        pm.environment.set('id2', responseJson.id);
        pm.environment.set('id3', json.id);
        """
        result = extractor.extract_correlations(script, "postman")
        assert len(result) == 3


class TestCorrelationExtractorInsomnia:
    """Tests for Insomnia script correlation extraction."""

    @pytest.fixture
    def extractor(self) -> CorrelationExtractor:
        """Create extractor instance."""
        return CorrelationExtractor()

    def test_extract_set_environment_variable(
        self, extractor: CorrelationExtractor
    ) -> None:
        """Test extracting insomnia.setEnvironmentVariable pattern."""
        script = """
        const data = await insomnia.response.json();
        insomnia.setEnvironmentVariable('user_id', data.id);
        """
        result = extractor.extract_correlations(script, "insomnia")
        assert len(result) == 1
        assert result[0].variable_name == "user_id"
        assert result[0].json_path == "$.id"
        assert result[0].source_format == "insomnia"

    def test_extract_nested_path(self, extractor: CorrelationExtractor) -> None:
        """Test extracting nested paths in Insomnia."""
        script = """
        insomnia.setEnvironmentVariable('token', data.auth.access_token);
        """
        result = extractor.extract_correlations(script, "insomnia")
        assert len(result) == 1
        assert result[0].json_path == "$.auth.access_token"

    def test_extract_with_response_variable(
        self, extractor: CorrelationExtractor
    ) -> None:
        """Test extracting with response variable name."""
        script = """
        insomnia.setEnvironmentVariable('id', response.user_id);
        """
        result = extractor.extract_correlations(script, "insomnia")
        assert len(result) == 1
        assert result[0].json_path == "$.user_id"


class TestConvertToJsonpath:
    """Tests for JavaScript to JSONPath conversion."""

    @pytest.fixture
    def extractor(self) -> CorrelationExtractor:
        """Create extractor instance."""
        return CorrelationExtractor()

    def test_simple_property(self, extractor: CorrelationExtractor) -> None:
        """Test simple property conversion."""
        result = extractor._convert_to_jsonpath("id")
        assert result == "$.id"

    def test_nested_property(self, extractor: CorrelationExtractor) -> None:
        """Test nested property conversion."""
        result = extractor._convert_to_jsonpath("user.name")
        assert result == "$.user.name"

    def test_deeply_nested(self, extractor: CorrelationExtractor) -> None:
        """Test deeply nested property conversion."""
        result = extractor._convert_to_jsonpath("response.data.user.profile.name")
        assert result == "$.response.data.user.profile.name"

    def test_array_index(self, extractor: CorrelationExtractor) -> None:
        """Test array index conversion."""
        result = extractor._convert_to_jsonpath("items[0].id")
        assert result == "$.items[0].id"

    def test_multiple_array_indices(self, extractor: CorrelationExtractor) -> None:
        """Test multiple array indices."""
        result = extractor._convert_to_jsonpath("data[0].items[1].value")
        assert result == "$.data[0].items[1].value"

    def test_empty_path_returns_none(self, extractor: CorrelationExtractor) -> None:
        """Test empty path returns None."""
        result = extractor._convert_to_jsonpath("")
        assert result is None

    def test_none_path_returns_none(self, extractor: CorrelationExtractor) -> None:
        """Test None path returns None."""
        result = extractor._convert_to_jsonpath(None)
        assert result is None

    def test_invalid_characters_returns_none(
        self, extractor: CorrelationExtractor
    ) -> None:
        """Test invalid characters return None."""
        result = extractor._convert_to_jsonpath("data.value()")
        assert result is None


class TestHasComplexLogic:
    """Tests for complex logic detection."""

    @pytest.fixture
    def extractor(self) -> CorrelationExtractor:
        """Create extractor instance."""
        return CorrelationExtractor()

    def test_simple_script_not_complex(
        self, extractor: CorrelationExtractor
    ) -> None:
        """Test simple script is not detected as complex."""
        script = """
        const data = res.body;
        bru.setVar('id', data.id);
        """
        assert not extractor.has_complex_logic(script)

    def test_if_statement_is_complex(self, extractor: CorrelationExtractor) -> None:
        """Test if statement is detected as complex."""
        script = """
        if (data.status === 'success') {
            bru.setVar('id', data.id);
        }
        """
        assert extractor.has_complex_logic(script)

    def test_else_clause_is_complex(self, extractor: CorrelationExtractor) -> None:
        """Test else clause is detected as complex."""
        script = """
        bru.setVar('id', data.id);
        else {
            bru.setVar('id', '');
        }
        """
        assert extractor.has_complex_logic(script)

    def test_for_loop_is_complex(self, extractor: CorrelationExtractor) -> None:
        """Test for loop is detected as complex."""
        script = """
        for (let i = 0; i < data.length; i++) {
            console.log(data[i]);
        }
        """
        assert extractor.has_complex_logic(script)

    def test_while_loop_is_complex(self, extractor: CorrelationExtractor) -> None:
        """Test while loop is detected as complex."""
        script = """
        while (condition) {
            doSomething();
        }
        """
        assert extractor.has_complex_logic(script)

    def test_array_map_is_complex(self, extractor: CorrelationExtractor) -> None:
        """Test array map is detected as complex."""
        script = """
        const ids = data.items.map(item => item.id);
        """
        assert extractor.has_complex_logic(script)

    def test_array_filter_is_complex(self, extractor: CorrelationExtractor) -> None:
        """Test array filter is detected as complex."""
        script = """
        const active = data.items.filter(item => item.active);
        """
        assert extractor.has_complex_logic(script)

    def test_foreach_is_complex(self, extractor: CorrelationExtractor) -> None:
        """Test forEach is detected as complex."""
        script = """
        data.items.forEach(item => {
            console.log(item);
        });
        """
        assert extractor.has_complex_logic(script)

    def test_try_catch_is_complex(self, extractor: CorrelationExtractor) -> None:
        """Test try-catch is detected as complex."""
        script = """
        try {
            bru.setVar('id', data.id);
        } catch (e) {
            console.log(e);
        }
        """
        assert extractor.has_complex_logic(script)

    def test_empty_script_not_complex(
        self, extractor: CorrelationExtractor
    ) -> None:
        """Test empty script is not complex."""
        assert not extractor.has_complex_logic("")

    def test_none_script_not_complex(self, extractor: CorrelationExtractor) -> None:
        """Test None script is not complex."""
        assert not extractor.has_complex_logic(None)


class TestUnknownFormat:
    """Tests for unknown format handling."""

    @pytest.fixture
    def extractor(self) -> CorrelationExtractor:
        """Create extractor instance."""
        return CorrelationExtractor()

    def test_unknown_format_returns_empty(
        self, extractor: CorrelationExtractor
    ) -> None:
        """Test unknown format returns empty list."""
        script = "bru.setVar('id', data.id);"
        result = extractor.extract_correlations(script, "unknown")
        assert result == []

    def test_empty_format_returns_empty(
        self, extractor: CorrelationExtractor
    ) -> None:
        """Test empty format returns empty list."""
        script = "bru.setVar('id', data.id);"
        result = extractor.extract_correlations(script, "")
        assert result == []
