function esc(s) {
  return frappe.utils.escape_html(s == null ? "" : String(s));
}
function dash(v) {
  return v ? esc(v) : '<span class="nt-ops-muted">—</span>';
}
function money(n, currency) {
  n = Number(n || 0);
  try {
    if (currency && typeof format_currency === "function") {
      return esc(format_currency(n, currency));
    }
    return esc(format_number(n, null, 2));
  } catch (e) {
    return esc(String(n));
  }
}
function docLink(dt, name, label) {
  if (!name) return dash(label);
  return '<a href="' + frappe.utils.get_form_link(dt, name) + '">' + esc(label || name) + "</a>";
}
function fillHeaderAndKpis(root, d) {
  var titleEl = root.querySelector(".nt-ops-page-title");
  if (titleEl) {
    var tnm = (d.company_name || d.company || "").trim();
    titleEl.textContent = tnm || __("Netting");
  }
  var img = root.querySelector(".nt-ops-company-logo");
  var ph = root.querySelector(".nt-ops-logo-ph");
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
  var cluster = root.querySelector(".nt-ops-meta-cluster");
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
      '<div class="ab-meta-row"><i class="fa fa-sitemap"></i><span class="ab-meta-k">' +
      __("Groups") +
      "</span><span>" +
      (k.groups || 0) +
      "</span></div>" +
      '<div class="ab-meta-row"><i class="fa fa-balance-scale"></i><span class="ab-meta-k">' +
      __("Ready") +
      "</span><span>" +
      (k.ready || 0) +
      "</span></div></div>";
  }
  var kpis = root.querySelector(".nt-ops-kpis");
  if (kpis) {
    var cur = d.currency || "";
    kpis.innerHTML =
      '<div class="header-item"><label>' +
      __("Groups") +
      "</label><span>" +
      (k.groups || 0) +
      "</span></div>" +
      '<div class="header-item nt-ops-kpi-ready"><label>' +
      __("Ready to net") +
      "</label><span>" +
      (k.ready || 0) +
      "</span></div>" +
      '<div class="header-item"><label>' +
      __("AR ready") +
      "</label><span>" +
      money(k.ar_ready, cur) +
      "</span></div>" +
      '<div class="header-item"><label>' +
      __("AP ready") +
      "</label><span>" +
      money(k.ap_ready, cur) +
      "</span></div>" +
      '<div class="header-item nt-ops-kpi-ready"><label>' +
      __("Nettable") +
      "</label><span>" +
      money(k.nettable, cur) +
      "</span></div>" +
      '<div class="header-item nt-ops-kpi-draft"><label>' +
      __("Draft entries") +
      "</label><span>" +
      (k.drafts || 0) +
      "</span></div>";
  }
  var ring = root.querySelector(".nt-ops-alert-ring");
  var rp = root.querySelector(".nt-ops-ring-pct");
  var rcap = root.querySelector(".nt-ops-ring-cap");
  var ready = k.ready || 0;
  if (ring) ring.style.setProperty("--ab-pct", ready > 0 ? "100" : "0");
  if (rp) rp.textContent = String(ready);
  if (rcap) rcap.textContent = __("ready");
}
function splitBar(ar, ap) {
  ar = Math.max(0, Number(ar) || 0);
  ap = Math.max(0, Number(ap) || 0);
  var tot = ar + ap;
  if (!tot) {
    return '<div class="nt-ops-split" title="—"></div>';
  }
  var arPct = (ar / tot) * 100;
  var apPct = (ap / tot) * 100;
  return (
    '<div class="nt-ops-split" title="' +
    esc(__("AR") + " " + ar + " / " + __("AP") + " " + ap) +
    '"><div class="nt-ops-split-ar" style="width:' +
    arPct +
    '%"></div><div class="nt-ops-split-ap" style="width:' +
    apPct +
    '%"></div></div>'
  );
}
function matchesQuery(row, q) {
  if (!q) return true;
  var blob = [row.org, row.name, row.settlement_customer, row.settlement_supplier, (row.customers || []).join(" "), (row.suppliers || []).join(" ")]
    .join(" ")
    .toLowerCase();
  return blob.indexOf(q) !== -1;
}
function renderOrgs(root, d) {
  var body = root.querySelector(".nt-ops-orgs-body");
  var empty = root.querySelector(".nt-ops-empty-msg");
  if (!body) return;
  var q = "";
  var inp = root.querySelector(".nt-ops-search");
  if (inp) q = (inp.value || "").trim().toLowerCase();
  var rows = (d.orgs || []).filter(function (r) {
    return matchesQuery(r, q);
  });
  var cur = d.currency || "";
  if (!rows.length) {
    body.innerHTML = "";
    if (empty) {
      empty.style.display = "";
      empty.textContent = q
        ? __("No netting orgs match this search.")
        : d.ready_only
          ? __("No settlement groups currently have both AR and AP ready for netting.")
          : __("No active settlement groups found.");
    }
    return;
  }
  if (empty) {
    empty.style.display = "none";
    empty.textContent = "";
  }
  body.innerHTML = rows
    .map(function (r, i) {
      var netCls = Number(r.net_position) >= 0 ? "nt-ops-net-pos" : "nt-ops-net-neg";
      var readyPill = r.ready ? '<span class="nt-ops-ready">' + __("Ready") + "</span>" : "";
      return (
        '<tr class="nt-ops-row-click" data-group="' +
        esc(r.name) +
        '"><td class="nt-ops-muted">' +
        (i + 1) +
        '</td><td><div class="nt-ops-org">' +
        docLink("Settlement Group", r.name, r.org) +
        readyPill +
        "</div></td><td>" +
        docLink("Customer", r.settlement_customer, r.settlement_customer) +
        (r.customer_count > 1 ? ' <span class="nt-ops-muted">+' + (r.customer_count - 1) + "</span>" : "") +
        "</td><td>" +
        docLink("Supplier", r.settlement_supplier, r.settlement_supplier) +
        (r.supplier_count > 1 ? ' <span class="nt-ops-muted">+' + (r.supplier_count - 1) + "</span>" : "") +
        '</td><td class="nt-ops-num">' +
        money(r.ar, cur) +
        '</td><td class="nt-ops-num">' +
        money(r.ap, cur) +
        '</td><td class="nt-ops-num">' +
        money(r.nettable, cur) +
        '</td><td class="nt-ops-num ' +
        netCls +
        '">' +
        money(r.net_position, cur) +
        "</td><td>" +
        splitBar(r.ar, r.ap) +
        '</td><td class="nt-ops-num">' +
        (r.drafts ? '<span class="nt-ops-kpi-draft">' + r.drafts + "</span>" : '<span class="nt-ops-muted">0</span>') +
        '</td><td class="nt-ops-settle"><a href="#" class="nt-ops-new-entry" data-group="' +
        esc(r.name) +
        '">' +
        __("Settle") +
        "</a></td></tr>"
      );
    })
    .join("");
  body.querySelectorAll(".nt-ops-row-click").forEach(function (tr) {
    tr.addEventListener("click", function (e) {
      if (e.target && (e.target.closest("a") || e.target.tagName === "A")) return;
      var name = tr.getAttribute("data-group");
      if (name) frappe.set_route("Form", "Settlement Group", name);
    });
  });
  body.querySelectorAll(".nt-ops-new-entry").forEach(function (a) {
    a.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      frappe.route_options = { settlement_group: a.getAttribute("data-group") };
      frappe.new_doc("Settlement Entry");
    });
  });
}
function refresh() {
  var root = root_element;
  var readySel = root.querySelector(".nt-ops-filter-ready");
  var limSel = root.querySelector(".nt-ops-filter-limit");
  frappe.call({
    method: "logistics.netting.netting_dashboard.get_netting_dashboard",
    args: {
      ready_only: readySel && readySel.value ? readySel.value : "1",
      limit: limSel && limSel.value ? limSel.value : "15",
    },
    callback: function (r) {
      if (!r.message) return;
      var d = r.message;
      root._ntLastDash = d;
      fillHeaderAndKpis(root, d);
      renderOrgs(root, d);
      var ban = root.querySelector(".nt-ops-banner");
      if (ban) {
        var ready = (d.kpis && d.kpis.ready) || 0;
        if (ready > 0) {
          ban.style.display = "";
          ban.textContent =
            ready +
            " " +
            __("org(s) have both AR and AP outstanding and are ready for netting.");
        } else {
          ban.style.display = "none";
          ban.textContent = "";
        }
      }
    },
  });
}
var r = root_element;
r.querySelector(".nt-ops-refresh").addEventListener("click", refresh);
var readyF = r.querySelector(".nt-ops-filter-ready");
if (readyF) readyF.addEventListener("change", refresh);
var limF = r.querySelector(".nt-ops-filter-limit");
if (limF) limF.addEventListener("change", refresh);
var search = r.querySelector(".nt-ops-search");
if (search) {
  search.addEventListener("input", function () {
    if (root_element._ntLastDash) renderOrgs(root_element, root_element._ntLastDash);
  });
}
refresh();
