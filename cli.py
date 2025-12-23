"""
CLI tool for WebSocket handler management.

Provides commands for viewing registered handlers and generating new handlers
using the f-string code generator with AST validation.
"""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from app.api.ws.constants import PkgID
from app.routing import pkg_router
from generate_ws_handler import HandlerGenerator

# Initialize Typer app with help text
typer_app = typer.Typer(
    name="ws-cli",
    help="WebSocket Handler Management CLI - Manage and generate WebSocket handlers",
    add_completion=False,
)
console = Console()


@typer_app.command(name="ws-handlers")
def ws_handlers():
    """
    Display a table of all registered WebSocket handlers.

    Shows PkgID values, names, and their corresponding handler functions.
    Empty rows indicate PkgIDs without registered handlers.

    Example:
        python cli.py ws-handlers
        make ws-handlers
    """
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]Registered WebSocket Handlers[/bold cyan]",
            border_style="cyan"
        )
    )
    console.print()

    table = Table(
        "PkgID",
        "Handler Path",
        title="WebSocket Handlers Registry",
        show_lines=True,
    )

    missing_handlers = []

    for pkg_id in PkgID:
        handler = pkg_router.handlers_registry.get(pkg_id)

        if not handler:
            table.add_row(
                f"[dim]{pkg_id.value} - {pkg_id.name}[/dim]",
                "[red]No handler registered[/red]"
            )
            missing_handlers.append(pkg_id.name)
            continue

        handler_path = f"{handler.__module__}.[yellow]{handler.__name__}[/yellow]"
        table.add_row(
            f"[green]{pkg_id.value} - {pkg_id.name}[/green]",
            handler_path
        )

    console.print(table)
    console.print()

    # Show summary
    total = len(PkgID)
    registered = total - len(missing_handlers)
    console.print(
        f"[bold]Summary:[/bold] {registered}/{total} handlers registered"
    )

    if missing_handlers:
        console.print()
        console.print(
            "[yellow]⚠[/yellow] Missing handlers for:",
            ", ".join(f"[cyan]{h}[/cyan]" for h in missing_handlers[:5])
        )
        if len(missing_handlers) > 5:
            console.print(
                f"  ... and {len(missing_handlers) - 5} more"
            )
    console.print()


def _validate_pkg_id_input() -> str:
    """
    Prompt user to select an available PkgID by number.

    Shows a numbered list of unused PkgIDs and prompts for selection.
    Validates the input and returns the selected PkgID name.

    Returns:
        str: Valid PkgID name selected by user
    """
    # Get available PkgIDs
    all_pkg_ids = {pkg.name for pkg in PkgID}
    taken_pkg_ids = {pkg.name for pkg in pkg_router.handlers_registry.keys()}
    available_pkg_ids = sorted(all_pkg_ids - taken_pkg_ids)

    if not available_pkg_ids:
        console.print(
            "[red]✗ No available PkgIDs[/red] - All PkgIDs have handlers"
        )
        console.print()
        console.print(
            "[yellow]Hint:[/yellow] Add a new PkgID to the enum in "
            "[cyan]app/api/ws/constants.py[/cyan]"
        )
        console.print()
        raise typer.Exit(code=1)

    # Display available PkgIDs with numbers
    console.print("[bold cyan]Available PkgIDs (unused):[/bold cyan]")
    console.print()

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Number", style="cyan", justify="right")
    table.add_column("PkgID", style="yellow")

    for idx, pkg_id_name in enumerate(available_pkg_ids, start=1):
        table.add_row(f"{idx}.", pkg_id_name)

    console.print(table)
    console.print()

    # Prompt for selection
    while True:
        try:
            selection = console.input(
                f"[cyan]Select PkgID[/cyan] (1-{len(available_pkg_ids)}): "
            ).strip()

            # Allow direct PkgID name input as well
            if selection in available_pkg_ids:
                return selection

            # Parse number selection
            num = int(selection)
            if 1 <= num <= len(available_pkg_ids):
                selected_pkg_id = available_pkg_ids[num - 1]
                console.print(
                    f"[green]✓[/green] Selected: [yellow]{selected_pkg_id}[/yellow]"
                )
                return selected_pkg_id
            else:
                console.print(
                    f"[red]✗[/red] Invalid selection. "
                    f"Please enter a number between 1 and {len(available_pkg_ids)}"
                )
                console.print()

        except ValueError:
            console.print(
                f"[red]✗[/red] Invalid input. "
                f"Please enter a number between 1 and {len(available_pkg_ids)}"
            )
            console.print()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Cancelled[/yellow]")
            raise typer.Exit(code=0)


@typer_app.command(name="generate-new-ws-handler")
def generate_new_ws_handler(
    schema: bool = typer.Option(
        False,
        "--schema",
        "-s",
        help="Include JSON schema validation example"
    ),
    paginated: bool = typer.Option(
        False,
        "--paginated",
        "-p",
        help="Include pagination logic with get_paginated_results"
    ),
    roles: list[str] = typer.Option(
        None,
        "--role",
        "-r",
        help="Required RBAC roles (can specify multiple: -r admin -r editor)"
    ),
    overwrite: bool = typer.Option(
        False,
        "--overwrite",
        help="Overwrite existing file without prompting"
    ),
):
    """
    Generate a new WebSocket handler using f-string code generation.

    Creates a properly formatted Python file with:
    - Comprehensive docstrings with request/response examples
    - Type hints throughout
    - Proper error handling (ValueError, Exception)
    - AST validation (catches syntax errors)
    - Auto-formatting with Black (if available)

    The generated code passes all pre-commit hooks automatically.

    Examples:
        # Simple handler
        python cli.py generate-new-ws-handler

        # Handler with schema validation
        python cli.py generate-new-ws-handler --schema

        # Paginated handler with RBAC
        python cli.py generate-new-ws-handler --paginated -r admin -r viewer

        # All options
        python cli.py generate-new-ws-handler -s -p -r admin --overwrite
    """
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]WebSocket Handler Generator[/bold cyan]",
            subtitle="F-string based with AST validation",
            border_style="cyan"
        )
    )
    console.print()

    # Collect inputs
    module_name = console.input(
        "[cyan]Module name[/cyan] (e.g., user_handlers): "
    ).strip()

    handler_name = console.input(
        "[cyan]Handler function name[/cyan] (e.g., get_users): "
    ).strip()

    console.print()
    pkg_id = _validate_pkg_id_input()

    # Show summary
    console.print()
    console.print("[bold]Generation Summary:[/bold]")
    console.print(f"  Module: [yellow]{module_name}.py[/yellow]")
    console.print(f"  Function: [yellow]{handler_name}[/yellow]")
    console.print(f"  PkgID: [yellow]{pkg_id}[/yellow]")
    if schema:
        console.print("  Schema: [green]✓[/green] Included")
    if paginated:
        console.print("  Pagination: [green]✓[/green] Included")
    if roles:
        console.print(f"  Roles: [green]{', '.join(roles)}[/green]")
    console.print()

    try:
        generator = HandlerGenerator()
        output_path = generator.create_handler_file(
            module_name=module_name,
            pkg_id=pkg_id,
            handler_name=handler_name,
            has_schema=schema,
            has_pagination=paginated,
            roles=roles if roles else None,
            overwrite=overwrite,
        )

        console.print(
            Panel.fit(
                f"[green]✓ Handler successfully generated[/green]\n\n"
                f"File: [yellow]{output_path}[/yellow]",
                border_style="green",
                title="Success"
            )
        )
        console.print()

        # Show next steps
        console.print("[bold]Next steps:[/bold]")
        console.print(
            "  [cyan]1.[/cyan] Implement the TODO sections in the generated file"
        )
        console.print(
            "  [cyan]2.[/cyan] Verify registration: [yellow]make ws-handlers[/yellow]"
        )
        console.print(
            "  [cyan]3.[/cyan] Test the handler: [yellow]make test[/yellow]"
        )
        console.print()

    except FileExistsError as e:
        console.print()
        console.print(
            Panel.fit(
                f"[red]File already exists[/red]\n\n{e}",
                border_style="red",
                title="Error"
            )
        )
        console.print()
        console.print(
            "[yellow]Hint:[/yellow] Use [cyan]--overwrite[/cyan] flag to replace it"
        )
        console.print()
        raise typer.Exit(code=1)

    except SyntaxError as e:
        console.print()
        console.print(
            Panel.fit(
                f"[red]Syntax error in generated code[/red]\n\n{e}",
                border_style="red",
                title="Error"
            )
        )
        console.print()
        raise typer.Exit(code=1)

    except Exception as e:
        console.print()
        console.print(
            Panel.fit(
                f"[red]Unexpected error[/red]\n\n{e}",
                border_style="red",
                title="Error"
            )
        )
        console.print()
        raise typer.Exit(code=1)


@typer_app.command(name="validate-handlers")
def validate_handlers():
    """
    Validate that all PkgIDs have registered handlers.

    Checks for missing handlers and reports the validation status.
    Useful for CI/CD pipelines to ensure complete handler coverage.

    Example:
        python cli.py validate-handlers
    """
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]Handler Validation[/bold cyan]",
            border_style="cyan"
        )
    )
    console.print()

    missing_handlers = []
    for pkg_id in PkgID:
        handler = pkg_router.handlers_registry.get(pkg_id)
        if not handler:
            missing_handlers.append(pkg_id.name)

    total = len(PkgID)
    registered = total - len(missing_handlers)

    if missing_handlers:
        console.print(
            f"[red]✗ Validation Failed[/red]: "
            f"{registered}/{total} handlers registered\n"
        )
        console.print("[bold]Missing handlers:[/bold]")
        for handler_name in missing_handlers:
            console.print(f"  [red]•[/red] {handler_name}")
        console.print()
        raise typer.Exit(code=1)
    else:
        console.print(
            Panel.fit(
                f"[green]✓ All handlers registered[/green]\n\n"
                f"Total: {total}/{total}",
                border_style="green",
                title="Success"
            )
        )
        console.print()


if __name__ == "__main__":
    typer_app()
