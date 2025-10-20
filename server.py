from flask import Flask, send_from_directory, jsonify, request, send_file, abort
import subprocess
import os
import sys
import uuid
import time

USER_DATA_DIR = os.path.join(os.path.dirname(__file__), 'user_data')
os.makedirs(USER_DATA_DIR, exist_ok=True)

app = Flask(__name__, static_folder='.')



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

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/pattern.json')
def pattern():
    sid = _session_id_from_request()
    p = _pattern_path_for(sid)
    if os.path.exists(p):
        return send_file(p, mimetype='application/json')
    # If no per-session pattern, return empty array to keep client happy
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
            return send_file(p, mimetype='application/json')
        # fallback to global data.json if user-specific doesn't exist
        return send_from_directory('.', 'data.json')

@app.route('/generate', methods=['POST'])
def generate():
    # Run PepesMachine.py
    sid = _session_id_from_request()
    env = dict(os.environ)
    if sid:
        env['SESSION_ID'] = sid
    # Use same python interpreter running the server
    subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), 'PepesMachine.py')], env=env)
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
