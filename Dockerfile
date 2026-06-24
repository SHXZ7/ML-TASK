FROM python:3.11-slim

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install dependencies (no torch/transformers - using HF Inference API instead)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire workspace (including images, products.csv, outfits.csv, and backend)
COPY . .

# Expose FastAPI port (HuggingFace Spaces routes to app_port: 8000 as set in README.md)
EXPOSE 8000

# Set PYTHONPATH so the backend package is importable
ENV PYTHONPATH=/app

# Run FastAPI using uvicorn on port 8000
CMD uvicorn backend.main:app --host 0.0.0.0 --port 8000
