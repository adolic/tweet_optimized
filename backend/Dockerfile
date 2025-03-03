FROM python:3.11-slim

# Set up the app directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create a backend directory for proper imports
RUN mkdir -p /app/backend

# Copy requirements first for better caching
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application files into the backend directory
COPY . /app/backend/

# Set the Python path to find modules properly
ENV PYTHONPATH=/app

# Install the application in development mode
WORKDIR /app/backend
RUN pip install -e .

# Change back to app directory and run the application
WORKDIR /app
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]