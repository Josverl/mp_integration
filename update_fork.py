#!/usr/bin/env python3

import argparse
import subprocess
import sys
from pathlib import Path

from repos import load_repo_config, get_available_repos


def run_command(command, check=True):
    """Runs a command and returns its output."""
    print(f"Executing: {' '.join(command)}")
    result = subprocess.run(command, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"Error running command: {' '.join(command)}")
        print(f"Stdout:\n{result.stdout}")
        print(f"Stderr:\n{result.stderr}")
        sys.exit(1)
    return result.stdout.strip()


def parse_cli_merge_item(value):
    """Parse a CLI merge item into int PR number or branch name string."""
    value = value.strip()
    if value.isdigit():
        return int(value)
    return value


def git_ref_exists(ref):
    """Return True if a git ref exists locally."""
    result = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", ref], capture_output=True, text=True
    )
    return result.returncode == 0


def detect_current_repo(available_repos):
    """
    Detect the current repository by checking git remote URLs.

    Returns:
        str: The detected repository name, or None if not detected.
    """
    # Try to get remote URLs (both upstream and origin)
    for remote in ["upstream", "origin"]:
        result = subprocess.run(
            ["git", "remote", "get-url", remote],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            # Extract repo name from URL
            # Handles both HTTPS and SSH URLs:
            # - https://github.com/owner/repo.git
            # - git@github.com:owner/repo.git
            # - https://github.com/owner/repo
            for repo_name in available_repos:
                # Match if URL contains /repo_name.git or /repo_name (end of string)
                if f"/{repo_name}.git" in url or url.endswith(f"/{repo_name}"):
                    return repo_name

    return None


def resolve_branch_merge_ref(branch, origin_remote):
    """Resolve a merge ref for branch, preferring local then origin/<branch>."""
    # Check if branch already specifies a remote (e.g., "upstream/branch_name")
    # Only treat as remote-qualified if the prefix is an actual git remote.
    if "/" in branch:
        remote_name, branch_name = branch.split("/", 1)
        # Verify this is a real remote, not just a branch with slashes (e.g., "copilot/feature")
        remote_check = subprocess.run(
            ["git", "remote", "get-url", remote_name],
            capture_output=True, text=True,
        )
        if remote_check.returncode == 0:
            remote_ref = f"refs/remotes/{remote_name}/{branch_name}"
            if git_ref_exists(remote_ref):
                print(f"Using remote branch '{branch}' for merge.")
                return branch, False
            print(f"Error: Remote branch '{branch}' does not exist.")
            sys.exit(1)

    # Check for local branch
    local_ref = f"refs/heads/{branch}"
    if git_ref_exists(local_ref):
        return branch, True

    # Fall back to origin remote
    remote_ref = f"refs/remotes/{origin_remote}/{branch}"
    if git_ref_exists(remote_ref):
        fallback = f"{origin_remote}/{branch}"
        print(f"Local branch '{branch}' not found; falling back to '{fallback}' for merge.")
        return fallback, False

    print(f"Error: Neither local branch '{branch}' nor '{origin_remote}/{branch}' exists.")
    sys.exit(1)


def build_merge_commit_message(display_name, target_branch):
    """Build a merge commit subject that satisfies verifygitlog formatting rules (max 72 chars)."""
    msg = f"ci: Merge {display_name} into {target_branch}."
    if len(msg) > 72:
        # Truncate display_name so the subject fits; keep trailing period.
        overhead = len("ci: Merge  into .") + len(target_branch)
        msg = f"ci: Merge {display_name[: 72 - overhead]}… into {target_branch}."
    # try to avoid creating noise in PR conversations.
    return msg.replace("#", " ").strip()


def bump_version():
    """Bump version using uv and commit the changes."""
    print("\n--- Bumping version ---")

    # Check if uv is available
    result = subprocess.run(["uv", "--version"], capture_output=True, text=True)
    if result.returncode != 0:
        print("Warning: 'uv' command not found. Skipping version bump.")
        return False

    # Check if pyproject.toml exists (indicates a Python project with uv support)
    if not Path("pyproject.toml").exists():
        print("Warning: pyproject.toml not found. Skipping version bump.")
        return False

    # Run uv version bump
    print("Executing: uv version --bump dev --bump patch")
    result = subprocess.run(
        ["uv", "version", "--bump", "dev", "--bump", "patch"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Warning: uv version bump failed. Skipping.")
        print(f"Stderr: {result.stderr}")
        return False

    print(result.stdout.strip())

    # Check if there are changes to commit
    result = subprocess.run(["git", "diff", "--quiet", "pyproject.toml"], capture_output=True, text=True)

    if result.returncode == 0:
        print("No version changes detected.")
        return False

    # Commit the version bump
    run_command(["git", "add", "pyproject.toml"])
    # Get the new version for the commit message
    result = subprocess.run(["uv", "version"], capture_output=True, text=True)
    version = result.stdout.strip() if result.returncode == 0 else "unknown"

    run_command(
        [
            "git",
            "commit",
            "-m",
            f"build: Bump version to {version}",
            "--signoff",
            "--no-verify",
        ]
    )
    print(f"Version bumped to {version} and committed.")
    return True


def build_integration_branch(branch_key, args, config, first_items=None, last_items=None):
    """Build one integration branch identified by branch_key."""
    first_items = first_items or []
    last_items = last_items or []

    merge_order = config.integration_branches[branch_key]["sources"]
    target_branch = config.integration_branches[branch_key]["target_branch"]

    UPSTREAM_REMOTE = config.UPSTREAM_REMOTE
    ORIGIN_REMOTE = config.ORIGIN_REMOTE
    MAIN_BRANCH = config.MAIN_BRANCH

    active_merge_order = first_items + list(merge_order) + last_items

    # 3. Prepare branches by fetching upstream PRs
    # (We no longer rebase them individually here to preserve any stacked dependencies)
    # Each entry is (merge_ref, strategy, display_name).
    branches_to_combine = []
    for item in active_merge_order:
        strategy = None
        if isinstance(item, tuple):
            item, strategy = item

        if isinstance(item, int) or (isinstance(item, str) and item.isdigit()):
            pr_number = item
            print(f"\n--- Fetching upstream PR {pr_number} ---")
            if args.keep_pr_refs:
                local_pr_branch = f"upstream-pr/{pr_number}"
                # Fetch the PR from upstream into a local branch (use + to force overwrite if local branch diverges)
                run_command(
                    [
                        "git",
                        "fetch",
                        UPSTREAM_REMOTE,
                        f"+pull/{pr_number}/head:{local_pr_branch}",
                    ]
                )
                # Push it to origin so we have a synced backup of this PR in our fork
                if not args.no_push:
                    run_command(
                        [
                            "git",
                            "push",
                            ORIGIN_REMOTE,
                            f"{local_pr_branch}:{local_pr_branch}",
                            "--force",
                        ]
                    )
                branches_to_combine.append((local_pr_branch, strategy, local_pr_branch))
            else:
                # Fetch PR head to FETCH_HEAD and merge by commit SHA to avoid creating extra branches.
                run_command(["git", "fetch", UPSTREAM_REMOTE, f"pull/{pr_number}/head"])
                pr_commit = run_command(["git", "rev-parse", "FETCH_HEAD"])
                branches_to_combine.append((pr_commit, strategy, f"PR {pr_number}"))
        else:
            branch = item
            merge_ref, has_local_branch = resolve_branch_merge_ref(branch, ORIGIN_REMOTE)

            if "update_fork" not in branch:
                print(f"\n--- Including local feature branch for merge: {branch} ---")
                if has_local_branch:
                    if not args.no_push:
                        # Push the local feature branch before merge to keep origin in sync.
                        run_command(["git", "push", ORIGIN_REMOTE, branch, "--force-with-lease"])
                else:
                    print(f"Skipping push for '{branch}' because only '{merge_ref}' exists.")
            branches_to_combine.append((merge_ref, strategy, branch))

    # 4. Build the combined development branch
    print(f"\n--- Rebuilding {target_branch} as a combination of all branches ---")
    # Reset destination branch to match MAIN_BRANCH
    run_command(["git", "checkout", "-B", target_branch, MAIN_BRANCH])

    # Bump version if requested
    if args.bump:
        bump_version()

    # Merge all PRs and feature branches into this daily integrated branch
    for merge_ref, strategy, display_name in branches_to_combine:
        print(f"Merging {display_name} into {target_branch}...")
        merge_cmd = [
            "git",
            "merge",
            merge_ref,
            "-m",
            build_merge_commit_message(display_name, target_branch),
            "--signoff",
            "--no-verify",  # skip commit hooks (verifygitlog etc.) for automated merges
        ]
        if strategy:
            merge_cmd.append(strategy)
        result = subprocess.run(merge_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            # rerere may have resolved conflicts in the working tree but not staged them.
            # Use 'git rerere remaining' to check for truly unresolved files.
            remaining = subprocess.run(
                ["git", "rerere", "remaining"],
                capture_output=True, text=True,
            )
            unresolved = remaining.stdout.strip()
            if not unresolved:
                # rerere resolved everything — stage and commit
                print(f"  rerere resolved conflicts for {display_name}, committing...")
                run_command(["git", "add", "--update"])
                run_command([
                    "git", "commit",
                    "-m", build_merge_commit_message(display_name, target_branch),
                    "--signoff", "--no-verify", "--no-edit",
                ])
            else:
                print(f"Error running command: {' '.join(merge_cmd)}")
                print(f"Stdout:\n{result.stdout}")
                print(f"Stderr:\n{result.stderr}")
                print(f"Unresolved files:\n{unresolved}")
                print(
                    "\nTip: Resolve manually, commit, and rerere will remember "
                    "the resolution for next time."
                )
                sys.exit(1)

    # Force push the newly combined development branch
    if not args.no_push:
        run_command(["git", "push", ORIGIN_REMOTE, target_branch, "--force"])


def main():
    """Main function to update the repository."""
    available_repos = get_available_repos()

    # Detect the current repository from git remotes
    detected_repo = detect_current_repo(available_repos)
    default_repo = detected_repo if detected_repo else "micropython"

    parser = argparse.ArgumentParser(
        description="Update fork and local branches for multiple repositories.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Available repositories: {', '.join(available_repos)}",
    )

    repo_help = f"Repository to work with. Choices: {', '.join(available_repos)}."
    if detected_repo:
        repo_help += f" (default: {default_repo}, auto-detected from git remotes)"
    else:
        repo_help += f" (default: {default_repo})"

    parser.add_argument(
        "--repo",
        default=default_repo,
        choices=available_repos,
        metavar="REPO",
        help=repo_help,
    )
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="Build/merge branches locally but skip all 'git push' steps.",
    )
    parser.add_argument(
        "--branch",
        metavar="BRANCH",
        help="Integration branch to build, or 'all' to build every branch. "
        "If not specified, uses the repository's default target.",
    )
    parser.add_argument(
        "--insert",
        "--first",
        dest="first",
        action="append",
        default=[],
        metavar="ITEM",
        help="Prepend merge item(s) to merge_order. ITEM can be a PR number (e.g. 18853) or branch name. "
        "Ignored when --branch all is used.",
    )
    parser.add_argument(
        "--add",
        "--last",
        dest="last",
        action="append",
        default=[],
        metavar="ITEM",
        help="Append merge item(s) to merge_order. ITEM can be a PR number (e.g. 18853) or branch name. "
        "Ignored when --branch all is used.",
    )
    parser.add_argument(
        "--keep-pr-refs",
        action="store_true",
        help="Keep fetched PRs as local/origin upstream-pr/* branches (default: merge directly from fetched commits).",
    )
    parser.add_argument(
        "--bump",
        action="store_true",
        help="Bump version using 'uv version --bump dev --bump patch' and commit before merging branches.",
    )
    parser.add_argument(
        "--list-repos",
        action="store_true",
        help="List all available repository configurations and exit.",
    )
    args = parser.parse_args()

    # Handle --list-repos
    if args.list_repos:
        print("Available repository configurations:")
        for repo in available_repos:
            from repos import get_repo_info

            info = get_repo_info(repo)
            print(f"\n  {repo}:")
            print(f"    Description: {info['description'].strip()}")
            print(f"    Upstream: {info['upstream_remote']}")
            print(f"    Main branch: {info['main_branch']}")
            print(f"    Default target: {info['default_target']}")
            print(f"    Integration branches: {', '.join(info['integration_branches'])}")
        sys.exit(0)

    # Load repository configuration
    try:
        config = load_repo_config(args.repo)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Set branch default after loading config
    if args.branch is None:
        args.branch = config.DEFAULT_TARGET

    # Validate branch choice
    branch_choices = list(config.integration_branches.keys()) + ["all"]
    if args.branch not in branch_choices:
        print(f"Error: Invalid branch '{args.branch}'.")
        print(f"Choices: {', '.join(branch_choices)}")
        sys.exit(1)

    cwd = Path.cwd()
    if not (cwd / ".git").is_dir():
        print("Error: This script must be run from the root of a git repository.")
        sys.exit(1)

    print(f"Starting process to update {args.repo} fork and custom branches...")

    # Ensure rerere is enabled so conflict resolutions are remembered across rebuilds.
    result = subprocess.run(
        ["git", "config", "--local", "rerere.enabled"],
        capture_output=True, text=True,
    )
    if result.stdout.strip() != "true":
        print("Enabling git rerere for this repository...")
        run_command(["git", "config", "--local", "rerere.enabled", "true"])

    # 1. Fetch the latest changes from all remotes.
    run_command(["git", "fetch", "--all"])

    # 2. Switch to the main branch and update it from upstream.
    print(f"\n--- Updating {config.MAIN_BRANCH} from {config.UPSTREAM_REMOTE} ---")
    # Reset local main branch directly to upstream's state to prevent ambiguity
    run_command(
        [
            "git",
            "checkout",
            "-B",
            config.MAIN_BRANCH,
            f"refs/remotes/{config.UPSTREAM_REMOTE}/{config.MAIN_BRANCH}",
        ]
    )
    # Push the updated master branch to your origin (fork)
    if not args.no_push:
        run_command(["git", "push", config.ORIGIN_REMOTE, config.MAIN_BRANCH])

    if args.branch == "all":
        if args.first or args.last:
            print("Warning: --insert/--add are ignored when --branch all is used.")
        for branch_key in config.integration_branches:
            print(f"\n{'=' * 60}")
            print(f"Processing integration branch: {branch_key}")
            print(f"{'=' * 60}")
            build_integration_branch(branch_key, args, config)
    else:
        first_items = [parse_cli_merge_item(item) for item in args.first]
        last_items = [parse_cli_merge_item(item) for item in args.last]
        build_integration_branch(args.branch, args, config, first_items, last_items)

    print("\n--- Repository update complete! ---")


if __name__ == "__main__":
    main()
