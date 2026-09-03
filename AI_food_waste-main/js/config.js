/**
 * API base for the tray-scan ML backend (Flask + YOLOv8s-seg).
 * Empty string = same origin (local Flask serving /site/).
 * On Vercel this points at the public Hugging Face Space.
 */
(function () {
  "use strict";
  var host = typeof location !== "undefined" ? location.hostname : "";
  var local = /^(localhost|127\.0\.0\.1)$/i.test(host);
  window.FW_API_BASE = local
    ? ""
    : "https://cappuuuuu1234-ai-food-waste.hf.space";
})();
