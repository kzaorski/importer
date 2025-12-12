"""Unit tests for exceptions module."""

import pytest

from collection_importer.exceptions import (
    CollectionImporterException,
    ImporterException,
    JMXGenerationException,
    ValidationException,
)


class TestCollectionImporterException:
    """Tests for CollectionImporterException base class."""

    def test_message_only(self) -> None:
        """Test exception with message only."""
        exc = CollectionImporterException("Something went wrong")
        assert exc.message == "Something went wrong"
        assert exc.details is None
        assert str(exc) == "Something went wrong"

    def test_message_with_details(self) -> None:
        """Test exception with message and details."""
        exc = CollectionImporterException("Error occurred", details="File not found")
        assert exc.message == "Error occurred"
        assert exc.details == "File not found"
        assert str(exc) == "Error occurred: File not found"

    def test_details_converted_to_string(self) -> None:
        """Test non-string details are converted to string."""
        exc = CollectionImporterException("Error", details=123)
        assert exc.details == "123"
        assert str(exc) == "Error: 123"

    def test_details_none_handled(self) -> None:
        """Test None details are preserved."""
        exc = CollectionImporterException("Error", details=None)
        assert exc.details is None
        assert str(exc) == "Error"

    def test_exception_inheritance(self) -> None:
        """Test exception inherits from Exception."""
        exc = CollectionImporterException("Error")
        assert isinstance(exc, Exception)

    def test_can_be_raised_and_caught(self) -> None:
        """Test exception can be raised and caught."""
        with pytest.raises(CollectionImporterException, match="Test error"):
            raise CollectionImporterException("Test error")


class TestImporterException:
    """Tests for ImporterException class."""

    def test_inherits_from_base(self) -> None:
        """Test inherits from CollectionImporterException."""
        exc = ImporterException("Import failed")
        assert isinstance(exc, CollectionImporterException)

    def test_message_only(self) -> None:
        """Test exception with message only."""
        exc = ImporterException("Failed to parse collection")
        assert exc.message == "Failed to parse collection"
        assert str(exc) == "Failed to parse collection"

    def test_message_with_details(self) -> None:
        """Test exception with message and details."""
        exc = ImporterException(
            "Invalid collection format",
            details="Expected bruno.json file",
        )
        assert exc.message == "Invalid collection format"
        assert exc.details == "Expected bruno.json file"
        assert str(exc) == "Invalid collection format: Expected bruno.json file"

    def test_can_be_caught_as_base(self) -> None:
        """Test can be caught as base exception."""
        with pytest.raises(CollectionImporterException):
            raise ImporterException("Import error")


class TestJMXGenerationException:
    """Tests for JMXGenerationException class."""

    def test_inherits_from_base(self) -> None:
        """Test inherits from CollectionImporterException."""
        exc = JMXGenerationException("Generation failed")
        assert isinstance(exc, CollectionImporterException)

    def test_message_only(self) -> None:
        """Test exception with message only."""
        exc = JMXGenerationException("Failed to create JMX")
        assert exc.message == "Failed to create JMX"
        assert str(exc) == "Failed to create JMX"

    def test_message_with_details(self) -> None:
        """Test exception with message and details."""
        exc = JMXGenerationException(
            "Invalid thread count",
            details="Value must be positive integer",
        )
        assert exc.message == "Invalid thread count"
        assert exc.details == "Value must be positive integer"
        assert str(exc) == "Invalid thread count: Value must be positive integer"

    def test_can_be_caught_as_base(self) -> None:
        """Test can be caught as base exception."""
        with pytest.raises(CollectionImporterException):
            raise JMXGenerationException("JMX error")


class TestValidationException:
    """Tests for ValidationException class."""

    def test_inherits_from_base(self) -> None:
        """Test inherits from CollectionImporterException."""
        exc = ValidationException("Validation failed")
        assert isinstance(exc, CollectionImporterException)

    def test_message_only(self) -> None:
        """Test exception with message only."""
        exc = ValidationException("Invalid JMX structure")
        assert exc.message == "Invalid JMX structure"
        assert str(exc) == "Invalid JMX structure"

    def test_message_with_details(self) -> None:
        """Test exception with message and details."""
        exc = ValidationException(
            "Missing required element",
            details="TestPlan element not found",
        )
        assert exc.message == "Missing required element"
        assert exc.details == "TestPlan element not found"
        assert str(exc) == "Missing required element: TestPlan element not found"

    def test_can_be_caught_as_base(self) -> None:
        """Test can be caught as base exception."""
        with pytest.raises(CollectionImporterException):
            raise ValidationException("Validation error")


class TestExceptionHierarchy:
    """Tests for exception hierarchy structure."""

    def test_all_exceptions_inherit_from_base(self) -> None:
        """Test all custom exceptions inherit from base."""
        exceptions = [
            ImporterException("test"),
            JMXGenerationException("test"),
            ValidationException("test"),
        ]
        for exc in exceptions:
            assert isinstance(exc, CollectionImporterException)
            assert isinstance(exc, Exception)

    def test_exceptions_are_distinct_types(self) -> None:
        """Test exception types are distinct."""
        importer = ImporterException("test")
        jmx = JMXGenerationException("test")
        validation = ValidationException("test")

        # Should not be instances of each other
        assert not isinstance(importer, JMXGenerationException)
        assert not isinstance(importer, ValidationException)
        assert not isinstance(jmx, ImporterException)
        assert not isinstance(jmx, ValidationException)
        assert not isinstance(validation, ImporterException)
        assert not isinstance(validation, JMXGenerationException)

    def test_can_catch_specific_exceptions(self) -> None:
        """Test specific exceptions can be caught individually."""
        # ImporterException
        try:
            raise ImporterException("import error")
        except ImporterException:
            pass
        except Exception:
            pytest.fail("ImporterException not caught")

        # JMXGenerationException
        try:
            raise JMXGenerationException("jmx error")
        except JMXGenerationException:
            pass
        except Exception:
            pytest.fail("JMXGenerationException not caught")

        # ValidationException
        try:
            raise ValidationException("validation error")
        except ValidationException:
            pass
        except Exception:
            pytest.fail("ValidationException not caught")

    def test_exception_args(self) -> None:
        """Test exception args attribute."""
        exc = CollectionImporterException("Test message")
        assert exc.args == ("Test message",)
