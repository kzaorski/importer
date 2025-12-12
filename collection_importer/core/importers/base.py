"""Abstract base class for collection importers.

All collection format importers (Bruno, Postman, Insomnia) inherit from BaseImporter.
This provides a common interface and shared utility methods.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from collection_importer.core.data_types import (
    CollectionMetadata,
    CollectionRequest,
    ParsedCollection,
)
from collection_importer.core.variable_manager import VariableManager


class BaseImporter(ABC):
    """Abstract base class for collection importers.

    All format-specific importers must implement:
    - can_import(): Check if the importer can handle a given path
    - import_collection(): Parse the collection and return ParsedCollection
    - list_requests(): Preview requests without full import
    """

    def __init__(self) -> None:
        """Initialize the importer with a variable manager."""
        self._var_manager = VariableManager()

    @property
    @abstractmethod
    def format_name(self) -> str:
        """Return the format name (e.g., 'bruno', 'postman', 'insomnia')."""
        pass

    @abstractmethod
    def can_import(self, path: Path) -> bool:
        """Check if this importer can handle the given path.

        Args:
            path: Path to collection file or folder.

        Returns:
            True if this importer can handle the path.
        """
        pass

    @abstractmethod
    def import_collection(
        self,
        path: Path,
        env_path: Path | None = None,
        name: str | None = None,
        base_url: str | None = None,
    ) -> ParsedCollection:
        """Import collection and return ParsedCollection.

        Args:
            path: Path to collection file or folder.
            env_path: Optional path to environment file.
            name: Optional override for collection name.
            base_url: Optional override for base URL.

        Returns:
            ParsedCollection with metadata and requests.

        Raises:
            ImporterException: If import fails.
        """
        pass

    @abstractmethod
    def list_requests(self, path: Path) -> list[dict[str, str]]:
        """List requests without full import (preview mode).

        This is a lightweight operation that returns basic request info
        without parsing bodies, scripts, or environment variables.

        Args:
            path: Path to collection file or folder.

        Returns:
            List of request summaries with keys:
            - name: Request name
            - method: HTTP method
            - path: Request path
        """
        pass

    # Shared utility methods

    def _convert_variables(self, text: str) -> str:
        """Convert {{var}} to ${var} syntax.

        Args:
            text: Text containing {{var}} placeholders.

        Returns:
            Text with ${var} placeholders.
        """
        return self._var_manager.convert_variable_syntax(text)

    def _convert_payload(
        self, payload: dict[str, Any] | list[Any] | str
    ) -> dict[str, Any] | list[Any] | str:
        """Recursively convert variables in payload.

        Args:
            payload: Request body.

        Returns:
            Payload with converted variable syntax.
        """
        return self._var_manager.convert_payload_variables(payload)

    def _extract_path(self, url: str) -> str:
        """Extract path from URL, converting variables.

        Args:
            url: Full URL or path.

        Returns:
            Clean path starting with /.
        """
        return self._var_manager.extract_path_from_url(url)

    def _extract_base_url(self, url: str) -> str | None:
        """Extract base URL (protocol + host) from URL.

        Args:
            url: Full URL.

        Returns:
            Base URL or None.
        """
        return self._var_manager.extract_base_url(url)

    def _build_request(
        self,
        name: str,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        body: dict[str, Any] | list[Any] | str | None = None,
        body_type: str = "none",
        auth_type: str | None = None,
        auth_value: str | None = None,
        folder_path: str = "",
        sequence: int = 0,
        pre_script: str | None = None,
        post_script: str | None = None,
        correlations: list[dict[str, str]] | None = None,
    ) -> CollectionRequest:
        """Build a CollectionRequest with variable conversion.

        This is a helper method that handles variable conversion
        and creates a properly structured CollectionRequest.

        Args:
            name: Request name.
            method: HTTP method.
            url: Request URL (will be converted to path).
            headers: Request headers (optional).
            body: Request body (optional).
            body_type: Body type (json, form, raw, none).
            auth_type: Auth type (bearer, basic, apikey).
            auth_value: Auth credentials.
            folder_path: Folder hierarchy path.
            sequence: Order in collection.
            pre_script: Pre-request script.
            post_script: Post-response script.
            correlations: Extracted correlations for JSONPostProcessor.

        Returns:
            CollectionRequest with converted variables.
        """
        # Convert variables in path
        path = self._extract_path(url)

        # Convert variables in headers
        converted_headers: dict[str, str] = {}
        if headers:
            converted_headers = {
                k: self._convert_variables(v) for k, v in headers.items()
            }

        # Convert variables in body
        converted_body = None
        if body is not None:
            converted_body = self._convert_payload(body)

        # Convert auth value if present
        converted_auth = None
        if auth_value:
            converted_auth = self._convert_variables(auth_value)

        return CollectionRequest(
            name=name,
            method=method,
            path=path,
            headers=converted_headers,
            body=converted_body,
            body_type=body_type,
            auth_type=auth_type,
            auth_value=converted_auth,
            folder_path=folder_path,
            sequence=sequence,
            pre_script=pre_script,
            post_script=post_script,
            correlations=correlations or [],
        )

    def _build_metadata(
        self,
        name: str,
        source_path: str,
        description: str = "",
        base_url: str | None = None,
        variables: dict[str, str] | None = None,
    ) -> CollectionMetadata:
        """Build CollectionMetadata with variable conversion.

        Args:
            name: Collection name.
            source_path: Path to original collection.
            description: Collection description.
            base_url: Base URL for requests.
            variables: Collection variables.

        Returns:
            CollectionMetadata instance.
        """
        # Convert variables in variable values
        converted_vars: dict[str, str] = {}
        if variables:
            converted_vars = {
                k: self._convert_variables(v) for k, v in variables.items()
            }

        return CollectionMetadata(
            name=name,
            description=description,
            base_url=base_url,
            variables=converted_vars,
            format=self.format_name,
            source_path=source_path,
        )
