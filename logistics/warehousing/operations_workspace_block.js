function opsLinkDoctype(root) {
  if (!root || !root.getAttribute) return "Warehouse Job";
  return (root.getAttribute("data-link-doctype") || "Warehouse Job").trim();
}
function esc(s) {
  return frappe.utils.escape_html(s == null ? "" : String(s));
}
function docLink(dt, name, label) {
  if (!name) return esc(label || "—");
  return '<a href="' + frappe.utils.get_form_link(dt, name) + '">' + esc(label || name) + "</a>";
}
function sevLabel(s) {
  var map = {
    overdue: __("Overdue"),
    at_risk: __("At risk"),
    live: __("Live"),
    active: __("Active"),
    idle: __("Idle"),
    upcoming: __("Upcoming"),
    move_in_due: __("Move-in due"),
    start_due: __("Start due"),
  };
  return map[s] || s || "—";
}
function pill(sev) {
  var key = (sev || "active").replace(/[^a-z0-9_]/gi, "");
  return '<span class="wh-ops-sev wh-ops-sev-' + key + '">' + esc(sevLabel(sev)) + "</span>";
}
function numBad(n) {
  n = n || 0;
  if (!n) return "0";
  return '<span class="wh-ops-num-bad">' + n + "</span>";
}
function dash(v) {
  return v ? esc(v) : '<span class="wh-ops-muted">—</span>';
}
function matchesQuery(row, q) {
  if (!q) return true;
  var blob = [
    row.name,
    row.title,
    row.owner_label,
    row.status,
    row.lifecycle_stage,
    row.organizer,
    row.customer,
    row.venue_name,
    row.type,
    row.job_status,
    row.doctype,
  ]
    .join(" ")
    .toLowerCase();
  return blob.indexOf(q) !== -1;
}
function fillHeaderAndKpis(root, d) {
  var titleEl = root.querySelector(".wh-ops-page-title");
  if (titleEl) {
    var tnm = (d.company_name || d.company || "").trim();
    titleEl.textContent = tnm || "—";
  }
  var img = root.querySelector(".wh-ops-company-logo");
  var ph = root.querySelector(".wh-ops-logo-ph");
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
  var cluster = root.querySelector(".wh-ops-meta-cluster");
  if (cluster) {
    var cnt = (d.kpis && d.kpis.jobs) || 0;
    var users = (d.user_workload || []).length;
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
      '<div class="ab-meta-row"><i class="fa fa-cubes"></i><span class="ab-meta-k">' +
      __("Jobs") +
      "</span><span>" +
      cnt +
      "</span></div>" +
      '<div class="ab-meta-row"><i class="fa fa-users"></i><span class="ab-meta-k">' +
      __("Owners") +
      "</span><span>" +
      users +
      "</span></div></div>";
  }
  var kpis = root.querySelector(".wh-ops-kpis");
  if (kpis) {
    var k = d.kpis || {};
    var jobsN = k.jobs || 0;
    var live = k.live || 0;
    var overdue = k.overdue || 0;
    var openOrders = k.open_orders || 0;
    var slaRisk = k.sla_at_risk || 0;
    var slaBreach = k.sla_breached || 0;
    kpis.innerHTML =
      '<div class="header-item wh-ops-kpi-ongoing"><label>' +
      __("Jobs") +
      "</label><span>" +
      jobsN +
      "</span></div>" +
      '<div class="header-item wh-ops-kpi-live"><label>' +
      __("Live") +
      "</label><span>" +
      live +
      "</span></div>" +
      '<div class="header-item wh-ops-kpi-overdue"><label>' +
      __("Overdue") +
      "</label><span>" +
      overdue +
      "</span></div>" +
      '<div class="header-item wh-ops-kpi-soon"><label>' +
      __("Awaiting job") +
      "</label><span>" +
      openOrders +
      "</span></div>" +
      '<div class="header-item wh-ops-kpi-soon"><label>' +
      __("SLA at risk") +
      "</label><span>" +
      slaRisk +
      "</span></div>" +
      '<div class="header-item wh-ops-kpi-overdue"><label>' +
      __("SLA breached") +
      "</label><span>" +
      slaBreach +
      "</span></div>";
    var ring = root.querySelector(".wh-ops-alert-ring");
    var rp = root.querySelector(".wh-ops-ring-pct");
    var rcap = root.querySelector(".wh-ops-ring-cap");
    var ringVal = overdue > 0 ? overdue : jobsN;
    if (ring) {
      ring.style.setProperty("--ab-pct", ringVal > 0 ? "100" : "0");
      ring.classList.toggle("wh-ops-alert-ring--overdue", overdue > 0);
    }
    if (rp) rp.textContent = String(ringVal);
    if (rcap) rcap.textContent = overdue > 0 ? __("overdue") : __("jobs");
  }
  var tc = root.querySelector(".wh-ops-alerts-tab-count");
  if (tc) {
    var asum = d.alert_summary || {};
    var sum = (asum.danger || 0) + (asum.warning || 0) + (asum.info || 0);
    tc.textContent = "(" + sum + ")";
  }
}

function chipKey(s) {
  return String(s || "active").replace(/[^a-z0-9_]/gi, "") || "active";
}
function userBarValue(r) {
  return Number(r.jobs || r.active || r.brand_count || 0);
}
function renderStackBar(el, pipeline) {
  if (!el) return;
  var items = pipeline || [];
  var total = 0;
  items.forEach(function (p) {
    total += Number(p.program_count || 0);
  });
  if (!total) {
    el.innerHTML = "";
    return;
  }
  el.innerHTML = items
    .map(function (p) {
      var n = Number(p.program_count || 0);
      var pct = Math.max(2, (n / total) * 100);
      var key = chipKey(p.lifecycle_stage);
      return (
        '<span class="wh-ops-stackseg wh-ops-chip-' +
        key +
        '" style="width:' +
        pct +
        '%" title="' +
        esc(sevLabel(p.lifecycle_stage) + " " + n) +
        '"></span>'
      );
    })
    .join("");
}
function renderUserBars(root, users) {
  var el = root.querySelector(".wh-ops-userbars");
  if (!el) return;
  users = users || [];
  if (!users.length) {
    el.innerHTML = '<div class="wh-ops-empty">' + __("No user activity for these filters.") + "</div>";
    return;
  }
  var max = 1;
  users.forEach(function (r) {
    max = Math.max(max, userBarValue(r));
  });
  el.innerHTML = users
    .map(function (r) {
      var n = userBarValue(r);
      var pct = Math.max(3, (n / max) * 100);
      var cls = r.overdue || r.sla_breached ? "is-overdue" : r.sla_at_risk || r.due_soon ? "is-risk" : "";
      return (
        '<div class="wh-ops-ubar" data-owner="' +
        esc(r.owner || "") +
        '"><div class="wh-ops-ubar-lbl" title="' +
        esc(r.label || r.owner || __("Unassigned")) +
        '">' +
        esc(r.label || r.owner || __("Unassigned")) +
        '</div><div class="wh-ops-ubar-track"><div class="wh-ops-ubar-fill ' +
        cls +
        '" style="width:' +
        pct +
        '%"></div></div><div class="wh-ops-ubar-n">' +
        n +
        "</div></div>"
      );
    })
    .join("");
  el.querySelectorAll(".wh-ops-ubar").forEach(function (row) {
    row.addEventListener("click", function () {
      var sel = root.querySelector(".wh-ops-filter-user");
      if (!sel) return;
      sel.value = row.getAttribute("data-owner") || "";
      sel._whOwnerTouched = true;
      refresh();
    });
  });
}

function renderOverview(root, d) {
  root._whLastDash = d;
  var q = ((root.querySelector(".wh-ops-search") || {}).value || "").trim().toLowerCase();
  var pipeEl = root.querySelector(".wh-ops-pipeline");
  if (pipeEl) {
    var chips = (d.pipeline || [])
      .map(function (p) {
        var key = (p.lifecycle_stage || "").replace(/[^a-z0-9_]/gi, "") || "active";
        return (
          '<span class="wh-ops-chip wh-ops-chip-' +
          key +
          '">' +
          esc(sevLabel(p.lifecycle_stage)) +
          " <b>" +
          (p.program_count || 0) +
          "</b></span>"
        );
      })
      .join("");
    pipeEl.innerHTML = chips || '<div class="wh-ops-empty">' + __("No jobs in this filter.") + "</div>";
  }
  renderStackBar(root.querySelector(".wh-ops-stackbar"), d.pipeline || []);
  var mixEl = root.querySelector(".wh-ops-mix");
  if (mixEl) {
    var m = d.mix || {};
    var bits = [
      "<span>" + __("Jobs") + " <strong>" + (m.jobs || 0) + "</strong></span>",
      "<span>" + __("Awaiting job") + " <strong>" + (m.open_orders || d.open_orders || 0) + "</strong></span>",
      "<span>" + __("Gate passes") + " <strong>" + (m.gate_passes || 0) + "</strong></span>",
    ];
    var st = m.statuses || {};
    Object.keys(st).forEach(function (k) {
      bits.push("<span>" + esc(k) + " <strong>" + st[k] + "</strong></span>");
    });
    mixEl.innerHTML = bits.join("");
  }
  var attnEl = root.querySelector(".wh-ops-attention");
  if (attnEl) {
    var hot = d.attention_rows || [];
    attnEl.innerHTML = hot.length
      ? hot
          .map(function (r) {
            return (
              '<div class="wh-ops-attn-item">' +
              pill(r.severity) +
              " " +
              docLink(r.doctype || "Warehouse Job", r.name, r.title || r.name) +
              '<div class="wh-ops-attn-meta">' +
              esc(r.owner_label || __("Unassigned")) +
              (r.type ? " · " + esc(r.type) : "") +
              (r.customer ? " · " + esc(r.customer) : "") +
              (r.sla_status && r.sla_status !== "Not Applicable" ? " · " + esc(r.sla_status) : "") +
              "</div></div>"
            );
          })
          .join("")
      : '<div class="wh-ops-empty">' + __("Nothing needs attention in this view.") + "</div>";
  }
  var users = (d.user_workload || []).filter(function (r) {
    if (!q) return true;
    return ((r.label || "") + " " + (r.owner || "")).toLowerCase().indexOf(q) !== -1;
  });
  renderUserBars(root, d.user_workload || []);
  var usersAll = d.user_workload || [];
  var usersCount = root.querySelector(".wh-ops-users-count");
  if (usersCount) usersCount.textContent = usersAll.length ? "(" + usersAll.length + ")" : "";
  var usersWrap = root.querySelector(".wh-ops-users-wrap");
  var usersCountList = root.querySelector(".wh-ops-users-count-list");
  if (usersCountList) usersCountList.textContent = users.length ? "(" + users.length + ")" : "";
  if (usersWrap) {
    if (!users.length) {
      usersWrap.innerHTML = '<div class="wh-ops-empty">' + __("No user activity for these filters.") + "</div>";
    } else {
      usersWrap.innerHTML =
        '<table class="wh-ops-table"><thead><tr><th>' +
        __("User") +
        "</th><th>" +
        __("Jobs") +
        "</th><th>" +
        __("Live") +
        "</th><th>" +
        __("Overdue") +
        "</th><th>" +
        __("At risk") +
        "</th><th>" +
        __("Breached") +
        "</th></tr></thead><tbody>" +
        users
          .map(function (r) {
            return (
              '<tr class="wh-ops-row-click" data-owner="' +
              esc(r.owner || "") +
              '"><td>' +
              esc(r.label || r.owner || __("Unassigned")) +
              "</td><td>" +
              (r.jobs || 0) +
              "</td><td>" +
              (r.live || 0) +
              "</td><td>" +
              numBad(r.overdue) +
              "</td><td>" +
              numBad(r.sla_at_risk) +
              "</td><td>" +
              numBad(r.sla_breached) +
              "</td></tr>"
            );
          })
          .join("") +
        "</tbody></table>";
      usersWrap.querySelectorAll("tr.wh-ops-row-click").forEach(function (tr) {
        tr.addEventListener("click", function () {
          var sel = root.querySelector(".wh-ops-filter-user");
          if (!sel) return;
          sel.value = tr.getAttribute("data-owner") || "";
          sel._whOwnerTouched = true;
          refresh();
        });
      });
    }
  }
  var unas = (d.open_order_rows || []).filter(function (r) {
    return matchesQuery(r, q);
  });
  var unasPanel = root.querySelector(".wh-ops-unassigned-panel");
  var unasWrap = root.querySelector(".wh-ops-unassigned-wrap");
  if (unasPanel) unasPanel.style.display = unas.length || (!q && (d.open_orders || 0)) ? "" : "none";
  if (unasWrap) {
    if (!unas.length) {
      unasWrap.innerHTML =
        '<div class="wh-ops-empty">' + __("Every open order already has a warehouse job.") + "</div>";
    } else {
      unasWrap.innerHTML =
        '<table class="wh-ops-table"><thead><tr><th>' +
        __("Order") +
        "</th><th>" +
        __("Type") +
        "</th><th>" +
        __("Customer") +
        "</th><th>" +
        __("Due") +
        "</th><th>" +
        __("Owner") +
        "</th></tr></thead><tbody>" +
        unas
          .map(function (r) {
            return (
              "<tr><td>" +
              docLink(r.doctype, r.name, r.name) +
              "</td><td>" +
              esc(r.doctype || "") +
              "</td><td>" +
              dash(r.customer) +
              "</td><td>" +
              (r.severity === "overdue" ? numBad(1) + " " : "") +
              dash(r.due_date) +
              "</td><td>" +
              esc(r.owner_label || "") +
              "</td></tr>"
            );
          })
          .join("") +
        "</tbody></table>";
    }
  }
  var work = (d.work_rows || []).filter(function (r) {
    return matchesQuery(r, q);
  });
  var workWrap = root.querySelector(".wh-ops-work-wrap");
  var workCount = root.querySelector(".wh-ops-work-count");
  if (workCount) {
    var extra = d.work_truncated ? " + " + d.work_truncated : "";
    workCount.textContent = work.length ? "(" + work.length + extra + ")" : "";
  }
  if (workWrap) {
    if (!work.length) {
      workWrap.innerHTML = '<div class="wh-ops-empty">' + __("No jobs match these filters.") + "</div>";
    } else {
      workWrap.innerHTML =
        '<table class="wh-ops-table"><thead><tr><th>' +
        __("Job") +
        "</th><th>" +
        __("Attention") +
        "</th><th>" +
        __("Type") +
        "</th><th>" +
        __("Status") +
        "</th><th>" +
        __("Customer") +
        "</th><th>" +
        __("Open") +
        "</th><th>" +
        __("Owner") +
        "</th><th>" +
        __("Order") +
        "</th></tr></thead><tbody>" +
        work
          .map(function (r) {
            return (
              "<tr><td>" +
              docLink(r.doctype || "Warehouse Job", r.name, r.title || r.name) +
              "</td><td>" +
              pill(r.severity) +
              "</td><td>" +
              dash(r.type) +
              "</td><td>" +
              dash(r.job_status) +
              "</td><td>" +
              dash(r.customer) +
              "</td><td>" +
              dash(r.job_open_date) +
              "</td><td>" +
              dash(r.owner_label) +
              "</td><td>" +
              (r.reference_order
                ? docLink(r.reference_order_type || "Inbound Order", r.reference_order, r.reference_order)
                : "—") +
              "</td></tr>"
            );
          })
          .join("") +
        "</tbody></table>";
    }
  }
}

function getJobStatusFilter(root) {
  var s = root.querySelector(".wh-ops-filter-status");
  return (s && s.value) || "open";
}
function getSlaFilter(root) {
  var s = root.querySelector(".wh-ops-filter-sla");
  return (s && s.value) || "all";
}
function populateUserFilter(root, job_status_filter) {
  var sel = root.querySelector(".wh-ops-filter-user");
  if (!sel) return;
  var prev = sel.value;
  frappe.call({
    method: "logistics.warehousing.warehouse_operations_dashboard.get_warehouse_operations_filter_users",
    args: { job_status_filter: job_status_filter || "open" },
    callback: function (r2) {
      var rows = r2.message || [];
      sel.innerHTML = "";
      rows.forEach(function (row) {
        var o = document.createElement("option");
        o.value = row.value || "";
        o.textContent = row.label || row.value || "";
        sel.appendChild(o);
      });
      var want = prev != null && prev !== undefined ? prev : "";
      for (var i = 0; i < sel.options.length; i++) {
        if (sel.options[i].value === want) {
          sel.selectedIndex = i;
          break;
        }
      }
    },
  });
}
function populateAlertUserFilter(root, job_status_filter) {
  var sel = root.querySelector(".wh-ops-filter-alert-user");
  if (!sel) return;
  var prev = sel.value;
  frappe.call({
    method: "logistics.warehousing.warehouse_operations_dashboard.get_warehouse_operations_filter_users",
    args: { job_status_filter: job_status_filter || "open" },
    callback: function (r2) {
      var rows = r2.message || [];
      sel.innerHTML = "";
      rows.forEach(function (row) {
        var o = document.createElement("option");
        o.value = row.value || "";
        o.textContent = row.label || row.value || "";
        sel.appendChild(o);
      });
      var want = prev != null && prev !== undefined ? prev : "";
      for (var i = 0; i < sel.options.length; i++) {
        if (sel.options[i].value === want) {
          sel.selectedIndex = i;
          break;
        }
      }
    },
  });
}
function selectedAirlineCodes(root) {
  var out = [];
  root.querySelectorAll(".wh-ops-airline-cb:checked").forEach(function (cb) {
    if (cb.value) out.push(cb.value);
  });
  return out;
}
function updateAirlineSummary(root) {
  var sumEl = root.querySelector(".wh-ops-airline-summary");
  if (!sumEl) return;
  var cbs = root.querySelectorAll(".wh-ops-airline-cb");
  var n = cbs.length;
  var selN = 0;
  for (var i = 0; i < cbs.length; i++) {
    if (cbs[i].checked) selN++;
  }
  if (!n) {
    sumEl.textContent = __("No types");
    return;
  }
  if (!selN || selN === n) {
    sumEl.textContent = __("All types");
    return;
  }
  if (selN === 1) {
    for (var j = 0; j < cbs.length; j++) {
      if (cbs[j].checked) {
        var row = cbs[j].closest(".wh-ops-airline-cb-row");
        var sp = row && row.querySelector(".wh-ops-airline-lbl");
        sumEl.textContent = (sp && sp.textContent) || cbs[j].value;
        return;
      }
    }
  }
  sumEl.textContent = selN + " " + __("selected");
}
function bindAirlineDropdown(root) {
  if (root._whCarrierUiBound) return;
  var wrap = root.querySelector(".wh-ops-airline-ms");
  var btn = root.querySelector(".wh-ops-airline-dd-toggle");
  if (!wrap || !btn) return;
  root._whCarrierUiBound = true;
  btn.addEventListener("click", function (e) {
    e.stopPropagation();
    var open = wrap.classList.toggle("wh-ops-airline-dd-open");
    btn.setAttribute("aria-expanded", open ? "true" : "false");
  });
  if (!window._whOpsCarrierDocClose) {
    window._whOpsCarrierDocClose = true;
    document.addEventListener("click", function (e) {
      var opens = document.querySelectorAll(".wh-ops-airline-ms.wh-ops-airline-dd-open");
      for (var k = 0; k < opens.length; k++) {
        var w = opens[k];
        if (w.contains(e.target)) continue;
        w.classList.remove("wh-ops-airline-dd-open");
        var b = w.querySelector(".wh-ops-airline-dd-toggle");
        if (b) b.setAttribute("aria-expanded", "false");
      }
    });
  }
  root.addEventListener("change", function (e) {
    if (!e.target || !e.target.classList || !e.target.classList.contains("wh-ops-airline-cb")) return;
    updateAirlineSummary(root);
    refresh();
  });
}
function populateAirlineFilter(root, options, preserveValues) {
  var box = root.querySelector(".wh-ops-airline-checkboxes");
  if (!box) return;
  var prev = preserveValues && preserveValues.length ? preserveValues : selectedAirlineCodes(root);
  var want = {};
  prev.forEach(function (v) {
    want[v] = true;
  });
  box.innerHTML = "";
  (options || []).forEach(function (row) {
    var v = row.value || "";
    var lbl = row.label || row.value || "";
    var lab = document.createElement("label");
    lab.className = "wh-ops-airline-cb-row";
    var inp = document.createElement("input");
    inp.type = "checkbox";
    inp.className = "wh-ops-airline-cb";
    inp.value = v;
    if (want[v]) inp.checked = true;
    var sp = document.createElement("span");
    sp.className = "wh-ops-airline-lbl";
    sp.textContent = lbl;
    lab.appendChild(inp);
    lab.appendChild(sp);
    box.appendChild(lab);
  });
  updateAirlineSummary(root);
}
function renderAlerts(root, summary, items) {
  summary = summary || {};
  items = items || [];
  var danger = summary.danger || 0;
  var warning = summary.warning || 0;
  var info = summary.info || 0;
  var total = danger + warning + info;
  var shipSeen = {};
  items.forEach(function (it) {
    if (it.shipment) shipSeen[it.shipment] = true;
  });
  var shipN = Object.keys(shipSeen).length;
  var section = root.querySelector(".wh-ops-dash-alerts-section");
  if (section) {
    var icons = { danger: "fa-exclamation-circle", warning: "fa-exclamation-triangle", info: "fa-info-circle" };
    var groups = { danger: [], warning: [], info: [] };
    items.forEach(function (it) {
      var lvl = it.level === "danger" ? "danger" : it.level === "warning" ? "warning" : "info";
      var linkDt = it.doctype || opsLinkDoctype(root);
      var link = frappe.utils.get_form_link(linkDt, it.shipment);
      var row =
        '<div class="dash-alert-item ' +
        lvl +
        '"><i class="fa ' +
        icons[lvl] +
        '"></i><span><a href="' +
        link +
        '">' +
        esc(it.shipment) +
        "</a> — " +
        esc(it.msg || "") +
        "</span></div>";
      groups[lvl].push(row);
    });
    var order = ["danger", "warning", "info"];
    var labels = {
      danger: __("There are %s critical alerts"),
      warning: __("There are %s warnings"),
      info: __("There are %s information alerts"),
    };
    var counts = { danger: danger, warning: warning, info: info };
    var groupsHtml = "";
    order.forEach(function (level) {
      var cnt = counts[level];
      if (!cnt) return;
      var label = (labels[level] || "").replace("%s", String(cnt));
      var bodyInner = groups[level].join("");
      groupsHtml +=
        '<div class="dash-alert-group dash-alert-group-' +
        level +
        ' collapsed">' +
        '<div class="dash-alert-group-header" data-level="' +
        level +
        '">' +
        '<i class="fa fa-chevron-right dash-alert-group-chevron"></i>' +
        '<span class="dash-alert-group-title">' +
        esc(label) +
        "</span></div>" +
        '<div class="dash-alert-group-body">' +
        (bodyInner ||
          '<div class="text-muted small">' +
          __("No items.") +
          "</div>") +
        '<div class="text-muted small" style="padding:0.35rem 0 0;">' +
        __("Expand for details. Additional lines may exist beyond the loaded list.") +
        "</div></div></div>";
    });
    section.innerHTML =
      groupsHtml || '<div class="text-muted small">' + __("No alerts for listed jobs.") + "</div>";
    section.querySelectorAll(".dash-alert-group-body").forEach(function (bod) {
      bod.style.setProperty("max-height", "300px");
      bod.style.setProperty("min-height", "0");
      bod.style.setProperty("overflow-y", "auto");
      bod.style.setProperty("overflow-x", "hidden");
    });
    section.querySelectorAll(".dash-alert-group-header").forEach(function (h) {
      h.addEventListener("click", function () {
        var g = h.closest(".dash-alert-group");
        if (!g) return;
        var collapsed = g.classList.toggle("collapsed");
        var chev = h.querySelector(".dash-alert-group-chevron");
        if (chev) {
          chev.classList.remove("fa-chevron-right", "fa-chevron-down");
          chev.classList.add(collapsed ? "fa-chevron-right" : "fa-chevron-down");
        }
      });
    });
  }
  var cardsHost = root.querySelector(".wh-ops-ops-alert-cards");
  if (cardsHost) {
    function oneCard(title, val, alertType) {
      return (
        '<div class="doc-alert-card doc-alert-card-' +
        alertType +
        '"><div class="doc-alert-card-value">' +
        val +
        '</div><div class="doc-alert-card-title">' +
        title +
        "</div></div>"
      );
    }
    cardsHost.innerHTML = [
      oneCard(__("Critical"), danger, "danger"),
      oneCard(__("Warnings"), warning, "warning"),
      oneCard(__("Information"), info, "info"),
      oneCard(__("Jobs"), shipN, "success"),
      oneCard(__("Total"), total, "secondary"),
    ].join("");
  }
}
function refresh() {
  var root = root_element;
  var job_status_filter = getJobStatusFilter(root);
  var sel = root.querySelector(".wh-ops-filter-user");
  var filter_user = sel && sel.value ? sel.value : "";
  var alertSel = root.querySelector(".wh-ops-filter-alert-user");
  var alert_filter_user = alertSel && alertSel.value ? alertSel.value : "";
  var prevAir = selectedAirlineCodes(root);
  var attention = getSlaFilter(root);
  frappe.call({
    method: "logistics.warehousing.warehouse_operations_dashboard.get_warehouse_operations_dashboard",
    args: {
      job_status_filter: job_status_filter,
      filter_user: filter_user,
      alert_filter_user: alert_filter_user,
      attention: attention,
      airlines: prevAir.length ? JSON.stringify(prevAir) : "",
    },
    callback: function (r) {
      if (!r.message) return;
      var d = r.message;
      fillHeaderAndKpis(root, d);
      var ban = root.querySelector(".wh-ops-banner");
      var waiting = d.open_orders || 0;
      if (ban) {
        var parts = [];
        if (waiting > 0) {
          parts.push(
            waiting + " " + __("open order(s) have no warehouse job yet. Create a job from the order to start work.")
          );
        }
        if (d.work_truncated) {
          parts.push(d.work_truncated + " " + __("more job(s) are not shown. Narrow the filters to see the rest."));
        }
        if (parts.length) {
          ban.style.display = "";
          ban.textContent = parts.join(" ");
        } else {
          ban.style.display = "none";
          ban.textContent = "";
        }
      }
      populateAirlineFilter(root, d.airline_options || [], prevAir);
      renderOverview(root, d);
      renderAlerts(root, d.alert_summary || {}, d.alert_items || []);
    },
  });
}
function bindSearch(root) {
  if (root._whSearchBound) return;
  var inp = root.querySelector(".wh-ops-search");
  if (!inp) return;
  root._whSearchBound = true;
  inp.addEventListener("input", function () {
    if (root._whLastDash) renderOverview(root, root._whLastDash);
  });
}
var r = root_element;
r.querySelector(".afw-hub-refresh").addEventListener("click", refresh);
var st = r.querySelector(".wh-ops-filter-status");
if (st) {
  st.addEventListener("change", function () {
    populateUserFilter(root_element, getJobStatusFilter(root_element));
    populateAlertUserFilter(root_element, getJobStatusFilter(root_element));
    refresh();
  });
}
var fu = r.querySelector(".wh-ops-filter-user");
if (fu) {
  fu.addEventListener("change", function () {
    fu._whOwnerTouched = true;
    refresh();
  });
}
var afu = r.querySelector(".wh-ops-filter-alert-user");
if (afu) {
  afu.addEventListener("change", function () {
    afu._whAlertUserTouched = true;
    refresh();
  });
}
var arf = r.querySelector(".wh-ops-alerts-refresh");
if (arf) arf.addEventListener("click", refresh);
var slf = r.querySelector(".wh-ops-filter-sla");
if (slf) slf.addEventListener("change", refresh);
bindAirlineDropdown(root_element);
bindSearch(root_element);
populateUserFilter(root_element, getJobStatusFilter(root_element));
populateAlertUserFilter(root_element, getJobStatusFilter(root_element));
refresh();
