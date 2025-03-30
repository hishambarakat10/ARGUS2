import os
import requests
import json
import torch
import threading
import time
from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash
from flask_socketio import SocketIO
from collections import Counter
from sendtodashboard import parse_fast_log

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Replace with a real secret key
socketio = SocketIO(app, cors_allowed_origins="*")

log_data = []
classification_counts = {}

# Dummy credentials (replace with database check if needed)
USER_CREDENTIALS = {
    "admin": "password123"
}

def process_log_entry(log_entry):
    timestamp = log_entry["timestamp"]
    classification = log_entry["classification"]
    classification_counts[classification] = classification_counts.get(classification, 0) + 1
    log_data.append(log_entry)

@app.route("/")
def root():
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route("/dashboard")
def dashboard():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    return render_template("dashboard.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        flash("Invalid username or password", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))

@app.route("/api/logs", methods=["POST"])
def handle_logs():
    log_entry = request.get_json()
    if log_entry:
        process_log_entry(log_entry)
        socketio.emit("update_charts")
        return jsonify({"message": "Log received"}), 200
    return jsonify({"error": "No log data provided"}), 400

@app.route("/api/logs", methods=["GET"])
def get_logs():
    return jsonify(log_data)

@app.route("/api/chat", methods=["POST"])
def chat_with_rasa():
    user_input = request.json.get("message")
    if not user_input:
        return jsonify({"error": "No message provided"}), 400

    rasa_server_url = "http://192.168.1.100:5005/webhooks/rest/webhook"
    try:
        rasa_response = requests.post(rasa_server_url,
                                      json={"sender": "user", "message": user_input},
                                      timeout=5)
    except Exception as e:
        return jsonify({"response": f"Error connecting to Rasa server: {e}"}), 500

    if rasa_response.status_code == 200:
        response_data = rasa_response.json()
        chatbot_reply = response_data[0]["text"] if response_data else "I didn't understand that."
    else:
        chatbot_reply = "Error reaching chatbot."
    return jsonify({"response": chatbot_reply})

@app.route("/api/alerts-over-time")
def alerts_over_time():
    minute_timestamps = [entry["timestamp"][:16] for entry in log_data]
    counts = Counter(minute_timestamps)
    sorted_items = sorted(counts.items())
    if sorted_items:
        timestamps, alert_counts = zip(*sorted_items)
    else:
        timestamps, alert_counts = [], []
    alerts_tensor = torch.tensor(alert_counts, dtype=torch.int32)
    return jsonify({"timestamps": timestamps, "alerts": alerts_tensor.tolist()})

@app.route("/api/severity-breakdown")
def severity_breakdown():
    return jsonify({
        "labels": list(classification_counts.keys()),
        "percentages": list(classification_counts.values())
    })

# Background log forwarding
def forward_logs_to_rasa():
    log_file_path = "/var/log/suricata/fast.log"
    with open(log_file_path, "r") as file:
        file.seek(0, os.SEEK_END)
        while True:
            line = file.readline()
            if not line:
                time.sleep(0.1)
                continue
            parsed = parse_fast_log(line)
            if parsed:
                try:
                    requests.post("http://192.168.1.100:5005/api/receive_log_data", json=parsed, timeout=5)
                    print("Forwarded log to Rasa:", parsed)
                except Exception as e:
                    print("Error forwarding log to Rasa:", e)

log_thread = threading.Thread(target=forward_logs_to_rasa, daemon=True)
log_thread.start()

if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=5000, debug=True)
