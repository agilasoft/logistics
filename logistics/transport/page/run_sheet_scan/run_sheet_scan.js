// route: run-sheet-scan
// title: Run Sheet Scan (Offline-ready, no PWA/SW)

frappe.provide("logistics.run_sheet_scan");

frappe.pages["run-sheet-scan"].on_page_load = function (wrapper) {
  new logistics.run_sheet_scan.RunSheetScanPage(wrapper);
};

(function () {
  // -----------------------------
  // Resilient storage (IndexedDB with optional localStorage shadow)
  // -----------------------------
  const DB_NAME = "rss_offline_v1";
  const DB_STORE = "kv";

  // Keys
  const LS_Q    = "rss:queue:v1";               // pending updates [{ id, rs, name, updates, ts }]
  const LS_RS   = (rs) => `rss:cache:${rs}:v1`;  // cached run sheet + legs
  const LS_IDX  = "rss:index:v1";                // list of cached run sheet ids [{id, at}]
  const LS_LAST = "rss:last_rs:v1";              // last successfully opened run sheet id

  function idbOpen() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, 1);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains(DB_STORE)) db.createObjectStore(DB_STORE);
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }
  function idbTx(db, mode = "readonly") { return db.transaction(DB_STORE, mode).objectStore(DB_STORE); }
  async function idbGet(key) {
    const db = await idbOpen();
    return new Promise((resolve, reject) => {
      const req = idbTx(db).get(key);
      req.onsuccess = () => resolve(req.result ?? null);
      req.onerror = () => reject(req.error);
    });
  }
  async function idbSet(key, val) {
    const db = await idbOpen();
    return new Promise((resolve, reject) => {
      const req = idbTx(db, "readwrite").put(val, key);
      req.onsuccess = () => resolve(true);
      req.onerror = () => reject(req.error);
    });
  }
  async function idbDel(key) {
    const db = await idbOpen();
    return new Promise((resolve, reject) => {
      const req = idbTx(db, "readwrite").delete(key);
      req.onsuccess = () => resolve(true);
      req.onerror = () => reject(req.error);
    });
  }

  // Shadow localStorage (best-effort only)
  function lsSetShadow(key, val) { try { localStorage.setItem(key, JSON.stringify(val)); } catch {} }
  function lsGetShadow(key)      { try { const v = localStorage.getItem(key); return v ? JSON.parse(v) : null; } catch { return null; } }
  function lsDelShadow(key)      { try { localStorage.removeItem(key); } catch {} }

  // Unified async KV
  async function jget(key, fallback = null) {
    const shadow = lsGetShadow(key);
    if (shadow !== null && shadow !== undefined) return shadow;
    const v = await idbGet(key);
    return (v === undefined || v === null) ? fallback : v;
  }
  async function jset(key, val) { await idbSet(key, val); lsSetShadow(key, val); }
  async function jdel(key)      { await idbDel(key); lsDelShadow(key); }

  // Utils
  function nowISO() { return frappe.datetime.now_datetime(); }
  function uid() { return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`; }

  // Queue helpers
  async function readQueue() { return await jget(LS_Q, []); }
  async function writeQueue(arr) { await jset(LS_Q, Array.isArray(arr) ? arr : []); }
  async function enqueue(op) { const q = await readQueue(); q.push({ id: uid(), ts: Date.now(), ...op }); await writeQueue(q); }
  async function dequeueById(id) { const q = (await readQueue()).filter((x) => x.id !== id); await writeQueue(q); }

  // Cache/index helpers
  async function indexAdd(rs) {
    const idx = await jget(LS_IDX, []);
    if (!idx.find((x) => x.id === rs)) idx.push({ id: rs, at: Date.now() });
    await jset(LS_IDX, idx);
  }
  async function indexList() { return await jget(LS_IDX, []); }
  async function cacheSet(rs, payload) { await jset(LS_RS(rs), { cached_at: Date.now(), ...payload }); await indexAdd(rs); }
  async function cacheGet(rs) { return await jget(LS_RS(rs), null); }
  async function cacheUpdateLegFields(rs, legName, updates) {
    const cache = await cacheGet(rs);
    if (!cache) return;
    const leg = (cache.legs || []).find((x) => x.name === legName);
    if (!leg) return;
    Object.assign(leg, updates || {});
    await cacheSet(rs, cache);
  }

  // Remember last-opened RS
  async function rememberLastRS(rs) { if (!rs) return; await jset(LS_LAST, { id: rs, at: Date.now() }); }
  async function getLastRS() { const o = await jget(LS_LAST, null); return o && o.id ? o.id : null; }

  // ---------------------------------------
  // Number helpers
  // ---------------------------------------
  const toFloat = (v, def = 0) => { const n = Number(v); return Number.isFinite(n) ? n : def; };
  const fmtNum = (v, precision = 2) => { const n = toFloat(v, 0); try { return frappe.format(n, { fieldtype: "Float", precision }); } catch { return n.toFixed(precision); } };

  // ---------------------------------------
  // Geo helpers
  // ---------------------------------------
  function parseJSONSafe(v) { try { return typeof v === "string" ? JSON.parse(v) : v; } catch { return null; } }
  function isFiniteNum(n) { return typeof n === "number" && isFinite(n); }
  function extractLatLonFromGeo(geo) {
    if (!geo) return null;
    if (typeof geo === "object" && isFiniteNum(geo.lat) && isFiniteNum(geo.lng)) return { lat: Number(geo.lat), lon: Number(geo.lng) };
    if (geo && geo.type === "FeatureCollection" && Array.isArray(geo.features)) { for (const f of geo.features) { const r = extractLatLonFromGeo(f); if (r) return r; } return null; }
    if (geo && geo.type === "Feature" && geo.geometry) return extractLatLonFromGeo(geo.geometry);
    if (geo && geo.type === "Point" && Array.isArray(geo.coordinates) && geo.coordinates.length >= 2) {
      const [lon, lat] = geo.coordinates; if (isFiniteNum(lat) && isFiniteNum(lon)) return { lat: Number(lat), lon: Number(lon) };
    }
    return null;
  }
  async function getAddressLatLon(addrname) {
    if (!addrname) return null;
    try {
      const d = await frappe.db.get_doc("Address", addrname);
      const geo = d?.custom_geolocation ? parseJSONSafe(d.custom_geolocation) : null;
      const pt = extractLatLonFromGeo(geo); if (pt) return pt;
      const lat = d.custom_latitude ?? d.latitude; const lon = d.custom_longitude ?? d.longitude;
      if (isFiniteNum(Number(lat)) && isFiniteNum(Number(lon))) return { lat: Number(lat), lon: Number(lon) };
    } catch {}
    return null;
  }

  // ---------------------------------------
  // Error/HTML/session helpers for sync
  // ---------------------------------------
  function isHTMLResponse(xhr) { try { const ct = xhr && xhr.getResponseHeader && xhr.getResponseHeader("content-type"); return ct && ct.includes("text/html"); } catch { return false; } }
  function extractTitleFromHTML(html) { try { const m = String(html || "").match(/<title[^>]*>([^<]*)<\/title>/i); return m ? m[1].trim() : null; } catch { return null; } }
  function likelySessionIssue(xhr) {
    if (!xhr) return false;
    const status = xhr.status;
    if (status === 401 || status === 403) return true;
    if (isHTMLResponse(xhr)) {
      const title = extractTitleFromHTML(xhr.responseText || "");
      return /login|session|signin|forbidden/i.test((title || "")) || /login/i.test(xhr.responseText || "");
    }
    return false;
  }
  function sleep(ms){ return new Promise(res=>setTimeout(res, ms)); }

  // ------------------------------------------------
  // The Page class (UI + online/offline + syncing)
  // ------------------------------------------------
  class RunSheetScanPage {
    constructor(wrapper) {
      this.wrapper = $(wrapper);
      this.page = frappe.ui.make_app_page({ parent: wrapper, title: __("Run Sheet Scan"), single_column: true });
      this.state = { rs: null, doc: null, legs: [], online: navigator.onLine, syncing: false };
      this.make_layout();
      this.bind_events();

      // Suppress Frappe "No internet" toast on this page
      this._orig_show_alert = frappe.show_alert;
      frappe.show_alert = (opts, seconds) => {
        const msg = typeof opts === "string" ? opts : (opts && opts.message);
        const onThisPage = (frappe.get_route && frappe.get_route()[0] === "run-sheet-scan");
        if (onThisPage && msg && /no internet/i.test(String(msg))) return null;
        return this._orig_show_alert.call(frappe, opts, seconds);
      };
      frappe.router.on("change", () => {
        if (this._orig_show_alert) { frappe.show_alert = this._orig_show_alert; this._orig_show_alert = null; }
      });

      // Restore view (route → cache → last_rs)
      this.robust_restore();

      this.update_status();
      window.addEventListener("online", () => { this.state.online = true; this.update_status(); this.try_sync_queue(); });
      window.addEventListener("offline", () => { this.state.online = false; this.update_status(); });
    }

    // ---------------- UI ----------------
    make_layout() {
      const $ui = $(`
        <div class="rss space-y-4">
          <div class="card">
            <div class="card-body" style="padding:12px;">
              <div class="rss-bar">
                <button class="btn btn-sm btn-primary" id="rss-scan"><i class="fa fa-qrcode"></i> ${__("Scan Run Sheet")}</button>
                <input type="text" class="form-control input-sm" id="rss-input" placeholder="${__("Enter or scan Run Sheet (e.g., RS-00000123)")}">
                <button class="btn btn-sm btn-default" id="rss-load">${__("Load")}</button>
                <a class="btn btn-sm btn-default" id="rss-open">${__("Open Document")}</a>
                <div class="rss-right">
                  <span id="rss-status" class="badge"></span>
                  <button class="btn btn-sm btn-default" id="rss-sync">${__("Sync Now")}</button>
                  <button class="btn btn-sm btn-default" id="rss-clear-cache">${__("Clear Cache")}</button>
                  <div class="dropdown">
                    <button class="btn btn-sm btn-default dropdown-toggle" data-toggle="dropdown">${__("Offline Cache")}</button>
                    <div class="dropdown-menu dropdown-menu-right" id="rss-cache-list"></div>
                  </div>
                </div>
              </div>
              <div id="rss-head" class="text-muted" style="margin-top:8px;"></div>
              <div id="rss-reauth" class="alert alert-warning" style="display:none; margin-top:8px;">
                <strong>${__("Authentication needed")}</strong> — ${__("Please sign in again to sync your offline actions.")}
                <a class="btn btn-xs btn-primary" style="margin-left:8px;" id="rss-login">${__("Open Login")}</a>
              </div>
            </div>
          </div>

          <div class="card">
            <div class="card-header"><strong>${__("Legs")}</strong></div>
            <div class="card-body" style="padding:12px;">
              <div id="rss-legs"></div>
            </div>
          </div>

          <!-- Signature Dialog -->
          <div class="modal fade" id="rss-signature-modal" tabindex="-1" role="dialog">
            <div class="modal-dialog modal-lg" role="document">
              <div class="modal-content">
                <div class="modal-header">
                  <h4 class="modal-title">${__("Sign ePOD")}</h4>
                  <button type="button" class="close" data-dismiss="modal">&times;</button>
                </div>
                <div class="modal-body">
                  <div class="signature-container">
                    <div class="signature-header">
                      <label>${__("Signature")}:</label>
                      <button type="button" class="btn btn-sm btn-default" id="rss-clear-signature">${__("Clear")}</button>
                    </div>
                    <canvas id="rss-signature-canvas" width="600" height="200" style="border: 1px solid #ccc; cursor: crosshair; max-width: 100%; height: auto;"></canvas>
                    <div class="signature-info" style="margin-top: 10px;">
                      <div class="form-group">
                        <label>${__("Signed By")}:</label>
                        <input type="text" class="form-control" id="rss-signed-by" placeholder="${__("Enter name")}" required>
                      </div>
                      <div class="form-group">
                        <label>${__("Date Signed")}:</label>
                        <input type="datetime-local" class="form-control" id="rss-date-signed" required>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="modal-footer">
                  <button type="button" class="btn btn-default" data-dismiss="modal">${__("Cancel")}</button>
                  <button type="button" class="btn btn-primary" id="rss-save-signature">${__("Save Signature")}</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      `);

      this.page.body.append($ui);
      this.page.body.append(`
        <style>
          .rss .rss-bar { display:flex; gap:6px; flex-wrap:wrap; align-items:center; }
          .rss .rss-bar #rss-input{ min-width:220px; max-width:340px; }
          .rss .rss-bar .rss-right{ margin-left:auto; display:flex; gap:6px; align-items:center; }
          .rss .badge{ background:#e5e7eb; color:#111827; border-radius:10px; padding:4px 8px; font-size:12px; }
          .rss .badge.online{ background:#dcfce7; color:#065f46; }
          .rss .badge.offline{ background:#fee2e2; color:#991b1b; }
          .rss .leg-grid{ display:grid; gap:10px; }
          .rss .leg-card{ border:1px solid var(--border-color,#e5e7eb); border-radius:12px; padding:10px; background:#fff; box-shadow:0 1px 0 rgba(0,0,0,0.02); }
          .rss .leg-main{ display:flex; justify-content:space-between; gap:8px; align-items:center; }
          .rss .leg-name{ font-weight:600; }
          .rss .leg-desc{ color:#6b7280; font-size:12px; margin-top:2px; }
          .rss .leg-actions{ display:flex; gap:6px; flex-wrap:wrap; }
          .rss .leg-actions .btn{ min-width:92px; flex:1 1 auto; }
          @media (max-width: 768px) {
            .rss .leg-actions{ flex-direction:column; gap:4px; }
            .rss .leg-actions .btn{ min-width:auto; width:100%; }
            .rss .leg-main{ flex-direction:column; align-items:stretch; }
            .rss .leg-actions{ margin-top:8px; }
          }
          .rss .leg-meta{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:6px; margin-top:8px; font-size:12px; color:#374151; }
          .rss .leg-meta label{ font-weight:600; margin-right:6px; }
          .rss .leg-status{ font-weight:600; text-transform:uppercase; }
          .rss .status-open{ color:#6b7280; }
          .rss .status-assigned{ color:#3b82f6; }
          .rss .status-started{ color:#f59e0b; }
          .rss .status-completed{ color:#10b981; }
          .rss .status-billed{ color:#8b5cf6; }
          .rss .unsynced{ background:#fff7ed; color:#9a3412; border:1px dashed #fdba74; padding:1px 6px; border-radius:999px; font-size:11px; }
          .rss .btn[disabled]{ opacity:.6; pointer-events:none; }
          .signature-container{ text-align: center; }
          .signature-header{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
          .signature-header label{ font-weight: 600; margin: 0; }
          #rss-signature-canvas{ background: white; }
          .signature-info{ text-align: left; }
          .signature-info .form-group{ margin-bottom: 10px; }
          .signature-info label{ font-weight: 600; margin-bottom: 5px; display: block; }
          @media (max-width: 768px) {
            .signature-header{ flex-direction: column; gap: 8px; align-items: stretch; }
            .signature-header label{ text-align: left; }
            #rss-signature-canvas{ width: 100%; height: 150px; }
            .modal-dialog{ margin: 10px; }
            .modal-body{ padding: 15px; }
          }
        </style>
      `);

      // refs
      this.$input  = $ui.find("#rss-input");
      this.$scan   = $ui.find("#rss-scan");
      this.$load   = $ui.find("#rss-load");
      this.$open   = $ui.find("#rss-open");
      this.$head   = $ui.find("#rss-head");
      this.$legs   = $ui.find("#rss-legs");
      this.$status = $ui.find("#rss-status");
      this.$sync   = $ui.find("#rss-sync");
      this.$clear  = $ui.find("#rss-clear-cache");
      this.$cache  = $ui.find("#rss-cache-list");
      this.$reauth = $ui.find("#rss-reauth");

      this.$reauth.find("#rss-login").on("click", () => window.open("/login", "_blank", "noopener"));
    }

    bind_events() {
      this.$scan.on("click", async () => {
        const code = await this.scan_barcode();
        if (!code) return;
        const name = this.extract_rs_name(code);
        this.$input.val(name);
        await this.load_run_sheet(name);
      });

      this.$load.on("click", async () => {
        const name = this.extract_rs_name(this.$input.val());
        if (!name) return frappe.show_alert({ message: __("Enter a Run Sheet ID"), indicator: "orange" });
        await this.load_run_sheet(name);
      });

      this.$input.on("keydown", async (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          const name = this.extract_rs_name(this.$input.val());
          if (name) await this.load_run_sheet(name);
        }
      });

      this.$open.on("click", () => {
        if (!this.state.rs) return;
        frappe.set_route("Form", "Run Sheet", this.state.rs);
      });

      this.$sync.on("click", () => this.try_sync_queue());
      this.$clear.on("click", () => this.handle_clear_cache());

      // populate offline cache dropdown
      this.refresh_cache_dropdown();
    }

    // ----- Clear Cache (only when all synced) -----
    async handle_clear_cache() {
      const qlen = (await readQueue()).length;
      if (qlen > 0) {
        frappe.msgprint({
          title: __("Cannot Clear Cache"),
          message: __("{0} offline action(s) pending. Please sync first.", [qlen]),
          indicator: "orange",
        });
        return;
      }

      const idx = await indexList();
      if (!idx.length) {
        frappe.show_alert({ message: __("Nothing to clear."), indicator: "blue" });
        return;
      }

      frappe.confirm(
        __("This will remove all locally cached run sheets on this device. Continue?"),
        async () => {
          for (const x of idx) { await jdel(LS_RS(x.id)); }
          await jdel(LS_IDX);
          await jdel(LS_LAST);

          this.state.doc = null;
          this.state.legs = [];
          this.render_empty();
          await this.refresh_cache_dropdown();
          await this.update_status();

          frappe.show_alert({ message: __("Local cache cleared."), indicator: "green" });
        },
        () => {}
      );
    }

    async update_status() {
      const qlen = (await readQueue()).length;
      const cls = this.state.online ? "online" : "offline";
      const txt = this.state.online ? __("Online") : __("Offline");
      this.$status.removeClass("online offline").addClass(cls).text(`${txt} ${qlen ? `• ${__("unsynced")}: ${qlen}` : ""}`);

      // Enable Clear Cache only when no pending queue
      if (qlen > 0) this.$clear.attr("disabled", "disabled");
      else this.$clear.removeAttr("disabled");
    }

    async refresh_cache_dropdown() {
      const idx = await indexList();
      const items = idx
        .sort((a,b)=>b.at-a.at)
        .slice(0,20)
        .map(x => `<a class="dropdown-item" data-rs="${frappe.utils.escape_html(x.id)}">${frappe.utils.escape_html(x.id)}</a>`)
        .join("") || `<div class="dropdown-item disabled">${__("No cached run sheets yet.")}</div>`;
      this.$cache.html(items);
      this.$cache.find(".dropdown-item:not(.disabled)").on("click", async (ev) => {
        const rs = $(ev.currentTarget).data("rs");
        await this.load_from_cache(rs);
      });
    }

    // ------------- Scan helpers -------------
    extract_rs_name(scanned) {
      if (!scanned) return null;
      const s = String(scanned).trim();
      const m = s.match(/(?:\/Form\/Run\s*Sheet\/|name=|#Form\/Run\s*Sheet\/)?([A-Z]{2,}-\d{3,})/i);
      return (m && m[1]) ? m[1].toUpperCase() : s;
    }

    async scan_barcode() {
      try { if (window.erpnext?.utils?.scan_barcode) { const v = await erpnext.utils.scan_barcode(); if (v) return String(v).trim(); } } catch {}
      try {
        if (frappe.ui && typeof frappe.ui.Scanner === "function") {
          return await new Promise((resolve, reject) => {
            const s = new frappe.ui.Scanner({
              dialog: true, multiple: false,
              on_scan: (d) => resolve(String((d?.decodedText || d?.code || d?.content || d || "")).trim()),
              on_error: reject,
            });
            s.make?.(); s.open?.();
          });
        }
      } catch {}
      try {
        if (frappe.ui && typeof frappe.ui.BarcodeScanner === "function") {
          return await new Promise((resolve, reject) => {
            const bs = new frappe.ui.BarcodeScanner({
              dialog: true, scan_action: (val) => resolve(String(val || "").trim()), on_error: reject,
            });
            bs.scan?.();
          });
        }
      } catch {}
      const v = await new Promise((resolve) => {
        frappe.prompt([{ fieldname: "code", fieldtype: "Data", label: __("Barcode"), reqd: 1 }],
          (vals) => resolve(String(vals.code || "").trim()), __("Enter / Paste Barcode"), __("OK"));
      });
      return v;
    }

    // --------- Data fetch (server bundle) ----------
    async fetch_run_sheet(rs) {
      const data = await frappe.call({
        method: "logistics.transport.api.get_run_sheet_bundle",
        args: { name: rs },
        freeze: true,
        freeze_message: __("Loading Run Sheet…"),
      }).then(r => r && r.message);

      if (!data) return null;

      const { doc, legs } = data;

      // Pre-fetch pick/drop coordinates so Google Maps works even after going offline
      for (const leg of legs || []) {
        leg._pick_coord = await getAddressLatLon(leg.pick_address);
        leg._drop_coord = await getAddressLatLon(leg.drop_address);
      }

      return { doc, legs };
    }

    async cache_current(rs, payload) {
      await cacheSet(rs, payload);
      await rememberLastRS(rs);
      await this.refresh_cache_dropdown();
    }

    async load_run_sheet(rs) {
      this.$head.text(__("Loading…"));
      if (!this.state.online) {
        return await this.load_from_cache(rs, { offline: true });
      }

      try {
        const data = await this.fetch_run_sheet(rs);
        if (!data) {
          frappe.msgprint({ title: __("Not Found"), message: __("Run Sheet {0} not found.", [rs]), indicator: "red" });
          this.render_empty();
          return;
        }
        this.state.rs = rs;
        this.state.doc = data.doc;
        this.state.legs = data.legs || [];
        await this.cache_current(rs, data);
        this.render_header(data.doc);
        this.render_legs(this.state.legs);
        frappe.show_alert({ message: __("Loaded {0}", [rs]), indicator: "green" });
      } catch (e) {
        console.error(e);
        frappe.msgprint({ title: __("Error"), message: __("Could not load the Run Sheet. Please check your server logs."), indicator: "red" });
        this.render_empty();
      } finally {
        await this.update_status();
      }
    }

    async load_from_cache(rs, opts = {}) {
      const cached = await cacheGet(rs);
      if (!cached) {
        frappe.msgprint({
          title: __("Not in Offline Cache"),
          message: __("Run Sheet {0} is not cached yet. Open it once while online to use it offline.", [frappe.utils.escape_html(rs)]),
          indicator: "orange"
        });
        return;
      }
      this.state.rs = rs;
      this.state.doc = cached.doc;
      this.state.legs = cached.legs || [];
      await rememberLastRS(rs);
      this.render_header(cached.doc, { offline: !!opts.offline });
      this.render_legs(this.state.legs);
      if (!opts.silent) frappe.show_alert({ message: __("Loaded cached {0}", [rs]), indicator: "blue" });
      await this.update_status();
    }

    // ---------------- Rendering ----------------
    fmt_dt(dt) { return dt ? frappe.datetime.str_to_user(dt) : "-"; }

    render_header(doc, opts = {}) {
      const bits = [
        `<b>${frappe.utils.escape_html(doc.name || "")}</b>`,
        doc.run_date ? `${__("Run Date")}: ${frappe.utils.escape_html(frappe.datetime.str_to_user(doc.run_date))}` : "",
        doc.driver ? `${__("Driver")}: ${frappe.utils.escape_html(doc.driver)}` : "",
        `${__("Docstatus")}: ${[__("Draft"),__("Submitted"),__("Cancelled")][doc.docstatus || 0]}`,
        opts.offline ? `<span class="unsynced" style="margin-left:6px;">${__("Offline mode — cached view")}</span>` : ""
      ].filter(Boolean);
      this.$head.html(bits.join(" • "));
    }

    async render_legs(legs) {
      if (!legs?.length) {
        this.$legs.html(`<div class="text-muted">${__("No legs on this run sheet (or they are cancelled).")}</div>`);
        return;
      }

      const q = await readQueue();
      const unsyncedByLeg = new Set(q.filter(x => x.rs === this.state.rs).map(x => x.name));

      const make_card = (r) => {
        const safe = (x) => (x == null ? "" : String(x));
        const hasStart = !!r.start_date;
        const hasEnd   = !!r.end_date;
        const unsynced = unsyncedByLeg.has(r.name);

        const coordsOk = !!(r._pick_coord && r._drop_coord);
        const gmapUrl = coordsOk
          ? `https://www.google.com/maps/dir/?api=1&origin=${r._pick_coord.lat},${r._pick_coord.lon}&destination=${r._drop_coord.lat},${r._drop_coord.lon}`
          : null;

        return `
          <div class="leg-card" data-row="${frappe.utils.escape_html(r.name)}">
            <div class="leg-main">
              <div class="leg-left">
                <div class="leg-name">${frappe.utils.escape_html(safe(r.name))} ${unsynced ? `<span class="unsynced">${__("unsynced")}</span>` : ""}</div>
                <div class="leg-desc">
                  ${frappe.utils.escape_html(safe(r.facility_from) || "")}
                  ${r.facility_from && r.facility_to ? "→" : ""} 
                  ${frappe.utils.escape_html(safe(r.facility_to) || "")}
                </div>
              </div>
              <div class="leg-actions">
                ${!hasStart ? `<button class="btn btn-sm btn-primary leg-start">${__("Start")}</button>` : ""}
                ${hasStart && !hasEnd ? `<button class="btn btn-sm btn-success leg-end">${__("End")}</button>` : ""}
                ${hasStart && !r.signature ? `<button class="btn btn-sm btn-info leg-sign-epod">${__("Sign ePOD")}</button>` : ""}
                ${gmapUrl ? `<a class="btn btn-sm btn-default" target="_blank" rel="noopener" href="${gmapUrl}">${__("View Map")}</a>` : ""}
              </div>
            </div>
            <div class="leg-meta">
              <div><label>${__("Status")}:</label><span class="leg-status status-${(r.status || "Open").toLowerCase()}">${frappe.utils.escape_html(r.status || "Open")}</span></div>
              <div><label>${__("Started")}:</label><span class="leg-start-at">${this.fmt_dt(r.start_date)}</span></div>
              <div><label>${__("Ended")}:</label><span class="leg-end-at">${this.fmt_dt(r.end_date)}</span></div>
              <div><label>${__("Planned")}:</label><span>${this.plan_text(r)}</span></div>
              ${r.signature ? `<div><label>${__("Signed")}:</label><span>${frappe.utils.escape_html(r.signed_by || "")} (${this.fmt_dt(r.date_signed)})</span></div>` : ""}
            </div>
          </div>
        `;
      };

      this.$legs.html(`<div class="leg-grid">${legs.map(make_card).join("")}</div>`);
      this.bind_leg_buttons();
    }

    plan_text(r) {
      const d = r.route_distance_km ?? r.distance_km;
      const m = r.route_duration_min ?? r.duration_min;
      const parts = [];
      if (d != null && d !== "") parts.push(`${fmtNum(d, 3)} km`);
      if (m != null && m !== "") parts.push(`${fmtNum(m, 1)} min`);
      return parts.join(" • ") || "-";
    }


    render_empty() {
      this.$head.empty();
      this.$legs.html(`<div class="text-muted">${__("Scan a Run Sheet to begin.")}</div>`);
    }

    // ------------- Buttons per card -------------
    bind_leg_buttons() {
      const $root = this.$legs;

      $root.find(".leg-start").on("click", async (ev) => {
        const $btn  = $(ev.currentTarget);
        const $card = $btn.closest(".leg-card");
        const name  = $card.data("row");
        const val   = nowISO();

        const ok = await this.apply_leg_updates(name, { start_date: val });
        if (!ok) return;

        // Update the leg data and re-render to show correct buttons
        const leg = this.state.legs.find(l => l.name === name);
        if (leg) leg.start_date = val;
        $card.find(".leg-start-at").text(this.fmt_dt(val));
        this.render_legs(this.state.legs); // Re-render to update button visibility
      });

      $root.find(".leg-end").on("click", async (ev) => {
        const $btn  = $(ev.currentTarget);
        const $card = $btn.closest(".leg-card");
        const name  = $card.data("row");
        const val   = nowISO();

        const ok = await this.apply_leg_updates(name, { end_date: val });
        if (!ok) return;

        // Update the leg data and re-render to hide buttons
        const leg = this.state.legs.find(l => l.name === name);
        if (leg) leg.end_date = val;
        $card.find(".leg-end-at").text(this.fmt_dt(val));
        this.render_legs(this.state.legs); // Re-render to update button visibility
      });

      $root.find(".leg-sign-epod").on("click", async (ev) => {
        const $btn  = $(ev.currentTarget);
        const $card = $btn.closest(".leg-card");
        const name  = $card.data("row");
        
        this.current_leg_for_signature = name;
        this.show_signature_dialog();
      });
    }

    // ----------------- Apply updates (online or offline) -----------------
    async apply_leg_updates(legName, updates) {
      const rs = this.state.rs;
      if (!rs || !legName || !updates) return false;

      await cacheUpdateLegFields(rs, legName, updates);
      this.mark_row_unsynced_ui(legName, true);

      if (!this.state.online) {
        await enqueue({ rs, name: legName, updates });
        await this.update_status();
        frappe.show_alert({ message: __("Saved offline"), indicator: "blue" });
        return true;
      }

      try {
        await frappe.db.set_value("Transport Leg", legName, updates);
        this.mark_row_unsynced_ui(legName, false);
        await this.update_status();
        frappe.show_alert({ message: __("Saved"), indicator: "green" });
        const r = this.state.legs.find(x => x.name === legName);
        if (r) Object.assign(r, updates);
        return true;
      } catch (e) {
        console.warn("Online save failed; queuing offline op.", e);
        await enqueue({ rs, name: legName, updates });
        await this.update_status();
        frappe.show_alert({ message: __("Saved offline (will sync later)"), indicator: "blue" });
        return true;
      }
    }

    mark_row_unsynced_ui(legName, unsynced) {
      const $card = this.$legs.find(`.leg-card[data-row="${CSS.escape(legName)}"]`);
      if (!$card.length) return;
      const $name = $card.find(".leg-name");
      const hasChip = $name.find(".unsynced").length > 0;
      if (unsynced && !hasChip) $name.append(` <span class="unsynced">${__("unsynced")}</span>`);
      if (!unsynced && hasChip) $name.find(".unsynced").remove();
    }

    // ----------------- Signature functionality -----------------
    show_signature_dialog() {
      // Initialize signature canvas
      this.init_signature_canvas();
      
      // Set current date/time
      const now = new Date();
      const localDateTime = now.toISOString().slice(0, 16);
      $("#rss-date-signed").val(localDateTime);
      
      // Clear previous data
      $("#rss-signed-by").val("");
      this.clear_signature();
      
      // Show modal
      $("#rss-signature-modal").modal("show");
    }

    init_signature_canvas() {
      const canvas = document.getElementById("rss-signature-canvas");
      if (!canvas) return;
      
      // Adjust canvas size for mobile
      const isMobile = window.innerWidth <= 768;
      if (isMobile) {
        canvas.width = Math.min(600, window.innerWidth - 40);
        canvas.height = 150;
      } else {
        canvas.width = 600;
        canvas.height = 200;
      }
      
      const ctx = canvas.getContext("2d");
      let isDrawing = false;
      let lastX = 0;
      let lastY = 0;

      // Mouse events
      canvas.addEventListener("mousedown", (e) => {
        isDrawing = true;
        const rect = canvas.getBoundingClientRect();
        lastX = e.clientX - rect.left;
        lastY = e.clientY - rect.top;
      });

      canvas.addEventListener("mousemove", (e) => {
        if (!isDrawing) return;
        const rect = canvas.getBoundingClientRect();
        const currentX = e.clientX - rect.left;
        const currentY = e.clientY - rect.top;
        
        ctx.beginPath();
        ctx.moveTo(lastX, lastY);
        ctx.lineTo(currentX, currentY);
        ctx.strokeStyle = "#000";
        ctx.lineWidth = 2;
        ctx.lineCap = "round";
        ctx.stroke();
        
        lastX = currentX;
        lastY = currentY;
      });

      canvas.addEventListener("mouseup", () => {
        isDrawing = false;
      });

      canvas.addEventListener("mouseout", () => {
        isDrawing = false;
      });

      // Touch events for mobile
      canvas.addEventListener("touchstart", (e) => {
        e.preventDefault();
        isDrawing = true;
        const rect = canvas.getBoundingClientRect();
        const touch = e.touches[0];
        lastX = touch.clientX - rect.left;
        lastY = touch.clientY - rect.top;
      });

      canvas.addEventListener("touchmove", (e) => {
        e.preventDefault();
        if (!isDrawing) return;
        const rect = canvas.getBoundingClientRect();
        const touch = e.touches[0];
        const currentX = touch.clientX - rect.left;
        const currentY = touch.clientY - rect.top;
        
        ctx.beginPath();
        ctx.moveTo(lastX, lastY);
        ctx.lineTo(currentX, currentY);
        ctx.strokeStyle = "#000";
        ctx.lineWidth = 2;
        ctx.lineCap = "round";
        ctx.stroke();
        
        lastX = currentX;
        lastY = currentY;
      });

      canvas.addEventListener("touchend", (e) => {
        e.preventDefault();
        isDrawing = false;
      });

      // Clear button
      $("#rss-clear-signature").off("click").on("click", () => {
        this.clear_signature();
      });

      // Save button
      $("#rss-save-signature").off("click").on("click", () => {
        this.save_signature();
      });
    }

    clear_signature() {
      const canvas = document.getElementById("rss-signature-canvas");
      if (!canvas) return;
      
      const ctx = canvas.getContext("2d");
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }

    async save_signature() {
      const signedBy = $("#rss-signed-by").val().trim();
      const dateSigned = $("#rss-date-signed").val();
      
      if (!signedBy) {
        frappe.show_alert({ message: __("Please enter the signer's name"), indicator: "orange" });
        return;
      }
      
      if (!dateSigned) {
        frappe.show_alert({ message: __("Please enter the date signed"), indicator: "orange" });
        return;
      }

      // Get signature as base64
      const canvas = document.getElementById("rss-signature-canvas");
      const signature = canvas.toDataURL("image/png");
      
      // Check if signature is empty (just white canvas)
      const ctx = canvas.getContext("2d");
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      const hasContent = imageData.data.some((value, index) => {
        return index % 4 !== 3 && value !== 255; // Check if any pixel is not white
      });
      
      if (!hasContent) {
        frappe.show_alert({ message: __("Please provide a signature"), indicator: "orange" });
        return;
      }

      const updates = {
        signature: signature,
        signed_by: signedBy,
        date_signed: dateSigned
      };

      const ok = await this.apply_leg_updates(this.current_leg_for_signature, updates);
      if (ok) {
        // Update the leg data and re-render to hide the sign button
        const leg = this.state.legs.find(l => l.name === this.current_leg_for_signature);
        if (leg) {
          leg.signature = signature;
          leg.signed_by = signedBy;
          leg.date_signed = dateSigned;
        }
        $("#rss-signature-modal").modal("hide");
        this.render_legs(this.state.legs); // Re-render to hide the sign button
        frappe.show_alert({ message: __("Signature saved"), indicator: "green" });
      }
    }

    // ----------------- Sync queue (hardened) -----------------
    async try_sync_queue() {
      if (!this.state.online || this.state.syncing) return;
      this.state.syncing = true;
      await this.update_status();

      const conflicts = [];
      let synced = 0;
      let blockedBySession = false;
      let firstServerErrorMsg = null;

      try {
        const q = await readQueue();
        for (const item of q) {
          if (blockedBySession) break;
          try {
            const doc = await frappe.db.get_doc("Transport Leg", item.name);
            const willOverwrite =
              (item.updates.start_date && doc.start_date && doc.start_date !== item.updates.start_date) ||
              (item.updates.end_date   && doc.end_date   && doc.end_date   !== item.updates.end_date);

            if (willOverwrite) { conflicts.push(item); continue; }

            await sleep(120); // gentle backoff
            await frappe.db.set_value("Transport Leg", item.name, item.updates);

            await dequeueById(item.id);
            await cacheUpdateLegFields(item.rs, item.name, item.updates);
            if (this.state.rs === item.rs) {
              const r = this.state.legs.find(x => x.name === item.name);
              if (r) Object.assign(r, item.updates);
              this.mark_row_unsynced_ui(item.name, false);
            }
            synced++;

          } catch (xhr) {
            if (likelySessionIssue(xhr)) {
              blockedBySession = true;
              if (this.$reauth) this.$reauth.show();
              frappe.show_alert({ message: __("Sign-in required to sync. Open Login and retry."), indicator: "orange" });
              break;
            }

            if (!firstServerErrorMsg) {
              let msg = null;
              try {
                if (isHTMLResponse(xhr)) {
                  const title = extractTitleFromHTML(xhr.responseText || "");
                  msg = title || __("Server returned an HTML error page.");
                } else if (xhr && xhr.responseJSON && xhr.responseJSON._error_message) {
                  msg = xhr.responseJSON._error_message;
                }
              } catch {}
              firstServerErrorMsg = msg;
            }

            console.warn("Sync item failed; will retry later", item, xhr);
          }
        }
      } finally {
        this.state.syncing = false;
        const qlen = (await readQueue()).length;
        await this.update_status();

        if (synced) frappe.show_alert({ message: __("{0} action(s) synced", [synced]), indicator: "green" });

        if (conflicts.length) {
          frappe.msgprint({
            title: __("Sync Conflicts"),
            message: __("{0} action(s) could not be applied because the server already has values. Open those legs to resolve.", [conflicts.length]),
            indicator: "orange",
          });
        }

        if (firstServerErrorMsg && !blockedBySession) {
          frappe.msgprint({
            title: __("Server Error"),
            message: __(firstServerErrorMsg),
            indicator: "red",
          });
        }
      }
    }

    // ------------- Robust restore on page load -------------
    async robust_restore() {
      const parts = frappe.get_route();
      if (parts && parts[0] === "run-sheet-scan" && parts[1]) {
        const name = this.extract_rs_name(parts[1]);
        if (name) {
          if (this.state.online) await this.load_run_sheet(name);
          else await this.load_from_cache(name, { offline: true, silent: true });
          return;
        }
      }

      if (!this.state.online) {
        const last = await getLastRS();
        if (last && (await cacheGet(last))) {
          await this.load_from_cache(last, { offline: true, silent: true });
          return;
        }
      }

      const last2 = await getLastRS();
      if (this.state.online && last2 && (await cacheGet(last2))) {
        await this.load_from_cache(last2, { silent: true });
        return;
      }

      this.render_empty();
    }

    // kept for backward compatibility
    restore_from_route() { this.robust_restore(); }
  }

  logistics.run_sheet_scan.RunSheetScanPage = RunSheetScanPage;
})();
