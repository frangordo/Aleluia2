from flask import Flask, send_from_directory, jsonify, request, session
import os
import json
import subprocess
import uuid

app = Flask(__name__, static_folder='.')
app.secret_key = os.urandom(24)  # Required for sessions

def get_user_directory():
    """Create and get user-specific directory"""
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    
    user_dir = os.path.join('user_data', session['user_id'])
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    return user_dir

def get_user_file(filename):
    """Get path to user-specific file"""
    return os.path.join(get_user_directory(), filename)

@app.route('/')
def index():
    # Initialize user data if it doesn't exist
    data_file = get_user_file('data.json')
    if not os.path.exists(data_file):
        default_data = {
            "knob_down": 1,
            "slider": 40,
            "switch": "center",
            "canvas_width": 2000,
            "canvas_height": 800,
            "button_0": "#ff66de",
            "button_1": "#f98686",
            "button_2": "#7081ff",
            "button_3": "#62fe74",
            "button_4": "#fcff4d",
            "button_5": "#ff7b24",
            "button_6": "#bd7ef1",
            "button_7": "#ffffff",
            "button_8": "#000000",
            "button_9": "#3517ab"
        }
        with open(data_file, 'w') as f:
            json.dump(default_data, f)
    
    return send_from_directory('.', 'index.html')

@app.route('/pattern.json')
def pattern():
    pattern_file = get_user_file('pattern.json')
    if os.path.exists(pattern_file):
        return send_from_directory(os.path.dirname(pattern_file), 
                                 os.path.basename(pattern_file))
    return jsonify([])

@app.route('/data.json', methods=['GET', 'POST'])
def data_json():
    data_file = get_user_file('data.json')
    
    if request.method == 'POST':
        with open(data_file, 'w') as f:
            f.write(request.data.decode('utf-8'))
        return jsonify({"status": "ok"})
    else:
        if os.path.exists(data_file):
            return send_from_directory(os.path.dirname(data_file), 
                                     os.path.basename(data_file))
        return jsonify({})

@app.route('/generate', methods=['POST'])
def generate():
    # Copy user's data.json to the location PepesMachine.py expects
    data_file = get_user_file('data.json')
    pattern_file = get_user_file('pattern.json')
    
    # Create a temporary data.json for PepesMachine.py to read
    temp_data = 'temp_data.json'
    temp_pattern = 'temp_pattern.json'
    
    if os.path.exists(data_file):
        with open(data_file, 'r') as src, open(temp_data, 'w') as dst:
            dst.write(src.read())
    
    # Run PepesMachine.py with temporary files
    subprocess.run(['python', 'PepesMachine.py'])
    
    # Move generated pattern to user's directory
    if os.path.exists(temp_pattern):
        with open(temp_pattern, 'r') as src, open(pattern_file, 'w') as dst:
            dst.write(src.read())
        os.remove(temp_pattern)
    
    if os.path.exists(temp_data):
        os.remove(temp_data)
    
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    # Create user_data directory if it doesn't exist
    if not os.path.exists('user_data'):
        os.makedirs('user_data')
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
