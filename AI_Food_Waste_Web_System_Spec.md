# AI Food Waste Management & Agricultural Learning Center

## 1. Project Concept

เว็บไซต์นี้เป็นระบบ **AI + Data Analysis + Agricultural Decision Support + Public Learning Center**

เป้าหมายมี 2 ส่วน:

1. **ระบบภายในโรงเรียน**: เก็บและวิเคราะห์ Food Waste จริงของโรงเรียน ลดการเกิดขยะอาหาร และแนะนำการนำ Food Waste ไปใช้ด้านการเกษตร
2. **ศูนย์การเรียนรู้สาธารณะ**: เปิดเผยข้อมูลแบบค่าเฉลี่ย/ข้อมูลรวมและองค์ความรู้ให้บุคคลทั่วไปศึกษา โดยไม่เปิดเผยข้อมูลเฉพาะของโรงเรียน

Flow หลัก:

```text
Kitchen Data
    ↓
AI Food Detection / Weight
    ↓
Food Waste by Category (kg)
    ↓
Validation & Pre-processing
    ↓
┌───────────────┬──────────────────┬────────────────────┐
│ Route 1       │ Route 2          │ Route 3            │
│ Reduce Waste  │ Agricultural Use │ Target Optimization │
└───────────────┴──────────────────┴────────────────────┘
    ↓
Recommendation / Report
    ↓
School Dashboard
    ↓
Aggregate Data → Public Learning Center
```

---

# 2. User Roles

## Public User — ไม่ต้อง Login

ดูได้:
- Home
- Public Food Waste Dashboard
- ค่าเฉลี่ย/ข้อมูล Aggregate
- Learning Center
- How It Works
- Formula Library
- Environmental Information

ดูไม่ได้:
- ข้อมูลรายวันของโรงเรียน
- เมนูของโรงเรียน
- ข้อมูลโรงครัว
- Raw AI data
- Recommendation เฉพาะโรงเรียน

## Kitchen Staff — Login

ทำได้:
- กรอกข้อมูลอาหารที่ผลิต
- กรอกจำนวนผู้กิน
- กรอก Food Waste
- กรอกอาหารที่ผลิตแต่ไม่ได้เสิร์ฟ
- กรอก Free Liquid
- ดูคำแนะนำด้านการลด Food Waste

## School Admin — Login

ทำได้ทั้งหมดของ Kitchen Staff และ:
- ดู Dashboard โรงเรียน
- ดูข้อมูลย้อนหลัง
- ดู Analytics
- ใช้ Route 1–3
- Export Report
- จัดการเมนู
- จัดการผู้ใช้โรงเรียน

## System Admin

- จัดการทุกโรงเรียน
- จัดการ Material Database
- จัดการ Formula/Threshold
- จัดการ Learning Center
- ตรวจสอบ Model/Data Quality

---

# 3. Site Map

## Public

```text
Home
├── Food Waste Data
│   ├── Overview
│   ├── Composition
│   ├── Trends
│   └── Environmental Impact
├── Learning Center
│   ├── Food Waste
│   ├── AI & Food Waste
│   ├── Compost
│   ├── C:N Ratio
│   ├── Moisture
│   ├── Food Waste → Agriculture
│   └── Formula Library
├── How It Works
└── Login
```

## Private School Area

```text
Dashboard
├── Kitchen Input
├── Food Waste Analysis
├── Route 1: Source Reduction
├── Route 2: Agricultural Use
├── Route 3: Target & Optimization
├── Reports
└── Settings
```

---

# 4. Home Page

## Hero

ข้อความหลัก:

> เปลี่ยน Food Waste ให้เป็นข้อมูล เพื่อสร้างการเปลี่ยนแปลง

คำอธิบาย:
AI ช่วยวิเคราะห์อาหารที่เหลือจากโรงอาหาร ลดการสูญเสียตั้งแต่ต้นทาง และค้นหาวิธีนำ Food Waste ไปใช้ประโยชน์ด้านการเกษตร

Buttons:
- `Explore Learning Center`
- `School Login`

## Public Statistics

แสดงเฉพาะ Aggregate:

```text
Food Waste Analyzed
XXX kg

Participating Schools
XX

Average Waste / Person
XX g

Food Waste Diverted
XX kg
```

ต้องระบุว่าเป็นข้อมูลรวม/ค่าเฉลี่ย

---

# 5. Public Food Waste Dashboard

จุดประสงค์คือให้คนนอกเข้ามาศึกษาได้

แสดง:

- Average Food Waste/person/day
- Average Food Waste by Category
- Composition
- Trend
- Aggregate Statistics

Charts:
- Donut → Food Waste Composition
- Line → Average Waste Trend
- Bar → Waste by Category

ตัวอย่าง:

```text
Average Food Waste

Rice       38%
Vegetable  30%
Fruit       9%
Protein     8%
Other      15%
```

ห้ามแสดงข้อมูลที่ระบุโรงเรียนได้โดยตรง

---

# 6. Learning Center

ต้องเป็นส่วนหนึ่งของเว็บ ไม่ใช่แค่หน้า About

หัวข้อ:

### Food Waste
- Food Waste คืออะไร
- เกิดจากอะไร
- Source Reduction

### AI & Computer Vision
```text
Camera
 ↓
Detection / Classification
 ↓
Food Category
 ↓
Estimated Quantity
 ↓
kg Dataset
```

### Compost
- Compost คืออะไร
- Carbon
- Nitrogen
- C:N
- Moisture
- Aeration

### Food Waste → Agriculture

```text
Food Waste
 ↓
Analyze
 ↓
Adjust
 ↓
Compost
 ↓
Test Finished Compost
 ↓
Use as Soil Amendment
```

### Formula Library

แต่ละสูตรต้องแสดง:
- ชื่อ
- Formula
- Input
- Unit
- Output
- ใช้ทำอะไร
- ตัวอย่าง
- Source

---

# 7. Login / Privacy

หลัง Login ต้องผูกกับ `school_id`

User เห็นเฉพาะข้อมูลโรงเรียนของตนเอง

```text
School: ABC School
```

ข้อมูล Public และ Private ต้องแยกกันตั้งแต่ Database/Backend ไม่ใช่แค่ซ่อนปุ่มบน Frontend

---

# 8. School Dashboard

แสดง KPI:

```text
Today's Food Waste
42.5 kg

Waste / Person
85 g

Waste Rate
18.4%

vs Last Week
↓ 12%
```

แสดง:
- Trend 7/30 วัน
- Top wasted foods
- Today's composition
- Quick Actions

Buttons:

```text
[ Analyze Today ]
[ Reduce Waste ]
[ Agricultural Use ]
[ Create Target ]
```

---

# 9. Kitchen Input Page

## Basic Information

```text
Date
Menu
Number of Diners
```

## Prepared Food

```text
Rice             ___ kg
Vegetable        ___ kg
Fruit            ___ kg
Protein          ___ kg
Other            ___ kg
```

## Unserved Food

อาหารที่ผลิตแล้วแต่ไม่ได้เสิร์ฟ:

```text
Unserved Rice       ___ kg
Unserved Vegetable  ___ kg
...
```

**ต้องแยก Unserved Food กับ Plate Waste**

## Plate Waste

```text
Rice Waste       ___ kg
Vegetable Waste  ___ kg
Fruit Waste      ___ kg
Protein Waste    ___ kg
Other Waste      ___ kg
```

## Free Liquid

```text
Soup / Gravy      ___ L
```

## Contamination

```text
Plastic           ___ kg
Other             ___ kg
```

ก่อน Save ต้องตรวจ Mass Balance

```text
Σ category weight ≈ Total weight
```

ถ้าไม่ตรงเกิน tolerance → แจ้ง Error/Warning

---

# 10. Processing Pipeline

```text
Input
 ↓
Unit Normalization
 ↓
Validation
 ↓
Separate:
 ├── Food Waste Solid
 ├── Free Liquid
 └── Contamination
 ↓
Composition
 ↓
Material Property Lookup
 ↓
Dry Matter
 ↓
Carbon
 ↓
Nitrogen
 ↓
C:N
 ↓
Moisture
 ↓
Decision Engine
 ↓
Recommendation
```

---

# 11. Route 1 — Source Reduction

## เป้าหมาย

ลด Food Waste ก่อนที่จะเกิดขึ้น

## Input

- Prepared Food kg
- Unserved Food kg
- Plate Waste kg
- Diners
- Portion
- Menu
- Historical Data

## Process

### Waste Rate

```text
Waste Rate =
Waste / Prepared × 100
```

### Consumed

```text
Consumed =
Prepared - Waste
```

### Consumption per Person

```text
Consumption/person =
Consumed / Diners
```

### Waste per Person

```text
Waste/person =
Waste / Diners
```

### Forecast

ใช้ Historical Consumption เพื่อประมาณการบริโภคครั้งต่อไป เช่น Weighted Moving Average:

```text
Forecast =
Σ(w × X) / Σw
```

### Recommended Production

```text
Recommended Production =
Expected Diners
× Forecast Consumption/person
× Safety Buffer
```

### Reduction

```text
Reduction =
Current Production
- Recommended Production
```

### Portion

```text
Recommended Portion =
Recommended Production / Expected Diners
```

## Output

```text
Rice

Current Production     100 kg
Waste                  20 kg
Waste Rate             20%
Waste / Person         40 g

Recommended Production 82 kg
Potential Reduction    18 kg
Suggested Portion      164 g/person
```

คำว่า Suggested/Estimated ควรใช้แทนการสั่งให้โรงครัวลดทันที

---

# 12. Route 2 — Agricultural Use

## เป้าหมาย

ดูว่า Food Waste ที่มีอยู่จริงในวันนั้นเหมาะนำไปใช้ด้านเกษตรอย่างไร

## Input

- Food Waste kg/category
- Free Liquid
- Contamination
- Moisture
- Carbon
- Nitrogen
- Material Properties

## Composition

```text
Share =
Wi / Wtotal × 100
```

## Dry Matter

```text
DM =
W × (1 - Moisture)
```

## Water in Food

```text
Water =
W - DM
```

## Carbon Mass

```text
C =
DM × Carbon Fraction
```

## Nitrogen Mass

```text
N =
DM × Nitrogen Fraction
```

## Total Carbon

```text
Ctotal = ΣC
```

## Total Nitrogen

```text
Ntotal = ΣN
```

## C:N

```text
C:N =
Ctotal / Ntotal
```

## Moisture

```text
Mmix =
Σ(W × M) / ΣW
```

---

# 13. Route 2 Decision Engine

ไม่ควรใช้คะแนนที่สร้างขึ้นเองแบบไม่มีหลักฐาน

ใช้ Rule/Constraint ที่อธิบายได้

ตัวอย่าง:

```text
Contamination สูง
→ SORT FIRST

Free Liquid สูง
→ SEPARATE LIQUID

C:N / Moisture ไม่เหมาะ
→ ADJUST BEFORE COMPOST

ผ่านเงื่อนไขพื้นฐาน
→ COMPOST CANDIDATE

Plant-based fraction สูงและเงื่อนไขเหมาะ
→ VERMICOMPOST CANDIDATE AFTER PRE-TREATMENT
```

Output ต้องมี:

```text
Recommendation
Why
Required Preparation
Current C:N
Current Moisture
Data Quality
```

---

# 14. Route 3 — Target & Optimization

หน้าเว็บใช้แนวคิด:

> ฉันอยากทำ...

ตัวอย่าง:

```text
[ Aerobic Compost ]
[ Vermicompost Preparation ]
[ Soil Amendment Preparation ]
```

สำหรับ MVP ให้ **Aerobic Compost** เป็น Target หลักก่อน

## Target Example

```text
C:N       25–30 : 1
Moisture  50–60%
Contamination  acceptable
```

ค่า Target ต้องมี Source และ Admin สามารถปรับได้

---

# 15. Route 3 Input

- Current Food Waste
- Current C
- Current N
- Current C:N
- Current Moisture
- Available Materials
- Material C
- Material N
- Material Moisture
- Available kg
- Price/kg

วัสดุอาจเป็น:
- ใบไม้แห้ง
- ฟาง
- แกลบ
- กิ่งไม้บด
- ขี้เลื่อยที่เหมาะสม

---

# 16. Route 3 Formulas

### Carbon Added

```text
Cadded =
X × (1-M) × C
```

### Nitrogen Added

```text
Nadded =
X × (1-M) × N
```

### C:N After Adjustment

```text
CNnew =
(Cfood + ΣCadded)
/
(Nfood + ΣNadded)
```

### Moisture After Adjustment

```text
Mnew =
(Wfood×Mfood + Σ(X×M))
/
(Wfood + ΣX)
```

### Cost

```text
Cost =
Σ(X × Price/kg)
```

---

# 17. Optimization Algorithm

อย่าให้ LLM คิดตัวเลขเอง

ใช้ Formula Engine + Grid Search/Constraint Search

ตัวอย่าง:

```text
ลองใบไม้แห้ง 0–30 kg
Step = 0.5 kg

ลองแกลบ 0–20 kg
Step = 0.5 kg
```

ทุก combination:

```text
Calculate C:N
Calculate Moisture
Check Constraints
Calculate Cost
```

เก็บเฉพาะสูตรที่ผ่าน:

```text
25 ≤ C:N ≤ 30
50% ≤ Moisture ≤ 60%
Contamination acceptable
Available material sufficient
```

ถ้าผ่านหลายสูตร:

1. ต้นทุนต่ำสุด
2. ใช้วัสดุน้อยที่สุด
3. สูตรที่ทำได้ง่ายกว่า

---

# 18. Route 3 Output

```text
TARGET
Aerobic Compost

CURRENT
C:N        17:1
Moisture   74%

RECOMMENDED
Dry Leaves    +15 kg
Rice Husk      +4 kg
Free Liquid    Separate

AFTER ADJUSTMENT
C:N        27.8:1
Moisture   57%

Estimated Cost
18 THB

STATUS
✓ Target Range Reached
```

ต้องใช้คำว่า Estimated/Predicted เพราะเป็นค่าคำนวณก่อนลงมือจริง

---

# 19. Finished Compost

Raw Food Waste ≠ Finished Compost

หลังหมักเสร็จจึงเข้าสู่ขั้น:

```text
Finished Compost
 ↓
Testing
 ↓
Soil / Crop Information
 ↓
Application Recommendation
```

ข้อมูลที่ควรตรวจ:
- pH
- EC
- C:N
- Organic Matter
- N
- P
- K
- Moisture
- Maturity
- Safety/contamination parameters ตามบริบท

จึงค่อยแนะนำการใช้ เช่น:
- แปลงผัก
- ไม้ดอก
- ไม้ประดับ
- ต้นไม้
- สนามหญ้า
- Soil Amendment
- Potting Mix

ห้ามสรุปจาก Raw Food Waste เพียงอย่างเดียวว่าเหมาะกับพืชชนิดใด

---

# 20. Reports

## Daily

- Total Food Waste
- Waste/person
- Composition
- Unserved Food
- Plate Waste
- Free Liquid
- Recommendation

## Weekly

- Total Waste
- Average Waste/person
- Top wasted foods
- Trend
- Reduction Recommendation

## Monthly

- Total Food Waste
- Waste Reduction %
- Top problematic menus
- Agricultural diversion
- Estimated recovered organic material

---

# 21. Public Environmental Dashboard

แสดงข้อมูล Aggregate เท่านั้น

ตัวอย่าง:

```text
Food Waste Analyzed
1,250 kg

Food Waste Diverted
800 kg

Average Waste / Person
XX g
```

แยกชัดเจนระหว่าง:
- Measured
- Estimated
- Modeled

ห้ามทำให้ค่าประมาณดูเหมือนค่าที่วัดจริง

---

# 22. Public Data Aggregation

```text
School A ─┐
School B ─┼→ Aggregation → Average/Median/Distribution
School C ─┘                         ↓
                              Public Dashboard
```

Public ไม่ควรเห็น:
- ชื่อโรงเรียน
- Raw data
- Menu เฉพาะโรงเรียน
- Daily school-specific statistics
- Kitchen information
- School-specific recommendation

---

# 23. AI vs Formula Engine vs LLM

## Computer Vision / AI

รับผิดชอบ:
- Detection
- Classification
- Food Category
- Quantity Estimation ตาม pipeline

## Formula Engine

รับผิดชอบ:
- Waste Rate
- Consumption
- Composition
- Dry Matter
- Carbon
- Nitrogen
- C:N
- Moisture
- Optimization
- Cost

## Rule / Decision Engine

รับผิดชอบ:
- Ready
- Adjust
- Separate Liquid
- Sort
- Compost Candidate
- Vermicompost Candidate

## LLM

ใช้สำหรับ:
- อธิบายผล
- สรุป Report
- ตอบคำถาม Learning Center
- อธิบายเหตุผลของ Recommendation

**LLM ไม่ควรเป็น Calculator หลัก**

---

# 24. Recommendation Card

ทุก Recommendation ควรมี:

```text
RECOMMENDATION
Compost after adjustment

WHY
Moisture สูง และ C:N ต่ำ

ACTION
Add dry carbon-rich material
Separate free liquid

EXPECTED RESULT
C:N ≈ XX
Moisture ≈ XX%

DATA QUALITY
Estimated from material database
```

กด `How was this calculated?` เพื่อดูสูตรและ Input

---

# 25. Data Quality

ทุกค่าต้องมี Source Type:

```text
Measured
AI Estimated
User Input
Database Reference
Calculated
```

ตัวอย่าง:

```text
Moisture: 74%
Source: Database Reference
Status: Estimated
```

ถ้ามี Lab:

```text
Moisture: 71.8%
Source: Laboratory Test
Status: Measured
```

---

# 26. Error Handling

ถ้าข้อมูลไม่พอ:

```text
INSUFFICIENT DATA

ต้องการ:
• Prepared Food
• Food Waste
• Number of Diners
```

ถ้าความมั่นใจต่ำ:

```text
LOW CONFIDENCE

ค่าคุณสมบัติวัตถุดิบมาจาก Reference Database
แนะนำตรวจตัวอย่างจริงเพื่อเพิ่มความแม่นยำ
```

---

# 27. Formula Library

## Source Reduction

```text
Waste Rate = Waste / Prepared × 100
Consumed = Prepared - Waste
Consumption/person = Consumed / Diners
Waste/person = Waste / Diners
Forecast = Σ(wX) / Σw
Recommended Production = Diners × Forecast × Buffer
Reduction = Current Production - Recommended Production
Portion = Recommended Production / Diners
```

## Food Waste Analysis

```text
Share = Wi / Wtotal × 100
DM = W × (1-M)
Water = W - DM
C = DM × Cfraction
N = DM × Nfraction
Ctotal = ΣC
Ntotal = ΣN
C:N = Ctotal / Ntotal
Mmix = Σ(W×M) / ΣW
```

## Optimization

```text
Cadded = X × (1-M) × C
Nadded = X × (1-M) × N
CNnew = (Cfood + ΣCadded) / (Nfood + ΣNadded)
Mnew = (Wfood×Mfood + ΣX×M) / (Wfood + ΣX)
Cost = Σ(X × Price)
```

## Evaluation

```text
Waste Reduction % =
(Baseline Waste - New Waste)
/
Baseline Waste × 100
```

---

# 28. Database Structure

## School

```text
school_id
school_name
location_general
created_at
```

## User

```text
user_id
school_id
role
email
```

## Meal

```text
meal_id
school_id
date
menu
diners
```

## Prepared Food

```text
meal_id
category
prepared_kg
unserved_kg
```

## Food Waste

```text
meal_id
category
waste_kg
free_liquid_kg
contamination_kg
```

## Material Property

```text
material_id
name
moisture
carbon
nitrogen
price_per_kg
available_kg
source
source_date
```

## Recommendation

```text
recommendation_id
school_id
date
route
target
input_snapshot
result
reason
status
```

---

# 29. UX Structure

ระบบควรมี 2 ระดับ

## Simple Mode

สำหรับโรงครัว:

```text
กรอกข้อมูล
 ↓
ระบบวิเคราะห์
 ↓
เห็นคำแนะนำ
```

ไม่ต้องแสดงสูตรเต็ม

## Learning / Expert Mode

สำหรับนักเรียน/อาจารย์/บุคคลทั่วไป:

```text
Input
 ↓
Formula
 ↓
Calculation
 ↓
Result
 ↓
Explanation
 ↓
Source
```

---

# 30. MVP ภายใน 2 เดือน

## Phase 1 — Foundation
- UI
- Login
- Roles
- Database
- Public/Private separation

## Phase 2 — Data Input
- Kitchen Input
- Prepared Food
- Unserved Food
- Plate Waste
- Free Liquid
- Contamination

## Phase 3 — Formula Engine
- Waste Rate
- Consumption
- Composition
- Dry Matter
- C/N
- Moisture

## Phase 4 — Route 1
- Historical Data
- Trend
- Forecast
- Production Recommendation

## Phase 5 — Route 2
- Decision Rules
- Compost Recommendation
- Pre-treatment Recommendation

## Phase 6 — Route 3
- Target Selection
- Material Database
- Constraint Search
- Recommended Mixture

## Phase 7 — Learning Center
- Learning Pages
- Formula Library
- Public Statistics
- Methodology

## Phase 8 — Validation
- Compare predicted vs measured
- Test calculations
- Test recommendations
- Privacy testing
- User testing

---

# 31. Required MVP Pages

## Public
1. Home
2. Public Food Waste Dashboard
3. Learning Center
4. How It Works
5. Formula Library
6. Login

## Private
7. School Dashboard
8. Kitchen Input
9. Food Waste Analysis
10. Route 1 — Source Reduction
11. Route 2 — Agricultural Use
12. Route 3 — Target & Optimization
13. Reports
14. Settings

---

# 32. Design Direction

Style:
- Modern
- Clean
- Environmental
- Scientific
- Trustworthy
- Easy to understand

ใช้:
- Cards
- Charts
- KPI
- Progress/Step indicators
- Status badges
- Clear CTA

หน้า Dashboard ไม่ควรเต็มไปด้วยสูตร

สูตรควรอยู่ใน:
- Learning Center
- Formula Library
- `How was this calculated?`

แนวคิดสำคัญ:

> คนทั่วไปเข้าใจได้ แต่คนที่ต้องการตรวจสอบสามารถเปิดดูวิธีคำนวณได้

---

# 33. Core Product Value

ระบบไม่ได้เป็นเพียง:

> AI ตรวจจับ Food Waste

แต่เป็น:

> **AI → Data → Mathematical Analysis → Decision Support → Agricultural Utilization → Learning**

และแก้ปัญหา 2 ฝั่ง:

### ต้นเหตุ

```text
วิเคราะห์อะไรเหลือ
→ ดูแนวโน้ม
→ ปรับการผลิต/Portion
→ ลด Food Waste
```

### ปลายเหตุ

```text
Food Waste ที่เกิดขึ้น
→ วิเคราะห์ Composition
→ C:N / Moisture
→ ดูความเหมาะสม
→ ปรับสูตร
→ Compost / Agricultural Use
```

พร้อมเปิดองค์ความรู้บางส่วนเป็น Public Learning Center เพื่อให้บุคคลภายนอกศึกษาและต่อยอดได้
