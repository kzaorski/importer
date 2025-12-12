"""Data types for parsed collections.

This module defines the core data structures used throughout the Collection Importer.
All collection formats (Bruno, Postman, Insomnia) are parsed into these structures.
"""

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CollectionRequest:
    """A single API request parsed from a collection.

    Attributes:
        name: Human-readable request name.
        method: HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS).
        path: Request path with variables (e.g., /users/${id}).
        headers: Request headers as key-value pairs.
        body: Request body (dict for JSON, str for raw).
        body_type: Body content type (json, form, raw, none).
        auth_type: Authentication type (bearer, basic, apikey, None).
        auth_value: Authentication credentials.
        folder_path: Folder hierarchy (e.g., "auth/users").
        sequence: Order in the collection (0-based).
        pre_script: Pre-request script (preserved for reference).
        post_script: Post-response script (preserved for reference).
        correlations: Extracted variable correlations for JSONPostProcessor.
    """

    name: str
    method: str
    path: str
    headers: dict[str, str] = field(default_factory=dict)
    body: dict[str, Any] | list[Any] | str | None = None
    body_type: str = "none"
    auth_type: str | None = None
    auth_value: str | None = None
    folder_path: str = ""
    sequence: int = 0
    pre_script: str | None = None
    post_script: str | None = None
    correlations: list[dict[str, str]] = field(default_factory=list)

    # Valid values for body_type
    VALID_BODY_TYPES = {"json", "form", "raw", "none"}

    # Valid values for auth_type (None is also valid)
    VALID_AUTH_TYPES = {"bearer", "basic", "apikey"}

    def __post_init__(self) -> None:
        """Validate and normalize request data."""
        # Normalize method to uppercase
        self.method = self.method.upper()

        # Validate method
        valid_methods = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
        if self.method not in valid_methods:
            raise ValueError(f"Invalid HTTP method: {self.method}")

        # Normalize empty path to "/"
        if not self.path or not self.path.strip():
            self.path = "/"
        # Ensure path starts with /
        elif not self.path.startswith("/"):
            self.path = "/" + self.path

        # Validate body_type
        if self.body_type not in self.VALID_BODY_TYPES:
            raise ValueError(
                f"Invalid body_type: {self.body_type}. "
                f"Must be one of: {', '.join(sorted(self.VALID_BODY_TYPES))}"
            )

        # Validate auth_type (None is valid)
        if self.auth_type is not None and self.auth_type not in self.VALID_AUTH_TYPES:
            raise ValueError(
                f"Invalid auth_type: {self.auth_type}. "
                f"Must be one of: {', '.join(sorted(self.VALID_AUTH_TYPES))} or None"
            )

    @property
    def full_name(self) -> str:
        """Return full name including folder path."""
        if self.folder_path:
            return f"{self.folder_path}/{self.name}"
        return self.name

    @property
    def has_body(self) -> bool:
        """Check if request has a body."""
        return self.body is not None and self.body_type != "none"


@dataclass
class CollectionMetadata:
    """Metadata about the collection.

    Attributes:
        name: Collection name.
        description: Collection description.
        base_url: Default base URL for requests.
        variables: Collection-level variables.
        format: Source format (bruno, postman, insomnia).
        source_path: Path to the original collection file/folder.
    """

    name: str
    description: str = ""
    base_url: str | None = None
    variables: dict[str, str] = field(default_factory=dict)
    format: str = "unknown"
    source_path: str = ""


@dataclass
class ParsedCollection:
    """A complete parsed collection.

    This is the unified data structure that all importers produce.
    It contains collection metadata and a list of parsed requests.

    Attributes:
        metadata: Collection-level metadata.
        requests: List of parsed requests in order.
    """

    metadata: CollectionMetadata
    requests: list[CollectionRequest] = field(default_factory=list)

    @property
    def request_count(self) -> int:
        """Return the number of requests in the collection."""
        return len(self.requests)

    def get_requests_by_folder(self) -> dict[str, list[CollectionRequest]]:
        """Group requests by folder path.

        Returns:
            Dictionary mapping folder paths to lists of requests.
            Root-level requests are under empty string key.
        """
        groups: dict[str, list[CollectionRequest]] = {}
        for request in self.requests:
            folder = request.folder_path
            if folder not in groups:
                groups[folder] = []
            groups[folder].append(request)
        return groups

    def get_all_variables(self) -> set[str]:
        """Extract all variable names used in the collection.

        Scans request paths, headers, and bodies for ${var} patterns.

        Returns:
            Set of variable names found in the collection.
        """
        variables: set[str] = set()
        pattern = r"\$\{(\w+)\}"

        for request in self.requests:
            # Check path
            variables.update(re.findall(pattern, request.path))

            # Check headers
            for value in request.headers.values():
                variables.update(re.findall(pattern, value))

            # Check body
            if isinstance(request.body, str):
                variables.update(re.findall(pattern, request.body))
            elif isinstance(request.body, dict):
                body_str = str(request.body)
                variables.update(re.findall(pattern, body_str))

        return variables
