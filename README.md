# MP Integration

Multi-repository fork and integration branch management tool.

## Overview

This tool automates the process of maintaining integration branches across multiple repositories by combining upstream PRs and local feature branches.

## Supported Repositories

- **micropython**: micropython/micropython → josverl/micropython
- **mpbuild**: mattytrentini/mpbuild → josverl/mpbuild

The tool automatically detects which repository you're working in by checking git remote URLs and uses it as the default.

## Usage

### Basic Usage

Update the default integration branch (auto-detects repository):
```bash
./update_fork.py
```

The script automatically detects the current repository from git remotes. If you're in the micropython repository, it defaults to micropython. If you're in the mpbuild repository, it defaults to mpbuild.

Explicitly specify a repository:
```bash
./update_fork.py --repo mpbuild
```

### Building Specific Branches

Build a specific integration branch:
```bash
./update_fork.py --repo micropython --branch mpremote
```

Build all integration branches:
```bash
./update_fork.py --repo micropython --branch all
```

### Adding Temporary Items

Add PRs or branches temporarily without editing configuration:
```bash
# Add items at the beginning
./update_fork.py --insert 18853 --insert jv/test-feature

# Add items at the end
./update_fork.py --add 18900 --add jv/another-feature
```

### Options

- `--repo REPO`: Select repository (micropython, mpbuild, etc.). Auto-detected from git remotes if not specified.
- `--branch BRANCH`: Integration branch to build, or 'all' for all branches
- `--insert ITEM`: Prepend PR number or branch name to merge order
- `--add ITEM`: Append PR number or branch name to merge order
- `--no-push`: Build locally without pushing to origin
- `--keep-pr-refs`: Keep fetched PRs as local upstream-pr/* branches
- `--list-repos`: List all available repository configurations

### Examples

```bash
# List all available repositories
./update_fork.py --list-repos

# Update micropython with a temporary PR included
./update_fork.py --repo micropython --insert 18853

# Build all mpbuild integration branches
./update_fork.py --repo mpbuild --branch all

# Test locally without pushing
./update_fork.py --repo micropython --no-push
```

## Adding a New Repository

1. Create a new configuration file in `repos/<reponame>.py`:

```python
"""
Your repository integration configuration.

Repository: upstream/repo
Fork: yourfork/repo
"""

UPSTREAM_REMOTE = "upstream"
MAIN_BRANCH = "main"
ORIGIN_REMOTE = "origin"
DEFAULT_TARGET = "main_jv"

BASE = [
    # Your base feature branches
]

integration_branches = {
    "main_jv": {
        "target_branch": "main_jv",
        "sources": BASE
    },
    # Add more integration branches as needed
}
```

2. The configuration is automatically discovered and available via `--repo <reponame>`

## Configuration Structure

Each repository configuration must define:

- `UPSTREAM_REMOTE`: Remote name for upstream repository
- `MAIN_BRANCH`: Name of the main/master branch
- `ORIGIN_REMOTE`: Remote name for your fork
- `DEFAULT_TARGET`: Default integration branch to build
- `integration_branches`: Dictionary of integration branch configurations

### Integration Branch Format

```python
integration_branches = {
    "branch_key": {
        "target_branch": "actual/branch/name",
        "sources": [
            123,                    # PR number from upstream
            "jv/feature",          # Local or origin branch
            (456, "-Xtheirs"),     # PR with merge strategy
        ]
    }
}
```

## How It Works

1. Fetches latest changes from all remotes
2. Updates the main branch from upstream
3. For each integration branch:
   - Resets to main branch
   - Fetches and merges PRs from upstream
   - Merges local feature branches
   - Pushes the combined branch to origin

## Handling Merge Conflicts with rerere

Because the integration branch is rebuilt from scratch on every run, the same merge conflicts can recur each time. The script uses Git's **rerere** ("reuse recorded resolution") to handle this automatically.

### How it works

1. **First time a conflict occurs**, the merge fails and the script stops. Git records a "preimage" of the conflict.
2. **You resolve the conflict** manually (e.g., in VS Code using the merge editor) and commit.
3. Git records your resolution as a "postimage" — this is the rerere cache.
4. **On the next run**, Git detects the same conflict, applies your recorded resolution automatically, and the script stages and commits it without stopping.

### Resolving a conflict (first time)

When the script stops with a conflict:

1. Open the conflicted file in VS Code — it will show the merge conflict markers and offer **Accept Current**, **Accept Incoming**, **Accept Both** options inline.
2. Resolve the conflict (e.g., click **Accept Both Changes** to keep both sides).
3. Save the file.
4. Stage and commit from the terminal:
   ```bash
   git add -u
   git commit --signoff --no-verify --no-edit
   ```
   This records the resolution in the rerere cache.
5. Re-run the script:
   ```bash
   ../mp_integration/update_fork.py
   ```
   The same conflict will now be resolved automatically:
   ```
   Merging PR 95 into main_jv...
     rerere resolved conflicts for PR 95, committing...
   ```

### Merge strategies

For sources that consistently conflict, you can specify a merge strategy in the configuration:

```python
BASE = [
    "my-feature",              # Normal merge
    (95, "-Xtheirs"),          # On conflict, take the PR's version
    (74, "-Xpatience"),        # Use patience diff for cleaner conflict detection
]
```

| Strategy | Effect |
|----------|--------|
| `-Xtheirs` | On conflict, accept the incoming (PR/branch) side |
| `-Xours` | On conflict, accept the current (integration branch) side |
| `-Xpatience` | Use patience diff algorithm for better conflict alignment |

### Checking rerere status

```bash
# List recorded resolutions
git rerere status

# See the diff of what rerere resolved
git rerere diff

# Clear all cached resolutions (if needed)
git rerere gc
```

## Requirements

- Git repository with upstream and origin remotes configured
- Python 3.6+
- Appropriate access to push to origin
