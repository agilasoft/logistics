function esc(s) {
  return frappe.utils.escape_html(s == null ? "" : String(s));
}
function kg(n) {
  n = Number(n || 0);
  var digits = Math.abs(n) >= 100 ? 0 : 1;
  try {
    return format_number(n, null, digits);
  } catch (e) {
    return String(Math.round(n * 10) / 10);
  }
}
function docLink(dt, name, label) {
  if (!name) return "";
  return '<a href="' + frappe.utils.get_form_link(dt, name) + '">' + esc(label || name) + "</a>";
}
function fillHeaderAndKpis(root, d) {
  var titleEl = root.querySelector(".su-ops-page-title");
  if (titleEl) {
    var tnm = (d.company_name || d.company || "").trim();
    titleEl.textContent = tnm ? tnm + " · " + __("Carbon lanes") : __("Carbon lanes");
  }
  var img = root.querySelector(".su-ops-company-logo");
  var ph = root.querySelector(".su-ops-logo-ph");
  if (d.company_logo_url && img) {
    img.src = d.company_logo_url;
    img.alt = d.company_name || d.company || "";
    img.style.display = "block";
    if (ph) ph.style.display = "none";
  } else {
    if (img) img.style.display = "none";
    if (ph) {
      var nm = (d.company_name || d.company || "Co").trim();
      ph.textContent = (nm.length >= 2 ? nm.substring(0, 2) : nm || "Co").toUpperCase();
      ph.style.display = "inline-flex";
    }
  }
  var k = d.kpis || {};
  var unit = d.unit || "kg CO2e";
  var cluster = root.querySelector(".su-ops-meta-cluster");
  if (cluster) {
    var su = frappe.session.user || "";
    var userSpan = "—";
    if (su && su !== "Guest") {
      var uinf = frappe.user_info(su);
      var sfull = (uinf && uinf.fullname) || su;
      userSpan = sfull + " (" + su + ")";
    }
    cluster.innerHTML =
      '<div class="ab-summary-meta-rows">' +
      '<div class="ab-meta-row"><i class="fa fa-user"></i><span class="ab-meta-k">' +
      __("User") +
      "</span><span>" +
      esc(userSpan) +
      "</span></div>" +
      '<div class="ab-meta-row"><i class="fa fa-road"></i><span class="ab-meta-k">' +
      __("Lanes") +
      "</span><span>" +
      (k.lanes || 0) +
      "</span></div>" +
      '<div class="ab-meta-row"><i class="fa fa-leaf"></i><span class="ab-meta-k">' +
      __("Records") +
      "</span><span>" +
      (k.records || 0) +
      "</span></div></div>";
  }
  var kpis = root.querySelector(".su-ops-kpis");
  if (kpis) {
    kpis.innerHTML =
      '<div class="header-item"><label>' +
      __("Emissions") +
      "</label><span>" +
      esc(kg(k.emissions)) +
      " " +
      esc(unit) +
      "</span></div>" +
      '<div class="header-item su-ops-kpi-net"><label>' +
      __("Net") +
      "</label><span>" +
      esc(kg(k.net)) +
      " " +
      esc(unit) +
      "</span></div>" +
      '<div class="header-item"><label>' +
      __("Offset") +
      "</label><span>" +
      esc(kg(k.offset)) +
      " " +
      esc(unit) +
      "</span></div>" +
      '<div class="header-item"><label>' +
      __("Lanes") +
      "</label><span>" +
      (k.lanes || 0) +
      "</span></div>" +
      '<div class="header-item su-ops-kpi-high"><label>' +
      __("High emission") +
      "</label><span>" +
      (k.high_lanes || 0) +
      "</span></div>";
  }
  var share = Number(k.high_share || 0);
  var ring = root.querySelector(".su-ops-alert-ring");
  var rp = root.querySelector(".su-ops-ring-pct");
  var rcap = root.querySelector(".su-ops-ring-cap");
  var ringColor = share >= 50 ? "#b91c1c" : share >= 25 ? "#c2410c" : "#15803d";
  if (ring) {
    ring.style.setProperty("--ab-pct", String(Math.max(0, Math.min(100, share))));
    ring.style.setProperty("--ro-ring-fill", ringColor);
  }
  if (rp) rp.textContent = Math.round(share) + "%";
  if (rcap) rcap.textContent = __("high emission");
  var count = root.querySelector(".su-ops-lane-count");
  if (count) count.textContent = "(" + (k.shown != null ? k.shown : (d.lanes || []).length) + ")";
}
function renderLegend(root, d) {
  var host = root.querySelector(".su-ops-legend");
  if (!host) return;
  host.innerHTML = (d.legend || [])
    .map(function (band) {
      var cap = band.max == null ? "2000+" : "≤" + band.max;
      return (
        '<span class="su-ops-legend-item" title="' +
        esc(cap + " kg CO2e") +
        '"><span class="su-ops-swatch" style="background:' +
        esc(band.color) +
        '"></span>' +
        esc(__(band.label)) +
        "</span>"
      );
    })
    .join("");
}
function renderLanes(root, d) {
  var host = root.querySelector(".su-ops-lanes");
  var empty = root.querySelector(".su-ops-empty");
  if (!host) return;
  var lanes = d.lanes || [];
  var unit = d.unit || "kg CO2e";
  if (!lanes.length) {
    host.innerHTML = "";
    if (empty) {
      empty.style.display = "";
      empty.textContent = __("No carbon footprint lanes in this period.");
    }
    return;
  }
  if (empty) {
    empty.style.display = "none";
    empty.textContent = "";
  }
  host.innerHTML = lanes
    .map(function (lane) {
      var chips = (lane.records || [])
        .map(function (rec) {
          var ref = "";
          if (rec.reference_doctype && rec.reference_name) {
            ref = docLink(rec.reference_doctype, rec.reference_name, rec.reference_name);
          }
          return (
            '<span class="su-ops-chip" style="--su-chip:' +
            esc(rec.color) +
            ";--su-chip-tint:" +
            esc(rec.tint) +
            '"><span class="su-ops-chip-dot"></span>' +
            docLink("Carbon Footprint", rec.name, rec.name) +
            " · " +
            esc(kg(rec.emissions)) +
            (ref ? " · " + ref : "") +
            "</span>"
          );
        })
        .join("");
      var ends =
        lane.origin && lane.destination
          ? esc(lane.origin) + " → " + esc(lane.destination)
          : esc(lane.label);
      return (
        '<article class="su-ops-lane" style="--su-lane:' +
        esc(lane.color) +
        ";--su-tint:" +
        esc(lane.tint) +
        '"><div class="su-ops-lane-head"><div><div class="su-ops-lane-title">' +
        ends +
        '</div><div class="su-ops-lane-meta"><span class="su-ops-module">' +
        esc(lane.module) +
        '</span><span class="su-ops-pill">' +
        esc(__(lane.band_label || "")) +
        "</span><span>" +
        (lane.count || 0) +
        " " +
        __("records") +
        '</span></div></div><div class="su-ops-kg"><div class="su-ops-kg-value">' +
        esc(kg(lane.emissions)) +
        '</div><div class="su-ops-kg-unit">' +
        esc(unit) +
        '</div></div></div><div class="su-ops-bar" title="' +
        esc(kg(lane.emissions) + " " + unit) +
        '"><span style="width:' +
        Number(lane.bar_pct || 0) +
        '%"></span></div><div class="su-ops-chips">' +
        chips +
        "</div></article>"
      );
    })
    .join("");
}
function refresh() {
  var root = root_element;
  var period = root.querySelector(".su-ops-filter-period");
  var moduleSel = root.querySelector(".su-ops-filter-module");
  var scope = root.querySelector(".su-ops-filter-scope");
  frappe.call({
    method: "logistics.sustainability.sustainability_operations_dashboard.get_sustainability_dashboard",
    args: {
      period: period && period.value ? period.value : "90",
      module: moduleSel && moduleSel.value ? moduleSel.value : "all",
      scope: scope && scope.value ? scope.value : "all",
      limit: 12,
    },
    callback: function (r) {
      if (!r.message) return;
      var d = r.message;
      fillHeaderAndKpis(root, d);
      renderLegend(root, d);
      renderLanes(root, d);
      var ban = root.querySelector(".su-ops-banner");
      if (ban) {
        var high = (d.kpis && d.kpis.high_lanes) || 0;
        if (high > 0) {
          ban.style.display = "";
          ban.textContent =
            high +
            " " +
            __("lane(s) are Poor or Very Poor. Color follows total kg CO2e on the lane.");
        } else {
          ban.style.display = "none";
          ban.textContent = "";
        }
      }
    },
  });
}
var r = root_element;
r.querySelector(".su-ops-refresh").addEventListener("click", refresh);
[".su-ops-filter-period", ".su-ops-filter-module", ".su-ops-filter-scope"].forEach(function (sel) {
  var el = r.querySelector(sel);
  if (el) el.addEventListener("change", refresh);
});
refresh();
