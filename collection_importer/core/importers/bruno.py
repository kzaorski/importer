"""Bruno collection importer.

Parses Bruno .bru collection folders and converts them to ParsedCollection.
Bruno uses a folder structure with individual .bru files for each request.

Reference: https://docs.usebruno.com/bru-lang/overview
"""

import base64
import json
import logging
import re
from pathlib import Path
from typing import Any

from collection_importer.core.correlation_extractor import CorrelationExtractor
from collection_importer.core.data_types import CollectionRequest, ParsedCollection
from collection_importer.core.importers.base import BaseImporter
from collection_importer.exceptions import ImporterException

logger = logging.getLogger(__name__)


class BrunoImporter(BaseImporter):
    """Import Bruno collections (.bru files).

    Bruno collections are folder-based with:
    - bruno.json: Collection metadata
    - *.bru: Individual request files
    - environments/*.bru: Environment variable files
    """

    # HTTP methods supported in .bru files
    HTTP_METHODS = ("get", "post", "put", "patch", "delete", "head", "options")

    def _safe_read_utf8(
        self, file: Path, raise_on_error: bool = True
    ) -> str | None:
        """Safely read file with UTF-8 encoding.

        Args:
            file: File to read.
            raise_on_error: If True, raises ImporterException on error.
                           If False, logs warning and returns None.

        Returns:
            File content or None if read failed and raise_on_error=False.

        Raises:
            ImporterException: If raise_on_error=True and read fails.
        """
        try:
            return file.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            msg = f"{file.name} must be UTF-8 encoded"
            if raise_on_error:
                raise ImporterException(msg, details=str(e)) from e
            logger.warning(msg)
            return None
        except OSError as e:
            msg = f"Cannot read file {file.name}"
            if raise_on_error:
                raise ImporterException(msg, details=str(e)) from e
            logger.warning(f"{msg}: {e}")
            return None

    @property
    def format_name(self) -> str:
        """Return format identifier."""
        return "bruno"

    def can_import(self, path: Path) -> bool:
        """Check if path is a Bruno collection.

        A Bruno collection is identified by:
        1. A directory containing bruno.json, OR
        2. A directory containing .bru files

        Args:
            path: Path to check.

        Returns:
            True if path is a Bruno collection.
        """
        if not path.exists():
            return False

        if path.is_file():
            return path.suffix == ".bru"

        if path.is_dir():
            # Check for bruno.json
            if (path / "bruno.json").exists():
                return True
            # Check for any .bru files
            return any(path.rglob("*.bru"))

        return False

    def import_collection(
        self,
        path: Path,
        env_path: Path | None = None,
        name: str | None = None,
        base_url: str | None = None,
    ) -> ParsedCollection:
        """Import Bruno collection.

        Args:
            path: Path to Bruno collection folder.
            env_path: Optional path to environment .bru file.
            name: Optional override for collection name.
            base_url: Optional override for base URL.

        Returns:
            ParsedCollection with parsed requests.

        Raises:
            ImporterException: If import fails.
        """
        if not path.exists():
            raise ImporterException(f"Path does not exist: {path}")

        # Handle single .bru file
        if path.is_file():
            return self._import_single_file(path, name, base_url)

        # Handle collection folder
        return self._import_folder(path, env_path, name, base_url)

    def list_requests(self, path: Path) -> list[dict[str, str]]:
        """List requests in Bruno collection (preview mode).

        Args:
            path: Path to Bruno collection.

        Returns:
            List of request summaries.
        """
        requests: list[dict[str, str]] = []

        if path.is_file() and path.suffix == ".bru":
            files = [path]
        else:
            files = self._find_request_files(path)

        for file in files:
            content = self._safe_read_utf8(file, raise_on_error=False)
            if content is None:
                continue

            try:
                parsed = self._parse_bru_file(content)

                if parsed.get("method"):
                    folder = self._get_folder_path(file, path)
                    name = parsed.get("name", file.stem)
                    if folder:
                        name = f"{folder}/{name}"

                    requests.append({
                        "name": name,
                        "method": parsed["method"].upper(),
                        "path": self._extract_path(parsed.get("url", "")),
                    })
            except json.JSONDecodeError as e:
                logger.warning(f"Skipping {file.name}: invalid JSON in body - {e}")
                continue
            except ValueError as e:
                logger.warning(f"Skipping {file.name}: invalid request format - {e}")
                continue
            except Exception as e:
                logger.warning(f"Skipping {file.name}: unexpected error - {e}")
                continue

        return requests

    def _import_folder(
        self,
        path: Path,
        env_path: Path | None,
        name: str | None,
        base_url: str | None,
    ) -> ParsedCollection:
        """Import a Bruno collection folder."""
        # Load collection metadata
        collection_name = name or path.name
        bruno_json = path / "bruno.json"
        if bruno_json.exists():
            bruno_content = self._safe_read_utf8(bruno_json, raise_on_error=False)
            if bruno_content:
                try:
                    meta = json.loads(bruno_content)
                    collection_name = name or meta.get("name", path.name)
                except json.JSONDecodeError as e:
                    logger.warning(f"bruno.json is malformed, using folder name: {e}")

        # Load environment variables
        variables: dict[str, str] = {}
        detected_base_url: str | None = None

        if env_path:
            variables, detected_base_url = self._parse_environment(env_path)
        else:
            # Auto-detect environment file
            env_dir = path / "environments"
            if env_dir.exists():
                env_files = list(env_dir.glob("*.bru"))
                if env_files:
                    variables, detected_base_url = self._parse_environment(env_files[0])

        # Use provided base_url or detected one
        effective_base_url = base_url or detected_base_url

        # Parse all request files
        request_files = self._find_request_files(path)
        requests: list[CollectionRequest] = []

        for idx, file in enumerate(request_files):
            # Read file with proper error handling
            content = self._safe_read_utf8(file, raise_on_error=True)
            assert content is not None  # raise_on_error=True guarantees str return

            try:
                parsed = self._parse_bru_file(content)
            except json.JSONDecodeError as e:
                raise ImporterException(
                    f"Failed to parse JSON body in {file.name}",
                    details=str(e),
                ) from e

            if not parsed.get("method"):
                continue

            folder = self._get_folder_path(file, path)
            try:
                request = self._build_request_from_parsed(parsed, folder, idx)
                requests.append(request)
            except ValueError as e:
                raise ImporterException(
                    f"Failed to build request from {file.name}",
                    details=str(e),
                ) from e

        # Build metadata
        metadata = self._build_metadata(
            name=collection_name,
            source_path=str(path),
            base_url=effective_base_url,
            variables=variables,
        )

        return ParsedCollection(metadata=metadata, requests=requests)

    def _import_single_file(
        self,
        path: Path,
        name: str | None,
        base_url: str | None,
    ) -> ParsedCollection:
        """Import a single .bru file."""
        content = self._safe_read_utf8(path, raise_on_error=True)
        assert content is not None  # raise_on_error=True guarantees str return
        parsed = self._parse_bru_file(content)

        if not parsed.get("method"):
            raise ImporterException(
                "No HTTP method found in .bru file",
                details=f"File: {path}",
            )

        request = self._build_request_from_parsed(parsed, "", 0)

        metadata = self._build_metadata(
            name=name or parsed.get("name", path.stem),
            source_path=str(path),
            base_url=base_url,
        )

        return ParsedCollection(metadata=metadata, requests=[request])

    def _find_request_files(self, path: Path) -> list[Path]:
        """Find and sort .bru request files.

        Files are sorted by:
        1. Folder path
        2. Sequence number (from meta.seq)
        3. Filename

        Args:
            path: Collection root path.

        Returns:
            Sorted list of .bru file paths.
        """
        files = list(path.rglob("*.bru"))

        # Filter out environment files
        files = [f for f in files if "environments" not in f.parts]

        # Sort by folder, then by sequence, then by name
        def sort_key(file: Path) -> tuple[str, int, str]:
            folder = self._get_folder_path(file, path)
            seq = 999
            try:
                content = file.read_text(encoding="utf-8")
                seq_match = re.search(r"seq:\s*(\d+)", content)
                if seq_match:
                    seq = int(seq_match.group(1))
            except UnicodeDecodeError:
                logger.debug(f"Could not read sequence from {file.name}: encoding issue")
            except OSError as e:
                logger.debug(f"Could not read sequence from {file.name}: {e}")
            return (folder, seq, file.name)

        return sorted(files, key=sort_key)

    def _get_folder_path(self, file: Path, root: Path) -> str:
        """Get folder path relative to collection root.

        Args:
            file: Request file path.
            root: Collection root path.

        Returns:
            Folder path (e.g., "auth/users") or empty string.
        """
        try:
            relative = file.relative_to(root)
            parts = relative.parts[:-1]  # Exclude filename
            return "/".join(parts) if parts else ""
        except ValueError:
            return ""

    def _parse_bru_file(self, content: str) -> dict[str, Any]:
        """Parse a .bru file content.

        Args:
            content: Raw .bru file content.

        Returns:
            Parsed request data with keys:
            - name: Request name
            - method: HTTP method
            - url: Request URL
            - headers: Dict of headers
            - body: Request body (dict or string)
            - body_type: Body type
            - auth_type: Auth type
            - auth_value: Auth credentials
            - pre_script: Pre-request script
            - post_script: Post-response script
        """
        result: dict[str, Any] = {
            "name": "",
            "method": "",
            "url": "",
            "headers": {},
            "body": None,
            "body_type": "none",
            "auth_type": None,
            "auth_value": None,
            "pre_script": None,
            "post_script": None,
        }

        # Parse meta block
        meta = self._extract_block(content, "meta")
        if meta:
            meta_dict = self._parse_key_value(meta)
            result["name"] = meta_dict.get("name", "")

        # Parse HTTP method block (case-insensitive)
        for method in self.HTTP_METHODS:
            # Try lowercase first (most common)
            block = self._extract_block(content, method)
            if not block:
                # Try uppercase (fallback for some .bru files)
                block = self._extract_block(content, method.upper())
            if block:
                result["method"] = method.upper()
                method_dict = self._parse_key_value(block)
                result["url"] = method_dict.get("url", "")
                body_type = method_dict.get("body", "none")
                result["body_type"] = body_type
                break

        # Parse headers block
        headers_block = self._extract_block(content, "headers")
        if headers_block:
            result["headers"] = self._parse_key_value(headers_block)

        # Parse body:json block
        json_body = self._extract_block(content, "body:json")
        if json_body:
            try:
                result["body"] = json.loads(json_body.strip())
                result["body_type"] = "json"
            except json.JSONDecodeError:
                result["body"] = json_body.strip()
                result["body_type"] = "raw"

        # Parse auth:bearer block
        bearer_block = self._extract_block(content, "auth:bearer")
        if bearer_block:
            bearer_dict = self._parse_key_value(bearer_block)
            result["auth_type"] = "bearer"
            result["auth_value"] = bearer_dict.get("token", "")

        # Parse auth:basic block
        basic_block = self._extract_block(content, "auth:basic")
        if basic_block:
            basic_dict = self._parse_key_value(basic_block)
            username = basic_dict.get("username", "")
            password = basic_dict.get("password", "")
            result["auth_type"] = "basic"
            result["auth_value"] = f"{username}:{password}"

        # Parse scripts
        pre_script = self._extract_block(content, "script:pre-request")
        if pre_script:
            result["pre_script"] = pre_script.strip()

        post_script = self._extract_block(content, "script:post-response")
        if post_script:
            result["post_script"] = post_script.strip()

        return result

    def _extract_block(self, content: str, block_name: str) -> str | None:
        """Extract content of a named block.

        Args:
            content: Full .bru file content.
            block_name: Block name (e.g., "meta", "headers", "body:json").

        Returns:
            Block content or None if not found.
        """
        # Escape special regex characters in block name
        escaped_name = re.escape(block_name)
        pattern = rf"{escaped_name}\s*\{{([\s\S]*?)\n\}}"
        match = re.search(pattern, content)
        return match.group(1) if match else None

    def _parse_key_value(self, block: str) -> dict[str, str]:
        """Parse key: value pairs from a block.

        Args:
            block: Block content with key: value lines.

        Returns:
            Dict of parsed key-value pairs.
        """
        result: dict[str, str] = {}
        for line in block.strip().split("\n"):
            line = line.strip()
            if ":" in line and not line.startswith("#"):
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip()
                if key:
                    result[key] = value
        return result

    def _parse_environment(self, env_path: Path) -> tuple[dict[str, str], str | None]:
        """Parse environment file.

        Args:
            env_path: Path to environment .bru file.

        Returns:
            Tuple of (variables dict, base_url if found).
        """
        variables: dict[str, str] = {}
        base_url: str | None = None

        content = self._safe_read_utf8(env_path, raise_on_error=False)
        if content is None:
            return variables, base_url

        try:
            vars_block = self._extract_block(content, "vars")

            if vars_block:
                for line in vars_block.strip().split("\n"):
                    line = line.strip()
                    if ":" in line and not line.startswith("#"):
                        # Skip disabled vars (prefixed with ~)
                        if line.startswith("~"):
                            continue
                        key, _, value = line.partition(":")
                        key = key.strip()
                        value = value.strip()
                        if key:
                            variables[key] = value
                            if key in ("base_url", "baseUrl", "BASE_URL"):
                                base_url = value

        except Exception as e:
            logger.warning(f"Could not parse environment file {env_path.name}: {e}")

        return variables, base_url

    def _build_request_from_parsed(
        self,
        parsed: dict[str, Any],
        folder: str,
        sequence: int,
    ) -> CollectionRequest:
        """Build CollectionRequest from parsed .bru data."""
        # Handle auth headers
        headers = dict(parsed.get("headers", {}))
        if parsed.get("auth_type") == "bearer" and parsed.get("auth_value"):
            headers["Authorization"] = f"Bearer {parsed['auth_value']}"
        elif parsed.get("auth_type") == "basic" and parsed.get("auth_value"):
            encoded = base64.b64encode(parsed["auth_value"].encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"

        # Extract correlations from post-response script
        correlations: list[dict[str, str]] = []
        post_script = parsed.get("post_script")
        if post_script:
            extractor = CorrelationExtractor()
            extracted = extractor.extract_correlations(post_script, "bruno")
            correlations = [
                {"variable_name": c.variable_name, "json_path": c.json_path}
                for c in extracted
            ]
            if correlations:
                logger.debug(
                    f"Extracted {len(correlations)} correlations from post-script"
                )

        return self._build_request(
            name=parsed.get("name", "Unnamed Request"),
            method=parsed.get("method", "GET"),
            url=parsed.get("url", "/"),
            headers=headers if headers else None,
            body=parsed.get("body"),
            body_type=parsed.get("body_type", "none"),
            auth_type=parsed.get("auth_type"),
            auth_value=parsed.get("auth_value"),
            folder_path=folder,
            sequence=sequence,
            pre_script=parsed.get("pre_script"),
            post_script=post_script,
            correlations=correlations,
        )
