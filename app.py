import os
import json
import time
import pandas as pd
import socket
from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

DEVICE_NAME = socket.gethostname()

# Store incoming logs in memory
log_data = []
chart_data = []
pie_data = {}

def process_chart_data(log_entry):
    timestamp = log_entry["timestamp"]
    chart_data.append({"timestamp": timestamp, "count": 1})

def process_pie_data(log_entry):
    classification = log_entry["classification"]
    pie_data[classification] = pie_data.get(classification, 0) + 1

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/api/logs", methods=["POST"])
def handle_logs():
    log_entry = request.get_json()

    # Store and process data
    log_data.append(log_entry)
    process_chart_data(log_entry)
    process_pie_data(log_entry)

    socketio.emit("update_charts")  # Notify frontend
    return jsonify({"message": "Log data received and processed"}), 200

@app.route("/api/chart-data")
def chart_data_route():
    timestamps = [entry["timestamp"] for entry in chart_data]
    counts = [entry["count"] for entry in chart_data]
    return jsonify({"timestamps": timestamps, "alert_counts": counts})

@app.route("/api/pie-data")
def pie_data_route():
    return jsonify({"labels": list(pie_data.keys()), "data": list(pie_data.values())})

def monitor_logs():
    while True:
        socketio.emit("update_charts", {"message": "Periodic update"})
        time.sleep(5)

if __name__ == "__main__":
    socketio.start_background_task(monitor_logs)
    socketio.run(app, host="127.0.0.1", port=5000, debug=True)
