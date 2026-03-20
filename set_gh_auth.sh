#!/usr/bin/env bash
set -euo pipefail

# Configure repo-local Git credentials for browser-based GitHub auth in Codespaces
# without PATs and without SSH.

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELPER_PATH="$HOME/.local/bin/git-credential-gh-noenv"

echo "[1/5] Creating custom credential helper..."
mkdir -p "$HOME/.local/bin"
cat > "$HELPER_PATH" <<'EOF'
#!/usr/bin/env bash
unset GITHUB_TOKEN
unset GH_TOKEN
exec gh auth git-credential "$@"
EOF
chmod +x "$HELPER_PATH"

echo "[2/5] Setting repo-local credential helper..."
cd "$REPO_DIR"
# Remove all existing local helpers so reruns don't fail on multi-value keys.
git config --local --unset-all credential.helper || true
# Reset inherited helpers (e.g. Codespaces system helper) for this repo.
git config --local --add credential.helper ""
git config --local --add credential.helper "$HELPER_PATH"

echo "[3/5] Starting GitHub web login..."
env -u GITHUB_TOKEN -u GH_TOKEN gh auth login -h github.com -p https --web

echo "[4/5] Verifying auth..."
env -u GITHUB_TOKEN -u GH_TOKEN gh auth status -h github.com

echo "[5/5] Done. You can now push from this repo."
echo "Try: git -C \"$REPO_DIR\" push"
