import typer
from jinja2 import Template
from rich.console import Console
from rich.table import Table

from {{cookiecutter.module_name}}.api.ws.constants import PkgID
from {{cookiecutter.module_name}}.routing import pkg_router

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
            "If this is new PkgID please add first in PkgID Enum in {{cookiecutter.module_name}}.api.ws.constants.py"
        )
        print()
        print('If you want to exit/abort press "Ctrl + C"')
        pkg_id = __pkg_id_input()

    return pkg_id


@typer_app.command()
def generate_new_ws_handler():
    """
    This function generates a new WebSocket handler module based on user input.

    The function prompts the user to enter the module name, handler name, and PkgID.
    It then uses a Jinja2 template to render the WebSocket handler module code with the provided inputs.
    The rendered module code is written to a file with the specified module name.

    Parameters:
    None

    Returns:
    None
    """
    module_name: str = input("Please write module name: ")
    handler_name: str = input("Please write handler name: ")
    pkg_id = __pkg_id_input()

    with open("templates/ws_handler.jinja") as f:
        module_code = Template(f.read()).render(
            pkg_id=pkg_id,
            handler_name=handler_name,
        )

        # Write the rendered module to a file
        with open(f"{module_name}.py", "w") as f:
            f.write(module_code)

        print()
        print(
            "Module is succesfully generated. You can find it in {{cookiecutter.module_name}}.api.ws.handlers"
        )


if __name__ == "__main__":
    typer_app()
