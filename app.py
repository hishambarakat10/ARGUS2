import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
import requests
import re
import time
import socket
import psutil  # Import for CPU usage
from flask import Flask, render_template_string



app = Flask(__name__)

# Function to extract data from JSON logs
def extract_data(file_path):
    try:
        data = {'timestamp': [], 'event_id': [], 'classification': []}
        with open(file_path, 'r') as file:
            json_data = []
            current_json = ""

            for line in file:
                if line.startswith("Received Log: {"):
                    current_json = line[len("Received Log: "):].strip()
                elif line.strip() == "}":
                    current_json += line.strip()
                    json_data.append(current_json)
                    current_json = ""
                elif current_json:
                    current_json += line.strip()

            for json_str in json_data:
                try:
                    log_data = json.loads(json_str)
                    data['timestamp'].append(log_data['timestamp'])
                    data['event_id'].append(log_data['event_id'])
                    data['classification'].append(log_data['classification'])
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON in line: {json_str}")
                    print(f"Error: {e}")

        return pd.DataFrame(data)

    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# Function to generate pie chart
def generate_pie_chart(df):
    classification_counts = df['classification'].value_counts()
    plt.figure(figsize=(8, 8))
    plt.pie(classification_counts, labels=classification_counts.index, autopct='%1.1f%%', startangle=90)
    plt.title('Classification Distribution')

    # Convert plot to base64 string
    img_io = io.BytesIO()
    plt.savefig(img_io, format='png')
    img_io.seek(0)
    return base64.b64encode(img_io.getvalue()).decode()

# Function to generate bar chart
def generate_bar_chart(df):
    classification_counts = df['classification'].value_counts()
    plt.figure(figsize=(10, 6))
    plt.bar(classification_counts.index, classification_counts.values)
    plt.xlabel('Classification')
    plt.ylabel('Count')
    plt.title('Classification Distribution')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    # Convert plot to base64 string
    img_io = io.BytesIO()
    plt.savefig(img_io, format='png')
    img_io.seek(0)
    return base64.b64encode(img_io.getvalue()).decode()

@app.route("/")
def home():
    return "Go to /run_notebook to view the results"

@app.route("/run_notebook")
def run_notebook():
    file_path = r"/home/capstone/cap_project/ARGUS-main/ARGUS/message.json"  # Update this path if needed

    df = extract_data(file_path)
    if df is None or df.empty:
        return "No data found or file not available."

    # Generate charts
    pie_chart = generate_pie_chart(df)
    bar_chart = generate_bar_chart(df)

    # Convert DataFrame to HTML table
    table_html = df.to_html(classes="table table-striped", index=False)

    # Render results in HTML
    html_template = f"""
    <html>
    <head>
        <title>Notebook Output</title>
        <style>
            body {{ font-family: Arial, sans-serif; text-align: center; }}
            .container {{ max-width: 900px; margin: auto; }}
            img {{ max-width: 100%; height: auto; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid black; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Executed Notebook Output</h1>
            <h2>Extracted Data</h2>
            {table_html}
            <h2>Pie Chart</h2>
            <img src="data:image/png;base64,{pie_chart}" alt="Pie Chart">
            <h2>Bar Chart</h2>
            <img src="data:image/png;base64,{bar_chart}" alt="Bar Chart">
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template)

if __name__ == "__main__":
    app.run(debug=True)


# Directory where Suricata logs are stored
LOG_DIR = "/var/log/suricata"
LOG_FILE = "fast.log"

# Flask server API endpoints
LOGS_API_URL = "http://127.0.0.1:5000/api/logs"
CPU_API_URL = "http://127.0.0.1:5000/api/cpu"

# Get the device name
DEVICE_NAME = socket.gethostname()

@app.route("/api/logs")

def parse_fast_log(line):
    """
    Parses a Suricata fast.log line and extracts relevant fields.
    """
    pattern = r"^(.*?)\s+\[\*\*\]\s+\[.*?\]\s+(.*?)\s+\[\*\*\]\s+\[Classification:\s(.*?)\].*?{.*?}\s([\d\.]+):\d+\s->\s([\d\.]+):\d+"
    match = re.match(pattern, line)

    if match:
        return {
            "timestamp": match.group(1),
            "details": match.group(2),
            "classification": match.group(3),
            "src_ip": match.group(4),
            "dest_ip": match.group(5),
            "device_name": DEVICE_NAME
        }
    return None

def send_to_dashboard(data, url):
    """
    Sends data to the Flask dashboard.
    """
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        print(f"Data sent successfully to {url}:", data)
    except requests.exceptions.RequestException as e:
        print(f"Failed to send data to {url}:", e)

def send_cpu_data():
    """
    Sends CPU usage data, including total CPU usage and per-core utilization, to the Flask dashboard.
    """
    cpu_data = {
        "device_name": DEVICE_NAME,
        "cpu_usage": psutil.cpu_percent(interval=1),  # Total CPU usage
        "cpu_cores": psutil.cpu_count(logical=True),  # Number of logical cores
        "per_core_usage": psutil.cpu_percent(interval=1, percpu=True)  # List of per-core usage
    }
    send_to_dashboard(cpu_data, CPU_API_URL)

def monitor_logs():
    """
    Continuously reads the Suricata fast.log file and sends parsed entries to the dashboard.
    """
    while True:
        with open(os.path.join(LOG_DIR, LOG_FILE), "r") as file:
            for line in file:
                log_entry = parse_fast_log(line)
                if log_entry:
                    send_to_dashboard(log_entry, LOGS_API_URL)
        
        # Send CPU data every cycle
        send_cpu_data()

        print("Waiting for 1 hour before reading logs again...")
        time.sleep(3600)  # Sleep for 1 hour

if __name__ == "__main__":
    monitor_logs()
