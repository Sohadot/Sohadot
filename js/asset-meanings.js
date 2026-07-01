/*
 * Category Artifact Meaning Layer — progressive enhancement only.
 * The page renders fully in static HTML without this file. This script adds:
 *   1. Live search/filter across the already-rendered artifact dossiers.
 *   2. Acronym tooltips sourced from data/acronym-glossary.json.
 * Both features fail silently if JS or fetch is unavailable.
 */
(function () {
  "use strict";

  function initSearch() {
    var input = document.getElementById("artifactSearch");
    var countEl = document.getElementById("artifactResultCount");
    var articles = Array.prototype.slice.call(document.querySelectorAll(".artifact"));
    var emptyState = document.getElementById("artifactEmptyState");
    if (!input || articles.length === 0) return;

    function apply() {
      var query = input.value.trim().toLowerCase();
      var shown = 0;
      articles.forEach(function (article) {
        var haystack = article.getAttribute("data-search") || "";
        var match = query === "" || haystack.indexOf(query) !== -1;
        article.hidden = !match;
        if (match) shown += 1;
      });
      if (countEl) countEl.textContent = String(shown);
      if (emptyState) emptyState.hidden = shown !== 0;
    }

    input.addEventListener("input", apply);
    apply();
  }

  function initGlossaryTooltips() {
    var nodes = Array.prototype.slice.call(document.querySelectorAll("[data-acronym]"));
    if (nodes.length === 0) return;

    fetch("/data/acronym-glossary.json")
      .then(function (res) {
        if (!res.ok) throw new Error("glossary fetch failed");
        return res.json();
      })
      .then(function (glossary) {
        var terms = (glossary && glossary.terms) || [];
        var byAcronym = {};
        terms.forEach(function (term) {
          byAcronym[term.acronym] = term;
        });
        nodes.forEach(function (node) {
          var key = node.getAttribute("data-acronym");
          var term = byAcronym[key];
          if (!term) return;
          node.setAttribute(
            "title",
            key + " = " + term.expansion + (term.caution ? " — " + term.caution : "")
          );
        });
      })
      .catch(function () {
        /* Static titles already present in HTML cover the no-JS/no-fetch case. */
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      initSearch();
      initGlossaryTooltips();
    });
  } else {
    initSearch();
    initGlossaryTooltips();
  }
})();
