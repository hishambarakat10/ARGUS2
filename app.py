import os
import time
from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

log_data = []
classification_counts = {}  # For pie chart
timestamps_data = {}  # For line chart

def process_log_entry(log_entry):
    """ Processes log entry and updates data for charts """
    timestamp = log_entry["timestamp"]
    classification = log_entry["classification"]

    # Update classification count (for pie chart)
    classification_counts[classification] = classification_counts.get(classification, 0) + 1

    # Update timestamps vs. classification count (for line chart)
    if timestamp not in timestamps_data:
        timestamps_data[timestamp] = {}
    timestamps_data[timestamp][classification] = timestamps_data[timestamp].get(classification, 0) + 1

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/api/logs", methods=["POST"])
def handle_logs():
    """ Receives log data from sendtodashboard.py and updates charts """
    log_entry = request.get_json()
    if not log_entry or "timestamp" not in log_entry or "classification" not in log_entry:
        return jsonify({"error": "Invalid log format"}), 400

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
        for classification, count in timestamps_data[timestamp].items():
            if classification not in datasets:
                datasets[classification] = []
            datasets[classification].append(count)

    return jsonify({"timestamps": timestamps, "datasets": datasets})

@app.route("/api/pie-data")
def pie_data_route():
    """ Sends data for the pie chart """
    total_events = sum(classification_counts.values())
    percentages = {k: (v / total_events) * 100 for k, v in classification_counts.items()} if total_events else {}

    return jsonify({"labels": list(percentages.keys()), "percentages": list(percentages.values())})

if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=5000, debug=True)
