from flask import Flask, send_from_directory, jsonify, request, send_file, abort
import subprocess
import os
import sys
import uuid
import time
import json

# For region-level editing, import helpers from PepesMachine
try:
    import PepesMachine as pm
except Exception:
    pm = None

USER_DATA_DIR = os.path.join(os.path.dirname(__file__), 'user_data')
os.makedirs(USER_DATA_DIR, exist_ok=True)

# Serve the dedicated ./static folder under the URL path /static
app = Flask(__name__, static_folder='static')



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
    # Run PepesMachine.py
    sid = _session_id_from_request()
    env = dict(os.environ)
    if sid:
        env['SESSION_ID'] = sid
    # Start generation in a background process so the request returns quickly.
    # We create a '.running' marker file so clients can poll for status.
    run_marker = os.path.join(USER_DATA_DIR, f"generate_{sid}.running") if sid else os.path.join(os.path.dirname(__file__), 'generate.running')
    done_marker = os.path.join(USER_DATA_DIR, f"generate_{sid}.done") if sid else os.path.join(os.path.dirname(__file__), 'generate.done')
    try:
        # remove old done marker if present
        if os.path.exists(done_marker):
            os.remove(done_marker)
    except Exception:
        pass
    try:
        # touch running marker
        with open(run_marker, 'w') as f:
            f.write(str(time.time()))
    except Exception:
        pass

    # Launch child detached
    python = sys.executable
    script = os.path.join(os.path.dirname(__file__), 'PepesMachine.py')
    # on Windows, creationflags can be used to detach; subprocess.Popen is sufficient here
    try:
        subprocess.Popen([python, script], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        # fallback to blocking run if spawn fails
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
        if not (cf and cp):
            cf, cp = _pick_two_distinct_palette_colors(data_path)
        color_fundo, color_padrao = cf, cp
        variant = int(region.get('variant') or 1)
    else:  # reroll: new variant and new colors
        cf, cp = _pick_two_distinct_palette_colors(data_path)
        color_fundo, color_padrao = cf, cp
        import random
        if shape == 'aleluia_quadrados':
            variant = random.randint(1, 14)
        else:
            variant = random.randint(1, 7)

    # Generate new tiles for this region
    # Load current session settings to ensure region generation uses matching canvas/grid dims
    settings = _load_json_safe(data_path, {})
    try:
        tiles = pm.generate_region(region_id, x1, y1, x2, y2, shape, variant, color_fundo, color_padrao, settings=settings)
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

    # generate tiles for this new region
    try:
        tiles = pm.generate_region(next_id, x_lo, y_lo, x_hi, y_hi, shape, variant, color_fundo, color_padrao, settings=settings)
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
        'color_padrao': color_padrao
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
