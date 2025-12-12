"""Unit tests for MCP Server.

Tests cover:
- Tool listing: list_tools()
- Tool execution: call_tool()
- analyze_project_for_collections tool
- import_collection_to_jmx tool
- list_collection_requests tool
"""

from pathlib import Path

import pytest

from collection_importer.mcp_server import (
    TOOLS,
    _analyze_project,
    _import_collection,
    _list_requests,
    call_tool,
    list_tools,
)


class TestListTools:
    """Tests for list_tools function."""

    @pytest.mark.asyncio
    async def test_list_tools_returns_all_tools(self) -> None:
        """Test list_tools returns all defined tools."""
        tools = await list_tools()
        assert len(tools) == 3

    @pytest.mark.asyncio
    async def test_list_tools_contains_analyze(self) -> None:
        """Test list_tools includes analyze tool."""
        tools = await list_tools()
        names = [t.name for t in tools]
        assert "analyze_project_for_collections" in names

    @pytest.mark.asyncio
    async def test_list_tools_contains_import(self) -> None:
        """Test list_tools includes import tool."""
        tools = await list_tools()
        names = [t.name for t in tools]
        assert "import_collection_to_jmx" in names

    @pytest.mark.asyncio
    async def test_list_tools_contains_list_requests(self) -> None:
        """Test list_tools includes list_requests tool."""
        tools = await list_tools()
        names = [t.name for t in tools]
        assert "list_collection_requests" in names


class TestCallTool:
    """Tests for call_tool function."""

    @pytest.mark.asyncio
    async def test_call_unknown_tool(self) -> None:
        """Test calling unknown tool returns error."""
        result = await call_tool("unknown_tool", {})
        assert len(result) == 1
        assert "Unknown tool" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_routes_to_analyze(
        self, bruno_collection_dir: Path
    ) -> None:
        """Test call_tool routes analyze correctly."""
        result = await call_tool(
            "analyze_project_for_collections",
            {"project_path": str(bruno_collection_dir)},
        )
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_call_tool_routes_to_import(
        self, bruno_collection_dir: Path, tmp_path: Path
    ) -> None:
        """Test call_tool routes import correctly."""
        output = str(tmp_path / "test.jmx")
        result = await call_tool(
            "import_collection_to_jmx",
            {"collection_path": str(bruno_collection_dir), "output_path": output},
        )
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_call_tool_routes_to_list_requests(
        self, bruno_collection_dir: Path
    ) -> None:
        """Test call_tool routes list_requests correctly."""
        result = await call_tool(
            "list_collection_requests",
            {"collection_path": str(bruno_collection_dir)},
        )
        assert len(result) > 0


class TestAnalyzeProject:
    """Tests for _analyze_project function."""

    @pytest.mark.asyncio
    async def test_analyze_default_path(self) -> None:
        """Test analyze with fixtures collections directory."""
        fixtures_path = Path(__file__).parent / "fixtures" / "collections"
        result = await _analyze_project({"project_path": str(fixtures_path)})
        assert len(result) == 1
        # Should find Bruno, Postman, and Insomnia collections
        output = result[0].text.upper()
        assert "BRUNO" in output
        assert "POSTMAN" in output
        assert "INSOMNIA" in output

    @pytest.mark.asyncio
    async def test_analyze_finds_bruno_collection(
        self, bruno_collection_dir: Path
    ) -> None:
        """Test analyze finds Bruno collection."""
        result = await _analyze_project({"project_path": str(bruno_collection_dir)})
        assert "BRUNO" in result[0].text.upper()

    @pytest.mark.asyncio
    async def test_analyze_nonexistent_path(self) -> None:
        """Test analyze with non-existent path returns message."""
        result = await _analyze_project({"project_path": "/nonexistent"})
        # Should return error or no collections found
        assert "Error" in result[0].text or "No API collections" in result[0].text

    @pytest.mark.asyncio
    async def test_analyze_empty_directory(self, tmp_path: Path) -> None:
        """Test analyze with empty directory returns no collections."""
        result = await _analyze_project({"project_path": str(tmp_path)})
        assert "No API collections found" in result[0].text


class TestImportCollection:
    """Tests for _import_collection function."""

    @pytest.mark.asyncio
    async def test_import_bruno_collection(
        self, bruno_collection_dir: Path, tmp_path: Path
    ) -> None:
        """Test importing Bruno collection."""
        output = str(tmp_path / "test.jmx")
        result = await _import_collection(
            {
                "collection_path": str(bruno_collection_dir),
                "output_path": output,
            }
        )
        assert "JMX file generated successfully" in result[0].text
        assert Path(output).exists()

    @pytest.mark.asyncio
    async def test_import_postman_collection(
        self, postman_collection_file: Path, tmp_path: Path
    ) -> None:
        """Test importing Postman collection."""
        output = str(tmp_path / "test.jmx")
        result = await _import_collection(
            {
                "collection_path": str(postman_collection_file),
                "output_path": output,
            }
        )
        assert "JMX file generated successfully" in result[0].text

    @pytest.mark.asyncio
    async def test_import_with_format(
        self, postman_collection_file: Path, tmp_path: Path
    ) -> None:
        """Test import with explicit format."""
        output = str(tmp_path / "test.jmx")
        result = await _import_collection(
            {
                "collection_path": str(postman_collection_file),
                "output_path": output,
                "format": "postman",
            }
        )
        assert "JMX file generated successfully" in result[0].text

    @pytest.mark.asyncio
    async def test_import_with_thread_params(
        self, bruno_collection_dir: Path, tmp_path: Path
    ) -> None:
        """Test import with thread parameters."""
        output = str(tmp_path / "test.jmx")
        result = await _import_collection(
            {
                "collection_path": str(bruno_collection_dir),
                "output_path": output,
                "threads": 50,
                "rampup": 10,
                "duration": 300,
            }
        )
        assert "Threads: 50" in result[0].text

    @pytest.mark.asyncio
    async def test_import_unknown_format(self, tmp_path: Path) -> None:
        """Test import with unknown format returns error."""
        unknown_file = tmp_path / "unknown.txt"
        unknown_file.write_text("not a collection")
        result = await _import_collection(
            {"collection_path": str(unknown_file)}
        )
        assert "Could not detect" in result[0].text

    @pytest.mark.asyncio
    async def test_import_unsupported_format(
        self, postman_collection_file: Path, tmp_path: Path
    ) -> None:
        """Test import with unsupported format returns error."""
        result = await _import_collection(
            {
                "collection_path": str(postman_collection_file),
                "format": "unsupported",
            }
        )
        assert "not supported" in result[0].text


class TestListRequests:
    """Tests for _list_requests function."""

    @pytest.mark.asyncio
    async def test_list_bruno_requests(
        self, bruno_collection_dir: Path
    ) -> None:
        """Test listing Bruno collection requests."""
        result = await _list_requests(
            {"collection_path": str(bruno_collection_dir)}
        )
        assert "Requests in" in result[0].text
        assert "Total:" in result[0].text

    @pytest.mark.asyncio
    async def test_list_postman_requests(
        self, postman_collection_file: Path
    ) -> None:
        """Test listing Postman collection requests."""
        result = await _list_requests(
            {"collection_path": str(postman_collection_file)}
        )
        assert "Requests in" in result[0].text

    @pytest.mark.asyncio
    async def test_list_insomnia_requests(
        self, insomnia_collection_file: Path
    ) -> None:
        """Test listing Insomnia collection requests."""
        result = await _list_requests(
            {"collection_path": str(insomnia_collection_file)}
        )
        assert "Requests in" in result[0].text

    @pytest.mark.asyncio
    async def test_list_unknown_format(self, tmp_path: Path) -> None:
        """Test listing with unknown format returns error."""
        unknown_file = tmp_path / "unknown.txt"
        unknown_file.write_text("not a collection")
        result = await _list_requests({"collection_path": str(unknown_file)})
        assert "Could not detect" in result[0].text

    @pytest.mark.asyncio
    async def test_list_empty_collection(self, tmp_path: Path) -> None:
        """Test listing empty collection shows no requests."""
        # Create minimal bruno.json to be detected
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        (empty_dir / "bruno.json").write_text('{"name": "Empty"}')
        result = await _list_requests({"collection_path": str(empty_dir)})
        assert "No requests found" in result[0].text


class TestToolDefinitions:
    """Tests for tool definitions."""

    def test_tools_have_names(self) -> None:
        """Test all tools have names."""
        for tool in TOOLS:
            assert tool.name is not None
            assert len(tool.name) > 0

    def test_tools_have_descriptions(self) -> None:
        """Test all tools have descriptions."""
        for tool in TOOLS:
            assert tool.description is not None
            assert len(tool.description) > 0

    def test_tools_have_input_schemas(self) -> None:
        """Test all tools have input schemas."""
        for tool in TOOLS:
            assert tool.inputSchema is not None
            assert "type" in tool.inputSchema

    def test_analyze_tool_schema(self) -> None:
        """Test analyze tool has correct schema."""
        analyze_tool = next(t for t in TOOLS if t.name == "analyze_project_for_collections")
        assert "project_path" in analyze_tool.inputSchema.get("properties", {})

    def test_import_tool_schema(self) -> None:
        """Test import tool has correct schema."""
        import_tool = next(t for t in TOOLS if t.name == "import_collection_to_jmx")
        props = import_tool.inputSchema.get("properties", {})
        assert "collection_path" in props
        assert "output_path" in props
        assert "threads" in props
        assert "rampup" in props

    def test_list_requests_tool_schema(self) -> None:
        """Test list_requests tool has correct schema."""
        list_tool = next(t for t in TOOLS if t.name == "list_collection_requests")
        props = list_tool.inputSchema.get("properties", {})
        assert "collection_path" in props


class TestEdgeCases:
    """Edge case tests for MCP server."""

    @pytest.mark.asyncio
    async def test_import_with_base_url_override(
        self, bruno_collection_dir: Path, tmp_path: Path
    ) -> None:
        """Test import with base URL override."""
        output = str(tmp_path / "test.jmx")
        result = await _import_collection(
            {
                "collection_path": str(bruno_collection_dir),
                "output_path": output,
                "base_url": "https://api.example.com",
            }
        )
        assert "JMX file generated successfully" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_handles_exceptions(self) -> None:
        """Test call_tool handles exceptions gracefully."""
        # Call with invalid arguments that will cause an error
        result = await call_tool(
            "import_collection_to_jmx",
            {"collection_path": None},
        )
        assert "Error" in result[0].text

    @pytest.mark.asyncio
    async def test_import_default_output_path(
        self, bruno_collection_dir: Path, tmp_path: Path
    ) -> None:
        """Test import uses default output path."""
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = await _import_collection(
                {"collection_path": str(bruno_collection_dir)}
            )
            assert "JMX file generated successfully" in result[0].text
            assert (tmp_path / "test.jmx").exists()
        finally:
            os.chdir(original_cwd)
