"""CLI interface for Collection Importer.

Provides commands for analyzing, importing, and validating collections.
"""

import logging
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

from collection_importer import __version__
from collection_importer.core.collection_analyzer import CollectionAnalyzer
from collection_importer.core.importer_factory import get_importer
from collection_importer.core.importers.base import BaseImporter
from collection_importer.core.jmx_generator import JMXGenerator
from collection_importer.exceptions import (
    ImporterException,
    JMXGenerationException,
)

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="collection-importer")
def cli() -> None:
    """Collection Importer - Convert API collections to JMeter JMX files.

    Supports Bruno, Postman, and Insomnia collection formats.
    """
    pass


@cli.command()
@click.option(
    "--path",
    "-p",
    default=".",
    help="Project path to analyze (default: current directory)",
)
def analyze(path: str) -> None:
    """Discover API collections in project directory.

    Scans for Bruno folders, Postman JSON, and Insomnia JSON files.
    """
    console.print(f"\n[bold]Analyzing project:[/bold] {Path(path).resolve()}\n")

    analyzer = CollectionAnalyzer()
    result = analyzer.analyze_project(path)

    if result.get("error"):
        console.print(f"[red]Error:[/red] {result['error']}")
        raise SystemExit(1)

    if not result["collections_found"]:
        console.print("[yellow]No API collections found.[/yellow]")
        console.print("\nSupported formats:")
        console.print("  - Bruno: folder with bruno.json or *.bru files")
        console.print("  - Postman: *.postman_collection.json")
        console.print("  - Insomnia: insomnia*.json")
        return

    # Display found collections
    collections = result["collections"]
    table = Table(title="Found Collections")
    table.add_column("#", style="dim", width=3)
    table.add_column("Format", style="cyan")
    table.add_column("Path", style="green")
    table.add_column("Requests", justify="right")

    for i, coll in enumerate(collections, 1):
        table.add_row(
            str(i),
            coll["format"].upper(),
            coll["path"],
            str(coll["requests_count"]) if coll["requests_count"] > 0 else "-",
        )

    console.print(table)

    # Ask user which collection to import
    if len(collections) == 1:
        selected = collections[0]
    else:
        selection = click.prompt(
            "\nSelect collection to import (0 to skip)",
            type=click.IntRange(0, len(collections)),
            default=1,
        )
        if selection == 0:
            console.print("[dim]Import skipped.[/dim]")
            return
        selected = collections[selection - 1]

    # Generate descriptive filename
    output_file = _generate_jmx_filename(selected)

    # Handle existing file
    while Path(output_file).exists():
        console.print(f"\n[yellow]File '{output_file}' already exists.[/yellow]")

        while True:
            action = click.prompt(
                "Choose action (Overwrite, Rename, Cancel)",
                default="Rename",
            ).lower().strip()

            action_map = {
                "o": "overwrite", "overwrite": "overwrite",
                "r": "rename", "rename": "rename",
                "c": "cancel", "cancel": "cancel",
            }

            if action in action_map:
                action = action_map[action]
                break

            console.print("[red]Invalid choice. Use: O, R, C[/red]")

        if action == "cancel":
            console.print("[dim]Import cancelled.[/dim]")
            return
        elif action == "overwrite":
            break
        else:  # rename
            new_name = click.prompt("Enter new filename", default=output_file)
            if not new_name.endswith(".jmx"):
                new_name += ".jmx"
            output_file = new_name

    # Confirm and import
    if click.confirm(f"\nImport '{selected['name']}' to {output_file}?", default=True):
        ctx = click.Context(import_collection)
        ctx.invoke(
            import_collection,
            collection_path=selected["path"],
            output=output_file,
            format_name=None,
            env=None,
            base_url=None,
            threads=1,
            rampup=0,
            duration=None,
            preview=False,
            verbose=False,
        )


@cli.command("import")
@click.argument("collection_path", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    default="test.jmx",
    help="Output JMX file path (default: test.jmx)",
)
@click.option(
    "--format",
    "-f",
    "format_name",
    type=click.Choice(["bruno", "postman", "insomnia"]),
    help="Force collection format (auto-detected if not specified)",
)
@click.option(
    "--env",
    "-e",
    type=click.Path(exists=True),
    help="Environment file path",
)
@click.option(
    "--base-url",
    help="Override base URL",
)
@click.option(
    "--threads",
    default=1,
    type=int,
    help="Number of virtual users (default: 1)",
)
@click.option(
    "--rampup",
    default=0,
    type=int,
    help="Ramp-up period in seconds (default: 0)",
)
@click.option(
    "--duration",
    type=int,
    help="Test duration in seconds (uses loop count if not specified)",
)
@click.option(
    "--preview",
    is_flag=True,
    help="Preview requests without generating JMX",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output with debug information",
)
def import_collection(
    collection_path: str,
    output: str,
    format_name: str | None,
    env: str | None,
    base_url: str | None,
    threads: int,
    rampup: int,
    duration: int | None,
    preview: bool,
    verbose: bool,
) -> None:
    """Import collection and generate JMeter JMX file.

    Auto-detects collection format or use --format to specify.

    Examples:

        collection-importer import ./my-collection

        collection-importer import collection.json --format postman

        collection-importer import ./api -o performance-test.jmx --threads 50
    """
    # Configure logging for verbose mode
    if verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(message)s",
            handlers=[
                RichHandler(
                    console=console,
                    show_time=False,
                    show_path=True,
                    rich_tracebacks=True,
                )
            ],
        )
        console.print("[dim]Verbose mode enabled[/dim]\n")

    logger = logging.getLogger(__name__)
    path = Path(collection_path)

    logger.debug("Starting import process")
    logger.debug(f"Collection path: {path.resolve()}")
    logger.debug(f"Output path: {output}")
    logger.debug(f"Thread configuration: threads={threads}, rampup={rampup}, duration={duration}")

    # Detect format if not specified
    if not format_name:
        logger.debug("Auto-detecting collection format...")
        analyzer = CollectionAnalyzer()
        format_name = analyzer.detect_format(collection_path)
        logger.debug(f"Detected format: {format_name}")

        if format_name == "unknown":
            console.print(
                f"[red]Error:[/red] Could not detect collection format for {path.name}"
            )
            console.print("Use --format to specify: bruno, postman, or insomnia")
            raise SystemExit(1)
    else:
        logger.debug(f"Using specified format: {format_name}")

    console.print(f"\n[bold]Format:[/bold] {format_name.upper()}")
    console.print(f"[bold]Collection:[/bold] {path.resolve()}")

    # Get appropriate importer
    logger.debug(f"Initializing {format_name} importer...")
    importer = get_importer(format_name)

    # Preview mode
    if preview:
        logger.debug("Preview mode enabled, showing requests...")
        _show_preview(importer, path)
        return

    # Import collection
    try:
        env_path = Path(env) if env else None
        logger.debug(f"Environment file: {env_path or 'None'}")
        logger.debug(f"Base URL override: {base_url or 'None'}")
        logger.debug("Importing collection...")

        collection = importer.import_collection(
            path=path,
            env_path=env_path,
            base_url=base_url,
        )

        logger.debug(f"Successfully imported {collection.request_count} requests")
        logger.debug(f"Collection name: {collection.metadata.name}")
        logger.debug(f"Collection base URL: {collection.metadata.base_url or 'None'}")

        if collection.metadata.variables:
            logger.debug(f"Variables found: {list(collection.metadata.variables.keys())}")

        console.print(f"[bold]Requests:[/bold] {collection.request_count}")

        # Log request details in verbose mode
        for req in collection.requests:
            logger.debug(f"  [{req.method}] {req.path} - {req.name}")
            if req.pre_script:
                logger.debug(f"    Pre-script: {len(req.pre_script)} chars")
            if req.post_script:
                logger.debug(f"    Post-script: {len(req.post_script)} chars")

        # Generate JMX
        logger.debug("Initializing JMX generator...")
        generator = JMXGenerator()

        effective_base_url = base_url or collection.metadata.base_url
        logger.debug(f"Effective base URL: {effective_base_url or 'http://localhost:8080 (default)'}")
        logger.debug("Generating JMX file...")

        result = generator.generate(
            collection=collection,
            output_path=output,
            base_url=effective_base_url,
            threads=threads,
            rampup=rampup,
            duration=duration,
        )

        logger.debug(f"JMX generation complete: {result['samplers_created']} samplers created")

        if result["success"]:
            output_path = Path(result['jmx_path']).resolve()
            console.print(
                Panel(
                    f"[green]JMX file generated successfully![/green]\n\n"
                    f"Output: {output_path}\n"
                    f"Samplers: {result['samplers_created']}\n"
                    f"Threads: {result['threads']}\n"
                    f"Ramp-up: {result['rampup']}s\n"
                    f"Duration: {result['duration'] or 'N/A (loop count)'}",
                    title="Generation Complete",
                )
            )

    except ImporterException as e:
        console.print(f"[red]Import Error:[/red] {e.message}")
        if e.details:
            console.print(f"[dim]{e.details}[/dim]")
        raise SystemExit(1) from None

    except JMXGenerationException as e:
        console.print(f"[red]Generation Error:[/red] {e.message}")
        if e.details:
            console.print(f"[dim]{e.details}[/dim]")
        raise SystemExit(1) from None


@cli.command()
def mcp() -> None:
    """Start MCP Server for AI assistant integration."""
    from collection_importer.mcp_server import run_server

    console.print("[bold]Starting MCP Server...[/bold]")
    run_server()


def _generate_jmx_filename(collection: dict[str, Any]) -> str:
    """Generate descriptive JMX filename from collection info.

    Args:
        collection: Collection info dict with path and format keys.

    Returns:
        Sanitized filename ending with .jmx
    """
    col_path = Path(collection["path"])

    if col_path.is_dir():
        # Bruno - use last 2 path segments for uniqueness
        parts = col_path.parts[-2:] if len(col_path.parts) > 1 else [col_path.name]
        base_name = "-".join(parts)
    else:
        # Postman/Insomnia - use filename stem without format suffixes
        base_name = col_path.stem
        for suffix in ["_postman_collection", ".postman_collection", "_insomnia"]:
            suffix_clean = suffix.replace(".", "")
            if base_name.lower().endswith(suffix_clean):
                base_name = base_name[: -len(suffix_clean)]
                break

    # Sanitize for filesystem
    safe_name = "".join(c if c.isalnum() or c in "-_" else "-" for c in base_name)
    safe_name = safe_name.strip("-").lower()
    while "--" in safe_name:
        safe_name = safe_name.replace("--", "-")

    return f"{safe_name}.jmx"


def _show_preview(importer: BaseImporter, path: Path) -> None:
    """Show preview of collection requests."""
    try:
        requests = importer.list_requests(path)

        if not requests:
            console.print("[yellow]No requests found in collection.[/yellow]")
            return

        table = Table(title=f"Preview: {path.name}")
        table.add_column("#", style="dim", width=4)
        table.add_column("Method", style="cyan", width=8)
        table.add_column("Path", style="green")
        table.add_column("Name")

        for idx, req in enumerate(requests, 1):
            table.add_row(
                str(idx),
                req["method"],
                req["path"],
                req["name"],
            )

        console.print(table)
        console.print(f"\nTotal: {len(requests)} requests")

    except Exception as e:
        console.print(f"[red]Preview Error:[/red] {e}")


if __name__ == "__main__":
    cli()
