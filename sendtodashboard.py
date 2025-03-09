import os
import requests
import time
import re

LOG_FILE = "/var/log/suricata/fast.log"
DASHBOARD_API_URL = "http://127.0.0.1:5000/api/logs"
OLLAMA_API_URL = "http://localhost:11434/api/generate"

# Regex to extract timestamp and classification
log_pattern = re.compile(
    r"(?P<timestamp>\d{2}/\d{2}/\d{4}-\d{2}:\d{2}:\d{2}\.\d+)  \[\*\*\] .*? \[\*\*\] \[Classification: (?P<classification>.*?)\]"
)

def analyze_with_tinyllama(log_entry):
    """ Sends log data to TinyLlama for analysis via Ollama API """
    prompt = f"Analyze this Suricata log entry: {log_entry}"
    response = requests.post(OLLAMA_API_URL, json={"model": "tinyllama", "prompt": prompt})
    return response.json().get("response", "No response from TinyLlama")

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
                    
                    # Get TinyLlama analysis
                    ai_analysis = analyze_with_tinyllama(log_entry)
                    
                    # Store AI analysis for chatbot API
                    requests.post("http://127.0.0.1:5000/api/ai-log", json={"log": log_entry, "analysis": ai_analysis})
                    
                    print(f"Log sent successfully: {log_entry} | AI Analysis: {ai_analysis}")

            else:
                time.sleep(0.1)  # Prevent high CPU usage

if __name__ == "__main__":
    print("Monitoring fast.log and sending logs on update...")
    follow_log(LOG_FILE)
