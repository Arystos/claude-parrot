# Funny Terminal

Turn any GIF into an animated pixel art spinner for Claude Code. Replace the boring `· ✢ * ✶ ✻ ✽` thinking spinner with your own custom animation — a party parrot, Nyan Cat, a spinning globe, whatever you want.

**How it works:** Your GIF is converted into a color font (OpenType COLR/CPAL) where each animation frame is a glyph. Claude Code's spinner is patched to cycle through these glyphs, and your terminal font renders them as pixel art.

![Party Parrot Example](https://img.shields.io/badge/Party_Parrot-🦜-green)

[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support%20this%20project-FF5E5B?logo=ko-fi&logoColor=white)](https://ko-fi.com/arystos)

## Prerequisites

- [Python 3.10+](https://python.org) with `Pillow` and `fonttools` (`pip install Pillow fonttools`)
- [Node.js 18+](https://nodejs.org)
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed (VS Code extension or npm)
- Windows Terminal (or any terminal that supports COLR color fonts)

## Quick Start

```bash
git clone https://github.com/AristideBH/funny-terminal.git
cd funny-terminal

# 1. Drop your GIF in gifs/ (a party parrot is included as default)

# 2. Build the font
python build-font.py

# 3. Install the font — double-click the .ttf file, or:
#    (Windows) Right-click → Install for all users

# 4. Set your terminal font to "Funny Terminal" (or the name in your config)
#    Windows Terminal: Settings → Profiles → Defaults → Font face

# 5. Patch Claude Code's spinner
node scripts/patch-claude.js

# 6. Launch Claude Code — enjoy your custom spinner!
claude
```

## Using Your Own GIF

1. Delete the default GIF from `gifs/` (or keep it — the tool auto-detects)
2. Drop any `.gif` in the `gifs/` folder
3. Run `python build-font.py`
4. Reinstall the font and restart your terminal

The tool automatically extracts 10 evenly-spaced frames from your GIF, converts them to pixel art, and builds a color font.

> **Tip:** GIFs with a transparent background and a simple subject work best. Complex GIFs with many colors may need tuning (see Configuration below).

## Configuration

On first run, `build-font.py` creates `config.json` from `config.example.json`. Edit it to customize:

### Image Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `sourceGif` | `""` | Path to GIF. Empty = auto-detect in `gifs/` |
| `gridWidth` | `20` | Pixel art columns. More = finer detail |
| `gridHeight` | `20` | Pixel art rows. More = finer detail |
| `cellAspectRatio` | `0.55` | Terminal cell width:height ratio. Adjust if animation looks stretched |
| `resample` | `"nearest"` | `"nearest"` for sharp pixels, `"lanczos"` for smooth |
| `maxColorsPerFrame` | `16` | Color limit per frame. Lower = bolder, fewer font layers |

### Cleanup Filters

| Setting | Default | Description |
|---------|---------|-------------|
| `alphaThreshold` | `140` | Pixels with alpha below this become transparent |
| `darkThreshold` | `80` | Remove near-black pixels (RGB sum below this) |
| `lightThreshold` | `200` | Remove near-white stray pixels (min RGB above this) |

### Positioning

| Setting | Default | Description |
|---------|---------|-------------|
| `verticalOffset` | `0` | Shift animation up (+) or down (-) in grid rows |
| `horizontalPadding` | `0` | Remove columns from each side |

### Font Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `baseFont` | `"C:/Windows/Fonts/CascadiaMono.ttf"` | Monospace font to merge glyphs into |
| `fontName` | `"Funny Terminal"` | Font family name (set this in terminal settings) |
| `output` | `"FunnyTerminal.ttf"` | Output font filename |

### Advanced

| Setting | Default | Description |
|---------|---------|-------------|
| `frameDir` | `"frames"` | Directory for extracted frame PNGs |
| `firstCodepoint` | `"0xE000"` | First Unicode Private Use Area codepoint |

## Browser Preview

After building, open `test-colr-diag.html` in your browser to preview the animation at different sizes without installing the font.

## Project Structure

```
funny-terminal/
├── build-font.py           # Main tool — GIF → color font
├── config.example.json     # Default config template
├── package.json
├── README.md
├── gifs/                   # Drop your GIF here
│   └── partyparrt-21.gif   # Default party parrot
├── scripts/
│   ├── patch-claude.js     # Patch/restore Claude Code spinner
│   ├── preview.js          # Terminal spinner preview
│   └── install-font.ps1   # Windows font install helper (admin)
├── frames/                 # Auto-generated from GIF (gitignored)
├── config.json             # Your local config (gitignored)
└── *.ttf                   # Built font (gitignored)
```

## Commands Reference

```bash
# Build the font (extracts GIF frames + generates font + preview HTML)
python build-font.py

# Patch Claude Code spinner
node scripts/patch-claude.js

# Restore original Claude Code spinner
node scripts/patch-claude.js --restore

# Preview spinner in terminal (requires font installed + terminal font set)
node scripts/preview.js
```

## Troubleshooting

**Parrot looks stretched/squished:** Adjust `cellAspectRatio` in `config.json`. Lower values (0.4–0.5) for narrow terminal cells, higher (0.6–1.0) for wider cells.

**Stray white/gray pixels around the edges:** Increase `alphaThreshold` (try 160–200) and `lightThreshold` (try 150–180).

**Too many colors / large font file:** Set `maxColorsPerFrame` to 8–16 and use `resample: "nearest"`.

**Font not showing in terminal:** Make sure the terminal font is set to the name in your `config.json` (`fontName`). Restart the terminal after installing the font.

**Patch says "no patterns matched":** Claude Code may have updated. Run `node scripts/patch-claude.js --restore` first, then re-patch. If patterns have changed in a new Claude Code version, the regex in `patch-claude.js` may need updating.

**Multiple GIFs in gifs/ folder:** Set `sourceGif` in `config.json` to the filename you want (e.g. `"gifs/nyancat.gif"`).

## How It Works (Technical)

1. **Frame extraction:** The GIF is sampled to exactly 10 frames using Pillow
2. **Pixel art conversion:** Each frame is cropped to content, aspect-corrected, and resized to the grid (e.g. 20×20) using nearest-neighbor sampling
3. **Color font building:** Using fonttools, the pixel art is embedded as COLR/CPAL v0 glyphs in a copy of your base monospace font. Each unique color per frame becomes a layer glyph with colored rectangles
4. **Key trick:** Layer glyphs include invisible anchor contours at x=0 and x=advance_width to prevent DirectWrite from repositioning layers (a rendering quirk we discovered the hard way)
5. **Patching:** The spinner function in Claude Code's bundled JS is regex-matched and replaced with an array of Unicode Private Use Area characters that map to the font glyphs

## Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b my-feature`)
3. Make your changes
4. Test with `python build-font.py` and verify the preview HTML
5. Commit (`git commit -m "Add my feature"`)
6. Push and open a PR

**Ideas for contributions:**
- macOS / Linux font install scripts
- More GIF examples in `gifs/`
- Higher resolution grid support (COLR v1 with gradient fills)
- Auto-patching on Claude Code updates (file watcher)
- Support for other terminal apps beyond Claude Code

## After Claude Code Updates

Claude Code updates overwrite the patched files. Re-run:

```bash
node scripts/patch-claude.js
```

## Support

If you enjoy this project, consider buying me a coffee!

[![Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/arystos)

## License

MIT
