// route: customs-operations
// title: Customs Operations

frappe.provide("logistics.customs_operations");

(function injectAfOpsMapPopupCss() {
  if (document.getElementById("af-ops-map-popup-css")) return;
  const st = document.createElement("style");
  st.id = "af-ops-map-popup-css";
  st.textContent =
    ".afw-hub-unloco-popup{box-sizing:border-box;min-width:10.5rem;max-width:18rem;padding-right:2.6rem;margin:0}" +
    ".afw-hub-popup-head{display:flex;flex-direction:row;justify-content:space-between;align-items:flex-start;gap:0.5rem;width:100%;margin:0 0 0.45rem 0}" +
    ".afw-hub-popup-hero{display:flex;flex-direction:column;align-items:flex-start;gap:0.15rem;min-width:0}" +
    ".afw-hub-popup-flag{font-size:2.1rem;line-height:1;flex-shrink:0;font-family:Segoe UI Emoji,Apple Color Emoji,Noto Color Emoji,sans-serif}" +
    ".afw-hub-popup-close-slot{flex-shrink:0;width:2.75rem;min-width:2.75rem;min-height:2rem;pointer-events:none}" +
    ".afw-hub-popup-code{font-size:1rem;font-weight:600;line-height:1.25;color:#212529}" +
    ".afw-hub-popup-stats{display:flex;flex-direction:column;gap:0.28rem}" +
    ".afw-hub-popup-stat{font-size:0.8125rem;line-height:1.35;color:#333}" +
    ".afw-hub-popup-stat strong{font-weight:600}";
  document.head.appendChild(st);
})();

frappe.pages["customs-operations"].on_page_load = function (wrapper) {
  logistics.customs_operations.page = new logistics.customs_operations.CustomsOperationsPage(wrapper);
};

(function () {
  class CustomsOperationsPage {
    constructor(wrapper) {
      this.wrapper = $(wrapper);
      this.page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __("Customs Operations"),
        single_column: true,
      });
      this.map = null;
      this._googleMap = null;
      this._layers = [];
      this._mapMarkers = [];
      this._mapRenderer = "";
      this._leafletZoomCleanup = null;
      this._owner_filter_touched = false;
      this.make_layout();
      this.bind_events();
      this._populate_owner_filter(() => this.refresh());
    }

    make_layout() {
      const $ui = $(`
        <div class="af-ops-dashboard">
          <div class="af-ops-toolbar form-inline">
            <button class="btn btn-default btn-xs" type="button" id="af-ops-refresh">
              <i class="fa fa-refresh"></i> ${__("Refresh")}
            </button>
            <span class="af-ops-filter-group">
              <span class="af-ops-filter-lbl">${__("Status")}</span>
              <select id="af-ops-filter-status" class="form-control input-xs">
                <option value="ongoing" selected>${__("Ongoing (no draft)")}</option>
                <option value="open">${__("Ongoing (incl. draft)")}</option>
                <option value="Draft">${__("Draft")}</option>
                <option value="Submitted">${__("Submitted")}</option>
                <option value="In Progress">${__("In Progress")}</option>
                <option value="Reopened">${__("Reopened")}</option>
                <option value="Completed">${__("Completed")}</option>
                <option value="Closed">${__("Closed")}</option>
                <option value="Cancelled">${__("Cancelled")}</option>
              </select>
            </span>
            <span class="af-ops-filter-group">
              <span class="af-ops-filter-lbl">${__("Traffic")}</span>
              <select id="af-ops-filter-traffic" class="form-control input-xs">
                <option value="all">${__("All")}</option>
                <option value="import">${__("Import")}</option>
                <option value="export">${__("Export")}</option>
                <option value="domestic">${__("Domestic")}</option>
              </select>
            </span>
            <span class="af-ops-filter-group">
              <span class="af-ops-filter-lbl">${__("Owner")}</span>
              <select id="af-ops-filter-user" class="form-control input-xs"></select>
            </span>
          </div>
          <div class="af-ops-banner alert alert-warning" id="af-ops-skip-banner" style="display:none;"></div>
          <div class="af-ops-grid">
            <div class="af-ops-map-wrap">
              <div class="af-ops-map-title">${__("UNLOCO heat map — filtered by company and selections")}</div>
              <div class="af-ops-map-host">
                <div id="af-ops-map" class="af-ops-map"></div>
              </div>
              <div class="text-muted small" id="af-ops-map-renderer"></div>
            </div>
            <div class="af-ops-alerts af-ops-alerts-booking-format">
              <div class="af-ops-panel-title">${__("Alerts and notifications")}</div>
              <div id="af-ops-dash-alerts-section" class="dash-alerts-section"></div>
              <div class="doc-alerts-cards-wrapper" style="margin-top: 12px;">
                <div id="af-ops-alert-cards" class="doc-alerts-cards"></div>
              </div>
            </div>
          </div>
        </div>
        <style>
          .af-ops-dashboard { padding: 0 0 12px; }
          .af-ops-toolbar {
            margin-bottom: 8px;
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 8px 12px;
            font-size: 12px;
          }
          .af-ops-filter-group { display: inline-flex; align-items: center; gap: 6px; }
          .af-ops-filter-group-airlines { align-items: center; }
          .af-ops-airline-ms { position: relative; min-width: 11rem; max-width: 18rem; }
          .af-ops-airline-dd-toggle {
            min-height: 1.85rem;
            padding: 0.15rem 0.45rem;
            font-size: 0.75rem;
            border-radius: 6px;
            box-shadow: none;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.35rem;
          }
          .af-ops-airline-dd-toggle .af-ops-airline-summary {
            flex: 1;
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            text-align: left;
            font-weight: 500;
            color: var(--text-color);
          }
          .af-ops-airline-dd-toggle::after {
            content: "";
            flex-shrink: 0;
            width: 0;
            height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid var(--text-muted);
            margin-top: 2px;
          }
          .af-ops-airline-ms.af-ops-airline-dd-open .af-ops-airline-dd-panel { display: block; }
          .af-ops-airline-dd-panel {
            display: none;
            position: absolute;
            left: 0;
            right: 0;
            top: calc(100% + 2px);
            z-index: 800;
            background: var(--fg-color);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12);
            max-height: 240px;
            overflow-y: auto;
            padding: 0.25rem 0;
          }
          .af-ops-airline-cb-row {
            display: flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.3rem 0.65rem;
            margin: 0;
            font-size: 0.75rem;
            font-weight: 500;
            color: var(--text-color);
            cursor: pointer;
          }
          .af-ops-airline-cb-row:hover { background: var(--fg-hover-color); }
          .af-ops-airline-cb-row input { margin: 0; flex-shrink: 0; }
          .af-ops-filter-lbl {
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: var(--text-muted);
          }
          #af-ops-filter-status { min-width: 10.5rem; max-width: 14rem; }
          #af-ops-filter-traffic { min-width: 7.5rem; max-width: 10rem; }
          #af-ops-filter-user { min-width: 11rem; max-width: 16rem; }
          .af-ops-grid {
            display: grid;
            grid-template-columns: minmax(280px, 1fr) minmax(220px, 320px);
            gap: 10px;
            align-items: start;
          }
          @media (max-width: 1100px) {
            .af-ops-grid { grid-template-columns: 1fr; }
          }
          .af-ops-map-wrap { min-width: 0; }
          .af-ops-map-host { position: relative; }
          .af-ops-map-title, .af-ops-panel-title {
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            margin-bottom: 4px;
          }
          .af-ops-map {
            height: 440px;
            width: 100%;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            background: var(--control-bg);
          }
          .doc-alerts-cards-wrapper { background: var(--control-bg); border: 1px solid var(--border-color); border-radius: 8px; padding: 16px; }
          .doc-alerts-cards { display: flex; flex-wrap: wrap; gap: 12px; align-items: stretch; }
          .doc-alert-card { min-width: 80px; flex: 1; background: var(--fg-color); border-radius: 6px; border: 1px solid var(--border-color); padding: 12px 16px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
          .doc-alert-card-value { font-size: 24px; font-weight: 700; line-height: 1.2; }
          .doc-alert-card-title { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px; font-weight: 600; }
          .doc-alert-card-warning .doc-alert-card-value { color: #856404; }
          .doc-alert-card-warning { border-left: 4px solid #ffc107; }
          .doc-alert-card-danger .doc-alert-card-value { color: #721c24; }
          .doc-alert-card-danger { border-left: 4px solid #dc3545; }
          .doc-alert-card-info .doc-alert-card-value { color: #0c5460; }
          .doc-alert-card-info { border-left: 4px solid #17a2b8; }
          .doc-alert-card-success .doc-alert-card-value { color: #155724; }
          .doc-alert-card-success { border-left: 4px solid #28a745; }
          .doc-alert-card-secondary .doc-alert-card-value { color: #383d41; }
          .doc-alert-card-secondary { border-left: 4px solid #6c757d; }
          .dash-alerts-section { margin-bottom: 16px; }
          .dash-alert-item { padding: 8px 12px; border-radius: 6px; margin-bottom: 6px; font-size: 12px; display: flex; align-items: flex-start; gap: 8px; }
          .dash-alert-item.danger { background: #f8d7da; color: #721c24; border-left: 4px solid #dc3545; }
          .dash-alert-item.warning { background: #fff3cd; color: #856404; border-left: 4px solid #ffc107; }
          .dash-alert-item.info { background: #d1ecf1; color: #0c5460; border-left: 4px solid #17a2b8; }
          .dash-alert-item i { margin-top: 1px; }
          .dash-alert-group { margin-bottom: 12px; border-radius: 6px; overflow: hidden; border: 1px solid rgba(0,0,0,0.08); }
          .dash-alert-group-header { padding: 8px 12px; font-size: 12px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 8px; user-select: none; }
          .dash-alert-group-header:hover { opacity: 0.9; }
          .dash-alert-group.dash-alert-group-danger .dash-alert-group-header { background: #f8d7da; color: #721c24; }
          .dash-alert-group.dash-alert-group-warning .dash-alert-group-header { background: #fff3cd; color: #856404; }
          .dash-alert-group.dash-alert-group-info .dash-alert-group-header { background: #d1ecf1; color: #0c5460; }
          .dash-alert-group-chevron { font-size: 10px; transition: transform 0.2s ease; }
          .dash-alert-group-body { padding: 6px 12px 12px; }
          .dash-alert-group.collapsed .dash-alert-group-body { display: none; }
        </style>
      `);
      this.page.main.append($ui);
    }

    bind_events() {
      this.page.main.on("click", "#af-ops-refresh", () => this.refresh());
      this.page.main.on("change", "#af-ops-filter-status", () => {
        this._populate_owner_filter(() => this.refresh());
      });
      this.page.main.on("change", "#af-ops-filter-traffic", () => this.refresh());
      this.page.main.on("change", "#af-ops-filter-user", () => {
        this._owner_filter_touched = true;
        this.refresh();
      });
      this._bind_airline_dropdown();
    }

    _bind_airline_dropdown() {
      /* No carrier filter for customs */
    }

    _update_airline_summary() {
      const $sum = this.page.main.find("#af-ops-airline-summary");
      const $cbs = this.page.main.find(".af-ops-airline-cb");
      const n = $cbs.length;
      const selN = $cbs.filter(":checked").length;
      if (!n) {
        $sum.text(__("No airlines"));
        return;
      }
      if (!selN || selN === n) {
        $sum.text(__("All airlines"));
        return;
      }
      if (selN === 1) {
        const $one = $cbs.filter(":checked").first();
        const txt = $one.closest(".af-ops-airline-cb-row").find(".af-ops-airline-lbl").text() || $one.val();
        $sum.text(txt);
        return;
      }
      $sum.text(`${selN} ${__("selected")}`);
    }

    _selected_airline_codes() {
      const out = [];
      this.page.main.find(".af-ops-airline-cb:checked").each(function () {
        const v = $(this).val();
        if (v) out.push(v);
      });
      return out;
    }

    _populate_owner_filter(done) {
      const job_status_filter = this.page.main.find("#af-ops-filter-status").val() || "ongoing";
      const $sel = this.page.main.find("#af-ops-filter-user");
      const prev = $sel.val();
      frappe.call({
        method: "logistics.customs.customs_operations_dashboard.get_customs_operations_filter_users",
        args: { job_status_filter },
        callback: (r) => {
          const rows = r.message || [];
          $sel.empty();
          rows.forEach((row) => {
            $("<option></option>").attr("value", row.value || "").text(row.label || row.value || "").appendTo($sel);
          });
          let pick = prev;
          if (
            !this._owner_filter_touched &&
            (pick === null || pick === undefined || pick === "")
          ) {
            const me = frappe.session.user;
            if (
              me &&
              $sel.find("option").filter(function () {
                return $(this).attr("value") === me;
              }).length
            ) {
              pick = me;
            }
          }
          const want = pick != null && pick !== undefined ? pick : "";
          $sel.val(want);
          if (typeof done === "function") done();
        },
      });
    }

    _populate_airline_options(options, preserve) {
      const $box = this.page.main.find("#af-ops-airline-checkboxes");
      const want = {};
      (preserve || []).forEach((v) => {
        want[v] = true;
      });
      $box.empty();
      (options || []).forEach((row) => {
        const v = row.value || "";
        const lbl = row.label || v;
        const $lab = $("<label class=\"af-ops-airline-cb-row\"></label>");
        const $inp = $("<input type=\"checkbox\" class=\"af-ops-airline-cb\" />").attr("value", v);
        if (want[v]) $inp.prop("checked", true);
        const $sp = $("<span class=\"af-ops-airline-lbl\"></span>").text(lbl);
        $lab.append($inp, $sp);
        $box.append($lab);
      });
      this._update_airline_summary();
    }

    _clear_map() {
      const el = this.page.main.find("#af-ops-map")[0];
      if (typeof this._leafletZoomCleanup === "function") {
        try {
          this._leafletZoomCleanup();
        } catch (e) {
          /* ignore */
        }
        this._leafletZoomCleanup = null;
      }
      if (this.map) {
        try {
          this.map.remove();
        } catch (e) {
          /* ignore */
        }
        this.map = null;
      }
      if (this._googleMap && window.google && google.maps && google.maps.event) {
        try {
          google.maps.event.clearListeners(this._googleMap, "zoom_changed");
        } catch (e) {
          /* ignore */
        }
      }
      this._googleMap = null;
      this._layers = [];
      if (el) el.innerHTML = "";
    }

    _ensure_leaflet(done) {
      if (window.L) {
        done();
        return;
      }
      if (!document.querySelector("link[data-af-leaflet-css]")) {
        const c = document.createElement("link");
        c.rel = "stylesheet";
        c.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
        c.setAttribute("data-af-leaflet-css", "1");
        document.head.appendChild(c);
      }
      const s = document.createElement("script");
      s.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
      s.onload = () => done();
      document.head.appendChild(s);
    }

    _use_google_maps(mapRenderer) {
      return String(mapRenderer || "")
        .toLowerCase()
        .trim() === "google maps";
    }

    _ensure_google_maps(apiKey, done) {
      if (window.google && window.google.maps) {
        done();
        return;
      }
      const id = "af-ops-gmaps-js";
      if (document.getElementById(id)) {
        const check = () => {
          if (window.google && window.google.maps) done();
          else setTimeout(check, 50);
        };
        check();
        return;
      }
      const s = document.createElement("script");
      s.id = id;
      s.async = true;
      s.src = "https://maps.googleapis.com/maps/api/js?key=" + encodeURIComponent(apiKey) + "&libraries=geometry";
      s.onload = () => done();
      s.onerror = () => done(new Error("gmaps_load"));
      document.head.appendChild(s);
    }

    _flag_emoji_from_country_code(cc) {
      const s = String(cc || "")
        .trim()
        .toUpperCase();
      if (s.length !== 2) return "";
      const a = s.charCodeAt(0);
      const b = s.charCodeAt(1);
      if (a < 65 || a > 90 || b < 65 || b > 90) return "";
      return String.fromCharCode(a + 127397) + String.fromCharCode(b + 127397);
    }

    _unloco_popup_html(m) {
      const u = frappe.utils.escape_html(m.unloco || "");
      const imp = m.import_count || 0;
      const exp = m.export_count || 0;
      const dom = m.domestic_count || 0;
      const flagRaw = (m.flag && String(m.flag)) || this._flag_emoji_from_country_code(m.country_code);
      const flagDisp = flagRaw ? frappe.utils.escape_html(flagRaw) : "";
      const flagHtml = flagDisp ? `<span class="afw-hub-popup-flag" aria-hidden="true">${flagDisp}</span>` : "";
      return (
        `<div class="afw-hub-unloco-popup">` +
        `<div class="afw-hub-popup-head">` +
        `<div class="afw-hub-popup-hero">` +
        flagHtml +
        `<div class="afw-hub-popup-code"><strong>${u}</strong></div></div>` +
        `<span class="afw-hub-popup-close-slot" aria-hidden="true"></span></div>` +
        `<div class="afw-hub-popup-stats">` +
        `<div class="afw-hub-popup-stat"><strong>${__("International import")} (${__("Origin")}):</strong> <strong>${imp}</strong></div>` +
        `<div class="afw-hub-popup-stat"><strong>${__("International export")} (${__("Destination")}):</strong> <strong>${exp}</strong></div>` +
        `<div class="afw-hub-popup-stat"><strong>${__("Domestic")} (${__("Same country")}):</strong> <strong>${dom}</strong></div></div></div>`
      );
    }

    _base_radius_px(n) {
      const c = Math.max(0, Number(n) || 0);
      return Math.min(72, 18 + Math.sqrt(c) * 7);
    }

    _leaflet_zoom_radius_factor(zoom) {
      const z = Number(zoom);
      const zz = Number.isFinite(z) ? z : 3;
      return Math.max(0.7, Math.min(3.5, Math.pow(1.38, 7.3 - zz)));
    }

    /** Pixel radius scaled by map zoom (larger when zoomed out). */
    _radius_from_count(n, zoom) {
      return this._base_radius_px(n) * this._leaflet_zoom_radius_factor(zoom);
    }

    _google_base_radius_m(n) {
      const c = Math.max(0, Number(n) || 0);
      return Math.min(1600000, 72000 + 32000 * Math.sqrt(c));
    }

    _google_zoom_radius_factor(zoom) {
      const z = Number(zoom);
      const zz = Number.isFinite(z) ? z : 3;
      return Math.max(0.58, Math.min(3.6, Math.pow(1.37, 7.2 - zz)));
    }

    _google_circle_radius_m(n, zoom) {
      return this._google_base_radius_m(n) * this._google_zoom_radius_factor(zoom);
    }

    /** One bubble per UNLOCO; server applies traffic filter to counts. */
    _bubble_layers_for_marker(m) {
      const lat = m.lat;
      const lon = m.lon;
      if (lat == null || lon == null) return [];
      const imp = m.import_count || 0;
      const exp = m.export_count || 0;
      const dom = m.domestic_count || 0;
      const stroke = "#1e40af";
      const fill = "#3b82f6";
      const n = imp + exp + dom;
      if (n <= 0) return [];
      return [{ n, stroke, fill, ll: [lat, lon] }];
    }

    _render_map_leaflet(markers) {
      const el = this.page.main.find("#af-ops-map")[0];
      if (!el) return;
      this._ensure_leaflet(() => {
        el.innerHTML = "";
        const map = L.map(el).setView([20, 0], 2);
        this.map = map;
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
          attribution: "© OpenStreetMap",
        }).addTo(map);
        const bounds = [];
        const leafletBubbles = [];
        (markers || []).forEach((m) => {
          const layers = this._bubble_layers_for_marker(m);
          layers.forEach((layer) => {
            const cm = L.circleMarker(layer.ll, {
              radius: this._radius_from_count(layer.n, map.getZoom()),
              color: layer.stroke,
              fillColor: layer.fill,
              fillOpacity: 0.55,
              weight: 2,
            }).addTo(map);
            cm.bindPopup(this._unloco_popup_html(m));
            leafletBubbles.push({ cm, count: layer.n });
            bounds.push(layer.ll);
          });
        });
        const applyLeafletZoom = () => {
          const z = map.getZoom();
          leafletBubbles.forEach(({ cm, count }) => {
            cm.setRadius(this._radius_from_count(count, z));
          });
        };
        map.on("zoomend", applyLeafletZoom);
        this._leafletZoomCleanup = () => {
          map.off("zoomend", applyLeafletZoom);
        };
        applyLeafletZoom();
        if (bounds.length >= 2) {
          map.fitBounds(bounds, { padding: [40, 40], maxZoom: 8 });
        } else if (bounds.length === 1) {
          map.setView(bounds[0], 6);
        }
        setTimeout(() => {
          try {
            map.invalidateSize();
            applyLeafletZoom();
          } catch (e) {
            /* ignore */
          }
        }, 200);
      });
    }

    _render_map_google(markers, apiKey) {
      const el = this.page.main.find("#af-ops-map")[0];
      if (!el) return;
      el.innerHTML = "";
      this._ensure_google_maps(apiKey, (err) => {
        if (err || !window.google || !window.google.maps) {
          this._render_map_leaflet(markers);
          return;
        }
        try {
          const map = new google.maps.Map(el, {
            center: { lat: 20, lng: 0 },
            zoom: 2,
            mapTypeControl: false,
            streetViewControl: false,
          });
          this._googleMap = map;
          const bounds = new google.maps.LatLngBounds();
          let hasPt = false;
          const info = new google.maps.InfoWindow();
          const htmlFor = (m) => this._unloco_popup_html(m);
          const googleBubbles = [];
          (markers || []).forEach((m) => {
            const layers = this._bubble_layers_for_marker(m);
            layers.forEach((layer) => {
              const center = { lat: layer.ll[0], lng: layer.ll[1] };
              const circle = new google.maps.Circle({
                center,
                radius: this._google_circle_radius_m(layer.n, map.getZoom()),
                strokeColor: layer.stroke,
                strokeWeight: 2,
                fillColor: layer.fill,
                fillOpacity: 0.52,
                map,
              });
              const html = htmlFor(m);
              circle.addListener("click", (ev) => {
                info.setContent(html);
                info.setPosition(ev.latLng);
                info.open(map);
              });
              googleBubbles.push({ circle, n: layer.n });
              const b = circle.getBounds();
              if (b) {
                bounds.extend(b.getNorthEast());
                bounds.extend(b.getSouthWest());
                hasPt = true;
              }
            });
          });
          const applyGoogleZoom = () => {
            const z = map.getZoom();
            googleBubbles.forEach(({ circle, n }) => {
              circle.setRadius(this._google_circle_radius_m(n, z));
            });
          };
          map.addListener("zoom_changed", applyGoogleZoom);
          applyGoogleZoom();
          if (hasPt) {
            map.fitBounds(bounds, 56);
          }
          setTimeout(() => {
            try {
              google.maps.event.trigger(map, "resize");
              if (hasPt) map.fitBounds(bounds, 56);
              applyGoogleZoom();
            } catch (e) {
              /* ignore */
            }
          }, 200);
        } catch (e) {
          this._render_map_leaflet(markers);
        }
      });
    }

    _render_map(markers, mapRenderer) {
      const el = this.page.main.find("#af-ops-map")[0];
      if (!el) return;
      this._clear_map();
      if (!markers || !markers.length) {
        el.innerHTML = `<div class="pad-md text-muted">${__("No UNLOCO locations with coordinates to display.")}</div>`;
        return;
      }
      if (this._use_google_maps(mapRenderer)) {
        frappe.call({
          method: "logistics.document_management.api.get_google_maps_api_key",
          callback: (r) => {
            const key = r.message && r.message.api_key;
            if (!key || String(key).length < 10) {
              this._render_map_leaflet(markers);
              return;
            }
            this._render_map_google(markers, key);
          },
          error: () => this._render_map_leaflet(markers),
        });
        return;
      }
      this._render_map_leaflet(markers);
    }

    _render_alerts(summary, items) {
      summary = summary || {};
      items = items || [];
      const danger = summary.danger || 0;
      const warning = summary.warning || 0;
      const info = summary.info || 0;
      const total = danger + warning + info;
      const shipSeen = {};
      items.forEach((it) => {
        if (it.shipment) shipSeen[it.shipment] = true;
      });
      const shipN = Object.keys(shipSeen).length;

      const icons = { danger: "fa-exclamation-circle", warning: "fa-exclamation-triangle", info: "fa-info-circle" };
      const groups = { danger: [], warning: [], info: [] };
      items.forEach((it) => {
        const lvl = it.level === "danger" ? "danger" : it.level === "warning" ? "warning" : "info";
        const link = frappe.utils.get_form_link("Declaration", it.shipment);
        const row =
          `<div class="dash-alert-item ${lvl}"><i class="fa ${icons[lvl]}"></i><span>` +
          `<a href="${link}">${frappe.utils.escape_html(it.shipment)}</a> — ${frappe.utils.escape_html(it.msg || "")}</span></div>`;
        groups[lvl].push(row);
      });
      const order = ["danger", "warning", "info"];
      const labels = {
        danger: __("There are %s critical alerts"),
        warning: __("There are %s warnings"),
        info: __("There are %s information alerts"),
      };
      const counts = { danger, warning, info };
      let groupsHtml = "";
      order.forEach((level) => {
        const cnt = counts[level];
        if (!cnt) return;
        const label = (labels[level] || "").replace("%s", String(cnt));
        const bodyInner = groups[level].join("");
        groupsHtml +=
          `<div class="dash-alert-group dash-alert-group-${level} collapsed">` +
          `<div class="dash-alert-group-header" data-level="${level}">` +
          `<i class="fa fa-chevron-right dash-alert-group-chevron"></i>` +
          `<span class="dash-alert-group-title">${frappe.utils.escape_html(label)}</span></div>` +
          `<div class="dash-alert-group-body">` +
          (bodyInner ||
            `<div class="text-muted small">${__("Expand for details. Additional lines may exist beyond the loaded list.")}</div>`) +
          `</div></div>`;
      });
      const $section = this.page.main.find("#af-ops-dash-alerts-section");
      $section.html(
        groupsHtml || `<div class="text-muted small">${__("No alerts for listed shipments.")}</div>`
      );
      $section.find(".dash-alert-group-header").off("click").on("click", function () {
        const $h = $(this);
        const $g = $h.closest(".dash-alert-group");
        const collapsed = $g.toggleClass("collapsed").hasClass("collapsed");
        const $chev = $h.find(".dash-alert-group-chevron");
        $chev.removeClass("fa-chevron-right fa-chevron-down");
        $chev.addClass(collapsed ? "fa-chevron-right" : "fa-chevron-down");
      });

      const oneCard = (title, val, alertType) =>
        `<div class="doc-alert-card doc-alert-card-${alertType}">` +
        `<div class="doc-alert-card-value">${val}</div>` +
        `<div class="doc-alert-card-title">${title}</div></div>`;
      this.page.main.find("#af-ops-alert-cards").html(
        [
          oneCard(__("Critical"), danger, "danger"),
          oneCard(__("Warnings"), warning, "warning"),
          oneCard(__("Information"), info, "info"),
          oneCard(__("Declarations"), shipN, "success"),
          oneCard(__("Total"), total, "secondary"),
        ].join("")
      );
    }

    refresh() {
      const job_status_filter = this.page.main.find("#af-ops-filter-status").val() || "ongoing";
      const filter_user = this.page.main.find("#af-ops-filter-user").val() || "";
      const traffic = this.page.main.find("#af-ops-filter-traffic").val() || "all";
      const prevAir = this._selected_airline_codes();
      this.page.main.find("#af-ops-refresh").prop("disabled", true);
      frappe.call({
        method: "logistics.customs.customs_operations_dashboard.get_customs_operations_dashboard",
        args: {
          job_status_filter,
          filter_user,
          traffic,
          airlines: prevAir.length ? JSON.stringify(prevAir) : "",
        },
        callback: (r) => {
          this.page.main.find("#af-ops-refresh").prop("disabled", false);
          if (!r.message) return;
          const d = r.message;
          this.page.main.find("#af-ops-map-renderer").text("");
          const skip = d.skipped_unloco_no_coords || 0;
          const $ban = this.page.main.find("#af-ops-skip-banner");
          if (skip > 0) {
            $ban
              .show()
              .text(
                __("{0} UNLOCO code(s) with shipments have no coordinates on the map.", [String(skip)])
              );
          } else {
            $ban.hide().text("");
          }
          this._populate_airline_options(d.airline_options || [], prevAir);
          this._mapMarkers = d.unloco_markers || [];
          this._mapRenderer = d.map_renderer || "";
          this._render_map(this._mapMarkers, this._mapRenderer);
          this._render_alerts(d.alert_summary || {}, d.alert_items || []);
        },
        error: () => {
          this.page.main.find("#af-ops-refresh").prop("disabled", false);
        },
      });
    }
  }

  logistics.customs_operations.CustomsOperationsPage = CustomsOperationsPage;
})();
