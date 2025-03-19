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
        r"\[.*?\]\s+"                                            # Ignored bracketed data
        r"(.*?)\s+"                                             # Alert details (non-greedy)
        r"\[\*\*\]\s+"                                          # Literal [**]
        r"\[Classification:\s+\"(.*?)\"\]\s+"                    # Classification
        r"\[Priority:\s+(\d+)\]\s+"                               # Priority
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
        return {
            "timestamp": match.group(1),
            "details": match.group(2).strip(),
            "classification": match.group(3).strip(),
            "priority": priority_mapping.get(priority, "Unknown"),
            "src_ip": match.group(5),
            "dest_ip": match.group(6)
        }
    else:
        print("Failed to parse line:", line.strip())
    return None

def follow_log(file_path):
    """
    Continuously monitors fast.log for new lines and sends new logs immediately.
    """
    with open(file_path, "r") as file:
        file.seek(0, os.SEEK_END)  # Start at the end of the file
        while True:
            line = file.readline()
            if line:
                print("Line read:", line.strip())  # Debug: print raw line
                log_entry = parse_fast_log(line)
                if log_entry:
                    print("Parsed log:", log_entry)  # Debug: print parsed log
                    try:
                        response = requests.post(LOGS_API_URL, json=log_entry)
                        if response.status_code == 200:
                            print("Log sent:", log_entry)
                        else:
                            print("Error sending log:", response.status_code, response.text)
                    except Exception as e:
                        print("Exception while sending log:", e)
                else:
                    print("Log not parsed; skipping.")
            else:
                time.sleep(0.1)

if __name__ == "__main__":
    print("Monitoring fast.log for new logs...")
    follow_log(LOG_FILE)
