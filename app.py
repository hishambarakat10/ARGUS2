import os
import requests
from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit
import json
# Import torch and Counter for PyTorch-based processing
import torch
from collections import Counter

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Data storage for logs and analytics
log_data = []  # Stores log entries received from the log monitoring script
classification_counts = {}  # Stores classification counts for log analysis
timestamps_data = {}  # (Unused now, but kept if needed elsewhere)

# Existing log processing function remains unchanged
def process_log_entry(log_entry):
    """Processes and organizes log data for real-time visualization."""
    timestamp = log_entry["timestamp"]
    classification = log_entry["classification"]
    
    # Update classification counts (increment if exists, initialize if new)
    classification_counts[classification] = classification_counts.get(classification, 0) + 1

    # Update log storage categorized by timestamp
    if timestamp not in timestamps_data:
        timestamps_data[timestamp] = {}
    timestamps_data[timestamp][classification] = timestamps_data[timestamp].get(classification, 0) + 1

# Route for the main dashboard remains unchanged
@app.route("/")
def dashboard():
    return render_template("dashboard.html")

# API route to receive logs remains unchanged
@app.route("/api/logs", methods=["POST"])
def handle_logs():
    log_entry = request.get_json()
    log_data.append(log_entry)
    process_log_entry(log_entry)
    socketio.emit("update_charts")
    return jsonify({"message": "Log received"}), 200

# API route to communicate with the Rasa chatbot remains unchanged
@app.route("/api/chat", methods=["POST"])
def chat_with_rasa():
    user_input = request.json.get("message")
    if not user_input:
        return jsonify({"error": "No message provided"}), 400
    
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

# Modified API route for line chart data using PyTorch calculations
@app.route("/api/chart-data")
def chart_data():
    """
    Uses PyTorch to compute alerts over time.
    It extracts minute-level timestamps from log entries (assumes the first 16 characters of 'timestamp'),
    counts the number of alerts per minute using Counter, converts the counts to a PyTorch tensor,
    and returns the results as JSON.
    """
    # Extract minute-level timestamps (for example, "DD/MM/YYYY-HH:MM")
    minute_timestamps = [entry["timestamp"][:16] for entry in log_data]
    counts = Counter(minute_timestamps)
    # Sort counts by timestamp (chronologically)
    sorted_items = sorted(counts.items())
    if sorted_items:
        timestamps, alert_counts = zip(*sorted_items)
    else:
        timestamps, alert_counts = [], []
    # Convert the alert counts to a PyTorch tensor
    alerts_tensor = torch.tensor(alert_counts, dtype=torch.int32)
    # Convert tensor to a list for JSON serialization
    alerts_list = alerts_tensor.tolist()
    return jsonify({
        "timestamps": timestamps,
        "alerts": alerts_list
    })

# (Optional) If you have a separate pie chart endpoint, leave it as is.
@app.route("/api/pie-data")
def pie_data():
    # Your existing pie chart code here...
    # For example, it might return classification breakdowns.
    return jsonify({
        "labels": list(classification_counts.keys()),
        "percentages": list(classification_counts.values())
    })

if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=5000, debug=True)
