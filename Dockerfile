# Lean CPU image for local Docker, Hugging Face, and Render free tier.
# Uses the project's trained YOLOv8s-seg weights at models/best.pt
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    ultralytics opencv-python-headless

ENV YOLO_CONFIG_DIR=/tmp \
    MPLCONFIGDIR=/tmp/matplotlib \
    HOME=/tmp \
    PYTHONUNBUFFERED=1 \
    USER=tray \
    MODEL_PATH=models/best.pt \
    DEVICE=cpu \
    CONF_THRESHOLD=0.25 \
    SURE_CONF=0.60 \
    TRAY_CROP=true

COPY . .
EXPOSE 8899
# Render sets $PORT; local/docker-compose default to 8899
CMD ["sh", "-c", "python webapp.py --model models/best.pt --device cpu --host 0.0.0.0 --port ${PORT:-8899}"]
