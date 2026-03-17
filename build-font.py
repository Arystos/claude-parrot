#!/usr/bin/env python3
"""
Claude Parrot — GIF to COLR Font Builder

Converts any GIF animation into a color font (COLR/CPAL v0) for use as
a custom spinner in Claude Code (or any terminal app).

Workflow:
  1. Drop .gif files in gifs/ (or set gifList/sourceGif in config.json)
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
GIF_LIST = cfg.get("gifList", [])
ROTATION = cfg.get("rotation", "sequential")

DISPLAY_COLS = cfg.get("displayCols", 1)
RESAMPLE_METHOD = Image.NEAREST if RESAMPLE == "nearest" else Image.LANCZOS
BASE_FONT = cfg.get("baseFont", "C:/Windows/Fonts/CascadiaMono.ttf")
FONT_NAME = cfg.get("fontName", "Claude Parrot")
FONT_NAME_INTERNAL = cfg.get("fontNameInternal", "ClaudeParrot")
OUTPUT = os.path.join(SCRIPT_DIR, cfg.get("output", "ClaudeParrot.ttf"))
FRAME_DIR = os.path.join(SCRIPT_DIR, cfg.get("frameDir", "frames"))
FIRST_CP = int(cfg.get("firstCodepoint", "0xE000"), 16) if isinstance(cfg.get("firstCodepoint"), str) else cfg.get("firstCodepoint", 0xE000)

# With multi-cell, each frame uses DISPLAY_COLS codepoints (one per column slice)
GLYPHS_PER_FRAME = DISPLAY_COLS
# Codepoints per GIF
CPS_PER_GIF = NUM_FRAMES * GLYPHS_PER_FRAME


# ── GIF discovery ──────────────────────────────────────────────────

def find_gifs():
    """Find all source GIFs: from gifList config, sourceGif config, or auto-detect in gifs/."""
    if GIF_LIST:
        found = []
        for name in GIF_LIST:
            p = os.path.join(SCRIPT_DIR, "gifs", name)
            if os.path.isfile(p):
                found.append(p)
            elif os.path.isfile(os.path.join(SCRIPT_DIR, name)):
                found.append(os.path.join(SCRIPT_DIR, name))
            else:
                print(f"  Warning: GIF not found: {name}")
        return found
    # Backward compat: sourceGif
    if SOURCE_GIF:
        p = os.path.join(SCRIPT_DIR, SOURCE_GIF) if not os.path.isfile(SOURCE_GIF) else SOURCE_GIF
        if os.path.isfile(p):
            return [p]
    # Auto-detect all GIFs in gifs/ folder, falling back to project root
    gifs = sorted(glob.glob(os.path.join(SCRIPT_DIR, "gifs", "*.gif")))
    if not gifs:
        gifs = sorted(glob.glob(os.path.join(SCRIPT_DIR, "*.gif")))
    return gifs


# ── GIF frame extraction ────────────────────────────────────────────

def extract_frames_from_gif(gif_path, output_dir):
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

    os.makedirs(output_dir, exist_ok=True)

    for out_idx, gif_idx in enumerate(indices):
        gif.seek(gif_idx)
        frame = gif.convert("RGBA")
        frame_path = os.path.join(output_dir, f"frame_{out_idx:02d}.png")
        frame.save(frame_path)

    print(f"  Extracted {NUM_FRAMES} frames to {output_dir}/")
    return NUM_FRAMES


# ── Image processing ────────────────────────────────────────────────

def crop_to_content(img):
    bbox = img.getbbox()
    return img.crop(bbox) if bbox else img


# ── Font building ───────────────────────────────────────────────────

def build_font():
    # ── Step 1: Find GIFs ──
    gif_paths = find_gifs()

    if not gif_paths:
        # Check for pre-existing frames in legacy flat layout
        existing_frames = sorted(glob.glob(os.path.join(FRAME_DIR, "frame_*.png")))
        if existing_frames:
            print(f"  Using existing frames in {FRAME_DIR}/ ({len(existing_frames)} found)")
            # Treat as single anonymous GIF with pre-extracted frames
            gif_paths = []
            gif_infos = [{"name": "frames", "frame_dir": FRAME_DIR}]
        else:
            print("  Error: No GIF found and no frames/ directory.")
            print("  Drop a .gif in gifs/, or set 'sourceGif' in config.json")
            return
    else:
        gif_infos = None  # will be built below

    # ── Step 1b: Extract frames for each GIF ──
    if gif_infos is None:
        gif_infos = []
        for gif_path in gif_paths:
            gif_basename = os.path.splitext(os.path.basename(gif_path))[0]
            if len(gif_paths) == 1:
                # Single GIF: use flat frames/ dir for backward compatibility
                output_dir = FRAME_DIR
            else:
                output_dir = os.path.join(FRAME_DIR, gif_basename)
            extract_frames_from_gif(gif_path, output_dir)
            gif_infos.append({"name": gif_basename, "frame_dir": output_dir})

    num_gifs = len(gif_infos)
    print(f"  Processing {num_gifs} GIF(s)...")

    # Build codepoints for ALL GIFs
    codepoints = {}
    for gif_idx, info in enumerate(gif_infos):
        gif_first_cp = FIRST_CP + gif_idx * CPS_PER_GIF
        frame_dir = info["frame_dir"]
        frame_files = sorted(glob.glob(os.path.join(frame_dir, "frame_*.png")))
        num_frames = min(len(frame_files), NUM_FRAMES)
        info["num_frames"] = num_frames
        info["first_cp"] = gif_first_cp

        for i in range(num_frames):
            for col in range(GLYPHS_PER_FRAME):
                cp = gif_first_cp + i * GLYPHS_PER_FRAME + col
                glyph_name = f"g{gif_idx}_frame{i:02d}_c{col}" if num_gifs > 1 else (
                    f"frame{i:02d}_c{col}" if GLYPHS_PER_FRAME > 1 else f"frame{i:02d}"
                )
                codepoints[cp] = glyph_name

    # ── Step 2: Build font ──
    print(f"  Base font: {BASE_FONT}")
    font = TTFont(BASE_FONT)

    ascent = font["OS/2"].sTypoAscender
    descent = font["OS/2"].sTypoDescender
    advance_w = font["hmtx"]["space"][0]
    em_height = ascent - descent

    # Total grid spans DISPLAY_COLS cells worth of width
    total_grid_w = GRID_W * DISPLAY_COLS
    pixel_w = advance_w // GRID_W
    pixel_h = (em_height - 100) // GRID_H
    grid_h_total = GRID_H * pixel_h
    y_top = ascent - (em_height - grid_h_total) // 2 + V_OFFSET * pixel_h

    if DISPLAY_COLS > 1:
        print(f"  Multi-cell: {DISPLAY_COLS} columns ({total_grid_w}x{GRID_H} total grid)")
    print(f"  Grid per cell: {GRID_W}x{GRID_H}, pixel={pixel_w}x{pixel_h} units")
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

    # ── Add base glyphs with bbox (extended at slice boundaries for seam coverage) ──
    glyph_order = font.getGlyphOrder()
    edge_bleed = pixel_w // 2 if GLYPHS_PER_FRAME > 1 else 0

    for cp, name in sorted(codepoints.items()):
        if name not in glyph_order:
            glyph_order.append(name)
            # Determine which slice this glyph is (by position in its frame)
            idx_in_frame = (cp - FIRST_CP) % GLYPHS_PER_FRAME
            # Extend bbox past cell boundary at slice edges so COLR layers aren't clipped
            x_min = -edge_bleed if idx_in_frame > 0 else 0
            x_max = advance_w + edge_bleed if idx_in_frame < GLYPHS_PER_FRAME - 1 else advance_w
            pen = TTGlyphPen(None)
            pen.moveTo((x_min, descent))
            pen.lineTo((x_max, descent))
            pen.lineTo((x_max, ascent))
            pen.lineTo((x_min, ascent))
            pen.closePath()
            font["glyf"][name] = pen.glyph()
            font["hmtx"][name] = (advance_w, 0)

    # ── Process frames and build COLR layers ──
    all_colors = []
    color_map = {}
    color_layers = {}

    for gif_idx, info in enumerate(gif_infos):
        gif_name = info["name"]
        frame_dir = info["frame_dir"]
        num_frames = info["num_frames"]

        if num_gifs > 1:
            print(f"  --- {gif_name} (GIF {gif_idx + 1}/{num_gifs}) ---")

        for i in range(num_frames):
            frame_path = os.path.join(frame_dir, f"frame_{i:02d}.png")
            img = Image.open(frame_path).convert("RGBA")
            img = crop_to_content(img)

            # Aspect-corrected resize to total grid (spans DISPLAY_COLS cells)
            content_w, content_h = img.size
            img_aspect = content_w / content_h
            correct_rows = int(total_grid_w / img_aspect / CELL_ASPECT)
            correct_rows = min(correct_rows, GRID_H)
            img = img.resize((total_grid_w, correct_rows), RESAMPLE_METHOD)
            if correct_rows < GRID_H:
                padded = Image.new("RGBA", (total_grid_w, GRID_H), (0, 0, 0, 0))
                padded.paste(img, (0, GRID_H - correct_rows))
                img = padded

            # Quantize colors
            if MAX_COLORS > 0:
                alpha = img.split()[3]
                rgb = img.convert("RGB")
                rgb = rgb.quantize(colors=MAX_COLORS, method=Image.Quantize.MEDIANCUT).convert("RGB")
                img = rgb.convert("RGBA")
                img.putalpha(alpha)

            # For each column slice, group pixels by color and build layers
            for col_slice in range(GLYPHS_PER_FRAME):
                col_start = col_slice * GRID_W
                col_end = col_start + GRID_W
                slice_name = f"g{gif_idx}_frame{i:02d}_c{col_slice}" if num_gifs > 1 else (
                    f"frame{i:02d}_c{col_slice}" if GLYPHS_PER_FRAME > 1 else f"frame{i:02d}"
                )

                # Group pixels by color within this slice
                color_pixels = {}
                for r in range(GRID_H):
                    for c in range(col_start, col_end):
                        if H_PADDING > 0:
                            local_c = c - col_start
                            if local_c < H_PADDING or local_c >= GRID_W - H_PADDING:
                                continue
                        rgba = img.getpixel((c, r))
                        if rgba[3] < ALPHA_THRESHOLD:
                            continue
                        rgb_val = (rgba[0], rgba[1], rgba[2])
                        if DARK_THRESHOLD > 0 and sum(rgb_val) < DARK_THRESHOLD:
                            continue
                        if LIGHT_THRESHOLD > 0 and min(rgb_val) > LIGHT_THRESHOLD:
                            continue
                        if rgb_val not in color_pixels:
                            color_pixels[rgb_val] = []
                        # Store local column (within this cell)
                        color_pixels[rgb_val].append((r, c - col_start))

                # Create one layer glyph per color (with anchors + bleed)
                layers = []
                for rgb_val, pixels in color_pixels.items():
                    if rgb_val not in color_map:
                        color_map[rgb_val] = len(all_colors)
                        all_colors.append(rgb_val + (255,))

                    # Unique glyph name across all GIFs
                    glyph_name = f"g{gif_idx}_f{i}_s{col_slice}_c{color_map[rgb_val]}"
                    glyph_order.append(glyph_name)

                    pen = TTGlyphPen(None)

                    # Invisible anchors to force bbox (extended at slice edges)
                    anchor_y = descent - 100
                    anchor_left = -edge_bleed if col_slice > 0 else 0
                    anchor_right = advance_w + edge_bleed if col_slice < GLYPHS_PER_FRAME - 1 else advance_w
                    pen.moveTo((anchor_left, anchor_y))
                    pen.lineTo((anchor_left + 1, anchor_y))
                    pen.lineTo((anchor_left + 1, anchor_y + 1))
                    pen.lineTo((anchor_left, anchor_y + 1))
                    pen.closePath()
                    pen.moveTo((anchor_right - 1, anchor_y))
                    pen.lineTo((anchor_right, anchor_y))
                    pen.lineTo((anchor_right, anchor_y + 1))
                    pen.lineTo((anchor_right - 1, anchor_y + 1))
                    pen.closePath()

                    # Draw colored rectangles with bleed
                    bleed = 2
                    # Extra bleed at slice edges to cover inter-glyph seams
                    edge_bleed = pixel_w // 2 if GLYPHS_PER_FRAME > 1 else 0
                    for (r, c) in pixels:
                        # At left edge of non-first slice, extend left past 0
                        if c == 0 and col_slice > 0:
                            x0 = -edge_bleed
                        else:
                            x0 = max(0, c * pixel_w - bleed)
                        # At right edge of non-last slice, extend right past advance_w
                        if c == GRID_W - 1 and col_slice < GLYPHS_PER_FRAME - 1:
                            x1 = advance_w + edge_bleed
                        else:
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
                    layers.append((glyph_name, color_map[rgb_val]))

                color_layers[slice_name] = layers

            # Build the slice name pattern for layer count reporting
            total_slice_layers = sum(len(color_layers.get(
                f"g{gif_idx}_frame{i:02d}_c{col_s}" if num_gifs > 1 else (
                    f"frame{i:02d}_c{col_s}" if GLYPHS_PER_FRAME > 1 else f"frame{i:02d}"
                ), []))
                for col_s in range(GLYPHS_PER_FRAME))
            print(f"  frame_{i:02d}: {GLYPHS_PER_FRAME} slice(s), {total_slice_layers} layers")

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
    total_frames_all = sum(info["num_frames"] for info in gif_infos)
    print()
    print(f"  Built: {OUTPUT}")
    grid_desc = f"{total_grid_w}x{GRID_H} ({DISPLAY_COLS} cells wide)" if DISPLAY_COLS > 1 else f"{GRID_W}x{GRID_H}"
    print(f"  Font: {FONT_NAME} ({num_gifs} GIF(s), {total_frames_all} total frames, {grid_desc} pixel art)")
    print(f"  COLR: {total_layers} layers, {len(all_colors)} palette colors")

    # ── Write gifs-manifest.json ──
    manifest = {
        "gifs": [
            {"name": info["name"], "firstCodepoint": info["first_cp"]}
            for info in gif_infos
        ],
        "rotation": ROTATION,
        "displayCols": DISPLAY_COLS,
        "framesPerGif": NUM_FRAMES,
        "firstCodepoint": FIRST_CP,
    }
    manifest_path = os.path.join(SCRIPT_DIR, "gifs-manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"  Manifest: {manifest_path}")

    # ── Generate preview HTML ──
    write_preview_html(os.path.basename(OUTPUT), gif_infos)

    print()
    print(f"  Next steps:")
    print(f"  1. Install: double-click {os.path.basename(OUTPUT)}")
    print(f'  2. Set terminal font to "{FONT_NAME}"')
    print(f"  3. Patch Claude: node scripts/patch-claude.js")
    print(f"  4. Preview: open test-colr-diag.html in browser")


def write_preview_html(font_file, gif_infos):
    num_gifs = len(gif_infos)

    # Build per-GIF sections
    gif_sections = []
    for gif_idx, info in enumerate(gif_infos):
        gif_first_cp = info["first_cp"]
        num_frames = info["num_frames"]
        gif_name = info["name"]

        frame_strs = []
        for i in range(num_frames):
            frame_chars = "".join(
                chr(gif_first_cp + i * GLYPHS_PER_FRAME + col)
                for col in range(GLYPHS_PER_FRAME)
            )
            frame_strs.append(frame_chars)
        chars_raw = "".join(frame_strs)
        chars_spaced_raw = " ".join(frame_strs)

        section = f'''<h3>{gif_name} (GIF {gif_idx + 1}/{num_gifs}, U+{gif_first_cp:04X})</h3>
<p>120px — all {num_frames} frames:</p>
<div class="p" style="font-size:120px">{chars_raw}</div>
<p>120px — spaced:</p>
<div class="p" style="font-size:120px">{chars_spaced_raw}</div>
<p>48px:</p>
<div class="p" style="font-size:48px">{chars_spaced_raw}</div>
<p>24px (terminal-ish):</p>
<div class="p" style="font-size:24px">{chars_spaced_raw}</div>'''
        gif_sections.append(section)

    all_sections = "\n<hr style='border-color:#444'>\n".join(gif_sections)

    html = f'''<!DOCTYPE html>
<html>
<head>
<style>
@font-face {{ font-family: "ClaudeParrot"; src: url("{font_file}"); }}
body {{ background: #1a1a2e; color: white; padding: 40px; font-family: sans-serif; }}
.p {{ font-family: "ClaudeParrot"; }}
</style>
</head>
<body>
<h2>Claude Parrot Preview — {GRID_W}x{GRID_H} grid, {num_gifs} GIF(s)</h2>
{all_sections}
<hr style="margin-top:40px;border-color:#333">
<p style="color:#888;font-size:14px">Made with <a href="https://github.com/Arystos/claude-parrot" style="color:#8073f5">Claude Parrot</a></p>
<script type="text/javascript" src="https://storage.ko-fi.com/cdn/widget/Widget_2.js"></script>
<script type="text/javascript">kofiwidget2.init('Support me on Ko-fi', '#8073f5', 'U7U71W5S5I');kofiwidget2.draw();</script>
</body>
</html>'''

    preview_path = os.path.join(SCRIPT_DIR, "test-colr-diag.html")
    with open(preview_path, "w", encoding="utf-8") as f:
        f.write(html)


if __name__ == "__main__":
    build_font()
