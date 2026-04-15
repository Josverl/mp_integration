"""
mpbuild repository integration configuration.

Repository: mattytrentini/mpbuild
Fork: josverl/mpbuild
"""

# --- Configuration ---
# The name of your remote for the upstream repository.
# Note: If running this in GitHub Actions, you must manually add the upstream remote first, e.g.:
#       git remote add upstream https://github.com/mattytrentini/mpbuild.git
#
# mattytrentini/mpbuild repository integration branches configuration.
UPSTREAM_REMOTE = "upstream"
MAIN_BRANCH = "main"

# josverl/mpbuild
ORIGIN_REMOTE = "origin"
# The primary branch on your fork that tracks the upstream repository.
DEFAULT_TARGET = "main_jv"


BASE = [
    # Add your base feature branches here
]

integration_branches = {
    "main_jv": {"target_branch": "main_jv", "sources": BASE},
    # Add more integration branches as needed
    # Example:
    # "feature_integration": {
    #     "target_branch": "integration/feature",
    #     "sources": BASE + [
    #             123,  # PR number
    #             "jv/my_feature",  # Branch name
    #             (456, "-Xtheirs"),  # PR with merge strategy
    #     ]
    # },
}
