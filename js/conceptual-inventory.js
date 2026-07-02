/*
 * Conceptual Inventory Ledger — progressive enhancement only.
 * The page renders fully in static HTML without this file: every domain row
 * is already present in the DOM. This script only adds live search and
 * status filtering across the already-rendered rows. It fails silently if
 * JS is unavailable.
 */
(function () {
  "use strict";

  function init() {
    var input = document.getElementById("inventorySearch");
    var countEl = document.getElementById("inventoryResultCount");
    var emptyState = document.getElementById("inventoryEmptyState");
    var filterBar = document.getElementById("statusFilterBar");
    var rows = Array.prototype.slice.call(document.querySelectorAll("#inventoryBody tr"));
    if (rows.length === 0) return;

    var activeStatus = "all";

    function apply() {
      var query = (input && input.value.trim().toLowerCase()) || "";
      var shown = 0;
      rows.forEach(function (row) {
        var haystack = row.getAttribute("data-search") || "";
        var status = row.getAttribute("data-status") || "";
        var matchesQuery = query === "" || haystack.indexOf(query) !== -1;
        var matchesStatus = activeStatus === "all" || status === activeStatus;
        var match = matchesQuery && matchesStatus;
        row.hidden = !match;
        if (match) shown += 1;
      });
      if (countEl) countEl.textContent = String(shown);
      if (emptyState) emptyState.hidden = shown !== 0;
    }

    if (input) input.addEventListener("input", apply);

    if (filterBar) {
      var buttons = Array.prototype.slice.call(filterBar.querySelectorAll(".filter-btn"));
      buttons.forEach(function (btn) {
        btn.addEventListener("click", function () {
          activeStatus = btn.getAttribute("data-status-filter") || "all";
          buttons.forEach(function (b) {
            b.classList.toggle("active", b === btn);
          });
          apply();
        });
      });
    }

    apply();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
