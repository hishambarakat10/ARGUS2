import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

OLLAMA_API_URL = "http://localhost:11434/api/generate"  # Default Ollama port
MODEL_NAME = "llama3"  # Ensure you have the correct model installed

@app.route("/generate", methods=["POST"])
def generate():
    """Handles requests to query LLaMA 3"""
    user_prompt = request.json.get("prompt", "").strip()
    
    if not user_prompt:
        return jsonify({"error": "Prompt cannot be empty"}), 400

    payload = {
        "model": MODEL_NAME,
        "prompt": user_prompt,
        "stream": False  # Change to True for streaming responses
    }

    try:
        response = requests.post(OLLAMA_API_URL, json=payload)
        response_data = response.json()
        return jsonify({"response": response_data.get("response", "No response generated")})
    except Exception as e:
        return jsonify({"error": f"Error communicating with Ollama: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5002, debug=True)  # Running on port 5002