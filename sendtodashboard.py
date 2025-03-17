import os
import requests
import time
import re

LOG_FILE = "/var/log/suricata/fast.log"
LOGS_API_URL = "http://127.0.0.1:5000/api/logs"

def parse_fast_log(line):
    """
    Parses a Suricata fast.log line and extracts relevant fields.
    Also maps the priority to a human-readable description.
    """
    pattern = r"^(\d{2}/\d{2}/\d{4}-\d{2}:\d{2}:\d{2}\.\d+)\s+\*\*\s+\[.*?\]\s+(\w+)\s+\*\*\s+\[Classification:\s\"(.*?)\"\]\s+\[Priority:\s(\d+)\].*?(\d+\.\d+\.\d+\.\d+):\d+\s->\s(\d+\.\d+\.\d+\.\d+):\d+"

    match = re.match(pattern, line)

    if match:
        priority_mapping = {
            "1": "Not Suspicious",
            "2": "Potentially Suspicious",
            "3": "Malicious Traffic"
        }

        log_entry = {
            "timestamp": match.group(1),
            "details": match.group(2),
            "classification": match.group(3),
            "priority": priority_mapping.get(match.group(4), "Unknown"),
            "src_ip": match.group(5),
            "dest_ip": match.group(6)
        }

        # Ensure all required fields are present before sending
        if all(log_entry.values()):
            return log_entry

    return None  # Return None if parsing fails or any field is missing

def stream_log(file_path):
    """ Reads the log file from the beginning and sends all logs continuously. """
    with open(file_path, "r") as file:
        while True:
            line = file.readline()
            if not line:
                time.sleep(0.1)  # Wait for new logs if file hasn't updated
                continue

            log_entry = parse_fast_log(line)
            if log_entry:
                response = requests.post(LOGS_API_URL, json=log_entry)
                if response.status_code == 200:
                    print(f"Log sent successfully: {log_entry}")
                else:
                    print(f"Failed to send log: {response.status_code}, {response.text}")

if __name__ == "__main__":
    print("Streaming fast.log and sending logs continuously...")
    stream_log(LOG_FILE)
