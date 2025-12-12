"""Collection Importer - Convert API collections to JMeter JMX test plans.

Supports:
- Bruno collections (.bru files)
- Postman collections (v2.1 JSON)
- Insomnia exports (v4 JSON)
"""

__version__ = "1.0.0"
__author__ = "Krzysztof Zaorski"

from collection_importer.exceptions import (
    CollectionImporterException,
    ImporterException,
    JMXGenerationException,
    ValidationException,
)

__all__ = [
    "__version__",
    "CollectionImporterException",
    "ImporterException",
    "JMXGenerationException",
    "ValidationException",
]
