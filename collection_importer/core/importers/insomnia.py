"""Insomnia collection importer.

Parses Insomnia v4 JSON exports and converts them to ParsedCollection.

Reference: https://developer.konghq.com/insomnia/import-export/
"""

import base64
import json
import logging
from pathlib import Path
from typing import Any, cast

from collection_importer.core.correlation_extractor import CorrelationExtractor
from collection_importer.core.data_types import CollectionRequest, ParsedCollection
from collection_importer.core.importers.base import BaseImporter
from collection_importer.exceptions import ImporterException

logger = logging.getLogger(__name__)


class InsomniaImporter(BaseImporter):
    """Import Insomnia v4 exports.

    Parses Insomnia v4 JSON export files and converts them to ParsedCollection.
    Supports workspace, request_group (folders), request, and environment resources.
    """

    # Resource type constants
    TYPE_WORKSPACE = "workspace"
    TYPE_REQUEST_GROUP = "request_group"
    TYPE_REQUEST = "request"
    TYPE_ENVIRONMENT = "environment"

    # Authentication type constants
    AUTH_BEARER = "bearer"
    AUTH_BASIC = "basic"

    @property
    def format_name(self) -> str:
        """Return format identifier."""
        return "insomnia"

    def can_import(self, path: Path) -> bool:
        """Check if path is an Insomnia export.

        Insomnia exports are identified by:
        - JSON file with "_type": "export" field

        Args:
            path: Path to check.

        Returns:
            True if path is an Insomnia export.
        """
        if not path.exists() or not path.is_file():
            return False

        if not path.suffix.lower() == ".json":
            return False

        # Quick check: filename contains "insomnia"
        name = path.name.lower()
        if "insomnia" in name:
            return True

        # Full check: parse and look for _type: export
        try:
            content = json.loads(path.read_text(encoding="utf-8"))
            return bool(content.get("_type") == "export")
        except Exception:
            return False

    def import_collection(
        self,
        path: Path,
        env_path: Path | None = None,
        name: str | None = None,
        base_url: str | None = None,
    ) -> ParsedCollection:
        """Import Insomnia export.

        Args:
            path: Path to Insomnia export JSON file.
            env_path: Optional path to environment file.
            name: Optional override for collection name.
            base_url: Optional override for base URL.

        Returns:
            ParsedCollection with parsed requests.

        Raises:
            ImporterException: If import fails.
        """
        if not path.exists():
            raise ImporterException(
                f"Path does not exist: {path}",
                details="Check that the file path is correct",
            )

        # Parse export file
        export_data = self._parse_export(path)
        resources = export_data.get("resources", [])

        if not resources:
            raise ImporterException(
                "No resources found in export",
                details=f"File: {path}",
            )

        # Build resource index for lookups
        resource_index = self._build_resource_index(resources)

        # Find workspace
        workspace = self._find_workspace(resources)
        if not workspace:
            raise ImporterException(
                "No workspace resource found in export",
                details=f"File: {path}",
            )

        workspace_id = workspace.get("_id", "")

        # Build folder hierarchy
        folder_paths = self._build_folder_hierarchy(resource_index, workspace_id)

        # Extract environment variables
        variables, detected_base_url = self._extract_environment_variables(
            resources, workspace_id
        )

        # Load external environment if provided
        if env_path and env_path.exists():
            env_vars, env_base_url = self._parse_environment_file(env_path)
            variables.update(env_vars)
            if env_base_url and not detected_base_url:
                detected_base_url = env_base_url

        # Use override base_url if provided
        effective_base_url = base_url or detected_base_url

        # Parse requests
        requests: list[CollectionRequest] = []
        request_resources = [
            r for r in resources if r.get("_type") == self.TYPE_REQUEST
        ]

        # Sort by metaSortKey for consistent ordering
        request_resources = sorted(
            request_resources,
            key=lambda r: r.get("metaSortKey", 0),
            reverse=True,  # Higher values come first (more negative = later)
        )

        for idx, resource in enumerate(request_resources):
            parent_id = resource.get("parentId", "")
            folder_path = folder_paths.get(parent_id, "")

            try:
                request = self._parse_request(resource, folder_path, idx)
                requests.append(request)
            except Exception as e:
                logger.warning(f"Failed to parse request {resource.get('name')}: {e}")
                continue

        # Build collection name
        collection_name = name or workspace.get("name", path.stem)
        description = workspace.get("description", "")

        # Build metadata
        metadata = self._build_metadata(
            name=collection_name,
            source_path=str(path),
            description=description,
            base_url=effective_base_url,
            variables=variables,
        )

        return ParsedCollection(metadata=metadata, requests=requests)

    def list_requests(self, path: Path) -> list[dict[str, str]]:
        """List requests in Insomnia export (preview mode).

        Args:
            path: Path to Insomnia export.

        Returns:
            List of request summaries with name, method, path.
        """
        if not path.exists():
            return []

        try:
            export_data = self._parse_export(path)
            resources = export_data.get("resources", [])

            # Build resource index and folder hierarchy
            resource_index = self._build_resource_index(resources)
            workspace = self._find_workspace(resources)
            if not workspace:
                return []

            workspace_id = workspace.get("_id", "")
            folder_paths = self._build_folder_hierarchy(resource_index, workspace_id)

            # Extract request summaries
            result: list[dict[str, str]] = []
            request_resources = [
                r for r in resources if r.get("_type") == self.TYPE_REQUEST
            ]

            # Sort by metaSortKey
            request_resources = sorted(
                request_resources,
                key=lambda r: r.get("metaSortKey", 0),
                reverse=True,
            )

            for resource in request_resources:
                name = resource.get("name", "Unnamed")
                method = resource.get("method", "GET").upper()
                url = resource.get("url", "/")
                parent_id = resource.get("parentId", "")
                folder_path = folder_paths.get(parent_id, "")

                # Extract path from URL
                request_path = self._extract_path(url)

                # Include folder prefix in name
                if folder_path:
                    display_name = f"{folder_path}/{name}"
                else:
                    display_name = name

                result.append({
                    "name": display_name,
                    "method": method,
                    "path": request_path,
                })

            return result

        except Exception as e:
            logger.warning(f"Failed to list requests: {e}")
            return []

    # Helper methods

    def _parse_export(self, path: Path) -> dict[str, Any]:
        """Parse Insomnia export JSON file.

        Args:
            path: Path to JSON file.

        Returns:
            Parsed JSON content.

        Raises:
            ImporterException: If file is invalid.
        """
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            raise ImporterException(
                f"File must be UTF-8 encoded: {path.name}",
                details=str(e),
            ) from e
        except OSError as e:
            raise ImporterException(
                f"Cannot read file: {path.name}",
                details=str(e),
            ) from e

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ImporterException(
                "Invalid JSON format",
                details=str(e),
            ) from e

        # Validate export format
        if data.get("_type") != "export":
            raise ImporterException(
                "Not a valid Insomnia export",
                details="Missing '_type': 'export' field",
            )

        return cast(dict[str, Any], data)

    def _build_resource_index(
        self, resources: list[dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        """Build lookup index of resources by _id.

        Args:
            resources: List of resource objects.

        Returns:
            Dict mapping _id to resource.
        """
        return {r.get("_id", ""): r for r in resources if r.get("_id")}

    def _find_workspace(
        self, resources: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        """Find workspace resource in export.

        Args:
            resources: List of resource objects.

        Returns:
            Workspace resource or None.
        """
        for resource in resources:
            if resource.get("_type") == self.TYPE_WORKSPACE:
                return resource
        return None

    def _build_folder_hierarchy(
        self,
        resource_index: dict[str, dict[str, Any]],
        workspace_id: str,
    ) -> dict[str, str]:
        """Build folder path mapping for each resource.

        Args:
            resource_index: Resource lookup by _id.
            workspace_id: ID of the workspace resource.

        Returns:
            Dict mapping resource _id to folder path string.
        """
        cache: dict[str, str] = {}

        # Pre-calculate paths for all resources
        for resource_id in resource_index:
            self._get_folder_path(resource_id, resource_index, workspace_id, cache)

        return cache

    def _get_folder_path(
        self,
        resource_id: str,
        resource_index: dict[str, dict[str, Any]],
        workspace_id: str,
        cache: dict[str, str],
    ) -> str:
        """Recursively resolve folder path for a resource.

        Args:
            resource_id: ID of resource to get path for.
            resource_index: Resource lookup.
            workspace_id: Workspace ID (root).
            cache: Memoization cache.

        Returns:
            Folder path string (e.g., "auth/users").
        """
        # Check cache
        if resource_id in cache:
            return cache[resource_id]

        # Workspace is root
        if resource_id == workspace_id or not resource_id:
            cache[resource_id] = ""
            return ""

        resource = resource_index.get(resource_id)
        if not resource:
            cache[resource_id] = ""
            return ""

        parent_id = resource.get("parentId", "")
        resource_type = resource.get("_type", "")

        # If parent is workspace, this folder is at root level
        if parent_id == workspace_id:
            if resource_type == self.TYPE_REQUEST_GROUP:
                path = str(resource.get("name", ""))
            else:
                path = ""
            cache[resource_id] = path
            return path

        # Get parent path recursively
        parent_path = self._get_folder_path(
            parent_id, resource_index, workspace_id, cache
        )

        # Build current path
        if resource_type == self.TYPE_REQUEST_GROUP:
            name = str(resource.get("name", ""))
            if parent_path:
                path = f"{parent_path}/{name}"
            else:
                path = name
        else:
            path = parent_path

        cache[resource_id] = path
        return path

    def _parse_request(
        self,
        resource: dict[str, Any],
        folder_path: str,
        sequence: int,
    ) -> CollectionRequest:
        """Parse a request resource into CollectionRequest.

        Args:
            resource: Request resource dict.
            folder_path: Resolved folder path.
            sequence: Order in collection.

        Returns:
            CollectionRequest instance.
        """
        name = resource.get("name", "Unnamed Request")
        method = resource.get("method", "GET").upper()
        url = resource.get("url", "/")

        # Parse headers
        headers_list = resource.get("headers", [])
        headers = self._parse_headers(headers_list)

        # Parse body
        body_data = resource.get("body", {})
        body, body_type = self._parse_body(body_data)

        # Parse authentication
        auth_data = resource.get("authentication", {})
        auth_type, auth_value, auth_headers = self._parse_authentication(auth_data)

        # Merge auth headers
        if auth_headers:
            headers.update(auth_headers)

        # Extract scripts (Insomnia uses beforeRequestScript and afterResponseScript)
        pre_script = resource.get("beforeRequestScript")
        post_script = resource.get("afterResponseScript")

        # Extract correlations from post-response script
        correlations: list[dict[str, str]] = []
        if post_script:
            extractor = CorrelationExtractor()
            extracted = extractor.extract_correlations(post_script, "insomnia")
            correlations = [
                {"variable_name": c.variable_name, "json_path": c.json_path}
                for c in extracted
            ]
            if correlations:
                logger.debug(
                    f"Extracted {len(correlations)} correlations from post-script"
                )

        return self._build_request(
            name=name,
            method=method,
            url=url,
            headers=headers if headers else None,
            body=body,
            body_type=body_type,
            auth_type=auth_type,
            auth_value=auth_value,
            folder_path=folder_path,
            sequence=sequence,
            pre_script=pre_script,
            post_script=post_script,
            correlations=correlations,
        )

    def _parse_headers(
        self, headers: list[dict[str, Any]]
    ) -> dict[str, str]:
        """Parse Insomnia headers array into dict.

        Args:
            headers: List of header objects with name/value.

        Returns:
            Dict of header name to value.
        """
        result: dict[str, str] = {}
        if not headers or not isinstance(headers, list):
            return result

        for header in headers:
            if not isinstance(header, dict):
                continue

            name = header.get("name", "")
            value = header.get("value", "")

            # Skip disabled headers
            if header.get("disabled", False):
                continue

            if name:
                result[name] = value

        return result

    def _parse_body(
        self, body: dict[str, Any]
    ) -> tuple[dict[str, Any] | str | None, str]:
        """Parse Insomnia body object.

        Args:
            body: Body object with mimeType and text/params.

        Returns:
            Tuple of (body_content, body_type).
        """
        if not body or not isinstance(body, dict):
            return None, "none"

        mime_type = body.get("mimeType", "")

        if not mime_type:
            return None, "none"

        # JSON body
        if "json" in mime_type.lower():
            text = body.get("text", "")
            if text:
                try:
                    parsed = json.loads(text)
                    return parsed, "json"
                except json.JSONDecodeError:
                    # Return as raw string if JSON is invalid
                    return text, "raw"
            return None, "none"

        # Form data (urlencoded or multipart)
        if "form" in mime_type.lower() or "urlencoded" in mime_type.lower():
            params = body.get("params", [])
            if params and isinstance(params, list):
                form_data: dict[str, str] = {}
                for param in params:
                    if isinstance(param, dict):
                        param_name = param.get("name", "")
                        param_value = param.get("value", "")
                        if param_name and not param.get("disabled", False):
                            form_data[param_name] = param_value
                if form_data:
                    return form_data, "form"
            return None, "none"

        # Raw body (text, xml, etc.)
        text = body.get("text", "")
        if text:
            return text, "raw"

        return None, "none"

    def _parse_authentication(
        self, auth: dict[str, Any]
    ) -> tuple[str | None, str | None, dict[str, str]]:
        """Parse Insomnia authentication object.

        Args:
            auth: Authentication object.

        Returns:
            Tuple of (auth_type, auth_value, auth_headers).
            auth_headers contains Authorization header if applicable.
        """
        auth_headers: dict[str, str] = {}

        if not auth or not isinstance(auth, dict):
            return None, None, auth_headers

        auth_type_raw = auth.get("type", "")

        if not auth_type_raw:
            return None, None, auth_headers

        # Bearer token authentication
        if auth_type_raw.lower() == self.AUTH_BEARER:
            token = auth.get("token", "")
            prefix = auth.get("prefix", "Bearer")
            if token:
                auth_headers["Authorization"] = f"{prefix} {token}"
                return "bearer", token, auth_headers

        # Basic authentication
        if auth_type_raw.lower() == self.AUTH_BASIC:
            username = auth.get("username", "")
            password = auth.get("password", "")
            if username or password:
                credentials = f"{username}:{password}"
                encoded = base64.b64encode(credentials.encode()).decode()
                auth_headers["Authorization"] = f"Basic {encoded}"
                return "basic", credentials, auth_headers

        return None, None, auth_headers

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid (has scheme and no unresolved template vars).

        Args:
            url: URL string to validate.

        Returns:
            True if URL is valid for use as base URL.
        """
        # Skip URLs with unresolved template variables
        if "{{" in url or "}}" in url:
            return False
        # Must start with http:// or https://
        return url.startswith("http://") or url.startswith("https://")

    def _extract_flat_variables(self, data: dict[str, Any]) -> dict[str, str]:
        """Extract variables from environment data, skipping nested objects.

        Args:
            data: Environment data dictionary.

        Returns:
            Flat dictionary of string variables.
        """
        variables: dict[str, str] = {}
        for key, value in data.items():
            if isinstance(value, dict):
                # Skip nested objects like 'mastercard' with credentials
                continue
            if value is not None:
                variables[key] = str(value)
        return variables

    def _detect_base_url(self, variables: dict[str, str]) -> str | None:
        """Detect base URL from environment variables.

        Checks multiple possible keys: base_url, baseurl, base-url, host, url.

        Args:
            variables: Dictionary of environment variables.

        Returns:
            Detected base URL or None.
        """
        priority_keys = ("base_url", "baseurl", "base-url", "host", "url")
        for key in priority_keys:
            # Exact match first
            if key in variables:
                return variables[key]
            # Case-insensitive fallback
            for var_key, var_value in variables.items():
                if var_key.lower() == key:
                    return var_value
        return None

    def _build_environment_hierarchy(
        self,
        resources: list[dict[str, Any]],
        workspace_id: str,
    ) -> tuple[dict[str, str], str | None]:
        """Build environment hierarchy and merge variables with inheritance.

        Insomnia environments form a tree:
        - Base environment: parentId == workspace_id
        - Child environments: parentId == parent_environment_id

        Child environment variables override parent values.

        Args:
            resources: All resources from export.
            workspace_id: Workspace ID to find base environment.

        Returns:
            Tuple of (merged_variables_dict, detected_base_url).
        """
        # 1. Collect all environments
        environments: dict[str, dict[str, Any]] = {}
        for resource in resources:
            if resource.get("_type") == self.TYPE_ENVIRONMENT:
                env_id = resource.get("_id")
                if env_id:
                    environments[env_id] = resource

        # 2. Find base environment (direct child of workspace)
        base_env_id: str | None = None
        for env_id, env in environments.items():
            if env.get("parentId") == workspace_id:
                base_env_id = env_id
                break

        if not base_env_id:
            return {}, None

        # 3. Start with base environment variables
        merged_vars: dict[str, str] = {}
        base_data = environments[base_env_id].get("data", {})
        if isinstance(base_data, dict):
            merged_vars.update(self._extract_flat_variables(base_data))

        # 4. Find and process child environments (override parent values)
        base_url: str | None = None
        for _env_id, env in environments.items():
            if env.get("parentId") == base_env_id:
                child_data = env.get("data", {})
                if isinstance(child_data, dict):
                    child_vars = self._extract_flat_variables(child_data)
                    merged_vars.update(child_vars)  # Child overrides parent

                    # Prefer child's base_url/host if valid
                    child_base_url = self._detect_base_url(child_vars)
                    if child_base_url and self._is_valid_url(child_base_url):
                        base_url = child_base_url

        # 5. Fallback to base environment's base_url if valid
        if not base_url:
            base_base_url = self._detect_base_url(
                self._extract_flat_variables(base_data)
                if isinstance(base_data, dict)
                else {}
            )
            if base_base_url and self._is_valid_url(base_base_url):
                base_url = base_base_url

        return merged_vars, base_url

    def _extract_environment_variables(
        self,
        resources: list[dict[str, Any]],
        workspace_id: str,
    ) -> tuple[dict[str, str], str | None]:
        """Extract variables from environment resources with inheritance.

        Builds environment hierarchy and merges variables. Child environment
        variables override parent values. Only valid URLs (with scheme and
        without unresolved template variables) are used as base_url.

        Args:
            resources: All resources from export.
            workspace_id: Workspace ID to find base environment.

        Returns:
            Tuple of (variables_dict, detected_base_url).
        """
        return self._build_environment_hierarchy(resources, workspace_id)

    def _parse_environment_file(
        self, env_path: Path
    ) -> tuple[dict[str, str], str | None]:
        """Parse external Insomnia environment file.

        Args:
            env_path: Path to environment JSON file.

        Returns:
            Tuple of (variables_dict, detected_base_url).
        """
        variables: dict[str, str] = {}
        base_url: str | None = None

        try:
            content = env_path.read_text(encoding="utf-8")
            data = json.loads(content)

            # Check if it's an Insomnia export with environment
            if data.get("_type") == "export":
                resources = data.get("resources", [])
                for resource in resources:
                    if resource.get("_type") == self.TYPE_ENVIRONMENT:
                        env_data = resource.get("data", {})
                        for key, value in env_data.items():
                            str_value = str(value) if value is not None else ""
                            variables[key] = str_value

                            key_lower = key.lower()
                            if key_lower in ("base_url", "baseurl", "base-url"):
                                base_url = str_value

            # Plain JSON with variables
            elif isinstance(data, dict):
                for key, value in data.items():
                    str_value = str(value) if value is not None else ""
                    variables[key] = str_value

                    key_lower = key.lower()
                    if key_lower in ("base_url", "baseurl", "base-url"):
                        base_url = str_value

        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to parse environment file {env_path}: {e}")

        return variables, base_url
