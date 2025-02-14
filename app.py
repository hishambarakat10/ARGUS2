import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
import time
from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app)

LOG_DIR = "/var/log/suricata"
LOG_FILE = "fast.log"  # Assuming the log file is named eve.log

# Function to extract data from JSON logs
def extract_data(file_path):
    try:
        data = {'timestamp': [], 'event_id': [], 'classification': []}
        with open(file_path, 'r') as file:
            for line in file:
                try:
                    log_data = json.loads(line.strip())
                    data['timestamp'].append(log_data['timestamp'])
                    data['event_id'].append(log_data['event_id'])
                    data['classification'].append(log_data['classification'])
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON in line: {line.strip()}")
                    print(f"Error: {e}")

        return pd.DataFrame(data)

    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# Function to generate pie chart
def generate_pie_chart(df):
    classification_counts = df['classification'].value_counts()
    plt.figure(figsize=(8, 8))
    plt.pie(classification_counts, labels=classification_counts.index, autopct='%1.1f%%', startangle=90)
    plt.title('Classification Distribution')

    # Convert plot to base64 string
    img_io = io.BytesIO()
    plt.savefig(img_io, format='png')
    img_io.seek(0)
    return base64.b64encode(img_io.getvalue()).decode()

# Function to generate bar chart
def generate_bar_chart(df):
    classification_counts = df['classification'].value_counts()
    plt.figure(figsize=(10, 6))
    plt.bar(classification_counts.index, classification_counts.values)
    plt.xlabel('Classification')
    plt.ylabel('Count')
    plt.title('Classification Distribution')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    # Convert plot to base64 string
    img_io = io.BytesIO()
    plt.savefig(img_io, format='png')
    img_io.seek(0)
    return base64.b64encode(img_io.getvalue()).decode()

@app.route("/")
def home():
    return "Go to /run_notebook to view the results"

@app.route("/run_notebook")
def run_notebook():
    file_path = os.path.join(LOG_DIR, LOG_FILE)
    print(f"Reading data from: {file_path}")  # Debugging statement

    df = extract_data(file_path)
    if df is None or df.empty:
        print("No data found or file not available.")  # Debugging statement
        return "No data found or file not available."

    # Generate charts
    pie_chart = generate_pie_chart(df)
    bar_chart = generate_bar_chart(df)

    # Convert DataFrame to HTML table
    table_html = df.to_html(classes="table table-striped", index=False)

    # Render results in HTML
    html_template = f"""
    <html>
    <head>
        <title>Notebook Output</title>
        <style>
            body {{ font-family: Arial, sans-serif; text-align: center; }}
            .container {{ max-width: 900px; margin: auto; }}
            img {{ max-width: 100%; height: auto; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid black; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
        </style>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.0/socket.io.js"></script>
        <script type="text/javascript">
            var socket = io();
            socket.on('update_charts', function(data) {{
                document.getElementById('pie_chart').src = 'data:image/png;base64,' + data.pie_chart;
                document.getElementById('bar_chart').src = 'data:image/png;base64,' + data.bar_chart;
            }});
        </script>
    </head>
    <body>
        <div class="container">
            <h1>Executed Notebook Output</h1>
            <h2>Extracted Data</h2>
            {table_html}
            <h2>Pie Chart</h2>
            <img id="pie_chart" src="data:image/png;base64,{pie_chart}" alt="Pie Chart">
            <h2>Bar Chart</h2>
            <img id="bar_chart" src="data:image/png;base64,{bar_chart}" alt="Bar Chart">
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template)

def update_charts():
    file_path = os.path.join(LOG_DIR, LOG_FILE)
    df = extract_data(file_path)
    if df is not None and not df.empty:
        pie_chart = generate_pie_chart(df)
        bar_chart = generate_bar_chart(df)
        socketio.emit('update_charts', {'pie_chart': pie_chart, 'bar_chart': bar_chart})

def monitor_logs():
    """
    Continuously reads the Suricata eve.log file and sends parsed entries to the dashboard.
    """
    file_path = os.path.join(LOG_DIR, LOG_FILE)
    with open(file_path, 'r') as file:
        file.seek(0, os.SEEK_END)  # Move to the end of the file
        while True:
            line = file.readline()
            if not line:
                time.sleep(1)  # Sleep briefly to avoid busy-waiting
                continue

            # Process the new log line
            try:
                log_entry = json.loads(line.strip())
                # Here you can process the log_entry if needed
                print(f"New log entry: {log_entry}")  # Debugging statement
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON in line: {line.strip()}")  # Debugging statement
                print(f"Error: {e}")

            # Update charts with new data
            update_charts()

if __name__ == "__main__":
    socketio.run(app, debug=True)
    monitor_logs()
