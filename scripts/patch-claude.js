#!/usr/bin/env node

/**
 * Claude Parrot — Claude Code Spinner Patcher
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

// ── Load manifest ─────────────────────────────────────────────────
var manifestPath = path.join(__dirname, "..", "gifs-manifest.json");
var isRestore = process.argv.indexOf("--restore") !== -1;
if (!fs.existsSync(manifestPath) && !isRestore) {
  console.log("  Error: gifs-manifest.json not found. Run: python build-font.py");
  process.exit(1);
}
var manifest = fs.existsSync(manifestPath) ? JSON.parse(fs.readFileSync(manifestPath, "utf-8")) : { gifs: [], displayCols: 1, framesPerGif: 10, rotation: "sequential" };
var DISPLAY_COLS = manifest.displayCols || 1;
var FRAMES_PER_GIF = manifest.framesPerGif || 10;
var ROTATION = manifest.rotation || "sequential";

// Build frame sets — one array per GIF
var GIF_SETS = manifest.gifs.map(function(gif) {
  var frames = [];
  for (var f = 0; f < FRAMES_PER_GIF; f++) {
    var frame = "";
    for (var col = 0; col < DISPLAY_COLS; col++) {
      frame += String.fromCharCode(gif.firstCodepoint + f * DISPLAY_COLS + col);
    }
    frames.push(frame + " ");
  }
  return frames;
});
var FRAMES = GIF_SETS[0]; // first GIF's frames (used for base function & single-GIF mode)
var MULTI_GIF = GIF_SETS.length > 1;

var ANIMATION_SPEED = 100;

// ── Proxy builder for multi-GIF rotation ──────────────────────────
// Returns an IIFE string that creates a Proxy mimicking a ping-pong
// array. Switches GIF only when a time gap is detected (>2s between
// accesses = new prompt), so each thinking session shows one GIF.
function buildProxyCode(gifSets, rotation) {
  var setsJson = JSON.stringify(gifSets);
  var mode = JSON.stringify(rotation);
  return [
    "(function(){",
    "var _gs=" + setsJson + ";",
    "var _mode=" + mode + ";",
    "var _cg=Math.floor(Math.random()*_gs.length);",
    "var _lastT=0;",
    "var _ar=_gs.map(function(s){",
    "  var r=s.concat(s.slice().reverse().slice(1));",
    "  return r;",
    "});",
    "return new Proxy([],{",
    "  get:function(t,p){",
    "    if(p===\"length\")return _ar[0].length;",
    "    if(p===Symbol.iterator)return function(){",
    "      var i=0,a=_ar[_cg];",
    "      return{next:function(){return i<a.length?{value:a[i++],done:false}:{done:true};}};",
    "    };",
    "    if(typeof p===\"string\"&&!isNaN(p)){",
    "      var now=Date.now();",
    "      if(_lastT>0&&now-_lastT>2000){",
    "        if(_mode===\"random\")_cg=Math.floor(Math.random()*_gs.length);",
    "        else _cg=(_cg+1)%_gs.length;",
    "      }",
    "      _lastT=now;",
    "      return _ar[_cg][+p];",
    "    }",
    "    return [][p];",
    "  }",
    "});",
    "})()"
  ].join("");
}

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

  // Patch 1: Replace the base frame array (Qj1)
  var before = content;
  content = content.replace(
    /Qj1=\["\xB7","\u2722","\*","\u2736","\u273B","\u273D"\]/g,
    "Qj1=" + framesStr
  );
  if (content !== before) { count++; }

  // Patch 2: Replace the ping-pong array (Gj1)
  // For multi-GIF, replace with Proxy; for single-GIF, use static cycle
  if (MULTI_GIF) {
    // Match pattern like: Gj1=[...Qj1,...[...Qj1].reverse()]
    var pingPongRegex = /(\w+)=\[\.\.\.(\w+),\.\.\.\[\.\.\.(\w+)\]\.reverse\(\)\]/;
    var ppMatch = content.match(pingPongRegex);
    if (ppMatch) {
      content = content.replace(pingPongRegex, ppMatch[1] + "=" + buildProxyCode(GIF_SETS, ROTATION));
      count++;
      console.log("  patched " + ppMatch[1] + " -> Proxy (multi-GIF rotation)");
    }
  } else {
    // Single GIF: replace hardcoded ping-pong array with our frames' cycle
    var p2 = '"\xB7","\u2722","\u2733","\u2736","\u273B","\u273D","\u273B","\u2736","\u2733","\u2722"';
    if (content.indexOf(p2) !== -1) {
      var cycle = FRAMES.concat(FRAMES.slice().reverse().slice(1));
      content = content.replace("[" + p2 + "]", JSON.stringify(cycle));
      count++;
    }
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

  // Patch 1: Replace the frame-source function (eQ6) to return our frames
  var funcRegex = /function (\w+)\(\)\{if\(process\.env\.TERM==="xterm-ghostty"\)return\["\xB7"[^\]]*\];return process\.platform==="darwin"\?\["\xB7"[^\]]*\]:\["\xB7"[^\]]*\]\}/;
  var match = content.match(funcRegex);

  if (match) {
    content = content.replace(funcRegex, "function " + match[1] + "(){return " + framesStr + "}");
    count++;
    console.log("  patched " + match[1] + "() -> custom spinner");
  }

  // Patch 2 (multi-GIF only): Replace ping-pong array with Proxy
  if (MULTI_GIF) {
    // Match pattern like: RP4=[...LP4,...[...LP4].reverse()]
    var pingPongRegex = /(\w+)=\[\.\.\.(\w+),\.\.\.\[\.\.\.(\w+)\]\.reverse\(\)\]/;
    var ppMatch = content.match(pingPongRegex);
    if (ppMatch) {
      content = content.replace(pingPongRegex, ppMatch[1] + "=" + buildProxyCode(GIF_SETS, ROTATION));
      count++;
      console.log("  patched " + ppMatch[1] + " -> Proxy (multi-GIF rotation)");
    }
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
  console.log("\n  Claude Parrot — Claude Code Spinner Patcher\n");
  console.log("  GIFs: " + manifest.gifs.length + (MULTI_GIF ? " (multi-GIF, rotation: " + ROTATION + ")" : " (single)"));
  console.log("");

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
