#!/usr/bin/env bash
# Claude Parrot — Auto-Patch Installer (bash/zsh)
#
# Adds a line to your shell profile that silently re-patches
# Claude Code's spinner on every terminal open.
#
# Usage: bash scripts/install-autopatch.sh
#        bash scripts/install-autopatch.sh --uninstall

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PATCH_SCRIPT="$SCRIPT_DIR/scripts/patch-claude.js"
MARKER="# claude-parrot-autopatch"
LINE="node \"$PATCH_SCRIPT\" --quiet 2>/dev/null $MARKER"

# Detect shell profile
if [ -n "$ZSH_VERSION" ] || [ -f "$HOME/.zshrc" ]; then
    PROFILE="$HOME/.zshrc"
elif [ -f "$HOME/.bashrc" ]; then
    PROFILE="$HOME/.bashrc"
elif [ -f "$HOME/.bash_profile" ]; then
    PROFILE="$HOME/.bash_profile"
else
    PROFILE="$HOME/.bashrc"
fi

if [ "$1" = "--uninstall" ]; then
    if [ -f "$PROFILE" ]; then
        sed -i.bak "/$MARKER/d" "$PROFILE" && rm -f "$PROFILE.bak"
        echo "  Removed auto-patch from $PROFILE"
    else
        echo "  No profile found at $PROFILE"
    fi
    exit 0
fi

# Check if already installed
if grep -q "claude-parrot-autopatch" "$PROFILE" 2>/dev/null; then
    echo "  Auto-patch already installed in $PROFILE"
    exit 0
fi

# Append
echo "" >> "$PROFILE"
echo "$LINE" >> "$PROFILE"
echo ""
echo "  Claude Parrot auto-patch installed!"
echo ""
echo "  Added to: $PROFILE"
echo "  Every new terminal will silently ensure the parrot spinner is active."
echo ""
echo "  To remove: bash scripts/install-autopatch.sh --uninstall"
echo ""
