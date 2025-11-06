// Default button colors (will be used as fallback and initial palette)
const DEFAULT_BUTTON_COLORS = [
  "#ff66de","#f98686","#7081ff","#62fe74","#fcff4d",
  "#ff7b24","#bd7ef1","#ffffff","#007EA7","#3517ab"
];

// Persist session id via localStorage (survives browser restarts).
// We still set a cookie from localStorage so fetch requests include it.
function ensureSessionId() {
  let sid = localStorage.getItem('session_id');
  if (!sid) {
    sid = (crypto && crypto.randomUUID) ? crypto.randomUUID() : ('s' + Date.now() + '-' + Math.random().toString(36).slice(2,10));
    localStorage.setItem('session_id', sid);
  }
  // Mirror into a cookie so server request handlers can read it
  // Cookie is intentionally session-length (no expires) but is overwritten on load from localStorage.
  document.cookie = 'session_id=' + encodeURIComponent(sid) + '; path=/';
}
ensureSessionId();

// Helper to load JSON
async function loadJSON(url) {
  const resp = await fetch(url, { credentials: 'same-origin' });
  if (!resp.ok) throw new Error(`Failed to fetch ${url}: ${resp.status}`);
  return await resp.json();
}

// Determine zoom max based on intrinsic canvas size (mm)
function computeZoomMaxForDims(widthMm, heightMm) {
  const m = Math.max(parseInt(widthMm || 0, 10), parseInt(heightMm || 0, 10));
  if (m < 2000) return 10;      // < 2000 x 2000 -> 1..10
  if (m < 5000) return 20;      // < 5000 x 5000 -> 1..20
  if (m < 10000) return 50;     // < 10000 x 10000 -> 1..50
  return 100;                   // otherwise 1..100
}

// Helper to POST JSON
async function postJSON(url, data) {
  await fetch(url, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(data),
    credentials: 'same-origin'
  });
}

// Dynamically create button color/off inputs
// `data` may be legacy format (string) or normalized objects { state: "on"|"off", color: "#hex" }.
function isNarrowViewport(){ return (window.innerWidth || document.documentElement.clientWidth || 0) <= 768; }

function renderButtonInputs(data) {
  const mobileC = document.getElementById('buttonInputsMobile');
  const deskC = document.getElementById('buttonInputsDesktop');
  if (mobileC) mobileC.innerHTML = '';
  if (deskC) deskC.innerHTML = '';
  const container = (isNarrowViewport() && mobileC) ? mobileC : (deskC || mobileC);
  if (!container) return;
  for (let i = 0; i <= 9; i++) {
    const btnKey = `button_${i}`;
    // Normalize incoming value into object with { state, color }
    let value = data[btnKey];
    let state = "off";
    let color = DEFAULT_BUTTON_COLORS[i];
    if (typeof value === "string") {
      if (value !== "off") {
        state = "on";
        color = value;
      } else {
        state = "off";
      }
    } else if (value && typeof value === "object") {
      state = value.state === "on" ? "on" : "off";
      color = value.color || DEFAULT_BUTTON_COLORS[i];
    }
    const inactive = (state === 'off');
    // store color in data-color so we preserve it even while off
    container.innerHTML += `
      <div style="display:inline-block; margin:0 6px; text-align:center;">
        <div id="${btnKey}_swatch" class="swatch ${inactive ? 'inactive' : ''}" title="Click to toggle on/off"
             data-color="${color}" style="${inactive ? '' : 'background:' + color}">
        </div>
      </div>
    `;
  }

  // Add event listeners: left-click -> toggle active/inactive
  for (let i = 0; i <= 9; i++) {
    const btnKey = `button_${i}`;
    const swatch = document.getElementById(btnKey + '_swatch');
    if (!swatch) continue;
    swatch.addEventListener('click', function(e) {
      // Toggle on/off
      swatch.classList.toggle('inactive');
      // If activated and no explicit background, apply stored color
      if (!swatch.classList.contains('inactive')) {
        swatch.style.background = swatch.dataset.color || '#ffffff';
      } else {
        // clear background when turned off to show the hatch pattern
        swatch.style.background = '';
      }
        // For color palette changes, recolor existing layout instead of regenerating
        autoSaveAndRecolorImmediate();
    });
  }
  // After palette renders, recompute canvas size to account for palette height (desktop)
  try {
    if (typeof recomputeCanvasSize === 'function') {
      requestAnimationFrame(() => requestAnimationFrame(() => recomputeCanvasSize()));
    }
  } catch (e) { /* ignore */ }
}

// Fill form with data.json values. Normalize legacy button fields to {state,color} and persist back.
async function fillForm() {
  const raw = await loadJSON('data.json');
  const data = Object.assign({}, raw || {});
  // Ensure knob/switch/canvas fields exist; slider is fixed at 50 and has no UI
  const knobEl = document.getElementById('knob_down');
  if (knobEl) {
    knobEl.value = data.knob_down || 1;
    // Apply dynamic zoom range based on intrinsic mm size from data.json
    const zMax = computeZoomMaxForDims(data.canvas_width || 500, data.canvas_height || 500);
    knobEl.min = '1';
    knobEl.max = String(zMax);
    // Clamp current value within the new range
    const v = Math.max(1, Math.min(zMax, parseInt(knobEl.value || '1', 10)));
    if (v !== parseInt(knobEl.value || '1', 10)) {
      knobEl.value = String(v);
    }
  }
  const zv = document.getElementById('zoomValue');
  if (zv) zv.textContent = (data.knob_down || 1);
  if (data.switch === 'left') document.getElementById('switch_left').checked = true;
  else if (data.switch === 'right') document.getElementById('switch_right').checked = true;
  else document.getElementById('switch_center').checked = true;
  // Show sizes in cm for the UI (stored internally in mm). Default to 50 cm if missing.
  document.getElementById('canvas_width').value = (data.canvas_width ? Math.round(data.canvas_width / 10) : 50);
  document.getElementById('canvas_height').value = (data.canvas_height ? Math.round(data.canvas_height / 10) : 50);

  // Normalize button fields into objects { state, color } so colors are never lost.
  let normalized = false;
  for (let i = 0; i <= 9; i++) {
    const key = `button_${i}`;
    const val = data[key];
    if (typeof val === "string") {
      // legacy: either color or "off"
      if (val === "off") {
        data[key] = { state: "off", color: DEFAULT_BUTTON_COLORS[i] };
      } else {
        data[key] = { state: "on", color: val };
      }
      normalized = true;
    } else if (!val || typeof val !== "object") {
      // missing -> initialize default as on with default color
      data[key] = { state: "on", color: DEFAULT_BUTTON_COLORS[i] };
      normalized = true;
    } else {
      // object: ensure fallback color exists
      data[key].color = data[key].color || DEFAULT_BUTTON_COLORS[i];
    }
  }

  // Render UI with normalized data
  renderButtonInputs(data);

  // If we changed structure, persist normalized data back without triggering immediate generation
  if (normalized) {
    try {
      await postJSON('/data.json', data);
    } catch (e) {
      // ignore save error; UI still usable
      console.warn('Failed to persist normalized data', e);
      showToast('Could not save normalized settings (using defaults).', 'error');
    }
  }
}

// Update zoom slider value display (guard if element exists)
const knobInitEl = document.getElementById('knob_down');
if (knobInitEl) {
  knobInitEl.oninput = function() {
    const zv = document.getElementById('zoomValue');
    if (zv) zv.textContent = this.value;
  };
}

// Update slider value display
  const sliderEl0 = document.getElementById('slider');
  if (sliderEl0) {
    sliderEl0.oninput = function() {
      const sv = document.getElementById('sliderValue');
      if (sv) sv.textContent = this.value;
    };
  }

  async function saveSettings(data) {
    await postJSON('/data.json', data);
  }

  // Build settings object from the form
  function buildSettingsFromForm() {
    const data = {};
    // Clamp knob to dynamic max according to current size (cm inputs * 10 -> mm)
    const cmW = parseInt(document.getElementById('canvas_width').value) || 50;
    const cmH = parseInt(document.getElementById('canvas_height').value) || 50;
    const zMax = computeZoomMaxForDims(cmW * 10, cmH * 10);
    const knobRaw = parseInt(document.getElementById('knob_down').value) || 1;
    data.knob_down = Math.max(1, Math.min(zMax, knobRaw));
  data.slider = 50; // fixed per new requirement
    const sw = document.querySelector('input[name="switch"]:checked');
    data.switch = sw ? sw.value : 'center';
  // Convert from cm (UI) to mm (stored/used)
  data.canvas_width = parseInt(document.getElementById('canvas_width').value) * 10;
  data.canvas_height = parseInt(document.getElementById('canvas_height').value) * 10;
    for (let i = 0; i <= 9; i++) {
      const btnKey = `button_${i}`;
  const swatch = document.getElementById(btnKey + '_swatch');
      const color = (swatch && swatch.dataset && swatch.dataset.color) ? swatch.dataset.color : DEFAULT_BUTTON_COLORS[i];
      const state = (swatch && !swatch.classList.contains('inactive')) ? "on" : "off";
      data[btnKey] = { state: state, color: color };
    }
    return data;
  }

  // Save settings then recolor all instead of generating (only for palette changes)
  async function autoSaveAndRecolorImmediate() {
    const data = buildSettingsFromForm();
    await saveSettings(data);
    try {
      await recolorAllAndSaveHistory();
    } catch (e) {
      const msg = (e && e.message) ? e.message : String(e || '');
      if (msg.includes('No regions available to recolor')) {
        // If there are no regions yet, do a one-time generate to create layout
        showToast('No regions yet. Generating a base pattern…', 'info');
        await generateAndSaveHistory();
      } else {
        // Other errors: surface and do not auto-generate
        showToast(msg || 'Recolor failed.', 'error');
        return;
      }
    }
  }

  // Note: autoSaveAndGenerate is defined later with debounce to avoid rapid re-generations during input changes.

// Attach auto-save to all inputs in the form
function attachAutoSave() {
  const form = document.getElementById('settingsForm');
  if (form) {
    form.querySelectorAll('input').forEach(input => {
      // Only width/height remain in the form; defer autosave until overlay closes
      input.oninput = () => { settingsDirty = true; };
      input.onchange = () => { settingsDirty = true; };
    });
  }
  // Also attach listeners for inputs now on the main screen
  const sliderEl = document.getElementById('slider');
  if (sliderEl) {
    // Keep for safety if element exists, but slider is removed from UI now
    sliderEl.value = 50;
    const sv = document.getElementById('sliderValue');
    if (sv) sv.textContent = 50;
    sliderEl.onchange = autoSaveAndGenerate;
  }
  const knobEl = document.getElementById('knob_down');
  if (knobEl) {
    knobEl.oninput = () => {
      const zv = document.getElementById('zoomValue');
      if (zv) zv.textContent = knobEl.value;
      // keep the track fill in sync while sliding
      const v = parseFloat(knobEl.value || '1');
      const min = parseFloat(knobEl.min || '1');
      const max = parseFloat(knobEl.max || '10');
      const pct = Math.max(0, Math.min(100, ((v - min) / (max - min)) * 100));
      knobEl.style.setProperty('--progress', pct + '%');
    };
    // Save on release
    knobEl.onchange = autoSaveAndGenerate;
  }
  document.querySelectorAll('input[name="switch"]').forEach(r => {
    r.onchange = autoSaveAndGenerate;
  });
}

// Drawing logic (optimized with Path2D cache and viewport-aware backing size)
function resolveColor(c) {
  if (!c) return "#000";
  return c;
}
// Prebuilt normalized paths in [0,1]x[0,1] space
const PATH_CACHE = (function(){
  const tri = new Path2D();
  tri.moveTo(0,0); tri.lineTo(1,0); tri.lineTo(0,1); tri.closePath();
  const half = new Path2D();
  half.rect(0,0,0.5,1);
  return { triangle: tri, halfRect: half };
})();

function drawTile(ctx, tile, x, y, size) {
  // Background (fast fill)
  ctx.fillStyle = resolveColor(tile.color_fundo);
  ctx.fillRect(x, y, size, size);

  // Foreground using cached Path2D with transform
  ctx.save();
  // translate to center, apply rotation, then scale normalized path to size
  ctx.translate(x + size/2, y + size/2);
  const ang = (tile.rotation || 0) * Math.PI / 180;
  if (ang) ctx.rotate(ang);
  ctx.translate(-size/2, -size/2);
  ctx.scale(size, size); // scale from unit space
  ctx.fillStyle = resolveColor(tile.color_padrao);
  if (tile.tile === "Padrao Quadrado") {
    ctx.fill(PATH_CACHE.halfRect);
  } else if (tile.tile === "Padrao Triangulos") {
    ctx.fill(PATH_CACHE.triangle);
  }
  ctx.restore();
}

const TILE_MARGIN_RATIO = 0.008; // 8% of tile size as margin

// Helper: detect max safe canvas dimension (uses WebGL MAX_TEXTURE_SIZE) and ensure requested canvas fits
function getMaxCanvasSize() {
  try {
    const probe = document.createElement('canvas');
    const gl = probe.getContext('webgl') || probe.getContext('experimental-webgl');
    if (!gl) return 4096;
    const max = gl.getParameter(gl.MAX_TEXTURE_SIZE);
    return (typeof max === 'number' && max > 0) ? max : 4096;
  } catch (e) {
    return 4096;
  }
}
function ensureCanvasSizeWithinLimits(reqW, reqH) {
  const maxDim = getMaxCanvasSize();
  if (reqW <= maxDim && reqH <= maxDim) return { width: reqW, height: reqH, scale: 1 };
  const scale = Math.min(maxDim / reqW, maxDim / reqH);
  const newW = Math.max(1, Math.floor(reqW * scale));
  const newH = Math.max(1, Math.floor(reqH * scale));
  return { width: newW, height: newH, scale: scale };
}

// Helper: keep large intrinsic canvas but scale the displayed size to fit the screen
function applyCanvasDisplaySize(canvas, intrinsicW, intrinsicH) {
  // how much of the patternArea viewport we allow the canvas to use
  const patternArea = document.getElementById('patternArea');
  const areaRect = patternArea ? patternArea.getBoundingClientRect() : { width: window.innerWidth, height: window.innerHeight };
// Fit the canvas into the patternArea viewport while preserving aspect ratio.
const maxViewportWidth = Math.max(1, areaRect.width - 16);  // small padding
// subtract controls height so canvas doesn't sit beneath fixed controls
const controlsEl = document.getElementById('controls');
const controlsRect = controlsEl ? controlsEl.getBoundingClientRect() : { height: 0 };
// Only reserve controls height if they're actually visible (mobile keeps them hidden until needed)
const controlsVisible = controlsEl && controlsEl.classList.contains('visible');
const reserved = controlsVisible ? Math.max(12, Math.round(controlsRect.height)) : 8;
// On desktop, also reserve the desktop palette's height so it doesn't get clipped
let reservedTop = 0;
const paletteDesktop = document.getElementById('paletteBarDesktop');
if (paletteDesktop) {
  const ph = paletteDesktop.getBoundingClientRect().height || 0;
  if (ph > 0) reservedTop = Math.round(ph + 6); // small gap
}
const maxViewportHeight = Math.max(1, areaRect.height - reserved - 8);
// Deduct top reservation (desktop palette) from height available to the canvas
const availHeight = Math.max(1, maxViewportHeight - reservedTop);
const scale = Math.min(maxViewportWidth / intrinsicW, availHeight / intrinsicH, 1);
const cssW = Math.round(intrinsicW * scale);
const cssH = Math.round(intrinsicH * scale);
canvas.style.width = cssW + 'px';
canvas.style.height = cssH + 'px';
// ensure the canvas doesn't exceed the area (safety)
canvas.style.maxWidth = Math.round(maxViewportWidth) + 'px';
canvas.style.maxHeight = Math.round(availHeight) + 'px';
  // store intrinsic size so resize handler can reapply scale
  canvas.dataset.intrinsicWidth = intrinsicW;
  canvas.dataset.intrinsicHeight = intrinsicH;
  canvas.dataset.displayScale = scale;
}

// Compute an optimal backing-buffer size so we don't render more pixels than are visible.
function computeBackingSize(intrinsicW, intrinsicH) {
  const patternArea = document.getElementById('patternArea');
  const areaRect = patternArea ? patternArea.getBoundingClientRect() : { width: window.innerWidth, height: window.innerHeight };
  const controlsEl = document.getElementById('controls');
  const controlsRect = controlsEl ? controlsEl.getBoundingClientRect() : { height: 0 };
  const controlsVisible = controlsEl && controlsEl.classList.contains('visible');
  const reserved = controlsVisible ? Math.max(12, Math.round(controlsRect.height)) : 8;
  const maxViewportWidth = Math.max(1, areaRect.width - 16);
  // Also reserve desktop palette height if present/visible
  let reservedTop = 0;
  const paletteDesktop = document.getElementById('paletteBarDesktop');
  if (paletteDesktop) {
    const ph = paletteDesktop.getBoundingClientRect().height || 0;
    if (ph > 0) reservedTop = Math.round(ph + 6);
  }
  const maxViewportHeight = Math.max(1, areaRect.height - reserved - 8);
  const availHeight = Math.max(1, maxViewportHeight - reservedTop);
  const cssScale = Math.min(maxViewportWidth / intrinsicW, availHeight / intrinsicH, 1);
  const dpr = window.devicePixelRatio || 1;
  // Backing buffer target in device pixels, limited by GPU constraints
  const targetW = Math.max(1, Math.floor(intrinsicW * cssScale * dpr));
  const targetH = Math.max(1, Math.floor(intrinsicH * cssScale * dpr));
  const limited = ensureCanvasSizeWithinLimits(targetW, targetH);
  return { width: limited.width, height: limited.height, drawScaleX: limited.width / intrinsicW, drawScaleY: limited.height / intrinsicH };
}

let currentPattern = [];
async function drawPattern() {
  const pattern = await loadJSON('pattern.json');
  currentPattern = Array.isArray(pattern) ? pattern : [];
  const data = await loadJSON('data.json');
  const canvas = document.getElementById('patternCanvas');
  const width = data.canvas_width || 500;
  const height = data.canvas_height || 500;

  // Compute backing size according to visible viewport (avoid rendering invisible pixels)
  const backing = computeBackingSize(width, height);
  canvas.width = backing.width;
  canvas.height = backing.height;
  applyCanvasDisplaySize(canvas, width, height);

  let maxX = 0, maxY = 0;
  pattern.forEach(tile => {
    if (tile.grid_x > maxX) maxX = tile.grid_x;
    if (tile.grid_y > maxY) maxY = tile.grid_y;
  });
  // When backing buffer was downscaled, we must scale drawing coordinates to match.
const drawScaleX = backing.drawScaleX;
const drawScaleY = backing.drawScaleY;
  const cols = Math.max(1, maxX);
  const rows = Math.max(1, maxY);
  const tileSize = Math.min(width / cols, height / rows);
  const margin = tileSize * TILE_MARGIN_RATIO;
  const drawSize = tileSize - margin;
  const offsetX = (width - tileSize * cols) / 2;
  const offsetY = (height - tileSize * rows) / 2;

const ctx = canvas.getContext('2d');
// Clear the full backing buffer (use adjusted size)
ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Fill background with white for margins
  ctx.fillStyle = "#fff";
ctx.fillRect(0, 0, canvas.width, canvas.height);

  pattern.forEach(tile => {
    // map display coordinates into backing-buffer coordinates if downscaled
    const x_disp = offsetX + (tile.grid_x - 1) * tileSize + margin / 2;
    const y_disp = offsetY + (tile.grid_y - 1) * tileSize + margin / 2;
    const x = x_disp * drawScaleX;
    const y = y_disp * drawScaleY;
    const size = drawSize * Math.min(drawScaleX, drawScaleY);
    drawTile(ctx, tile, x, y, size);
  });
  // After drawing, ensure the canvas CSS is sized to fit the patternArea
  recomputeCanvasSize();
  // Once layout is synced, enable floating bar interactivity
  const areaReady1 = document.getElementById('patternArea');
  if (areaReady1) areaReady1.classList.add('pattern-ui-ready');
}

// Pattern history management
let patternHistory = [];
let historyIndex = -1;
let debounceTimer = null;
// Flag to indicate a generation is in progress (server processing + waiting for pattern.json)
let isGenerationInProgress = false;
// If a generation request arrives while another is in progress, queue one follow-up run
let needsGenerateAfterCurrent = false;

// Small helper to reflect generation state in the UI
function updateGenIndicator() {
  const el = document.getElementById('genIndicator');
  if (!el) return;
  if (isGenerationInProgress) {
    el.classList.remove('hidden');
    el.classList.add('visible');
  } else {
    el.classList.remove('visible');
    el.classList.add('hidden');
  }
}

function patternsAreEqual(a, b) {
  return JSON.stringify(a) === JSON.stringify(b);
}

function loadHistory() {
  const hist = localStorage.getItem('patternHistory');
  if (hist) {
    patternHistory = JSON.parse(hist);
    // support legacy entries that were only arrays
    patternHistory = patternHistory.map(e => {
      if (Array.isArray(e)) return { pattern: e, data: null };
      return e;
    });
    historyIndex = parseInt(localStorage.getItem('historyIndex')) || (patternHistory.length - 1);
  }
  updateHistoryButtons();
}

function saveHistory() {
  const MIN_HISTORY = 15;  // user-requested minimum steps if space allows
  const MAX_HISTORY = 100; // hard cap to keep storage sane

  // Ensure we don't exceed MAX_HISTORY entries in memory
  if (patternHistory.length > MAX_HISTORY) {
    patternHistory = patternHistory.slice(patternHistory.length - MAX_HISTORY);
    historyIndex = Math.max(0, Math.min(historyIndex, patternHistory.length - 1));
  }

  // Before saving, opportunistically convert any legacy full patterns into compressed form
  for (let i = 0; i < patternHistory.length; i++) {
    const e = patternHistory[i];
    if (e && e.pattern && !e.p) {
      // compress and drop the full pattern to save space
      patternHistory[i] = { p: compressPatternRows(e.pattern), d: e.data || null, v: 1 };
    }
  }

  // helper to identify quota errors across browsers
  function isQuotaExceeded(err) {
    if (!err) return false;
    return err.name === 'QuotaExceededError' || err.name === 'NS_ERROR_DOM_QUOTA_REACHED' ||
           err.code === 22 || err.code === 1014;
  }

  // Try to persist; on quota error evict oldest entries until it fits.
  try {
    localStorage.setItem('patternHistory', JSON.stringify(patternHistory));
  } catch (e) {
    if (isQuotaExceeded(e)) {
      // First pass: ensure all entries are compressed
      let changed = false;
      for (let i = 0; i < patternHistory.length; i++) {
        const ent = patternHistory[i];
        if (ent && ent.pattern && !ent.p) {
          patternHistory[i] = { p: compressPatternRows(ent.pattern), d: ent.data || null, v: 1 };
          changed = true;
        }
      }
      if (changed) {
        try {
          localStorage.setItem('patternHistory', JSON.stringify(patternHistory));
        } catch (err2) {
          // proceed to eviction if still too big
        }
      }

      // Evict oldest until we fit, but aim to preserve at least MIN_HISTORY
      while (patternHistory.length > MIN_HISTORY) {
        patternHistory.shift(); // evict oldest
        try {
          localStorage.setItem('patternHistory', JSON.stringify(patternHistory));
          break; // saved successfully
        } catch (err) {
          if (!isQuotaExceeded(err)) {
            // unknown error, rethrow
            throw err;
          }
          // still quota exceeded -> continue evicting
        }
      }
      // If we still can't save, keep trimming even below MIN_HISTORY if necessary
      while (patternHistory.length > 1) {
        try {
          localStorage.setItem('patternHistory', JSON.stringify(patternHistory));
          break;
        } catch (err) {
          patternHistory.shift();
        }
      }
      // If still can't save (single huge entry), fall back to empty history persist while keeping in-memory
      if (patternHistory.length <= 1) {
        try {
          // As a last resort, persist an empty history, but do not change the in-memory
          // historyIndex here so the current view remains stable.
          localStorage.setItem('patternHistory', JSON.stringify([]));
        } catch (err) {
          // give up silently; nothing more we can do in localStorage
          console.warn('saveHistory: unable to persist even minimal history', err);
        }
      }
    } else {
      // not a quota problem -> rethrow so it surfaces
      throw e;
    }
  }

  // Try to persist historyIndex (best-effort)
  try {
    localStorage.setItem('historyIndex', historyIndex);
  } catch (e) {
    // ignore failures here (historyIndex is small)
    console.warn('saveHistory: failed to save historyIndex', e);
  }

  updateHistoryButtons();
}

function updateHistoryButtons() {
  document.getElementById('backBtn').disabled = historyIndex <= 0;
  document.getElementById('forwardBtn').disabled = historyIndex >= patternHistory.length - 1;
}

async function fetchCurrentPattern() {
  return await loadJSON('pattern.json');
}

async function drawPatternFromHistory(idx) {
  if (patternHistory[idx]) {
    const entry = patternHistory[idx];
    // Decompress if stored compactly
    let pattern;
    if (entry.p && Array.isArray(entry.p)) {
      pattern = decompressPatternRows(entry.p);
    } else {
      pattern = entry.pattern || entry; // support legacy
    }
    currentPattern = Array.isArray(pattern) ? pattern : [];
    // prefer saved data that matches this pattern; fallback to current data.json
    let data = entry.data;
    if (!data) {
      data = await loadJSON('data.json');
    }
    const canvas = document.getElementById('patternCanvas');
    const width = data.canvas_width || 500;
    const height = data.canvas_height || 500;

    const backing = computeBackingSize(width, height);
    canvas.width = backing.width;
    canvas.height = backing.height;
    applyCanvasDisplaySize(canvas, width, height);

    const drawScaleX = backing.drawScaleX;
    const drawScaleY = backing.drawScaleY;
    let maxX = 0, maxY = 0;
     pattern.forEach(tile => {
       if (tile.grid_x > maxX) maxX = tile.grid_x;
       if (tile.grid_y > maxY) maxY = tile.grid_y;
     });
     const cols = Math.max(1, maxX);
     const rows = Math.max(1, maxY);
     const tileSize = Math.min(width / cols, height / rows);
     const margin = tileSize * TILE_MARGIN_RATIO;
     const drawSize = tileSize - margin;
     const offsetX = (width - tileSize * cols) / 2;
     const offsetY = (height - tileSize * rows) / 2;
 
     const ctx = canvas.getContext('2d');

     ctx.clearRect(0, 0, canvas.width, canvas.height);
 
     // Fill background with white for margins
     ctx.fillStyle = "#fff";
     ctx.fillRect(0, 0, canvas.width, canvas.height);
 
     pattern.forEach(tile => {
       const x_disp = offsetX + (tile.grid_x - 1) * tileSize + margin / 2;
       const y_disp = offsetY + (tile.grid_y - 1) * tileSize + margin / 2;
       const x = x_disp * drawScaleX;
       const y = y_disp * drawScaleY;
       const size = drawSize * Math.min(drawScaleX, drawScaleY);
       drawTile(ctx, tile, x, y, size);
     });
   }
   updateHistoryButtons();
  // ensure canvas CSS fits the patternArea after drawing history
  recomputeCanvasSize();
  // Enable floating bars once positioned for history draws too
  const areaReady2 = document.getElementById('patternArea');
  if (areaReady2) areaReady2.classList.add('pattern-ui-ready');
 }
 
 // On new generation, always append to end of history (never erase forward)
async function generateAndSaveHistory() {
  // Avoid starting another generation if one is already in progress
  if (isGenerationInProgress) return;
  // POST to /generate must include credentials so cookie (mirrored from localStorage) is sent
  const generateBtn = document.getElementById('generateBtn');
// disable to avoid duplicate requests while working
generateBtn.disabled = true;
isGenerationInProgress = true;
updateGenIndicator();
  try {
    // send generate request and then poll server status for completion
    const genResp = await fetch('/generate', { method: 'POST', credentials: 'same-origin' });
    if (!genResp.ok) {
      try { const js = await genResp.json(); showToast(js && js.message ? js.message : 'Generation failed to start', 'error'); } catch {}
      throw new Error('Failed to start generation');
    }

    const timeoutMs = 60000; // 60s
    const pollInterval = 400; // 0.4s
    const deadline = Date.now() + timeoutMs;
    let status = 'running';
    while (Date.now() < deadline) {
      try {
        const resp = await fetch('/generate/status', { credentials: 'same-origin' });
        const js = await resp.json();
        status = js && js.status || 'idle';
        if (status === 'done') break;
      } catch (e) {
        // ignore transient errors
      }
      await new Promise(r => setTimeout(r, pollInterval));
    }
    if (status !== 'done') {
      showToast('Generation timed out. Try again.', 'error');
      return;
    }
    // Now fetch the latest pattern once
let pattern = [];
try { pattern = await fetchCurrentPattern(); } catch (e) { pattern = []; showToast('Failed to fetch pattern.json', 'error'); }

const data = await loadJSON('data.json'); // capture the data that produced this pattern
// Append compressed pattern+data to end of history
patternHistory.push({ p: compressPatternRows(pattern), d: data, v: 1 });
    // Limit history to 100 generations
    if (patternHistory.length > 100) {
      patternHistory = patternHistory.slice(patternHistory.length - 100);
    }
// Move draw before save so UI updates immediately even if localStorage is slow or fails
historyIndex = patternHistory.length - 1;
drawPatternFromHistory(historyIndex);
// Persist history best-effort (may evict older entries on quota pressure)
saveHistory();
  } finally {
    isGenerationInProgress = false;
    generateBtn.disabled = false;
    updateGenIndicator();
    // If any changes happened while we were generating, run one follow-up generation
    if (needsGenerateAfterCurrent) {
      needsGenerateAfterCurrent = false;
      // schedule shortly so we don't recurse deeply
      setTimeout(() => {
        generateAndSaveHistory();
      }, 50);
    }
  }
}

document.getElementById('generateBtn').onclick = generateAndSaveHistory;

// Recolor-all path shared by button and palette-change flow
async function recolorAllAndSaveHistory() {
  const resp = await fetch('/recolor-all', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin'
  });
  const js = await resp.json();
  if (!resp.ok) {
    const msg = (js && js.message) ? js.message : 'Recolor-all failed';
    throw new Error(msg);
  }
  const pattern = js.pattern || [];
  const data = await loadJSON('data.json');
  patternHistory.push({ p: compressPatternRows(pattern), d: data, v: 1 });
  if (patternHistory.length > 100) patternHistory = patternHistory.slice(-100);
  historyIndex = patternHistory.length - 1;
  await drawPatternFromHistory(historyIndex);
  saveHistory();
}

document.getElementById('backBtn').onclick = function() {
  if (historyIndex > 0) {
    historyIndex--;
    saveHistory();
    drawPatternFromHistory(historyIndex);
  }
};

document.getElementById('forwardBtn').onclick = function() {
  if (historyIndex < patternHistory.length - 1) {
    historyIndex++;
    saveHistory();
    drawPatternFromHistory(historyIndex);
  }
};

// Debounced auto-save and generate
async function autoSaveAndGenerate() {
  const data = {};
  // Clamp knob to dynamic max according to current size (cm inputs * 10 -> mm)
  (function(){
    const cmW = parseInt(document.getElementById('canvas_width').value) || 50;
    const cmH = parseInt(document.getElementById('canvas_height').value) || 50;
    const zMax = computeZoomMaxForDims(cmW * 10, cmH * 10);
    const knobRaw = parseInt(document.getElementById('knob_down').value) || 1;
    const clamped = Math.max(1, Math.min(zMax, knobRaw));
    // Reflect clamp to the UI control to avoid confusion
    const knobEl2 = document.getElementById('knob_down');
    if (knobEl2) {
      knobEl2.max = String(zMax);
      if (clamped !== knobRaw) knobEl2.value = String(clamped);
    }
    data.knob_down = clamped;
  })();
  data.slider = 50; // fixed bias per requirement
  data.switch = document.querySelector('input[name="switch"]:checked').value;
  // Convert from cm (UI) to mm (stored/used)
  data.canvas_width = parseInt(document.getElementById('canvas_width').value) * 10;
  data.canvas_height = parseInt(document.getElementById('canvas_height').value) * 10;
  for (let i = 0; i <= 9; i++) {
    const btnKey = `button_${i}`;
    const swatch = document.getElementById(btnKey + '_swatch');
    const color = (swatch && swatch.dataset && swatch.dataset.color) ? swatch.dataset.color : DEFAULT_BUTTON_COLORS[i];
    const state = (swatch && !swatch.classList.contains('inactive')) ? "on" : "off";
    data[btnKey] = { state: state, color: color };
  }
  await postJSON('/data.json', data);

  // Debounce pattern generation. If a generation is already in progress, queue one follow-up.
  if (debounceTimer) clearTimeout(debounceTimer);
  if (!isGenerationInProgress) {
    debounceTimer = setTimeout(generateAndSaveHistory, 400);
  } else {
    // mark that we need one generation after current finishes
    needsGenerateAfterCurrent = true;
    debounceTimer = null;
  }
}

// Overlay logic
const settingsOverlay = document.getElementById('settingsOverlay');
const showSettingsTabs = Array.from(document.querySelectorAll('#showSettingsTab, #showSettingsTabMobile'));
const closeSettingsBtn = document.getElementById('closeSettingsBtn');
const settingsPanel = document.getElementById('settingsPanel');
let settingsDirty = false; // track if size inputs changed while settings open

function closeSettingsAndApply() {
  settingsOverlay.style.display = 'none';
  showSettingsTab.style.display = 'flex';
  document.body.classList.remove('settings-open');
  // Apply changes only once when closing
  if (settingsDirty) {
    settingsDirty = false;
    // Save and generate with the new size
    autoSaveAndGenerate();
  }
}

showSettingsTabs.forEach(tab => {
  if (!tab) return;
  tab.onclick = function(){
    settingsOverlay.style.display = 'flex';
    document.body.classList.add('settings-open');
    settingsDirty = false;
  };
});
if (closeSettingsBtn) {
  closeSettingsBtn.onclick = function() {
    closeSettingsAndApply();
  };
}
// Click outside panel closes overlay
settingsOverlay.onclick = function(e) {
  if (e.target === settingsOverlay) {
    closeSettingsAndApply();
  }
};

// Re-render palette in correct container on orientation/width change
window.addEventListener('resize', async () => {
  try {
    const raw = await loadJSON('data.json');
    await renderButtonInputs(raw || {});
  } catch (e) { /* ignore */ }
});

// Mobile top toolbar show/hide logic
(function(){
  const toolbar = document.getElementById('topToolbar');
  const handle = document.getElementById('topToolbarHandle');
  if (!toolbar || !handle) return;
  function isMobile(){ return isNarrowViewport(); }
  function show(){ document.body.classList.add('top-toolbar-visible'); }
  function hide(){ document.body.classList.remove('top-toolbar-visible'); }
  handle.addEventListener('click', () => { show(); }, { passive: true });
  document.addEventListener('click', (e)=>{
    if (!isMobile()) return;
    const t = e.target;
    const inside = toolbar.contains(t) || handle.contains(t);
    if (!inside){ hide(); }
  }, { capture: true, passive: true });
  window.addEventListener('resize', ()=>{ if (!isMobile()) { document.body.classList.remove('top-toolbar-visible'); } });
})();

// Initial load
// Ensure session cookie mirrors localStorage on every load before requests start
ensureSessionId();
fillForm().then(attachAutoSave);
loadHistory();
updateGenIndicator();
// If history exists, draw last pattern, else draw current
if (patternHistory.length > 0) {
  drawPatternFromHistory(historyIndex);
} else {
  drawPattern();
}

// Generate drawing instructions from a pattern array
function getDrawingInstructions(pattern) {
  let instructions = [];
  pattern.forEach((tile, idx) => {
    instructions.push(
      `Tile ${idx + 1}: Type=${tile.tile}, Grid=(${tile.grid_x},${tile.grid_y}), Rotation=${tile.rotation || 0}, ` +
      `Background=${tile.color_fundo}, PatternColor=${tile.color_padrao}`
    );
  });
  return instructions.join('\n');
}

// Export current pattern as a JPEG image (fits within device capabilities)
async function exportPatternJPEG(pattern, data, filename = 'pepe_pattern.jpg', quality = 0.92) {
  try {
    const intrinsicW = parseInt((data && data.canvas_width) || 500);
    const intrinsicH = parseInt((data && data.canvas_height) || 500);
    const limited = ensureCanvasSizeWithinLimits(intrinsicW, intrinsicH);
    const outW = Math.max(1, limited.width);
    const outH = Math.max(1, limited.height);

    // Offscreen canvas render
    const off = document.createElement('canvas');
    off.width = outW; off.height = outH;
    const ctx = off.getContext('2d');
    // white background
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, outW, outH);

    // Layout same as drawPattern but using export dimensions
    let maxX = 0, maxY = 0;
    pattern.forEach(tile => {
      if (tile.grid_x > maxX) maxX = tile.grid_x;
      if (tile.grid_y > maxY) maxY = tile.grid_y;
    });
    const cols = Math.max(1, maxX);
    const rows = Math.max(1, maxY);
    const tileSize = Math.min(outW / cols, outH / rows);
    const margin = tileSize * TILE_MARGIN_RATIO;
    const drawSize = tileSize - margin;
    const offsetX = (outW - tileSize * cols) / 2;
    const offsetY = (outH - tileSize * rows) / 2;

    pattern.forEach(tile => {
      const x = offsetX + (tile.grid_x - 1) * tileSize + margin / 2;
      const y = offsetY + (tile.grid_y - 1) * tileSize + margin / 2;
      drawTile(ctx, tile, x, y, drawSize);
    });

    const doDownload = (blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = filename;
      document.body.appendChild(a);
      a.click();
      setTimeout(() => { document.body.removeChild(a); URL.revokeObjectURL(url); }, 250);
    };

    if (off.toBlob) {
      off.toBlob((blob) => { if (blob) doDownload(blob); }, 'image/jpeg', quality);
    } else {
      const dataUrl = off.toDataURL('image/jpeg', quality);
      // Convert dataURL to Blob
      const byteString = atob(dataUrl.split(',')[1]);
      const mimeString = dataUrl.split(',')[0].split(':')[1].split(';')[0];
      const ab = new ArrayBuffer(byteString.length);
      const ia = new Uint8Array(ab);
      for (let i = 0; i < byteString.length; i++) ia[i] = byteString.charCodeAt(i);
      doDownload(new Blob([ab], { type: mimeString }));
    }
  } catch (e) {
    console.warn('exportPatternJPEG failed', e);
    showToast('Could not export JPG.', 'error');
  }
}

// Print button logic — now also downloads a JPG snapshot of the pattern
document.getElementById('printBtn').onclick = async function() {
  const entry = patternHistory[historyIndex];
  // Prefer the currently drawn pattern to guarantee latest edits are included
  const pattern = (currentPattern && currentPattern.length) ? currentPattern : (entry ? (entry.pattern || entry) : []);
  // 1) Download instructions txt
  const instructions = getDrawingInstructions(pattern);
  const blob = new Blob([instructions], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `pepe_pattern_instructions.txt`;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, 100);

  // 2) Also export a JPG of the pattern drawing
  let data;
  try { data = await loadJSON('data.json'); } catch(e) { data = { canvas_width: 500, canvas_height: 500 }; }
  await exportPatternJPEG(pattern, data, 'pepe_pattern.jpg', 0.92);
};

// Keep displayed canvas scaled properly when the window resizes
// Recompute canvas CSS size when the window or pattern area change size
function recomputeCanvasSize() {
  const canvas = document.getElementById('patternCanvas');
  const iw = parseInt(canvas.dataset.intrinsicWidth || 0, 10);
  const ih = parseInt(canvas.dataset.intrinsicHeight || 0, 10);
  if (iw && ih) applyCanvasDisplaySize(canvas, iw, ih);
  // keep overlay aligned with the canvas
  if (typeof syncOverlayToCanvas === 'function') syncOverlayToCanvas();
  // Mark UI ready on any subsequent layout updates as well
  const areaReady3 = document.getElementById('patternArea');
  if (areaReady3) areaReady3.classList.add('pattern-ui-ready');
}
window.addEventListener('resize', recomputeCanvasSize);
// Observe patternArea size changes (use ResizeObserver if available)
const patternAreaEl = document.getElementById('patternArea');
if (window.ResizeObserver && patternAreaEl) {
  const ro = new ResizeObserver(recomputeCanvasSize);
  ro.observe(patternAreaEl);
}
// Observe controls size changes so we can reserve the correct bottom space
const controlsEl = document.getElementById('controls');
if (window.ResizeObserver && controlsEl) {
  const cro = new ResizeObserver(recomputeCanvasSize);
  cro.observe(controlsEl);
}
// Observe desktop palette height changes to reflow canvas on first render and later wraps
const paletteDesktopEl = document.getElementById('paletteBarDesktop');
if (window.ResizeObserver && paletteDesktopEl) {
  const pro = new ResizeObserver(recomputeCanvasSize);
  pro.observe(paletteDesktopEl);
}
// Recompute after window load to catch late style/layout or font loading
window.addEventListener('load', () => {
  if (typeof recomputeCanvasSize === 'function') recomputeCanvasSize();
});

// Keep the overlay canvas aligned and scaled to the visible pattern canvas
function syncOverlayToCanvas() {
  const area = document.getElementById('patternArea');
  const canvas = document.getElementById('patternCanvas');
  const overlay = document.getElementById('overlayCanvas');
  const paletteBar = document.getElementById('paletteBar');
  const shapeBar = document.getElementById('shapeBar');
  const zoomBar = document.getElementById('zoomBar');
  const zoomHandle = document.getElementById('zoomHandle');
  if (!area || !canvas || !overlay) return;
  const areaRect = area.getBoundingClientRect();
  const canvasRect = canvas.getBoundingClientRect();
  const cssW = Math.max(1, Math.round(canvasRect.width));
  const cssH = Math.max(1, Math.round(canvasRect.height));
  overlay.style.width = cssW + 'px';
  overlay.style.height = cssH + 'px';
  overlay.style.left = Math.round(canvasRect.left - areaRect.left) + 'px';
  overlay.style.top = Math.round(canvasRect.top - areaRect.top) + 'px';
  const dpr = window.devicePixelRatio || 1;
  const newW = Math.max(1, Math.floor(cssW * dpr));
  const newH = Math.max(1, Math.floor(cssH * dpr));
  if (overlay.width !== newW) overlay.width = newW;
  if (overlay.height !== newH) overlay.height = newH;
  // clear any previous drawings when size changes
  const octx = overlay.getContext('2d');
  octx.clearRect(0, 0, overlay.width, overlay.height);

  // Align floating UI elements to the visible canvas, not the whole area
  const baseLeft = Math.round(canvasRect.left - areaRect.left);
  const baseTop = Math.round(canvasRect.top - areaRect.top);
  // Palette bar is now in-flow above the canvas; do not set absolute positioning here
  // Shape bar is now part of the controls; no absolute positioning here
  // Zoom bar pinned to top-right of canvas
  if (zoomBar) {
    // Anchor to the top of the canvas (no extra offset) and match its visible height
    const pyTop = baseTop;
    // Do not set left; keep CSS right anchoring
    zoomBar.style.left = '';
    zoomBar.style.top = pyTop + 'px';
    // Match the zoom bar container height to the displayed canvas height (force override)
    if (zoomBar.style && zoomBar.style.setProperty) {
      zoomBar.style.setProperty('height', cssH + 'px', 'important');
    } else {
      zoomBar.style.height = cssH + 'px';
    }
    // Ensure the internal range travel matches the full height minus padding
    const padTop = 6, padBottom = 6; // keep in sync with CSS padding on #zoomBar
    const extraInset = 10; // additional top/bottom inset inside the content box
    const innerTravel = Math.max(60, cssH - (padTop + padBottom) - (2 * extraInset));
  const rangeEl = zoomBar.querySelector('input[type="range"]');
    if (rangeEl) {
      // Use native vertical slider: height controls the vertical travel; width is thickness
      if (rangeEl.style && rangeEl.style.setProperty) {
        rangeEl.style.setProperty('height', innerTravel + 'px', 'important');
        rangeEl.style.setProperty('width', '28px', 'important');
      } else {
        rangeEl.style.height = innerTravel + 'px';
        rangeEl.style.width = '28px';
      }
      // ensure Firefox uses vertical orientation hint
      try { rangeEl.setAttribute('orient', 'vertical'); } catch(e) {}
      rangeEl.min = '1';
      // Determine max based on intrinsic canvas size; fallback to inputs if dataset missing
      let iw = parseInt(canvas.dataset.intrinsicWidth || '0', 10);
      let ih = parseInt(canvas.dataset.intrinsicHeight || '0', 10);
      if (!(iw > 0 && ih > 0)) {
        const formWcm = parseInt(document.getElementById('canvas_width')?.value || '50', 10);
        const formHcm = parseInt(document.getElementById('canvas_height')?.value || '50', 10);
        iw = formWcm * 10; ih = formHcm * 10;
      }
      const dynMax = computeZoomMaxForDims(iw, ih);
      rangeEl.max = String(dynMax);
      rangeEl.step = '1';
      // Update CSS variable for progress fill (WebKit) based on current value
      // Clamp current value to new max if needed
      let vNum = parseInt(rangeEl.value || '1', 10);
      if (vNum > dynMax) {
        vNum = dynMax;
        rangeEl.value = String(vNum);
      }
      const v = parseFloat(String(vNum));
      const min = parseFloat(rangeEl.min || '1');
      const max = parseFloat(rangeEl.max || '100');
      const pct = Math.max(0, Math.min(100, ((v - min) / (max - min)) * 100));
      rangeEl.style.setProperty('--progress', pct + '%');
    }
    zoomBar.style.transform = ''; // no centering for corner pin
    // Preserve CSS right/bottom from stylesheet
  }
  // Position the zoom handle aligned with the canvas top on mobile
  if (zoomHandle) {
    const baseTop = Math.round(canvasRect.top - areaRect.top);
    zoomHandle.style.top = (baseTop + 8) + 'px';
  }
}

// Zoom slider replaces image-based potentiometer; handled via #knob_down input in attachAutoSave
// Auto-hide controls on small screens: show on interaction, hide after idle
(function(){
  const controls = document.getElementById('controls');
  const handle = document.getElementById('controlsHandle');
  if (!controls || !handle) return;

  const IDLE_MS = 2500; // hide after 2.5s of inactivity
  let idleTimer = null;
  let isManualOpen = false; // user explicitly opened controls via handle

  function isSmallViewport() {
    return window.innerHeight < 1700 || window.innerWidth < 1700; // heuristic
  }

  function showControls() {
    controls.classList.remove('hidden');
    controls.classList.add('visible');
    handle.style.opacity = '0';
    handle.style.pointerEvents = 'none';
    // Mark controls visible so shape bar lifts above controls bar
    document.body.classList.add('controls-visible');
  }

  function hideControls() {
    if (isManualOpen) return; // don't auto-hide if user pinned it open
    controls.classList.add('hidden');
    controls.classList.remove('visible');
    handle.style.opacity = '1';
    handle.style.pointerEvents = 'auto';
    // Controls hidden -> drop the lift
    document.body.classList.remove('controls-visible');
  }

  function resetIdle() {
    if (idleTimer) clearTimeout(idleTimer);
    // On mobile, we only show on handle click; don't auto-hide by timer.
    if (!isSmallViewport()) {
      idleTimer = setTimeout(hideControls, IDLE_MS);
    }
  }

  // Show on pointer/move/touch
  ['mousemove','pointermove','touchstart','touchmove'].forEach(evt => {
    window.addEventListener(evt, () => {
      // Only auto-show on larger screens; on mobile, require handle click
      if (!isSmallViewport()) {
        showControls();
        resetIdle();
      }
    }, { passive: true });
  });

  // Handle: toggle manual open/close on click or tap
  handle.addEventListener('click', (e) => {
    isManualOpen = !isManualOpen;
    if (isManualOpen) {
      showControls();
    } else {
      hideControls();
    }
  });

  // Hide controls when clicking/tapping outside them on mobile
  document.addEventListener('click', (e) => {
    if (!isSmallViewport()) return; // only on mobile
    const target = e.target;
    const clickedInsideControls = controls.contains(target) || handle.contains(target);
    if (!clickedInsideControls && controls.classList.contains('visible')) {
      isManualOpen = false;
      hideControls();
    }
  }, { capture: true, passive: true });

  // Recompute behaviour on resize
  window.addEventListener('resize', () => {
    if (!isSmallViewport()) {
      // always visible on large screens
      controls.classList.remove('hidden');
      controls.classList.add('visible');
      handle.style.opacity = '0';
    } else {
      // On mobile: keep controls hidden until handle tapped
      isManualOpen = false;
      controls.classList.add('hidden');
      controls.classList.remove('visible');
      handle.style.opacity = '1';
      handle.style.pointerEvents = 'auto';
      document.body.classList.remove('controls-visible');
    }
  });

  // initialize
  if (isSmallViewport()) {
    // Mobile: start hidden; show only when handle is tapped
    isManualOpen = false;
    controls.classList.add('hidden');
    controls.classList.remove('visible');
    handle.style.opacity = '1';
    handle.style.pointerEvents = 'auto';
    document.body.classList.remove('controls-visible');
  } else {
    showControls();
  }
})();

// Mobile retractable zoom: show on handle tap, hide on outside tap
(function(){
  const zoomBar = document.getElementById('zoomBar');
  const zoomHandle = document.getElementById('zoomHandle');
  function isMobile(){ return (window.innerWidth || document.documentElement.clientWidth || 0) <= 768; }
  if (!zoomBar || !zoomHandle) return;
  // Start hidden on mobile
  if (isMobile()) { document.body.classList.remove('zoom-visible'); }
  zoomHandle.addEventListener('click', ()=>{
    if (!isMobile()) return;
    document.body.classList.add('zoom-visible');
  }, { passive: true });
  document.addEventListener('click', (e)=>{
    if (!isMobile()) return;
    const t = e.target;
    const inside = zoomBar.contains(t) || zoomHandle.contains(t);
    if (!inside) { document.body.classList.remove('zoom-visible'); }
  }, { capture: true, passive: true });
  window.addEventListener('resize', ()=>{
    if (!isMobile()) {
      // Ensure zoom is visible by default on desktop
      document.body.classList.add('zoom-visible');
    } else {
      // Hide by default on mobile until user taps handle
      document.body.classList.remove('zoom-visible');
    }
  });
})();

// ---- Division-level edit interactions ----
(function(){
  const canvas = document.getElementById('patternCanvas');
  if (!canvas) return;
  const overlay = document.getElementById('overlayCanvas');

  // Magic Wand state
  let wandMode = false;
  let wandFirst = null;
  const wandBtn = document.getElementById('magicWandBtn');
  function setWand(active){
    wandMode = !!active;
    wandFirst = null;
    if (wandBtn){ wandBtn.classList.toggle('active', wandMode); wandBtn.textContent = wandMode ? '✨ Wand: pick 2 tiles' : '✨ Magic Wand'; }
    if (!wandMode) { clearOverlay(); }
    // ensure overlay is sized when toggling on
    if (wandMode && typeof syncOverlayToCanvas === 'function') syncOverlayToCanvas();
  }
  if (wandBtn){ wandBtn.addEventListener('click', ()=> setWand(!wandMode)); }

  function clearOverlay(){
    if (!overlay) return;
    const octx = overlay.getContext('2d');
    octx.clearRect(0, 0, overlay.width, overlay.height);
  }

  // Compute layout in intrinsic coordinates and the CSS display scale
  function getLayout(){
    const iw = parseInt(canvas.dataset.intrinsicWidth || canvas.width, 10);
    const ih = parseInt(canvas.dataset.intrinsicHeight || canvas.height, 10);
    if (!iw || !ih || !currentPattern || !currentPattern.length) return null;
    let maxX = 0, maxY = 0;
    currentPattern.forEach(t => { if (t.grid_x > maxX) maxX = t.grid_x; if (t.grid_y > maxY) maxY = t.grid_y; });
    const cols = Math.max(1, maxX);
    const rows = Math.max(1, maxY);
    const tileSize = Math.min(iw / cols, ih / rows);
    const margin = tileSize * TILE_MARGIN_RATIO;
    const offsetX = (iw - tileSize * cols) / 2;
    const offsetY = (ih - tileSize * rows) / 2;
    const displayScale = parseFloat(canvas.dataset.displayScale || '1') || 1;
    return { iw, ih, cols, rows, tileSize, margin, offsetX, offsetY, displayScale };
  }

  function drawWandOverlay(hover){
    if (!overlay) return;
    if (!wandMode || !wandFirst || !hover) { clearOverlay(); return; }
    const L = getLayout();
    if (!L) { clearOverlay(); return; }
    const x0 = Math.min(wandFirst.grid_x, hover.grid_x);
    const x1 = Math.max(wandFirst.grid_x, hover.grid_x);
    const y0 = Math.min(wandFirst.grid_y, hover.grid_y);
    const y1 = Math.max(wandFirst.grid_y, hover.grid_y);

    // rectangle in intrinsic display coords (like drawPattern x_disp / drawSize union)
    const startX = L.offsetX + (x0 - 1) * L.tileSize + L.margin / 2;
    const startY = L.offsetY + (y0 - 1) * L.tileSize + L.margin / 2;
    const selW = (x1 - x0 + 1) * L.tileSize - L.margin;
    const selH = (y1 - y0 + 1) * L.tileSize - L.margin;

    // convert to CSS pixels via displayScale, then to overlay backing pixels via DPR
    const cssX = startX * L.displayScale;
    const cssY = startY * L.displayScale;
    const cssW = selW * L.displayScale;
    const cssH = selH * L.displayScale;
    const dpr = window.devicePixelRatio || 1;
    const pxX = Math.round(cssX * dpr);
    const pxY = Math.round(cssY * dpr);
    const pxW = Math.max(1, Math.round(cssW * dpr));
    const pxH = Math.max(1, Math.round(cssH * dpr));

    const octx = overlay.getContext('2d');
    octx.clearRect(0, 0, overlay.width, overlay.height);
    octx.save();
    octx.strokeStyle = 'rgba(0,128,255,0.85)';
    octx.fillStyle = 'rgba(0,128,255,0.18)';
    octx.lineWidth = Math.max(1, Math.round(2 * dpr));
    octx.beginPath();
    octx.rect(pxX + 0.5, pxY + 0.5, pxW - 1, pxH - 1);
    octx.fill();
    octx.stroke();
    octx.restore();
  }

  function getGridFromEvent(e){
    const rect = canvas.getBoundingClientRect();
    const cssW = rect.width || 1;
    const cssH = rect.height || 1;
    const dx = (e.clientX - rect.left);
    const dy = (e.clientY - rect.top);
    // convert from CSS pixels to backing buffer pixels
    const backX = dx * (canvas.width / cssW);
    const backY = dy * (canvas.height / cssH);

    const iw = parseInt(canvas.dataset.intrinsicWidth || canvas.width, 10);
    const ih = parseInt(canvas.dataset.intrinsicHeight || canvas.height, 10);
    const width = iw || canvas.width;
    const height = ih || canvas.height;

    // reconstruct layout like drawPattern
    let maxX = 0, maxY = 0;
    currentPattern.forEach(t => { if (t.grid_x > maxX) maxX = t.grid_x; if (t.grid_y > maxY) maxY = t.grid_y; });
    const cols = Math.max(1, maxX);
    const rows = Math.max(1, maxY);
    const tileSize = Math.min(width / cols, height / rows);
    const margin = tileSize * TILE_MARGIN_RATIO;
    const offsetX = (width - tileSize * cols) / 2;
    const offsetY = (height - tileSize * rows) / 2;

    // drawing buffer scale factors
    const drawScaleX = canvas.width / width;
    const drawScaleY = canvas.height / height;
    // invert to logical (intrinsic) coordinates used for layout
    const x_disp = backX / drawScaleX;
    const y_disp = backY / drawScaleY;

    const gx = Math.floor((x_disp - offsetX) / tileSize) + 1;
    const gy = Math.floor((y_disp - offsetY) / tileSize) + 1;
    if (gx < 1 || gy < 1 || gx > cols || gy > rows) return null;
    return { grid_x: gx, grid_y: gy };
  }

async function postWand(x1,y1,x2,y2){
    try{
      const resp = await fetch('/magic-wand', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({ x1, y1, x2, y2 })
      });
      const js = await resp.json();
      if (!resp.ok) throw new Error(js && js.message || 'Magic wand failed');
      const pattern = js.pattern || [];
      const data = await loadJSON('data.json');
      patternHistory.push({ p: compressPatternRows(pattern), d: data, v: 1 });
      if (patternHistory.length > 100) patternHistory = patternHistory.slice(-100);
      historyIndex = patternHistory.length - 1;
      await drawPatternFromHistory(historyIndex);
      saveHistory();
    }catch(err){ console.warn('magic-wand failed', err); showToast('Magic wand failed. Please try again.', 'error'); }
  }

async function postEdit(region_id, action){
    try{
      const resp = await fetch('/edit-region', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({ region_id, action })
      });
      const js = await resp.json();
      if (!resp.ok) throw new Error(js && js.message || 'Edit failed');
      const pattern = js.pattern || [];
      // push compressed to history and draw
      const data = await loadJSON('data.json');
      patternHistory.push({ p: compressPatternRows(pattern), d: data, v: 1 });
      if (patternHistory.length > 100) patternHistory = patternHistory.slice(-100);
      historyIndex = patternHistory.length - 1;
      await drawPatternFromHistory(historyIndex);
      saveHistory();
    }catch(err){
      console.warn('edit-region failed', err);
      showToast('Edit failed. Please try again.', 'error');
    }
  }

  // Recolor all regions
  const recolorAllBtn = document.getElementById('recolorAllBtn');
  async function recolorAll(){
    if (!recolorAllBtn) return;
    recolorAllBtn.disabled = true;
    try{
        await recolorAllAndSaveHistory();
        showToast('Recolored all regions', 'success');
      }catch(err){
        console.warn('recolor-all failed', err);
        showToast(err.message || 'Recolor-all failed', 'error');
      } finally {
        recolorAllBtn.disabled = false;
      }
  }
  if (recolorAllBtn) recolorAllBtn.addEventListener('click', recolorAll);

  canvas.addEventListener('click', async (e)=>{
    const g = getGridFromEvent(e);
    if (!g) return;
    if (wandMode){
      if (!wandFirst){
        wandFirst = g;
        // draw single-tile overlay to indicate first selection
        drawWandOverlay(g);
      } else {
        const a = wandFirst; const b = g;
        setWand(false);
        clearOverlay();
        await postWand(a.grid_x, a.grid_y, b.grid_x, b.grid_y);
      }
      return;
    }
    // find tile
    const tile = currentPattern.find(t => t.grid_x === g.grid_x && t.grid_y === g.grid_y);
    if (!tile || tile.region_id == null) return;
    await postEdit(tile.region_id, 'reroll');
  });

  // Right-click -> recolor
  canvas.addEventListener('contextmenu', async (e)=>{
    e.preventDefault();
    const g = getGridFromEvent(e);
    if (!g) return false;
    if (wandMode){ return false; }
    const tile = currentPattern.find(t => t.grid_x === g.grid_x && t.grid_y === g.grid_y);
    if (!tile || tile.region_id == null) return false;
    await postEdit(tile.region_id, 'recolor');
    return false;
  });

  // Basic long-press for touch recolor
  let touchTimer = null;
  canvas.addEventListener('touchstart', (e)=>{
    if (touchTimer) clearTimeout(touchTimer);
    const touch = e.touches && e.touches[0];
    if (!touch) return;
    const ev = { clientX: touch.clientX, clientY: touch.clientY };
    touchTimer = setTimeout(async ()=>{
      const g = getGridFromEvent(ev);
      if (!g) return;
      const tile = currentPattern.find(t => t.grid_x === g.grid_x && t.grid_y === g.grid_y);
      if (!tile || tile.region_id == null) return;
      await postEdit(tile.region_id, 'recolor');
    }, 550);
  }, { passive: true });
  canvas.addEventListener('touchend', ()=>{ if (touchTimer) { clearTimeout(touchTimer); touchTimer = null; } }, { passive: true });
  canvas.addEventListener('touchmove', ()=>{ if (touchTimer) { clearTimeout(touchTimer); touchTimer = null; } }, { passive: true });

  // Hover visualization for Magic Wand
  canvas.addEventListener('mousemove', (e)=>{
    if (!wandMode || !wandFirst) { clearOverlay(); return; }
    const g = getGridFromEvent(e);
    drawWandOverlay(g);
  });
  canvas.addEventListener('mouseleave', ()=>{ clearOverlay(); });
})();

// Compact pattern codec to store more steps in localStorage
// Row format: [gx, gy, t, r, cf, cp, rid] where t: 0=Quadrado,1=Triangulos
function compressPatternRows(pattern){
  const rows = [];
  for (let i = 0; i < pattern.length; i++){
    const t = pattern[i];
    const tt = (t.tile === 'Padrao Quadrado') ? 0 : 1;
    rows.push([
      t.grid_x|0, t.grid_y|0,
      tt,
      (t.rotation|0) || 0,
      t.color_fundo || '#000',
      t.color_padrao || '#000',
      (t.region_id==null? null : (t.region_id|0))
    ]);
  }
  return rows;
}
function decompressPatternRows(rows){
  const out = new Array(rows.length);
  for (let i = 0; i < rows.length; i++){
    const r = rows[i];
    out[i] = {
      grid_x: r[0]|0,
      grid_y: r[1]|0,
      tile: (r[2] === 0) ? 'Padrao Quadrado' : 'Padrao Triangulos',
      rotation: r[3]|0,
      color_fundo: r[4],
      color_padrao: r[5],
      region_id: (r[6] == null ? null : (r[6]|0))
    };
  }
  return out;
}
// Simple toast helper
function showToast(message, type = 'info', ms = 3200) {
  try {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.innerHTML = `<span>${escapeHtml(String(message || ''))}</span><span class="close" aria-label="Close">✕</span>`;
    const closer = el.querySelector('.close');
    if (closer) closer.onclick = () => { container.removeChild(el); };
    container.appendChild(el);
    setTimeout(() => { if (el.parentNode === container) container.removeChild(el); }, ms);
  } catch (e) { /* ignore */ }
}
function escapeHtml(s){
  return s.replace(/[&<>\"]+/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[ch]));
}
