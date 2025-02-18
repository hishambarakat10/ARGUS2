import os
import re
import json
import requests
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
import time
import socket
import psutil
from flask import Flask, request, jsonify, render_template_string
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app)

LOG_DIR = "/var/log/suricata"
LOG_FILE = "fast.log"

LOGS_API_URL = "http://127.0.0.1:5000/api/logs"
CPU_API_URL = "http://127.0.0.1:5000/api/cpu"
DEVICE_NAME = socket.gethostname()
logs = []  # Store received logs

def extract_data(file_path):
    try:
        data = {'timestamp': [], 'event_id': [], 'classification': []}
        pattern = re.compile(r"^(\d{2}/\d{2}/\d{4}-\d{2}:\d{2}:\d{2}\.\d+)  \[\*\*] \[1:(\d+):\d+] .*? \[\*\*] \[Classification: ([^]]+)]")
        
        with open(file_path, 'r') as file:
            for line in file:
                match = pattern.search(line)
                if match:
                    data['timestamp'].append(match.group(1))
                    data['event_id'].append(match.group(2))
                    data['classification'].append(match.group(3))
        
        return pd.DataFrame(data)
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

@app.route("/api/logs", methods=['GET'])
def get_logs():
    file_path = os.path.join(LOG_DIR, LOG_FILE)
    df = extract_data(file_path)
    if df is None or df.empty:
        return jsonify({"error": "No logs found"}), 404
    return df.to_json(orient="records")

def send_to_dashboard(data, url):
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        print(f"Data sent successfully to {url}:", data)
    except requests.exceptions.RequestException as e:
        print(f"Failed to send data to {url}:", e)

def send_cpu_data():
    cpu_data = {
        "device_name": DEVICE_NAME,
        "cpu_usage": psutil.cpu_percent(interval=1),
        "cpu_cores": psutil.cpu_count(logical=True),
        "per_core_usage": psutil.cpu_percent(interval=1, percpu=True)
    }
    send_to_dashboard(cpu_data, CPU_API_URL)

def generate_pie_chart(df):
    classification_counts = df['classification'].value_counts()
    plt.figure(figsize=(8, 8))
    plt.pie(classification_counts, labels=classification_counts.index, autopct='%1.1f%%', startangle=90)
    plt.title('Classification Distribution')
    img_io = io.BytesIO()
    plt.savefig(img_io, format='png')
    plt.close()
    img_io.seek(0)
    return base64.b64encode(img_io.getvalue()).decode()

def generate_line_chart(df):
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['alert_count'] = 1
    df_grouped = df.groupby(df['timestamp'].dt.floor('T')).count()
    
    plt.figure(figsize=(12, 6))
    plt.plot(df_grouped.index, df_grouped['alert_count'], marker='o', linestyle='-')
    plt.xlabel('Timestamp')
    plt.ylabel('Number of Alerts')
    plt.title('Alerts Over Time')
    plt.xticks(rotation=90, ha='right')
    plt.tight_layout()
    img_io = io.BytesIO()
    plt.savefig(img_io, format='png')
    plt.close()
    img_io.seek(0)
    return base64.b64encode(img_io.getvalue()).decode()

@app.route("/run_notebook")
def run_notebook():
    file_path = os.path.join(LOG_DIR, LOG_FILE)
    df = extract_data(file_path)
    if df is None or df.empty:
        return "No data found or file not available."
    
    pie_chart = generate_pie_chart(df)
    line_chart = generate_line_chart(df)

    html_template = f"""
    <html>
    <head>
        <title>Real Time Dashboard</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.0/socket.io.js"></script>
        <script type="text/javascript">
            var socket = io();
            socket.on('update_charts', function(data) {{
                document.getElementById('pie_chart').src = 'data:image/png;base64,' + data.pie_chart;
                document.getElementById('line_chart').src = 'data:image/png;base64,' + data.line_chart;
            }});
        </script>
    </head>
    <body>
        <h1>Real Time Dashboard</h1>
        <h2>Pie Chart</h2>
        <img id="pie_chart" src="data:image/png;base64,{pie_chart}" alt="Pie Chart">
        <h2>Line Chart</h2>
        <img id="line_chart" src="data:image/png;base64,{line_chart}" alt="Line Chart">
    </body>
    </html>
    """
    return render_template_string(html_template)

def monitor_logs():
    while True:
        with open(os.path.join(LOG_DIR, LOG_FILE), "r") as file:
            for line in file:
                log_entry = extract_data(line)
                if log_entry is not None:
                    send_to_dashboard(log_entry, LOGS_API_URL)
        send_cpu_data()
        print("Waiting for 1 hour before reading logs again...")
        time.sleep(3600)

if __name__ == "__main__":
    socketio.start_background_task(monitor_logs)
    socketio.run(app, debug=True)
