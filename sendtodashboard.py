import os
import requests
import time
import re

LOG_FILE = "/var/log/suricata/fast.log"
LOGS_API_URL = "http://127.0.0.1:5000/api/logs"

# Updated regex to extract classification inside [Classification: ...]
log_pattern = re.compile(
    r"(?P<timestamp>\d{2}/\d{2}/\d{4}-\d{2}:\d{2}:\d{2}\.\d+)  \[\*\*\] .*? \[\*\*\] \[Classification: (?P<classification>.*?)\]"
)

def read_logs():
    """ Continuously reads fast.log and sends relevant log entries to the dashboard """
    with open(LOG_FILE, "r") as file:
        file.seek(0, os.SEEK_END)  # Move to the end of the file

        while True:
            line = file.readline()
            if not line:
                time.sleep(1)
                continue
            
            match = log_pattern.search(line)
            if match:
                log_entry = {
                    "timestamp": match.group("timestamp"),
                    "classification": match.group("classification")  # Extracted classification
                }
                response = requests.post(LOGS_API_URL, json=log_entry)
                
                if response.status_code == 200:
                    print(f"Log sent successfully: {log_entry}")
                else:
                    print(f"Failed to send log: {response.status_code}, {response.text}")

if __name__ == "__main__":
    print("Monitoring fast.log for new logs...")
    read_logs()
