#!/usr/bin/env node
// Claude Parrot — Spinner Preview
// Usage: node preview.js          (font codepoint mode)
//        node preview.js --ansi   (legacy ANSI art mode)

const fs = require("fs");
const path = require("path");

// ── Load config ──
var configPath = path.join(__dirname, "..", "config.json");
var config = {};
if (fs.existsSync(configPath)) {
  var raw = JSON.parse(fs.readFileSync(configPath, "utf-8"));
  Object.keys(raw).forEach(function(k) {
    if (!k.startsWith("//")) config[k] = raw[k];
  });
}

var NUM_FRAMES = 10;
var FIRST_CP = parseInt(config.firstCodepoint || "0xE000", 16);
var DISPLAY_COLS = config.displayCols || 1;

// Build font frame array from codepoints
// Each frame is DISPLAY_COLS characters (one per cell column)
var FONT_FRAMES = [];
for (var f = 0; f < NUM_FRAMES; f++) {
  var frame = "";
  for (var col = 0; col < DISPLAY_COLS; col++) {
    frame += String.fromCharCode(FIRST_CP + f * DISPLAY_COLS + col);
  }
  FONT_FRAMES.push(frame + " ");
}

const VERBS = [
  "Thinking...", "Ruminating...", "Vibing...", "Clauding...",
  "Baking...", "Brewing...", "Pondering...", "Forging...",
  "Cooking...", "Crafting...",
];

// ── Load manifest (with fallback to config for backward compat) ──
var manifestPath = path.join(__dirname, "..", "gifs-manifest.json");
var manifest = null;
if (fs.existsSync(manifestPath)) {
  manifest = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));
}

var GIF_SETS, ROTATION;
if (manifest && manifest.gifs) {
  ROTATION = manifest.rotation || "sequential";
  GIF_SETS = manifest.gifs.map(function(gif) {
    var frames = [];
    var dc = manifest.displayCols || 1;
    var fpg = manifest.framesPerGif || 10;
    for (var f = 0; f < fpg; f++) {
      var frame = "";
      for (var col = 0; col < dc; col++) {
        frame += String.fromCharCode(gif.firstCodepoint + f * dc + col);
      }
      frames.push(frame + " ");
    }
    return { name: gif.name, frames: frames };
  });
} else {
  ROTATION = "sequential";
  GIF_SETS = [{ name: config.fontName || "GIF", frames: FONT_FRAMES }];
}

var currentGif = 0;
var frameIdx = 0;
var fontName = config.fontName || "Claude Parrot";

console.log("\n  Claude Parrot — Spinner Preview (Ctrl+C to exit)");
console.log("  Font: " + fontName);
if (GIF_SETS.length > 1) {
  console.log("  GIFs: " + GIF_SETS.length + " (" + ROTATION + " rotation)");
}
console.log("");

setInterval(function() {
  var set = GIF_SETS[currentGif];
  var frame = set.frames[frameIdx % set.frames.length];
  var label = GIF_SETS.length > 1 ? set.name : VERBS[frameIdx % VERBS.length];
  process.stdout.write("\r  " + frame + " " + label + "     ");
  frameIdx++;
  // Rotate after a full cycle
  if (frameIdx % set.frames.length === 0 && GIF_SETS.length > 1) {
    if (ROTATION === "random") {
      currentGif = Math.floor(Math.random() * GIF_SETS.length);
    } else {
      currentGif = (currentGif + 1) % GIF_SETS.length;
    }
  }
}, 100);
