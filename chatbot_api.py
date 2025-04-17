from flask import Flask, request, jsonify
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
import requests

app = Flask(__name__)

# Connect to your local Ollama model
llm = OllamaLLM(model="llama3")

# 🔌 IP of your VM where Flask is running
VM_FLASK_API = "http://192.168.56.101:5000"  # Update if needed

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

# Run Flask server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005)