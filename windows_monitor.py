# windows_monitor.py
import psutil
import socket
import platform
import time
import requests
import win32evtlog
import win32api
import win32con
from datetime import datetime

log_counter = 0
latest_data = {}

def get_device_name():
    return platform.node()

def get_ip_address():
    try:
        return socket.gethostbyname(socket.gethostname())
    except:
        return "Unavailable"

def get_os_version():
    return platform.platform()

def get_uptime():
    boot_time = psutil.boot_time()
    uptime_seconds = time.time() - boot_time
    hours = int(uptime_seconds // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    return f"{hours}h {minutes}m"

def get_cpu_usage():
    return psutil.cpu_percent(interval=0.5)

def get_memory_usage():
    return psutil.virtual_memory().percent

def collect_windows_metrics():
    global log_counter, latest_data
    while True:
        latest_data = {
            'device_name': get_device_name(),
            'ip_address': get_ip_address(),
            'os_version': get_os_version(),
            'uptime': get_uptime(),
            'cpu_percent': get_cpu_usage(),
            'memory_percent': get_memory_usage(),
            'last_check_in': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        log_counter += 1
        time.sleep(5)

def get_log_count():
    return log_counter

def get_latest_info():
    return latest_data

def get_security_logs(count=10):
    server = 'localhost'
    log_type = 'Security'
    hand = win32evtlog.OpenEventLog(server, log_type)
    flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
    events = win32evtlog.ReadEventLog(hand, flags, 0)
    logs = []

    for i, event in enumerate(events):
        if i >= count:
            break
        log = {
            "event_id": str(event.EventID),
            "time_generated": str(event.TimeGenerated.Format()),
            "category": str(event.EventCategory),
            "computer_name": event.ComputerName,
            "message": event.StringInserts[0] if event.StringInserts else "",
            "source_ip": "N/A",  # Optional: parse from message
            "account_name": "N/A",  # Optional: parse from message
            "priority": "High" if event.EventCategory == 1 else "Low"
        }
        logs.append(log)
    return logs

def send_logs():
    logs = get_security_logs(5)
    try:
        res = requests.post("http://192.168.2.8:5000/api/windows-events", json=logs)
        print("Status:", res.status_code, res.text)
    except Exception as e:
        print("Send failed:", e)

send_logs()
