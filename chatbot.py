import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

OLLAMA_API_URL = "http://localhost:11434/api/generate"  # Ollama's default port
MODEL_NAME = "tinyllama"  # Use the TinyLlama model

SYSTEM_PROMPT = "You are an AI assistant that only answers questions related to the IDS logs from Suricata. Ignore any unrelated questions."

def query_ollama_api(user_message):
    payload = {
        "model": MODEL_NAME,
        "prompt": f"{SYSTEM_PROMPT}\n\nUser: {user_message}\nAI:",
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
    user_input = request.json.get("message", "").strip()
    if not user_input:
        return jsonify({"error": "Empty message"}), 400
    
    bot_response = query_ollama_api(user_input)
    return jsonify({"response": bot_response})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
