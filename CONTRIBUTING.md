# Contributing to Claude Parrot

Thanks for your interest in contributing! Here's how to get started.

## How to Contribute

1. **Fork** the repo
2. **Create a branch** from `master` (`git checkout -b my-feature`)
3. **Make your changes**
4. **Test** — run `python build-font.py` and check the preview HTML
5. **Commit** with a clear message
6. **Push** and open a **Pull Request**

## What to Contribute

- **New GIF examples** — drop them in `gifs/` with a descriptive name
- **Bug fixes** — if something doesn't work, fix it and open a PR
- **Platform support** — macOS/Linux font install scripts, other terminals
- **Documentation** — improve the README, add screenshots, write guides
- **Config presets** — share your fine-tuned config for specific GIFs

## Guidelines

- Keep it simple — this is a fun project, not enterprise software
- Test your changes before opening a PR
- One feature per PR — don't bundle unrelated changes
- Be respectful in issues and discussions

## Issue Labels

When opening an issue, add the relevant label so it's easy to triage:

| Label | Use for |
|-------|---------|
| `bug` | Something isn't working |
| `enhancement` | Feature requests and suggestions |
| `question` | Need help or clarification |
| `gif-request` | Requesting a new GIF/animation |
| `config` | Config tuning or settings help |
| `font-rendering` | Color font display issues |
| `patching` | Claude Code patcher issues |
| `windows` / `macos` / `linux` | Platform-specific issues |
| `good first issue` | Easy tasks for newcomers |
| `fun` | Just for fun — not useful, just funny |

## Reporting Bugs

Open an issue with:
- What you expected to happen
- What actually happened
- Your OS, terminal, and Python/Node versions
- Your `config.json` (if relevant)

## Feature Requests

Open an issue describing what you'd like and why. Keep it focused.

## Roadmap

Currently **Windows only**. Help us bring Claude Parrot to other platforms!

### macOS Support
- [ ] Font install script (`scripts/install-font-mac.sh`) — copy to `~/Library/Fonts/`
- [ ] Update `config.example.json` with macOS default font path (e.g. `/System/Library/Fonts/SFMono-Regular.otf` or Menlo)
- [ ] Test COLR/CPAL rendering in macOS Terminal, iTerm2, and Alacritty
- [ ] Update `patch-claude.js` to find Claude Code on macOS (`~/.npm-global/` or `/usr/local/lib/`)

### Linux Support
- [ ] Font install script (`scripts/install-font-linux.sh`) — copy to `~/.local/share/fonts/` + `fc-cache`
- [ ] Update `config.example.json` with Linux default font paths (e.g. `/usr/share/fonts/truetype/dejavu/`)
- [ ] Test COLR/CPAL rendering in GNOME Terminal, Konsole, Alacritty, kitty
- [ ] Update `patch-claude.js` to find Claude Code on Linux

### General
- [ ] Auto-detect OS and use platform-appropriate defaults in `build-font.py`
- [ ] More GIF examples in `gifs/`
- [ ] Gallery of community-submitted animations in README

Pick any unchecked item, open a PR, and help us get there!

## Questions?

Open an issue — happy to help!
