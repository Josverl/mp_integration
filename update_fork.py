import argparse
import subprocess
import sys
from pathlib import Path

from branches import (DEFAULT_TARGET, MAIN_BRANCH, ORIGIN_REMOTE,
                      UPSTREAM_REMOTE, integration_branches)


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
    result = subprocess.run(["git", "show-ref", "--verify", "--quiet", ref], capture_output=True, text=True)
    return result.returncode == 0


def resolve_branch_merge_ref(branch, origin_remote):
    """Resolve a merge ref for branch, preferring local then origin/<branch>."""
    local_ref = f"refs/heads/{branch}"
    if git_ref_exists(local_ref):
        return branch, True

    remote_ref = f"refs/remotes/{origin_remote}/{branch}"
    if git_ref_exists(remote_ref):
        fallback = f"{origin_remote}/{branch}"
        print(f"Local branch '{branch}' not found; falling back to '{fallback}' for merge.")
        return fallback, False

    print(f"Error: Neither local branch '{branch}' nor '{origin_remote}/{branch}' exists.")
    sys.exit(1)


def build_merge_commit_message(display_name, target_branch):
    """Build a merge commit subject that satisfies verifygitlog formatting rules."""
    return f"ci: Merge {display_name} into {target_branch}."

def main():
    """Main function to update the repository."""
    parser = argparse.ArgumentParser(description="Update fork and local branches.")
    parser.add_argument("--upstream", default="upstream", help="Upstream remote name")
    parser.add_argument("--origin", default="origin", help="Origin remote name")
    parser.add_argument(
        "--branch",
        default=DEFAULT_TARGET,
        help=f"Destination integration branch (default: {DEFAULT_TARGET})",
    )
    parser.add_argument(
        "--insert", "--first",
        dest="first",
        action="append",
        default=[],
        metavar="ITEM",
        help="Prepend merge item(s) to merge_order. ITEM can be a PR number (e.g. 18853) or branch name.",
    )
    parser.add_argument(
        "--add", "--last",
        dest="last",
        action="append",
        default=[],
        metavar="ITEM",
        help="Append merge item(s) to merge_order. ITEM can be a PR number (e.g. 18853) or branch name.",
    )
    parser.add_argument(
        "--keep-pr-refs",
        action="store_true",
        help="Keep fetched PRs as local/origin upstream-pr/* branches (default: merge directly from fetched commits).",
    )
    args = parser.parse_args()

    # UPSTREAM_REMOTE = args.upstream
    # ORIGIN_REMOTE = args.origin
    target_branch = args.branch

    cwd = Path.cwd()
    if not (cwd / ".git").is_dir():
        print("Error: This script must be run from the root of a git repository.")
        sys.exit(1)
    if not (cwd / "mpy-cross").is_dir():
        print("Error: This script must be run from the root of the micropython repository.")
        sys.exit(1)

    if target_branch not in integration_branches:
        print(f"Error: Target branch '{target_branch}' is not defined in branches.py.")
        print(f"Available branches: {', '.join(integration_branches.keys())}")
        sys.exit(1)

    merge_order = integration_branches[target_branch]["sources"]
    target_branch = integration_branches[target_branch]["target_branch"]

    print("Starting process to update fork and custom branches...")

    first_items = [parse_cli_merge_item(item) for item in args.first]
    last_items = [parse_cli_merge_item(item) for item in args.last]
    active_merge_order = first_items + list(merge_order) + last_items

    # 1. Fetch the latest changes from all remotes.
    run_command(["git", "fetch", "--all"])

    # 2. Switch to the main branch and update it from upstream.
    print(f"\n--- Updating {MAIN_BRANCH} from {UPSTREAM_REMOTE} ---")
    # Reset local main branch directly to upstream's state to prevent ambiguity
    run_command(["git", "checkout", "-B", MAIN_BRANCH, f"refs/remotes/{UPSTREAM_REMOTE}/{MAIN_BRANCH}"])
    # Push the updated master branch to your origin (fork)
    run_command(["git", "push", ORIGIN_REMOTE, MAIN_BRANCH])

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
                run_command(["git", "fetch", UPSTREAM_REMOTE, f"+pull/{pr_number}/head:{local_pr_branch}"])
                # Push it to origin so we have a synced backup of this PR in our fork
                run_command(["git", "push", ORIGIN_REMOTE, f"{local_pr_branch}:{local_pr_branch}", "--force"])
                branches_to_combine.append((local_pr_branch, strategy, local_pr_branch))
            else:
                # Fetch PR head to FETCH_HEAD and merge by commit SHA to avoid creating extra branches.
                run_command(["git", "fetch", UPSTREAM_REMOTE, f"pull/{pr_number}/head"])
                pr_commit = run_command(["git", "rev-parse", "FETCH_HEAD"])
                branches_to_combine.append((pr_commit, strategy, f"PR #{pr_number}"))
        else:
            branch = item
            merge_ref, has_local_branch = resolve_branch_merge_ref(branch, ORIGIN_REMOTE)

            if "update_fork" not in branch:
                print(f"\n--- Including local feature branch for merge: {branch} ---")
                if has_local_branch:
                    # Push the local feature branch before merge to keep origin in sync.
                    run_command(["git", "push", ORIGIN_REMOTE, branch, "--force-with-lease"])
                else:
                    print(f"Skipping push for '{branch}' because only '{merge_ref}' exists.")
            branches_to_combine.append((merge_ref, strategy, branch))

    # 4. Build the combined development branch (master_jv)
    print(f"\n--- Rebuilding {target_branch} as a combination of all branches ---")
    # Reset destination branch to match MAIN_BRANCH
    run_command(["git", "checkout", "-B", target_branch, MAIN_BRANCH])
    
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
        ]
        if strategy:
            merge_cmd.append(strategy)
        run_command(merge_cmd)

    # Force push the newly combined development branch
    run_command(["git", "push", ORIGIN_REMOTE, target_branch, "--force"])

    print("\n--- Repository update complete! ---")

if __name__ == "__main__":
    main()
