#!/usr/bin/env node
// Preview party parrot sixel animation in Windows Terminal 1.22+

const fs = require("fs");
const path = require("path");

const framesFile = path.join(__dirname, "parrot-sixel-frames.json");
const frames = JSON.parse(fs.readFileSync(framesFile, "utf-8"));

const VERBS = [
  "Thinking...", "Ruminating...", "Vibing...", "Clauding...",
  "Baking...", "Brewing...", "Pondering...", "Forging...",
  "Cooking...", "Crafting...",
];

process.stdout.write("\x1b[?25l"); // hide cursor
console.log("\n  Party Parrot Sixel Preview (Ctrl+C to exit)");

var startRow = null;
var i = 0;
var imgLines = 3;
var timer = null;

function cleanup() {
  if (timer) clearInterval(timer);
  process.stdout.write("\x1b[?25h\n\n"); // show cursor
  process.stdin.setRawMode(false);
  process.exit();
}

process.stdout.write("\x1b[6n");
process.stdin.setRawMode(true);
process.stdin.resume();

// Listen for Ctrl+C (0x03) and 'q' to quit
process.stdin.on("data", function (data) {
  if (startRow !== null) return; // still waiting for cursor pos

  // After init, any keypress with Ctrl+C or 'q' exits
  for (var j = 0; j < data.length; j++) {
    if (data[j] === 0x03 || data[j] === 0x71) { // Ctrl+C or 'q'
      cleanup();
    }
  }
});

process.stdin.once("data", function (data) {
  var match = data.toString().match(/\[(\d+);(\d+)R/);
  startRow = match ? parseInt(match[1]) : 5;

  timer = setInterval(function () {
    var frame = frames[i % frames.length];
    var verb = VERBS[i % VERBS.length];

    process.stdout.write(
      "\x1b[" + startRow + ";1H" +
      "\x1b[2K" + frame +
      "\x1b[" + (startRow + imgLines) + ";1H" +
      "\x1b[2K  " + verb
    );
    i++;
  }, 120);

  // Now listen for quit keys
  process.stdin.on("data", function (data) {
    for (var j = 0; j < data.length; j++) {
      if (data[j] === 0x03 || data[j] === 0x71) cleanup();
    }
  });
});
