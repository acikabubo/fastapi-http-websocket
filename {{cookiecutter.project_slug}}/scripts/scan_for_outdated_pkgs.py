import json
import subprocess
import sys
from datetime import datetime
from typing import Any


def scan_outdated_packages() -> list[dict[str, Any]]:
    """
    Scan for outdated packages using uv pip list --outdated in JSON format.
    Returns a list of dictionaries containing package information.
    """
    try:
        # Run uv pip list --outdated with JSON output
        result = subprocess.run(
            ["uv", "pip", "list", "--outdated", "--format", "json"],
            capture_output=True,
            text=True,
            check=True,
        )

        # Parse JSON output
        packages = json.loads(result.stdout)

        # Sort packages by name
        packages.sort(key=lambda x: x["name"].lower())

        return packages

    except subprocess.CalledProcessError as e:
        print(f"Error running uv pip list: {e}")
        print(f"Error output: {e.stderr}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON output: {e}")
        sys.exit(1)


def format_output(packages: list[dict[str, Any]]) -> None:
    """
    Format and print the outdated package information.
    """
    if not packages:
        print("All packages are up to date!")
        return

    print(
        f"\nFound {len(packages)} outdated package(s) on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    print(
        "\nPackage Name".ljust(25)
        + "Current".ljust(15)
        + "Latest".ljust(15)
        + "Type"
    )
    print("-" * 65)

    for pkg in packages:
        name = pkg["name"]
        current = pkg["version"]
        latest = pkg["latest_version"]
        update_type = "normal"

        # Determine update type
        if "latest_filetype" in pkg:
            update_type = pkg["latest_filetype"]

        print(f"{name:<25}{current:<15}{latest:<15}{update_type}")


def main():
    """
    Main function to scan and display outdated packages.
    """
    try:
        packages = scan_outdated_packages()
        format_output(packages)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
