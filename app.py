import os
import re
import json
import pandas as pd
import socket
import psutil
import time
from flask import Flask, jsonify, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

LOG_DIR = "/var/log/suricata"
LOG_FILE = "fast.log"
DEVICE_NAME = socket.gethostname()

def extract_data(file_path):
    try:
        data = {'timestamp': [], 'event_id': [], 'classification': []}
        pattern = re.compile(r"^(\d{2}/\d{2}/\d{4}-\d{2}:\d{2}:\d{2}\.\d+)  \[\*\*] \[1:(\d+):\d+] .*? \[\*\*] \[Classification: ([^]]+)]")

        with open(file_path, 'r') as file:
            for line in file:
                match = pattern.search(line)
                if match:
                    data['timestamp'].append(match.group(1))
                    data['event_id'].append(match.group(2))
                    data['classification'].append(match.group(3))

        return pd.DataFrame(data)
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/api/chart-data")
def chart_data():
    file_path = os.path.join(LOG_DIR, LOG_FILE)
    df = extract_data(file_path)

    if df is None or df.empty:
        return jsonify({"error": "No data found"}), 404

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['alert_count'] = 1
    df_grouped = df.groupby(df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')).count()

    return jsonify({
        "timestamps": df_grouped.index.tolist(),
        "alert_counts": df_grouped["alert_count"].tolist()
    })

@app.route("/api/pie-data")
def pie_data():
    file_path = os.path.join(LOG_DIR, LOG_FILE)
    df = extract_data(file_path)

    if df is None or df.empty:
        return jsonify({"error": "No data found"}), 404

    classification_counts = df['classification'].value_counts()

    return jsonify({
        "labels": classification_counts.index.tolist(),
        "data": classification_counts.tolist()
    })

def monitor_logs():
    while True:
        file_path = os.path.join(LOG_DIR, LOG_FILE)
        df = extract_data(file_path)

        if df is not None and not df.empty:
            socketio.emit("update_charts")

        print("Waiting for 5 seconds before reading logs again...")
        time.sleep(5)

if __name__ == "__main__":
    socketio.start_background_task(monitor_logs)
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
