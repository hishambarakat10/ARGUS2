# windows_monitor.py
import psutil
import socket
import platform
import time
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