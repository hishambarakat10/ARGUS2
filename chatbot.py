import requests
from flask import Flask, request, jsonify
from flask_cors import CORS  # Allow cross-origin requests

app = Flask(__name__)
CORS(app)  # Enable CORS so the dashboard can communicate

OLLAMA_API_URL = "http://127.0.0.1:11434"  # Ollama API
DASHBOARD_API_URL = "http://127.0.0.1:5000/api/logs"  # Fetch logs from Dashboard
MODEL_NAME = "tinyllama"

SYSTEM_PROMPT = (
    "You are an AI assistant that only answers questions related to the IDS logs "
    "from Suricata. Use the provided log data to generate informed responses. "
    "Ignore any unrelated questions."
)

def get_latest_logs():
    """Fetch the latest logs from the dashboard API"""
    try:
        response = requests.get(DASHBOARD_API_URL)
        if response.status_code == 200:
            logs = response.json()
            return logs if logs else "No recent IDS logs available."
        else:
            return "Error: Could not fetch IDS logs from the dashboard."
    except Exception as e:
        return f"Error fetching logs: {str(e)}"

def query_ollama_api(user_message):
    """Query Ollama AI with IDS logs for context-aware answers"""
    logs_data = get_latest_logs()
    full_prompt = f"{SYSTEM_PROMPT}\n\nRecent IDS Logs:\n{logs_data}\n\nUser: {user_message}\nAI:"

    payload = {
        "model": MODEL_NAME,
        "prompt": full_prompt,
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_API_URL, json=payload)
        response_data = response.json()
        return response_data.get("response", "I couldn't generate a response.")
    except Exception as e:
        return f"Error communicating with Ollama: {str(e)}"

@app.route("/chat", methods=["POST"])
def chat():
    """Handle user queries and return IDS-aware chatbot responses"""
    user_input = request.json.get("message", "").strip()
    if not user_input:
        return jsonify({"error": "Empty message"}), 400
    
    bot_response = query_ollama_api(user_input)
    return jsonify({"response": bot_response})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
