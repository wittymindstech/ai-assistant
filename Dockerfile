FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

# Install system dependencies for pytesseract
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p data/pdfs data/images

# Expose FastAPI port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/queue')" || exit 1

# Run the FastAPI app
CMD ["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
