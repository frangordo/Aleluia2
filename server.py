from flask import Flask, send_from_directory, jsonify, request, session
import os
import json
import subprocess
import uuid
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__, static_folder='.')
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# Configure logging
if not os.path.exists('logs'):
    os.makedirs('logs')

formatter = logging.Formatter(
    '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)

file_handler = RotatingFileHandler(
    'logs/app.log', 
    maxBytes=10240, 
    backupCount=10
)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)

app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)

def get_user_directory():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
        app.logger.info(f"Created new session: {session['user_id']}")
    
    user_dir = os.path.join('user_data', session['user_id'])
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
        app.logger.info(f"Created user directory: {user_dir}")
    return user_dir

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
    try:
        user_dir = get_user_directory()
        app.logger.info(f"Generating pattern for user: {session['user_id']}")
        
        # Set timeouts for subprocess
        timeout = 30  # 30 seconds timeout
        
        # Run PepesMachine.py with timeout
        process = subprocess.run(
            ['python', 'PepesMachine.py'],
            timeout=timeout,
            capture_output=True
        )
        
        if process.returncode != 0:
            app.logger.error(f"Generation failed: {process.stderr.decode()}")
            return jsonify({"error": "Pattern generation failed"}), 500
            
        app.logger.info("Pattern generated successfully")
        return jsonify({"status": "ok"})
        
    except subprocess.TimeoutExpired:
        app.logger.error("Pattern generation timed out")
        return jsonify({"error": "Generation timed out"}), 504
    except Exception as e:
        app.logger.error(f"Error in generate: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Create necessary directories
    for dir in ['user_data', 'logs']:
        if not os.path.exists(dir):
            os.makedirs(dir)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
