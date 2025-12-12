"""
Comprehensive database migration tests.

Tests verify that:
- Migration IDs are unique
- Migrations have proper documentation
- No conflicting migration branches exist
- Migrations have down_revision linkage

For upgrade/downgrade testing, use `make test-migrations` script.
"""

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory


@pytest.fixture
def alembic_config() -> Config:
    """
    Create Alembic configuration for testing.

    Returns:
        Alembic Config object.
    """
    return Config("alembic.ini")


@pytest.fixture
def alembic_script(alembic_config: Config) -> ScriptDirectory:
    """
    Get Alembic script directory for inspecting migrations.

    Args:
        alembic_config: Alembic configuration.

    Returns:
        ScriptDirectory object for migration inspection.
    """
    return ScriptDirectory.from_config(alembic_config)


class TestMigrationStructure:
    """Test migration structure and metadata."""

    def test_migration_ids_unique(self, alembic_script: ScriptDirectory):
        """Test all migration revision IDs are unique."""
        revisions = [rev.revision for rev in alembic_script.walk_revisions()]

        assert len(revisions) == len(set(revisions)), (
            "Duplicate revision IDs found in migrations"
        )

    def test_migrations_have_docstrings(
        self, alembic_script: ScriptDirectory
    ):
        """Test all migrations have descriptive docstrings."""
        for revision in alembic_script.walk_revisions():
            assert revision.doc, (
                f"Migration {revision.revision} is missing docstring. "
                "Add a message with -m flag when creating migrations."
            )
            assert len(revision.doc) > 10, (
                f"Migration {revision.revision} has too short docstring: "
                f"{revision.doc}"
            )

    def test_no_migration_conflicts(self, alembic_script: ScriptDirectory):
        """Test there are no conflicting migration branches."""
        heads = alembic_script.get_heads()

        assert len(heads) == 1, (
            f"Multiple migration heads found: {heads}. "
            "Merge migrations to create single head."
        )

    def test_migrations_have_down_revision(
        self, alembic_script: ScriptDirectory
    ):
        """Test all migrations (except first) have down_revision."""
        revisions = list(alembic_script.walk_revisions())

        # All revisions except the last (oldest) should have down_revision
        for revision in revisions[:-1]:
            assert revision.down_revision, (
                f"Migration {revision.revision} is missing down_revision"
            )
