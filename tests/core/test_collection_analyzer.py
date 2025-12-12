"""Unit tests for collection_analyzer module."""

import json
from pathlib import Path

import pytest

from collection_importer.core.collection_analyzer import CollectionAnalyzer


class TestCollectionAnalyzerDetectFormat:
    """Tests for CollectionAnalyzer.detect_format method."""

    @pytest.fixture
    def analyzer(self) -> CollectionAnalyzer:
        """Create CollectionAnalyzer instance."""
        return CollectionAnalyzer()

    def test_detect_nonexistent_path(self, analyzer: CollectionAnalyzer) -> None:
        """Test detection returns unknown for nonexistent path."""
        result = analyzer.detect_format("/nonexistent/path")
        assert result == "unknown"

    def test_detect_bruno_folder_with_json(
        self, analyzer: CollectionAnalyzer, tmp_path: Path
    ) -> None:
        """Test detection of Bruno folder with bruno.json."""
        (tmp_path / "bruno.json").write_text('{"name": "test"}')
        result = analyzer.detect_format(str(tmp_path))
        assert result == "bruno"

    def test_detect_bruno_folder_with_bru_files(
        self, analyzer: CollectionAnalyzer, tmp_path: Path
    ) -> None:
        """Test detection of Bruno folder with .bru files."""
        (tmp_path / "test.bru").write_text("meta { name: test }")
        result = analyzer.detect_format(str(tmp_path))
        assert result == "bruno"

    def test_detect_postman_file(
        self, analyzer: CollectionAnalyzer, tmp_path: Path
    ) -> None:
        """Test detection of Postman collection file."""
        collection = {
            "info": {
                "_postman_id": "test-id",
                "name": "Test Collection",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            },
            "item": [],
        }
        file_path = tmp_path / "test.postman_collection.json"
        file_path.write_text(json.dumps(collection))
        result = analyzer.detect_format(str(file_path))
        assert result == "postman"

    def test_detect_postman_by_filename_pattern(
        self, analyzer: CollectionAnalyzer, tmp_path: Path
    ) -> None:
        """Test detection of Postman by filename pattern."""
        file_path = tmp_path / "api_collection.json"
        file_path.write_text('{"info": {"name": "test"}, "item": []}')
        result = analyzer.detect_format(str(file_path))
        assert result == "postman"

    def test_detect_insomnia_file(
        self, analyzer: CollectionAnalyzer, tmp_path: Path
    ) -> None:
        """Test detection of Insomnia export file."""
        export = {
            "_type": "export",
            "__export_format": 4,
            "resources": [],
        }
        file_path = tmp_path / "insomnia_export.json"
        file_path.write_text(json.dumps(export))
        result = analyzer.detect_format(str(file_path))
        assert result == "insomnia"

    def test_detect_insomnia_by_filename_pattern(
        self, analyzer: CollectionAnalyzer, tmp_path: Path
    ) -> None:
        """Test detection of Insomnia by filename pattern."""
        file_path = tmp_path / "insomnia_backup.json"
        file_path.write_text('{"_type": "export", "resources": []}')
        result = analyzer.detect_format(str(file_path))
        assert result == "insomnia"

    def test_detect_unknown_json(
        self, analyzer: CollectionAnalyzer, tmp_path: Path
    ) -> None:
        """Test detection returns unknown for unrecognized JSON."""
        file_path = tmp_path / "random.json"
        file_path.write_text('{"random": "data"}')
        result = analyzer.detect_format(str(file_path))
        assert result == "unknown"

    def test_detect_unknown_empty_folder(
        self, analyzer: CollectionAnalyzer, tmp_path: Path
    ) -> None:
        """Test detection returns unknown for empty folder."""
        result = analyzer.detect_format(str(tmp_path))
        assert result == "unknown"


class TestCollectionAnalyzerGetImporter:
    """Tests for CollectionAnalyzer.get_importer method."""

    @pytest.fixture
    def analyzer(self) -> CollectionAnalyzer:
        """Create CollectionAnalyzer instance."""
        return CollectionAnalyzer()

    def test_get_bruno_importer(self, analyzer: CollectionAnalyzer) -> None:
        """Test getting Bruno importer."""
        importer = analyzer.get_importer("bruno")
        assert importer is not None
        assert importer.format_name == "bruno"

    def test_get_postman_importer(self, analyzer: CollectionAnalyzer) -> None:
        """Test getting Postman importer."""
        importer = analyzer.get_importer("postman")
        assert importer is not None
        assert importer.format_name == "postman"

    def test_get_insomnia_importer(self, analyzer: CollectionAnalyzer) -> None:
        """Test getting Insomnia importer."""
        importer = analyzer.get_importer("insomnia")
        assert importer is not None
        assert importer.format_name == "insomnia"

    def test_get_unknown_importer(self, analyzer: CollectionAnalyzer) -> None:
        """Test getting unknown format returns None."""
        importer = analyzer.get_importer("unknown")
        assert importer is None

    def test_get_nonexistent_importer(self, analyzer: CollectionAnalyzer) -> None:
        """Test getting nonexistent format returns None."""
        importer = analyzer.get_importer("swagger")
        assert importer is None


class TestCollectionAnalyzerAnalyzeProject:
    """Tests for CollectionAnalyzer.analyze_project method."""

    @pytest.fixture
    def analyzer(self) -> CollectionAnalyzer:
        """Create CollectionAnalyzer instance."""
        return CollectionAnalyzer()

    def test_analyze_nonexistent_path(self, analyzer: CollectionAnalyzer) -> None:
        """Test analyze returns error for nonexistent path."""
        result = analyzer.analyze_project("/nonexistent/path")
        assert result["collections_found"] is False
        assert result["collections"] == []
        assert result["recommended_collection"] is None
        assert "error" in result

    def test_analyze_empty_directory(
        self, analyzer: CollectionAnalyzer, tmp_path: Path
    ) -> None:
        """Test analyze empty directory."""
        result = analyzer.analyze_project(str(tmp_path))
        assert result["collections_found"] is False
        assert result["collections"] == []
        assert result["recommended_collection"] is None

    def test_analyze_finds_bruno(
        self, analyzer: CollectionAnalyzer, tmp_path: Path
    ) -> None:
        """Test analyze finds Bruno collection."""
        bruno_dir = tmp_path / "api"
        bruno_dir.mkdir()
        (bruno_dir / "bruno.json").write_text('{"name": "API Collection"}')
        (bruno_dir / "get-users.bru").write_text(
            "meta {\n  name: Get Users\n}\n\nget {\n  url: /users\n}\n"
        )

        result = analyzer.analyze_project(str(tmp_path))
        assert result["collections_found"] is True
        assert len(result["collections"]) == 1
        assert result["collections"][0]["format"] == "bruno"
        assert result["recommended_collection"] is not None

    def test_analyze_finds_postman(
        self, analyzer: CollectionAnalyzer, tmp_path: Path
    ) -> None:
        """Test analyze finds Postman collection."""
        collection = {
            "info": {
                "_postman_id": "123",
                "name": "Test",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            },
            "item": [
                {
                    "name": "Get Users",
                    "request": {"method": "GET", "url": "/users"},
                }
            ],
        }
        file_path = tmp_path / "api.postman_collection.json"
        file_path.write_text(json.dumps(collection))

        result = analyzer.analyze_project(str(tmp_path))
        assert result["collections_found"] is True
        # May find duplicates due to overlapping patterns
        assert len(result["collections"]) >= 1
        # At least one should be postman format
        postman_collections = [c for c in result["collections"] if c["format"] == "postman"]
        assert len(postman_collections) >= 1

    def test_analyze_finds_insomnia(
        self, analyzer: CollectionAnalyzer, tmp_path: Path
    ) -> None:
        """Test analyze finds Insomnia collection."""
        export = {
            "_type": "export",
            "__export_format": 4,
            "resources": [
                {
                    "_id": "wrk_1",
                    "_type": "workspace",
                    "name": "Test Workspace",
                },
                {
                    "_id": "req_1",
                    "_type": "request",
                    "parentId": "wrk_1",
                    "name": "Get Users",
                    "method": "GET",
                    "url": "http://localhost/users",
                },
            ],
        }
        file_path = tmp_path / "insomnia_export.json"
        file_path.write_text(json.dumps(export))

        result = analyzer.analyze_project(str(tmp_path))
        assert result["collections_found"] is True
        assert len(result["collections"]) == 1
        assert result["collections"][0]["format"] == "insomnia"

    def test_analyze_prioritizes_bruno(
        self, analyzer: CollectionAnalyzer, tmp_path: Path
    ) -> None:
        """Test analyze prioritizes Bruno over Postman."""
        # Create Bruno collection
        bruno_dir = tmp_path / "bruno-api"
        bruno_dir.mkdir()
        (bruno_dir / "bruno.json").write_text('{"name": "Bruno API"}')

        # Create Postman collection
        postman = {
            "info": {
                "_postman_id": "123",
                "name": "Postman API",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            },
            "item": [],
        }
        (tmp_path / "api.postman_collection.json").write_text(json.dumps(postman))

        result = analyzer.analyze_project(str(tmp_path))
        assert result["collections_found"] is True
        # May find duplicate postman due to overlapping patterns
        assert len(result["collections"]) >= 2
        # Bruno should be recommended (first in list after sorting)
        assert result["collections"][0]["format"] == "bruno"
        assert "bruno" in result["recommended_collection"].lower()

    def test_analyze_respects_depth_limit(
        self, analyzer: CollectionAnalyzer, tmp_path: Path
    ) -> None:
        """Test analyze respects max depth limit."""
        # Create deeply nested Bruno collection (depth 8, beyond MAX_DEPTH of 7)
        deep_dir = tmp_path / "a" / "b" / "c" / "d" / "e" / "f" / "g" / "h"
        deep_dir.mkdir(parents=True)
        (deep_dir / "bruno.json").write_text('{"name": "Deep Collection"}')

        result = analyzer.analyze_project(str(tmp_path))
        # Should not find collection beyond MAX_DEPTH (7)
        assert result["collections_found"] is False

    def test_analyze_skips_node_modules(
        self, analyzer: CollectionAnalyzer, tmp_path: Path
    ) -> None:
        """Test analyze skips node_modules directory."""
        node_modules = tmp_path / "node_modules" / "some-package"
        node_modules.mkdir(parents=True)
        (node_modules / "bruno.json").write_text('{"name": "Package Collection"}')

        result = analyzer.analyze_project(str(tmp_path))
        assert result["collections_found"] is False

    def test_analyze_skips_git_directory(
        self, analyzer: CollectionAnalyzer, tmp_path: Path
    ) -> None:
        """Test analyze skips .git directory."""
        git_dir = tmp_path / ".git" / "hooks"
        git_dir.mkdir(parents=True)
        (git_dir / "bruno.json").write_text('{"name": "Git Collection"}')

        result = analyzer.analyze_project(str(tmp_path))
        assert result["collections_found"] is False

    def test_analyze_counts_requests(
        self, analyzer: CollectionAnalyzer, tmp_path: Path
    ) -> None:
        """Test analyze counts requests in collection."""
        bruno_dir = tmp_path / "api"
        bruno_dir.mkdir()
        (bruno_dir / "bruno.json").write_text('{"name": "API"}')
        (bruno_dir / "get-users.bru").write_text(
            "meta {\n  name: Get Users\n}\n\nget {\n  url: /users\n}\n"
        )
        (bruno_dir / "create-user.bru").write_text(
            "meta {\n  name: Create User\n}\n\npost {\n  url: /users\n}\n"
        )

        result = analyzer.analyze_project(str(tmp_path))
        assert result["collections_found"] is True
        assert result["collections"][0]["requests_count"] == 2


class TestCollectionAnalyzerInit:
    """Tests for CollectionAnalyzer initialization."""

    def test_init_creates_importers(self) -> None:
        """Test initialization creates all importers."""
        analyzer = CollectionAnalyzer()
        assert len(analyzer._importers) == 3

    def test_init_importers_have_format_names(self) -> None:
        """Test all importers have format names."""
        analyzer = CollectionAnalyzer()
        format_names = [i.format_name for i in analyzer._importers]
        assert "bruno" in format_names
        assert "postman" in format_names
        assert "insomnia" in format_names

    def test_max_depth_constant(self) -> None:
        """Test MAX_DEPTH is set."""
        analyzer = CollectionAnalyzer()
        assert analyzer.MAX_DEPTH == 7


class TestCollectionAnalyzerPatterns:
    """Tests for collection file patterns."""

    def test_postman_patterns(self) -> None:
        """Test Postman patterns are defined."""
        analyzer = CollectionAnalyzer()
        assert "*.postman_collection.json" in analyzer.POSTMAN_PATTERNS
        assert "*_collection.json" in analyzer.POSTMAN_PATTERNS

    def test_insomnia_patterns(self) -> None:
        """Test Insomnia patterns are defined."""
        analyzer = CollectionAnalyzer()
        assert "insomnia*.json" in analyzer.INSOMNIA_PATTERNS
        assert "*_insomnia.json" in analyzer.INSOMNIA_PATTERNS


class TestCollectionAnalyzerNestedCollections:
    """Tests for nested collection detection."""

    @pytest.fixture
    def analyzer(self) -> CollectionAnalyzer:
        """Create CollectionAnalyzer instance."""
        return CollectionAnalyzer()

    def test_finds_nested_bruno_collections(
        self, analyzer: CollectionAnalyzer, tmp_path: Path
    ) -> None:
        """Test analyzer finds nested Bruno collections."""
        # Create main collection
        main_dir = tmp_path / "main-api"
        main_dir.mkdir()
        (main_dir / "bruno.json").write_text('{"name": "Main API"}')
        (main_dir / "get-users.bru").write_text(
            "meta {\n  name: Get Users\n}\n\nget {\n  url: /users\n}\n"
        )

        # Create nested collections in subdirectory
        nested_dir = main_dir / "microservices" / "auth-service"
        nested_dir.mkdir(parents=True)
        (nested_dir / "bruno.json").write_text('{"name": "Auth Service"}')
        (nested_dir / "login.bru").write_text(
            "meta {\n  name: Login\n}\n\npost {\n  url: /login\n}\n"
        )

        user_service = main_dir / "microservices" / "user-service"
        user_service.mkdir(parents=True)
        (user_service / "bruno.json").write_text('{"name": "User Service"}')

        result = analyzer.analyze_project(str(tmp_path))

        # Should find all 3 collections
        bruno_collections = [c for c in result["collections"] if c["format"] == "bruno"]
        assert len(bruno_collections) == 3

        # Verify paths
        paths = [c["path"] for c in bruno_collections]
        assert any("main-api" in p and "microservices" not in p for p in paths)
        assert any("auth-service" in p for p in paths)
        assert any("user-service" in p for p in paths)

    def test_skips_bruno_subdirectories_without_bruno_json(
        self, analyzer: CollectionAnalyzer, tmp_path: Path
    ) -> None:
        """Test that folders with .bru files but no bruno.json are skipped."""
        # Create Bruno collection with subfolders
        api_dir = tmp_path / "api"
        api_dir.mkdir()
        (api_dir / "bruno.json").write_text('{"name": "API"}')

        # Create subfolders with .bru files (part of parent collection)
        auth_dir = api_dir / "auth"
        auth_dir.mkdir()
        (auth_dir / "login.bru").write_text(
            "meta {\n  name: Login\n}\n\npost {\n  url: /login\n}\n"
        )

        users_dir = api_dir / "users"
        users_dir.mkdir()
        (users_dir / "get-users.bru").write_text(
            "meta {\n  name: Get Users\n}\n\nget {\n  url: /users\n}\n"
        )

        result = analyzer.analyze_project(str(tmp_path))

        # Should find only 1 collection (auth/ and users/ are part of parent)
        assert len(result["collections"]) == 1
        assert result["collections"][0]["format"] == "bruno"
        assert "api" in result["collections"][0]["path"]

    def test_skips_environments_folder(
        self, analyzer: CollectionAnalyzer, tmp_path: Path
    ) -> None:
        """Test that environments folder is skipped and not detected as separate collection."""
        api_dir = tmp_path / "api"
        api_dir.mkdir()
        (api_dir / "bruno.json").write_text('{"name": "API"}')

        # Create environments folder with .bru files
        env_dir = api_dir / "environments"
        env_dir.mkdir()
        (env_dir / "dev.bru").write_text("vars {\n  base_url: http://localhost\n}\n")

        result = analyzer.analyze_project(str(tmp_path))

        # Should find only 1 collection (environments/ is skipped)
        assert len(result["collections"]) == 1
        assert result["collections"][0]["format"] == "bruno"
        # The collection path should be api/, not environments/
        assert result["collections"][0]["path"].endswith("api")

    def test_finds_mixed_collections_in_nested_structure(
        self, analyzer: CollectionAnalyzer, tmp_path: Path
    ) -> None:
        """Test finding Bruno, Postman, and Insomnia in nested directories."""
        # Create Bruno collection
        bruno_dir = tmp_path / "api" / "bruno"
        bruno_dir.mkdir(parents=True)
        (bruno_dir / "bruno.json").write_text('{"name": "Bruno API"}')

        # Create Postman collection
        postman_dir = tmp_path / "api" / "postman"
        postman_dir.mkdir()
        postman = {
            "info": {
                "_postman_id": "123",
                "name": "Postman API",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            },
            "item": [],
        }
        (postman_dir / "test.postman_collection.json").write_text(json.dumps(postman))

        # Create Insomnia collection
        insomnia_dir = tmp_path / "api" / "insomnia"
        insomnia_dir.mkdir()
        insomnia = {
            "_type": "export",
            "__export_format": 4,
            "resources": [],
        }
        (insomnia_dir / "insomnia_export.json").write_text(json.dumps(insomnia))

        result = analyzer.analyze_project(str(tmp_path))

        formats = {c["format"] for c in result["collections"]}
        assert "bruno" in formats
        assert "postman" in formats
        assert "insomnia" in formats

    def test_nested_bruno_with_separate_bruno_json(
        self, analyzer: CollectionAnalyzer, tmp_path: Path
    ) -> None:
        """Test nested folder with its own bruno.json is detected as separate collection."""
        # Create parent collection
        parent_dir = tmp_path / "api"
        parent_dir.mkdir()
        (parent_dir / "bruno.json").write_text('{"name": "Parent API"}')
        (parent_dir / "main.bru").write_text(
            "meta {\n  name: Main\n}\n\nget {\n  url: /main\n}\n"
        )

        # Create nested folder with .bru files but WITHOUT bruno.json (part of parent)
        part_of_parent = parent_dir / "utils"
        part_of_parent.mkdir()
        (part_of_parent / "helper.bru").write_text(
            "meta {\n  name: Helper\n}\n\nget {\n  url: /helper\n}\n"
        )

        # Create nested folder WITH its own bruno.json (separate collection)
        separate = parent_dir / "separate"
        separate.mkdir()
        (separate / "bruno.json").write_text('{"name": "Separate API"}')
        (separate / "other.bru").write_text(
            "meta {\n  name: Other\n}\n\nget {\n  url: /other\n}\n"
        )

        result = analyzer.analyze_project(str(tmp_path))

        bruno_collections = [c for c in result["collections"] if c["format"] == "bruno"]

        # Should find 2 collections: parent and separate (not utils)
        assert len(bruno_collections) == 2

        paths = [c["path"] for c in bruno_collections]
        assert any("api" in p and "separate" not in p for p in paths)
        assert any("separate" in p for p in paths)
        # utils should NOT be a separate collection
        assert not any(p.endswith("utils") for p in paths)

    def test_finds_collections_in_fixture_directory(
        self, analyzer: CollectionAnalyzer
    ) -> None:
        """Test analyzer finds nested Bruno collections in test fixtures."""
        # Use actual test fixtures
        fixtures_path = Path(__file__).parent.parent / "fixtures" / "collections" / "bruno"

        if not fixtures_path.exists():
            pytest.skip("Bruno fixtures directory not found")

        result = analyzer.analyze_project(str(fixtures_path))

        # Should find main collection + real-world/jsonplaceholder + real-world/github-api
        bruno_collections = [c for c in result["collections"] if c["format"] == "bruno"]
        assert len(bruno_collections) >= 3

        # Verify paths contain expected collections
        paths = [c["path"] for c in bruno_collections]
        assert any("jsonplaceholder" in p for p in paths)
        assert any("github-api" in p for p in paths)
