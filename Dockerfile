# Install system dependencies for Adafruit-DHT
RUN apt-get update && \
    apt-get install -y \
    python3-dev \
    gcc \
    g++ \
    libssl-dev \
    libffi-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy requirements.txt and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Adafruit-DHT with the --force-pi flag
RUN pip install --no-cache-dir Adafruit-DHT==1.4.0 --force-pi

# Copy the rest of the application code
COPY . .

# Command to run the app
CMD ["python", "app.py"]
