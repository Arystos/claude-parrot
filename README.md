# Party Parrot for Claude Code

Replace Claude Code's thinking spinner with a rainbow-colored party parrot that cycles through colors while Claude is thinking.

```
  Normal:    * Thinking...
  Patched:   🟥🦜 Vibing...  →  🟧🦜 Ruminating...  →  🟩🦜 Clauding...
```

## What it does

- Replaces the `· ✢ * ✶ ✻ ✽` spinner symbols with a rainbow parrot animation
- Works in both **VS Code** (Claude Code extension) and **terminal** (CLI)
- Backs up all original files — fully reversible
- Re-run after Claude Code updates to re-apply the patch

## Prerequisites

- [Node.js](https://nodejs.org) (v18+)
- [Claude Code](https://claude.ai/code) installed (either via VS Code extension, standalone binary, or npm)

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/party-parrot-claude.git
cd party-parrot-claude
node setup.js
```

The setup script will:
1. Install Claude Code via npm (if not already installed)
2. Rename the compiled binary so the patchable npm version takes priority (Windows)
3. Patch the spinner in both VS Code webview and CLI

## Usage

```bash
# Full setup (first time)
node setup.js

# Re-apply patch (after Claude Code updates)
node patch-parrot.js

# Restore original spinners
node patch-parrot.js --restore

# Full uninstall (restore everything)
node uninstall.js
```

Or with npm scripts:

```bash
npm run setup       # Full setup
npm run patch       # Re-apply patch
npm run restore     # Restore originals
npm run uninstall   # Full uninstall
```

## How it works

Claude Code's thinking animation uses an array of Unicode symbols (`·`, `✢`, `*`, `✶`, `✻`, `✽`) that cycle while the AI is processing. This tool:

1. **Finds** the Claude Code installation (VS Code extension + npm CLI)
2. **Backs up** the original files (`.parrot-backup`)
3. **Replaces** the spinner symbol arrays with rainbow-colored parrot emoji frames
4. For the **CLI**: uses ANSI true-color escape codes for smooth rainbow cycling
5. For **VS Code**: uses colored emoji squares paired with the parrot

### Files patched

| Target | File | What changes |
|--------|------|-------------|
| VS Code | `~/.vscode/extensions/anthropic.claude-code-*/webview/index.js` | Spinner symbol arrays + animation speed |
| CLI | `%APPDATA%/npm/node_modules/@anthropic-ai/claude-code/cli.js` | Spinner function returns parrot frames |

## After Claude Code updates

Claude Code updates will overwrite the patched files. Just re-run:

```bash
node patch-parrot.js
```

The setup script only needs to run once. After that, `patch-parrot.js` is enough.

## Uninstall

```bash
node uninstall.js
```

This restores all backed-up files and renames `claude-original.exe` back to `claude.exe`.

## License

MIT
