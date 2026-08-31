/**
 * Shared app helpers: auth, storage, nav, formatting, charts setup.
 */
(function () {
  "use strict";

  const STORAGE_KEYS = {
    auth: "fw_auth",
    meals: "fw_meals",
    settings: "fw_settings",
    expertMode: "fw_expert_mode",
    simpleMode: "fw_simple_mode",
  };

  function todayISO() {
    const d = new Date();
    return d.toISOString().slice(0, 10);
  }

  function getSettings() {
    try {
      const raw = localStorage.getItem(STORAGE_KEYS.settings);
      if (raw) return JSON.parse(raw);
    } catch (_) {}
    return {
      schoolName: FW_DATA.schoolNameDefault,
      safetyBuffer: 1.08,
      expectedDiners: null,
      unitDisplay: "kg",
    };
  }

  function saveSettings(s) {
    localStorage.setItem(STORAGE_KEYS.settings, JSON.stringify(s));
  }

  function getAuth() {
    try {
      const raw = localStorage.getItem(STORAGE_KEYS.auth);
      if (raw) return JSON.parse(raw);
    } catch (_) {}
    return null;
  }

  function login(role) {
    const auth = {
      role: role || "kitchen",
      schoolName: getSettings().schoolName || FW_DATA.schoolNameDefault,
      loggedInAt: new Date().toISOString(),
    };
    localStorage.setItem(STORAGE_KEYS.auth, JSON.stringify(auth));
    return auth;
  }

  function logout() {
    localStorage.removeItem(STORAGE_KEYS.auth);
  }

  function requireAuth() {
    const auth = getAuth();
    if (!auth) {
      window.location.href = "login.html";
      return null;
    }
    return auth;
  }

  function getMeals() {
    try {
      const raw = localStorage.getItem(STORAGE_KEYS.meals);
      if (raw) return JSON.parse(raw);
    } catch (_) {}
    return [];
  }

  function saveMeals(meals) {
    localStorage.setItem(STORAGE_KEYS.meals, JSON.stringify(meals));
  }

  function saveMeal(meal) {
    const meals = getMeals();
    const id = meal.id || "meal-" + Date.now();
    const record = { ...meal, id, savedAt: new Date().toISOString() };
    const idx = meals.findIndex((m) => m.id === id || m.date === meal.date);
    if (idx >= 0) meals[idx] = record;
    else meals.unshift(record);
    saveMeals(meals);
    return record;
  }

  function getLatestMeal() {
    const meals = getMeals();
    if (meals.length) return meals[0];
    return null;
  }

  function getDemoMeal() {
    const demo = JSON.parse(JSON.stringify(FW_DATA.demoMeal));
    demo.date = todayISO();
    demo.id = "demo-" + demo.date;
    demo.isDemo = true;
    return demo;
  }

  function loadDemoData() {
    const demo = getDemoMeal();
    const history = FW_DATA.mockHistoryMeals.map((m) => ({
      ...JSON.parse(JSON.stringify(m)),
      isDemo: true,
    }));
    saveMeals([demo, ...history]);
    return demo;
  }

  function resetDemoData() {
    localStorage.removeItem(STORAGE_KEYS.meals);
    return loadDemoData();
  }

  function ensureDemoSeeded() {
    if (!getMeals().length) loadDemoData();
  }

  function isExpertMode() {
    return localStorage.getItem(STORAGE_KEYS.expertMode) === "1";
  }

  function setExpertMode(on) {
    localStorage.setItem(STORAGE_KEYS.expertMode, on ? "1" : "0");
  }

  function isSimpleMode() {
    const v = localStorage.getItem(STORAGE_KEYS.simpleMode);
    return v !== "0";
  }

  function setSimpleMode(on) {
    localStorage.setItem(STORAGE_KEYS.simpleMode, on ? "1" : "0");
  }

  function catLabel(key) {
    const c = FW_DATA.categories.find((x) => x.key === key);
    return c ? c.labelTh : key;
  }

  function badge(type) {
    const map = {
      Measured: { cls: "badge-measured", th: "วัดจริง" },
      "AI Estimated": { cls: "badge-ai", th: "AI ประมาณ" },
      "User Input": { cls: "badge-input", th: "ผู้ใช้กรอก" },
      "Database Reference": { cls: "badge-db", th: "ข้อมูลจากตารางอ้างอิง" },
      Calculated: { cls: "badge-calc", th: "คำนวณ" },
      Estimated: { cls: "badge-ai", th: "ประมาณการ" },
      Predicted: { cls: "badge-ai", th: "ทำนาย" },
    };
    const m = map[type] || { cls: "badge-db", th: type };
    return `<span class="badge ${m.cls}" title="${type}">${m.th}</span>`;
  }

  function publicNav(active) {
    const items = [
      { href: "index.html", id: "home", label: "หน้าแรก" },
      { href: "public-dashboard.html", id: "public", label: "ตัวเลขอาหารเหลือ" },
      { href: "learning.html", id: "learning", label: "ศูนย์เรียนรู้" },
      { href: "how-it-works.html", id: "how", label: "ทำงานยังไง" },
      { href: "formulas.html", id: "formulas", label: "วิธีคิดตัวเลข" },
      { href: "login.html", id: "login", label: "เข้าสู่ระบบ" },
    ];
    return `
      <header class="top-nav">
        <div class="nav-inner">
          <a class="brand" href="index.html">
            <span class="brand-mark" aria-hidden="true"></span>
            <span class="brand-text">Food Waste Lab</span>
          </a>
          <nav class="nav-links" aria-label="เมนูหลัก">
            ${items
              .map(
                (i) =>
                  `<a href="${i.href}" class="${i.id === active ? "active" : ""}">${i.label}</a>`
              )
              .join("")}
          </nav>
          <button type="button" class="nav-toggle" aria-label="เมนู" data-nav-toggle>☰</button>
        </div>
      </header>`;
  }

  function privateSidebar(active) {
    const auth = getAuth();
    const school = auth?.schoolName || getSettings().schoolName;
    const items = [
      { href: "dashboard.html", id: "dashboard", label: "หน้าสรุปโรงเรียน", icon: "◈" },
      { href: "kitchen.html", id: "kitchen", label: "บันทึกครัว", icon: "◎" },
      { href: "scan.html", id: "scan", label: "สแกนถาดอาหาร", icon: "◍" },
      { href: "analysis.html", id: "analysis", label: "วิเคราะห์อาหารเหลือ", icon: "◉" },
      { href: "routes.html", id: "routes", label: "รายงานอาหารเหลือ", icon: "▤" },
      { href: "settings.html", id: "settings", label: "ตั้งค่า", icon: "⚙" },
    ];
    return `
      <aside class="sidebar">
        <div class="sidebar-brand">
          <a href="dashboard.html" class="brand">
            <span class="brand-mark" aria-hidden="true"></span>
            <span class="brand-text">Food Waste Lab</span>
          </a>
          <div class="school-chip" title="โรงเรียนที่ล็อกอิน">${school}</div>
        </div>
        <nav class="sidebar-nav">
          ${items
            .map(
              (i) =>
                `<a href="${i.href}" class="${i.id === active ? "active" : ""}"><span class="nav-ico">${i.icon}</span>${i.label}</a>`
            )
            .join("")}
        </nav>
        <div class="sidebar-foot">
          <a href="index.html" class="btn btn-ghost btn-sm">กลับหน้าแรก</a>
          <button type="button" class="btn btn-outline btn-sm" data-logout>ออกจากระบบ</button>
        </div>
      </aside>`;
  }

  function pageShell(opts) {
    // opts: { type: 'public'|'private', active, title, subtitle, bodyHtml, extraClass }
  }

  function initPublicPage(active) {
    const mount = document.getElementById("app-nav");
    if (mount) mount.innerHTML = publicNav(active);
    document.querySelector("[data-nav-toggle]")?.addEventListener("click", () => {
      document.querySelector(".nav-links")?.classList.toggle("open");
    });
  }

  function initPrivatePage(active) {
    if (!requireAuth()) return false;
    ensureDemoSeeded();
    const mount = document.getElementById("app-sidebar");
    if (mount) mount.innerHTML = privateSidebar(active);
    document.querySelector("[data-logout]")?.addEventListener("click", () => {
      logout();
      window.location.href = "login.html";
    });
    const nameEl = document.querySelector("[data-school-name]");
    if (nameEl) nameEl.textContent = getAuth().schoolName;
    return true;
  }

  function massBalanceWarn(categorySum, totalField) {
    if (totalField == null || totalField === "" || Number.isNaN(Number(totalField))) return null;
    const total = Number(totalField);
    if (!total) return null;
    const diff = Math.abs(categorySum - total) / total;
    if (diff > 0.05) {
      return `ผลรวมรายหมวด (${categorySum.toFixed(2)} kg) ต่างจากยอดรวม (${total.toFixed(2)} kg) มากกว่า 5% — กรุณาตรวจสอบ`;
    }
    return null;
  }

  function chartColors() {
    return ["#1B5E3B", "#3D8B5F", "#8B6914", "#C45C26", "#6B7C6E", "#A3B18A"];
  }

  function emptyState(msg, missing) {
    const list =
      missing && missing.length
        ? `<ul class="missing-list">${missing.map((m) => `<li>${m}</li>`).join("")}</ul>`
        : "";
    return `<div class="empty-state"><p class="empty-title">ข้อมูลไม่เพียงพอ</p><p>${msg}</p>${list}</div>`;
  }

  function lowConfidenceBanner() {
    return `<div class="banner banner-warn" role="status">
      <strong>ตัวเลขนี้อาจยังไม่แม่นมาก</strong>
      — คุณสมบัติของอาหารมาจาก ${badge("Database Reference")} ไม่ใช่ค่าที่วัดในห้องแล็บวันนี้
    </div>`;
  }

  function howCalculatedPanel(id, title, lines) {
    return `
      <details class="how-panel" id="${id}">
        <summary>ตัวเลขนี้คิดยังไง?</summary>
        <div class="how-body">
          <h4>${title}</h4>
          ${lines.map((l) => `<p class="mono">${l}</p>`).join("")}
        </div>
      </details>`;
  }

  window.FW = {
    STORAGE_KEYS,
    todayISO,
    getSettings,
    saveSettings,
    getAuth,
    login,
    logout,
    requireAuth,
    getMeals,
    saveMeal,
    getLatestMeal,
    getDemoMeal,
    loadDemoData,
    resetDemoData,
    ensureDemoSeeded,
    isExpertMode,
    setExpertMode,
    isSimpleMode,
    setSimpleMode,
    catLabel,
    badge,
    initPublicPage,
    initPrivatePage,
    massBalanceWarn,
    chartColors,
    emptyState,
    lowConfidenceBanner,
    howCalculatedPanel,
  };
})();
