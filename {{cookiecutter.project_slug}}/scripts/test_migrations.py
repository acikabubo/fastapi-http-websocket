"""
Test database migrations can be applied and rolled back cleanly.

This script tests that:
1. Current migrations can be applied (upgrade)
2. Migrations can be rolled back (downgrade)
3. Migrations can be reapplied after rollback

Usage:
    python scripts/test_migrations.py
    make test-migrations
"""

import asyncio
import subprocess
import sys

from sqlalchemy import text

from {{cookiecutter.module_name}}.logging import logger
from {{cookiecutter.module_name}}.storage.db import engine


async def get_current_revision() -> str | None:
    """
    Get the current migration revision from the database.

    Returns:
        Current revision ID or None if no migrations applied.
    """
    try:
        async with engine.begin() as conn:
            result = await conn.execute(
                text("SELECT version_num FROM alembic_version")
            )
            return result.scalar()
    except Exception as e:
        logger.warning(f"Could not get current revision: {e}")
        return None


async def run_alembic_command(command: list[str]) -> bool:
    """
    Run an Alembic command and check for success.

    Args:
        command: Alembic command as list (e.g., ["upgrade", "head"])

    Returns:
        True if command succeeded, False otherwise.
    """
    full_command = ["alembic"] + command
    logger.info(f"Running: {' '.join(full_command)}")

    result = subprocess.run(
        full_command, capture_output=True, text=True, check=False
    )

    if result.returncode != 0:
        logger.error(f"Command failed: {result.stderr}")
        return False

    logger.info(f"Command succeeded: {result.stdout}")
    return True


async def test_migrations() -> bool:
    """
    Test migration upgrade and downgrade operations.

    Returns:
        True if all tests pass, False otherwise.
    """
    logger.info("=" * 60)
    logger.info("Testing database migrations...")
    logger.info("=" * 60)

    # Get initial revision
    initial_rev = await get_current_revision()
    logger.info(f"Initial revision: {initial_rev}")

    if not initial_rev:
        logger.warning("No migrations applied. Applying all migrations...")
        if not await run_alembic_command(["upgrade", "head"]):
            logger.error("Failed to apply initial migrations")
            return False
        initial_rev = await get_current_revision()

    # Test downgrade (rollback one revision)
    logger.info("\n" + "=" * 60)
    logger.info("Test 1: Testing downgrade (-1 revision)...")
    logger.info("=" * 60)

    if not await run_alembic_command(["downgrade", "-1"]):
        logger.error("❌ Downgrade test failed")
        return False

    downgraded_rev = await get_current_revision()
    logger.info(f"After downgrade: {downgraded_rev}")

    if downgraded_rev == initial_rev:
        logger.error("❌ Revision did not change after downgrade")
        return False

    logger.info("✅ Downgrade test passed")

    # Test upgrade (reapply migrations)
    logger.info("\n" + "=" * 60)
    logger.info("Test 2: Testing upgrade to head...")
    logger.info("=" * 60)

    if not await run_alembic_command(["upgrade", "head"]):
        logger.error("❌ Upgrade test failed")
        return False

    final_rev = await get_current_revision()
    logger.info(f"After upgrade: {final_rev}")

    if final_rev != initial_rev:
        logger.error(
            f"❌ Final revision ({final_rev}) != "
            f"initial revision ({initial_rev})"
        )
        return False

    logger.info("✅ Upgrade test passed")

    # All tests passed
    logger.info("\n" + "=" * 60)
    logger.info("✅ All migration tests passed!")
    logger.info("=" * 60)
    return True


async def main() -> int:
    """
    Main entry point for migration testing.

    Returns:
        Exit code: 0 for success, 1 for failure.
    """
    try:
        success = await test_migrations()
        return 0 if success else 1
    except Exception as e:
        logger.error(f"Migration testing failed with exception: {e}")
        return 1
    finally:
        await engine.dispose()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
