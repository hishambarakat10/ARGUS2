import os
import requests
from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit
import json
import torch
from collections import Counter

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

    # Update classification counts
    classification_counts[classification] = classification_counts.get(classification, 0) + 1

    # Append log entry to global log list
    log_data.append(log_entry)

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/api/logs", methods=["POST"])
def handle_logs():
    """
    Receives logs from sendtodashboard.py, processes them,
    and notifies the frontend to update charts.
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
    Handles user messages by sending them to the Rasa chatbot
    and returning the chatbot's response.
    """
    user_input = request.json.get("message")
    if not user_input:
        return jsonify({"error": "No message provided"}), 400

    # Send the user message to the Rasa chatbot
    rasa_response = requests.post("http://localhost:5005/webhooks/rest/webhook",
                                  json={"sender": "user", "message": user_input})
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
    It extracts minute-level timestamps from log entries (assumes the first 16 characters of 'timestamp'),
    counts the number of alerts per minute using Counter, converts the counts into a PyTorch tensor,
    and returns the sorted timestamps and counts as JSON.
    """
    # Extract minute-level timestamps (e.g., "03/18/2025-04:55")
    minute_timestamps = [entry["timestamp"][:16] for entry in log_data]
    # Count alerts per minute
    counts = Counter(minute_timestamps)
    # Sort the counts chronologically
    sorted_items = sorted(counts.items())
    if sorted_items:
        timestamps, alert_counts = zip(*sorted_items)
    else:
        timestamps, alert_counts = [], []
    # Convert counts to a PyTorch tensor for potential further processing
    alerts_tensor = torch.tensor(alert_counts, dtype=torch.int32)
    # Convert tensor to a Python list for JSON serialization
    alerts_list = alerts_tensor.tolist()
    return jsonify({
        "timestamps": timestamps,
        "alerts": alerts_list
    })

@app.route("/api/severity-breakdown")
def severity_breakdown():
    """
    Returns the severity breakdown of the logs based on the 'priority' field.
    Uses the classification_counts dictionary.
    """
    return jsonify({
        "labels": list(classification_counts.keys()),
        "percentages": list(classification_counts.values())
    })

if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=5000, debug=True)
