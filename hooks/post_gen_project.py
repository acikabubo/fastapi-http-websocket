"""Post-generation hook for cookiecutter template.

This script runs after the project is generated from the template.
It creates a .env file from .env.example for convenience.
"""

import logging
import shutil
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)


def create_env_file() -> None:
    """Create .env file from .env.example in the generated project."""
    # Get the current directory (generated project root)
    project_root = Path.cwd()

    env_example = project_root / ".env.example"
    env_file = project_root / ".env"

    # Create .env from .env.example if it exists
    if env_example.exists():
        if not env_file.exists():
            shutil.copy(env_example, env_file)
            logger.info(
                "✓ Created %s",
                env_file.relative_to(project_root.parent),
            )
        else:
            logger.warning(
                "⚠ %s already exists, skipping creation",
                env_file.name,
            )
    else:
        logger.warning(
            "⚠ %s not found, skipping .env creation",
            env_example.name,
        )


def remove_monitoring_files() -> None:
    """Remove monitoring-related files if monitoring is disabled."""
    include_monitoring = "{{ cookiecutter.include_monitoring }}"

    if include_monitoring == "no":
        project_root = Path.cwd()
        docker_dir = project_root / "docker"

        # List of monitoring directories to remove
        monitoring_dirs = [
            docker_dir / "prometheus",
            docker_dir / "grafana",
            docker_dir / "loki",
            docker_dir / "alloy",
        ]

        for directory in monitoring_dirs:
            if directory.exists():
                shutil.rmtree(directory)
                logger.info(
                    "✓ Removed %s (monitoring disabled)",
                    directory.relative_to(project_root),
                )


if __name__ == "__main__":
    logger.info("")
    logger.info("Running post-generation setup...")
    logger.info("")

    create_env_file()
    remove_monitoring_files()

    logger.info("")
    logger.info("✓ Project setup complete!")
    logger.info("")
