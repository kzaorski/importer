"""Factory for creating collection importers.

Provides a centralized way to get importers by format name.
This module consolidates duplicate importer creation logic from CLI and MCP server.
"""

from collection_importer.core.importers.base import BaseImporter
from collection_importer.core.importers.bruno import BrunoImporter
from collection_importer.core.importers.insomnia import InsomniaImporter
from collection_importer.core.importers.postman import PostmanImporter
from collection_importer.exceptions import CollectionImporterException

# Registry of available importers
_IMPORTERS: dict[str, type[BaseImporter]] = {
    "bruno": BrunoImporter,
    "postman": PostmanImporter,
    "insomnia": InsomniaImporter,
}

SUPPORTED_FORMATS = list(_IMPORTERS.keys())


def get_importer(format_name: str) -> BaseImporter:
    """Get importer instance for the specified format.

    Args:
        format_name: Format name (bruno, postman, insomnia).

    Returns:
        Importer instance ready to import collections.

    Raises:
        CollectionImporterException: If format not supported.
    """
    if format_name not in _IMPORTERS:
        raise CollectionImporterException(
            f"Format '{format_name}' not supported",
            details=f"Supported formats: {', '.join(SUPPORTED_FORMATS)}",
        )
    return _IMPORTERS[format_name]()


def is_supported_format(format_name: str) -> bool:
    """Check if format is supported.

    Args:
        format_name: Format name to check.

    Returns:
        True if format is supported, False otherwise.
    """
    return format_name in _IMPORTERS
