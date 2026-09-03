# Free-tier friendly: ONNX Runtime only (no PyTorch). Real weights: models/best.onnx
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    onnxruntime opencv-python-headless

ENV YOLO_CONFIG_DIR=/tmp \
    MPLCONFIGDIR=/tmp/matplotlib \
    HOME=/tmp \
    PYTHONUNBUFFERED=1 \
    USER=tray \
    MODEL_RUNTIME=onnx \
    MODEL_PATH=models/best.onnx \
    DEVICE=cpu \
    CONF_THRESHOLD=0.25 \
    SURE_CONF=0.60 \
    TRAY_CROP=true \
    INFER_IMGSZ=320 \
    INFER_MAX_SIDE=720 \
    DEMO_LIMIT=1 \
    FLASK_THREADED=0

COPY . .
EXPOSE 8899
CMD ["sh", "-c", "python webapp.py --model models/best.onnx --device cpu --host 0.0.0.0 --port ${PORT:-8899}"]
