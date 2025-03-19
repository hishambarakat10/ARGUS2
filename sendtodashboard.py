import os
import requests
import time
import re

LOG_FILE = "/var/log/suricata/fast.log"
LOGS_API_URL = "http://127.0.0.1:5000/api/logs"

def parse_fast_log(line):
    """
    Parses a Suricata fast.log line and extracts relevant fields.
    This version is adapted to match log lines like:
    03/18/2025-04:55:16.293281  [**] [1:1003:2] SQL Injection Attempt Detected [**] [Classification: "SQL Injection Occured"] [Priority: 3] {TCP} 91.189.91.83:80 -> 192.168.2.4:41212
    """
    pattern = (
        r"^(\d{2}/\d{2}/\d{4}-\d{2}:\d{2}:\d{2}\.\d+)"         # Timestamp
        r"\s+\[\*\*\]\s+"                                        # Literal [**]
        r"\[.*?\]\s+"                                            # [1:1003:2] (ignored)
        r"(.*?)\s+"                                             # Details (non-greedy to capture the alert text)
        r"\[\*\*\]\s+"                                          # Literal [**]
        r"\[Classification:\s+\"(.*?)\"\]\s+"                    # Classification (inside quotes)
        r"\[Priority:\s+(\d+)\]\s+"                               # Priority (digits)
        r"\{.*?\}\s+"                                           # Protocol info (e.g. {TCP}, ignored)
        r"([\d\.]+):\d+\s+->\s+([\d\.]+):\d+"                    # Source and destination IPs
    )
    match = re.match(pattern, line)
    if match:
        return {
            "timestamp": match.group(1),
            "details": match.group(2).strip(),
            "classification": match.group(3).strip(),
            "priority": match.group(4),
            "src_ip": match.group(5),
            "dest_ip": match.group(6)
        }
    return None

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
