import os
import requests
import time
import re
import chatbot  # Import AI analysis functions

LOG_FILE = "/var/log/suricata/fast.log"
DASHBOARD_API_URL = "http://127.0.0.1:5000/api/logs"

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
            if line:
                match = log_pattern.search(line)
                if match:
                    log_entry = {
                        "timestamp": match.group("timestamp"),
                        "classification": match.group("classification")
                    }
                    
                    # Send log to dashboard
                    requests.post(DASHBOARD_API_URL, json=log_entry)
                    
                    # Get TinyLlama analysis and store it
                    ai_analysis = chatbot.analyze_with_tinyllama(log_entry)
                    chatbot.store_ai_log(log_entry, ai_analysis)

                    print(f"Log sent successfully: {log_entry} | AI Analysis: {ai_analysis}")

            else:
                time.sleep(0.1)  # Prevent high CPU usage

if __name__ == "__main__":
    print("Monitoring fast.log and sending logs on update...")
    follow_log(LOG_FILE)
