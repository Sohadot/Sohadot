/*
 * Category Cluster & Buyer Logic Layer — progressive enhancement only.
 * The page renders fully in static HTML without this file. This script adds a
 * single feature: live search/filter across the already-rendered cluster
 * panels (by cluster name, buyer type, or member domain). It fails silently
 * if JS is unavailable — every cluster and member link is already in the DOM.
 */
(function () {
  "use strict";

  function initSearch() {
    var input = document.getElementById("clusterSearch");
    var countEl = document.getElementById("clusterResultCount");
    var clusters = Array.prototype.slice.call(document.querySelectorAll(".cluster"));
    var emptyState = document.getElementById("clusterEmptyState");
    if (!input || clusters.length === 0) return;

    function apply() {
      var query = input.value.trim().toLowerCase();
      var shown = 0;
      clusters.forEach(function (cluster) {
        var haystack = cluster.getAttribute("data-search") || "";
        var match = query === "" || haystack.indexOf(query) !== -1;
        cluster.hidden = !match;
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
