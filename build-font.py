#!/usr/bin/env python3
"""
Build PartyParrot font — Cascadia Mono + party parrot COLR/CPAL glyphs.

Each parrot frame uses COLR v0 with one layer per unique color.
Each layer glyph contains ALL rectangles of that color as multiple contours,
anchored at x=0 to prevent renderer repositioning.

Usage: python build-font.py
Output: PartyParrot.ttf
"""

import os
import io
from PIL import Image
from fontTools.ttLib import TTFont, newTable
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.colorLib.builder import buildCOLR, buildCPAL

# ── Config ──────────────────────────────────────────────────────────
FRAME_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frames")
OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PartyParrot.ttf")
BASE_FONT = "C:/Windows/Fonts/CascadiaMono.ttf"
NUM_FRAMES = 10

GRID_W = 10
GRID_H = 20

CODEPOINTS = {0xE000 + i: f"parrot{i:02d}" for i in range(NUM_FRAMES)}


def crop_to_content(img):
    bbox = img.getbbox()
    return img.crop(bbox) if bbox else img


def build_font():
    print(f"  Base font: {BASE_FONT}")
    font = TTFont(BASE_FONT)

    ascent = font["OS/2"].sTypoAscender
    descent = font["OS/2"].sTypoDescender
    advance_w = font["hmtx"]["space"][0]
    em_height = ascent - descent

    pixel_w = advance_w // GRID_W
    pixel_h = (em_height - 100) // GRID_H
    grid_h_total = GRID_H * pixel_h
    y_top = ascent - (em_height - grid_h_total) // 2

    print(f"  Grid: {GRID_W}x{GRID_H}, pixel={pixel_w}x{pixel_h} units")

    # ── Rename font ──
    for record in font["name"].names:
        try:
            text = record.toUnicode()
        except:
            continue
        if "Cascadia Mono" in text:
            record.string = text.replace("Cascadia Mono", "Party Terminal")
        elif "CascadiaMono" in text:
            record.string = text.replace("CascadiaMono", "PartyTerminal")

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
        img = img.resize((GRID_W, GRID_H), Image.LANCZOS)

        # Group pixels by color
        color_pixels = {}  # rgb -> list of (row, col)
        for r in range(GRID_H):
            for c in range(GRID_W):
                rgba = img.getpixel((c, r))
                if rgba[3] < 64:
                    continue
                rgb = (rgba[0], rgba[1], rgba[2])
                if rgb not in color_pixels:
                    color_pixels[rgb] = []
                color_pixels[rgb].append((r, c))

        # Create one layer glyph per color, containing all rectangles
        layers = []
        for rgb, pixels in color_pixels.items():
            if rgb not in color_map:
                color_map[rgb] = len(all_colors)
                all_colors.append(rgb + (255,))

            glyph_name = f"f{i}_c{color_map[rgb]}"
            glyph_order.append(glyph_name)

            pen = TTGlyphPen(None)

            # Anchor contour at x=0 (prevents renderer repositioning)
            pen.moveTo((0, 0))
            pen.lineTo((1, 0))
            pen.lineTo((1, 1))
            pen.lineTo((0, 1))
            pen.closePath()

            # Also anchor at x=advance_w (forces full-width bbox)
            pen.moveTo((advance_w - 1, 0))
            pen.lineTo((advance_w, 0))
            pen.lineTo((advance_w, 1))
            pen.lineTo((advance_w - 1, 1))
            pen.closePath()

            # Draw all rectangles for this color
            for (r, c) in pixels:
                x0 = c * pixel_w
                x1 = x0 + pixel_w
                y1_pos = y_top - r * pixel_h
                y0_pos = y_top - (r + 1) * pixel_h
                pen.moveTo((x0, y0_pos))
                pen.lineTo((x1, y0_pos))
                pen.lineTo((x1, y1_pos))
                pen.lineTo((x0, y1_pos))
                pen.closePath()

            font["glyf"][glyph_name] = pen.glyph()
            font["hmtx"][glyph_name] = (advance_w, 0)
            layers.append((glyph_name, color_map[rgb]))

        color_layers[f"parrot{i:02d}"] = layers
        print(f"  frame_{i:02d}: {len(pixels)} px, {len(color_pixels)} colors, {len(layers)} layers")

    font.setGlyphOrder(glyph_order)
    font["maxp"].numGlyphs = len(glyph_order)

    # Update cmap
    for subtable in font["cmap"].tables:
        if hasattr(subtable, "cmap") and subtable.cmap is not None:
            for cp, name in CODEPOINTS.items():
                subtable.cmap[cp] = name

    # ── Build COLR/CPAL ──
    print(f"  Building COLR v0 with {len(all_colors)} palette colors...")
    font["COLR"] = buildCOLR(color_layers)
    normalized = [(r/255, g/255, b/255, a/255) for r, g, b, a in all_colors]
    font["CPAL"] = buildCPAL([normalized])

    font.save(OUTPUT)
    total_layers = sum(len(v) for v in color_layers.values())
    print()
    print(f"  Built: {OUTPUT}")
    print(f"  Font name: Party Terminal")
    print(f"  Parrot: {NUM_FRAMES} frames, {GRID_W}x{GRID_H} pixel art")
    print(f"  Total COLR layers: {total_layers}")
    print(f"  Palette: {len(all_colors)} colors")
    print(f"  Layer glyphs: {sum(len(v) for v in color_layers.values())} (one per color per frame)")


if __name__ == "__main__":
    build_font()
