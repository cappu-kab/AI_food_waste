/**
 * Exact formula engine for AI Food Waste prototype.
 * UI must call these functions — do not hardcode final results in HTML.
 */
(function (global) {
  "use strict";

  function sumValues(obj) {
    if (!obj) return 0;
    return Object.keys(obj).reduce((s, k) => s + (Number(obj[k]) || 0), 0);
  }

  function wasteRate(waste, prepared) {
    if (!prepared) return NaN;
    return (waste / prepared) * 100;
  }

  function consumed(prepared, waste) {
    return prepared - waste;
  }

  function consumptionPerPerson(consumedKg, diners) {
    if (!diners) return NaN;
    return consumedKg / diners;
  }

  function wastePerPerson(waste, diners) {
    if (!diners) return NaN;
    return waste / diners;
  }

  /** Forecast = Σ(w × X) / Σw — weighted moving average */
  function forecast(values, weights) {
    if (!values || !values.length) return NaN;
    const w = weights || values.map((_, i) => i + 1);
    let sw = 0;
    let sx = 0;
    for (let i = 0; i < values.length; i++) {
      const wi = w[i] != null ? w[i] : i + 1;
      sw += wi;
      sx += wi * values[i];
    }
    if (!sw) return NaN;
    return sx / sw;
  }

  function recommendedProduction(expectedDiners, forecastConsumptionPerPerson, safetyBuffer) {
    return expectedDiners * forecastConsumptionPerPerson * safetyBuffer;
  }

  function reduction(currentProduction, recommendedProductionKg) {
    return currentProduction - recommendedProductionKg;
  }

  function recommendedPortion(recommendedProductionKg, expectedDiners) {
    if (!expectedDiners) return NaN;
    return recommendedProductionKg / expectedDiners;
  }

  function wasteReductionPct(baselineWaste, newWaste) {
    if (!baselineWaste) return NaN;
    return ((baselineWaste - newWaste) / baselineWaste) * 100;
  }

  function share(wi, wtotal) {
    if (!wtotal) return NaN;
    return (wi / wtotal) * 100;
  }

  function dryMatter(w, moisture) {
    return w * (1 - moisture);
  }

  function waterMass(w, moisture) {
    return w - dryMatter(w, moisture);
  }

  function carbonMass(dm, carbonFraction) {
    return dm * carbonFraction;
  }

  function nitrogenMass(dm, nitrogenFraction) {
    return dm * nitrogenFraction;
  }

  function cnRatio(ctotal, ntotal) {
    if (!ntotal) return NaN;
    return ctotal / ntotal;
  }

  /** Mmix = Σ(W × M) / ΣW */
  function mixMoisture(weights, moistures) {
    let sw = 0;
    let sm = 0;
    for (let i = 0; i < weights.length; i++) {
      const w = Number(weights[i]) || 0;
      sw += w;
      sm += w * (Number(moistures[i]) || 0);
    }
    if (!sw) return NaN;
    return sm / sw;
  }

  function cAdded(x, moisture, cFrac) {
    return x * (1 - moisture) * cFrac;
  }

  function nAdded(x, moisture, nFrac) {
    return x * (1 - moisture) * nFrac;
  }

  function cnNew(cfood, nfood, cAddedSum, nAddedSum) {
    const n = nfood + nAddedSum;
    if (!n) return NaN;
    return (cfood + cAddedSum) / n;
  }

  function mNew(wfood, mfood, additions) {
    // additions: [{x, moisture}, ...]
    let wSum = wfood;
    let mSum = wfood * mfood;
    for (const a of additions || []) {
      wSum += a.x;
      mSum += a.x * a.moisture;
    }
    if (!wSum) return NaN;
    return mSum / wSum;
  }

  function cost(additions) {
    // additions: [{x, price}, ...]
    return (additions || []).reduce((s, a) => s + a.x * a.price, 0);
  }

  /** Merge unserved + plate waste per category */
  function solidWasteByCategory(unserved, plateWaste, categories) {
    const keys = categories || Object.keys(unserved || {});
    const out = {};
    keys.forEach((k) => {
      out[k] = (Number(unserved?.[k]) || 0) + (Number(plateWaste?.[k]) || 0);
    });
    return out;
  }

  function analyzeMealWaste(meal) {
    const cats = ["rice", "vegetable", "fruit", "protein", "other"];
    const prepared = sumValues(meal.prepared);
    const wasteByCat = solidWasteByCategory(meal.unserved, meal.plateWaste, cats);
    const waste = sumValues(wasteByCat);
    const unservedTotal = sumValues(meal.unserved);
    const plateTotal = sumValues(meal.plateWaste);
    const contam =
      (Number(meal.contamination?.plastic) || 0) + (Number(meal.contamination?.other) || 0);
    const diners = Number(meal.diners) || 0;
    const cons = consumed(prepared, waste);
    return {
      categories: cats,
      preparedTotal: prepared,
      wasteByCategory: wasteByCat,
      wasteTotal: waste,
      unservedTotal,
      plateTotal,
      contaminationTotal: contam,
      freeLiquidL: Number(meal.freeLiquidL) || 0,
      diners,
      wasteRate: wasteRate(waste, prepared),
      consumed: cons,
      consumptionPerPerson: consumptionPerPerson(cons, diners),
      wastePerPerson: wastePerPerson(waste, diners),
    };
  }

  /**
   * Compost chemistry for solid food waste only.
   * materials: { key: { moisture, carbon, nitrogen } }
   */
  function analyzeCompostChemistry(wasteByCategory, materials) {
    const rows = [];
    let wtotal = 0;
    let ctotal = 0;
    let ntotal = 0;
    let dmTotal = 0;
    const weights = [];
    const moistures = [];

    Object.keys(wasteByCategory).forEach((key) => {
      const w = Number(wasteByCategory[key]) || 0;
      const mat = materials[key];
      if (!mat || w <= 0) {
        if (w > 0 && !mat) {
          rows.push({ key, w, error: "missing material properties" });
        }
        return;
      }
      const dm = dryMatter(w, mat.moisture);
      const water = waterMass(w, mat.moisture);
      const c = carbonMass(dm, mat.carbon);
      const n = nitrogenMass(dm, mat.nitrogen);
      wtotal += w;
      ctotal += c;
      ntotal += n;
      dmTotal += dm;
      weights.push(w);
      moistures.push(mat.moisture);
      rows.push({
        key,
        w,
        share: null, // fill after wtotal
        dm,
        water,
        c,
        n,
        moisture: mat.moisture,
        carbonFrac: mat.carbon,
        nitrogenFrac: mat.nitrogen,
      });
    });

    rows.forEach((r) => {
      if (r.w != null && !r.error) r.share = share(r.w, wtotal);
    });

    const plantKeys = ["rice", "vegetable", "fruit", "other"];
    const plantMass = plantKeys.reduce((s, k) => s + (Number(wasteByCategory[k]) || 0), 0);
    const plantFraction = wtotal ? plantMass / wtotal : 0;

    return {
      rows,
      wtotal,
      dmTotal,
      ctotal,
      ntotal,
      cn: cnRatio(ctotal, ntotal),
      mmix: mixMoisture(weights, moistures),
      plantFraction,
    };
  }

  function decisionEngine({ contaminationTotal, solidWaste, freeLiquidL, cn, mmix, plantFraction }) {
    const reasons = [];
    const prep = [];
    let recommendation = "COMPOST CANDIDATE";
    let status = "ok";

    const contamRatio = solidWaste > 0 ? contaminationTotal / solidWaste : 0;
    if (contamRatio > 0.02) {
      recommendation = "SORT FIRST";
      reasons.push(
        `มีของแปลกปลอมประมาณ ${(contamRatio * 100).toFixed(1)}% ของอาหารเหลือแข็ง (เกิน 2%)`
      );
      prep.push("คัดพลาสติกและของที่ไม่ใช่อาหารออกก่อนนำไปหมัก");
      status = "warn";
    }

    if (freeLiquidL > 0) {
      if (recommendation === "COMPOST CANDIDATE") recommendation = "SEPARATE LIQUID";
      reasons.push(`มีน้ำซุป/น้ำแกง ${freeLiquidL} ลิตร ต้องแยกออกจากอาหารเหลือแข็ง`);
      prep.push("เทน้ำซุป/น้ำแกงออกจากอาหารเหลือแข็ง");
      status = "warn";
    }

    const moisturePct = mmix * 100;
    const cnOut = !(cn >= 20 && cn <= 40);
    const mOut = !(moisturePct >= 45 && moisturePct <= 65);

    if (cnOut || mOut) {
      if (recommendation === "COMPOST CANDIDATE" || recommendation === "SEPARATE LIQUID") {
        recommendation = "ADJUST BEFORE COMPOST";
      }
      if (cnOut) reasons.push(`อัตราส่วนคาร์บอนต่อไนโตรเจน (C:N) = ${cn.toFixed(1)} ยังไม่อยู่ในช่วง 20–40`);
      if (mOut) reasons.push(`ความชื้นรวม = ${moisturePct.toFixed(1)}% ยังไม่อยู่ในช่วง 45–65%`);
      prep.push("ปรับด้วยวัสดุคาร์บอนหรือไนโตรเจน หรือปรับความชื้นก่อนหมัก");
      status = "adjust";
    }

    if (recommendation === "COMPOST CANDIDATE") {
      reasons.push("ค่า C:N และความชื้นอยู่ในช่วงที่หมักได้ และของแปลกปลอมไม่มากเกินไป");
      prep.push("กองหมักตามวิธีมาตรฐาน กลับกอง และดูอุณหภูมิ");
    }

    let vermiNote = null;
    if (plantFraction >= 0.85) {
      vermiNote =
        "อาจเหมาะกับปุ๋ยไส้เดือนหลังเตรียมวัตถุดิบ — สัดส่วนพืช ≥ 85% (ต้องเตรียมก่อน)";
      prep.push("ถ้าจะใช้ไส้เดือน ต้องเตรียมวัตถุดิบให้พร้อมก่อน");
    }

    return {
      recommendation,
      reasons,
      requiredPreparation: prep,
      vermiNote,
      status,
      contamRatio,
      currentCN: cn,
      currentMoisture: mmix,
    };
  }

  /**
   * Grid search for Route 3.
   * Search dry leaves 0–30 step 0.5, rice husk 0–20 step 0.5,
   * optionally rice straw 0–20 step 1.
   */
  function optimizeAerobicMix(opts) {
    const {
      wfood,
      mfood,
      cfood,
      nfood,
      target,
      amendments,
      includeStraw = true,
    } = opts;

    const leaves = amendments.dryLeaves;
    const husk = amendments.riceHusk;
    const straw = amendments.riceStraw;

    const candidates = [];

    function evalMix(xLeaves, xHusk, xStraw) {
      if (xLeaves > leaves.available || xHusk > husk.available) return;
      if (xStraw > (straw?.available || 0)) return;

      const adds = [];
      if (xLeaves > 0)
        adds.push({
          key: "dryLeaves",
          x: xLeaves,
          moisture: leaves.moisture,
          carbon: leaves.carbon,
          nitrogen: leaves.nitrogen,
          price: leaves.price,
        });
      if (xHusk > 0)
        adds.push({
          key: "riceHusk",
          x: xHusk,
          moisture: husk.moisture,
          carbon: husk.carbon,
          nitrogen: husk.nitrogen,
          price: husk.price,
        });
      if (xStraw > 0)
        adds.push({
          key: "riceStraw",
          x: xStraw,
          moisture: straw.moisture,
          carbon: straw.carbon,
          nitrogen: straw.nitrogen,
          price: straw.price,
        });

      let cAdd = 0;
      let nAdd = 0;
      adds.forEach((a) => {
        cAdd += cAdded(a.x, a.moisture, a.carbon);
        nAdd += nAdded(a.x, a.moisture, a.nitrogen);
      });

      const cn = cnNew(cfood, nfood, cAdd, nAdd);
      const m = mNew(
        wfood,
        mfood,
        adds.map((a) => ({ x: a.x, moisture: a.moisture }))
      );
      const totalCost = cost(adds.map((a) => ({ x: a.x, price: a.price })));
      const totalKg = adds.reduce((s, a) => s + a.x, 0);
      const types = adds.length;

      if (
        cn >= target.cnMin &&
        cn <= target.cnMax &&
        m >= target.moistureMin &&
        m <= target.moistureMax
      ) {
        candidates.push({
          additions: adds,
          cn,
          moisture: m,
          cost: totalCost,
          totalKg,
          types,
          cAdded: cAdd,
          nAdded: nAdd,
        });
      }
    }

    for (let xl = 0; xl <= 30 + 1e-9; xl = Math.round((xl + 0.5) * 10) / 10) {
      for (let xh = 0; xh <= 20 + 1e-9; xh = Math.round((xh + 0.5) * 10) / 10) {
        evalMix(xl, xh, 0);
      }
    }

    if (includeStraw && candidates.length === 0) {
      for (let xl = 0; xl <= 30 + 1e-9; xl = Math.round((xl + 0.5) * 10) / 10) {
        for (let xh = 0; xh <= 20 + 1e-9; xh = Math.round((xh + 0.5) * 10) / 10) {
          for (let xs = 0; xs <= 20 + 1e-9; xs += 1) {
            if (xs === 0) continue;
            evalMix(xl, xh, xs);
          }
        }
      }
    }

    candidates.sort((a, b) => {
      if (a.cost !== b.cost) return a.cost - b.cost;
      if (a.totalKg !== b.totalKg) return a.totalKg - b.totalKg;
      return a.types - b.types;
    });

    return {
      found: candidates.length > 0,
      best: candidates[0] || null,
      count: candidates.length,
      searchedWithStraw: includeStraw,
    };
  }

  function sourceReductionTable(meal, opts) {
    const cats = ["rice", "vegetable", "fruit", "protein", "other"];
    const {
      forecastValues = null,
      safetyBuffer = 1.08,
      expectedDiners = null,
      historicalConsumption = null,
    } = opts || {};

    const diners = expectedDiners != null ? expectedDiners : Number(meal.diners) || 0;
    const hist =
      historicalConsumption ||
      (typeof FW_DATA !== "undefined" ? FW_DATA.mockConsumptionPerPerson : [0.38, 0.36, 0.37, 0.365, 0.37]);
    const forecastCpp = forecastValues
      ? forecast(forecastValues)
      : forecast(hist, [1, 2, 3, 4, 5]);

    const rows = [];
    let prepTotal = 0;
    let wasteTotal = 0;

    cats.forEach((key) => {
      const prepared = Number(meal.prepared?.[key]) || 0;
      const waste =
        (Number(meal.unserved?.[key]) || 0) + (Number(meal.plateWaste?.[key]) || 0);
      prepTotal += prepared;
      wasteTotal += waste;
      const wr = wasteRate(waste, prepared);
      const wpp = wastePerPerson(waste, meal.diners);
      // Per-category forecast uses same consumption share scaled — use category share of consumption
      const catConsumed = consumed(prepared, waste);
      const catCpp = consumptionPerPerson(catConsumed, meal.diners);
      // Recommended production for category: use category-specific forecast from catCpp as point estimate
      // Spec: Forecast from last 5 consumption/person (total). For category table use proportion.
      const shareOfCons = forecastCpp > 0 && meal.diners
        ? catCpp / (consumptionPerPerson(consumed(sumValues(meal.prepared), wasteTotal), meal.diners) || 1)
        : 0;
      void shareOfCons;
      const recProd = recommendedProduction(diners, catCpp, safetyBuffer);
      const red = reduction(prepared, recProd);
      const portion = recommendedPortion(recProd, diners);
      rows.push({
        key,
        currentProduction: prepared,
        waste,
        wasteRate: wr,
        wastePerPerson: wpp,
        recommendedProduction: recProd,
        potentialReduction: red,
        suggestedPortion: portion,
        forecastCpp: catCpp,
      });
    });

    const cons = consumed(prepTotal, wasteTotal);
    const cpp = consumptionPerPerson(cons, meal.diners);
    const recProdTotal = recommendedProduction(diners, forecastCpp, safetyBuffer);
    const totalRow = {
      key: "total",
      currentProduction: prepTotal,
      waste: wasteTotal,
      wasteRate: wasteRate(wasteTotal, prepTotal),
      wastePerPerson: wastePerPerson(wasteTotal, meal.diners),
      recommendedProduction: recProdTotal,
      potentialReduction: reduction(prepTotal, recProdTotal),
      suggestedPortion: recommendedPortion(recProdTotal, diners),
      forecastCpp,
    };

    return {
      rows,
      total: totalRow,
      safetyBuffer,
      expectedDiners: diners,
      forecastCpp,
      historicalConsumption: hist,
      consumptionPerPersonToday: cpp,
    };
  }

  function roundDisplay(value, kind) {
    if (value == null || Number.isNaN(value)) return "—";
    switch (kind) {
      case "kg":
        return Number(value).toFixed(2);
      case "g":
        return String(Math.round(Number(value)));
      case "pct":
        return Number(value).toFixed(1);
      case "cn":
        return Number(value).toFixed(1);
      case "thb":
        return Number(value).toFixed(2);
      default:
        return String(value);
    }
  }

  /** Self-check against demo meal + default properties. Returns { checks: [...], allPass } */
  function runSelfChecks(data) {
    const d = data || (typeof FW_DATA !== "undefined" ? FW_DATA : null);
    const checks = [];
    function assert(name, actual, expected, tol) {
      const t = tol != null ? tol : 1e-9;
      const pass = Math.abs(actual - expected) <= t;
      checks.push({ name, actual, expected, pass });
      return pass;
    }

    // Route 1 demo totals
    const wasteDemo = 50;
    const preparedDemo = 235;
    assert("Waste Rate %", wasteRate(wasteDemo, preparedDemo), (50 / 235) * 100, 1e-9);
    assert("Consumed kg", consumed(preparedDemo, wasteDemo), 185, 1e-9);
    assert("Consumption/person kg", consumptionPerPerson(185, 500), 0.37, 1e-9);
    assert("Waste/person kg", wastePerPerson(50, 500), 0.1, 1e-9);

    // Display rounding
    assert("Waste Rate display 21.3", Number(roundDisplay(wasteRate(50, 235), "pct")), 21.3, 0.05);

    // Chemistry
    const wasteByCat = { rice: 20, vegetable: 15, fruit: 5, protein: 7, other: 3 };
    const chem = analyzeCompostChemistry(wasteByCat, d.foodMaterials);
    assert("Wtotal", chem.wtotal, 50, 1e-9);
    assert("DM rice", chem.rows.find((r) => r.key === "rice").dm, 7, 1e-9);
    assert("DM veg", chem.rows.find((r) => r.key === "vegetable").dm, 1.5, 1e-9);
    assert("DM fruit", chem.rows.find((r) => r.key === "fruit").dm, 0.75, 1e-9);
    assert("DM protein", chem.rows.find((r) => r.key === "protein").dm, 2.1, 1e-9);
    assert("DM other", chem.rows.find((r) => r.key === "other").dm, 0.75, 1e-9);
    assert("DMtotal", chem.dmTotal, 12.1, 1e-9);

    const cExpected = 7 * 0.4 + 1.5 * 0.38 + 0.75 * 0.4 + 2.1 * 0.45 + 0.75 * 0.4;
    const nExpected = 7 * 0.012 + 1.5 * 0.025 + 0.75 * 0.015 + 2.1 * 0.08 + 0.75 * 0.02;
    assert("Ctotal", chem.ctotal, cExpected, 1e-9);
    assert("Ntotal", chem.ntotal, nExpected, 1e-9);
    assert("C:N", chem.cn, cExpected / nExpected, 1e-9);
    const mExpected = (20 * 0.65 + 15 * 0.9 + 5 * 0.85 + 7 * 0.7 + 3 * 0.75) / 50;
    assert("Mmix", chem.mmix, mExpected, 1e-9);

    // Forecast weights
    const hist = [0.38, 0.36, 0.37, 0.365, 0.37];
    const f = forecast(hist, [1, 2, 3, 4, 5]);
    const fExp = (1 * 0.38 + 2 * 0.36 + 3 * 0.37 + 4 * 0.365 + 5 * 0.37) / 15;
    assert("Forecast WMA", f, fExp, 1e-12);

    // Mass balance helper
    const meal = {
      diners: 500,
      prepared: d.demoMeal.prepared,
      unserved: d.demoMeal.unserved,
      plateWaste: d.demoMeal.plateWaste,
      freeLiquidL: 8,
      contamination: { plastic: 0.4, other: 0 },
    };
    const analysis = analyzeMealWaste(meal);
    assert("Demo waste total", analysis.wasteTotal, 50, 1e-9);
    assert("Demo prepared", analysis.preparedTotal, 235, 1e-9);

    return { checks, allPass: checks.every((c) => c.pass) };
  }

  const FW_FORMULAS = {
    sumValues,
    wasteRate,
    consumed,
    consumptionPerPerson,
    wastePerPerson,
    forecast,
    recommendedProduction,
    reduction,
    recommendedPortion,
    wasteReductionPct,
    share,
    dryMatter,
    waterMass,
    carbonMass,
    nitrogenMass,
    cnRatio,
    mixMoisture,
    cAdded,
    nAdded,
    cnNew,
    mNew,
    cost,
    solidWasteByCategory,
    analyzeMealWaste,
    analyzeCompostChemistry,
    decisionEngine,
    optimizeAerobicMix,
    sourceReductionTable,
    roundDisplay,
    runSelfChecks,
  };

  global.FW_FORMULAS = FW_FORMULAS;
})(typeof window !== "undefined" ? window : globalThis);
