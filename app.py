import json
from flask import Flask, jsonify, render_template

app = Flask(__name__)

# Define threat severity based on classification
SEVERITY_MAP = {
    "Not Suspicious Traffic": "Low",
    "Misc activity": "Medium",
    "Potentially Bad Traffic": "High",
    "Attack Detected": "Critical"
}

# Load logs and simplify them for users
def process_logs():
    with open("logs.json", "r", encoding="utf-8") as file:
        logs = json.load(file)

    simplified_logs = []
    for log in logs:
        simplified_logs.append({
            "time_detected": log.get("timestamp", "Unknown"),
            "device": log.get("device_name", "Unknown"),
            "threat_level": SEVERITY_MAP.get(log.get("classification", ""), "Unknown"),
            "threat_description": log.get("classification", "Unknown"),
            "recommended_action": "Check your network" if SEVERITY_MAP.get(log.get("classification", "")) in ["High", "Critical"] else "No action needed"
        })
    
    return simplified_logs

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/logs")
def get_logs():
    return jsonify(process_logs())

if __name__ == "__main__":
    app.run(debug=True)
