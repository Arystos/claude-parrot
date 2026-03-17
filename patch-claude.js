#!/usr/bin/env node

/**
 * Funny Terminal — Claude Code Spinner Patcher
 *
 * Replaces Claude Code's thinking spinner with custom animated
 * glyphs from a COLR font (built by build-font.py from any GIF).
 *
 * Usage: node patch-claude.js          (patch)
 *        node patch-claude.js --restore (undo)
 */

const fs = require("fs");
const path = require("path");
const os = require("os");

// ── Load config ────────────────────────────────────────────────────
var configPath = path.join(__dirname, "config.json");
if (!fs.existsSync(configPath)) {
  var examplePath = path.join(__dirname, "config.example.json");
  if (fs.existsSync(examplePath)) {
    fs.copyFileSync(examplePath, configPath);
    console.log("  Created config.json from example. Edit it to customize.\n");
  }
}

var config = {};
if (fs.existsSync(configPath)) {
  var raw = JSON.parse(fs.readFileSync(configPath, "utf-8"));
  Object.keys(raw).forEach(function(k) {
    if (!k.startsWith("//")) config[k] = raw[k];
  });
}

var NUM_FRAMES = 10;
var FIRST_CP = parseInt(config.firstCodepoint || "0xE000", 16);

// Build frame array from config codepoints
var FRAMES = [];
for (var f = 0; f < NUM_FRAMES; f++) {
  FRAMES.push(String.fromCharCode(FIRST_CP + f) + " ");
}

var ANIMATION_SPEED = 100;

// ── Find Claude Code installations ─────────────────────────────────
function findVSCodeExtensions() {
  var dir = path.join(os.homedir(), ".vscode", "extensions");
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir)
    .filter(function(d) { return d.startsWith("anthropic.claude-code-"); })
    .map(function(d) { return path.join(dir, d); })
    .sort().reverse();
}

function findNpmCli() {
  var dir = path.join(os.homedir(), "AppData", "Roaming", "npm",
    "node_modules", "@anthropic-ai", "claude-code");
  if (fs.existsSync(dir)) return dir;
  // Linux/macOS
  var globalDir = path.join(os.homedir(), ".npm-global", "lib",
    "node_modules", "@anthropic-ai", "claude-code");
  if (fs.existsSync(globalDir)) return globalDir;
  return null;
}

// ── Patching ───────────────────────────────────────────────────────
function patchWebview(extensionDir) {
  var file = path.join(extensionDir, "webview", "index.js");
  if (!fs.existsSync(file)) return false;
  var backup = file + ".parrot-backup";
  if (!fs.existsSync(backup)) fs.copyFileSync(file, backup);

  var content = fs.readFileSync(file, "utf-8");
  var framesStr = JSON.stringify(FRAMES);
  var count = 0;

  var before = content;
  content = content.replace(
    /Qj1=\["\xB7","\u2722","\*","\u2736","\u273B","\u273D"\]/g,
    "Qj1=" + framesStr
  );
  if (content !== before) { count++; }

  var p2 = '"\xB7","\u2722","\u2733","\u2736","\u273B","\u273D","\u273B","\u2736","\u2733","\u2722"';
  if (content.indexOf(p2) !== -1) {
    var cycle = FRAMES.concat(FRAMES.slice().reverse().slice(1));
    content = content.replace("[" + p2 + "]", JSON.stringify(cycle));
    count++;
  }

  before = content;
  content = content.replace(/yL0=120/g, "yL0=" + ANIMATION_SPEED);
  if (content !== before) count++;

  if (count > 0) {
    fs.writeFileSync(file, content, "utf-8");
    console.log("  webview patched (" + count + " changes)");
    return true;
  }
  console.log("  ! no patterns matched");
  return false;
}

function patchCliJs(cliDir) {
  var file = path.join(cliDir, "cli.js");
  if (!fs.existsSync(file)) return false;
  var backup = file + ".parrot-backup";
  if (!fs.existsSync(backup)) fs.copyFileSync(file, backup);

  var content = fs.readFileSync(file, "utf-8");
  var framesStr = JSON.stringify(FRAMES);
  var count = 0;

  var funcRegex = /function (\w+)\(\)\{if\(process\.env\.TERM==="xterm-ghostty"\)return\["\xB7"[^\]]*\];return process\.platform==="darwin"\?\["\xB7"[^\]]*\]:\["\xB7"[^\]]*\]\}/;
  var match = content.match(funcRegex);

  if (match) {
    content = content.replace(funcRegex, "function " + match[1] + "(){return " + framesStr + "}");
    count++;
    console.log("  patched " + match[1] + "() -> custom spinner");
  }

  if (count > 0) {
    fs.writeFileSync(file, content, "utf-8");
    console.log("  CLI patched (" + count + " changes)");
    return true;
  }
  console.log("  ! no patterns matched");
  return false;
}

function restore(filePath) {
  var backup = filePath + ".parrot-backup";
  if (fs.existsSync(backup)) {
    fs.copyFileSync(backup, filePath);
    fs.unlinkSync(backup);
    console.log("  restored: " + filePath);
    return true;
  }
  return false;
}

// ── Main ───────────────────────────────────────────────────────────
function main() {
  var isRestore = process.argv.indexOf("--restore") !== -1;
  console.log("\n  Funny Terminal — Claude Code Spinner Patcher\n");

  var exts = findVSCodeExtensions();
  var cli = findNpmCli();

  if (exts.length === 0 && !cli) {
    console.log("  No Claude Code installations found!");
    process.exit(1);
  }

  for (var i = 0; i < exts.length; i++) {
    var v = path.basename(exts[i]).replace("anthropic.claude-code-", "");
    console.log("  [vscode] v" + v);
    if (isRestore) restore(path.join(exts[i], "webview", "index.js"));
    else patchWebview(exts[i]);
    console.log("");
  }

  if (cli) {
    console.log("  [cli] npm");
    if (isRestore) restore(path.join(cli, "cli.js"));
    else patchCliJs(cli);
    console.log("");
  }

  console.log(isRestore ? "  Restored!" : "  Custom spinner activated!");
  console.log("");
}

main();
