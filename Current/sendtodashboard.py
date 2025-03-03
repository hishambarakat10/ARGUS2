import os
import json
import requests
import re
import time
import socket
import psutil  # Import for CPU usage

# Directory where Suricata logs are stored
LOG_DIR = "/var/log/suricata"
LOG_FILE = "fast.log"

# Flask server API endpoints
LOGS_API_URL = "http://127.0.0.1:5000/api/logs"
CPU_API_URL = "http://127.0.0.1:5000/api/cpu"

# Get the device name
DEVICE_NAME = socket.gethostname()

def parse_fast_log(line):
    """
    Parses a Suricata fast.log line and extracts relevant fields.
    """
    pattern = r"^(.*?)\s+\[\*\*\]\s+\[.*?\]\s+(.*?)\s+\[\*\*\]\s+\[Classification:\s\"(.*?)\"\].*?{.*?}\s([\d\.]+):\d+\s->\s([\d\.]+):\d+"
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
        time.sleep(20)  # Sleep for 1 hour

if __name__ == "__main__":
    monitor_logs()
