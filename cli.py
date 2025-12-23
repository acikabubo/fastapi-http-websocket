import typer
from rich.console import Console
from rich.table import Table

from app.api.ws.constants import PkgID
from app.routing import pkg_router
from generate_ws_handler import HandlerGenerator

typer_app = typer.Typer()
console = Console()


@typer_app.command()
def ws_handlers():
    """
    Prints a table of all the registered WebSocket handlers and their corresponding package IDs.

    The table includes the following columns:
    - PkgID: The package ID of the WebSocket handler.
    - Handlers Path: The full module path of the WebSocket handler function.

    This function is used to provide an overview of all the registered WebSocket handlers in the application.
    """
    table = Table("PkgID", "Handler Path")

    for pkg_id in PkgID:
        handler = pkg_router.handlers_registry.get(pkg_id)

        if not handler:
            table.add_row(str(pkg_id), "")
            continue

        handler_path = f"{handler.__module__}.[yellow]{handler.__name__}"
        table.add_row(f"{pkg_id.value} - {pkg_id.name}", handler_path)

    console.print(table)


def __pkg_id_input() -> str:
    """
    Function to handle user input for PkgID.

    This function prompts the user to enter a PkgID name. It then checks if the entered PkgID is valid,
    not unknown, and not already taken. If the PkgID is invalid, the function provides a list of available
    PkgIDs and prompts the user to enter a valid PkgID.

    Parameters:
    None

    Returns:
    str: The validated PkgID entered by the user.
    """
    pkg_id: str = input("Please write PkgID name: ")

    # Check pkg_id
    all_pkg_ids = {pkg.name for pkg in PkgID}
    taken_pkg_ids = {pkg.name for pkg in pkg_router.handlers_registry.keys()}

    available_pkg_id = all_pkg_ids - taken_pkg_ids

    if pkg_id not in available_pkg_id:
        print()
        print(f'"{pkg_id}" invalid unknown or taken PkgID')
        print()
        print(f"You need to use one of these: {available_pkg_id}")
        print()
        print(
            "If this is new PkgID please add first in PkgID Enum in app.api.ws.constants.py"
        )
        print()
        print('If you want to exit/abort press "Ctrl + C"')
        pkg_id = __pkg_id_input()

    return pkg_id


@typer_app.command()
def generate_new_ws_handler(
    schema: bool = typer.Option(
        False, "--schema", help="Include JSON schema validation"
    ),
    paginated: bool = typer.Option(
        False, "--paginated", help="Include pagination logic"
    ),
    roles: list[str] = typer.Option(
        None, "--role", help="Required RBAC roles (can specify multiple)"
    ),
    overwrite: bool = typer.Option(
        False, "--overwrite", help="Overwrite existing file if it exists"
    ),
):
    """
    Generate a new WebSocket handler module using f-string code generation.

    This command prompts for module name, handler name, and PkgID,
    then generates a properly formatted Python file with comprehensive
    docstrings, error handling, and type hints.

    The generated code is validated using AST and automatically formatted
    with Black (if available) to match project standards.
    """
    console.print(
        "\n[bold cyan]WebSocket Handler Generator[/bold cyan]\n"
    )

    module_name: str = input("Please write module name: ")
    handler_name: str = input("Please write handler name: ")
    pkg_id = __pkg_id_input()

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

        console.print()
        console.print(
            f"[green]✓[/green] Handler successfully generated at: "
            f"[yellow]{output_path}[/yellow]"
        )
        console.print()

        # Show next steps
        console.print("[bold]Next steps:[/bold]")
        console.print(
            "  1. Implement the TODO sections in the generated file"
        )
        console.print(
            "  2. Test the handler: [cyan]make ws-handlers[/cyan]"
        )
        console.print(
            "  3. Run tests: [cyan]make test[/cyan]"
        )
        console.print()

    except FileExistsError as e:
        console.print(
            f"\n[red]✗[/red] Error: {e}\n",
            style="red"
        )
        console.print(
            "Use [cyan]--overwrite[/cyan] flag to replace the existing file.\n"
        )
    except SyntaxError as e:
        console.print(
            f"\n[red]✗[/red] Syntax error in generated code: {e}\n",
            style="red"
        )
    except Exception as e:
        console.print(
            f"\n[red]✗[/red] Unexpected error: {e}\n",
            style="red"
        )


if __name__ == "__main__":
    typer_app()
