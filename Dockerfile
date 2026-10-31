# Use an official Python runtime as a parent image
FROM python:3.14-slim

# Set the working directory inside the container
WORKDIR /app

# Prevent Python from writing pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project code into the container
COPY . .

# Set PYTHONPATH to ensure correct module imports
ENV PYTHONPATH=/app

# Default command to run tests or application
CMD ["pytest", "-v"]