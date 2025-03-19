import os
import requests
import time
import re
import threading

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
        r"\[.*?\]\s+"                                            # Ignored bracketed data
        r"(.*?)\s+"                                             # Alert details (non-greedy)
        r"\[\*\*\]\s+"                                          # Literal [**]
        r"\[Classification:\s+\"(.*?)\"\]\s+"                    # Classification inside quotes
        r"\[Priority:\s+(\d+)\]\s+"                               # Priority (number)
        r"\{.*?\}\s+"                                           # Protocol info (ignored)
        r"([\d\.]+):\d+\s+->\s+([\d\.]+):\d+"                    # Source and destination IPs
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

def send_all_logs():
    """
    Reads the entire fast.log file and sends each parsed log entry to the API.
    This function is scheduled to run every 2 minutes.
    """
    print("Reading entire log file and sending logs...")
    try:
        with open(LOG_FILE, "r") as file:
            lines = file.readlines()
    except Exception as e:
        print("Error reading log file:", e)
        # Schedule next try even if reading fails
        threading.Timer(120, send_all_logs).start()
        return

    sent_count = 0
    for line in lines:
        log_entry = parse_fast_log(line)
        if log_entry:
            response = requests.post(LOGS_API_URL, json=log_entry)
            if response.status_code == 200:
                print("Log sent successfully:", log_entry)
                sent_count += 1
            else:
                print("Failed to send log:", response.status_code, response.text)
    print(f"Completed sending logs from file. Total sent: {sent_count}")
    # Schedule the next run in 2 minutes
    threading.Timer(120, send_all_logs).start()

if __name__ == "__main__":
    print("Starting log sender: Will send all logs (previous and new) every 2 minutes.")
    # Start the periodic log sender after 2 minutes (first run happens immediately)
    send_all_logs()
    # Keep the main thread alive
    while True:
        time.sleep(60)
