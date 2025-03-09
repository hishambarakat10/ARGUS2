import requests
import json

OLLAMA_API_URL = "http://localhost:11434/api/generate"
ai_logs = []  # Stores analyzed logs for chatbot responses

def analyze_with_tinyllama(log_entry=None, query=None, classification_data=None):
    """ Sends log data or query to TinyLlama for analysis via Ollama API """
    if log_entry:
        prompt = f"Analyze this Suricata log entry: {log_entry}"
    elif query:
        prompt = f"User query: {query}. Please provide insights based on the logs and classifications."
    elif classification_data:
        prompt = f"Analyze the classification data: {classification_data}"
    else:
        return "No valid input provided."

    response = requests.post(OLLAMA_API_URL, json={"model": "tinyllama", "prompt": prompt})

    # Handle JSON response
    try:
        return response.json().get("response", "No response from TinyLlama")
    except requests.exceptions.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return "Error decoding response from TinyLlama"

def store_ai_log(log_entry, analysis):
    """ Stores AI log analysis for chatbot queries """
    ai_logs.append({"log": log_entry, "analysis": analysis})

def handle_chat_request(user_message):
    """ Processes chatbot queries using TinyLlama """
    # Here, you could query log data or classification data
    return analyze_with_tinyllama(query=user_message)
