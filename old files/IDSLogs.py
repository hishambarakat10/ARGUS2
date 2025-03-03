import json

def parse_logs(input_file, output_file):
    logs = []
    log_entry = {}
    
    with open(input_file, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()

            if line.startswith("Received Log:"):
                if log_entry:  
                    logs.append(log_entry)  
                log_entry = {}

            elif '"timestamp":' in line:
                log_entry["timestamp"] = line.split(": ", 1)[1].strip('",')

            elif '"event_id":' in line:
                log_entry["event_id"] = line.split(": ", 1)[1].strip('",')

            elif '"before_classification":' in line:
                log_entry["before_classification"] = line.split(": ", 1)[1].strip('",')

            elif '"classification":' in line:
                log_entry["classification"] = line.split(": ", 1)[1].strip('",')

            elif '"device_name":' in line:
                log_entry["device_name"] = line.split(": ", 1)[1].strip('",')

        if log_entry:  
            logs.append(log_entry)

    with open(output_file, 'w', encoding='utf-8') as json_file:
        json.dump(logs, json_file, indent=4)

    print(f"Logs successfully converted to {output_file}")

# Example Usage
parse_logs("message.txt", "logs.json")
