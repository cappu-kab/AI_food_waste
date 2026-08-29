# GROK BUILD PROMPT — AI Food Waste Web System (Local HTML Prototype)

Copy everything inside the fence below and paste it into Grok Build / Grok CLI.

---

```
Build a complete LOCAL multi-page static website prototype (no backend, no npm build step required) for an AI Food Waste Management & Agricultural Learning Center.

GOAL
Create a user-friendly, easy-to-use scientific + environmental web app that school kitchen staff and the public can understand immediately. Show important numbers first. Hide raw formulas behind “How was this calculated?” but IMPLEMENT EVERY FORMULA EXACTLY as specified — never invent numbers, never let LLM-style text replace the calculator.

OUTPUT
- A folder of plain HTML + CSS + vanilla JS files I can open locally.
- index.html as the entry point.
- Shared assets: css/styles.css, js/app.js, js/formulas.js, js/data.js
- One HTML file per page (see sitemap).
- A README.md explaining how to run: `python3 -m http.server 8080` from the project root, then open http://localhost:8080
- No frameworks, no bundler, no Tailwind CDN required if you prefer a single custom CSS file. You MAY use Chart.js from CDN for charts. Thai + English labels are OK; primary UI language is Thai.

DESIGN
- Modern, clean, environmental, scientific, trustworthy.
- Light mode first: off-white / cream background (#F7F4EE), forest green primary (#1B5E3B), earth brown accents, soft card shadows, 12–16px rounded cards.
- Sidebar on private pages; top nav on public pages.
- Large KPI numbers, muted labels, green/red trend arrows.
- Mobile-friendly but optimize for desktop 1280–1440px.
- Status badges: Measured / AI Estimated / User Input / Database Reference / Calculated.
- Always label Estimated vs Measured. Never present modeled values as measured.

ROLES (prototype with mock login)
- Public (no login): Home, Public Dashboard, Learning Center, How It Works, Formula Library, Login
- Kitchen Staff / School Admin after mock login (password can be anything, store role in localStorage): School Dashboard, Kitchen Input, Analysis, Route 1–3, Reports, Settings
- Mock school name after login: “โรงเรียนสาธิตตัวอย่าง”
- Public pages MUST NEVER show school name, daily school data, menus, raw kitchen data, or school-specific recommendations.

SITEMAP — create these files
Public:
1. index.html — Home
2. public-dashboard.html — Public Food Waste Dashboard (aggregate only)
3. learning.html — Learning Center hub + article sections
4. how-it-works.html
5. formulas.html — Formula Library
6. login.html

Private:
7. dashboard.html — School Dashboard
8. kitchen.html — Kitchen Input
9. analysis.html — Food Waste Analysis
10. route1.html — Source Reduction
11. route2.html — Agricultural Use
12. route3.html — Target & Optimization
13. reports.html
14. settings.html

HOME
Hero headline: “เปลี่ยน Food Waste ให้เป็นข้อมูล เพื่อสร้างการเปลี่ยนแปลง”
Sub: AI ช่วยวิเคราะห์อาหารที่เหลือจากโรงอาหาร ลดการสูญเสียตั้งแต่ต้นทาง และค้นหาวิธีนำ Food Waste ไปใช้ประโยชน์ด้านการเกษตร
CTAs: Explore Learning Center, School Login
Public aggregate KPIs (clearly labeled “ข้อมูลรวม / ค่าเฉลี่ย”):
- Food Waste Analyzed: 1,250 kg
- Participating Schools: 8
- Average Waste / Person: 82 g
- Food Waste Diverted: 800 kg

PUBLIC DASHBOARD
Aggregate only. Charts (donut composition, line 30-day average trend, bar by category).
Example composition:
Rice 38%, Vegetable 30%, Fruit 9%, Protein 8%, Other 15%.
Caption every chart “ค่าเฉลี่ยจากโรงเรียนที่เข้าร่วม ไม่ระบุโรงเรียน”

LEARNING CENTER
Readable articles with diagrams in HTML (not just About):
- Food Waste คืออะไร / เกิดจากอะไร / Source Reduction
- AI pipeline: Camera → Detection/Classification → Food Category → Estimated Quantity → kg Dataset
- Compost: Carbon, Nitrogen, C:N, Moisture, Aeration
- Food Waste → Analyze → Adjust → Compost → Test Finished Compost → Soil Amendment
Emphasize: Raw Food Waste ≠ Finished Compost. Do not recommend crop use from raw waste alone.

FORMULA LIBRARY
Each formula card MUST show: Name, Formula, Input, Unit, Output, What it is used for, Worked example with numbers, Source type.
Implement all of these EXACTLY:

Source Reduction
- Waste Rate = Waste / Prepared × 100
- Consumed = Prepared - Waste
- Consumption/person = Consumed / Diners
- Waste/person = Waste / Diners
- Forecast = Σ(w × X) / Σw   (weighted moving average)
- Recommended Production = Expected Diners × Forecast Consumption/person × Safety Buffer
- Reduction = Current Production - Recommended Production
- Recommended Portion = Recommended Production / Expected Diners
- Waste Reduction % = (Baseline Waste - New Waste) / Baseline Waste × 100

Food Waste Analysis
- Share = Wi / Wtotal × 100
- DM = W × (1 - Moisture)
- Water = W - DM
- C = DM × Carbon Fraction
- N = DM × Nitrogen Fraction
- Ctotal = ΣC
- Ntotal = ΣN
- C:N = Ctotal / Ntotal
- Mmix = Σ(W × M) / ΣW

Optimization (Route 3)
- Cadded = X × (1-M) × C
- Nadded = X × (1-M) × N
- CNnew = (Cfood + ΣCadded) / (Nfood + ΣNadded)
- Mnew = (Wfood×Mfood + Σ(X×M)) / (Wfood + ΣX)
- Cost = Σ(X × Price/kg)

Put ALL calculation functions in js/formulas.js and unit-test them in the browser console with the worked examples below. Display results rounded reasonably (kg 2 decimals, g integer, % 1 decimal, C:N 1 decimal) but compute with full precision.

KITCHEN INPUT (user-friendly)
Simple form sections:
- Date, Menu name, Number of Diners
- Prepared Food kg: Rice, Vegetable, Fruit, Protein, Other
- Unserved Food kg (MUST be separate from plate waste): same categories
- Plate Waste kg: same categories
- Free Liquid L (Soup/Gravy)
- Contamination kg: Plastic, Other
Before save:
- Mass-balance check: Σ category waste ≈ total if a total field exists; warn if mismatch > 5%
- Show live preview of Waste Rate, Waste/person as they type
Save to localStorage as a meal record.
Include a “Load demo day” button that fills:
  Diners = 500
  Prepared: Rice 100, Vegetable 60, Fruit 20, Protein 40, Other 15  (total 235 kg)
  Unserved: Rice 8, Vegetable 5, Fruit 2, Protein 3, Other 1
  Plate waste: Rice 12, Vegetable 10, Fruit 3, Protein 4, Other 2
  Free liquid = 8 L
  Contamination plastic = 0.4 kg
Treat Waste for Route 1 as Unserved + Plate Waste per category (and total).
Prepared is prepared kg.
Waste total demo = (8+5+2+3+1)+(12+10+3+4+2) = 50 kg
Waste Rate = 50/235×100 = 21.276...% → show 21.3%
Consumed = 235-50 = 185 kg
Consumption/person = 185/500 = 0.370 kg = 370 g
Waste/person = 50/500 = 0.100 kg = 100 g

SCHOOL DASHBOARD
KPI cards from the saved/demo meal:
- Today's Food Waste
- Waste / Person
- Waste Rate
- vs Last Week (use mock historical: ↓ 12%)
Trend chart 7 days (mock series + today’s real calculated point)
Top wasted foods
Today composition donut
Quick actions: Analyze Today, Reduce Waste, Agricultural Use, Create Target

ROUTE 1 — SOURCE REDUCTION
Compute per category AND total using exact formulas.
Forecast: use last 5 mock historical consumption/person values with weights 1,2,3,4,5 (most recent heaviest).
Safety Buffer default 1.08 (editable).
Expected Diners default = today’s diners (editable).
Show a results table like:
  Current Production, Waste, Waste Rate, Waste/Person,
  Recommended Production, Potential Reduction, Suggested Portion
Use words Suggested / Estimated — never command the kitchen to cut immediately.
Button “How was this calculated?” opens a panel listing inputs + formula + substituted numbers.

ROUTE 2 — AGRICULTURAL USE
Use ONLY plate waste + unserved (solid food waste) for compost chemistry. Separate free liquid and contamination from the mix.
Material property defaults (Database Reference — show source badge). Moisture is mass fraction 0–1. Carbon and Nitrogen are fractions of DRY matter.

Default material database (put in js/data.js):
Food waste categories:
- Rice:       M=0.65, C=0.40, N=0.012
- Vegetable:  M=0.90, C=0.38, N=0.025
- Fruit:      M=0.85, C=0.40, N=0.015
- Protein:    M=0.70, C=0.45, N=0.080
- Other:      M=0.75, C=0.40, N=0.020

Amendments:
- Dry leaves:   M=0.15, C=0.48, N=0.009, price=1.5 THB/kg, available=40
- Rice straw:   M=0.12, C=0.50, N=0.006, price=1.2 THB/kg, available=30
- Rice husk:    M=0.10, C=0.42, N=0.005, price=2.0 THB/kg, available=25
- Wood chips:   M=0.20, C=0.49, N=0.004, price=2.5 THB/kg, available=20
- Sawdust:      M=0.12, C=0.50, N=0.003, price=1.8 THB/kg, available=15

Compute Share, DM, Water, C, N per category, then Ctotal, Ntotal, C:N, Mmix.
Decision engine (rules only, no made-up scores):
- If contamination / solid waste > 2% → SORT FIRST
- If free liquid > 0 → SEPARATE LIQUID
- If C:N outside 20–40 OR moisture outside 45–65% → ADJUST BEFORE COMPOST
- Else → COMPOST CANDIDATE
- If plant-based fraction (rice+veg+fruit+other) ≥ 85% AND after noting pre-treatment needed → VERMICOMPOST CANDIDATE AFTER PRE-TREATMENT
Recommendation card MUST include: Recommendation, Why, Required Preparation, Current C:N, Current Moisture, Data Quality.
Disclaimer: this is raw waste chemistry, not finished compost crop advice.

ROUTE 3 — TARGET & OPTIMIZATION
Target selector. MVP default target: Aerobic Compost
  C:N 25–30 : 1
  Moisture 50–60%
  Contamination acceptable
Show CURRENT vs TARGET.
Optimization MUST be a real grid search in JavaScript, not guessed text:
- Search dry leaves 0–30 kg step 0.5
- Search rice husk 0–20 kg step 0.5
- Optionally include straw 0–20 step 1 if needed to find a feasible mix
For every combination compute CNnew, Mnew, Cost with the exact formulas.
Keep only mixes where 25 ≤ C:N ≤ 30 and 0.50 ≤ Mnew ≤ 0.60 and materials ≤ available.
Rank by: (1) lowest cost (2) least total amendment kg (3) fewer material types
Display best mix:
  TARGET, CURRENT, RECOMMENDED additions, AFTER ADJUSTMENT C:N and Moisture, Estimated Cost THB, STATUS ✓ Target Range Reached
If no mix found, say so and suggest separating more liquid / adding more carbon.
All values labeled Estimated/Predicted.
Include “How was this calculated?” with the winning inputs substituted into the formulas.

REPORTS
Daily / Weekly / Monthly tabs using localStorage meals + mock history.
Show totals, waste/person, composition, unserved vs plate waste, free liquid, recommendations summary.
Export as printable view (window.print CSS).

SETTINGS
School name, default buffer, expected diners, unit display (kg/g), reset demo data.

FORMULA ENGINE RULES (critical)
- Implement calculations ONLY in js/formulas.js
- UI must call those functions
- Do not hardcode final C:N or recommended kg in HTML
- Include a self-check block on formulas.html that runs asserts against the demo meal + default properties and shows PASS/FAIL in the page
Worked self-check (approx; compute exactly in code):
  Solid waste W: rice 20, veg 15, fruit 5, protein 7, other 3 → Wtotal=50
  DM rice=20*0.35=7; veg=15*0.10=1.5; fruit=5*0.15=0.75; protein=7*0.30=2.1; other=3*0.25=0.75; DMtotal=12.1
  C = 7*0.40 + 1.5*0.38 + 0.75*0.40 + 2.1*0.45 + 0.75*0.40
  N = 7*0.012 + 1.5*0.025 + 0.75*0.015 + 2.1*0.080 + 0.75*0.020
  Then C:N = C/N and Mmix = Σ(W*M)/50
  Route 1 totals as specified above.

UX
- Simple Mode on Kitchen + Dashboard: numbers + advice, formulas collapsed
- Expert Mode toggle on Route pages + Formula Library: show substitution steps
- Empty states and INSUFFICIENT DATA messages listing missing fields
- LOW CONFIDENCE banner when properties come from Database Reference
- Thai labels, clear buttons, no cluttered formula walls on dashboards

DELIVER
Working static site. Consistent nav. Demo data button. Exact formulas. README with run command.
```
