# รันบนเครื่องตัวเอง (ไม่ต้องใช้ Docker)

ต้องมี **Python 3.10+**

## วิธีเร็วสุด (Windows)

ดับเบิลคลิกไฟล์ `run-local.bat`

ครั้งแรกจะติดตั้งไลบรารีให้เอง อาจใช้เวลาหลายนาที

## วิธีรันด้วยคำสั่ง

```bat
cd tray-waste-web\tray-waste-web
python -m venv .venv
.\.venv\Scripts\pip.exe install flask ultralytics opencv-python-headless numpy
set MODEL_PATH=models\best.pt
.\.venv\Scripts\python.exe webapp.py --model models\best.pt --device cpu --port 8899
```

## เปิดเว็บ

| ลิงก์ | คืออะไร |
|---|---|
| http://localhost:8899/ | หน้าสแกนถาดอาหาร (มี AI) |
| http://localhost:8899/site/ | เว็บ Food Waste Lab (หน้าแรก / เรียนรู้ / เข้าสู่ระบบ) |
| http://localhost:8899/?demo=1 | ลองดูตัวอย่างโดยไม่ต้องมีรูป |

## หมายเหตุ

- รอบแรกที่โหลดโมเดลอาจช้าหน่อย (CPU)
- ถ้าอยากใช้ Docker แทน ดู `README.md` (ต้องติดตั้ง Docker Desktop ก่อน)
