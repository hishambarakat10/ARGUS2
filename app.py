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
    
chart_data = []  # List to hold chart data
pie_data = {}    # Dictionary to hold pie chart data (classification counts)

def process_chart_data(log_entry):
    # Process log data for chart (line graph)
    timestamp = log_entry["timestamp"]
    # Assuming chart data is based on timestamps, update accordingly
    chart_data.append({
        "timestamp": timestamp,
        "count": 1  # Assuming each log entry is an alert (you can modify this logic)
    })

def process_pie_data(log_entry):
    # Process log data for pie chart (classification counts)
    classification = log_entry["classification"]
    if classification not in pie_data:
        pie_data[classification] = 0
    pie_data[classification] += 1

@app.route("/")
def dashboard():
    # Serve the dashboard page with real-time charts
    return render_template("dashboard.html")

@app.route("/api/logs", methods=["POST"])
def handle_logs():
    # Receive the log data sent from sendtodashboard.py
    log_data = request.get_json()
    
    # You will need to process this log data (store it, for example, in-memory, a file, or a DB)
    # For simplicity, let's just append the data to a list or process it as required
    
    log_entry = {
        "timestamp": log_data["timestamp"],
        "classification": log_data["classification"],
        "src_ip": log_data["src_ip"],
        "dest_ip": log_data["dest_ip"]
    }
    
    # Process the data for chart (line) and pie
    process_chart_data(log_entry)
    process_pie_data(log_entry)
    
    # Emit an update to inform frontend that data is ready
    socketio.emit("update_charts")  # Notify frontend for update
    
    return jsonify({"message": "Log data received and processed"}), 200

@app.route("/api/chart-data")
def chart_data_route():
    # Return chart data as JSON
    timestamps = [entry["timestamp"] for entry in chart_data]
    counts = [entry["count"] for entry in chart_data]
    
    return jsonify({
        "timestamps": timestamps,
        "alert_counts": counts
    })

@app.route("/api/pie-data")
def pie_data_route():
    # Return pie chart data as JSON
    classifications = list(pie_data.keys())
    counts = list(pie_data.values())
    
    return jsonify({
        "labels": classifications,
        "data": counts
    })

def monitor_logs():
    while True:
        # You could fetch data or emit events periodically if needed (e.g., every 5 seconds)
        socketio.emit("update_charts", {"message": "Periodic update"})
        time.sleep(5)

if __name__ == "__main__":
    socketio.start_background_task(monitor_logs)
    socketio.run(app, host="127.0.0.1", port=5000, debug=True)
