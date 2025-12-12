"""Custom exceptions for Collection Importer.

Exception hierarchy:
    CollectionImporterException (base)
    ├── ImporterException       - Collection parsing errors
    ├── JMXGenerationException  - JMX generation errors
    └── ValidationException     - JMX validation errors
"""


class CollectionImporterException(Exception):
    """Base exception for all Collection Importer errors."""

    def __init__(self, message: str, details: str | None = None) -> None:
        """Initialize exception with message and optional details.

        Args:
            message: Human-readable error message.
            details: Additional technical details (optional). Will be converted
                     to string if not already.
        """
        self.message = message
        # Ensure details is a string or None
        if details is not None and not isinstance(details, str):
            details = str(details)
        self.details = details
        super().__init__(message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class ImporterException(CollectionImporterException):
    """Exception raised when collection parsing fails.

    Examples:
        - Invalid collection format
        - Missing required fields
        - Unsupported collection version
        - File not found or unreadable
    """

    pass


class JMXGenerationException(CollectionImporterException):
    """Exception raised when JMX generation fails.

    Examples:
        - Invalid endpoint configuration
        - XML generation errors
        - File write errors
    """

    pass


class ValidationException(CollectionImporterException):
    """Exception raised when JMX validation fails.

    Examples:
        - Missing required XML elements
        - Invalid ThreadGroup configuration
        - Malformed JMX structure
    """

    pass
