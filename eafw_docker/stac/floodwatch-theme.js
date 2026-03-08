(function () {
  "use strict";

  var BRAND_TITLE = "FloodWatch STAC API";
  var BRAND_NOTE = "Regional catalog for hazard, rainfall, and multimodal operational layers.";
  var BRAND_LOGO = "/stac-browser/icpac-logo.png";
  var BRAND_TEXT_RE = /^(stac-fastapi|floodwatch data catalog|floodwatch stac api)$/i;
  var rafToken = 0;
  var routeToken = "";

  function removeLegacySections() {
    ["fw-hero", "fw-ops"].forEach(function (id) {
      var node = document.getElementById(id);
      if (node && node.parentNode) {
        node.parentNode.removeChild(node);
      }
    });
  }

  function createLogoNode() {
    var link = document.createElement("a");
    link.className = "fw-brand-logo";
    link.href = "https://www.icpac.net/";
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.setAttribute("aria-label", "IGAD ICPAC");

    var img = document.createElement("img");
    img.src = BRAND_LOGO;
    img.alt = "IGAD ICPAC";
    img.className = "fw-brand-logo__img";
    link.appendChild(img);

    return link;
  }

  function findBrandTitleNode() {
    var nodes = document.querySelectorAll("h1, h2, .navbar-brand, [data-cy='catalog-title']");
    for (var i = 0; i < nodes.length; i++) {
      var text = (nodes[i].textContent || "").trim();
      if (BRAND_TEXT_RE.test(text)) {
        return nodes[i];
      }
    }
    return null;
  }

  function ensureBrandHeading() {
    var titleNode = findBrandTitleNode();
    if (!titleNode || !titleNode.parentNode) return;

    titleNode.textContent = BRAND_TITLE;

    var row = titleNode.closest(".fw-brand-row");
    if (!row) {
      row = document.createElement("div");
      row.className = "fw-brand-row";
      titleNode.parentNode.insertBefore(row, titleNode);
      row.appendChild(titleNode);
    }

    if (!row.querySelector(".fw-brand-logo")) {
      row.insertBefore(createLogoNode(), row.firstChild);
    }

    var note = row.nextElementSibling;
    if (!note || !note.classList || !note.classList.contains("fw-brand-note")) {
      note = document.createElement("p");
      note.className = "fw-brand-note";
      row.parentNode.insertBefore(note, row.nextSibling);
    }
    note.textContent = BRAND_NOTE;
  }

  function normalizeStaleExternalPath() {
    var path = window.location.pathname || "";
    if (
      path.indexOf("/stac-browser/external/http") === 0 ||
      path.indexOf("/stac-browser/http://") === 0 ||
      path.indexOf("/stac-browser/https://") === 0
    ) {
      window.history.replaceState({}, "", "/stac-browser/");
    }
  }

  function unregisterServiceWorkers() {
    if (!("serviceWorker" in navigator) || !navigator.serviceWorker.getRegistrations) {
      return;
    }
    navigator.serviceWorker
      .getRegistrations()
      .then(function (regs) {
        regs.forEach(function (reg) {
          reg.unregister();
        });
      })
      ["catch"](function () {});
  }

  function applyTheme() {
    removeLegacySections();
    normalizeStaleExternalPath();
    ensureBrandHeading();
  }

  function scheduleApply() {
    if (rafToken) cancelAnimationFrame(rafToken);
    rafToken = requestAnimationFrame(function () {
      rafToken = 0;
      applyTheme();
    });
  }

  function scheduleApplyOnRouteChange() {
    var next = (window.location.pathname || "") + "|" + (window.location.search || "");
    if (next === routeToken) return;
    routeToken = next;
    scheduleApply();
    setTimeout(scheduleApply, 300);
  }

  function init() {
    unregisterServiceWorkers();
    scheduleApplyOnRouteChange();
    window.addEventListener("popstate", scheduleApplyOnRouteChange);
    window.addEventListener("hashchange", scheduleApplyOnRouteChange);
    window.addEventListener("pageshow", scheduleApplyOnRouteChange);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
