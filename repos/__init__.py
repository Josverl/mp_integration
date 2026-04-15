"""
Repository configuration plugin discovery.

This module automatically discovers and loads repository-specific configurations
from the repos/ directory. Each repository configuration is a Python module that
defines the required constants and integration_branches dictionary.
"""

import importlib
import sys
from pathlib import Path
from typing import Dict, Any


def discover_repo_configs():
    """
    Discover all available repository configurations.

    Returns:
        Dict[str, str]: Dictionary mapping repo names to module names.
    """
    repos_dir = Path(__file__).parent
    repo_configs = {}

    for config_file in repos_dir.glob("*.py"):
        if config_file.name.startswith("_"):
            continue

        repo_name = config_file.stem
        repo_configs[repo_name] = f"repos.{repo_name}"

    return repo_configs


def load_repo_config(repo_name: str):
    """
    Load a repository configuration by name.

    Args:
        repo_name: The name of the repository (e.g., 'micropython', 'mpbuild')

    Returns:
        Module: The loaded configuration module

    Raises:
        ValueError: If the repository configuration doesn't exist or is invalid
    """
    available_configs = discover_repo_configs()

    if repo_name not in available_configs:
        available = ", ".join(available_configs.keys())
        raise ValueError(f"Repository '{repo_name}' not found. Available: {available}")

    module_name = available_configs[repo_name]
    config = importlib.import_module(module_name)

    # Validate required attributes
    required_attrs = [
        "UPSTREAM_REMOTE",
        "MAIN_BRANCH",
        "ORIGIN_REMOTE",
        "DEFAULT_TARGET",
        "integration_branches",
    ]

    missing = [attr for attr in required_attrs if not hasattr(config, attr)]
    if missing:
        raise ValueError(
            f"Repository config '{repo_name}' is missing required attributes: {missing}"
        )

    return config


def get_available_repos():
    """
    Get a list of all available repository configurations.

    Returns:
        List[str]: List of available repository names.
    """
    return sorted(discover_repo_configs().keys())


def get_repo_info(repo_name: str) -> Dict[str, Any]:
    """
    Get information about a repository configuration.

    Args:
        repo_name: The name of the repository

    Returns:
        Dict containing repository information
    """
    config = load_repo_config(repo_name)

    return {
        "name": repo_name,
        "upstream_remote": config.UPSTREAM_REMOTE,
        "main_branch": config.MAIN_BRANCH,
        "origin_remote": config.ORIGIN_REMOTE,
        "default_target": config.DEFAULT_TARGET,
        "integration_branches": list(config.integration_branches.keys()),
        "description": config.__doc__ or "",
    }
