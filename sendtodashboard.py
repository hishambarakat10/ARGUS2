import os
import requests
import time
import re
import socket
import threading
import psutil

LOG_FILE = "/var/log/suricata/fast.log"
LOGS_API_URL = "http://127.0.0.1:5000/api/logs"
PORTS_API_URL = "http://127.0.0.1:5000/api/ports"
CHATBOT_API_URL = "http://127.0.0.1:5005/chat" # Replace with your actual host IP
TARGET_IP = "127.0.0.1"
PORTS_TO_SCAN = range (1, 65536)

def parse_fast_log(line):
    pattern = (
        r"^(\d{2}/\d{2}/\d{4}-\d{2}:\d{2}:\d{2}\.\d+)"
        r"\s+\[\*\*\]\s+"
        r"\[.*?\]\s+"
        r"(.*?)\s+"
        r"\[\*\*\]\s+"
        r"\[Classification:\s+\"?(.*?)\"?\]\s+"
        r"\[Priority:\s+(\d+)\]\s+"
        r"\{.*?\}\s+"
        r"([\d\.]+):\d+\s+->\s+([\d\.]+):\d+"
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
    with open(file_path, "r") as file:
        file.seek(0, os.SEEK_END)
        while True:
            line = file.readline()
            if not line:
                time.sleep(0.1)
                continue

            print("Line read:", line.strip())
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

def scan_open_ports(ip, ports):
    open_ports = []
    for port in ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            try:
                s.connect((ip, port))
                open_ports.append(str(port))
            except:
                continue
    return open_ports

def send_open_ports_periodically():
    while True:
        open_ports = scan_open_ports(TARGET_IP, PORTS_TO_SCAN)
        print("Open ports:", open_ports)
        try:
            response = requests.post(PORTS_API_URL, json=open_ports)
            if response.status_code == 200:
                print("Open ports sent successfully.")

                # Also notify chatbot
                port_summary = ", ".join(open_ports) if open_ports else "No ports open"
                chatbot_msg = {
                    "message": f"Network update: Detected open ports - {port_summary}."
                }
                requests.post(CHATBOT_API_URL, json=chatbot_msg)
            else:
                print("Port data send error:", response.status_code, response.text)
        except Exception as e:
            print("Exception sending ports:", e)
        time.sleep(60)
        
def send_cpu_usage_periodically():
    while True:
        usage = psutil.cpu_percent(interval=1)
        try:
            requests.post("http://127.0.0.1:5000/api/cpu", json={"cpu": usage})
            print(f"Sent CPU usage: {usage}%")

            # Also send a quick warm-up message to chatbot
            chatbot_msg = {
                "message": f"System status update: CPU usage is {usage}%."
            }
            requests.post(CHATBOT_API_URL, json=chatbot_msg)

        except Exception as e:
            print("Failed to send CPU usage:", e)
        time.sleep(60)

if __name__ == "__main__":
    print("Starting Suricata log + port scanner monitor...")
    threading.Thread(target=follow_log, args=(LOG_FILE,), daemon=True).start()
    threading.Thread(target=send_open_ports_periodically, daemon=True).start()
    threading.Thread(target=send_cpu_usage_periodically, daemon=True).start()
    while True:
        time.sleep(120)
