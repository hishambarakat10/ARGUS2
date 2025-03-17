import os
import requests
import tensorflow as tf  # TensorFlow for alert calculations
import numpy as np
from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit
import json
from datetime import datetime  # Used for time-based calculations

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

RASA_API_URL = "http://localhost:5005/webhooks/rest/webhook"

log_data = []
alerts_per_minute = {}  # Stores alert counts per minute for the line chart
severity_counts = {"Not Suspicious": 0, "Potentially Suspicious": 0, "Malicious Traffic": 0}  # Stores severity distribution for the pie chart

def process_log_entry(log_entry):
    """Processes log data to calculate alerts per minute and severity breakdown."""
    timestamp = datetime.strptime(log_entry["timestamp"], "%d/%m/%Y-%H:%M:%S.%f")
    minute_key = timestamp.strftime("%Y-%m-%d %H:%M")  # Groups logs by minute

    # TensorFlow-based calculation for alerts per minute
    minute_tensor = tf.constant([minute_key])  # Convert minute to TensorFlow tensor
    alerts_tensor = tf.constant([alerts_per_minute.get(minute_key, 0) + 1], dtype=tf.float32)

    # Store computed alerts per minute
    alerts_per_minute[minute_tensor.numpy()[0].decode()] = int(alerts_tensor.numpy()[0])

    # Update severity breakdown based on priority (Pie Chart)
    severity_counts[log_entry["priority"]] = severity_counts.get(log_entry["priority"], 0) + 1

@app.route("/")
def dashboard():
    """Loads the main dashboard page."""
    return render_template("dashboard.html")

@app.route("/api/logs", methods=["POST"])
def handle_logs():
    """Receives logs from sendtodashboard.py and updates real-time charts."""
    log_entry = request.get_json()
    log_data.append(log_entry)  # Store logs
    process_log_entry(log_entry)  # Process alerts and severity
    socketio.emit("update_charts")  # Notify frontend to refresh charts
    return jsonify({"message": "Log received"}), 200

@app.route("/api/alerts-over-time")
def alerts_over_time():
    """Provides processed alert data for the line chart."""
    return jsonify({
        "timestamps": list(alerts_per_minute.keys()),  # X-axis: Timestamps
        "alerts": list(alerts_per_minute.values())  # Y-axis: Alert counts
    })

@app.route("/api/severity-breakdown")
def severity_breakdown():
    """Provides severity distribution for the pie chart."""
    return jsonify({
        "labels": list(severity_counts.keys()),  # Labels: Priority categories
        "values": list(severity_counts.values())  # Values: Count of each severity type
    })

@app.route("/api/chat", methods=["POST"])
def chat_with_rasa():
    """Handles user messages and forwards them to Rasa chatbot."""
    user_input = request.json.get("message")

    if not user_input:
        return jsonify({"error": "No message provided"}), 400

    rasa_response = requests.post(RASA_API_URL, json={"sender": "user", "message": user_input})

    if rasa_response.status_code == 200:
        response_data = rasa_response.json()
        chatbot_reply = response_data[0]["text"] if response_data and isinstance(response_data, list) and "text" in response_data[0] else "I didn't understand that."
    else:
        chatbot_reply = "Error reaching chatbot."

    return jsonify({"response": chatbot_reply})

if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=5000, debug=True)
