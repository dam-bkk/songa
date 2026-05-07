FROM python:3.11-slim AS base
WORKDIR /app

# System deps pour OpenCV
RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Python deps (sans torch/torchvision pour image légère — optionnel en prod GPU)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Crée les dossiers nécessaires
RUN mkdir -p uploads output models sample_output

EXPOSE 8000
ENV PYTHONUNBUFFERED=1
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
