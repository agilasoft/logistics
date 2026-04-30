var mapInstance = null;
function loadLeafCss(root) {
  if (root.querySelector("link[data-afw-lf]")) return;
  var l = document.createElement("link");
  l.rel = "stylesheet";
  l.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
  l.setAttribute("data-afw-lf", "1");
  root.appendChild(l);
}
function loadLeafJs(cb) {
  if (window.L) {
    cb();
    return;
  }
  var s = document.createElement("script");
  s.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
  s.onload = cb;
  document.head.appendChild(s);
}
function afwMapWalkAncestors(ph, fn) {
  var el = ph;
  while (el) {
    fn(el);
    if (el.parentElement) el = el.parentElement;
    else if (el.parentNode && el.parentNode.nodeType === 11 && el.parentNode.host) el = el.parentNode.host;
    else el = null;
  }
}
function afwMapScrollParents(ph) {
  var out = [];
  afwMapWalkAncestors(ph, function (el) {
    try {
      if (el.nodeType === 1 && el !== document.documentElement) {
        var oy = window.getComputedStyle(el).overflowY;
        var ox = window.getComputedStyle(el).overflowX;
        if (
          (oy === "auto" || oy === "scroll" || oy === "overlay" || ox === "auto" || ox === "scroll") &&
          (el.scrollHeight > el.clientHeight + 2 || el.scrollWidth > el.clientWidth + 2)
        ) {
          out.push(el);
        }
      }
    } catch (e0) {}
  });
  return out;
}
function afwMapMountContainer(ph) {
  var host = ph.getRootNode && ph.getRootNode().host;
  if (!host) return document.body;
  return host.parentElement || document.body;
}
function removeGoogleMapOverlay(root) {
  if (!root) return;
  var u = root._afwGmUnbind;
  var ro = root._afwGmRo;
  var m = root._afwGmMount;
  if (u) {
    try {
      u();
    } catch (e) {}
  }
  root._afwGmUnbind = null;
  if (ro) {
    try {
      ro.disconnect();
    } catch (e) {}
  }
  root._afwGmRo = null;
  if (m && m.parentNode) {
    try {
      m.parentNode.removeChild(m);
    } catch (e) {}
  }
  root._afwGmMount = null;
  root._afwGmMap = null;
  var c = root._afwGmContainer;
  if (c && root._afwGmSetRelative) {
    try {
      c.style.position = "";
    } catch (e1) {}
    root._afwGmSetRelative = false;
  }
  root._afwGmContainer = null;
}
function clearMapEl(el) {
  var root = el && el.getRootNode ? el.getRootNode() : null;
  if (root && root.host) removeGoogleMapOverlay(root);
  if (mapInstance) {
    try {
      if (typeof mapInstance._afwLeafletZoomCleanup === "function") {
        mapInstance._afwLeafletZoomCleanup();
      }
    } catch (eC) {}
    try {
      mapInstance.remove();
    } catch (e) {}
    mapInstance = null;
  }
  if (el) el.innerHTML = "";
}
function useGoogleMaps(mr) {
  return String(mr || "")
    .toLowerCase()
    .trim() === "google maps";
}
function ensureGoogleMaps(apiKey, done) {
  if (window.google && window.google.maps) {
    done();
    return;
  }
  var id = "afw-hub-gmaps-js";
  if (document.getElementById(id)) {
    var tries = 0;
    var check = function () {
      if (window.google && window.google.maps) done();
      else if (tries++ < 120) setTimeout(check, 50);
      else done(new Error("gmaps_timeout"));
    };
    check();
    return;
  }
  var s = document.createElement("script");
  s.id = id;
  s.async = true;
  s.src = "https://maps.googleapis.com/maps/api/js?key=" + encodeURIComponent(apiKey) + "&libraries=geometry";
  s.onload = function () {
    done();
  };
  s.onerror = function () {
    done(new Error("gmaps_load"));
  };
  document.head.appendChild(s);
}
function baseRadiusPx(n) {
  n = Math.max(0, Number(n) || 0);
  return Math.min(72, 18 + Math.sqrt(n) * 7);
}
function leafletZoomRadiusFactor(zoom) {
  var z = Number(zoom);
  var zz = isFinite(z) ? z : 3;
  return Math.max(0.7, Math.min(3.5, Math.pow(1.38, 7.3 - zz)));
}
function radiusFromCount(n, zoom) {
  return baseRadiusPx(n) * leafletZoomRadiusFactor(zoom);
}
function googleBaseRadiusM(n) {
  n = Math.max(0, Number(n) || 0);
  return Math.min(1600000, 72000 + 32000 * Math.sqrt(n));
}
function googleZoomRadiusFactor(zoom) {
  var z = Number(zoom);
  var zz = isFinite(z) ? z : 3;
  return Math.max(0.58, Math.min(3.6, Math.pow(1.37, 7.2 - zz)));
}
function googleCircleRadiusM(n, zoom) {
  return googleBaseRadiusM(n) * googleZoomRadiusFactor(zoom);
}
function flagEmojiFromCountryCode(cc) {
  var s = String(cc || "")
    .trim()
    .toUpperCase();
  if (s.length !== 2) return "";
  var a = s.charCodeAt(0);
  var b = s.charCodeAt(1);
  if (a < 65 || a > 90 || b < 65 || b > 90) return "";
  return String.fromCharCode(a + 127397) + String.fromCharCode(b + 127397);
}
function unlocoPopupHtml(m) {
  var u = frappe.utils.escape_html(m.unloco || "");
  var imp = m.import_count || 0;
  var exp = m.export_count || 0;
  var dom = m.domestic_count || 0;
  var flagRaw = (m.flag && String(m.flag)) || flagEmojiFromCountryCode(m.country_code);
  var flagDisp = flagRaw ? frappe.utils.escape_html(flagRaw) : "";
  var flagHtml = flagDisp
    ? '<span class="afw-hub-popup-flag" aria-hidden="true">' + flagDisp + "</span>"
    : "";
  return (
    '<div class="afw-hub-unloco-popup">' +
    '<div class="afw-hub-popup-head">' +
    '<div class="afw-hub-popup-hero">' +
    flagHtml +
    '<div class="afw-hub-popup-code"><strong>' +
    u +
    "</strong></div></div>" +
    '<span class="afw-hub-popup-close-slot" aria-hidden="true"></span></div>' +
    '<div class="afw-hub-popup-stats">' +
    '<div class="afw-hub-popup-stat"><strong>' +
    __("International import") +
    " (" +
    __("Origin") +
    '):</strong> <strong>' +
    imp +
    "</strong></div>" +
    '<div class="afw-hub-popup-stat"><strong>' +
    __("International export") +
    " (" +
    __("Destination") +
    '):</strong> <strong>' +
    exp +
    "</strong></div>" +
    '<div class="afw-hub-popup-stat"><strong>' +
    __("Domestic") +
    " (" +
    __("Same country") +
    '):</strong> <strong>' +
    dom +
    "</strong></div></div></div>"
  );
}
function bubbleLayersForMarker(m) {
  var lat = m.lat;
  var lon = m.lon;
  if (lat == null || lon == null) return [];
  var imp = m.import_count || 0;
  var exp = m.export_count || 0;
  var dom = m.domestic_count || 0;
  var stroke = "#1e40af";
  var fill = "#3b82f6";
  var n = imp + exp + dom;
  if (n <= 0) return [];
  return [{ n: n, stroke: stroke, fill: fill, ll: [lat, lon] }];
}
function renderMapLeaflet(root, markers) {
  var el = root.querySelector(".afw-hub-map");
  if (!el) return;
  loadLeafCss(root);
  loadLeafJs(function () {
    el.innerHTML = "";
    var map = L.map(el).setView([20, 0], 2);
    mapInstance = map;
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "OpenStreetMap" }).addTo(map);
    var bounds = [];
    var leafletBubbles = [];
    (markers || []).forEach(function (m) {
      var layers = bubbleLayersForMarker(m);
      layers.forEach(function (layer) {
        var cm = L.circleMarker(layer.ll, {
          radius: radiusFromCount(layer.n, map.getZoom()),
          color: layer.stroke,
          fillColor: layer.fill,
          fillOpacity: 0.55,
          weight: 2,
        })
          .addTo(map)
          .bindPopup(unlocoPopupHtml(m));
        leafletBubbles.push({ cm: cm, count: layer.n });
        bounds.push(layer.ll);
      });
    });
    var applyLeafletZoom = function () {
      var z = map.getZoom();
      leafletBubbles.forEach(function (row) {
        row.cm.setRadius(radiusFromCount(row.count, z));
      });
    };
    map.on("zoomend", applyLeafletZoom);
    map._afwLeafletZoomCleanup = function () {
      map.off("zoomend", applyLeafletZoom);
    };
    applyLeafletZoom();
    if (bounds.length >= 2) map.fitBounds(bounds, { padding: [40, 40], maxZoom: 8 });
    else if (bounds.length === 1) map.setView(bounds[0], 6);
    setTimeout(function () {
      try {
        map.invalidateSize();
        applyLeafletZoom();
      } catch (e) {}
    }, 250);
  });
}
function renderMapGoogle(root, markers, apiKey) {
  var ph = root.querySelector(".afw-hub-map");
  if (!ph) return;
  removeGoogleMapOverlay(root);
  ph.innerHTML = "";
  ensureGoogleMaps(apiKey, function (err) {
    if (err || !window.google || !window.google.maps) {
      renderMapLeaflet(root, markers);
      return;
    }
    try {
      var container = afwMapMountContainer(ph);
      var useFixed = container === document.body;
      var cs = window.getComputedStyle(container);
      if (!useFixed && cs.position === "static") {
        container.style.position = "relative";
        root._afwGmSetRelative = true;
      } else {
        root._afwGmSetRelative = false;
      }
      root._afwGmContainer = container;
      var mount = document.createElement("div");
      mount.className = "afw-hub-gm-mount";
      mount.style.cssText =
        (useFixed ? "position:fixed;z-index:5999;" : "position:absolute;z-index:50;") +
        "left:0;top:0;width:10px;height:10px;border-radius:6px;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,0.12);background:#e5e7eb;";
      container.appendChild(mount);
      root._afwGmMount = mount;
      function sync() {
        var r = ph.getBoundingClientRect();
        if (useFixed) {
          mount.style.left = r.left + "px";
          mount.style.top = r.top + "px";
        } else {
          var cr = container.getBoundingClientRect();
          mount.style.left = r.left - cr.left + container.scrollLeft + "px";
          mount.style.top = r.top - cr.top + container.scrollTop + "px";
        }
        mount.style.width = Math.max(2, Math.round(r.width)) + "px";
        mount.style.height = Math.max(2, Math.round(r.height)) + "px";
        if (root._afwGmMap) try {
          google.maps.event.trigger(root._afwGmMap, "resize");
        } catch (e2) {}
      }
      sync();
      root._afwGmRo = new ResizeObserver(sync);
      root._afwGmRo.observe(ph);
      var onRS = function () {
        sync();
      };
      window.addEventListener("resize", onRS);
      window.addEventListener("scroll", onRS, true);
      var scrollEls = afwMapScrollParents(ph);
      scrollEls.forEach(function (se) {
        se.addEventListener("scroll", onRS, { passive: true });
      });
      root._afwGmUnbind = function () {
        window.removeEventListener("resize", onRS);
        window.removeEventListener("scroll", onRS, true);
        scrollEls.forEach(function (se) {
          se.removeEventListener("scroll", onRS);
        });
      };
      var map = new google.maps.Map(mount, {
        center: { lat: 20, lng: 0 },
        zoom: 2,
        mapTypeControl: false,
        streetViewControl: false,
      });
      root._afwGmMap = map;
      var bounds = new google.maps.LatLngBounds();
      var hasPt = false;
      var info = new google.maps.InfoWindow();
      var googleBubbles = [];
      (markers || []).forEach(function (m) {
        var layers = bubbleLayersForMarker(m);
        layers.forEach(function (layer) {
          var center = { lat: layer.ll[0], lng: layer.ll[1] };
          var circle = new google.maps.Circle({
            center: center,
            radius: googleCircleRadiusM(layer.n, map.getZoom()),
            strokeColor: layer.stroke,
            strokeWeight: 2,
            fillColor: layer.fill,
            fillOpacity: 0.52,
            map: map,
          });
          var html = unlocoPopupHtml(m);
          circle.addListener("click", function (ev) {
            info.setContent(html);
            info.setPosition(ev.latLng);
            info.open(map);
          });
          googleBubbles.push({ circle: circle, n: layer.n });
          var b = circle.getBounds();
          if (b) {
            bounds.extend(b.getNorthEast());
            bounds.extend(b.getSouthWest());
            hasPt = true;
          }
        });
      });
      var applyGoogleZoom = function () {
        var z = map.getZoom();
        googleBubbles.forEach(function (row) {
          row.circle.setRadius(googleCircleRadiusM(row.n, z));
        });
      };
      map.addListener("zoom_changed", applyGoogleZoom);
      applyGoogleZoom();
      if (hasPt) map.fitBounds(bounds, 56);
      setTimeout(sync, 0);
      setTimeout(sync, 80);
      setTimeout(function () {
        try {
          google.maps.event.trigger(map, "resize");
          sync();
          if (hasPt) map.fitBounds(bounds, 56);
          applyGoogleZoom();
        } catch (e3) {}
      }, 350);
    } catch (e) {
      renderMapLeaflet(root, markers);
    }
  });
}
function renderMap(root, markers, mapRenderer) {
  var el = root.querySelector(".afw-hub-map");
  if (!el) return;
  clearMapEl(el);
  if (!markers || !markers.length) {
    el.innerHTML = "<div class=\"pad text-muted\">" + __("No UNLOCO locations with coordinates to display.") + "</div>";
    return;
  }
  if (useGoogleMaps(mapRenderer)) {
    frappe.call({
      method: "logistics.document_management.api.get_google_maps_api_key",
      callback: function (r) {
        var key = r.message && r.message.api_key;
        if (!key || String(key).length < 10) {
          renderMapLeaflet(root, markers);
          return;
        }
        renderMapGoogle(root, markers, key);
      },
      error: function () {
        renderMapLeaflet(root, markers);
      },
    });
    return;
  }
  renderMapLeaflet(root, markers);
}
function opsLinkDoctype(root) {
  if (!root || !root.getAttribute) return "Air Shipment";
  return (root.getAttribute("data-link-doctype") || "Air Shipment").trim();
}
function fillHeaderAndKpis(root, d) {
  var titleEl = root.querySelector(".afw-ops-page-title");
  if (titleEl) {
    var tnm = (d.company_name || d.company || "").trim();
    titleEl.textContent = tnm || "—";
  }
  var img = root.querySelector(".afw-ops-company-logo");
  var ph = root.querySelector(".afw-ops-logo-ph");
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
  var cluster = root.querySelector(".afw-ops-meta-cluster");
  if (cluster) {
    var cnt = (d.limits_applied && d.limits_applied.shipment_count) || 0;
    var lim = d.limits_applied && d.limits_applied.max_shipments;
    var ports = (d.unloco_markers || []).length;
    var shipSpan = lim != null && lim !== "" ? cnt + " / " + lim : String(cnt);
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
      frappe.utils.escape_html(userSpan) +
      "</span></div>" +
      '<div class="ab-meta-row"><i class="fa fa-plane"></i><span class="ab-meta-k">' +
      __("Shipments") +
      "</span><span>" +
      shipSpan +
      "</span></div>" +
      '<div class="ab-meta-row"><i class="fa fa-map-marker"></i><span class="ab-meta-k">' +
      __("Map ports") +
      "</span><span>" +
      ports +
      "</span></div></div>";
  }
  var kpis = root.querySelector(".afw-ops-kpis");
  if (kpis) {
    var s = d.alert_summary || {};
    var da = s.danger || 0;
    var wa = s.warning || 0;
    var inf = s.info || 0;
    var tot = (d.limits_applied && d.limits_applied.shipment_count) || 0;
    kpis.innerHTML =
      '<div class="header-item"><label>' +
      __("Critical") +
      "</label><span>" +
      da +
      "</span></div>" +
      '<div class="header-item"><label>' +
      __("Warnings") +
      "</label><span>" +
      wa +
      "</span></div>" +
      '<div class="header-item"><label>' +
      __("Information") +
      "</label><span>" +
      inf +
      "</span></div>" +
      '<div class="header-item"><label>' +
      __("UNLOCO on map") +
      "</label><span>" +
      (d.unloco_markers || []).length +
      "</span></div>";
    var ring = root.querySelector(".afw-ops-alert-ring");
    var rp = root.querySelector(".afw-ops-ring-pct");
    var rcap = root.querySelector(".afw-ops-ring-cap");
    if (ring) ring.style.setProperty("--ab-pct", tot > 0 ? "100" : "0");
    if (rp) rp.textContent = String(tot);
    if (rcap) rcap.textContent = __("shipments");
  }
  var tc = root.querySelector(".afw-ops-alerts-tab-count");
  if (tc) {
    var asum = d.alert_summary || {};
    var sum = (asum.danger || 0) + (asum.warning || 0) + (asum.info || 0);
    tc.textContent = "(" + sum + ")";
  }
}

function getJobStatusFilter(root) {
  var s = root.querySelector(".afw-ops-filter-status");
  return (s && s.value) || "ongoing";
}

function populateUserFilter(root, job_status_filter) {
  var sel = root.querySelector(".afw-ops-filter-user");
  if (!sel) return;
  var prev = sel.value;
  frappe.call({
    method: "logistics.air_freight.air_freight_operations_dashboard.get_air_freight_operations_filter_users",
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
      var pick = prev;
      if (!sel._afwOwnerTouched && !pick && frappe.session.user) {
        for (var j = 0; j < sel.options.length; j++) {
          if (sel.options[j].value === frappe.session.user) {
            pick = frappe.session.user;
            break;
          }
        }
      }
      var want = pick != null && pick !== undefined ? pick : "";
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
  root.querySelectorAll(".afw-ops-airline-cb:checked").forEach(function (cb) {
    if (cb.value) out.push(cb.value);
  });
  return out;
}

function updateAirlineSummary(root) {
  var sumEl = root.querySelector(".afw-ops-airline-summary");
  if (!sumEl) return;
  var cbs = root.querySelectorAll(".afw-ops-airline-cb");
  var n = cbs.length;
  var selN = 0;
  for (var i = 0; i < cbs.length; i++) {
    if (cbs[i].checked) selN++;
  }
  if (!n) {
    sumEl.textContent = __("No airlines");
    return;
  }
  if (!selN || selN === n) {
    sumEl.textContent = __("All airlines");
    return;
  }
  if (selN === 1) {
    for (var j = 0; j < cbs.length; j++) {
      if (cbs[j].checked) {
        var row = cbs[j].closest(".afw-ops-airline-cb-row");
        var sp = row && row.querySelector(".afw-ops-airline-lbl");
        sumEl.textContent = (sp && sp.textContent) || cbs[j].value;
        return;
      }
    }
  }
  sumEl.textContent = selN + " " + __("selected");
}

function bindAirlineDropdown(root) {
  if (root._afwAirlineUiBound) return;
  var wrap = root.querySelector(".afw-ops-airline-ms");
  var btn = root.querySelector(".afw-ops-airline-dd-toggle");
  if (!wrap || !btn) return;
  root._afwAirlineUiBound = true;
  btn.addEventListener("click", function (e) {
    e.stopPropagation();
    var open = wrap.classList.toggle("afw-ops-airline-dd-open");
    btn.setAttribute("aria-expanded", open ? "true" : "false");
  });
  if (!window._afwOpsAirlineDocClose) {
    window._afwOpsAirlineDocClose = true;
    document.addEventListener("click", function (e) {
      var opens = document.querySelectorAll(".afw-ops-airline-ms.afw-ops-airline-dd-open");
      for (var k = 0; k < opens.length; k++) {
        var w = opens[k];
        if (w.contains(e.target)) continue;
        w.classList.remove("afw-ops-airline-dd-open");
        var b = w.querySelector(".afw-ops-airline-dd-toggle");
        if (b) b.setAttribute("aria-expanded", "false");
      }
    });
  }
  root.addEventListener("change", function (e) {
    if (!e.target || !e.target.classList || !e.target.classList.contains("afw-ops-airline-cb")) return;
    updateAirlineSummary(root);
    refresh();
  });
}

function populateAirlineFilter(root, options, preserveValues) {
  var box = root.querySelector(".afw-ops-airline-checkboxes");
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
    lab.className = "afw-ops-airline-cb-row";
    var inp = document.createElement("input");
    inp.type = "checkbox";
    inp.className = "afw-ops-airline-cb";
    inp.value = v;
    if (want[v]) inp.checked = true;
    var sp = document.createElement("span");
    sp.className = "afw-ops-airline-lbl";
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

  var section = root.querySelector(".afw-ops-dash-alerts-section");
  if (section) {
    var icons = { danger: "fa-exclamation-circle", warning: "fa-exclamation-triangle", info: "fa-info-circle" };
    var groups = { danger: [], warning: [], info: [] };
    items.forEach(function (it) {
      var lvl = it.level === "danger" ? "danger" : it.level === "warning" ? "warning" : "info";
      var link = frappe.utils.get_form_link(opsLinkDoctype(root), it.shipment);
      var row =
        '<div class="dash-alert-item ' +
        lvl +
        '"><i class="fa ' +
        icons[lvl] +
        '"></i><span><a href="' +
        link +
        '">' +
        frappe.utils.escape_html(it.shipment) +
        "</a> — " +
        frappe.utils.escape_html(it.msg || "") +
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
        frappe.utils.escape_html(label) +
        "</span></div>" +
        '<div class="dash-alert-group-body">' +
        (bodyInner ||
          '<div class="text-muted small">' +
          __("Expand for details. Additional lines may exist beyond the loaded list.") +
          "</div>") +
        "</div></div>";
    });
    section.innerHTML =
      groupsHtml ||
      '<div class="text-muted small">' + __("No alerts for listed shipments.") + "</div>";
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

  var cardsHost = root.querySelector(".afw-ops-ops-alert-cards");
  if (cardsHost) {
    function oneCard(title, val, alertType) {
      return (
        '<div class="doc-alert-card doc-alert-card-' +
        alertType +
        '">' +
        '<div class="doc-alert-card-value">' +
        val +
        "</div>" +
        '<div class="doc-alert-card-title">' +
        title +
        "</div></div>"
      );
    }
    cardsHost.innerHTML = [
      oneCard(__("Critical"), danger, "danger"),
      oneCard(__("Warnings"), warning, "warning"),
      oneCard(__("Information"), info, "info"),
      oneCard(__("Shipments"), shipN, "success"),
      oneCard(__("Total"), total, "secondary"),
    ].join("");
  }
}
function refresh() {
  var root = root_element;
  var job_status_filter = getJobStatusFilter(root);
  var sel = root.querySelector(".afw-ops-filter-user");
  var filter_user = sel && sel.value ? sel.value : "";
  var prevAir = selectedAirlineCodes(root);
  var tr = root.querySelector(".afw-ops-filter-traffic");
  var traffic = tr && tr.value ? tr.value : "all";
  frappe.call({
    method: "logistics.air_freight.air_freight_operations_dashboard.get_air_freight_operations_dashboard",
    args: {
      job_status_filter: job_status_filter,
      filter_user: filter_user,
      traffic: traffic,
      airlines: prevAir.length ? JSON.stringify(prevAir) : "",
    },
    callback: function (r) {
      if (!r.message) return;
      var d = r.message;
      fillHeaderAndKpis(root, d);
      var ban = root.querySelector(".afw-ops-banner");
      var skip = d.skipped_unloco_no_coords || 0;
      if (ban) {
        if (skip > 0) {
          ban.style.display = "";
          ban.textContent =
            skip + " " + __("UNLOCO code(s) with shipments have no coordinates on the map.");
        } else {
          ban.style.display = "none";
          ban.textContent = "";
        }
      }
      populateAirlineFilter(root, d.airline_options || [], prevAir);
      root._afwLastMarkers = d.unloco_markers || [];
      root._afwLastRenderer = d.map_renderer || "";
      renderMap(root, root._afwLastMarkers, root._afwLastRenderer);
      renderAlerts(root, d.alert_summary || {}, d.alert_items || []);
    },
  });
}
var r = root_element;
r.querySelector(".afw-hub-refresh").addEventListener("click", refresh);
var st = r.querySelector(".afw-ops-filter-status");
if (st) {
  st.addEventListener("change", function () {
    populateUserFilter(root_element, getJobStatusFilter(root_element));
    refresh();
  });
}
var fu = r.querySelector(".afw-ops-filter-user");
if (fu) {
  fu.addEventListener("change", function () {
    fu._afwOwnerTouched = true;
    refresh();
  });
}
var trf = r.querySelector(".afw-ops-filter-traffic");
if (trf) {
  trf.addEventListener("change", refresh);
}
bindAirlineDropdown(root_element);
populateUserFilter(root_element, getJobStatusFilter(root_element));
refresh();
