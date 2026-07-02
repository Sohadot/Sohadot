/*
 * Top 75 Meaning Lock Expansion Queue — progressive enhancement only.
 * The page renders fully in static HTML without this file: all 25 queue
 * candidates are already present in the DOM. This script only adds live
 * search across the already-rendered cards. It fails silently if JS is
 * unavailable.
 */
(function () {
  "use strict";

  function initSearch() {
    var input = document.getElementById("queueSearch");
    var countEl = document.getElementById("queueResultCount");
    var cards = Array.prototype.slice.call(document.querySelectorAll(".queue-card"));
    var emptyState = document.getElementById("queueEmptyState");
    if (!input || cards.length === 0) return;

    function apply() {
      var query = input.value.trim().toLowerCase();
      var shown = 0;
      cards.forEach(function (card) {
        var haystack = card.getAttribute("data-search") || "";
        var match = query === "" || haystack.indexOf(query) !== -1;
        card.hidden = !match;
        if (match) shown += 1;
      });
      if (countEl) countEl.textContent = String(shown);
      if (emptyState) emptyState.hidden = shown !== 0;
    }

    input.addEventListener("input", apply);
    apply();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initSearch);
  } else {
    initSearch();
  }
})();
