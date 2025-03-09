import os
import requests
import time
import re
import chatbot  # Import AI analysis functions

LOG_FILE = "/var/log/suricata/fast.log"
DASHBOARD_API_URL = "http://127.0.0.1:5000/api/logs"
TRAINING_INTERVAL = 60  # Time in seconds between TinyLlama training requests
SEND_INTERVAL = 10  # Time in seconds to resend the last log entry (even if no new lines appear)

# Regex to extract timestamp and classification
log_pattern = re.compile(
    r"(?P<timestamp>\d{2}/\d{2}/\d{4}-\d{2}:\d{2}:\d{2}\.\d+)  \[\*\*] .*? \[\*\*] \[Classification: (?P<classification>.*?)\]"
)

def get_log_entries(file_path):
    """ Returns the current log entries from the file """
    log_entries = []
    with open(file_path, "r") as file:
        for line in file:
            match = log_pattern.search(line)
            if match:
                log_entries.append({
                    "timestamp": match.group("timestamp"),
                    "classification": match.group("classification")
                })
    return log_entries

def send_logs_periodically():
    """ Sends logs from the log file to the dashboard periodically """
    log_data_buffer = []  # Store log data for training and sending
    last_sent_time = time.time()

    while True:
        log_entries = get_log_entries(LOG_FILE)
        if log_entries:
            # Collect raw log lines and store in the buffer
            for entry in log_entries:
                log_data_buffer.append(entry)
                
                # Send the log entry to the dashboard
                requests.post(DASHBOARD_API_URL, json=entry)
                
                # Analyze with TinyLlama and store AI response
                ai_analysis = chatbot.analyze_with_tinyllama(log_entry=entry)
                chatbot.store_ai_log(entry, ai_analysis)

                print(f"Log sent successfully: {entry} | AI Analysis: {ai_analysis}")

        # Resend last log every SEND_INTERVAL seconds
        if time.time() - last_sent_time >= SEND_INTERVAL:
            if log_data_buffer:
                print("Resending last log entries...")
                last_sent_time = time.time()  # Reset the timer
                for entry in log_data_buffer:
                    requests.post(DASHBOARD_API_URL, json=entry)
                    ai_analysis = chatbot.analyze_with_tinyllama(log_entry=entry)
                    chatbot.store_ai_log(entry, ai_analysis)
                    print(f"Resent log: {entry} | AI Analysis: {ai_analysis}")
        
        time.sleep(1)  # Sleep for a short time to prevent high CPU usage

if __name__ == "__main__":
    print("Monitoring fast.log and sending logs on update...")
    send_logs_periodically()
