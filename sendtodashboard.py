import os
import requests
import time
import re

LOG_FILE = "/var/log/suricata/fast.log"
LOGS_API_URL = "http://127.0.0.1:5000/api/logs"

def parse_fast_log(line):
    """
    Parses a Suricata fast.log line and extracts relevant fields.
    
    Example logs:
      With quotes:
      03/19/2025-13:54:22.351676  [**] [1:1003:2] SQL Injection Attempt Detected [**] [Classification: "SQL Injection Occured"] [Priority: 3] {TCP} 142.251.186.94:80 -> 192.168.2.4:56148
      
      Without quotes:
      03/19/2025-13:54:08.151001  [**] [1:2231000:1] SURICATA QUIC failed decrypt [**] [Classification: Generic Protocol Command Decode] [Priority: 3] {UDP} 192.168.2.4:49019 -> 142.250.114.94:443
    """
    pattern = (
        r"^(\d{2}/\d{2}/\d{4}-\d{2}:\d{2}:\d{2}\.\d+)"       # Timestamp
        r"\s+\[\*\*\]\s+"                                      # Literal [**]
        r"\[.*?\]\s+"                                          # Ignored bracketed data (e.g., [1:2231000:1])
        r"(.*?)\s+"                                           # Alert details (non-greedy)
        r"\[\*\*\]\s+"                                        # Literal [**]
        r"\[Classification:\s+\"?(.*?)\"?\]\s+"                # Classification, optionally in quotes
        r"\[Priority:\s+(\d+)\]\s+"                             # Priority (number)
        r"\{.*?\}\s+"                                         # Protocol info (ignored)
        r"([\d\.]+):\d+\s+->\s+([\d\.]+):\d+"                  # Source and destination IPs
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
    Continuously monitors the fast.log file for new log entries.
    When a new line is added, it is parsed and, if valid,
    immediately sent to the API endpoint.
    """
    with open(file_path, "r") as file:
        file.seek(0, os.SEEK_END)  # Start at the end of the file
        while True:
            line = file.readline()
            if not line:
                time.sleep(0.1)  # Wait briefly if no new line
                continue

            print("Line read:", line.strip())  # Debug: show raw line
            log_entry = parse_fast_log(line)
            if log_entry:
                print("Parsed log:", log_entry)
                try:
                    response = requests.post(LOGS_API_URL, json=log_entry)
                    if response.status_code == 200:
                        print("Log sent successfully:", log_entry)
                    else:
                        print("Error sending log:", response.status_code, response.text)
                except Exception as e:
                    print("Exception while sending log:", e)
            else:
                print("Log not parsed; skipping.")

if __name__ == "__main__":
    print("Monitoring fast.log for new logs and sending them immediately...")
    follow_log(LOG_FILE)
