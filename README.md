# Food Waste Lab — AI Food Waste Web

เว็บจัดการอาหารเหลือในโรงเรียน + สแกนถาดด้วย AI (มีโมเดลพร้อมใช้)

Clone แล้วรันบนเครื่องได้เลย ไม่ต้องเทรนโมเดลเพิ่ม

## ความต้องการ

- Python 3.10+ (แนะนำ 3.12)
- Windows: ดับเบิลคลิก `run-local.bat` ได้เลย
- หรือใช้ Docker (ถ้ามี) — `docker compose up --build`

## รันแบบเร็ว (Windows)

```bat
git clone https://github.com/cappu-kab/AI_food_waste.git
cd AI_food_waste
run-local.bat
```

ครั้งแรกจะสร้าง `.venv` และติดตั้งแพ็กเกจให้เอง (อาจใช้เวลาหลายนาที)

## รันด้วยคำสั่ง

```bat
python -m venv .venv
.\.venv\Scripts\pip.exe install -r requirements.txt
.\.venv\Scripts\pip.exe install ultralytics opencv-python-headless
.\.venv\Scripts\python.exe webapp.py --model models\best.pt --device cpu --port 8899
```

บน macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt ultralytics opencv-python-headless
python webapp.py --model models/best.pt --device cpu --port 8899
```

## เปิดเว็บ

| ลิงก์ | หน้า |
|---|---|
| http://localhost:8899/site/ | หน้าแรก Food Waste Lab |
| http://localhost:8899/ | สแกนถาดด้วย AI |
| http://localhost:8899/?demo=1 | ลองตัวอย่างโดยไม่ต้องมีรูป |
| http://localhost:8899/site/project-brief.html | สรุปโปรเจกต์สำหรับสไลด์/พรีเซนต์ |

## มีอะไรในนี้

- `models/best.pt` — โมเดล YOLOv8s-seg ที่เทรนแล้ว (5 class)
- `webapp.py` — เซิร์ฟเวอร์ Flask
- `AI_food_waste-main/` — เว็บ Lab (หน้าแรก / เรียนรู้ / รายงาน)
- `templates/` — หน้าสแกนถาด
- `samples/demo/` — รูปตัวอย่าง
- `project-brief.html` — เอกสารสรุปสำหรับพรีเซนต์
- `run-local.bat` / `RUN_LOCAL.md` — คู่มือรันบนเครื่อง

## หมายเหตุ

- ค่าเริ่มต้นรันบน CPU
- ตั้งขนาดถาดจริงใน `.env` จาก `.env.example` ถ้าถาดไม่ใช่เส้นผ่านศูนย์กลาง 35 ซม.
- อาหารเหลือดิบยังไม่ใช่ปุ๋ยหมักสำเร็จ
