function opsLinkDoctype(root) {
  if (!root || !root.getAttribute) return "HV Brands";
  return (root.getAttribute("data-link-doctype") || "HV Brands").trim();
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
  return '<span class="hv-ops-sev hv-ops-sev-' + key + '">' + esc(sevLabel(sev)) + "</span>";
}
function numBad(n) {
  n = n || 0;
  if (!n) return "0";
  return '<span class="hv-ops-num-bad">' + n + "</span>";
}
function dash(v) {
  return v ? esc(v) : '<span class="hv-ops-muted">—</span>';
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
    row.job_status,
    row.doctype,
  ]
    .join(" ")
    .toLowerCase();
  return blob.indexOf(q) !== -1;
}
function fillHeaderAndKpis(root, d) {
  var titleEl = root.querySelector(".hv-ops-page-title");
  if (titleEl) {
    var tnm = (d.company_name || d.company || "").trim();
    titleEl.textContent = tnm || "—";
  }
  var img = root.querySelector(".hv-ops-company-logo");
  var ph = root.querySelector(".hv-ops-logo-ph");
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
  var cluster = root.querySelector(".hv-ops-meta-cluster");
  if (cluster) {
    var cnt = (d.kpis && d.kpis.brands) || 0;
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
      '<div class="ab-meta-row"><i class="fa fa-diamond"></i><span class="ab-meta-k">' +
      __("Brands") +
      "</span><span>" +
      cnt +
      "</span></div>" +
      '<div class="ab-meta-row"><i class="fa fa-users"></i><span class="ab-meta-k">' +
      __("Owners") +
      "</span><span>" +
      users +
      "</span></div></div>";
  }
  var kpis = root.querySelector(".hv-ops-kpis");
  if (kpis) {
    var k = d.kpis || {};
    var brands = k.brands || 0;
    var active = k.active || 0;
    var live = k.live || 0;
    var overdue = k.overdue || 0;
    var slaRisk = k.sla_at_risk || 0;
    var slaBreach = k.sla_breached || 0;
    kpis.innerHTML =
      '<div class="header-item hv-ops-kpi-ongoing"><label>' +
      __("Brands") +
      "</label><span>" +
      brands +
      "</span></div>" +
      '<div class="header-item hv-ops-kpi-soon"><label>' +
      __("Active") +
      "</label><span>" +
      active +
      "</span></div>" +
      '<div class="header-item hv-ops-kpi-live"><label>' +
      __("Live") +
      "</label><span>" +
      live +
      "</span></div>" +
      '<div class="header-item hv-ops-kpi-overdue"><label>' +
      __("Overdue") +
      "</label><span>" +
      overdue +
      "</span></div>" +
      '<div class="header-item hv-ops-kpi-soon"><label>' +
      __("SLA at risk") +
      "</label><span>" +
      slaRisk +
      "</span></div>" +
      '<div class="header-item hv-ops-kpi-overdue"><label>' +
      __("SLA breached") +
      "</label><span>" +
      slaBreach +
      "</span></div>";
    var ring = root.querySelector(".hv-ops-alert-ring");
    var rp = root.querySelector(".hv-ops-ring-pct");
    var rcap = root.querySelector(".hv-ops-ring-cap");
    var ringVal = overdue > 0 ? overdue : brands;
    if (ring) {
      ring.style.setProperty("--ab-pct", ringVal > 0 ? "100" : "0");
      ring.classList.toggle("hv-ops-alert-ring--overdue", overdue > 0);
    }
    if (rp) rp.textContent = String(ringVal);
    if (rcap) rcap.textContent = overdue > 0 ? __("overdue") : __("brands");
  }
  var tc = root.querySelector(".hv-ops-alerts-tab-count");
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
        '<span class="hv-ops-stackseg hv-ops-chip-' +
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
  var el = root.querySelector(".hv-ops-userbars");
  if (!el) return;
  users = users || [];
  if (!users.length) {
    el.innerHTML = '<div class="hv-ops-empty">' + __("No user activity for these filters.") + "</div>";
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
        '<div class="hv-ops-ubar" data-owner="' +
        esc(r.owner || "") +
        '"><div class="hv-ops-ubar-lbl" title="' +
        esc(r.label || r.owner || __("Unassigned")) +
        '">' +
        esc(r.label || r.owner || __("Unassigned")) +
        '</div><div class="hv-ops-ubar-track"><div class="hv-ops-ubar-fill ' +
        cls +
        '" style="width:' +
        pct +
        '%"></div></div><div class="hv-ops-ubar-n">' +
        n +
        "</div></div>"
      );
    })
    .join("");
  el.querySelectorAll(".hv-ops-ubar").forEach(function (row) {
    row.addEventListener("click", function () {
      var sel = root.querySelector(".hv-ops-filter-user");
      if (!sel) return;
      sel.value = row.getAttribute("data-owner") || "";
      sel._hvOwnerTouched = true;
      refresh();
    });
  });
}

function renderOverview(root, d) {
  root._hvLastDash = d;
  var q = ((root.querySelector(".hv-ops-search") || {}).value || "").trim().toLowerCase();
  var pipeEl = root.querySelector(".hv-ops-pipeline");
  if (pipeEl) {
    var chips = (d.pipeline || [])
      .map(function (p) {
        var key = (p.lifecycle_stage || "").replace(/[^a-z0-9_]/gi, "") || "active";
        return (
          '<span class="hv-ops-chip hv-ops-chip-' +
          key +
          '">' +
          esc(sevLabel(p.lifecycle_stage)) +
          " <b>" +
          (p.program_count || 0) +
          "</b></span>"
        );
      })
      .join("");
    pipeEl.innerHTML = chips || '<div class="hv-ops-empty">' + __("No brands in this filter.") + "</div>";
  }
  renderStackBar(root.querySelector(".hv-ops-stackbar"), d.pipeline || []);
  var mixEl = root.querySelector(".hv-ops-mix");
  if (mixEl) {
    var m = d.mix || {};
    mixEl.innerHTML =
      "<span>" +
      __("Quotes") +
      " <strong>" +
      (m.quotes || 0) +
      "</strong></span><span>" +
      __("Air") +
      " <strong>" +
      (m.air || 0) +
      "</strong></span><span>" +
      __("Sea") +
      " <strong>" +
      (m.sea || 0) +
      "</strong></span><span>" +
      __("Transport") +
      " <strong>" +
      (m.transport || 0) +
      "</strong></span><span>" +
      __("Unassigned jobs") +
      " <strong>" +
      (m.unassigned || d.unassigned_jobs || 0) +
      "</strong></span>";
  }
  var attnEl = root.querySelector(".hv-ops-attention");
  if (attnEl) {
    var hot = d.attention_rows || [];
    attnEl.innerHTML = hot.length
      ? hot
          .map(function (r) {
            return (
              '<div class="hv-ops-attn-item">' +
              pill(r.severity) +
              " " +
              docLink(r.doctype || "HV Brands", r.name, r.title || r.name) +
              '<div class="hv-ops-attn-meta">' +
              esc(r.owner_label || __("Unassigned")) +
              " · " +
              __("Jobs") +
              " " +
              (r.job_count || 0) +
              (r.sla_breached ? " · " + __("SLA breached") + " " + r.sla_breached : "") +
              "</div></div>"
            );
          })
          .join("")
      : '<div class="hv-ops-empty">' + __("Nothing needs attention in this view.") + "</div>";
  }
  var users = (d.user_workload || []).filter(function (r) {
    if (!q) return true;
    return ((r.label || "") + " " + (r.owner || "")).toLowerCase().indexOf(q) !== -1;
  });
  renderUserBars(root, d.user_workload || []);
  var usersAll = d.user_workload || [];
  var usersCount = root.querySelector(".hv-ops-users-count");
  if (usersCount) usersCount.textContent = usersAll.length ? "(" + usersAll.length + ")" : "";
  var usersWrap = root.querySelector(".hv-ops-users-wrap");
  var usersCountList = root.querySelector(".hv-ops-users-count-list");
  if (usersCountList) usersCountList.textContent = users.length ? "(" + users.length + ")" : "";
  if (usersWrap) {
    if (!users.length) {
      usersWrap.innerHTML = '<div class="hv-ops-empty">' + __("No user activity for these filters.") + "</div>";
    } else {
      usersWrap.innerHTML =
        '<table class="hv-ops-table"><thead><tr><th>' +
        __("User") +
        "</th><th>" +
        __("Brands") +
        "</th><th>" +
        __("Quotes") +
        "</th><th>" +
        __("Jobs") +
        "</th><th>" +
        __("Live") +
        "</th><th>" +
        __("At risk") +
        "</th><th>" +
        __("Breached") +
        "</th></tr></thead><tbody>" +
        users
          .map(function (r) {
            return (
              '<tr class="hv-ops-row-click" data-owner="' +
              esc(r.owner || "") +
              '"><td>' +
              esc(r.label || r.owner || __("Unassigned")) +
              "</td><td>" +
              (r.brand_count || 0) +
              "</td><td>" +
              (r.quotes || 0) +
              "</td><td>" +
              (r.jobs || 0) +
              "</td><td>" +
              (r.live || 0) +
              "</td><td>" +
              numBad(r.sla_at_risk) +
              "</td><td>" +
              numBad(r.sla_breached) +
              "</td></tr>"
            );
          })
          .join("") +
        "</tbody></table>";
      usersWrap.querySelectorAll("tr.hv-ops-row-click").forEach(function (tr) {
        tr.addEventListener("click", function () {
          var sel = root.querySelector(".hv-ops-filter-user");
          if (!sel) return;
          sel.value = tr.getAttribute("data-owner") || "";
          sel._hvOwnerTouched = true;
          refresh();
        });
      });
    }
  }
  var unas = (d.unassigned_rows || []).filter(function (r) {
    return matchesQuery(r, q);
  });
  var unasPanel = root.querySelector(".hv-ops-unassigned-panel");
  var unasWrap = root.querySelector(".hv-ops-unassigned-wrap");
  if (unasPanel) unasPanel.style.display = unas.length || (!q && (d.unassigned_jobs || 0)) ? "" : "none";
  if (unasWrap) {
    if (!unas.length) {
      unasWrap.innerHTML =
        '<div class="hv-ops-empty">' + __("Set HV Brand on the Sales Quote to attach these jobs.") + "</div>";
    } else {
      unasWrap.innerHTML =
        '<table class="hv-ops-table"><thead><tr><th>' +
        __("Job") +
        "</th><th>" +
        __("Type") +
        "</th><th>" +
        __("Status") +
        "</th><th>" +
        __("SLA") +
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
              esc(r.job_status || "") +
              "</td><td>" +
              (r.sla_status ? pill(r.sla_status === "Breached" ? "overdue" : r.sla_status === "At Risk" ? "at_risk" : "active") : "—") +
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
  var workWrap = root.querySelector(".hv-ops-work-wrap");
  var workCount = root.querySelector(".hv-ops-work-count");
  if (workCount) {
    var extra = d.work_truncated ? " + " + d.work_truncated : "";
    workCount.textContent = work.length ? "(" + work.length + extra + ")" : "";
  }
  if (workWrap) {
    if (!work.length) {
      workWrap.innerHTML = '<div class="hv-ops-empty">' + __("No brands match these filters.") + "</div>";
    } else {
      workWrap.innerHTML =
        '<table class="hv-ops-table"><thead><tr><th>' +
        __("Brand") +
        "</th><th>" +
        __("Attention") +
        "</th><th>" +
        __("Quotes") +
        "</th><th>" +
        __("Jobs") +
        "</th><th>" +
        __("Live") +
        "</th><th>" +
        __("SLA") +
        "</th><th>" +
        __("Owners") +
        "</th></tr></thead><tbody>" +
        work
          .map(function (r) {
            var sla =
              (r.sla_breached ? r.sla_breached + " " + __("breached") : "") +
              (r.sla_at_risk ? (r.sla_breached ? ", " : "") + r.sla_at_risk + " " + __("at risk") : "");
            return (
              "<tr><td>" +
              docLink(r.doctype || "HV Brands", r.name, r.title || r.name) +
              "</td><td>" +
              pill(r.severity) +
              "</td><td>" +
              (r.quote_count || 0) +
              "</td><td>" +
              (r.job_count || 0) +
              "</td><td>" +
              (r.live_job_count || 0) +
              "</td><td>" +
              (sla ? numBad(r.sla_breached || r.sla_at_risk) + " " + esc(sla) : "—") +
              "</td><td>" +
              dash(r.owner_label) +
              "</td></tr>"
            );
          })
          .join("") +
        "</tbody></table>";
    }
  }
}

function getJobStatusFilter(root) {
  var s = root.querySelector(".hv-ops-filter-status");
  return (s && s.value) || "ongoing";
}
function getSlaFilter(root) {
  var s = root.querySelector(".hv-ops-filter-sla");
  return (s && s.value) || "all";
}
function populateUserFilter(root, job_status_filter) {
  var sel = root.querySelector(".hv-ops-filter-user");
  if (!sel) return;
  var prev = sel.value;
  frappe.call({
    method: "logistics.high_value.high_value_operations_dashboard.get_high_value_operations_filter_users",
    args: { job_status_filter: job_status_filter || "ongoing" },
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
  var sel = root.querySelector(".hv-ops-filter-alert-user");
  if (!sel) return;
  var prev = sel.value;
  frappe.call({
    method: "logistics.high_value.high_value_operations_dashboard.get_high_value_operations_filter_users",
    args: { job_status_filter: job_status_filter || "ongoing" },
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
  root.querySelectorAll(".hv-ops-airline-cb:checked").forEach(function (cb) {
    if (cb.value) out.push(cb.value);
  });
  return out;
}
function updateAirlineSummary(root) {
  var sumEl = root.querySelector(".hv-ops-airline-summary");
  if (!sumEl) return;
  var cbs = root.querySelectorAll(".hv-ops-airline-cb");
  var n = cbs.length;
  var selN = 0;
  for (var i = 0; i < cbs.length; i++) {
    if (cbs[i].checked) selN++;
  }
  if (!n) {
    sumEl.textContent = __("No brands");
    return;
  }
  if (!selN || selN === n) {
    sumEl.textContent = __("All brands");
    return;
  }
  if (selN === 1) {
    for (var j = 0; j < cbs.length; j++) {
      if (cbs[j].checked) {
        var row = cbs[j].closest(".hv-ops-airline-cb-row");
        var sp = row && row.querySelector(".hv-ops-airline-lbl");
        sumEl.textContent = (sp && sp.textContent) || cbs[j].value;
        return;
      }
    }
  }
  sumEl.textContent = selN + " " + __("selected");
}
function bindAirlineDropdown(root) {
  if (root._hvCarrierUiBound) return;
  var wrap = root.querySelector(".hv-ops-airline-ms");
  var btn = root.querySelector(".hv-ops-airline-dd-toggle");
  if (!wrap || !btn) return;
  root._hvCarrierUiBound = true;
  btn.addEventListener("click", function (e) {
    e.stopPropagation();
    var open = wrap.classList.toggle("hv-ops-airline-dd-open");
    btn.setAttribute("aria-expanded", open ? "true" : "false");
  });
  if (!window._hvOpsCarrierDocClose) {
    window._hvOpsCarrierDocClose = true;
    document.addEventListener("click", function (e) {
      var opens = document.querySelectorAll(".hv-ops-airline-ms.hv-ops-airline-dd-open");
      for (var k = 0; k < opens.length; k++) {
        var w = opens[k];
        if (w.contains(e.target)) continue;
        w.classList.remove("hv-ops-airline-dd-open");
        var b = w.querySelector(".hv-ops-airline-dd-toggle");
        if (b) b.setAttribute("aria-expanded", "false");
      }
    });
  }
  root.addEventListener("change", function (e) {
    if (!e.target || !e.target.classList || !e.target.classList.contains("hv-ops-airline-cb")) return;
    updateAirlineSummary(root);
    refresh();
  });
}
function populateAirlineFilter(root, options, preserveValues) {
  var box = root.querySelector(".hv-ops-airline-checkboxes");
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
    lab.className = "hv-ops-airline-cb-row";
    var inp = document.createElement("input");
    inp.type = "checkbox";
    inp.className = "hv-ops-airline-cb";
    inp.value = v;
    if (want[v]) inp.checked = true;
    var sp = document.createElement("span");
    sp.className = "hv-ops-airline-lbl";
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
  var section = root.querySelector(".hv-ops-dash-alerts-section");
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
      groupsHtml || '<div class="text-muted small">' + __("No alerts for listed brands.") + "</div>";
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
  var cardsHost = root.querySelector(".hv-ops-ops-alert-cards");
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
      oneCard(__("Brands"), shipN, "success"),
      oneCard(__("Total"), total, "secondary"),
    ].join("");
  }
}
function refresh() {
  var root = root_element;
  var job_status_filter = getJobStatusFilter(root);
  var sel = root.querySelector(".hv-ops-filter-user");
  var filter_user = sel && sel.value ? sel.value : "";
  var alertSel = root.querySelector(".hv-ops-filter-alert-user");
  var alert_filter_user = alertSel && alertSel.value ? alertSel.value : "";
  var prevAir = selectedAirlineCodes(root);
  var attention = getSlaFilter(root);
  frappe.call({
    method: "logistics.high_value.high_value_operations_dashboard.get_high_value_operations_dashboard",
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
      var ban = root.querySelector(".hv-ops-banner");
      var unassigned = d.unassigned_jobs || 0;
      if (ban) {
        if (unassigned > 0) {
          ban.style.display = "";
          ban.textContent =
            unassigned +
            " " +
            __("high-value job(s) are not linked to a brand. Set HV Brand on the Sales Quote.");
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
  if (root._hvSearchBound) return;
  var inp = root.querySelector(".hv-ops-search");
  if (!inp) return;
  root._hvSearchBound = true;
  inp.addEventListener("input", function () {
    if (root._hvLastDash) renderOverview(root, root._hvLastDash);
  });
}
var r = root_element;
r.querySelector(".afw-hub-refresh").addEventListener("click", refresh);
var st = r.querySelector(".hv-ops-filter-status");
if (st) {
  st.addEventListener("change", function () {
    populateUserFilter(root_element, getJobStatusFilter(root_element));
    populateAlertUserFilter(root_element, getJobStatusFilter(root_element));
    refresh();
  });
}
var fu = r.querySelector(".hv-ops-filter-user");
if (fu) {
  fu.addEventListener("change", function () {
    fu._hvOwnerTouched = true;
    refresh();
  });
}
var afu = r.querySelector(".hv-ops-filter-alert-user");
if (afu) {
  afu.addEventListener("change", function () {
    afu._hvAlertUserTouched = true;
    refresh();
  });
}
var arf = r.querySelector(".hv-ops-alerts-refresh");
if (arf) arf.addEventListener("click", refresh);
var slf = r.querySelector(".hv-ops-filter-sla");
if (slf) slf.addEventListener("change", refresh);
bindAirlineDropdown(root_element);
bindSearch(root_element);
populateUserFilter(root_element, getJobStatusFilter(root_element));
populateAlertUserFilter(root_element, getJobStatusFilter(root_element));
refresh();
