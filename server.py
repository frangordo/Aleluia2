from flask import Flask, send_from_directory, jsonify, request
import subprocess
import os

app = Flask(__name__, static_folder='.')

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/pattern.json')
def pattern():
    return send_from_directory('.', 'pattern.json')

@app.route('/data.json', methods=['GET', 'POST'])
def data_json():
    if request.method == 'POST':
        with open('data.json', 'w') as f:
            f.write(request.data.decode('utf-8'))
        return jsonify({"status": "ok"})
    else:
        return send_from_directory('.', 'data.json')

@app.route('/generate', methods=['POST'])
def generate():
    # Run PepesMachine.py
    subprocess.run(['python', 'PepesMachine.py'])
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(debug=True)