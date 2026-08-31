/**
 * Shared reference data, mock history, and public aggregates.
 * Material moisture is mass fraction 0–1. C and N are fractions of dry matter.
 */
const FW_DATA = {
  schoolNameDefault: "โรงเรียนสาธิตตัวอย่าง",

  publicKpis: {
    foodWasteAnalyzedKg: 1250,
    /** จำนวนนักเรียนที่มีถาดถูกบันทึกเข้าสู่ระบบ */
    studentsWithTrays: 520,
    avgWastePerPersonG: 82,
  },

  publicComposition: [
    { key: "rice", labelTh: "ข้าว", labelEn: "Rice", pct: 38 },
    { key: "vegetable", labelTh: "ผัก", labelEn: "Vegetable", pct: 30 },
    { key: "fruit", labelTh: "ผลไม้", labelEn: "Fruit", pct: 9 },
    { key: "protein", labelTh: "โปรตีน", labelEn: "Protein", pct: 8 },
    { key: "other", labelTh: "อื่นๆ", labelEn: "Other", pct: 15 },
  ],

  /** 30-day average waste/person (g) for public trend chart */
  publicTrend30d: [
    95, 92, 90, 88, 91, 87, 85, 86, 84, 83,
    85, 82, 80, 81, 79, 78, 80, 77, 76, 75,
    78, 74, 73, 72, 74, 71, 70, 69, 71, 82,
  ],

  categories: [
    { key: "rice", labelTh: "ข้าว", labelEn: "Rice" },
    { key: "vegetable", labelTh: "ผัก", labelEn: "Vegetable" },
    { key: "fruit", labelTh: "ผลไม้", labelEn: "Fruit" },
    { key: "protein", labelTh: "โปรตีน", labelEn: "Protein" },
    { key: "other", labelTh: "อื่นๆ", labelEn: "Other" },
  ],

  foodMaterials: {
    rice: { moisture: 0.65, carbon: 0.4, nitrogen: 0.012, source: "Database Reference" },
    vegetable: { moisture: 0.9, carbon: 0.38, nitrogen: 0.025, source: "Database Reference" },
    fruit: { moisture: 0.85, carbon: 0.4, nitrogen: 0.015, source: "Database Reference" },
    protein: { moisture: 0.7, carbon: 0.45, nitrogen: 0.08, source: "Database Reference" },
    other: { moisture: 0.75, carbon: 0.4, nitrogen: 0.02, source: "Database Reference" },
  },

  amendments: {
    dryLeaves: {
      key: "dryLeaves",
      labelTh: "ใบแห้ง",
      labelEn: "Dry leaves",
      moisture: 0.15,
      carbon: 0.48,
      nitrogen: 0.009,
      price: 1.5,
      available: 40,
      source: "Database Reference",
    },
    riceStraw: {
      key: "riceStraw",
      labelTh: "ฟางข้าว",
      labelEn: "Rice straw",
      moisture: 0.12,
      carbon: 0.5,
      nitrogen: 0.006,
      price: 1.2,
      available: 30,
      source: "Database Reference",
    },
    riceHusk: {
      key: "riceHusk",
      labelTh: "แกลบ",
      labelEn: "Rice husk",
      moisture: 0.1,
      carbon: 0.42,
      nitrogen: 0.005,
      price: 2.0,
      available: 25,
      source: "Database Reference",
    },
    woodChips: {
      key: "woodChips",
      labelTh: "เศษไม้",
      labelEn: "Wood chips",
      moisture: 0.2,
      carbon: 0.49,
      nitrogen: 0.004,
      price: 2.5,
      available: 20,
      source: "Database Reference",
    },
    sawdust: {
      key: "sawdust",
      labelTh: "ขี้เลื่อย",
      labelEn: "Sawdust",
      moisture: 0.12,
      carbon: 0.5,
      nitrogen: 0.003,
      price: 1.8,
      available: 15,
      source: "Database Reference",
    },
  },

  /** Last 5 consumption/person (kg) for forecast; oldest → newest. Weights 1..5 */
  mockConsumptionPerPerson: [0.38, 0.36, 0.37, 0.365, 0.37],

  /** 7-day waste/person (g) mock series; last slot replaced by today's calculated */
  mockWastePerPerson7d: [115, 108, 102, 98, 95, 90, null],

  /** vs last week mock delta */
  vsLastWeekPct: -12,

  aerobicCompostTarget: {
    nameTh: "ปุ๋ยหมักแบบมีอากาศ",
    nameEn: "Aerobic Compost",
    cnMin: 25,
    cnMax: 30,
    moistureMin: 0.5,
    moistureMax: 0.6,
  },

  demoMeal: {
    date: null, // filled at load time
    menuName: "เมนูตัวอย่าง — ข้าวผัด / ผักลวก / ผลไม้",
    diners: 500,
    prepared: { rice: 100, vegetable: 60, fruit: 20, protein: 40, other: 15 },
    unserved: { rice: 8, vegetable: 5, fruit: 2, protein: 3, other: 1 },
    plateWaste: { rice: 12, vegetable: 10, fruit: 3, protein: 4, other: 2 },
    freeLiquidL: 8,
    contamination: { plastic: 0.4, other: 0 },
  },

  mockHistoryMeals: [
    {
      id: "hist-1",
      date: "2026-08-21",
      menuName: "ข้าวแกง",
      diners: 480,
      prepared: { rice: 95, vegetable: 55, fruit: 18, protein: 38, other: 12 },
      unserved: { rice: 10, vegetable: 6, fruit: 2, protein: 4, other: 1 },
      plateWaste: { rice: 14, vegetable: 11, fruit: 3, protein: 5, other: 2 },
      freeLiquidL: 7,
      contamination: { plastic: 0.3, other: 0.1 },
    },
    {
      id: "hist-2",
      date: "2026-08-22",
      menuName: "ก๋วยเตี๋ยว",
      diners: 510,
      prepared: { rice: 90, vegetable: 70, fruit: 22, protein: 42, other: 14 },
      unserved: { rice: 7, vegetable: 8, fruit: 3, protein: 3, other: 1 },
      plateWaste: { rice: 11, vegetable: 12, fruit: 4, protein: 4, other: 2 },
      freeLiquidL: 10,
      contamination: { plastic: 0.5, other: 0 },
    },
    {
      id: "hist-3",
      date: "2026-08-25",
      menuName: "ข้าวราดแกง",
      diners: 495,
      prepared: { rice: 105, vegetable: 58, fruit: 19, protein: 39, other: 16 },
      unserved: { rice: 9, vegetable: 4, fruit: 2, protein: 3, other: 2 },
      plateWaste: { rice: 13, vegetable: 9, fruit: 3, protein: 4, other: 2 },
      freeLiquidL: 6,
      contamination: { plastic: 0.2, other: 0 },
    },
  ],
};

(typeof window !== "undefined" ? window : globalThis).FW_DATA = FW_DATA;
