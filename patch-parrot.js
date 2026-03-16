#!/usr/bin/env node

/**
 * Party Parrot Patcher for Claude Code
 *
 * Replaces Claude Code's thinking spinner with rainbow-colored frames
 * matching the party parrot GIF color cycle.
 *
 * Usage: node patch-parrot.js          (patch)
 *        node patch-parrot.js --restore (undo)
 */

const fs = require("fs");
const path = require("path");
const os = require("os");

// -- Party parrot color frames (pure emoji, no ANSI) --
// Colors extracted from the actual party parrot GIF (10 frames):
//   pink -> yellow -> green -> teal -> blue -> purple -> magenta -> hot pink -> salmon -> red
// Using colored circle emoji to represent each frame + trailing space
const PARROT_FRAMES = [
  "\uD83D\uDD34 ",  // frame 0: red/pink
  "\uD83D\uDFE0 ",  // frame 1: orange/yellow
  "\uD83D\uDFE1 ",  // frame 2: yellow
  "\uD83D\uDFE2 ",  // frame 3: green
  "\uD83D\uDD35 ",  // frame 4: blue/teal
  "\uD83D\uDFE3 ",  // frame 5: purple
  "\uD83D\uDFE0 ",  // frame 6: magenta (reuse orange as closest)
  "\uD83D\uDD34 ",  // frame 7: hot pink (reuse red)
];

// Animation speed in ms (original is 120)
var ANIMATION_SPEED = 100;

// -- Find installations --

function findVSCodeExtensions() {
  var vscodeDir = path.join(os.homedir(), ".vscode", "extensions");
  if (!fs.existsSync(vscodeDir)) return [];
  return fs.readdirSync(vscodeDir)
    .filter(function(d) { return d.startsWith("anthropic.claude-code-"); })
    .map(function(d) { return path.join(vscodeDir, d); })
    .sort().reverse();
}

function findNpmCli() {
  var npmGlobal = path.join(
    os.homedir(), "AppData", "Roaming", "npm",
    "node_modules", "@anthropic-ai", "claude-code"
  );
  if (fs.existsSync(npmGlobal)) return npmGlobal;
  return null;
}

// -- Patch VS Code webview --

function patchWebview(extensionDir) {
  var webviewFile = path.join(extensionDir, "webview", "index.js");
  if (!fs.existsSync(webviewFile)) {
    console.log("  ! No webview/index.js found");
    return false;
  }

  var backupFile = webviewFile + ".parrot-backup";
  if (!fs.existsSync(backupFile)) {
    fs.copyFileSync(webviewFile, backupFile);
    console.log("  backup: " + backupFile);
  }

  var content = fs.readFileSync(webviewFile, "utf-8");
  var patchCount = 0;
  var framesStr = JSON.stringify(PARROT_FRAMES);

  // Patch 1: Qj1=["·","✢","*","✶","✻","✽"]
  var before = content;
  content = content.replace(
    /Qj1=\["\xB7","\u2722","\*","\u2736","\u273B","\u273D"\]/g,
    "Qj1=" + framesStr
  );
  if (content !== before) { patchCount++; console.log("  patched Qj1 spinner frames"); }

  // Patch 2: ["·","✢","✳","✶","✻","✽","✻","✶","✳","✢"]
  var p2 = '"\xB7","\u2722","\u2733","\u2736","\u273B","\u273D","\u273B","\u2736","\u2733","\u2722"';
  if (content.indexOf(p2) !== -1) {
    var cycle = PARROT_FRAMES.concat(PARROT_FRAMES.slice().reverse().slice(1));
    content = content.replace("[" + p2 + "]", JSON.stringify(cycle));
    patchCount++;
    console.log("  patched secondary spinner frames");
  }

  // Patch 3: animation speed
  before = content;
  content = content.replace(/yL0=120/g, "yL0=" + ANIMATION_SPEED);
  if (content !== before) { patchCount++; console.log("  set speed to " + ANIMATION_SPEED + "ms"); }

  if (patchCount > 0) {
    fs.writeFileSync(webviewFile, content, "utf-8");
    console.log("  webview patched (" + patchCount + " changes)");
    return true;
  }
  console.log("  ! no patterns matched");
  return false;
}

// -- Patch npm CLI --

function patchCliJs(cliDir) {
  var cliFile = path.join(cliDir, "cli.js");
  if (!fs.existsSync(cliFile)) {
    console.log("  ! No cli.js found");
    return false;
  }

  var backupFile = cliFile + ".parrot-backup";
  if (!fs.existsSync(backupFile)) {
    fs.copyFileSync(cliFile, backupFile);
    console.log("  backup: " + backupFile);
  }

  var content = fs.readFileSync(cliFile, "utf-8");
  var patchCount = 0;
  var framesStr = JSON.stringify(PARROT_FRAMES);

  // Replace the spinner function that returns platform-specific arrays
  var funcRegex = /function (\w+)\(\)\{if\(process\.env\.TERM==="xterm-ghostty"\)return\["\xB7"[^\]]*\];return process\.platform==="darwin"\?\["\xB7"[^\]]*\]:\["\xB7"[^\]]*\]\}/;
  var match = content.match(funcRegex);

  if (match) {
    var funcName = match[1];
    content = content.replace(funcRegex, "function " + funcName + "(){return " + framesStr + "}");
    patchCount++;
    console.log("  patched " + funcName + "() -> party parrot");
  } else {
    // Fallback: replace individual arrays
    var patterns = [
      '["\xB7","\u2722","*","\u2736","\u273B","\u273D"]',
      '["\xB7","\u2722","\u2733","\u2736","\u273B","\u273D"]',
      '["\xB7","\u2722","\u2733","\u2736","\u273B","*"]',
    ];
    for (var i = 0; i < patterns.length; i++) {
      while (content.indexOf(patterns[i]) !== -1) {
        content = content.replace(patterns[i], framesStr);
        patchCount++;
        console.log("  patched inline spinner array");
      }
    }
  }

  if (patchCount > 0) {
    fs.writeFileSync(cliFile, content, "utf-8");
    console.log("  CLI patched (" + patchCount + " changes)");
    return true;
  }
  console.log("  ! no patterns matched");
  return false;
}

// -- Restore --

function restore(filePath) {
  var backupFile = filePath + ".parrot-backup";
  if (fs.existsSync(backupFile)) {
    fs.copyFileSync(backupFile, filePath);
    fs.unlinkSync(backupFile);
    console.log("  restored: " + filePath);
    return true;
  }
  return false;
}

// -- Main --

function main() {
  var isRestore = process.argv.indexOf("--restore") !== -1;

  console.log("");
  console.log("  Party Parrot Patcher for Claude Code");
  console.log("  =====================================");
  console.log("");

  var vscodeExts = findVSCodeExtensions();
  var npmCli = findNpmCli();

  if (vscodeExts.length === 0 && !npmCli) {
    console.log("  No Claude Code installations found!");
    console.log("  Install via: npm install -g @anthropic-ai/claude-code");
    process.exit(1);
  }

  for (var i = 0; i < vscodeExts.length; i++) {
    var ext = vscodeExts[i];
    var version = path.basename(ext).replace("anthropic.claude-code-", "");
    console.log("  [vscode] v" + version);
    if (isRestore) {
      restore(path.join(ext, "webview", "index.js"));
    } else {
      patchWebview(ext);
    }
    console.log("");
  }

  if (npmCli) {
    console.log("  [cli] npm installation");
    if (isRestore) {
      restore(path.join(npmCli, "cli.js"));
    } else {
      patchCliJs(npmCli);
    }
    console.log("");
  }

  if (isRestore) {
    console.log("  Restored! Restart Claude Code to see changes.");
  } else {
    console.log("  Party parrot activated! Restart Claude Code.");
    console.log("  Run with --restore to undo.");
  }
  console.log("");
}

main();
