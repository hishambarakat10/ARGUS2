import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
from flask import Flask, render_template_string

app = Flask(__name__)

# Function to extract data from JSON logs
def extract_data(file_path):
    try:
        data = {'timestamp': [], 'event_id': [], 'classification': []}
        with open(file_path, 'r') as file:
            json_data = []
            current_json = ""

            for line in file:
                if line.startswith("Received Log: {"):
                    current_json = line[len("Received Log: "):].strip()
                elif line.strip() == "}":
                    current_json += line.strip()
                    json_data.append(current_json)
                    current_json = ""
                elif current_json:
                    current_json += line.strip()

            for json_str in json_data:
                try:
                    log_data = json.loads(json_str)
                    data['timestamp'].append(log_data['timestamp'])
                    data['event_id'].append(log_data['event_id'])
                    data['classification'].append(log_data['classification'])
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON in line: {json_str}")
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
    file_path = r"C:\Users\hisha\Documents\CSCI_4385\message.json"  # Update this path if needed

    df = extract_data(file_path)
    if df is None or df.empty:
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
    </head>
    <body>
        <div class="container">
            <h1>Executed Notebook Output</h1>
            <h2>Extracted Data</h2>
            {table_html}
            <h2>Pie Chart</h2>
            <img src="data:image/png;base64,{pie_chart}" alt="Pie Chart">
            <h2>Bar Chart</h2>
            <img src="data:image/png;base64,{bar_chart}" alt="Bar Chart">
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template)

if __name__ == "__main__":
    app.run(debug=True)
