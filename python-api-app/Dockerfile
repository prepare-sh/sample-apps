# Use a lightweight Python image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy files to the container
COPY app.py /app

# Install required system packages including curl and wget
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set permissions for the /app directory and create the /app/data directory
RUN mkdir -p /app/data && chmod -R 777 /app

# Install Flask and prometheus_client
RUN pip install flask prometheus_client

# Expose the application on port 8080
EXPOSE 8080

# Run the app
CMD ["python", "app.py"]