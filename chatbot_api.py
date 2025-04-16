from flask import Flask, request, jsonify
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
import requests
import re

app = Flask(__name__)

# Connect to your local Ollama model
llm = OllamaLLM(model="llama3", max_tokens=100)

# 🔌 IP of your VM where Flask is running
VM_FLASK_API = "http://192.168.56.101:5000"  # Update if needed

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
            for log in logs[-20:]  # last 20 logs for performance
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

# Chatbot personality prompt
template = """
You are Argus Sentinel — a slightly witty, but serious Intrusion Detection System (IDS) assistant.

You ONLY answer questions about:
- Suricata fast.log entries
- Alert classifications
- Source and destination IPs
- Chart data showing alert volume and severity breakdown

LOG DATA:
{log_data}

CHART DATA:
{chart_data}

User question:
{question}

Respond clearly, based only on the above.
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

    try:
        response = chain.invoke({
            "question": user_input,
            "log_data": log_data,
            "chart_data": chart_data
        })
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"response": f"Chatbot error: {str(e)}"}), 500

# Warm up the LLM on startup with a test message
if __name__ == "__main__":
    try:
        print("Warming up LLaMA chatbot with previous fast.log entries...")
        log_data = load_startup_logs()
        _ = chain.invoke({
            "question": "Summarize the most recent logs",
            "log_data": log_data,
            "chart_data": "None"
        })
        print("Chatbot is warm and ready with startup logs.")
    except Exception as e:
        print(f"Warmup failed: {e}")

    app.run(host="0.0.0.0", port=5005)