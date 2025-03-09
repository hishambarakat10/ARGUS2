import os
import requests
from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit
import json

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Google Gemini 2.0 API endpoint and key
GEMINI_API_URL = "https://gemini.googleapis.com/v1/chat"
GEMINI_API_KEY = "AIzaSyDrA-I9691P5TdccQRT4rAkjqQYMbB84qk"  # Replace with your Gemini API key

# Sample data (you will update this based on the data you want Gemini to analyze)
log_data = []
classification_counts = {}  # For pie chart
timestamps_data = {}  # For line chart

# Process log entries (same as before)
def process_log_entry(log_entry):
    timestamp = log_entry["timestamp"]
    classification = log_entry["classification"]
    classification_counts[classification] = classification_counts.get(classification, 0) + 1

    if timestamp not in timestamps_data:
        timestamps_data[timestamp] = {}
    timestamps_data[timestamp][classification] = timestamps_data[timestamp].get(classification, 0) + 1

# Route to serve the dashboard
@app.route("/")
def dashboard():
    return render_template("dashboard.html")

# Handle incoming logs (from sendtodashboard.py)
@app.route("/api/logs", methods=["POST"])
def handle_logs():
    log_entry = request.get_json()
    if not log_entry or "timestamp" not in log_entry or "classification" not in log_entry:
        return jsonify({"error": "Invalid log format"}), 400

    log_data.append(log_entry)
    process_log_entry(log_entry)

    # Notify frontend for real-time updates
    socketio.emit("update_charts")
    return jsonify({"message": "Log received"}), 200

# Fetch chart data for the line chart
@app.route("/api/chart-data")
def chart_data_route():
    timestamps = sorted(timestamps_data.keys())
    datasets = {}

    for timestamp in timestamps:
        for classification, count in timestamps_data[timestamp].items():
            if classification not in datasets:
                datasets[classification] = []
            datasets[classification].append(count)

    return jsonify({"timestamps": timestamps, "datasets": datasets})

# Fetch pie chart data
@app.route("/api/pie-data")
def pie_data_route():
    total_events = sum(classification_counts.values())
    percentages = {k: (v / total_events) * 100 for k, v in classification_counts.items()} if total_events else {}

    return jsonify({"labels": list(percentages.keys()), "percentages": list(percentages.values())})

# Chatbot route to interact with Gemini 2.0 Flash model
@app.route("/api/chat", methods=["POST"])
def chat_with_gemini():
    """Send chat message to Gemini 2.0 Flash model and get response"""
    user_message = request.json.get("message")
    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    payload = {
        "messages": [
            {"role": "user", "content": user_message},
            {"role": "system", "content": "You are an AI assistant for Suricata IDS logs."}
        ],
        "model": "gemini-2.0-flash"  # Model identifier for Gemini 2.0 Flash model
    }

    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(GEMINI_API_URL, json=payload, headers=headers)

    if response.status_code == 200:
        return jsonify({"response": response.json()})
    else:
        return jsonify({"error": "Failed to get response from Gemini API", "details": response.text}), 500

# Running the app
if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=5000, debug=True)
