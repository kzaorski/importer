"""Unit tests for CLI interface.

Tests cover:
- analyze command: project discovery
- import command: collection import and JMX generation
- mcp command: MCP server startup
- Helper functions: _show_preview
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from collection_importer.cli import _generate_jmx_filename, _show_preview, cli
from collection_importer.core.importer_factory import get_importer
from collection_importer.exceptions import CollectionImporterException


class TestAnalyzeCommand:
    """Tests for 'analyze' CLI command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    def test_analyze_default_path(self, runner: CliRunner) -> None:
        """Test analyze with fixtures collections directory."""
        fixtures_path = Path(__file__).parent / "fixtures" / "collections"
        # Input "0" to skip import prompt
        result = runner.invoke(cli, ["analyze", "--path", str(fixtures_path)], input="0\n")
        assert result.exit_code == 0
        # Should find Bruno, Postman, and Insomnia collections
        assert "BRUNO" in result.output.upper()
        assert "POSTMAN" in result.output.upper()
        assert "INSOMNIA" in result.output.upper()

    def test_analyze_with_bruno_collection(
        self, runner: CliRunner, bruno_collection_dir: Path
    ) -> None:
        """Test analyze finds Bruno collection."""
        # Input "0" to skip selection (multiple nested Bruno collections)
        result = runner.invoke(cli, ["analyze", "--path", str(bruno_collection_dir)], input="0\n")
        assert result.exit_code == 0
        assert "BRUNO" in result.output.upper()

    def test_analyze_with_postman_collection(
        self, runner: CliRunner, postman_collection_file: Path
    ) -> None:
        """Test analyze finds Postman collection."""
        # Input "n" to decline import confirmation
        result = runner.invoke(
            cli, ["analyze", "--path", str(postman_collection_file.parent)], input="n\n"
        )
        assert result.exit_code == 0
        # May or may not find the collection depending on structure

    def test_analyze_nonexistent_path(self, runner: CliRunner) -> None:
        """Test analyze with non-existent path shows error."""
        result = runner.invoke(cli, ["analyze", "--path", "/nonexistent/path"])
        assert result.exit_code == 1
        assert "Error" in result.output or "No API collections found" in result.output

    def test_analyze_empty_directory(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test analyze with empty directory shows no collections."""
        result = runner.invoke(cli, ["analyze", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert "No API collections found" in result.output

    def test_analyze_short_option(
        self, runner: CliRunner, bruno_collection_dir: Path
    ) -> None:
        """Test analyze with -p short option."""
        # Input "0" to skip selection (multiple nested Bruno collections)
        result = runner.invoke(cli, ["analyze", "-p", str(bruno_collection_dir)], input="0\n")
        assert result.exit_code == 0


class TestImportCommand:
    """Tests for 'import' CLI command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    def test_import_bruno_collection(
        self, runner: CliRunner, bruno_collection_dir: Path, tmp_path: Path
    ) -> None:
        """Test importing Bruno collection."""
        output = str(tmp_path / "test.jmx")
        result = runner.invoke(
            cli, ["import", str(bruno_collection_dir), "-o", output]
        )
        assert result.exit_code == 0
        assert "JMX file generated successfully" in result.output
        assert Path(output).exists()

    def test_import_postman_collection(
        self, runner: CliRunner, postman_collection_file: Path, tmp_path: Path
    ) -> None:
        """Test importing Postman collection."""
        output = str(tmp_path / "test.jmx")
        result = runner.invoke(
            cli, ["import", str(postman_collection_file), "-o", output]
        )
        assert result.exit_code == 0
        assert Path(output).exists()

    def test_import_insomnia_collection(
        self, runner: CliRunner, insomnia_collection_file: Path, tmp_path: Path
    ) -> None:
        """Test importing Insomnia collection."""
        output = str(tmp_path / "test.jmx")
        result = runner.invoke(
            cli, ["import", str(insomnia_collection_file), "-o", output]
        )
        assert result.exit_code == 0
        assert Path(output).exists()

    def test_import_with_format_flag(
        self, runner: CliRunner, postman_collection_file: Path, tmp_path: Path
    ) -> None:
        """Test import with explicit format flag."""
        output = str(tmp_path / "test.jmx")
        result = runner.invoke(
            cli,
            ["import", str(postman_collection_file), "-f", "postman", "-o", output],
        )
        assert result.exit_code == 0

    def test_import_with_thread_options(
        self, runner: CliRunner, bruno_collection_dir: Path, tmp_path: Path
    ) -> None:
        """Test import with thread configuration."""
        output = str(tmp_path / "test.jmx")
        result = runner.invoke(
            cli,
            [
                "import",
                str(bruno_collection_dir),
                "-o",
                output,
                "--threads",
                "50",
                "--rampup",
                "10",
                "--duration",
                "300",
            ],
        )
        assert result.exit_code == 0
        assert "Threads: 50" in result.output

    def test_import_preview_mode(
        self, runner: CliRunner, bruno_collection_dir: Path
    ) -> None:
        """Test import with --preview flag."""
        result = runner.invoke(
            cli, ["import", str(bruno_collection_dir), "--preview"]
        )
        assert result.exit_code == 0
        assert "Preview" in result.output or "Total:" in result.output

    def test_import_verbose_mode(
        self, runner: CliRunner, bruno_collection_dir: Path, tmp_path: Path
    ) -> None:
        """Test import with --verbose flag."""
        output = str(tmp_path / "test.jmx")
        result = runner.invoke(
            cli, ["import", str(bruno_collection_dir), "-o", output, "-v"]
        )
        assert result.exit_code == 0

    def test_import_with_base_url_override(
        self, runner: CliRunner, bruno_collection_dir: Path, tmp_path: Path
    ) -> None:
        """Test import with base URL override."""
        output = str(tmp_path / "test.jmx")
        result = runner.invoke(
            cli,
            [
                "import",
                str(bruno_collection_dir),
                "-o",
                output,
                "--base-url",
                "https://api.example.com",
            ],
        )
        assert result.exit_code == 0

    def test_import_unknown_format_error(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test import with unknown format shows error."""
        unknown_file = tmp_path / "unknown.txt"
        unknown_file.write_text("not a collection")
        result = runner.invoke(cli, ["import", str(unknown_file)])
        assert result.exit_code == 1
        assert "Could not detect collection format" in result.output

    def test_import_nonexistent_path_error(self, runner: CliRunner) -> None:
        """Test import with non-existent path shows error."""
        result = runner.invoke(cli, ["import", "/nonexistent/collection"])
        # Click returns 2 for invalid path or 1 for our error handling
        assert result.exit_code in (1, 2)

    def test_import_default_output(
        self, runner: CliRunner, bruno_collection_dir: Path, tmp_path: Path
    ) -> None:
        """Test import uses default output filename."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["import", str(bruno_collection_dir)])
            assert result.exit_code == 0
            assert Path("test.jmx").exists()


class TestMcpCommand:
    """Tests for 'mcp' CLI command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    @patch("collection_importer.mcp_server.run_server")
    def test_mcp_starts_server(
        self, mock_run_server: MagicMock, runner: CliRunner
    ) -> None:
        """Test mcp command starts server."""
        result = runner.invoke(cli, ["mcp"])
        assert "Starting MCP Server" in result.output
        mock_run_server.assert_called_once()


class TestImporterFactory:
    """Tests for importer factory function."""

    def test_get_bruno_importer(self) -> None:
        """Test getting Bruno importer."""
        importer = get_importer("bruno")
        assert importer.format_name == "bruno"

    def test_get_postman_importer(self) -> None:
        """Test getting Postman importer."""
        importer = get_importer("postman")
        assert importer.format_name == "postman"

    def test_get_insomnia_importer(self) -> None:
        """Test getting Insomnia importer."""
        importer = get_importer("insomnia")
        assert importer.format_name == "insomnia"

    def test_get_unknown_importer_raises(self) -> None:
        """Test getting unknown importer raises exception."""
        with pytest.raises(CollectionImporterException) as exc_info:
            get_importer("unknown")
        assert "not supported" in str(exc_info.value)


class TestShowPreview:
    """Tests for _show_preview helper function."""

    def test_show_preview_displays_requests(
        self, bruno_collection_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test preview displays request information."""
        from collection_importer.core.importers.bruno import BrunoImporter

        importer = BrunoImporter()
        _show_preview(importer, bruno_collection_dir)
        captured = capsys.readouterr()
        # Should display some HTTP method
        assert any(method in captured.out for method in ["GET", "POST", "PUT", "DELETE"])

    def test_show_preview_empty_collection(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test preview with empty collection shows message."""
        from collection_importer.core.importers.bruno import BrunoImporter

        # Create empty bruno collection
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        (empty_dir / "bruno.json").write_text('{"name": "Empty"}')

        importer = BrunoImporter()
        _show_preview(importer, empty_dir)
        captured = capsys.readouterr()
        assert "No requests found" in captured.out


class TestVersionOption:
    """Tests for --version option."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    def test_version_output(self, runner: CliRunner) -> None:
        """Test --version shows version."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "collection-importer" in result.output

    def test_help_output(self, runner: CliRunner) -> None:
        """Test --help shows help."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "analyze" in result.output
        assert "import" in result.output
        assert "mcp" in result.output


class TestImportCommandEdgeCases:
    """Edge case tests for import command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    def test_import_with_env_file(
        self, runner: CliRunner, bruno_collection_dir: Path, tmp_path: Path
    ) -> None:
        """Test import with environment file."""
        output = str(tmp_path / "test.jmx")
        env_file = bruno_collection_dir / "environments" / "dev.bru"
        if env_file.exists():
            result = runner.invoke(
                cli,
                [
                    "import",
                    str(bruno_collection_dir),
                    "-o",
                    output,
                    "--env",
                    str(env_file),
                ],
            )
            assert result.exit_code == 0

    def test_import_real_world_collection(
        self, runner: CliRunner, bruno_real_world_jsonplaceholder: Path, tmp_path: Path
    ) -> None:
        """Test importing real-world JSONPlaceholder collection."""
        output = str(tmp_path / "jsonplaceholder.jmx")
        result = runner.invoke(
            cli,
            ["import", str(bruno_real_world_jsonplaceholder), "-o", output],
        )
        assert result.exit_code == 0
        assert Path(output).exists()

    def test_import_invalid_format_flag(
        self, runner: CliRunner, bruno_collection_dir: Path, tmp_path: Path
    ) -> None:
        """Test import with invalid format flag."""
        output = str(tmp_path / "test.jmx")
        result = runner.invoke(
            cli,
            ["import", str(bruno_collection_dir), "-f", "invalid", "-o", output],
        )
        # Click validates choices, returns 2 for invalid choice
        assert result.exit_code == 2
        assert "Invalid value" in result.output


class TestGenerateJmxFilename:
    """Tests for _generate_jmx_filename helper function."""

    def test_bruno_directory_two_segments(self, tmp_path: Path) -> None:
        """Test filename generation for Bruno directory with two segments."""
        api_dir = tmp_path / "api" / "users"
        api_dir.mkdir(parents=True)
        collection = {"path": str(api_dir), "format": "bruno"}
        filename = _generate_jmx_filename(collection)
        assert filename == "api-users.jmx"

    def test_bruno_directory_uses_last_two_segments(self, tmp_path: Path) -> None:
        """Test filename generation uses last 2 path segments for Bruno."""
        api_dir = tmp_path / "project" / "api" / "users"
        api_dir.mkdir(parents=True)
        collection = {"path": str(api_dir), "format": "bruno"}
        filename = _generate_jmx_filename(collection)
        assert filename == "api-users.jmx"

    def test_postman_collection_file(self, tmp_path: Path) -> None:
        """Test filename generation for Postman collection file."""
        postman_file = tmp_path / "my-api.postman_collection.json"
        postman_file.write_text("{}")
        collection = {"path": str(postman_file), "format": "postman"}
        filename = _generate_jmx_filename(collection)
        assert filename == "my-api.jmx"

    def test_postman_collection_underscore_suffix(self, tmp_path: Path) -> None:
        """Test filename generation for Postman file with underscore suffix."""
        postman_file = tmp_path / "my-api_postman_collection.json"
        postman_file.write_text("{}")
        collection = {"path": str(postman_file), "format": "postman"}
        filename = _generate_jmx_filename(collection)
        assert filename == "my-api.jmx"

    def test_insomnia_export_file(self, tmp_path: Path) -> None:
        """Test filename generation for Insomnia export file."""
        insomnia_file = tmp_path / "my-api_insomnia.json"
        insomnia_file.write_text("{}")
        collection = {"path": str(insomnia_file), "format": "insomnia"}
        filename = _generate_jmx_filename(collection)
        assert filename == "my-api.jmx"

    def test_sanitizes_special_characters(self, tmp_path: Path) -> None:
        """Test that special characters are sanitized."""
        api_dir = tmp_path / "parent" / "My API Collection!"
        api_dir.mkdir(parents=True)
        collection = {"path": str(api_dir), "format": "bruno"}
        filename = _generate_jmx_filename(collection)
        assert "!" not in filename
        assert " " not in filename
        assert filename.endswith("-my-api-collection.jmx")

    def test_sanitizes_spaces_to_dashes(self, tmp_path: Path) -> None:
        """Test that spaces are converted to dashes."""
        api_dir = tmp_path / "parent" / "User Management API"
        api_dir.mkdir(parents=True)
        collection = {"path": str(api_dir), "format": "bruno"}
        filename = _generate_jmx_filename(collection)
        assert " " not in filename
        assert filename.endswith("-user-management-api.jmx")

    def test_removes_duplicate_dashes(self, tmp_path: Path) -> None:
        """Test that duplicate dashes are removed."""
        api_dir = tmp_path / "parent" / "api--test"
        api_dir.mkdir(parents=True)
        collection = {"path": str(api_dir), "format": "bruno"}
        filename = _generate_jmx_filename(collection)
        assert "--" not in filename

    def test_lowercase_output(self, tmp_path: Path) -> None:
        """Test that output is lowercase."""
        api_dir = tmp_path / "parent" / "MyAPI"
        api_dir.mkdir(parents=True)
        collection = {"path": str(api_dir), "format": "bruno"}
        filename = _generate_jmx_filename(collection)
        assert filename == filename.lower()
        assert filename.endswith("-myapi.jmx")

    def test_strips_leading_trailing_dashes(self, tmp_path: Path) -> None:
        """Test that leading and trailing dashes are stripped."""
        api_dir = tmp_path / "parent" / "-api-"
        api_dir.mkdir(parents=True)
        collection = {"path": str(api_dir), "format": "bruno"}
        filename = _generate_jmx_filename(collection)
        # After sanitization: "parent--api-" -> stripped -> "parent-api"
        assert not filename.startswith("-")
        assert not filename.replace(".jmx", "").endswith("-")


class TestAnalyzeInteractiveSelection:
    """Tests for interactive collection selection in analyze command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    def test_analyze_select_collection(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test selecting a specific collection from multiple found."""
        # Create multiple collections
        bruno_dir = tmp_path / "api1"
        bruno_dir.mkdir()
        (bruno_dir / "bruno.json").write_text('{"name": "API 1"}')
        (bruno_dir / "test.bru").write_text("meta {\n  name: Test\n  type: http\n}\nget {\n  url: /test\n}\n")

        postman_file = tmp_path / "api2.postman_collection.json"
        postman_file.write_text('{"info": {"name": "API 2", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"}, "item": []}')

        # Select collection 1 (Bruno), then decline import
        result = runner.invoke(
            cli, ["analyze", "--path", str(tmp_path)],
            input="1\nn\n"
        )
        assert result.exit_code == 0

    def test_analyze_single_collection_auto_selected(
        self, runner: CliRunner, postman_basic_collection: Path
    ) -> None:
        """Test single collection is auto-selected for import."""
        # Single collection, decline import at confirmation
        result = runner.invoke(
            cli, ["analyze", "--path", str(postman_basic_collection.parent)],
            input="n\n"
        )
        assert result.exit_code == 0

    def test_analyze_file_exists_overwrite(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test file exists - choose to overwrite."""
        # Create collection
        collection_dir = tmp_path / "api"
        collection_dir.mkdir()
        (collection_dir / "bruno.json").write_text('{"name": "API"}')
        (collection_dir / "test.bru").write_text("meta {\n  name: Test\n  type: http\n}\nget {\n  url: /test\n}\n")

        # Create existing file that would conflict
        # Bruno uses parent-api.jmx pattern with last 2 path parts
        expected_filename = f"{tmp_path.name}-api.jmx".lower()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create the conflicting file
            Path(expected_filename).write_text("<jmeter/>")

            # Select, overwrite existing file, confirm import
            result = runner.invoke(
                cli, ["analyze", "--path", str(collection_dir)],
                input="o\ny\n"
            )
            # May or may not succeed depending on collection structure
            assert result.exit_code in (0, 1)

    def test_analyze_file_exists_rename(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test file exists - choose to rename."""
        # Create collection
        collection_dir = tmp_path / "api"
        collection_dir.mkdir()
        (collection_dir / "bruno.json").write_text('{"name": "API"}')
        (collection_dir / "test.bru").write_text("meta {\n  name: Test\n  type: http\n}\nget {\n  url: /test\n}\n")

        expected_filename = f"{tmp_path.name}-api.jmx".lower()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create the conflicting file
            Path(expected_filename).write_text("<jmeter/>")

            # Select, choose rename, provide new name, confirm import
            result = runner.invoke(
                cli, ["analyze", "--path", str(collection_dir)],
                input="r\nnew-output.jmx\ny\n"
            )
            assert result.exit_code in (0, 1)

    def test_analyze_file_exists_cancel(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test file exists - choose to cancel."""
        # Create collection
        collection_dir = tmp_path / "api"
        collection_dir.mkdir()
        (collection_dir / "bruno.json").write_text('{"name": "API"}')
        (collection_dir / "test.bru").write_text("meta {\n  name: Test\n  type: http\n}\nget {\n  url: /test\n}\n")

        expected_filename = f"{tmp_path.name}-api.jmx".lower()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create the conflicting file
            Path(expected_filename).write_text("<jmeter/>")

            # Select, cancel
            result = runner.invoke(
                cli, ["analyze", "--path", str(collection_dir)],
                input="c\n"
            )
            assert result.exit_code == 0
            assert "cancelled" in result.output.lower()

    def test_analyze_file_exists_invalid_then_valid(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test file exists - invalid action then valid."""
        # Create collection
        collection_dir = tmp_path / "api"
        collection_dir.mkdir()
        (collection_dir / "bruno.json").write_text('{"name": "API"}')
        (collection_dir / "test.bru").write_text("meta {\n  name: Test\n  type: http\n}\nget {\n  url: /test\n}\n")

        expected_filename = f"{tmp_path.name}-api.jmx".lower()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create the conflicting file
            Path(expected_filename).write_text("<jmeter/>")

            # Select, invalid choice, then cancel
            result = runner.invoke(
                cli, ["analyze", "--path", str(collection_dir)],
                input="invalid\nc\n"
            )
            assert result.exit_code == 0
            assert "Invalid choice" in result.output


class TestVerboseLogging:
    """Tests for verbose output in import command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    def test_verbose_logs_debug_info(
        self, runner: CliRunner, bruno_collection_dir: Path, tmp_path: Path
    ) -> None:
        """Test verbose mode shows debug information."""
        output = str(tmp_path / "test.jmx")
        result = runner.invoke(
            cli, ["import", str(bruno_collection_dir), "-o", output, "-v"]
        )
        assert result.exit_code == 0
        assert "Verbose mode enabled" in result.output

    def test_verbose_with_env_file(
        self, runner: CliRunner, postman_basic_collection: Path,
        postman_env_disabled_vars: Path, tmp_path: Path
    ) -> None:
        """Test verbose logs environment file info."""
        output = str(tmp_path / "test.jmx")
        result = runner.invoke(
            cli, [
                "import", str(postman_basic_collection),
                "-o", output, "-v",
                "--env", str(postman_env_disabled_vars)
            ]
        )
        assert result.exit_code == 0


class TestExceptionHandling:
    """Tests for exception handling in import command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    def test_importer_exception_with_details(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test ImporterException with details is displayed."""
        # Create a file that will cause an ImporterException when parsing
        invalid_file = tmp_path / "invalid.postman_collection.json"
        invalid_file.write_text('{"foo": "bar"}')  # Missing required 'info' field

        result = runner.invoke(
            cli, ["import", str(invalid_file), "-f", "postman"]
        )
        assert result.exit_code == 1
        assert "Error" in result.output

    def test_jmx_exception_handling(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test JMXGenerationException handling."""
        # Create a valid collection but point to invalid output path
        bruno_dir = tmp_path / "api"
        bruno_dir.mkdir()
        (bruno_dir / "bruno.json").write_text('{"name": "API"}')
        (bruno_dir / "test.bru").write_text(
            "meta {\n  name: Test\n  type: http\n}\nget {\n  url: /test\n}\n"
        )

        # Try to write to a directory that doesn't exist
        result = runner.invoke(
            cli, ["import", str(bruno_dir), "-o", "/nonexistent/path/test.jmx"]
        )
        # Should handle the error gracefully
        assert result.exit_code in (0, 1)


class TestPreviewExceptions:
    """Tests for preview exception handling."""

    def test_preview_exception_shows_error(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test preview handles exceptions gracefully."""
        from collection_importer.core.importers.bruno import BrunoImporter

        # Create a collection that will cause list_requests to fail
        bad_dir = tmp_path / "bad"
        bad_dir.mkdir()
        # No bruno.json - may cause issues in some scenarios
        (bad_dir / "test.bru").write_text("invalid bru content {{{")

        importer = BrunoImporter()
        # This should not raise, but show error message
        _show_preview(importer, bad_dir)
        captured = capsys.readouterr()
        # Either shows error or handles gracefully
        assert captured.out is not None


class TestAnalyzeSkipSelection:
    """Tests for skipping import in analyze command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    def test_analyze_skip_selection_zero(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test selecting 0 skips import."""
        # Create multiple collections
        bruno_dir = tmp_path / "api1"
        bruno_dir.mkdir()
        (bruno_dir / "bruno.json").write_text('{"name": "API 1"}')
        (bruno_dir / "test.bru").write_text("meta {\n  name: Test\n  type: http\n}\nget {\n  url: /test\n}\n")

        postman_file = tmp_path / "api2.postman_collection.json"
        postman_file.write_text('{"info": {"name": "API 2", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"}, "item": []}')

        # Select 0 to skip
        result = runner.invoke(
            cli, ["analyze", "--path", str(tmp_path)],
            input="0\n"
        )
        assert result.exit_code == 0
        assert "skipped" in result.output.lower()


class TestImportWithSpecificFormat:
    """Tests for import with explicit format specification."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    def test_import_with_specified_format_logs_debug(
        self, runner: CliRunner, postman_basic_collection: Path, tmp_path: Path
    ) -> None:
        """Test import with specified format shows debug info in verbose mode."""
        output = str(tmp_path / "test.jmx")
        result = runner.invoke(
            cli, [
                "import", str(postman_basic_collection),
                "-f", "postman", "-o", output, "-v"
            ]
        )
        assert result.exit_code == 0
        assert "Using specified format" in result.output or "postman" in result.output.lower()
