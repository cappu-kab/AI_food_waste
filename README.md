# AI Food Waste Lab — Local HTML Prototype

Static multi-page website for an **AI Food Waste Management & Agricultural Learning Center**. No backend, no npm build step.

## Run locally

From the project root:

```bash
python3 -m http.server 8080
```

Then open [http://localhost:8080](http://localhost:8080).

On Windows, `python -m http.server 8080` works the same if Python is installed.

You can also open `index.html` directly in a browser; using a local server is preferred so Chart.js CDN and relative paths behave consistently.

## What’s included

| Path | Role |
|------|------|
| `index.html` | Public home |
| `public-dashboard.html` | Aggregate public KPIs & charts |
| `learning.html` | Learning Center articles |
| `how-it-works.html` | System overview |
| `formulas.html` | Formula library + PASS/FAIL self-check |
| `login.html` | Mock login (any password) |
| `dashboard.html` … `settings.html` | Private school pages |
| `css/styles.css` | Shared design system |
| `js/data.js` | Material DB, mock history, public aggregates |
| `js/formulas.js` | **All** calculation formulas |
| `js/app.js` | Auth, localStorage, nav helpers |

## Mock login

1. Open **School Login**
2. Choose Kitchen Staff or School Admin
3. Enter any password
4. School name after login: **โรงเรียนสาธิตตัวอย่าง**

Public pages never show the school name or kitchen-specific data.

## Demo meal

On **Kitchen Input**, click **Load demo day**:

- Diners 500, Prepared 235 kg, Waste 50 kg  
- Waste Rate **21.3%**, Waste/person **100 g**

Formulas are implemented in `js/formulas.js` only. Open `formulas.html` to see browser asserts (PASS/FAIL), or in the console:

```js
FW_FORMULAS.runSelfChecks(FW_DATA)
```

## Notes

- Chart.js is loaded from CDN on chart pages.
- Primary UI language is Thai; English labels appear where useful.
- Compost recommendations are for **raw waste chemistry**, not finished compost crop advice.
