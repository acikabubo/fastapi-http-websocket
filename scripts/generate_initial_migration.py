#!/usr/bin/env python3
"""
Generate initial Alembic migration for existing models.

This script is meant to be run once to create the initial migration
for the existing Author model and any other models that exist.
"""

import subprocess
import sys


def run_command(cmd: list[str]) -> tuple[int, str, str]:
    """
    Run a shell command and return exit code, stdout, and stderr.

    Args:
        cmd: Command and arguments as a list.

    Returns:
        Tuple of (exit_code, stdout, stderr).
    """
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return result.returncode, result.stdout, result.stderr


def main() -> int:
    """
    Generate initial migration.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    print("Generating initial migration for existing models...")
    print("-" * 60)

    # Run alembic revision with autogenerate
    cmd = [
        "uv",
        "run",
        "alembic",
        "revision",
        "--autogenerate",
        "-m",
        "Initial migration - create author table",
    ]

    print(f"Running: {' '.join(cmd)}")
    exit_code, stdout, stderr = run_command(cmd)

    if stdout:
        print("STDOUT:")
        print(stdout)

    if stderr:
        print("STDERR:")
        print(stderr)

    if exit_code == 0:
        print("-" * 60)
        print("✅ Initial migration generated successfully!")
        print()
        print("Next steps:")
        print("1. Review the generated migration in alembic/versions/")
        print("2. Apply the migration: make migrate")
        print("3. If you have an existing database, consider using:")
        print("   make migration-stamp rev='head'")
        return 0
    else:
        print("-" * 60)
        print("❌ Failed to generate migration")
        print(f"Exit code: {exit_code}")
        return exit_code


if __name__ == "__main__":
    sys.exit(main())
