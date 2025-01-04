from flask import Flask, jsonify, request, Response, render_template_string
import random
import logging
import time
import os
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

# Basic setup for logging
logging.basicConfig(level=logging.INFO)

# Prometheus metrics
REQUEST_COUNT = Counter('app_requests_total', 'Total number of requests', ['method', 'endpoint', 'http_status'])
REQUEST_LATENCY = Histogram('app_request_latency_seconds', 'Latency of HTTP requests in seconds', ['endpoint'])
ERROR_COUNT = Counter('app_errors_total', 'Total number of errors', ['endpoint', 'error_type'])

# Middleware for metrics
@app.before_request
def start_timer():
    request.start_time = time.time()

@app.after_request
def record_metrics(response):
    request_latency = time.time() - request.start_time
    REQUEST_LATENCY.labels(request.path).observe(request_latency)
    REQUEST_COUNT.labels(request.method, request.path, response.status_code).inc()
    return response

@app.route('/metrics', methods=['GET'])
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

# Health Check Endpoint
@app.route('/health', methods=['GET'])
def health_check():
    app.logger.info("Health check requested")
    return jsonify({"status": "healthy"}), 200

# Info Endpoint - Returns a visually appealing HTML page
@app.route('/info', methods=['GET'])
def info():
    app.logger.info("Info endpoint accessed")
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Application Info</title>
        <style>
            body { font-family: Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 20px; }
            .container { background-color: #fff; padding: 20px; border-radius: 5px; max-width: 600px; margin: auto; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            h1 { text-align: center; color: #333; }
            p { font-size: 1.1em; color: #666; }
            .footer { text-align: center; margin-top: 20px; font-size: 0.9em; color: #999; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Application Information</h1>
            <p><strong>App:</strong> Sample Dockerized App</p>
            <p><strong>Version:</strong> 1.0.0</p>
            <p><strong>Description:</strong> A versatile app for testing with multiple endpoints.</p>
            <div class="footer">
                &copy; 2024 Prepare.sh
            </div>
        </div>
    </body>
    </html>
    """
    return Response(html_content, mimetype='text/html'), 200

# Data Endpoint - Reads content from a specified file within a safe directory
@app.route('/data', methods=['POST'])
def data():
    app.logger.info("Data endpoint accessed")
    data = request.get_json()
    
    if not data or 'file_path' not in data:
        app.logger.error("Invalid input received for /data")
        ERROR_COUNT.labels('/data', 'InvalidInput').inc()
        return jsonify({"error": "Invalid input, 'file_path' required"}), 400
    
    file_path = data['file_path']
    
    # Define a safe base directory
    base_dir = '/tmp/'
    
    # Resolve the absolute path
    safe_path = os.path.abspath(os.path.join(base_dir, file_path))
    
    # Ensure the resolved path starts with the base directory to prevent path traversal
    if not safe_path.startswith(os.path.abspath(base_dir)):
        app.logger.warning(f"Attempted unauthorized access to {file_path}")
        ERROR_COUNT.labels('/data', 'UnauthorizedAccess').inc()
        return jsonify({"error": "Unauthorized file path"}), 403
    
    if not os.path.isfile(safe_path):
        app.logger.error(f"File not found: {safe_path}")
        ERROR_COUNT.labels('/data', 'FileNotFound').inc()
        return jsonify({"error": "File not found"}), 404
    
    try:
        with open(safe_path, 'r') as file:
            content = file.read()
        return jsonify({"file_content": content}), 200
    except Exception as e:
        app.logger.error(f"Error reading file {safe_path}: {str(e)}")
        ERROR_COUNT.labels('/data', 'FileReadError').inc()
        return jsonify({"error": "Error reading file"}), 500

# Error Endpoint (50% chance of error)
@app.route('/error', methods=['GET'])
def error():
    if random.choice([True, False]):
        app.logger.error("Random error triggered!")
        ERROR_COUNT.labels('/error', 'RandomError').inc()
        return jsonify({"error": "A random error occurred!"}), 500
    else:
        return jsonify({"status": "success"}), 200

# Custom Endpoint (Handles POST requests and errors on certain values)
@app.route('/compute', methods=['POST'])
def compute():
    data = request.get_json()
    if not data or 'number' not in data:
        app.logger.error("Invalid input received for /compute")
        ERROR_COUNT.labels('/compute', 'InvalidInput').inc()
        return jsonify({"error": "Invalid input, 'number' required"}), 400
    if not isinstance(data['number'], (int, float)):
        app.logger.error("Non-numeric input received for /compute")
        ERROR_COUNT.labels('/compute', 'NonNumericInput').inc()
        return jsonify({"error": "'number' must be numeric"}), 400
    if data['number'] < 0:
        app.logger.warning("Negative number encountered in /compute")
        ERROR_COUNT.labels('/compute', 'NegativeNumber').inc()
        return jsonify({"error": "Negative numbers are not allowed"}), 400
    result = data['number'] * 2
    return jsonify({"result": result}), 200

if __name__ == '__main__':
    # Ensure the base data directory exists
    os.makedirs('/app/data/', exist_ok=True)
    app.run(host='0.0.0.0', port=8080)