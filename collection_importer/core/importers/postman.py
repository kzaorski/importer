"""Postman collection importer.

Parses Postman v2.1 JSON collections and converts them to ParsedCollection.

Reference: https://schema.postman.com/json/collection/v2.1.0/docs/index.html
"""

import json
import logging
from pathlib import Path
from typing import Any, cast

from collection_importer.core.correlation_extractor import CorrelationExtractor
from collection_importer.core.data_types import CollectionRequest, ParsedCollection
from collection_importer.core.importers.base import BaseImporter
from collection_importer.exceptions import ImporterException

logger = logging.getLogger(__name__)


class PostmanImporter(BaseImporter):
    """Import Postman v2.1 collections.

    Parses Postman v2.1 JSON collection files and converts them to ParsedCollection.
    Supports nested folders, all body types, and authentication methods.
    """

    # Authentication type constants
    AUTH_BEARER = "bearer"
    AUTH_BASIC = "basic"
    AUTH_APIKEY = "apikey"

    # Body mode constants
    BODY_MODE_RAW = "raw"
    BODY_MODE_FORMDATA = "formdata"
    BODY_MODE_URLENCODED = "urlencoded"

    @property
    def format_name(self) -> str:
        """Return format identifier."""
        return "postman"

    def can_import(self, path: Path) -> bool:
        """Check if path is a Postman collection.

        Postman collections are identified by:
        - JSON file with "postman" in filename, or
        - JSON file with info.schema containing "postman"

        Args:
            path: Path to check.

        Returns:
            True if path is a Postman collection.
        """
        if not path.exists() or not path.is_file():
            return False

        if not path.suffix.lower() == ".json":
            return False

        # Quick check: filename contains "postman" or ends with "_collection.json"
        name = path.name.lower()
        if "postman" in name or name.endswith("_collection.json"):
            return True

        # Full check: parse and look for schema
        try:
            content = json.loads(path.read_text(encoding="utf-8"))
            schema = content.get("info", {}).get("schema", "")
            return "postman" in schema.lower()
        except Exception:
            return False

    def import_collection(
        self,
        path: Path,
        env_path: Path | None = None,
        name: str | None = None,
        base_url: str | None = None,
    ) -> ParsedCollection:
        """Import Postman collection.

        Args:
            path: Path to Postman collection JSON file.
            env_path: Optional path to environment JSON file.
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

        # Parse collection file
        try:
            collection_data = self._parse_collection(path)
        except ImporterException:
            raise
        except Exception as e:
            raise ImporterException(
                f"Failed to parse Postman collection: {path}",
                details=str(e),
            ) from e

        # Extract collection name
        info = collection_data.get("info", {})
        collection_name = name or info.get("name", path.stem)
        description = info.get("description", "")

        # Extract collection variables
        variables, detected_base_url = self._extract_variables(
            collection_data.get("variable", [])
        )

        # Load environment variables if provided
        if env_path and env_path.exists():
            env_vars = self._load_environment(env_path)
            variables.update(env_vars)

        # Determine final base URL
        final_base_url = base_url or detected_base_url

        # Process items recursively
        items = collection_data.get("item", [])
        requests = self._process_items(items, folder_path="", sequence_start=0)

        # Build metadata
        metadata = self._build_metadata(
            name=collection_name,
            source_path=str(path),
            description=description,
            base_url=final_base_url,
            variables=variables,
        )

        return ParsedCollection(metadata=metadata, requests=requests)

    def list_requests(self, path: Path) -> list[dict[str, str]]:
        """List requests in Postman collection (preview mode).

        Args:
            path: Path to Postman collection.

        Returns:
            List of request summaries with name, method, path.
        """
        requests: list[dict[str, str]] = []

        try:
            collection_data = self._parse_collection(path)
            items = collection_data.get("item", [])
            self._list_items_recursive(items, folder_path="", result=requests)
        except Exception as e:
            logger.warning(f"Failed to list requests from {path}: {e}")

        return requests

    def _parse_collection(self, path: Path) -> dict[str, Any]:
        """Parse Postman collection JSON file.

        Args:
            path: Path to collection file.

        Returns:
            Parsed collection data.

        Raises:
            ImporterException: If parsing fails or format is invalid.
        """
        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ImporterException(
                f"Invalid JSON in Postman collection: {path}",
                details=str(e),
            ) from e

        # Validate Postman collection structure
        if "info" not in data:
            raise ImporterException(
                "Invalid Postman collection: missing 'info' field",
                details=f"File: {path}",
            )

        schema = data.get("info", {}).get("schema", "")
        if schema and "postman" not in schema.lower() and "2.1" not in schema:
            logger.warning(f"Unrecognized Postman schema: {schema}")

        return cast(dict[str, Any], data)

    def _process_items(
        self,
        items: list[dict[str, Any]],
        folder_path: str,
        sequence_start: int,
    ) -> list[CollectionRequest]:
        """Recursively process items (folders and requests).

        Args:
            items: List of item objects from collection.
            folder_path: Current folder path prefix.
            sequence_start: Starting sequence number.

        Returns:
            List of parsed CollectionRequest objects.
        """
        requests: list[CollectionRequest] = []
        sequence = sequence_start

        for item in items:
            # Check if this is a folder (has nested items)
            if "item" in item and isinstance(item.get("item"), list):
                # This is a folder
                folder_name = item.get("name", "Unnamed Folder")
                new_folder_path = (
                    f"{folder_path}/{folder_name}" if folder_path else folder_name
                )
                nested_requests = self._process_items(
                    item["item"],
                    folder_path=new_folder_path,
                    sequence_start=sequence,
                )
                requests.extend(nested_requests)
                sequence += len(nested_requests)
            elif "request" in item:
                # This is a request
                try:
                    request = self._parse_request(item, folder_path, sequence)
                    requests.append(request)
                    sequence += 1
                except Exception as e:
                    logger.warning(
                        f"Failed to parse request '{item.get('name', 'Unknown')}': {e}"
                    )

        return requests

    def _parse_request(
        self,
        item: dict[str, Any],
        folder_path: str,
        sequence: int,
    ) -> CollectionRequest:
        """Parse a single request item.

        Args:
            item: Request item from collection.
            folder_path: Folder path for this request.
            sequence: Sequence number.

        Returns:
            CollectionRequest object.
        """
        request_data = item.get("request", {})
        name = item.get("name", "Unnamed Request")

        # Handle request as string (simple URL) or dict
        if isinstance(request_data, str):
            # Simple format: request is just a URL string
            return self._build_request(
                name=name,
                method="GET",
                url=request_data,
                folder_path=folder_path,
                sequence=sequence,
            )

        # Parse method
        method = request_data.get("method", "GET").upper()

        # Parse URL
        url = self._parse_url(request_data.get("url", ""))

        # Parse headers
        headers = self._parse_headers(request_data.get("header", []))

        # Parse body
        body, body_type = self._parse_body(request_data.get("body"))

        # Parse authentication
        auth_type, auth_value, auth_headers = self._parse_auth(
            request_data.get("auth")
        )

        # Merge auth headers with request headers
        headers.update(auth_headers)

        # Extract scripts (events)
        pre_script, post_script = self._extract_scripts(item.get("event", []))

        # Extract correlations from post-response script
        correlations: list[dict[str, str]] = []
        if post_script:
            extractor = CorrelationExtractor()
            extracted = extractor.extract_correlations(post_script, "postman")
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

    def _parse_url(self, url: Any) -> str:
        """Parse URL from various formats.

        Postman URL can be:
        - A string: "{{base_url}}/users"
        - An object with raw: {"raw": "{{base_url}}/users", ...}

        Args:
            url: URL value from request.

        Returns:
            URL string.
        """
        if url is None:
            return "/"

        if isinstance(url, str):
            return url

        if isinstance(url, dict):
            # Prefer raw URL if available
            raw = url.get("raw", "")
            if raw:
                return str(raw)

            # Build URL from parts
            protocol = url.get("protocol", "")
            host = url.get("host", [])
            port = url.get("port", "")
            path = url.get("path", [])

            # Build host string
            if isinstance(host, list):
                host_str = ".".join(host)
            else:
                host_str = str(host)

            # Build path string
            if isinstance(path, list):
                path_str = "/" + "/".join(path)
            else:
                path_str = str(path) if path else "/"

            # Combine parts
            if protocol and host_str:
                url_str = f"{protocol}://{host_str}"
                if port:
                    url_str += f":{port}"
                url_str += path_str
                return url_str

            return path_str

        return "/"

    def _parse_headers(
        self, headers: list[dict[str, Any]] | None
    ) -> dict[str, str]:
        """Parse headers array to dict.

        Args:
            headers: List of header objects with key/value.

        Returns:
            Dict of header name -> value.
        """
        result: dict[str, str] = {}

        if not headers:
            return result

        for header in headers:
            if not isinstance(header, dict):
                continue

            # Skip disabled headers
            if header.get("disabled", False):
                continue

            key = header.get("key", "")
            value = header.get("value", "")

            if key:
                result[key] = value

        return result

    def _parse_body(
        self, body: dict[str, Any] | None
    ) -> tuple[dict[str, Any] | str | None, str]:
        """Parse request body.

        Args:
            body: Body object from request.

        Returns:
            Tuple of (body_content, body_type).
        """
        if not body:
            return None, "none"

        mode = body.get("mode", "")

        if mode == self.BODY_MODE_RAW:
            raw = body.get("raw", "")
            # Check if it's JSON
            options = body.get("options", {})
            raw_options = options.get("raw", {})
            language = raw_options.get("language", "")

            if language == "json" or self._looks_like_json(raw):
                try:
                    parsed = json.loads(raw)
                    return parsed, "json"
                except json.JSONDecodeError:
                    pass
            return raw, "raw"

        elif mode == self.BODY_MODE_URLENCODED:
            params = body.get("urlencoded", [])
            form_data: dict[str, str] = {}
            for param in params:
                if isinstance(param, dict) and not param.get("disabled", False):
                    key = param.get("key", "")
                    value = param.get("value", "")
                    if key:
                        form_data[key] = value
            return form_data, "form"

        elif mode == self.BODY_MODE_FORMDATA:
            params = body.get("formdata", [])
            form_data = {}
            for param in params:
                if isinstance(param, dict) and not param.get("disabled", False):
                    key = param.get("key", "")
                    value = param.get("value", "")
                    param_type = param.get("type", "text")
                    if key and param_type == "text":
                        form_data[key] = value
            return form_data, "form"

        return None, "none"

    def _looks_like_json(self, text: str) -> bool:
        """Check if text looks like JSON.

        Args:
            text: Text to check.

        Returns:
            True if text appears to be JSON.
        """
        if not text:
            return False
        stripped = text.strip()
        return (stripped.startswith("{") and stripped.endswith("}")) or (
            stripped.startswith("[") and stripped.endswith("]")
        )

    def _parse_auth(
        self, auth: dict[str, Any] | None
    ) -> tuple[str | None, str | None, dict[str, str]]:
        """Parse authentication configuration.

        Args:
            auth: Auth object from request.

        Returns:
            Tuple of (auth_type, auth_value, additional_headers).
        """
        if not auth:
            return None, None, {}

        auth_type = auth.get("type", "")
        additional_headers: dict[str, str] = {}

        if auth_type == self.AUTH_BEARER:
            bearer_config = auth.get("bearer", [])
            token = self._get_auth_value(bearer_config, "token")
            return "bearer", token, {}

        elif auth_type == self.AUTH_BASIC:
            basic_config = auth.get("basic", [])
            username = self._get_auth_value(basic_config, "username")
            password = self._get_auth_value(basic_config, "password")
            if username or password:
                return "basic", f"{username}:{password}", {}
            return "basic", None, {}

        elif auth_type == self.AUTH_APIKEY:
            apikey_config = auth.get("apikey", [])
            key = self._get_auth_value(apikey_config, "key")
            value = self._get_auth_value(apikey_config, "value")
            location = self._get_auth_value(apikey_config, "in")

            if location == "header" and key and value:
                additional_headers[key] = value
            return "apikey", value, additional_headers

        return None, None, {}

    def _get_auth_value(
        self, config: list[dict[str, Any]], key: str
    ) -> str | None:
        """Get value from auth config array.

        Args:
            config: List of auth config objects.
            key: Key to find.

        Returns:
            Value for the key, or None.
        """
        for item in config:
            if isinstance(item, dict) and item.get("key") == key:
                return item.get("value")
        return None

    def _extract_scripts(
        self, events: list[dict[str, Any]]
    ) -> tuple[str | None, str | None]:
        """Extract pre-request and post-response scripts.

        Args:
            events: List of event objects.

        Returns:
            Tuple of (pre_script, post_script).
        """
        pre_script: str | None = None
        post_script: str | None = None

        for event in events:
            if not isinstance(event, dict):
                continue

            listen = event.get("listen", "")
            script = event.get("script", {})

            if isinstance(script, dict):
                exec_lines = script.get("exec", [])
                if isinstance(exec_lines, list):
                    script_content = "\n".join(exec_lines)
                else:
                    script_content = str(exec_lines)

                if listen == "prerequest" and script_content:
                    pre_script = script_content
                elif listen == "test" and script_content:
                    post_script = script_content

        return pre_script, post_script

    def _extract_variables(
        self, variables: list[dict[str, Any]]
    ) -> tuple[dict[str, str], str | None]:
        """Extract collection variables.

        Args:
            variables: List of variable objects.

        Returns:
            Tuple of (variables_dict, base_url).
        """
        result: dict[str, str] = {}
        base_url: str | None = None

        for var in variables:
            if not isinstance(var, dict):
                continue

            key = var.get("key", "")
            value = var.get("value", "")

            if key:
                result[key] = value
                # Check if this is a base_url variable
                if key.lower() in ("base_url", "baseurl", "base"):
                    base_url = value

        return result, base_url

    def _load_environment(self, env_path: Path) -> dict[str, str]:
        """Load environment variables from file.

        Args:
            env_path: Path to environment file.

        Returns:
            Dict of environment variables.
        """
        try:
            content = env_path.read_text(encoding="utf-8")
            data = json.loads(content)

            variables: dict[str, str] = {}

            # Handle Postman environment format
            env_values = data.get("values", [])
            for var in env_values:
                if isinstance(var, dict) and var.get("enabled", True):
                    key = var.get("key", "")
                    value = var.get("value", "")
                    if key:
                        variables[key] = value

            return variables
        except Exception as e:
            logger.warning(f"Failed to load environment file {env_path}: {e}")
            return {}

    def _list_items_recursive(
        self,
        items: list[dict[str, Any]],
        folder_path: str,
        result: list[dict[str, str]],
    ) -> None:
        """Recursively list items for preview.

        Args:
            items: List of items.
            folder_path: Current folder path.
            result: List to append results to.
        """
        for item in items:
            if "item" in item and isinstance(item.get("item"), list):
                # This is a folder
                folder_name = item.get("name", "Unnamed Folder")
                new_folder_path = (
                    f"{folder_path}/{folder_name}" if folder_path else folder_name
                )
                self._list_items_recursive(item["item"], new_folder_path, result)
            elif "request" in item:
                # This is a request
                name = item.get("name", "Unnamed Request")
                request_data = item.get("request", {})

                # Handle simple URL string
                if isinstance(request_data, str):
                    result.append({
                        "name": f"{folder_path}/{name}" if folder_path else name,
                        "method": "GET",
                        "path": self._extract_path(request_data),
                    })
                    continue

                method = request_data.get("method", "GET").upper()
                url = self._parse_url(request_data.get("url", ""))
                path = self._extract_path(url)

                result.append({
                    "name": f"{folder_path}/{name}" if folder_path else name,
                    "method": method,
                    "path": path,
                })
