import os
import time
from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit
import chatbot  # Import chatbot functions

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

log_data = []
classification_counts = {}  # For pie chart
timestamps_data = {}  # For line chart

def process_log_entry(log_entry):
    """ Processes log entry and updates data for charts """
    timestamp = log_entry["timestamp"]
    classification = log_entry["classification"]

    classification_counts[classification] = classification_counts.get(classification, 0) + 1

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
    
    # Analyze with TinyLlama and store AI response
    ai_analysis = chatbot.analyze_with_tinyllama(log_entry)
    chatbot.store_ai_log(log_entry, ai_analysis)

    socketio.emit("update_charts")
    return jsonify({"message": "Log received"}), 200

@app.route("/api/chat", methods=["POST"])
def chat():
    """ Handles chatbot queries using TinyLlama """
    user_message = request.json.get("message", "")
    response_text = chatbot.handle_chat_request(user_message)
    return jsonify({"response": response_text})

if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=5000, debug=True)
