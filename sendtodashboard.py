import os
import requests
import time
import re

LOG_FILE = "/var/log/suricata/fast.log"
LOGS_API_URL = "http://127.0.0.1:5000/api/logs"

# Regex to extract timestamp and classification
log_pattern = re.compile(
    r"(?P<timestamp>\d{2}/\d{2}/\d{4}-\d{2}:\d{2}:\d{2}\.\d+)  \[\*\*\] .*? \[\*\*\] \[Classification: (?P<classification>.*?)\]"
)

def read_logs():
    """ Continuously reads fast.log and sends a log entry every 10 seconds """
    with open(LOG_FILE, "r") as file:
        file.seek(0, os.SEEK_END)  # Move to the end of the file
        last_log = None

        while True:
            line = file.readline()
            if line:
                match = log_pattern.search(line)
                if match:
                    last_log = {
                        "timestamp": match.group("timestamp"),
                        "classification": match.group("classification")
                    }
            
            if last_log:
                response = requests.post(LOGS_API_URL, json=last_log)
                if response.status_code == 200:
                    print(f"Log sent successfully: {last_log}")
                else:
                    print(f"Failed to send log: {response.status_code}, {response.text}")
            else:
                print("No new log found, resending last known log...")

            time.sleep(10)  # Send a log every 10 seconds

if __name__ == "__main__":
    print("Monitoring fast.log and sending a log every 10 seconds...")
    read_logs()
