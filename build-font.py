#!/usr/bin/env python3
"""
Funny Terminal — GIF to COLR Font Builder

Converts any GIF animation into a color font (COLR/CPAL v0) for use as
a custom spinner in Claude Code (or any terminal app).

Workflow:
  1. Drop a .gif in gifs/ (or set sourceGif in config.json)
  2. Run: python build-font.py
  3. Install the output .ttf font
  4. Run: node scripts/patch-claude.js

Config: config.json (auto-created from config.example.json on first run)
"""

import os
import io
import json
import glob
import shutil
from PIL import Image
from fontTools.ttLib import TTFont, newTable
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.colorLib.builder import buildCOLR, buildCPAL

NUM_FRAMES = 10  # fixed: 10 frames per animation

# ── Load config ─────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")
EXAMPLE_PATH = os.path.join(SCRIPT_DIR, "config.example.json")

if not os.path.exists(CONFIG_PATH):
    shutil.copy(EXAMPLE_PATH, CONFIG_PATH)
    print(f"  Created config.json from config.example.json")
    print(f"  Edit it to customize, then re-run.\n")

with open(CONFIG_PATH, "r") as f:
    raw = json.load(f)
    cfg = {k: v for k, v in raw.items() if not k.startswith("//")}

GRID_W = cfg.get("gridWidth", 20)
GRID_H = cfg.get("gridHeight", 20)
CELL_ASPECT = cfg.get("cellAspectRatio", 0.55)
ALPHA_THRESHOLD = cfg.get("alphaThreshold", 140)
RESAMPLE = cfg.get("resample", "nearest")
MAX_COLORS = cfg.get("maxColorsPerFrame", 0)
DARK_THRESHOLD = cfg.get("darkThreshold", 0)
LIGHT_THRESHOLD = cfg.get("lightThreshold", 0)
V_OFFSET = cfg.get("verticalOffset", 0)
H_PADDING = cfg.get("horizontalPadding", 0)
SOURCE_GIF = cfg.get("sourceGif", "")

RESAMPLE_METHOD = Image.NEAREST if RESAMPLE == "nearest" else Image.LANCZOS
BASE_FONT = cfg.get("baseFont", "C:/Windows/Fonts/CascadiaMono.ttf")
FONT_NAME = cfg.get("fontName", "Funny Terminal")
FONT_NAME_INTERNAL = cfg.get("fontNameInternal", "FunnyTerminal")
OUTPUT = os.path.join(SCRIPT_DIR, cfg.get("output", "FunnyTerminal.ttf"))
FRAME_DIR = os.path.join(SCRIPT_DIR, cfg.get("frameDir", "frames"))
FIRST_CP = int(cfg.get("firstCodepoint", "0xE000"), 16) if isinstance(cfg.get("firstCodepoint"), str) else cfg.get("firstCodepoint", 0xE000)

CODEPOINTS = {FIRST_CP + i: f"frame{i:02d}" for i in range(NUM_FRAMES)}


# ── GIF frame extraction ────────────────────────────────────────────

def find_gif():
    """Find source GIF: config path > auto-detect in project root."""
    if SOURCE_GIF and os.path.isfile(os.path.join(SCRIPT_DIR, SOURCE_GIF)):
        return os.path.join(SCRIPT_DIR, SOURCE_GIF)
    if SOURCE_GIF and os.path.isfile(SOURCE_GIF):
        return SOURCE_GIF

    # Auto-detect any .gif in gifs/ folder or project root
    gifs = glob.glob(os.path.join(SCRIPT_DIR, "gifs", "*.gif"))
    if not gifs:
        gifs = glob.glob(os.path.join(SCRIPT_DIR, "*.gif"))
    if len(gifs) == 1:
        return gifs[0]
    elif len(gifs) > 1:
        print(f"  Found {len(gifs)} GIF files — set 'sourceGif' in config.json to pick one:")
        for g in gifs:
            print(f"    {os.path.basename(g)}")
        return None
    return None


def extract_frames_from_gif(gif_path):
    """Extract exactly NUM_FRAMES evenly sampled frames from a GIF."""
    print(f"  Source GIF: {os.path.basename(gif_path)}")

    gif = Image.open(gif_path)
    total_frames = 0
    try:
        while True:
            total_frames += 1
            gif.seek(gif.tell() + 1)
    except EOFError:
        pass

    print(f"  GIF has {total_frames} frames, sampling {NUM_FRAMES}...")

    # Evenly sample NUM_FRAMES indices
    if total_frames <= NUM_FRAMES:
        indices = list(range(total_frames))
        # Pad with last frame if GIF has fewer frames
        while len(indices) < NUM_FRAMES:
            indices.append(total_frames - 1)
    else:
        indices = [int(i * total_frames / NUM_FRAMES) for i in range(NUM_FRAMES)]

    os.makedirs(FRAME_DIR, exist_ok=True)

    for out_idx, gif_idx in enumerate(indices):
        gif.seek(gif_idx)
        frame = gif.convert("RGBA")
        frame_path = os.path.join(FRAME_DIR, f"frame_{out_idx:02d}.png")
        frame.save(frame_path)

    print(f"  Extracted {NUM_FRAMES} frames to {FRAME_DIR}/")
    return NUM_FRAMES


# ── Image processing ────────────────────────────────────────────────

def crop_to_content(img):
    bbox = img.getbbox()
    return img.crop(bbox) if bbox else img


# ── Font building ───────────────────────────────────────────────────

def build_font():
    # ── Step 1: Ensure frames exist ──
    gif_path = find_gif()
    existing_frames = sorted(glob.glob(os.path.join(FRAME_DIR, "frame_*.png")))

    if gif_path:
        extract_frames_from_gif(gif_path)
    elif existing_frames:
        print(f"  Using existing frames in {FRAME_DIR}/ ({len(existing_frames)} found)")
    else:
        print("  Error: No GIF found and no frames/ directory.")
        print("  Drop a .gif in gifs/, or set 'sourceGif' in config.json")
        return

    # Recount frames after extraction
    frame_files = sorted(glob.glob(os.path.join(FRAME_DIR, "frame_*.png")))
    num_frames = min(len(frame_files), NUM_FRAMES)
    codepoints = {FIRST_CP + i: f"frame{i:02d}" for i in range(num_frames)}

    # ── Step 2: Build font ──
    print(f"  Base font: {BASE_FONT}")
    font = TTFont(BASE_FONT)

    ascent = font["OS/2"].sTypoAscender
    descent = font["OS/2"].sTypoDescender
    advance_w = font["hmtx"]["space"][0]
    em_height = ascent - descent

    pixel_w = advance_w // GRID_W
    pixel_h = (em_height - 100) // GRID_H
    grid_h_total = GRID_H * pixel_h
    y_top = ascent - (em_height - grid_h_total) // 2 + V_OFFSET * pixel_h

    print(f"  Grid: {GRID_W}x{GRID_H}, pixel={pixel_w}x{pixel_h} units")
    print(f"  Font name: {FONT_NAME}")

    # ── Rename font ──
    base_family = None
    for record in font["name"].names:
        try:
            text = record.toUnicode()
        except:
            continue
        if record.nameID == 1 and base_family is None:
            base_family = text.strip()

    if base_family:
        base_internal = base_family.replace(" ", "")
        for record in font["name"].names:
            try:
                text = record.toUnicode()
            except:
                continue
            if base_family in text:
                record.string = text.replace(base_family, FONT_NAME)
            elif base_internal in text:
                record.string = text.replace(base_internal, FONT_NAME_INTERNAL)

    # ── Add base glyphs with full-cell bbox ──
    glyph_order = font.getGlyphOrder()

    for cp, name in sorted(codepoints.items()):
        if name not in glyph_order:
            glyph_order.append(name)
            pen = TTGlyphPen(None)
            pen.moveTo((0, descent))
            pen.lineTo((advance_w, descent))
            pen.lineTo((advance_w, ascent))
            pen.lineTo((0, ascent))
            pen.closePath()
            font["glyf"][name] = pen.glyph()
            font["hmtx"][name] = (advance_w, 0)

    # ── Process frames and build COLR layers ──
    all_colors = []
    color_map = {}
    color_layers = {}

    for i in range(num_frames):
        frame_path = os.path.join(FRAME_DIR, f"frame_{i:02d}.png")
        img = Image.open(frame_path).convert("RGBA")
        img = crop_to_content(img)

        # Aspect-corrected resize
        content_w, content_h = img.size
        img_aspect = content_w / content_h
        correct_rows = int(GRID_W / img_aspect / CELL_ASPECT)
        correct_rows = min(correct_rows, GRID_H)
        img = img.resize((GRID_W, correct_rows), RESAMPLE_METHOD)
        if correct_rows < GRID_H:
            padded = Image.new("RGBA", (GRID_W, GRID_H), (0, 0, 0, 0))
            padded.paste(img, (0, GRID_H - correct_rows))
            img = padded

        # Quantize colors
        if MAX_COLORS > 0:
            alpha = img.split()[3]
            rgb = img.convert("RGB")
            rgb = rgb.quantize(colors=MAX_COLORS, method=Image.Quantize.MEDIANCUT).convert("RGB")
            img = rgb.convert("RGBA")
            img.putalpha(alpha)

        # Group pixels by color
        color_pixels = {}
        for r in range(GRID_H):
            for c in range(GRID_W):
                if H_PADDING > 0 and (c < H_PADDING or c >= GRID_W - H_PADDING):
                    continue
                rgba = img.getpixel((c, r))
                if rgba[3] < ALPHA_THRESHOLD:
                    continue
                rgb = (rgba[0], rgba[1], rgba[2])
                if DARK_THRESHOLD > 0 and sum(rgb) < DARK_THRESHOLD:
                    continue
                if LIGHT_THRESHOLD > 0 and min(rgb) > LIGHT_THRESHOLD:
                    continue
                if rgb not in color_pixels:
                    color_pixels[rgb] = []
                color_pixels[rgb].append((r, c))

        # Create one layer glyph per color (with anchors + bleed)
        layers = []
        for rgb, pixels in color_pixels.items():
            if rgb not in color_map:
                color_map[rgb] = len(all_colors)
                all_colors.append(rgb + (255,))

            glyph_name = f"f{i}_c{color_map[rgb]}"
            glyph_order.append(glyph_name)

            pen = TTGlyphPen(None)

            # Invisible anchors to force full-width bbox
            anchor_y = descent - 100
            pen.moveTo((0, anchor_y))
            pen.lineTo((1, anchor_y))
            pen.lineTo((1, anchor_y + 1))
            pen.lineTo((0, anchor_y + 1))
            pen.closePath()
            pen.moveTo((advance_w - 1, anchor_y))
            pen.lineTo((advance_w, anchor_y))
            pen.lineTo((advance_w, anchor_y + 1))
            pen.lineTo((advance_w - 1, anchor_y + 1))
            pen.closePath()

            # Draw colored rectangles with bleed
            bleed = 2
            for (r, c) in pixels:
                x0 = max(0, c * pixel_w - bleed)
                x1 = min(advance_w, (c + 1) * pixel_w + bleed)
                y1_pos = min(ascent, y_top - r * pixel_h + bleed)
                y0_pos = max(descent, y_top - (r + 1) * pixel_h - bleed)
                pen.moveTo((x0, y0_pos))
                pen.lineTo((x1, y0_pos))
                pen.lineTo((x1, y1_pos))
                pen.lineTo((x0, y1_pos))
                pen.closePath()

            font["glyf"][glyph_name] = pen.glyph()
            font["hmtx"][glyph_name] = (advance_w, 0)
            layers.append((glyph_name, color_map[rgb]))

        color_layers[f"frame{i:02d}"] = layers
        print(f"  frame_{i:02d}: {sum(len(v) for v in color_pixels.values())} px, {len(color_pixels)} colors")

    font.setGlyphOrder(glyph_order)
    font["maxp"].numGlyphs = len(glyph_order)

    # Update cmap
    for subtable in font["cmap"].tables:
        if hasattr(subtable, "cmap") and subtable.cmap is not None:
            for cp, name in codepoints.items():
                subtable.cmap[cp] = name

    # ── Build COLR/CPAL ──
    total_layers = sum(len(v) for v in color_layers.values())
    print(f"  Building COLR v0: {total_layers} layers, {len(all_colors)} colors...")
    font["COLR"] = buildCOLR(color_layers)
    normalized = [(r/255, g/255, b/255, a/255) for r, g, b, a in all_colors]
    font["CPAL"] = buildCPAL([normalized])

    font.save(OUTPUT)
    print()
    print(f"  Built: {OUTPUT}")
    print(f"  Font: {FONT_NAME} ({num_frames} frames, {GRID_W}x{GRID_H} pixel art)")
    print(f"  COLR: {total_layers} layers, {len(all_colors)} palette colors")

    # ── Generate preview HTML ──
    write_preview_html(os.path.basename(OUTPUT), num_frames)

    print()
    print(f"  Next steps:")
    print(f"  1. Install: double-click {os.path.basename(OUTPUT)}")
    print(f'  2. Set terminal font to "{FONT_NAME}"')
    print(f"  3. Patch Claude: node scripts/patch-claude.js")
    print(f"  4. Preview: open test-colr-diag.html in browser")


def write_preview_html(font_file, num_frames):
    chars_raw = "".join(chr(FIRST_CP + i) for i in range(num_frames))
    chars_spaced_raw = " ".join(chr(FIRST_CP + i) for i in range(num_frames))

    html = f'''<!DOCTYPE html>
<html>
<head>
<style>
@font-face {{ font-family: "FunnyTerminal"; src: url("{font_file}"); }}
body {{ background: #1a1a2e; color: white; padding: 40px; font-family: sans-serif; }}
.p {{ font-family: "FunnyTerminal"; }}
</style>
</head>
<body>
<h2>Funny Terminal Preview — {GRID_W}x{GRID_H} grid</h2>
<p>120px — all {num_frames} frames:</p>
<div class="p" style="font-size:120px">{chars_raw}</div>
<p>120px — spaced:</p>
<div class="p" style="font-size:120px">{chars_spaced_raw}</div>
<p>48px:</p>
<div class="p" style="font-size:48px">{chars_spaced_raw}</div>
<p>24px (terminal-ish):</p>
<div class="p" style="font-size:24px">{chars_spaced_raw}</div>
<hr style="margin-top:40px;border-color:#333">
<p style="color:#888;font-size:14px">Made with <a href="https://github.com/Arystos/funny-terminal" style="color:#8073f5">Funny Terminal</a></p>
<script type="text/javascript" src="https://storage.ko-fi.com/cdn/widget/Widget_2.js"></script>
<script type="text/javascript">kofiwidget2.init('Support me on Ko-fi', '#8073f5', 'U7U71W5S5I');kofiwidget2.draw();</script>
</body>
</html>'''

    preview_path = os.path.join(SCRIPT_DIR, "test-colr-diag.html")
    with open(preview_path, "w", encoding="utf-8") as f:
        f.write(html)


if __name__ == "__main__":
    build_font()
