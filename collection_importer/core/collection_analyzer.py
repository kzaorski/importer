"""Collection Analyzer for discovering API collections in projects.

Scans directories for Bruno folders, Postman JSON, and Insomnia JSON files.
"""

import logging
from pathlib import Path
from typing import Any

from collection_importer.core.importers.base import BaseImporter
from collection_importer.core.importers.bruno import BrunoImporter
from collection_importer.core.importers.insomnia import InsomniaImporter
from collection_importer.core.importers.postman import PostmanImporter

logger = logging.getLogger(__name__)


class CollectionAnalyzer:
    """Discover and analyze API collections in project directories.

    Supports:
    - Bruno collections (folder with bruno.json or *.bru files)
    - Postman collections (any .json with valid Postman schema)
    - Insomnia exports (any .json with _type: export)
    """

    # Maximum directory depth to search
    MAX_DEPTH = 7

    # Common collection file patterns
    POSTMAN_PATTERNS = [
        "*.postman_collection.json",
        "*_collection.json",
        "postman/*.json",
    ]

    INSOMNIA_PATTERNS = [
        "insomnia*.json",
        "*_insomnia.json",
        "insomnia/*.json",
    ]

    def __init__(self) -> None:
        """Initialize analyzer with available importers."""
        self._importers: list[BaseImporter] = [
            BrunoImporter(),
            PostmanImporter(),
            InsomniaImporter(),
        ]

    def analyze_project(self, path: str = ".") -> dict[str, Any]:
        """Analyze project directory for API collections.

        Args:
            path: Project directory path (default: current directory).

        Returns:
            Analysis result with keys:
            - collections_found: bool
            - collections: list of found collections
            - recommended_collection: path to recommended collection
        """
        root = Path(path).resolve()

        if not root.exists():
            return {
                "collections_found": False,
                "collections": [],
                "recommended_collection": None,
                "error": f"Path does not exist: {path}",
            }

        collections = self._find_collections(root)

        # Sort by priority: Bruno > Postman > Insomnia
        format_priority = {"bruno": 0, "postman": 1, "insomnia": 2, "unknown": 3}
        collections.sort(key=lambda c: (format_priority.get(c["format"], 3), c["path"]))

        recommended = collections[0]["path"] if collections else None

        return {
            "collections_found": len(collections) > 0,
            "collections": collections,
            "recommended_collection": recommended,
        }

    def detect_format(self, path: str) -> str:
        """Auto-detect collection format.

        Args:
            path: Path to collection file or folder.

        Returns:
            Format name: 'bruno', 'postman', 'insomnia', or 'unknown'.
        """
        p = Path(path)

        if not p.exists():
            return "unknown"

        # Check with registered importers
        for importer in self._importers:
            if importer.can_import(p):
                return importer.format_name

        # Check for Postman patterns
        if p.is_file():
            name = p.name.lower()
            if "postman" in name and name.endswith(".json"):
                return "postman"
            if "insomnia" in name and name.endswith(".json"):
                return "insomnia"
            if name.endswith("_collection.json"):
                return "postman"

        return "unknown"

    def get_importer(self, format_name: str) -> BaseImporter | None:
        """Get importer for a specific format.

        Args:
            format_name: Format name (bruno, postman, insomnia).

        Returns:
            Importer instance or None if not found.
        """
        for importer in self._importers:
            if importer.format_name == format_name:
                return importer
        return None

    def _find_collections(
        self,
        root: Path,
        depth: int = 0,
    ) -> list[dict[str, Any]]:
        """Recursively find collections in directory.

        Args:
            root: Directory to search.
            depth: Current search depth.

        Returns:
            List of collection info dicts.
        """
        collections: list[dict[str, Any]] = []

        if depth > self.MAX_DEPTH:
            return collections

        is_bruno_collection = False

        # Check if current directory is a Bruno collection
        if (root / "bruno.json").exists():
            collections.append(self._analyze_collection(root, "bruno"))
            is_bruno_collection = True
        elif list(root.glob("*.bru")):
            # .bru files without bruno.json - still a Bruno collection
            collections.append(self._analyze_collection(root, "bruno"))
            is_bruno_collection = True

        # Check for Postman and Insomnia files using content-based detection
        if not is_bruno_collection:
            postman_importer = self.get_importer("postman")
            insomnia_importer = self.get_importer("insomnia")

            for json_file in root.glob("*.json"):
                if not json_file.is_file():
                    continue
                # Check Postman first (higher priority)
                if postman_importer and postman_importer.can_import(json_file):
                    collections.append(self._analyze_collection(json_file, "postman"))
                elif insomnia_importer and insomnia_importer.can_import(json_file):
                    collections.append(self._analyze_collection(json_file, "insomnia"))

        # Recurse into subdirectories
        try:
            for child in root.iterdir():
                if child.is_dir() and not child.name.startswith("."):
                    # Skip common non-collection directories
                    if child.name in ("node_modules", "__pycache__", "venv", ".git"):
                        continue

                    # Skip Bruno collection subdirectories (environments, folders with .bru)
                    if is_bruno_collection:
                        # Skip if it's part of parent Bruno collection (has .bru files but no bruno.json)
                        if list(child.glob("*.bru")) and not (child / "bruno.json").exists():
                            continue
                        # Skip environments folder
                        if child.name == "environments":
                            continue

                    collections.extend(self._find_collections(child, depth + 1))
        except PermissionError as e:
            logger.debug(f"Permission denied accessing {root}: {e}")
        except OSError as e:
            logger.debug(f"Error accessing {root}: {e}")

        return collections

    def _analyze_collection(self, path: Path, format_name: str) -> dict[str, Any]:
        """Analyze a single collection.

        Args:
            path: Path to collection.
            format_name: Detected format.

        Returns:
            Collection info dict.
        """
        info = {
            "path": str(path),
            "format": format_name,
            "name": path.name,
            "requests_count": 0,
        }

        # Try to get request count
        importer = self.get_importer(format_name)
        if importer:
            try:
                requests = importer.list_requests(path)
                info["requests_count"] = len(requests)
            except Exception as e:
                logger.debug(f"Could not list requests for {path}: {e}")

        return info
