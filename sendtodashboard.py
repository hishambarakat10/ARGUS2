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

def follow_log(file_path):
    """ Continuously reads fast.log and sends logs when new lines appear """
    with open(file_path, "r") as file:
        file.seek(0, os.SEEK_END)  # Move to the end of the file

        while True:
            line = file.readline()
            print(line)
            break
            if line:
                match = log_pattern.search(line)
                if match:
                    log_entry = {
                        "timestamp": match.group("timestamp"),
                        "classification": match.group("classification")
                    }
                    response = requests.post(LOGS_API_URL, json=log_entry)
                    
                    if response.status_code == 200:
                        print(f"Log sent successfully: {log_entry}")
                    else:
                        print(f"Failed to send log: {response.status_code}, {response.text}")
            else:
                time.sleep(0.1)  # Prevent high CPU usage when no new data

if __name__ == "__main__":
    print("Monitoring fast.log and sending logs on update...")
    follow_log(LOG_FILE)
