import os
import requests
import time
import re

LOG_FILE = "/var/log/suricata/fast.log"
LOGS_API_URL = "http://127.0.0.1:5000/api/logs"

def parse_fast_log(line):
    """
    Parses a Suricata fast.log line and extracts relevant fields.
    Example log:
    03/18/2025-04:55:16.293281  [**] [1:1003:2] SQL Injection Attempt Detected [**] [Classification: "SQL Injection Occured"] [Priority: 3] {TCP} 91.189.91.83:80 -> 192.168.2.4:41212
    """
    pattern = (
        r"^(\d{2}/\d{2}/\d{4}-\d{2}:\d{2}:\d{2}\.\d+)"         # Timestamp
        r"\s+\[\*\*\]\s+"                                        # Literal [**]
        r"\[.*?\]\s+"                                            # Ignored bracketed data (e.g., [1:1003:2])
        r"(.*?)\s+"                                             # Alert details (non-greedy)
        r"\[\*\*\]\s+"                                          # Literal [**]
        r"\[Classification:\s+\"(.*?)\"\]\s+"                    # Classification inside quotes
        r"\[Priority:\s+(\d+)\]\s+"                               # Priority (number)
        r"\{.*?\}\s+"                                           # Protocol info (ignored, e.g., {TCP})
        r"([\d\.]+):\d+\s+->\s+([\d\.]+):\d+"                    # Source and destination IP addresses
    )
    match = re.match(pattern, line)
    if match:
        priority_mapping = {
            "1": "Not Suspicious",
            "2": "Potentially Suspicious",
            "3": "Malicious Traffic"
        }
        priority = match.group(4)
        priority_description = priority_mapping.get(priority, "Unknown")
        return {
            "timestamp": match.group(1),
            "details": match.group(2).strip(),
            "classification": match.group(3).strip(),
            "priority": priority_description,
            "src_ip": match.group(5),
            "dest_ip": match.group(6)
        }
    return None

def follow_log(file_path):
    """
    Reads the fast.log file continuously and accumulates log entries.
    Every 2 minutes, all accumulated logs are sent individually to the API.
    """
    buffer = []  # List to hold parsed log entries
    next_send_time = time.time() + 10  # 2 minutes from now
    with open(file_path, "r") as file:
        file.seek(0, os.SEEK_END)  # Start reading at the end of file
        while True:
            line = file.readline()
            if line:
                log_entry = parse_fast_log(line)
                if log_entry:
                    buffer.append(log_entry)
            else:
                time.sleep(0.1)
            # Check if 2 minutes have elapsed
            if time.time() >= next_send_time:
                if buffer:
                    print(f"Sending {len(buffer)} log entries...")
                    for log_entry in buffer:
                        response = requests.post(LOGS_API_URL, json=log_entry)
                        if response.status_code == 200:
                            print(f"Log sent successfully: {log_entry}")
                        else:
                            print(f"Failed to send log: {response.status_code}, {response.text}")
                    buffer = []  # Clear the buffer after sending
                next_send_time = time.time() + 120  # Reset the timer

if __name__ == "__main__":
    print("Monitoring fast.log and sending logs every 2 minutes...")
    follow_log(LOG_FILE)
