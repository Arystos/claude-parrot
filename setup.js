#!/usr/bin/env node

/**
 * Party Parrot for Claude Code - Setup Script
 *
 * Installs Claude Code via npm (if needed), patches the spinner
 * with rainbow parrot animation, and ensures the patched version
 * takes priority over the compiled binary.
 *
 * Usage: node setup.js
 */

const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const os = require("os");

function run(cmd, opts = {}) {
  try {
    return execSync(cmd, { encoding: "utf-8", stdio: "pipe", ...opts }).trim();
  } catch (e) {
    return null;
  }
}

function main() {
  console.log("");
  console.log("  Party Parrot for Claude Code - Setup");
  console.log("  =====================================");
  console.log("");

  // Step 1: Check Node.js
  const nodeVersion = run("node --version");
  if (!nodeVersion) {
    console.log("  [error] Node.js is required. Install it from https://nodejs.org");
    process.exit(1);
  }
  console.log("  [ok] Node.js " + nodeVersion);

  // Step 2: Install Claude Code via npm if not already installed
  const npmRoot = run("npm root -g");
  const claudeNpmDir = path.join(npmRoot, "@anthropic-ai", "claude-code");

  if (!fs.existsSync(claudeNpmDir)) {
    console.log("  [..] Installing @anthropic-ai/claude-code via npm...");
    const result = run("npm install -g @anthropic-ai/claude-code 2>&1");
    if (!fs.existsSync(claudeNpmDir)) {
      console.log("  [error] Failed to install Claude Code via npm");
      console.log("  " + (result || "Unknown error"));
      process.exit(1);
    }
    console.log("  [ok] Claude Code installed via npm");
  } else {
    console.log("  [ok] Claude Code already installed via npm");
  }

  // Step 3: Handle compiled binary (Windows)
  if (process.platform === "win32") {
    const localBin = path.join(os.homedir(), ".local", "bin");
    const binaryPath = path.join(localBin, "claude.exe");
    const renamedPath = path.join(localBin, "claude-original.exe");

    if (fs.existsSync(binaryPath) && !fs.existsSync(renamedPath)) {
      console.log("  [..] Renaming compiled binary so npm version takes priority...");
      fs.renameSync(binaryPath, renamedPath);
      console.log("  [ok] Renamed claude.exe -> claude-original.exe");
      console.log("       (original saved at " + renamedPath + ")");
    } else if (fs.existsSync(renamedPath)) {
      console.log("  [ok] Compiled binary already renamed");
    } else {
      console.log("  [ok] No compiled binary found (npm version will be used)");
    }
  }

  // Step 4: Run the patcher
  console.log("");
  const patcherPath = path.join(__dirname, "patch-parrot.js");
  try {
    execSync("node " + JSON.stringify(patcherPath), { stdio: "inherit" });
  } catch (e) {
    console.log("  [error] Patcher failed");
    process.exit(1);
  }

  // Step 5: Verify
  const activeClaude = run("where claude") || run("which claude");
  console.log("  Active claude: " + (activeClaude ? activeClaude.split("\n")[0] : "not found"));
  console.log("");
  console.log("  Done! Open a new terminal and run 'claude' to see the party parrot.");
  console.log("");
}

main();
