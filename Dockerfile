# Use Python 3.11 on Debian Bookworm
FROM python:3.11-slim-bookworm

# Prevent Python from writing pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install System Dependencies
# We include libraries for OpenCV, compilation tools, and multimedia
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    pkg-config \
    libopencv-dev \
    libatlas-base-dev \
    libjpeg-dev \
    libpng-dev \
    libwebp-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# --- HAILO SIMULATION SETUP ---
# Note: Actual HailoRT requires the physical device and drivers mounted.
# We set up the environment variables expected by the Hailo SDK.
ENV HAILO_MODEL_ZOO_PATH=/usr/share/hailo-models
ENV HAILO_EXAMPLES_PATH=/usr/share/hailo-examples

# Create placeholder directories for models
RUN mkdir -p /usr/share/hailo-models && \
    mkdir -p /usr/share/hailo-examples

# Copy requirements 
COPY requirements.txt .

# Install dependencies 
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt
    
# Copy the entire application
COPY . .

# Expose the Flask port
EXPOSE 5000

# Create a non-root user for security (optional but recommended)
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Healthcheck to verify the web server is up
HEALTHCHECK --interval=30s --timeout=5s \
  CMD curl -f http://localhost:5000/ || exit 1

# Default command runs the new Orchestrator
CMD ["python", "main.py"]