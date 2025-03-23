import json
import os
import sqlite3
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session

app = Flask(__name__)
app.secret_key = os.urandom(24)  # To store session data (like flash messages)

LOG_FILE = "logs.json"
CPU_FILE = "cpu_data.json"

# Load logs from file (if exists)
def load_logs():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return []
    return []

# Load CPU data from file (if exists)
def load_cpu_data():
    if os.path.exists(CPU_FILE):
        with open(CPU_FILE, "r") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return {}
    return {}

# Save logs to file
def save_logs():
    with open(LOG_FILE, "w") as file:
        json.dump(logs, file, indent=4)

# Save CPU data to file
def save_cpu_data():
    with open(CPU_FILE, "w") as file:
        json.dump(cpu_data_store, file, indent=4)

logs = load_logs()  # Load existing logs at startup
cpu_data_store = load_cpu_data()  # Load CPU data at startup

# Database connection and user authentication functions
def check_user_credentials(username, password):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    
    # Check if the username and password match
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    user = cursor.fetchone()
    conn.close()
    
    return user

@app.route('/')
def dashboard():
    """Serves the main HTML dashboard."""
    if 'logged_in' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in
    return render_template('dashboard.html')

@app.route('/api/logs', methods=['POST'])
def receive_log():
    """Receives structured log data and stores it persistently."""
    data = request.get_json()
    
    required_fields = {"timestamp", "details", "classification", "src_ip", "dest_ip", "device_name"}
    if not data or not all(field in data for field in required_fields):
        return jsonify({"error": "Invalid log format"}), 400

    logs.append(data)
    save_logs()  # Save logs to file
    return jsonify({"message": "Log received", "log": data}), 200

@app.route('/api/logs', methods=['GET'])
def send_logs():
    """Returns all stored logs as JSON."""
    return jsonify(logs)

@app.route('/api/cpu', methods=['POST'])
def receive_cpu_data():
    """Receives and stores CPU usage data persistently.""" 
    data = request.get_json()

    required_fields = {"device_name", "cpu_usage", "cpu_cores", "per_core_usage"}
    if not data or not all(field in data for field in required_fields):
        return jsonify({"error": "Invalid CPU data format"}), 400

    cpu_data_store[data["device_name"]] = {
        "cpu_usage": data["cpu_usage"],
        "cpu_cores": data["cpu_cores"],
        "per_core_usage": data["per_core_usage"]
    }
    
    save_cpu_data()  # Save CPU data to file
    return jsonify({"message": "CPU data received", "cpu_data": cpu_data_store[data["device_name"]]}), 200

@app.route('/api/cpu', methods=['GET'])
def send_cpu_data():
    """Returns the latest CPU usage data for all devices."""
    return jsonify(cpu_data_store)

@app.route('/ctf', methods=['GET', 'POST'])
def sql_vulnerable_login():
    """Handles the SQL vulnerable login form."""
    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")

        conn = sqlite3.connect("ctf.db")
        cursor = conn.cursor()

        try:
            # **Vulnerable SQL Query**
            query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
            cursor.execute(query)
            user = cursor.fetchone()
        except sqlite3.OperationalError as e:
            # Handle the exception to prevent it from showing up
            user = None
        finally:
            conn.close()

        if user:
            return render_template('ctf.html', message=f"Login Successful! Welcome, {username}")
        else:
            return render_template('ctf.html', message="Invalid Credentials.")

    return render_template('ctf.html', message="")

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles the login form."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = check_user_credentials(username, password)

        if user:
            session['logged_in'] = True  # Set session data to indicate user is logged in
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid username or password.", "error")

    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logs out the user and clears the session."""
    session.pop('logged_in', None)  # Remove the 'logged_in' session key
    return redirect(url_for('login'))  # Redirect to the login page

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
