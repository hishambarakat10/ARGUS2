import os
import re
import json
import time
import pandas as pd
import socket
from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

LOG_DIR = "/var/log/suricata"
LOG_FILE = "fast.log"
DEVICE_NAME = socket.gethostname()

# Store incoming logs in memory (You can also store in a database or file)
log_data = []

# Helper function to extract log data and generate DataFrame
def extract_data():
    try:
        data = {'timestamp': [], 'event_id': [], 'classification': []}
        pattern = re.compile(r"^(\d{2}/\d{2}/\d{4}-\d{2}:\d{2}:\d{2}\.\d+)  \[\*\*] \[1:(\d+):\d+] .*? \[\*\*] \[Classification: ([^]]+)]")

        # Loop through stored logs (or read from file if necessary)
        for log in log_data:
            match = pattern.search(log['timestamp'])  # Assuming logs have timestamps in 'timestamp' field
            if match:
                data['timestamp'].append(log['timestamp'])
                data['event_id'].append(log['event_id'])
                data['classification'].append(log['classification'])

        return pd.DataFrame(data)
    except Exception as e:
        print(f"An error occurred while extracting data: {e}")
        return None

@app.route("/")
def dashboard():
    # Serve the dashboard page with real-time charts
    return render_template("dashboard.html")

@app.route("/api/logs", methods=["POST"])
def handle_logs():
    # This endpoint handles incoming log data
    new_log = request.json
    if new_log:
        log_data.append(new_log)  # Store the new log entry in memory
        socketio.emit("update_charts", {"message": "Update charts"})  # Emit Socket.IO event for chart update
        return jsonify({"message": "Log data received and processed"}), 200
    return jsonify({"error": "No log data received"}), 400

@app.route("/api/chart-data")
def chart_data():
    # Fetch chart data
    df = extract_data()
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
    # Fetch pie chart data
    df = extract_data()
    if df is None or df.empty:
        return jsonify({"error": "No data found"}), 404

    classification_counts = df['classification'].value_counts()

    return jsonify({
        "labels": classification_counts.index.tolist(),
        "data": classification_counts.tolist()
    })

def monitor_logs():
    while True:
        # You could fetch data or emit events periodically if needed (e.g., every 5 seconds)
        socketio.emit("update_charts", {"message": "Periodic update"})
        time.sleep(5)

if __name__ == "__main__":
    socketio.start_background_task(monitor_logs)
    socketio.run(app, host="127.0.0.1", port=5000, debug=True)
