# ใช้ image ทางการของ Ultralytics ที่ฝัง PyTorch + YOLO ตรง version มาแล้ว
# GPU : ultralytics/ultralytics:latest
# CPU : ultralytics/ultralytics:latest-cpu  (ค่าเริ่มต้นของแพ็กเกจนี้ — รันได้ทุกเครื่อง)
ARG BASE_IMAGE=ultralytics/ultralytics:latest-cpu
FROM ${BASE_IMAGE}

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ชี้ config/cache ไปที่ /tmp กัน permission error ตอนรันด้วย uid ของ user บน host
ENV YOLO_CONFIG_DIR=/tmp \
    MPLCONFIGDIR=/tmp/matplotlib \
    HOME=/tmp \
    PYTHONUNBUFFERED=1
# uid ที่ map จาก host ไม่มีใน /etc/passwd ของ image → getpass.getuser() พังเป็น KeyError
ENV USER=tray

COPY . .
EXPOSE 8899
CMD ["python", "webapp.py", "--port", "8899"]
