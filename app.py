import os
import json
import time
import socket
import pandas as pd
from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

LOG_FILE = "/var/log/suricata/eve.json"
DEVICE_NAME = socket.gethostname()

# Store processed logs
log_data = []
event_type_counts = {}  # For pie chart
timestamps_data = {}  # For line chart

def process_log_entry(log_entry):
    """ Processes log entry and updates data for charts """
    timestamp = log_entry["timestamp"]
    event_type = log_entry["event_type"]

    # Update event type count (for pie chart)
    if event_type not in event_type_counts:
        event_type_counts[event_type] = 0
    event_type_counts[event_type] += 1

    # Update timestamps vs. event type count (for line chart)
    if timestamp not in timestamps_data:
        timestamps_data[timestamp] = {}
    if event_type not in timestamps_data[timestamp]:
        timestamps_data[timestamp][event_type] = 0
    timestamps_data[timestamp][event_type] += 1

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/api/logs", methods=["POST"])
def handle_logs():
    """ Receives log data from sendtodashboard.py and updates charts """
    log_entry = request.get_json()
    if not log_entry or "timestamp" not in log_entry or "event_type" not in log_entry:
        return jsonify({"error": "Invalid log format"}), 400

    # Store and process log
    log_data.append(log_entry)
    process_log_entry(log_entry)

    # Notify frontend for real-time updates
    socketio.emit("update_charts")

    return jsonify({"message": "Log received"}), 200

@app.route("/api/chart-data")
def chart_data_route():
    """ Sends data for the line chart """
    timestamps = sorted(timestamps_data.keys())
    datasets = {}

    for timestamp in timestamps:
        for event_type, count in timestamps_data[timestamp].items():
            if event_type not in datasets:
                datasets[event_type] = []
            datasets[event_type].append(count)

    return jsonify({"timestamps": timestamps, "datasets": datasets})

@app.route("/api/pie-data")
def pie_data_route():
    """ Sends data for the pie chart """
    total_events = sum(event_type_counts.values())
    percentages = {k: (v / total_events) * 100 for k, v in event_type_counts.items()} if total_events else {}

    return jsonify({"labels": list(percentages.keys()), "data": list(percentages.values())})

if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=5000, debug=True)
