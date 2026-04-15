"""
Backwards compatibility shim - imports from repos.micropython.

This file exists for backwards compatibility. The actual configuration
has been moved to repos/micropython.py as part of the multi-repository
plugin architecture.
"""

# Import everything from the micropython repository configuration
from repos.micropython import (
    UPSTREAM_REMOTE,
    MAIN_BRANCH,
    ORIGIN_REMOTE,
    DEFAULT_TARGET,
    BASE,
    integration_branches,
)

__all__ = [
    "UPSTREAM_REMOTE",
    "MAIN_BRANCH",
    "ORIGIN_REMOTE",
    "DEFAULT_TARGET",
    "BASE",
    "integration_branches",
]
