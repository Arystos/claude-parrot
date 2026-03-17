#!/usr/bin/env node

/**
 * Party Parrot Patcher for Claude Code
 *
 * Replaces Claude Code's thinking spinner with rainbow-colored emoji
 * that cycle through the party parrot GIF color sequence.
 *
 * Usage: node patch-parrot.js          (patch)
 *        node patch-parrot.js --restore (undo)
 */

const fs = require("fs");
const path = require("path");
const os = require("os");

// Party parrot color cycle (matching the 10-frame GIF)
// Each frame: colored circle + space
// Party parrot frames: PUA codepoints U+E000–U+E009
// Rendered by PartyParrot.ttf font (install first!)
const PARROT_FRAMES = [
  "\uE000 ",  // frame 0 (red)
  "\uE001 ",  // frame 1 (orange/yellow)
  "\uE002 ",  // frame 2 (green)
  "\uE003 ",  // frame 3 (teal)
  "\uE004 ",  // frame 4 (blue)
  "\uE005 ",  // frame 5 (purple)
  "\uE006 ",  // frame 6 (magenta)
  "\uE007 ",  // frame 7 (pink)
  "\uE008 ",  // frame 8 (rose)
  "\uE009 ",  // frame 9 (red-dark)
];

var ANIMATION_SPEED = 100;

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
  return null;
}

function patchWebview(extensionDir) {
  var file = path.join(extensionDir, "webview", "index.js");
  if (!fs.existsSync(file)) return false;
  var backup = file + ".parrot-backup";
  if (!fs.existsSync(backup)) fs.copyFileSync(file, backup);

  var content = fs.readFileSync(file, "utf-8");
  var framesStr = JSON.stringify(PARROT_FRAMES);
  var count = 0;

  var before = content;
  content = content.replace(
    /Qj1=\["\xB7","\u2722","\*","\u2736","\u273B","\u273D"\]/g,
    "Qj1=" + framesStr
  );
  if (content !== before) { count++; }

  var p2 = '"\xB7","\u2722","\u2733","\u2736","\u273B","\u273D","\u273B","\u2736","\u2733","\u2722"';
  if (content.indexOf(p2) !== -1) {
    var cycle = PARROT_FRAMES.concat(PARROT_FRAMES.slice().reverse().slice(1));
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
  var framesStr = JSON.stringify(PARROT_FRAMES);
  var count = 0;

  var funcRegex = /function (\w+)\(\)\{if\(process\.env\.TERM==="xterm-ghostty"\)return\["\xB7"[^\]]*\];return process\.platform==="darwin"\?\["\xB7"[^\]]*\]:\["\xB7"[^\]]*\]\}/;
  var match = content.match(funcRegex);

  if (match) {
    content = content.replace(funcRegex, "function " + match[1] + "(){return " + framesStr + "}");
    count++;
    console.log("  patched " + match[1] + "() -> party parrot");
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

function main() {
  var isRestore = process.argv.indexOf("--restore") !== -1;
  console.log("\n  Party Parrot Patcher for Claude Code\n");

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

  console.log(isRestore ? "  Restored!" : "  Party parrot activated!");
  console.log("");
}

main();
