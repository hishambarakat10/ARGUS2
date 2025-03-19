import os
import requests
import time
import re
import threading

LOG_FILE = "/var/log/suricata/fast.log"
LOGS_API_URL = "http://127.0.0.1:5000/api/logs"

# Global buffer to hold parsed log entries
buffer = []
buffer_lock = threading.Lock()  # Protects access to the buffer

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
    else:
        print("Failed to parse line:", line.strip())
    return None

def send_logs():
    """
    Sends all accumulated logs in the buffer to the API and then clears the buffer.
    This function is scheduled to run every 2 minutes using threading.Timer.
    """
    global buffer
    with buffer_lock:
        logs_to_send = buffer.copy()
        buffer.clear()
    if logs_to_send:
        print(f"Sending {len(logs_to_send)} log entries...")
        for log_entry in logs_to_send:
            response = requests.post(LOGS_API_URL, json=log_entry)
            if response.status_code == 200:
                print("Log sent successfully:", log_entry)
            else:
                print("Failed to send log:", response.status_code, response.text)
    else:
        print("No logs to send at this time.")
    # Schedule the next send in 2 minutes
    threading.Timer(120, send_logs).start()

def follow_log(file_path):
    """
    Continuously reads the fast.log file and appends parsed log entries to the global buffer.
    """
    with open(file_path, "r") as file:
        file.seek(0, os.SEEK_END)  # Start at the end of the file
        while True:
            line = file.readline()
            if line:
                # Debug: print raw line
                print("Line read:", line.strip())
                log_entry = parse_fast_log(line)
                if log_entry:
                    print("Parsed log:", log_entry)
                    with buffer_lock:
                        buffer.append(log_entry)
            else:
                time.sleep(0.1)

if __name__ == "__main__":
    print("Monitoring fast.log and sending logs every 2 minutes using a background timer...")
    # Start the periodic log sender after 2 minutes
    threading.Timer(10, send_logs).start()
    follow_log(LOG_FILE)
