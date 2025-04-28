from flask import Flask, request, jsonify
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
import requests
import re

app = Flask(__name__)

# Connect to your local Ollama model
llm = OllamaLLM(model="llama3", max_tokens=100)

# 🔌 IP of your VM where Flask is running
VM_FLASK_API = "http://:5000"  # Update if needed

# Load startup logs from the VM
def load_startup_logs(file_path="/var/log/suricata/fast.log", count=10):
    logs = []
    try:
        with open(file_path, "r") as f:
            lines = f.readlines()[-count:]
        for line in lines:
            match = re.match(
                r"^(\d{2}/\d{2}/\d{4}-\d{2}:\d{2}:\d{2}\.\d+)\s+\[\*\*\]\s+\[.*?\]\s+(.*?)\s+\[\*\*\]\s+\[Classification:\s+\"?(.*?)\"?\]\s+\[Priority:\s+(\d+)\]\s+\{.*?\}\s+([\d\.]+):\d+\s+->\s+([\d\.]+):\d+",
                line
            )
            if match:
                logs.append(f"{match.group(1)} | {match.group(3)} | {match.group(5)} → {match.group(6)}")
    except Exception as e:
        logs.append(f"Error loading fast.log: {str(e)}")
    return "\n".join(logs)

# Load latest logs from the VM API
def get_fast_log_data():
    try:
        res = requests.get(f"{VM_FLASK_API}/api/fast-log", timeout=5)
        logs = res.json()
        formatted = "\n".join([
            f"{log['timestamp']} | {log['classification']} | {log['src_ip']} → {log['dest_ip']}"
            for log in logs[-10:]  # last 20 logs for performance
        ])
        return formatted
    except Exception as e:
        return f"Error loading fast.log: {str(e)}"

# Load chart data
def get_chart_data():
    try:
        alerts = requests.get(f"{VM_FLASK_API}/api/alerts-over-time", timeout=5).json()
        severity = requests.get(f"{VM_FLASK_API}/api/severity-breakdown", timeout=5).json()
        return {
            "alerts_over_time": alerts,
            "severity_breakdown": severity
        }
    except Exception as e:
        return {"error": f"Chart API error: {str(e)}"}
    
def get_cpu_health():
    try:
        res = requests.get(f"{VM_FLASK_API}/api/cpu", timeout=5)
        return res.json().get("cpu", "unknown")
    except Exception as e:
        return f"Error fetching CPU health: {str(e)}"

def get_open_ports():
    try:
        res = requests.get(f"{VM_FLASK_API}/api/ports", timeout=5)
        data = res.json()
        if isinstance(data, list):
            return ", ".join(data) if data else "No open ports detected"
        return "No open port data available"
    except Exception as e:
        return f"Error fetching open ports: {str(e)}"

# Chatbot personality prompt
template = """
You are Argus Sentinel — a slightly witty but serious Intrusion Detection System (IDS) assistant.

You ONLY answer questions about:
- Suricata fast.log entries
- Alert classifications
- Source and destination IPs
- Chart data showing alert volume and severity breakdown
- Current CPU usage health
- Open ports detected on the system

LOG DATA:
{log_data}

CHART DATA:
{chart_data}

CPU HEALTH:
{cpu_health}%

OPEN PORTS:
{open_ports}

User question:
{question}

Respond clearly and concisely in **no more than two sentences**, based only on the above.
If the question is unrelated to IDS data, respond: "Sorry, I only answer questions about IDS logs, CPU health, open ports, and alert data."
"""

prompt = PromptTemplate(
    input_variables=["log_data", "chart_data", "question"],
    template=template
)

# Chain to combine prompt with LLM
chain = prompt | llm

# Chat route
@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message")
    if not user_input:
        return jsonify({"error": "No message provided"}), 400

    log_data = get_fast_log_data()
    chart_data = get_chart_data()
    cpu_health = get_cpu_health()
    open_ports = get_open_ports()

    try:
        response = chain.invoke({
            "question": user_input,
            "log_data": log_data,
            "chart_data": chart_data,
            "cpu_health": cpu_health,
            "open_ports": open_ports
        })
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"response": f"Chatbot error: {str(e)}"}), 500

# Warm up the LLM on startup with a test message
if __name__ == "__main__":
    try:
        print("Warming up LLaMA chatbot with previous fast.log entries...")
        log_data = load_startup_logs()
        chart_data = get_chart_data()
        cpu_health = get_cpu_health()
        open_ports = get_open_ports()
        _ = chain.invoke({
            "question": "Summarize the most recent logs",
            "log_data": log_data,
            "chart_data": chart_data,
            "cpu_health": cpu_health,
            "open_ports": open_ports
        })
        print("Chatbot is warm and ready with startup logs.")
    except Exception as e:
        print(f"Warmup failed: {e}")

    app.run(host="0.0.0.0", port=5005)