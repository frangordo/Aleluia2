from flask import Flask, send_from_directory, jsonify, request, send_file, abort
import subprocess
import os
import sys
import uuid
import time
import json
import threading
from concurrent.futures import ThreadPoolExecutor

# Optional speed-ups (safe fallbacks if unavailable)
try:
    import orjson as _orjson  # ultra-fast json
except Exception:
    _orjson = None
try:
    from flask_compress import Compress as _FlaskCompress
except Exception:
    _FlaskCompress = None

# For region-level editing, import helpers from PepesMachine
try:
    import PepesMachine as pm
except Exception:
    pm = None

USER_DATA_DIR = os.path.join(os.path.dirname(__file__), 'user_data')
os.makedirs(USER_DATA_DIR, exist_ok=True)

# Serve the dedicated ./static folder under the URL path /static
app = Flask(__name__, static_folder='static')

# Enable gzip compression for JSON where supported (no-op if package missing)
if _FlaskCompress is not None:
    _FlaskCompress(app)

# CONFIGURABLE QUOTAS (set via env vars)
USER_DATA_MAX_BYTES = int(os.environ.get('USER_DATA_MAX_BYTES', 50 * 1024 * 1024))  # default 50 MB
USER_DATA_MAX_FILES = int(os.environ.get('USER_DATA_MAX_FILES', 1000))              # default 1000 files
USER_DATA_MAX_AGE_DAYS = int(os.environ.get('USER_DATA_MAX_AGE_DAYS', 30))         # delete files older than 30 days

def cleanup_user_data(max_bytes=USER_DATA_MAX_BYTES, max_files=USER_DATA_MAX_FILES, max_age_days=USER_DATA_MAX_AGE_DAYS):
    """
    Remove oldest or stale files from user_data to keep total usage under quotas.
    Safe, idempotent; uses mtime to decide eviction order and respects the global data.json/pattern.json.
    """
    try:
        now = time.time()
        files = []
        total = 0
        for name in os.listdir(USER_DATA_DIR):
            path = os.path.join(USER_DATA_DIR, name)
            if not os.path.isfile(path):
                continue
            # skip any accidental global files
            if name in ('data.json', 'pattern.json'):
                continue
            st = os.stat(path)
            size = st.st_size
            mtime = st.st_mtime
            files.append((path, size, mtime))
            total += size

        # Remove files older than max_age_days first
        cutoff = now - (max_age_days * 24 * 3600)
        removed_any = False
        for path, size, mtime in list(files):
            if mtime < cutoff:
                try:
                    os.remove(path)
                    total -= size
                    removed_any = True
                except Exception:
                    pass
        if removed_any:
            # rebuild list/total after removals
            files = [(p,s,m) for (p,s,m) in files if os.path.exists(p)]
            total = sum(s for (_,s,_) in files)

        # If still over size or count limits, evict oldest files (LRU by mtime)
        if total > max_bytes or len(files) > max_files:
            files.sort(key=lambda x: x[2])  # oldest first
            for path, size, mtime in files:
                try:
                    os.remove(path)
                    total -= size
                except Exception:
                    pass
                if total <= max_bytes and len([1 for f in os.listdir(USER_DATA_DIR) if os.path.isfile(os.path.join(USER_DATA_DIR,f))]) <= max_files:
                    break
    except Exception as e:
        # logging to stdout so Render captures it; don't crash the request
        print("cleanup_user_data error:", e)

# Call cleanup at key points:
# - after a user POST to /data.json (to limit growth caused by new per-session files)
# - before/after /generate to reduce risk of disk exhaustion during generation.
# Insert calls in the relevant handlers below:


# -------- JSON helpers (use orjson when available) --------
def _json_load_file(path, default=None):
    try:
        with open(path, 'rb') as f:
            data = f.read()
        if _orjson is not None:
            return _orjson.loads(data)
        return json.loads(data.decode('utf-8'))
    except Exception:
        return default


def _json_dump_file(obj, path):
    try:
        if _orjson is not None:
            data = _orjson.dumps(obj, option=_orjson.OPT_NON_STR_KEYS)
        else:
            data = json.dumps(obj, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(data)
        return True
    except Exception as e:
        print("json dump error:", e)
        return False


# -------- Generation Job Manager (per-session, last-write-wins) --------
_pm_global_lock = threading.Lock()  # serialize in-process generation (pm has module-level globals)
_job_states = {}  # sid -> { 'version': int, 'running': bool }
_job_states_lock = threading.Lock()
_executor = ThreadPoolExecutor(max_workers=1)  # single worker due to pm global state


def _pattern_path_for(sid):
    if not sid:
        return os.path.join(os.path.dirname(__file__), 'pattern.json')
    return os.path.join(USER_DATA_DIR, f"pattern_{sid}.json")


def _regions_path_for(sid):
    if not sid:
        return os.path.join(os.path.dirname(__file__), 'regions.json')
    return os.path.join(USER_DATA_DIR, f"regions_{sid}.json")


def _meta_path_for(sid):
    if not sid:
        return os.path.join(os.path.dirname(__file__), 'meta.json')
    return os.path.join(USER_DATA_DIR, f"meta_{sid}.json")


def _data_path_for(sid):
    if not sid:
        return os.path.join(os.path.dirname(__file__), 'data.json')
    return os.path.join(USER_DATA_DIR, f"data_{sid}.json")


def _run_marker_for(sid):
    return os.path.join(USER_DATA_DIR, f"generate_{sid}.running") if sid else os.path.join(os.path.dirname(__file__), 'generate.running')


def _done_marker_for(sid):
    return os.path.join(USER_DATA_DIR, f"generate_{sid}.done") if sid else os.path.join(os.path.dirname(__file__), 'generate.done')


def _ensure_running_marker(sid):
    run_marker = _run_marker_for(sid)
    try:
        with open(run_marker, 'w') as f:
            f.write(str(time.time()))
    except Exception:
        pass


def _remove_done_marker(sid):
    done_marker = _done_marker_for(sid)
    try:
        if os.path.exists(done_marker):
            os.remove(done_marker)
    except Exception:
        pass


def _mark_done_and_clear_running(sid):
    run_marker = _run_marker_for(sid)
    done_marker = _done_marker_for(sid)
    try:
        with open(done_marker, 'w') as f:
            f.write(str(time.time()))
    except Exception:
        pass
    try:
        if os.path.exists(run_marker):
            os.remove(run_marker)
    except Exception:
        pass


def _get_or_create_job_state(sid):
    with _job_states_lock:
        st = _job_states.get(sid)
        if st is None:
            st = {'version': 0, 'running': False}
            _job_states[sid] = st
        return st


def _worker_generate_latest(sid):
    """Generate pattern for the latest requested version; coalesce intermediate requests.
    Writes pattern/regions files and done marker only for the latest version.
    """
    st = _get_or_create_job_state(sid)
    try:
        while True:
            with _job_states_lock:
                version_to_run = st['version']
                st['running'] = True
            # show running state early
            _remove_done_marker(sid)
            _ensure_running_marker(sid)

            # Load current settings from data.json (authoritative)
            data_path = _data_path_for(sid)
            settings = _json_load_file(data_path, {})

            # Optional: cleanup before heavy work
            cleanup_user_data()

            # Perform in-process generation under a global lock (pm has globals)
            with _pm_global_lock:
                try:
                    # Create a deterministic seed per full-generation run
                    start_ts = time.time()
                    seed = int(time.time_ns() ^ hash(sid or 'global')) & 0x7FFFFFFF
                    pattern = pm.generate(settings=settings, seed=seed) if pm is not None else None
                    regions = getattr(pm, 'REGIONS', []) if pm is not None else []
                    elapsed_ms = int((time.time() - start_ts) * 1000)
                except Exception as e:
                    print("in-process generate failed:", e)
                    # On failure, clear running marker (keep idle state)
                    try:
                        run_marker = _run_marker_for(sid)
                        if os.path.exists(run_marker):
                            os.remove(run_marker)
                    except Exception:
                        pass
                    return

            # If a newer request arrived while we were computing, loop again (discard this result)
            with _job_states_lock:
                if st['version'] != version_to_run:
                    # Another request superseded this run
                    continue

            # Write outputs atomically for this session
            pattern_path = _pattern_path_for(sid)
            regions_path = _regions_path_for(sid)
            meta_path = _meta_path_for(sid)
            _json_dump_file(pattern or [], pattern_path)
            _json_dump_file(regions or [], regions_path)
            _json_dump_file({"pattern_seed": seed, "generated_at": time.time()}, meta_path)

            # Structured log for diagnostics
            try:
                log_obj = {
                    "event": "generate_done",
                    "sid": sid or "global",
                    "tiles": len(pattern or []),
                    "regions": len(regions or []),
                    "elapsed_ms": elapsed_ms,
                    "seed": seed,
                }
                print(json.dumps(log_obj))
            except Exception:
                pass

            # Mark done and clean up
            _mark_done_and_clear_running(sid)
            cleanup_user_data()

            # If no newer request since we started, we can exit; else loop to serve the latest
            with _job_states_lock:
                if st['version'] == version_to_run:
                    st['running'] = False
                    break
                # else: run again (st['running'] stays True)
    finally:
        with _job_states_lock:
            st['running'] = False


def _schedule_generate(sid):
    st = _get_or_create_job_state(sid)
    with _job_states_lock:
        st['version'] += 1
        should_start = not st['running']
    if should_start:
        _executor.submit(_worker_generate_latest, sid)


def _session_id_from_request():
    sid = request.cookies.get('session_id')
    # If none, return None so we can fall back to global files
    return sid

def _data_path_for(sid):
    if not sid:
        return os.path.join(os.path.dirname(__file__), 'data.json')
    # store per-session data in user_data/
    return os.path.join(USER_DATA_DIR, f"data_{sid}.json")

def _pattern_path_for(sid):
    if not sid:
        return os.path.join(os.path.dirname(__file__), 'pattern.json')
    # store per-session pattern in user_data/
    return os.path.join(USER_DATA_DIR, f"pattern_{sid}.json")

def _regions_path_for(sid):
    if not sid:
        return os.path.join(os.path.dirname(__file__), 'regions.json')
    return os.path.join(USER_DATA_DIR, f"regions_{sid}.json")

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/pattern.json')
def pattern():
    sid = _session_id_from_request()
    p = _pattern_path_for(sid)
    if os.path.exists(p):
        resp = send_file(p, mimetype='application/json')
        # Avoid client/proxy caching of the current pattern
        resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        resp.headers['Pragma'] = 'no-cache'
        resp.headers['Expires'] = '0'
        return resp
    # If no per-session pattern, return empty array to keep client happy
    return jsonify([])

@app.route('/regions.json')
def regions():
    sid = _session_id_from_request()
    p = _regions_path_for(sid)
    if os.path.exists(p):
        resp = send_file(p, mimetype='application/json')
        resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        resp.headers['Pragma'] = 'no-cache'
        resp.headers['Expires'] = '0'
        return resp
    return jsonify([])

@app.route('/data.json', methods=['GET', 'POST'])
def data_json():
    if request.method == 'POST':
        sid = _session_id_from_request()
        p = _data_path_for(sid)
        # ensure directory exists (should already)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w') as f:
            f.write(request.data.decode('utf-8'))
        # opportunistic cleanup after user write
        cleanup_user_data()
        return jsonify({"status": "ok"})
    else:
        sid = _session_id_from_request()
        p = _data_path_for(sid)
        if os.path.exists(p):
            resp = send_file(p, mimetype='application/json')
            # Avoid caching user-specific data.json
            resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            resp.headers['Pragma'] = 'no-cache'
            resp.headers['Expires'] = '0'
            return resp
        # fallback to global data.json if user-specific doesn't exist
        resp = send_from_directory('.', 'data.json')
        resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        resp.headers['Pragma'] = 'no-cache'
        resp.headers['Expires'] = '0'
        return resp

@app.route('/generate', methods=['POST'])
def generate():
    # Run generation for this session (prefer in-process fast path; fallback to subprocess)
    sid = _session_id_from_request()

    # Optimistic cleanup to avoid disk pressure
    cleanup_user_data()

    if pm is not None:
        # Coalesced in-process generation using a worker
        _remove_done_marker(sid)
        _ensure_running_marker(sid)
        _schedule_generate(sid)
        return jsonify({"status": "started"})

    # Fallback: spawn subprocess (legacy behavior)
    env = dict(os.environ)
    if sid:
        env['SESSION_ID'] = sid
    run_marker = _run_marker_for(sid)
    done_marker = _done_marker_for(sid)
    try:
        if os.path.exists(done_marker):
            os.remove(done_marker)
    except Exception:
        pass
    try:
        with open(run_marker, 'w') as f:
            f.write(str(time.time()))
    except Exception:
        pass

    python = sys.executable
    script = os.path.join(os.path.dirname(__file__), 'PepesMachine.py')
    try:
        subprocess.Popen([python, script], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        try:
            subprocess.run([python, script], env=env)
        except Exception:
            return jsonify({"status": "error", "message": str(e)}), 500

    return jsonify({"status": "started"})


@app.route('/generate/status')
def generate_status():
    sid = _session_id_from_request()
    run_marker = os.path.join(USER_DATA_DIR, f"generate_{sid}.running") if sid else os.path.join(os.path.dirname(__file__), 'generate.running')
    done_marker = os.path.join(USER_DATA_DIR, f"generate_{sid}.done") if sid else os.path.join(os.path.dirname(__file__), 'generate.done')
    # If done marker exists, return done; if running marker exists return running; else return idle
    try:
        if os.path.exists(done_marker):
            return jsonify({"status": "done"})
        if os.path.exists(run_marker):
            return jsonify({"status": "running"})
    except Exception:
        pass
    return jsonify({"status": "idle"})

def _load_json_safe(path, default):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        return default

def _pick_two_distinct_palette_colors(data_path):
    """Pick two distinct colors from active palette buttons in data.json. Fallback to black/white."""
    data = _load_json_safe(data_path, {})
    colors = []
    for k, v in (data.items() if isinstance(data, dict) else []):
        if not str(k).startswith('button_'):
            continue
        if isinstance(v, dict):
            if v.get('state') == 'on' and v.get('color'):
                colors.append(v['color'])
        elif isinstance(v, str) and v != 'off':
            colors.append(v)
    colors = list({c: True for c in colors}.keys())  # unique preserve order
    if len(colors) < 2:
        return ('black', 'white')
    import random
    a, b = random.sample(colors, 2)
    return (a, b)


def _active_palette_colors(data_path):
    data = _load_json_safe(data_path, {})
    colors = []
    for k, v in (data.items() if isinstance(data, dict) else []):
        if not str(k).startswith('button_'):
            continue
        if isinstance(v, dict):
            if v.get('state') == 'on' and v.get('color'):
                colors.append(v['color'])
        elif isinstance(v, str) and v != 'off':
            colors.append(v)
    # unique preserve order
    return list({c: True for c in colors}.keys())

def _recent_pairs_from_region(region):
    lst = region.get('last_pairs') or []
    # Normalize to list of (cf, cp)
    norm = []
    for itm in lst:
        if isinstance(itm, (list, tuple)) and len(itm) == 2:
            norm.append((itm[0], itm[1]))
    return norm


def _choose_new_colors_for_region(region, palette, sid):
    """Choose a new (cf, cp) for the region using a deterministic PRNG tied to region seed and
    a small per-region counter to avoid alternating between two states. Avoid the last few pairs.
    Updates region['recolor_count'] and region['last_pairs'].
    """
    import random as _rr
    # Helper: ensure we have at least two colors to choose from
    def _hex_to_rgb(c):
        try:
            s = str(c).strip()
            if s.startswith('#') and len(s) == 7:
                r = int(s[1:3], 16); g = int(s[3:5], 16); b = int(s[5:7], 16)
                return (r, g, b)
        except Exception:
            pass
        return None
    def _contrast_bw(c):
        rgb = _hex_to_rgb(c)
        if rgb is None:
            # fallback on name
            if str(c).lower() in ('white', '#fff', '#ffffff'): return 'black'
            return 'white'
        r, g, b = rgb
        # perceived luminance (sRGB) simple approximation
        lum = 0.2126*(r/255) + 0.7152*(g/255) + 0.0722*(b/255)
        return 'black' if lum > 0.5 else 'white'
    def _ensure_pair_palette(pal, prev_cf=None, prev_cp=None):
        pal = list(pal or [])
        if len(pal) >= 2:
            return pal
        if len(pal) == 1:
            c = pal[0]
            other = _contrast_bw(c)
            if other == c:
                other = 'white' if c.lower() != 'white' else 'black'
            return [c, other]
        # none active -> fallback
        return ['black', 'white']

    palette = _ensure_pair_palette(palette, region.get('color_fundo'), region.get('color_padrao'))
    prev_cf = region.get('color_fundo')
    prev_cp = region.get('color_padrao')
    recent = _recent_pairs_from_region(region)
    # Ensure current pair is also avoided
    if prev_cf and prev_cp:
        recent = list(recent) + [(prev_cf, prev_cp)]
    # Deterministic RNG based on region seed + recolor_count
    rid = int(region.get('id')) if region.get('id') is not None else 0
    seed = _coerce_int(region.get('seed')) or _derive_region_seed(rid, sid)
    count = int(region.get('recolor_count') or 0)
    prng = _rr.Random((int(seed) & 0x7FFFFFFF) ^ (count * 0x9E3779B1))
    # Try to pick a pair not in recent
    max_tries = 24
    choice = None
    for _ in range(max_tries):
        a, b = prng.sample(palette, 2)
        if (a, b) not in recent:
            choice = (a, b)
            break
    if choice is None:
        # If only two colors or palette very small, flip as last resort
        if len(palette) == 2 and prev_cf in palette and prev_cp in palette:
            choice = (prev_cp, prev_cf)
        else:
            # Pick deterministically by rotating indices
            i = prng.randrange(0, len(palette))
            j = (i + 1 + prng.randrange(0, len(palette) - 1)) % len(palette)
            choice = (palette[i], palette[j])
    # Update region history
    region['recolor_count'] = count + 1
    new_hist = recent[-2:]  # keep last two (excluding current chosen)
    new_hist.append(choice)
    # store as list of lists for JSON friendliness
    region['last_pairs'] = [[c[0], c[1]] for c in new_hist]
    return choice


def _pick_pair_different_from(prev_cf, prev_cp, palette):
    """Pick a (cf,cp) from palette differing from previous pair; flip if needed for 2-color palettes."""
    if not palette or len(palette) < 2:
        return ('black', 'white')
    import random as _rr
    # Try a few random attempts to differ
    for _ in range(8):
        a, b = _rr.sample(palette, 2)
        if not (a == prev_cf and b == prev_cp):
            return (a, b)
    # If only two colors or repeated draws equal, flip order to guarantee visible change
    if len(palette) == 2 and prev_cf in palette and prev_cp in palette:
        return (prev_cp, prev_cf)
    # Fallback to any two distinct
    a, b = _rr.sample(palette, 2)
    return (a, b)


def _coerce_int(v, default=None):
    try:
        return int(v)
    except Exception:
        return default


def _derive_region_seed(region_id, sid):
    """Derive a deterministic seed for a region when none is stored, based on session meta and region id."""
    try:
        meta = _json_load_file(_meta_path_for(sid), {})
        base = int(meta.get('pattern_seed')) if meta and 'pattern_seed' in meta else None
    except Exception:
        base = None
    if base is None:
        base = int(time.time_ns() ^ hash(sid or 'global')) & 0x7FFFFFFF
    return int((base ^ (int(region_id) << 10)) & 0x7FFFFFFF)

@app.route('/edit-region', methods=['POST'])
def edit_region():
    """
    Edit a single region by id. Body: { region_id, action: 'reroll'|'recolor', colors?: { color_fundo?, color_padrao? } }
    Recomputes tiles for that region and updates the session's pattern and regions.
    """
    if pm is None:
        return jsonify({"status": "error", "message": "Generator module not available"}), 500
    js = request.get_json(force=True, silent=True) or {}
    region_id = js.get('region_id')
    action = js.get('action')
    if not region_id or action not in ('reroll', 'recolor'):
        return jsonify({"status": "error", "message": "Invalid request"}), 400
    try:
        region_id = int(region_id)
    except Exception:
        return jsonify({"status": "error", "message": "region_id must be an integer"}), 400

    sid = _session_id_from_request()
    pattern_path = _pattern_path_for(sid)
    regions_path = _regions_path_for(sid)
    data_path = _data_path_for(sid)

    regions = _load_json_safe(regions_path, [])
    if not regions:
        return jsonify({"status": "error", "message": "No regions available; regenerate first"}), 400
    region = next((r for r in regions if int(r.get('id')) == region_id), None)
    if not region:
        return jsonify({"status": "error", "message": "Region not found"}), 404

    # Determine new parameters
    shape = region.get('shape')
    x1 = int(region.get('x1'))
    y1 = int(region.get('y1'))
    x2 = int(region.get('x2'))
    y2 = int(region.get('y2'))

    # colors
    if action == 'recolor':
        c_in = js.get('colors') or {}
        cf = c_in.get('color_fundo')
        cp = c_in.get('color_padrao')
        prev_cf = region.get('color_fundo')
        prev_cp = region.get('color_padrao')
        if not (cf and cp):
            palette = _active_palette_colors(data_path)
            cf, cp = _choose_new_colors_for_region(region, palette, sid)
        color_fundo, color_padrao = cf, cp
        variant = int(region.get('variant') or 1)
        region_seed = _coerce_int(region.get('seed')) or _derive_region_seed(region_id, sid)
    else:  # reroll: new variant and new colors
        cf, cp = _pick_two_distinct_palette_colors(data_path)
        color_fundo, color_padrao = cf, cp
        import random
        if shape == 'aleluia_quadrados':
            variant = random.randint(1, 14)
        else:
            variant = random.randint(1, 7)
        # new seed for reroll
        region_seed = int(time.time_ns() ^ (region_id << 8)) & 0x7FFFFFFF

    # Generate new tiles for this region
    # Load current session settings to ensure region generation uses matching canvas/grid dims
    settings = _load_json_safe(data_path, {})
    try:
        tiles = pm.generate_region(region_id, x1, y1, x2, y2, shape, variant, color_fundo, color_padrao, settings=settings, seed=region_seed)
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to generate region: {e}"}), 500

    # Load existing pattern and replace region tiles
    pattern = _load_json_safe(pattern_path, [])
    pattern = [t for t in pattern if int(t.get('region_id') or -1) != region_id]
    pattern.extend(tiles)

    # Save pattern and regions
    try:
        with open(pattern_path, 'w') as pf:
            json.dump(pattern, pf, indent=2)
        # update region entry
        region['variant'] = int(variant)
        region['color_fundo'] = color_fundo
        region['color_padrao'] = color_padrao
        if region_seed is not None:
            region['seed'] = int(region_seed)
        with open(regions_path, 'w') as rf:
            json.dump(regions, rf, indent=2)
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to save edits: {e}"}), 500

    return jsonify({"status": "ok", "pattern": pattern, "regions": regions})

@app.route('/magic-wand', methods=['POST'])
def magic_wand():
    """
    Create a new region by selecting two opposite tiles (diagonal corners),
    fill that rectangular area with a freshly generated pattern using current data-driven settings.
    Body: { x1, y1, x2, y2 }
    """
    if pm is None:
        return jsonify({"status": "error", "message": "Generator module not available"}), 500
    js = request.get_json(force=True, silent=True) or {}
    try:
        x1 = int(js.get('x1'))
        y1 = int(js.get('y1'))
        x2 = int(js.get('x2'))
        y2 = int(js.get('y2'))
    except Exception:
        return jsonify({"status": "error", "message": "x1,y1,x2,y2 must be integers"}), 400
    # normalize to 1-based inclusive bounds
    x_lo, x_hi = (x1, x2) if x1 <= x2 else (x2, x1)
    y_lo, y_hi = (y1, y2) if y1 <= y2 else (y2, y1)
    # load paths and settings
    sid = _session_id_from_request()
    pattern_path = _pattern_path_for(sid)
    regions_path = _regions_path_for(sid)
    data_path = _data_path_for(sid)
    settings = _load_json_safe(data_path, {})

    # choose shape based on data (mirror PepeAI.GetPatternShape logic simplistically)
    switch_value = settings.get('switch')
    slider_value = int(settings.get('slider', 50))
    import random as _rnd
    if switch_value == 'left':
        shape = 'aleluia_quadrados'
    elif switch_value == 'right':
        shape = 'aleluia_triangulos'
    elif switch_value == 'center':
        shape = _rnd.choice(['aleluia_quadrados', 'aleluia_triangulos']) if slider_value <= 50 else _rnd.choice(['aleluia_triangulos', 'aleluia_quadrados'])
    else:
        shape = _rnd.choice(['aleluia_triangulos', 'aleluia_quadrados'])

    # pick colors from active palette
    color_fundo, color_padrao = _pick_two_distinct_palette_colors(data_path)
    # variant
    variant = _rnd.randint(1, 14) if shape == 'aleluia_quadrados' else _rnd.randint(1, 7)

    # regions bookkeeping
    regions = _load_json_safe(regions_path, [])
    next_id = (max([int(r.get('id', 0)) for r in regions]) + 1) if regions else 1
    # region seed
    region_seed = int(time.time_ns() ^ (next_id << 8)) & 0x7FFFFFFF

    # generate tiles for this new region
    try:
        tiles = pm.generate_region(next_id, x_lo, y_lo, x_hi, y_hi, shape, variant, color_fundo, color_padrao, settings=settings, seed=region_seed)
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to generate region: {e}"}), 500

    # update pattern: remove any tiles inside bounds, then add new ones
    pattern = _load_json_safe(pattern_path, [])
    kept = []
    for t in pattern:
        gx = int(t.get('grid_x', 0))
        gy = int(t.get('grid_y', 0))
        if x_lo <= gx <= x_hi and y_lo <= gy <= y_hi:
            continue
        kept.append(t)
    kept.extend(tiles)

    # update regions list
    new_region = {
        'id': next_id,
        'x1': x_lo,
        'y1': y_lo,
        'x2': x_hi,
        'y2': y_hi,
        'shape': shape,
        'variant': int(variant),
        'color_fundo': color_fundo,
        'color_padrao': color_padrao,
        'seed': int(region_seed)
    }
    regions.append(new_region)

    # save
    try:
        with open(pattern_path, 'w') as pf:
            json.dump(kept, pf, indent=2)
        with open(regions_path, 'w') as rf:
            json.dump(regions, rf, indent=2)
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to save magic wand result: {e}"}), 500

    return jsonify({"status": "ok", "pattern": kept, "regions": regions, "region": new_region})


@app.route('/recolor-all', methods=['POST'])
def recolor_all():
    """Recolor all existing regions (keep layout/variant/seed), return full updated pattern and regions."""
    if pm is None:
        return jsonify({"status": "error", "message": "Generator module not available"}), 500
    sid = _session_id_from_request()
    pattern_path = _pattern_path_for(sid)
    regions_path = _regions_path_for(sid)
    data_path = _data_path_for(sid)
    settings = _json_load_file(data_path, {})

    regions = _load_json_safe(regions_path, [])
    if not regions:
        return jsonify({"status": "error", "message": "No regions available to recolor"}), 400
    palette = _active_palette_colors(data_path)

    # Build new tiles per region
    new_tiles_all = []
    try:
        for idx, region in enumerate(regions):
            try:
                rid = int(region.get('id'))
                shape = region.get('shape')
                x1 = int(region.get('x1')); y1 = int(region.get('y1'))
                x2 = int(region.get('x2')); y2 = int(region.get('y2'))
                cf, cp = _choose_new_colors_for_region(region, palette, sid)
                seed = _coerce_int(region.get('seed')) or _derive_region_seed(rid, sid)
                variant = int(region.get('variant') or 1)
                tiles = pm.generate_region(rid, x1, y1, x2, y2, shape, variant, cf, cp, settings=settings, seed=seed)
                new_tiles_all.extend(tiles)
                # Update region colors (and ensure seed stored)
                region['color_fundo'] = cf
                region['color_padrao'] = cp
                region['seed'] = int(seed)
            except Exception as e:
                return jsonify({"status": "error", "message": f"Failed recoloring region {region.get('id')}: {e}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to recolor all: {e}"}), 500

    # Merge with existing pattern by replacing all region tiles
    pattern = _load_json_safe(pattern_path, [])
    keep = [t for t in pattern if (t.get('region_id') is None)]
    keep.extend(new_tiles_all)

    # Save
    try:
        with open(pattern_path, 'w') as pf:
            json.dump(keep, pf, indent=2)
        with open(regions_path, 'w') as rf:
            json.dump(regions, rf, indent=2)
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to save recolor-all: {e}"}), 500

    return jsonify({"status": "ok", "pattern": keep, "regions": regions})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
