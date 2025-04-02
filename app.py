# app.py
import os
import requests
import json
import torch
import threading
import time
import sqlite3
from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash
from flask_socketio import SocketIO
from collections import Counter
from sendtodashboard import parse_fast_log

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Replace with something secure
socketio = SocketIO(app, cors_allowed_origins="*")

log_data = []
classification_counts = {}

# ============================
# AUTHENTICATION
# ============================

def check_user_credentials(username, password):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    user = cursor.fetchone()
    conn.close()
    return user

@app.before_request
def require_login():
    allowed_routes = ['login', 'static', 'handle_logs', 'get_logs', 'chat_with_langchain_bot', 'alerts_over_time', 'severity_breakdown', 'get_fast_log']
    if request.endpoint not in allowed_routes and 'logged_in' not in session:
        return redirect(url_for('login'))

# ============================
# ROUTES
# ============================

@app.route("/")
def root():
    return redirect(url_for('dashboard'))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = check_user_credentials(username, password)
        if user:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        flash("Invalid username or password", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

# ============================
# CHAT API (LangChain + Ollama)
# ============================

@app.route("/api/chat", methods=["POST"])
def chat_with_langchain_bot():
    user_input = request.json.get("message")
    if not user_input:
        return jsonify({"error": "No message provided"}), 400

    host_chatbot_url = "http://10.152.48.106:5005/chat"  # Replace with your actual host IP

    try:
        response = requests.post(host_chatbot_url, json={"message": user_input}, timeout=60)
        response_data = response.json()
        return jsonify({"response": response_data.get("response", "No reply received.")})
    except Exception as e:
        return jsonify({"response": f"Error talking to host chatbot: {e}"}), 500

# ============================
# CHART + LOG APIs
# ============================

@app.route("/api/logs", methods=["POST"])
def handle_logs():
    log_entry = request.get_json()
    if log_entry:
        process_log_entry(log_entry)
        socketio.emit("update_charts", to='*')
        return jsonify({"message": "Log received"}), 200
    return jsonify({"error": "No log data provided"}), 400

@app.route("/api/logs", methods=["GET"])
def get_logs():
    return jsonify(log_data)

@app.route("/api/fast-log", methods=["GET"])
def get_fast_log():
    return jsonify(log_data[-100:])

@app.route("/api/alerts-over-time")
def alerts_over_time():
    minute_timestamps = [entry["timestamp"][: 86400] for entry in log_data]
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

# ============================
# BACKGROUND LOG MONITORING
# ============================

def process_log_entry(log_entry):
    timestamp = log_entry["timestamp"]
    classification = log_entry["classification"]
    classification_counts[classification] = classification_counts.get(classification, 0) + 1
    log_data.append(log_entry)

def forward_logs():
    log_file_path = "/var/log/suricata/fast.log"
    if not os.path.exists(log_file_path):
        print(f"File not found: {log_file_path}")
        return
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
                    requests.post("http://127.0.0.1:5000/api/logs", json=parsed, timeout=5)
                    print("Forwarded log:", parsed)
                except Exception as e:
                    print("Error forwarding log:", e)

log_thread = threading.Thread(target=forward_logs, daemon=True)
log_thread.start()

# ============================
# START FLASK SERVER
# ============================

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
