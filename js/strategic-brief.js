/*
 * Strategic Brief Request Layer — progressive enhancement only.
 * The form already works without this file: its native
 * action="mailto:agent@sohadot.com" method="GET" enctype="text/plain"
 * opens a plain-text email draft in browsers that support mailto form
 * submission. With JS enabled, this script:
 *   1. Prefills "asset_or_cluster_interest" and "inquiry_type" from the
 *      URL (?asset=, ?cluster=, ?type=) so links from category-artifacts.html
 *      and category-clusters.html land on a ready-to-send brief.
 *   2. Builds a cleaner mailto: link (structured subject + body) on submit,
 *      for more consistent behavior across mail clients than the native
 *      enctype="text/plain" fallback.
 * No data is sent, stored, or transmitted by this script — it only ever
 * constructs a mailto: URL and hands control to the user's own email app.
 */
(function () {
  "use strict";

  function getParam(name) {
    var params = new URLSearchParams(window.location.search);
    var value = params.get(name);
    return value ? value.trim() : "";
  }

  function prefillFromQuery() {
    var interestField = document.getElementById("asset_or_cluster_interest");
    var typeField = document.getElementById("inquiry_type");
    if (!interestField || !typeField) return;

    var asset = getParam("asset");
    var cluster = getParam("cluster");
    var interest = getParam("interest");
    var type = getParam("type");

    if (asset) {
      interestField.value = asset;
      if (!type) type = "single-asset-acquisition";
    } else if (cluster) {
      interestField.value = cluster;
      if (!type) type = "cluster-acquisition";
    } else if (interest) {
      interestField.value = interest;
    }

    if (type) {
      var option = typeField.querySelector('option[value="' + type + '"]');
      if (option) typeField.value = type;
    }
  }

  function refreshOptionsFromData() {
    var datalist = document.getElementById("assetClusterOptions");
    if (!datalist) return;

    fetch("/data/brief-request-options.json")
      .then(function (res) {
        if (!res.ok) throw new Error("options fetch failed");
        return res.json();
      })
      .then(function (data) {
        var values = [].concat(data.asset_options || [], data.cluster_options || []);
        if (values.length === 0) return;
        datalist.innerHTML = "";
        values.forEach(function (value) {
          var opt = document.createElement("option");
          opt.value = value;
          datalist.appendChild(opt);
        });
      })
      .catch(function () {
        /* Static <datalist> options already in the HTML cover this case. */
      });
  }

  function buildMailto(form) {
    var name = form.name.value.trim();
    var email = form.email.value.trim();
    var company = form.company_or_project.value.trim();
    var interest = form.asset_or_cluster_interest.value.trim();
    var typeSelect = form.inquiry_type;
    var selectedOption = typeSelect.options[typeSelect.selectedIndex];
    var typeLabel = selectedOption ? selectedOption.text : "";
    var message = form.message.value.trim();

    var subjectParts = ["Strategic Brief Request"];
    if (typeLabel) subjectParts.push(typeLabel);
    if (interest) subjectParts.push(interest);
    var subject = subjectParts.join(" — ");

    var bodyLines = [
      "Name: " + name,
      "Email: " + email,
      "Company / Project: " + (company || "—"),
      "Asset or Cluster of Interest: " + (interest || "—"),
      "Inquiry Type: " + (typeLabel || "—"),
      "",
      "Message:",
      message || "—",
    ];
    var body = bodyLines.join("\r\n");

    return (
      "mailto:agent@sohadot.com?subject=" +
      encodeURIComponent(subject) +
      "&body=" +
      encodeURIComponent(body)
    );
  }

  function initForm() {
    var form = document.getElementById("briefForm");
    var status = document.getElementById("briefStatus");
    if (!form) return;

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      if (typeof form.reportValidity === "function" && !form.reportValidity()) {
        return;
      }
      var mailtoUrl = buildMailto(form);
      if (status) status.hidden = false;
      window.location.href = mailtoUrl;
    });
  }

  function init() {
    prefillFromQuery();
    refreshOptionsFromData();
    initForm();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
