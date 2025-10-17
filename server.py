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
    """Create and get user-specific directory"""
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    
    user_dir = os.path.join('user_data', session['user_id'])
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
        # Copy default data.json to user directory if it exists
        default_data = os.path.join(os.path.dirname(__file__), 'data.json')
        if os.path.exists(default_data):
            with open(default_data, 'r') as src:
                with open(os.path.join(user_dir, 'data.json'), 'w') as dst:
                    dst.write(src.read())
    return user_dir

def get_user_file(filename):
    """Get path to user-specific file"""
    return os.path.join(get_user_directory(), filename)

@app.route('/')
def index():
    try:
        get_user_directory()  # Ensure user directory exists
        return send_from_directory('.', 'index.html')
    except Exception as e:
        app.logger.error(f"Error in index: {str(e)}")
        return str(e), 500

@app.route('/pattern.json')
def pattern():
    try:
        pattern_file = get_user_file('pattern.json')
        if os.path.exists(pattern_file):
            with open(pattern_file, 'r') as f:
                return jsonify(json.load(f))
        return jsonify([])
    except Exception as e:
        app.logger.error(f"Error in pattern: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/data.json', methods=['GET', 'POST'])
def data_json():
    try:
        data_file = get_user_file('data.json')
        
        if request.method == 'POST':
            data = request.get_json()
            with open(data_file, 'w') as f:
                json.dump(data, f)
            return jsonify({"status": "ok"})
        
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                return jsonify(json.load(f))
        return jsonify({})
    except Exception as e:
        app.logger.error(f"Error in data_json: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/generate', methods=['POST'])
def generate():
    try:
        user_dir = get_user_directory()
        data_file = get_user_file('data.json')
        pattern_file = get_user_file('pattern.json')
        
        # Set environment variables for PepesMachine.py
        os.environ['TEMP_DATA_PATH'] = data_file
        os.environ['TEMP_PATTERN_PATH'] = pattern_file
        
        # Run PepesMachine.py with timeout
        process = subprocess.run(
            ['python', 'PepesMachine.py'],
            timeout=30,
            capture_output=True
        )
        
        if process.returncode != 0:
            app.logger.error(f"Generation failed: {process.stderr.decode()}")
            return jsonify({"error": "Pattern generation failed"}), 500
            
        return jsonify({"status": "ok"})
    except Exception as e:
        app.logger.error(f"Error in generate: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Create necessary directories
    for dir in ['user_data', 'logs']:
        if not os.path.exists(dir):
            os.makedirs(dir)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
