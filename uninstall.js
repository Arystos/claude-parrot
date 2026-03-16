#!/usr/bin/env node

/**
 * Party Parrot for Claude Code - Uninstall Script
 *
 * Restores all patched files and renames the original binary back.
 *
 * Usage: node uninstall.js
 */

const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const os = require("os");

function run(cmd) {
  try {
    return execSync(cmd, { encoding: "utf-8", stdio: "pipe" }).trim();
  } catch (e) {
    return null;
  }
}

function main() {
  console.log("");
  console.log("  Party Parrot for Claude Code - Uninstall");
  console.log("  =========================================");
  console.log("");

  // Step 1: Restore patched files
  const patcherPath = path.join(__dirname, "patch-parrot.js");
  if (fs.existsSync(patcherPath)) {
    try {
      execSync("node " + JSON.stringify(patcherPath) + " --restore", {
        stdio: "inherit",
      });
    } catch (e) {
      console.log("  [warn] Patcher restore had issues, continuing...");
    }
  }

  // Step 2: Restore compiled binary (Windows)
  if (process.platform === "win32") {
    const localBin = path.join(os.homedir(), ".local", "bin");
    const binaryPath = path.join(localBin, "claude.exe");
    const renamedPath = path.join(localBin, "claude-original.exe");

    if (fs.existsSync(renamedPath) && !fs.existsSync(binaryPath)) {
      fs.renameSync(renamedPath, binaryPath);
      console.log("  [ok] Restored claude-original.exe -> claude.exe");
    } else if (fs.existsSync(renamedPath) && fs.existsSync(binaryPath)) {
      // Both exist — npm installed a claude.exe too? Just remove the renamed one.
      console.log("  [info] Both claude.exe and claude-original.exe exist");
      console.log("         You may want to manually remove claude-original.exe");
    } else {
      console.log("  [ok] No binary rename to undo");
    }
  }

  // Step 3: Optionally uninstall npm package
  console.log("");
  console.log("  Patched files restored!");
  console.log("");
  console.log("  To also remove the npm-installed Claude Code:");
  console.log("    npm uninstall -g @anthropic-ai/claude-code");
  console.log("");
  console.log("  Restart your terminal to use the original claude.");
  console.log("");
}

main();
