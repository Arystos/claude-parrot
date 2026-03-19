# Multi-GIF Rotation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Allow multiple GIFs to be packed into a single font, with the spinner rotating between them each cycle using a Proxy-based array that intercepts frame access.

**Architecture:** `build-font.py` processes multiple GIFs (from `gifs/` folder), each getting its own codepoint range in the font. The patcher injects a Proxy-wrapped array into Claude Code's spinner function — the Proxy tracks cycle count and serves frames from a different GIF each cycle. Config controls rotation order (sequential/random) and which GIFs to include.

**Tech Stack:** Python (Pillow, fonttools), Node.js, JavaScript Proxy API

---

## Current State

- `build-font.py` processes a **single GIF** → 10 frames → font glyphs at codepoints E000-E013 (with displayCols=2)
- `patch-claude.js` replaces spinner function with static array of frame strings
- CLI spinner: `eQ6()` called once at init → `LP4 = eQ6()` → `RP4 = [...LP4, ...LP4.reverse()]` → render uses `RP4[K % RP4.length]` where K is time-based counter
- Webview: `Qj1` array → `Gj1 = [...Qj1, ...Qj1.reverse()]` → `Gj1[G]` with setInterval

## Codepoint Layout

With N GIFs, 10 frames each, displayCols=2 (20 codepoints per GIF):

```
GIF 0 (parrot):  E000-E013  (frames 0-9, 2 codepoints each)
GIF 1 (nyancat): E014-E027  (frames 0-9, 2 codepoints each)
GIF 2 (globe):   E028-E03B  (frames 0-9, 2 codepoints each)
```

## Proxy Strategy

The consuming code does `RP4[K % RP4.length]`. We replace the static array with a Proxy:

```javascript
// GIF_SETS = [["\uE000\uE001 ", "\uE002\uE003 ", ...], ["\uE014\uE015 ", ...], ...]
// Each inner array = one GIF's 10 frames (already with displayCols chars + space)
var _gifSets = GIF_SETS;
var _mode = "sequential"; // or "random"
var _currentGif = 0;
var _cycleLen = GIF_SETS[0].length * 2 - 2; // ping-pong length (18 for 10 frames)
var _lastCycle = -1;

function eQ6() {
  // Return first GIF's frames — the Proxy on RP4/Gj1 handles rotation
  return _gifSets[0];
}

// After LP4=eQ6(), RP4=[...LP4,...LP4.reverse()] — we replace RP4 with a Proxy:
// The patch replaces the RP4/Gj1 assignment with:
var _allRP4 = _gifSets.map(function(s) {
  var r = s.concat(s.slice().reverse().slice(1));
  return r;
});

RP4 = new Proxy([], {
  get: function(t, p) {
    if (p === "length") return _allRP4[0].length;
    if (typeof p === "string" && !isNaN(p)) {
      var idx = Number(p);
      var cycle = Math.floor(idx / _allRP4[0].length);
      if (cycle !== _lastCycle) {
        _lastCycle = cycle;
        if (_mode === "random") {
          _currentGif = Math.floor(Math.random() * _gifSets.length);
        } else {
          _currentGif = cycle % _gifSets.length;
        }
      }
      return _allRP4[_currentGif][idx % _allRP4[0].length];
    }
    return [][p];
  }
});
```

Key insight: `K` in `RP4[K % RP4.length]` is monotonically increasing. The Proxy's `length` stays constant (18 for ping-pong of 10 frames), so `K % length` cycles 0-17 repeatedly. We detect when a new cycle starts by tracking `Math.floor(idx / length)` — but since the consuming code already does `K % RP4.length`, we never see the raw K.

**Revised approach:** We can't detect cycles from the modulo'd index alone. Instead, the Proxy tracks the *sequence of indices* — when it sees index 0 after having seen a higher index, a new cycle just started. This is robust regardless of the caller's counter.

```javascript
var _prevIdx = -1;
get: function(t, p) {
  if (p === "length") return _allRP4[0].length;
  if (typeof p === "string" && !isNaN(p)) {
    var idx = Number(p);
    // Detect cycle reset: index jumped back to start
    if (idx <= 1 && _prevIdx > _allRP4[0].length / 2) {
      if (_mode === "random") {
        _currentGif = Math.floor(Math.random() * _gifSets.length);
      } else {
        _currentGif = (_currentGif + 1) % _gifSets.length;
      }
    }
    _prevIdx = idx;
    return _allRP4[_currentGif][idx];
  }
  return [][p];
}
```

---

### Task 1: Update config schema for multi-GIF

**Files:**
- Modify: `config.example.json`
- Modify: `config.json` (user's local — add new fields)

**Step 1: Add rotation config fields to config.example.json**

Add after the `displayCols` block:

```json
"// ROTATION": "Rotation mode when multiple GIFs are in gifs/. 'sequential' cycles in order, 'random' picks randomly each cycle",
"rotation": "sequential",

"// GIFS": "List of GIF filenames from gifs/ to include (in order). Empty = auto-detect all GIFs in gifs/",
"gifList": [],
```

**Step 2: Commit**

```bash
git add config.example.json
git commit -m "feat: add rotation and gifList config options"
```

---

### Task 2: Refactor build-font.py to process multiple GIFs

**Files:**
- Modify: `build-font.py`

This is the biggest change. The current flow is:
1. Find one GIF → extract frames → build font

New flow:
1. Find all GIFs (from `gifList` config or auto-detect all in `gifs/`)
2. For each GIF: extract frames to `frames/<gif_name>/`
3. Build font with all GIFs' frames, each GIF getting its own codepoint range
4. Write a manifest JSON (`gifs-manifest.json`) that the patcher reads

**Step 1: Update config loading to support multi-GIF**

Replace `SOURCE_GIF` logic with:

```python
ROTATION = cfg.get("rotation", "sequential")
GIF_LIST = cfg.get("gifList", [])
```

**Step 2: Replace `find_gif()` with `find_gifs()`**

```python
def find_gifs():
    """Find all source GIFs: from gifList config or auto-detect in gifs/."""
    if GIF_LIST:
        found = []
        for name in GIF_LIST:
            p = os.path.join(SCRIPT_DIR, "gifs", name)
            if os.path.isfile(p):
                found.append(p)
            elif os.path.isfile(os.path.join(SCRIPT_DIR, name)):
                found.append(os.path.join(SCRIPT_DIR, name))
            else:
                print(f"  Warning: GIF not found: {name}")
        return found

    gifs = sorted(glob.glob(os.path.join(SCRIPT_DIR, "gifs", "*.gif")))
    if not gifs:
        gifs = sorted(glob.glob(os.path.join(SCRIPT_DIR, "*.gif")))
    return gifs
```

**Step 3: Update `extract_frames_from_gif()` to use per-GIF subdirectories**

```python
def extract_frames_from_gif(gif_path, output_dir):
    """Extract exactly NUM_FRAMES evenly sampled frames from a GIF."""
    # Same logic but saves to output_dir instead of FRAME_DIR
    os.makedirs(output_dir, exist_ok=True)
    # ... (same extraction code, using output_dir)
```

**Step 4: Update `build_font()` main loop**

The outer structure becomes:

```python
def build_font():
    gif_paths = find_gifs()
    if not gif_paths:
        print("  Error: No GIFs found. Drop .gif files in gifs/")
        return

    num_gifs = len(gif_paths)
    print(f"  Found {num_gifs} GIF(s)")

    # Extract frames for each GIF
    gif_frame_dirs = []
    for gif_path in gif_paths:
        gif_name = os.path.splitext(os.path.basename(gif_path))[0]
        frame_dir = os.path.join(FRAME_DIR, gif_name)
        extract_frames_from_gif(gif_path, frame_dir)
        gif_frame_dirs.append((gif_name, frame_dir))

    # Build codepoints: each GIF gets NUM_FRAMES * GLYPHS_PER_FRAME codepoints
    codepoints_per_gif = NUM_FRAMES * GLYPHS_PER_FRAME
    all_codepoints = {}
    for gif_idx, (gif_name, _) in enumerate(gif_frame_dirs):
        base_cp = FIRST_CP + gif_idx * codepoints_per_gif
        for i in range(NUM_FRAMES):
            for col in range(GLYPHS_PER_FRAME):
                cp = base_cp + i * GLYPHS_PER_FRAME + col
                glyph_name = f"g{gif_idx}_frame{i:02d}_c{col}" if GLYPHS_PER_FRAME > 1 else f"g{gif_idx}_frame{i:02d}"
                all_codepoints[cp] = glyph_name

    # ... (existing font building code, but iterating over all GIFs)
    # For each GIF, process its frames and add to color_layers

    # Write manifest for the patcher
    manifest = {
        "gifs": [],
        "rotation": ROTATION,
        "displayCols": DISPLAY_COLS,
        "framesPerGif": NUM_FRAMES,
        "firstCodepoint": FIRST_CP
    }
    for gif_idx, (gif_name, _) in enumerate(gif_frame_dirs):
        base_cp = FIRST_CP + gif_idx * codepoints_per_gif
        manifest["gifs"].append({
            "name": gif_name,
            "firstCodepoint": base_cp
        })

    manifest_path = os.path.join(SCRIPT_DIR, "gifs-manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"  Manifest: {os.path.basename(manifest_path)} ({num_gifs} GIFs)")
```

**Step 5: Update `write_preview_html()` to show all GIFs**

Show each GIF's frames as a separate row with a label.

**Step 6: Test with single GIF (backward compat)**

```bash
python build-font.py
```

Expected: Same output as before, plus `gifs-manifest.json` with one GIF entry.

**Step 7: Commit**

```bash
git add build-font.py
git commit -m "feat: build-font.py processes multiple GIFs into single font"
```

---

### Task 3: Update patch-claude.js with Proxy injection

**Files:**
- Modify: `scripts/patch-claude.js`

**Step 1: Load manifest instead of computing frames from config**

Replace the frame-building section with:

```javascript
var manifestPath = path.join(__dirname, "..", "gifs-manifest.json");
if (!fs.existsSync(manifestPath)) {
  console.log("  Error: gifs-manifest.json not found. Run: python build-font.py");
  process.exit(1);
}
var manifest = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));

var DISPLAY_COLS = manifest.displayCols || 1;
var FRAMES_PER_GIF = manifest.framesPerGif || 10;
var ROTATION = manifest.rotation || "sequential";

// Build frame sets: one array per GIF
var GIF_SETS = manifest.gifs.map(function(gif) {
  var frames = [];
  var baseCP = gif.firstCodepoint;
  for (var f = 0; f < FRAMES_PER_GIF; f++) {
    var frame = "";
    for (var col = 0; col < DISPLAY_COLS; col++) {
      frame += String.fromCharCode(baseCP + f * DISPLAY_COLS + col);
    }
    frames.push(frame + " ");
  }
  return frames;
});

// First GIF's frames (for the base return value)
var FRAMES = GIF_SETS[0];
```

**Step 2: Build the Proxy injection code for CLI**

```javascript
function buildProxyCode() {
  if (GIF_SETS.length <= 1) return null; // No proxy needed for single GIF

  var gifSetsStr = JSON.stringify(GIF_SETS);
  var code = 'var _gs=' + gifSetsStr + ',' +
    '_mode="' + ROTATION + '",' +
    '_cg=0,_pi=-1,' +
    '_ar=_gs.map(function(s){var r=s.concat(s.slice().reverse().slice(1));return r});' +
    'return new Proxy([],{get:function(t,p){' +
      'if(p==="length")return _ar[0].length;' +
      'if(p===Symbol.iterator)return function(){var i=0,a=_ar[_cg];return{next:function(){return i<a.length?{value:a[i++],done:false}:{done:true}}}};' +
      'if(typeof p==="string"&&!isNaN(p)){' +
        'var idx=+p;' +
        'if(idx<=1&&_pi>_ar[0].length/2){' +
          'if(_mode==="random")_cg=Math.floor(Math.random()*_gs.length);' +
          'else _cg=(_cg+1)%_gs.length' +
        '}' +
        '_pi=idx;' +
        'return _ar[_cg][idx]' +
      '}' +
      'return[][p]' +
    '}})';
  return code;
}
```

**Step 3: Update `patchCliJs()` to inject Proxy**

For CLI, the current patch replaces `eQ6()` function body. With multi-GIF, we need to also replace the `RP4=[...LP4,...[...LP4].reverse()]` assignment.

Two patches in CLI:
1. Replace `eQ6()` to return first GIF's frames (same as now)
2. Replace `RP4=[...LP4,...[...LP4].reverse()]` with `RP4=(function(){<proxy_code>})()`

```javascript
// After patching eQ6, also patch RP4 assignment
if (GIF_SETS.length > 1) {
  var proxyCode = buildProxyCode();
  // Find: RP4=[...LP4,...[...LP4].reverse()]
  // The variable names are minified — we found LP4 and RP4 from investigation
  // We need to match the pattern generically
  var rp4Regex = /(\w+)=\[\.\.\.\w+,\.\.\.\[\.\.\.\w+\]\.reverse\(\)\]/;
  // Replace with IIFE that returns proxy
  var rp4Match = content.match(rp4Regex);
  if (rp4Match) {
    content = content.replace(rp4Regex, rp4Match[1] + '=(function(){' + proxyCode + '})()');
    count++;
  }
}
```

**Step 4: Update `patchWebview()` similarly for Gj1**

Same pattern — find `Gj1=[...Qj1,...[...Qj1].reverse()]` and replace with Proxy IIFE.

**Step 5: Test with single GIF (should behave identically — no Proxy injected)**

```bash
node scripts/patch-claude.js --restore
node scripts/patch-claude.js
```

**Step 6: Commit**

```bash
git add scripts/patch-claude.js
git commit -m "feat: inject Proxy for multi-GIF rotation in spinner"
```

---

### Task 4: Update preview.js for multi-GIF

**Files:**
- Modify: `scripts/preview.js`

**Step 1: Load manifest and show rotation**

```javascript
var manifestPath = path.join(__dirname, "..", "gifs-manifest.json");
var manifest = null;
if (fs.existsSync(manifestPath)) {
  manifest = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));
}

// Build gif sets from manifest (or fall back to single-gif config)
var GIF_SETS, ROTATION;
if (manifest && manifest.gifs.length > 1) {
  ROTATION = manifest.rotation || "sequential";
  GIF_SETS = manifest.gifs.map(function(gif) {
    var frames = [];
    var baseCP = gif.firstCodepoint;
    var dc = manifest.displayCols || 1;
    for (var f = 0; f < (manifest.framesPerGif || 10); f++) {
      var frame = "";
      for (var col = 0; col < dc; col++) {
        frame += String.fromCharCode(baseCP + f * dc + col);
      }
      frames.push(frame + " ");
    }
    return { name: gif.name, frames: frames };
  });
} else {
  // Fallback to single GIF from config
  ROTATION = "sequential";
  GIF_SETS = [{ name: config.fontName || "GIF", frames: FONT_FRAMES }];
}

var currentGif = 0;
var cycleCount = 0;
var i = 0;

setInterval(function() {
  var set = GIF_SETS[currentGif];
  process.stdout.write("\r  " + set.frames[i % set.frames.length] + " " +
    set.name + " — " + VERBS[i % VERBS.length] + "     ");
  i++;
  // Rotate GIF every full cycle
  if (i % set.frames.length === 0) {
    if (ROTATION === "random") {
      currentGif = Math.floor(Math.random() * GIF_SETS.length);
    } else {
      currentGif = (currentGif + 1) % GIF_SETS.length;
    }
  }
}, 100);
```

**Step 2: Commit**

```bash
git add scripts/preview.js
git commit -m "feat: preview.js supports multi-GIF rotation"
```

---

### Task 5: Update README and config docs

**Files:**
- Modify: `README.md`
- Modify: `config.example.json` (final form)

**Step 1: Add multi-GIF section to README**

Add after the "Using Your Own GIF" section:

```markdown
## Multiple GIFs (Rotation)

Drop multiple `.gif` files in the `gifs/` folder. The font builder packs them all into a single font, and the spinner rotates between them.

1. Drop multiple GIFs in `gifs/`
2. Run `python build-font.py`
3. Reinstall the font and re-patch

### Rotation Modes

| Mode | Behavior |
|------|----------|
| `"sequential"` | Cycles through GIFs in order (alphabetical, or `gifList` order) |
| `"random"` | Picks a random GIF each cycle |

### Controlling Order

Set `gifList` in `config.json` to control which GIFs are included and in what order:

```json
"gifList": ["parrot.gif", "nyancat.gif", "globe.gif"],
"rotation": "sequential"
```

Leave `gifList` empty (`[]`) to auto-detect all GIFs in `gifs/`.
```

**Step 2: Commit**

```bash
git add README.md config.example.json
git commit -m "docs: add multi-GIF rotation documentation"
```

---

### Task 6: End-to-end test with 2+ GIFs

**Step 1: Get a second GIF into gifs/**

User must provide a second GIF file. Ask if they have one, or use a placeholder.

**Step 2: Build font**

```bash
python build-font.py
```

Expected output shows both GIFs being processed, manifest written.

**Step 3: Install font, restore, re-patch**

```bash
# Install font (manual double-click)
node scripts/patch-claude.js --restore
node scripts/patch-claude.js
```

**Step 4: Test preview**

```bash
node scripts/preview.js
```

Expected: Animation rotates between the two GIFs.

**Step 5: Test in Claude Code**

Launch Claude Code, send a prompt, observe spinner. Send another prompt, observe it switches to the second GIF.

**Step 6: Final commit**

```bash
git add -A
git commit -m "feat: multi-GIF rotation complete"
```

---

## Risk Notes

- **Proxy compatibility:** Node.js has had Proxy since v6. Claude Code requires Node 18+, so this is safe.
- **Webview Proxy:** The webview runs in Electron/Chromium — Proxy is fully supported.
- **Symbol.iterator on Proxy:** Needed because the spread operator `[...LP4, ...LP4.reverse()]` in the existing code calls `Symbol.iterator`. If we replace RP4 after that line executes, we don't need it. But if we replace it before, we do. The plan injects the Proxy in place of the spread result, so iterator support is included as safety.
- **Font size:** Each additional GIF adds ~10-20 codepoints and ~100-200 COLR layers. A font with 5 GIFs should still be under 500KB.
- **Private Use Area space:** E000-F8FF gives 6400 codepoints. At 20 codepoints per GIF (10 frames × 2 displayCols), that's 320 GIFs max. Not a concern.
