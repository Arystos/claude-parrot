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

// Build font frame array from codepoints
var FONT_FRAMES = [];
for (var f = 0; f < NUM_FRAMES; f++) {
  FONT_FRAMES.push(String.fromCharCode(FIRST_CP + f) + " ");
}

const VERBS = [
  "Thinking...", "Ruminating...", "Vibing...", "Clauding...",
  "Baking...", "Brewing...", "Pondering...", "Forging...",
  "Cooking...", "Crafting...",
];

var frames = FONT_FRAMES;

var i = 0;
var fontName = config.fontName || "Claude Parrot";
console.log("\n  Claude Parrot — Spinner Preview (Ctrl+C to exit)");
console.log("  Font: " + fontName + "\n");

setInterval(function () {
  process.stdout.write("\r  " + frames[i % frames.length] + " " + VERBS[i % VERBS.length] + "     ");
  i++;
}, 100);
