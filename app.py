import os
import requests
from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit
import json
import torch
from collections import Counter
import threading
import time

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global data storage for logs and analytics
log_data = []                 # List to store incoming log entries
classification_counts = {}    # Dictionary to track counts for each classification

def process_log_entry(log_entry):
    """
    Processes and organizes log data.
    Updates the classification counts and stores the log entry.
    """
    timestamp = log_entry["timestamp"]
    classification = log_entry["classification"]
    classification_counts[classification] = classification_counts.get(classification, 0) + 1
    log_data.append(log_entry)

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/api/logs", methods=["POST"])
def handle_logs():
    """
    Receives logs (e.g., from sendtodashboard.py), processes them,
    and emits a socket event to update charts.
    """
    log_entry = request.get_json()
    if log_entry:
        process_log_entry(log_entry)
        socketio.emit("update_charts")
        return jsonify({"message": "Log received"}), 200
    else:
        return jsonify({"error": "No log data provided"}), 400

@app.route("/api/chat", methods=["POST"])
def chat_with_rasa():
    """
    Handles chat messages by forwarding them to the Rasa server running on your local machine.
    """
    user_input = request.json.get("message")
    if not user_input:
        return jsonify({"error": "No message provided"}), 400

    # Replace with your local machine's IP address where the Rasa server is running.
    rasa_server_url = "http://10.152.48.106:5005/webhooks/rest/webhook"
    try:
        rasa_response = requests.post(rasa_server_url,
                                      json={"sender": "user", "message": user_input},
                                      timeout=5)
    except Exception as e:
        return jsonify({"response": f"Error connecting to Rasa server: {e}"}), 500

    if rasa_response.status_code == 200:
        response_data = rasa_response.json()
        if response_data and isinstance(response_data, list) and "text" in response_data[0]:
            chatbot_reply = response_data[0]["text"]
        else:
            chatbot_reply = "I didn't understand that."
    else:
        chatbot_reply = "Error reaching chatbot."

    return jsonify({"response": chatbot_reply})

@app.route("/api/alerts-over-time")
def alerts_over_time():
    """
    Uses PyTorch to compute alerts over time.
    It extracts minute-level timestamps from log entries, counts alerts per minute,
    converts counts into a PyTorch tensor, and returns the sorted timestamps and counts as JSON.
    """
    minute_timestamps = [entry["timestamp"][:16] for entry in log_data]
    counts = Counter(minute_timestamps)
    sorted_items = sorted(counts.items())
    if sorted_items:
        timestamps, alert_counts = zip(*sorted_items)
    else:
        timestamps, alert_counts = [], []
    alerts_tensor = torch.tensor(alert_counts, dtype=torch.int32)
    alerts_list = alerts_tensor.tolist()
    return jsonify({
        "timestamps": timestamps,
        "alerts": alerts_list
    })

@app.route("/api/severity-breakdown")
def severity_breakdown():
    """
    Returns the severity breakdown based on the 'priority' field.
    Uses the classification_counts dictionary.
    """
    return jsonify({
        "labels": list(classification_counts.keys()),
        "percentages": list(classification_counts.values())
    })

# --- New: Forward Real-Time Log Data from the VM's fast.log to Rasa ---

# Import parse_fast_log from sendtodashboard.py to reuse your log parser.
from sendtodashboard import parse_fast_log

def forward_logs_to_rasa():
    """
    Continuously reads new lines from /var/log/suricata/fast.log on the VM,
    parses them using parse_fast_log, and sends each parsed log entry to the Rasa server.
    The Rasa endpoint (here, /api/receive_log_data) must be implemented in your Rasa server.
    """
    log_file_path = "/var/log/suricata/fast.log"  # Path on the VM
    with open(log_file_path, "r") as file:
        file.seek(0, os.SEEK_END)  # Start at the end to capture only new logs
        while True:
            line = file.readline()
            if not line:
                time.sleep(0.1)
                continue
            parsed = parse_fast_log(line)
            if parsed:
                try:
                    # Replace with your local machine's IP where Rasa is running.
                    requests.post("http://192.168.1.216:5005/api/receive_log_data",
                                  json=parsed,
                                  timeout=5)
                    print("Forwarded log to Rasa:", parsed)
                except Exception as e:
                    print("Error forwarding log to Rasa:", e)
            else:
                print("Failed to parse log line:", line.strip())

# Start a background thread to forward log data to Rasa in real time.
log_thread = threading.Thread(target=forward_logs_to_rasa, daemon=True)
log_thread.start()

if __name__ == "__main__":
    # Run the Flask-SocketIO server on 127.0.0.1:5000 on the VM.
    socketio.run(app, host="127.0.0.1", port=5000, debug=True)
