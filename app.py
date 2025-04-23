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
from datetime import datetime
import smtplib
from email.message import EmailMessage
import threading

def load_initial_logs(file_path="/var/log/suricata/fast.log", count=10):
    if not os.path.exists(file_path):
        return
    with open(file_path, "r") as f:
        lines = f.readlines()[-count:]
        for line in lines:
            entry = parse_fast_log(line)
            if entry and entry["classification"] != "Generic Protocol Command Decode":
                log_data.append(entry)
                classification = entry["classification"]
                classification_counts[classification] = classification_counts.get(classification, 0) + 1

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Replace with something secure
VIRUSTOTAL_API_KEY = "111a10aea56259d602d50d583fbe32a130c4a3f1e8fe9b5e258eb2f184e211bf"  # Replace this with your actual key
socketio = SocketIO(app, cors_allowed_origins="*")
EMAIL_ADDRESS = "throwawayemail735144@gmail.com"
EMAIL_PASSWORD = "iifvxgfzitannnsj"              # Generated via website
EMAIL_RECEIVER = "throwawayemail735144@gmail.com" # 

log_data = []
classification_counts = {}
latest_cpu_usage = {"cpu": 0.0}

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

def send_email_alert(log_data):
    msg = EmailMessage()
    msg['Subject'] = 'Urgent: New Suricata Log Alert'
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = EMAIL_RECEIVER

    content = f"""
    A new log was received on the dashboard, please interact with the chatbot for further details.

    Time: {log_data.get('timestamp', 'N/A')}
    Details: {log_data.get('details', 'N/A')}
    Classification: {log_data.get('classification', 'N/A')}
    Source IP: {log_data.get('src_ip', 'N/A')}
    Destination IP: {log_data.get('dest_ip', 'N/A')}
    Device: {log_data.get('device_name', 'N/A')}
    """
    msg.set_content(content)

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
            smtp.ehlo()  # Identity ourselves to the SMTP server
            smtp.starttls()  # Secure the connection using STARTTLS
            smtp.ehlo()  # Handshake with the server
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)  # Send the email
            print("Email sent successfully.")
    except Exception as e:
        print("Failed to send email:", e)

@app.before_request
def require_login():
    allowed_routes = ['login', 'static', 'handle_logs', 'get_logs', 'chat_with_langchain_bot', 
                      'alerts_over_time', 'severity_breakdown', 'get_fast_log', 
                      'receive_ports', 'receive_cpu_usage', 'get_cpu_usage', 'receive_windows_health']
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
    with open('windows_health.json') as f:
        devices = json.load(f)
    try:
        with open('windows_events.json') as f:
            events = json.load(f)
        total_events = len(events)
    except:
        total_events = 0
    total_devices = len(devices)
    return render_template('dashboard.html', total_devices=total_devices, total_events=total_events)

# ============================
# CHAT API (LangChain + Ollama)
# ============================

@app.route("/api/chat", methods=["POST"])
def chat_with_langchain_bot():
    user_input = request.json.get("message")
    if not user_input:
        return jsonify({"error": "No message provided"}), 400

    host_chatbot_url = "http://192.168.1.1:5005/chat"  # Replace with your actual host IP

    try:
        response = requests.post(host_chatbot_url, json={"message": user_input}, timeout=150)
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
        print("Sending email for log:", log_entry)
        send_email_alert(log_entry)
        socketio.emit("update_charts", to='*')
        return jsonify({"message": "Log received"}), 200
    return jsonify({"error": "No log data provided"}), 400

def receive_log():
    data = request.get_json()
    required_fields = {"timestamp", "details", "classification", "src_ip", "dest_ip", "device_name"}
    if not data or not all(field in data for field in required_fields):
        return jsonify({"error": "Invalid log format"}), 400

    receive_log.append(data)  # Add the log data to the logs list
    handle_logs()  # Save the logs to a file

    # Send email alert
    send_email_alert(data)  # Calling the email sending function

    return jsonify({"message": "Log received", "log": data}), 200

@app.route("/api/logs", methods=["GET"])
def get_logs():
    return jsonify(log_data)

def send_logs():
    """Returns all stored logs as JSON."""
    return jsonify(log_data)

@app.route("/api/fast-log", methods=["GET"])
def get_fast_log():
    return jsonify(log_data[-100:])

@app.route("/api/alerts-over-time")
def alerts_over_time():
    minute_timestamps = []
    for entry in log_data:
        if entry["classification"] == "Generic Protocol Command Decode":
            continue
        try:
            ts = datetime.strptime(entry["timestamp"], "%m/%d/%Y-%H:%M:%S.%f")
            minute_str = ts.strftime("%Y-%m-%d %H:%M")
            minute_timestamps.append(minute_str)
        except:
            continue

    counts = Counter(minute_timestamps)
    sorted_items = sorted(counts.items())
    if sorted_items:
        timestamps, alert_counts = zip(*sorted_items)
    else:
        timestamps, alert_counts = [], []

    return jsonify({"timestamps": timestamps, "alerts": list(alert_counts)})

@app.route("/api/severity-breakdown")
def severity_breakdown():
    filtered_counts = {
        k: v for k, v in classification_counts.items()
        if k != "Generic Protocol Command Decode"
    }
    return jsonify({
        "labels": list(filtered_counts.keys()),
        "percentages": list(filtered_counts.values())
    })

@app.route('/api/ports', methods=['GET', 'POST'])
def receive_ports():
    if request.method == 'POST':
        data = request.get_json()
        if not data or not isinstance(data, list):
            return jsonify({"error": "Invalid port data format"}), 400
        with open("open_ports.json", "w") as f:
            json.dump(data, f, indent=4)
        return jsonify({"message": "Port data received", "ports": data}), 200
    elif request.method == 'GET':
        try:
            with open("open_ports.json", "r") as f:
                data = json.load(f)
            return jsonify(data)
        except FileNotFoundError:
            return jsonify({"error": "No port data available"}), 404
        
@app.route("/api/event-count", methods=["GET"])
def event_count():
    return jsonify({"count": len(log_data)})

@app.route("/api/cpu", methods=["POST"])
def receive_cpu_usage():
    global latest_cpu_usage  # ADD THIS
    data = request.get_json()
    if data and "cpu" in data:
        latest_cpu_usage["cpu"] = data["cpu"]
        print(" CPU updated:", latest_cpu_usage["cpu"])
        return jsonify({"message": "CPU usage received"}), 200
    return jsonify({"error": "Invalid CPU data"}), 400

@app.route("/api/cpu", methods=["GET"])
def get_cpu_usage():
    return jsonify(latest_cpu_usage)

@app.route('/alerts')
def alerts():
    return render_template('allalerts.html')

@app.route('/allalerts.html')
def all_alerts():
    """Serves the main HTML dashboard."""
    return render_template('allalerts.html')

@app.route('/allwindows.html')
def all_windows():
    with open('windows_events.json') as f:
        data = json.load(f)
    total_events = len(data)
    return render_template('allwindows.html', all_windows = data)

@app.route("/alldevices.html")
def all_devices():
    with open('windows_health.json') as f:
        devices = json.load(f)
    return render_template("alldevices.html", devices=devices)

@app.route("/api/virustotal/ip", methods=["POST"])
def virustotal_ip_lookup():
    data = request.get_json()
    ip = data.get("ip")
    if not ip:
        return jsonify({"error": "IP address required"}), 400

    url = f"https://www.virustotal.com/api/v3/ip_addresses/{ip}"
    headers = {
        "x-apikey": VIRUSTOTAL_API_KEY
    }

    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return jsonify({"error": "Failed to retrieve data"}), response.status_code
        vt_data = response.json()
        return jsonify(vt_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/ctf', methods=['GET', 'POST'])
def sql_vulnerable_login():
    if request.method == 'POST':
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        # Still weak sanitization
        username = username.replace('"', "'")
        password = password.replace('"', "'")

        print("Received username:", repr(username))
        print("Received password:", repr(password))

        try:
            conn = sqlite3.connect("ctf.db")
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM users")
            print("All users in DB:", cursor.fetchall())

            # Moderately hard injection point
            query = f"""
                SELECT * FROM users
                WHERE username = (
                    SELECT username FROM users
                    WHERE username = '{username}'
                    LIMIT 1
                )
                AND password = '{password}'
                AND 1 = (
                    SELECT CASE
                        WHEN (SELECT COUNT(*) FROM users WHERE password = '{password}') >= 1
                        THEN 1 ELSE 0 END
                )
                HAVING 1=1 -- misleading clause to trip up logic-based filters
            """

            print("Executing query:", query)
            cursor.execute(query)
            user = cursor.fetchone()

        except Exception as e:
            print("DB error:", e)
            user = None
        finally:
            conn.close()

        if user:
            return render_template('ctf.html', message=f"Login Successful! Welcome, {username}")
        else:
            return render_template('ctf.html', message="Invalid Credentials.")

    return render_template('ctf.html', message="")

# ============================
# NEW WINDOWS LOG APIs
# ============================

@app.route('/api/windows_logs', methods=['GET', 'POST'])
def receive_windows_logs():
    if request.method == 'POST':
        try:
            data = request.get_json()
            if not isinstance(data, list):
                return jsonify({"error": "Expected a list of event logs"}), 400

            try:
                with open("windows_events.json", "r") as f:
                    existing_logs = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                existing_logs = []

            existing_logs.extend(data)

            with open("windows_events.json", "w") as f:
                json.dump(existing_logs, f, indent=2)

            return jsonify({"message": "Windows events stored"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # GET request returns count
    elif request.method == 'GET':
        try:
            with open("windows_events.json", "r") as f:
                logs = json.load(f)
            return jsonify({"count": len(logs)})
        except:
            return jsonify({"count": 0})
    
@app.route("/api/windows", methods=["POST"])
def receive_windows_health():
    try:
        data = request.get_json(force=True)
        if not isinstance(data, dict):
            return jsonify({"error": "Expected a JSON object"}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to parse JSON: {str(e)}"}), 400

    try:
        with open("windows_health.json", "r") as f:
            devices = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        devices = []

    # Remove existing entry with same device_name
    devices = [d for d in devices if d.get("device_name") != data.get("device_name")]
    devices.append(data)

    with open("windows_health.json", "w") as f:
        json.dump(devices, f, indent=2)

    return jsonify({"message": "Windows health info stored"}), 200

# ============================
# BACKGROUND LOG MONITORING
# ============================

def process_log_entry(log_entry):
    classification = log_entry["classification"]
    if classification == "Generic Protocol Command Decode":
        return  # Skip this log
    timestamp = log_entry["timestamp"]
    classification_counts[classification] = classification_counts.get(classification, 0) + 1
    log_data.append(log_entry)

if __name__ == "__main__":
    load_initial_logs()
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
