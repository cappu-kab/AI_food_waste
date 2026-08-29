const fs = require("fs");
const path = require("path");
const vm = require("vm");

const root = path.join(__dirname, "..");
const ctx = { console };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(root, "js/data.js"), "utf8"), ctx);
vm.runInContext(fs.readFileSync(path.join(root, "js/formulas.js"), "utf8"), ctx);

const FW_DATA = ctx.FW_DATA;
const FW_FORMULAS = ctx.FW_FORMULAS;
if (!FW_DATA || !FW_FORMULAS) {
  console.error("Failed to load FW_DATA / FW_FORMULAS into VM context");
  process.exit(1);
}
const r = FW_FORMULAS.runSelfChecks(FW_DATA);
r.checks.forEach((c) => {
  console.log(`${c.pass ? "PASS" : "FAIL"} ${c.name} actual=${c.actual} expected=${c.expected}`);
});
console.log("ALL", r.allPass ? "PASS" : "FAIL");

const meal = JSON.parse(JSON.stringify(FW_DATA.demoMeal));
meal.diners = 500;
const a = FW_FORMULAS.analyzeMealWaste(meal);
console.log("demo waste", a.wasteTotal, "rate", a.wasteRate);

const chem = FW_FORMULAS.analyzeCompostChemistry(a.wasteByCategory, FW_DATA.foodMaterials);
console.log("cn", chem.cn, "mmix", chem.mmix);

const opt = FW_FORMULAS.optimizeAerobicMix({
  wfood: chem.wtotal,
  mfood: chem.mmix,
  cfood: chem.ctotal,
  nfood: chem.ntotal,
  target: FW_DATA.aerobicCompostTarget,
  amendments: FW_DATA.amendments,
  includeStraw: true,
});
console.log("opt found", opt.found, "count", opt.count);
if (opt.best) {
  console.log(
    JSON.stringify(
      {
        cn: opt.best.cn,
        m: opt.best.moisture,
        cost: opt.best.cost,
        adds: opt.best.additions.map((x) => ({ k: x.key, x: x.x })),
      },
      null,
      2
    )
  );
}

process.exit(r.allPass ? 0 : 1);
