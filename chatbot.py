import requests

OLLAMA_API_URL = "http://localhost:11434/api/generate"
ai_logs = []  # Stores analyzed logs for chatbot responses

def analyze_with_tinyllama(log_entry):
    """ Sends log data to TinyLlama for analysis via Ollama API """
    prompt = f"Analyze this Suricata log entry: {log_entry}"
    response = requests.post(OLLAMA_API_URL, json={"model": "tinyllama", "prompt": prompt})
    
    if response.status_code == 200:
        return response.json().get("response", "No response from TinyLlama")
    else:
        return "Error analyzing with TinyLlama"

def store_ai_log(log_entry, analysis):
    """ Stores AI log analysis for chatbot queries """
    ai_logs.append({"log": log_entry, "analysis": analysis})

def handle_chat_request(user_message):
    """ Processes chatbot queries using TinyLlama """
    response = requests.post(OLLAMA_API_URL, json={"model": "tinyllama", "prompt": user_message})
    
    if response.status_code == 200:
        return response.json().get("response", "No response from TinyLlama")
    else:
        return "Error processing chat request"
