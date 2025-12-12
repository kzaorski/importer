"""MCP Server for Collection Importer.

Provides tools for AI assistant integration.
"""

import asyncio
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from collection_importer.core.collection_analyzer import CollectionAnalyzer
from collection_importer.core.importer_factory import get_importer, is_supported_format
from collection_importer.core.jmx_generator import JMXGenerator
from collection_importer.exceptions import CollectionImporterException

# Initialize MCP server
server = Server("collection-importer")

# Tool definitions
TOOLS = [
    Tool(
        name="analyze_project_for_collections",
        description="Discover API collections in project directory. "
        "Finds Bruno, Postman, and Insomnia collections.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_path": {
                    "type": "string",
                    "description": "Path to project directory (default: current directory)",
                    "default": ".",
                },
            },
        },
    ),
    Tool(
        name="import_collection_to_jmx",
        description="Import API collection and generate JMeter JMX test plan. "
        "Supports Bruno, Postman, and Insomnia formats.",
        inputSchema={
            "type": "object",
            "properties": {
                "collection_path": {
                    "type": "string",
                    "description": "Path to collection file or folder",
                },
                "output_path": {
                    "type": "string",
                    "description": "Output JMX file path (default: test.jmx)",
                    "default": "test.jmx",
                },
                "format": {
                    "type": "string",
                    "description": "Collection format: bruno, postman, insomnia (auto-detected if not specified)",
                    "enum": ["bruno", "postman", "insomnia"],
                },
                "base_url": {
                    "type": "string",
                    "description": "Override base URL",
                },
                "threads": {
                    "type": "integer",
                    "description": "Number of virtual users (default: 1)",
                    "default": 1,
                    "minimum": 1,
                },
                "rampup": {
                    "type": "integer",
                    "description": "Ramp-up period in seconds (default: 0)",
                    "default": 0,
                    "minimum": 0,
                },
                "duration": {
                    "type": "integer",
                    "description": "Test duration in seconds",
                    "minimum": 1,
                },
            },
            "required": ["collection_path"],
        },
    ),
    Tool(
        name="list_collection_requests",
        description="Preview requests in a collection without generating JMX. "
        "Returns list of request names, methods, and paths.",
        inputSchema={
            "type": "object",
            "properties": {
                "collection_path": {
                    "type": "string",
                    "description": "Path to collection file or folder",
                },
            },
            "required": ["collection_path"],
        },
    ),
]


@server.list_tools()  # type: ignore[misc, no-untyped-call]
async def list_tools() -> list[Tool]:
    """Return list of available tools."""
    return TOOLS


@server.call_tool()  # type: ignore[misc]
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute a tool and return results."""
    try:
        if name == "analyze_project_for_collections":
            return await _analyze_project(arguments)
        elif name == "import_collection_to_jmx":
            return await _import_collection(arguments)
        elif name == "list_collection_requests":
            return await _list_requests(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def _analyze_project(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle analyze_project_for_collections tool."""
    project_path = arguments.get("project_path", ".")

    analyzer = CollectionAnalyzer()
    result = analyzer.analyze_project(project_path)

    if result.get("error"):
        return [TextContent(type="text", text=f"Error: {result['error']}")]

    if not result["collections_found"]:
        return [
            TextContent(
                type="text",
                text="No API collections found.\n\n"
                "Supported formats:\n"
                "- Bruno: folder with bruno.json or *.bru files\n"
                "- Postman: *.postman_collection.json\n"
                "- Insomnia: insomnia*.json",
            )
        ]

    # Format results
    lines = ["Found collections:\n"]
    for coll in result["collections"]:
        lines.append(
            f"- {coll['format'].upper()}: {coll['path']} ({coll['requests_count']} requests)"
        )

    if result["recommended_collection"]:
        lines.append(f"\nRecommended: {result['recommended_collection']}")

    return [TextContent(type="text", text="\n".join(lines))]


async def _import_collection(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle import_collection_to_jmx tool."""
    collection_path = arguments.get("collection_path")
    if not collection_path or not isinstance(collection_path, str):
        return [TextContent(type="text", text="Error: collection_path is required")]

    output_path = arguments.get("output_path", "test.jmx")
    format_name = arguments.get("format")
    base_url = arguments.get("base_url")
    threads = arguments.get("threads", 1)
    rampup = arguments.get("rampup", 0)
    duration = arguments.get("duration")

    path = Path(collection_path)

    # Detect format if not specified
    if not format_name:
        analyzer = CollectionAnalyzer()
        format_name = analyzer.detect_format(collection_path)

        if format_name == "unknown":
            return [
                TextContent(
                    type="text",
                    text=f"Could not detect collection format for {path.name}. "
                    "Please specify format: bruno, postman, or insomnia",
                )
            ]

    # Get importer
    if not is_supported_format(format_name):
        return [
            TextContent(
                type="text",
                text=f"Format '{format_name}' not supported. "
                "Supported formats: bruno, postman, insomnia",
            )
        ]
    importer = get_importer(format_name)

    # Import collection
    try:
        collection = importer.import_collection(
            path=path,
            base_url=base_url,
        )

        # Generate JMX
        generator = JMXGenerator()
        result = generator.generate(
            collection=collection,
            output_path=output_path,
            base_url=base_url or collection.metadata.base_url,
            threads=threads,
            rampup=rampup,
            duration=duration,
        )

        return [
            TextContent(
                type="text",
                text=f"JMX file generated successfully!\n\n"
                f"Output: {result['jmx_path']}\n"
                f"Samplers: {result['samplers_created']}\n"
                f"Threads: {result['threads']}\n"
                f"Ramp-up: {result['rampup']}s\n"
                f"Duration: {result['duration'] or 'N/A (loop count)'}",
            )
        ]

    except CollectionImporterException as e:
        return [TextContent(type="text", text=f"Error: {e.message}")]


async def _list_requests(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle list_collection_requests tool."""
    collection_path = arguments.get("collection_path")
    if not collection_path or not isinstance(collection_path, str):
        return [TextContent(type="text", text="Error: collection_path is required")]

    path = Path(collection_path)

    # Detect format
    analyzer = CollectionAnalyzer()
    format_name = analyzer.detect_format(collection_path)

    if format_name == "unknown":
        return [
            TextContent(
                type="text",
                text=f"Could not detect collection format for {path.name}",
            )
        ]

    # Get importer
    if not is_supported_format(format_name):
        return [
            TextContent(
                type="text",
                text=f"Format '{format_name}' not supported. "
                "Supported formats: bruno, postman, insomnia",
            )
        ]
    importer = get_importer(format_name)

    try:
        requests = importer.list_requests(path)

        if not requests:
            return [TextContent(type="text", text="No requests found in collection.")]

        lines = [f"Requests in {path.name}:\n"]
        for idx, req in enumerate(requests, 1):
            lines.append(f"{idx}. {req['method']} {req['path']} - {req['name']}")

        lines.append(f"\nTotal: {len(requests)} requests")

        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


def run_server() -> None:
    """Run the MCP server."""
    asyncio.run(_run_server())


async def _run_server() -> None:
    """Async server runner."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
