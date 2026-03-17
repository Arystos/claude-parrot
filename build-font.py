#!/usr/bin/env python3
"""
Build PartyParrot font — Cascadia Mono + party parrot COLR/CPAL glyphs.

Reads settings from parrot-config.json. Each parrot frame uses COLR v0
with one layer per unique color. Layer glyphs contain all rectangles of
that color as multiple contours, anchored at x=0 and x=advance_w.

Usage: python build-font.py
Config: parrot-config.json
"""

import os
import io
import json
from PIL import Image
from fontTools.ttLib import TTFont, newTable
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.colorLib.builder import buildCOLR, buildCPAL

# ── Load config ─────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "parrot-config.json")

with open(CONFIG_PATH, "r") as f:
    # Strip comment keys (keys starting with "//")
    raw = json.load(f)
    cfg = {k: v for k, v in raw.items() if not k.startswith("//")}

GRID_W = cfg.get("gridWidth", 10)
GRID_H = cfg.get("gridHeight", 15)
CELL_ASPECT = cfg.get("cellAspectRatio", 0.55)  # terminal cell width:height ratio
ALPHA_THRESHOLD = cfg.get("alphaThreshold", 64)
RESAMPLE = cfg.get("resample", "nearest")  # "nearest" for sharp, "lanczos" for smooth
MAX_COLORS = cfg.get("maxColorsPerFrame", 0)  # 0 = unlimited

DARK_THRESHOLD = cfg.get("darkThreshold", 0)  # RGB sum below this = removed
LIGHT_THRESHOLD = cfg.get("lightThreshold", 0)  # min(R,G,B) above this = removed
V_OFFSET = cfg.get("verticalOffset", 0)  # shift parrot in grid rows
H_PADDING = cfg.get("horizontalPadding", 0)  # columns removed from each side

RESAMPLE_METHOD = Image.NEAREST if RESAMPLE == "nearest" else Image.LANCZOS
BASE_FONT = cfg.get("baseFont", "C:/Windows/Fonts/CascadiaMono.ttf")
FONT_NAME = cfg.get("fontName", "Party Terminal")
FONT_NAME_INTERNAL = cfg.get("fontNameInternal", "PartyTerminal")
OUTPUT = os.path.join(SCRIPT_DIR, cfg.get("output", "PartyParrot.ttf"))
FRAME_DIR = os.path.join(SCRIPT_DIR, cfg.get("frameDir", "frames"))
FIRST_CP = int(cfg.get("firstCodepoint", "0xE000"), 16) if isinstance(cfg.get("firstCodepoint"), str) else cfg.get("firstCodepoint", 0xE000)

# Count frames
NUM_FRAMES = len([f for f in os.listdir(FRAME_DIR) if f.startswith("frame_") and f.endswith(".png")])
CODEPOINTS = {FIRST_CP + i: f"parrot{i:02d}" for i in range(NUM_FRAMES)}


def crop_to_content(img):
    bbox = img.getbbox()
    return img.crop(bbox) if bbox else img


def build_font():
    print(f"  Config: {CONFIG_PATH}")
    print(f"  Base font: {BASE_FONT}")
    print(f"  Frames: {NUM_FRAMES} in {FRAME_DIR}")
    font = TTFont(BASE_FONT)

    ascent = font["OS/2"].sTypoAscender
    descent = font["OS/2"].sTypoDescender
    advance_w = font["hmtx"]["space"][0]
    em_height = ascent - descent

    usable_w = GRID_W - 2 * H_PADDING  # grid columns after padding
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

    # ── Add parrot base glyphs with full-cell bbox ──
    glyph_order = font.getGlyphOrder()

    for cp, name in sorted(CODEPOINTS.items()):
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

    # ── Process frames and build color-grouped layer glyphs ──
    all_colors = []
    color_map = {}
    color_layers = {}

    for i in range(NUM_FRAMES):
        frame_path = os.path.join(FRAME_DIR, f"frame_{i:02d}.png")
        img = Image.open(frame_path).convert("RGBA")
        img = crop_to_content(img)
        # Resize with aspect correction: the terminal cell is taller than wide
        # (cellAspectRatio = width/height, e.g. 0.55). We pre-squash the image
        # vertically so it looks correct in the tall cell.
        content_w, content_h = img.size
        img_aspect = content_w / content_h
        correct_rows = int(GRID_W / img_aspect / CELL_ASPECT)
        correct_rows = min(correct_rows, GRID_H)
        img = img.resize((GRID_W, correct_rows), RESAMPLE_METHOD)
        if correct_rows < GRID_H:
            padded = Image.new("RGBA", (GRID_W, GRID_H), (0, 0, 0, 0))
            padded.paste(img, (0, GRID_H - correct_rows))
            img = padded

        # Quantize colors if configured
        if MAX_COLORS > 0:
            # Convert to P mode (palettized) to reduce colors, then back to RGBA
            alpha = img.split()[3]  # preserve alpha
            rgb = img.convert("RGB")
            rgb = rgb.quantize(colors=MAX_COLORS, method=Image.Quantize.MEDIANCUT).convert("RGB")
            img = rgb.convert("RGBA")
            img.putalpha(alpha)

        # Group pixels by color
        color_pixels = {}
        for r in range(GRID_H):
            for c in range(GRID_W):
                # Skip padding columns
                if H_PADDING > 0 and (c < H_PADDING or c >= GRID_W - H_PADDING):
                    continue
                rgba = img.getpixel((c, r))
                if rgba[3] < ALPHA_THRESHOLD:
                    continue
                rgb = (rgba[0], rgba[1], rgba[2])
                # Skip near-black pixels (outlines)
                if DARK_THRESHOLD > 0 and sum(rgb) < DARK_THRESHOLD:
                    continue
                # Skip near-white pixels (edge artifacts)
                if LIGHT_THRESHOLD > 0 and min(rgb) > LIGHT_THRESHOLD:
                    continue
                if rgb not in color_pixels:
                    color_pixels[rgb] = []
                color_pixels[rgb].append((r, c))

        # Create one layer glyph per color
        layers = []
        for rgb, pixels in color_pixels.items():
            if rgb not in color_map:
                color_map[rgb] = len(all_colors)
                all_colors.append(rgb + (255,))

            glyph_name = f"f{i}_c{color_map[rgb]}"
            glyph_order.append(glyph_name)

            pen = TTGlyphPen(None)

            # Invisible anchors at x=0 and x=advance_w to force full-width bbox.
            # Placed far below descent so they're never visible.
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

            # Draw all rectangles for this color (with 2-unit bleed to avoid seam gaps)
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

        color_layers[f"parrot{i:02d}"] = layers
        print(f"  frame_{i:02d}: {sum(len(v) for v in color_pixels.values())} px, {len(color_pixels)} colors")

    font.setGlyphOrder(glyph_order)
    font["maxp"].numGlyphs = len(glyph_order)

    # Update cmap
    for subtable in font["cmap"].tables:
        if hasattr(subtable, "cmap") and subtable.cmap is not None:
            for cp, name in CODEPOINTS.items():
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
    print(f"  Font: {FONT_NAME} ({NUM_FRAMES} frames, {GRID_W}x{GRID_H} pixel art)")
    print(f"  COLR: {total_layers} layers, {len(all_colors)} palette colors")

    # ── Generate preview HTML ──
    write_preview_html(os.path.basename(OUTPUT))

    print()
    print(f"  Install: double-click {os.path.basename(OUTPUT)}")
    print(f'  Terminal font: "{FONT_NAME}"')
    print(f"  Preview: test-colr-diag.html")


def write_preview_html(font_file):
    chars = "".join(f"\\u{FIRST_CP + i:04x}" for i in range(NUM_FRAMES))
    chars_spaced = " ".join(f"\\u{FIRST_CP + i:04x}" for i in range(NUM_FRAMES))
    # Build the actual unicode characters for embedding
    chars_raw = "".join(chr(FIRST_CP + i) for i in range(NUM_FRAMES))
    chars_spaced_raw = " ".join(chr(FIRST_CP + i) for i in range(NUM_FRAMES))

    html = f'''<!DOCTYPE html>
<html>
<head>
<style>
@font-face {{ font-family: "PartyTest"; src: url("{font_file}"); }}
body {{ background: #1a1a2e; color: white; padding: 40px; font-family: sans-serif; }}
.p {{ font-family: "PartyTest"; }}
</style>
</head>
<body>
<h2>PartyParrot Preview — {GRID_W}x{GRID_H} grid</h2>
<p>120px — all {NUM_FRAMES} frames:</p>
<div class="p" style="font-size:120px">{chars_raw}</div>
<p>120px — spaced:</p>
<div class="p" style="font-size:120px">{chars_spaced_raw}</div>
<p>48px:</p>
<div class="p" style="font-size:48px">{chars_spaced_raw}</div>
<p>24px (terminal-ish):</p>
<div class="p" style="font-size:24px">{chars_spaced_raw}</div>
</body>
</html>'''

    path = os.path.join(SCRIPT_DIR, "test-colr-diag.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


if __name__ == "__main__":
    build_font()
