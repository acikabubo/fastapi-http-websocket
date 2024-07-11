import typer
from rich.console import Console
from rich.table import Table

from app.api.ws.constants import PkgID
from app.routing import pkg_router

app = typer.Typer()
console = Console()


@app.command()
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


@app.command()
def new_command():
    pass


if __name__ == "__main__":
    app()
