// route: warehouse-job-card
// purpose: Operations Start/End only (auto-save + actual_hours) with button-hide logic

frappe.pages["warehouse-job-card"].on_page_load = function (wrapper) {
  new WarehouseJobCardPage(wrapper);
};

class WarehouseJobCardPage {
  constructor(wrapper) {
    this.wrapper = $(wrapper);
    this.page = frappe.ui.make_app_page({
      parent: wrapper,
      title: __("Warehouse Job Card"),
      single_column: true,
    });
    this.state = { job: null, doc: null, operations: [] };
    this.make_layout();
    this.bind_events();
    this.maybe_load_from_route();
  }

  make_layout() {
    const $ui = $(`
      <div class="wjc space-y-4">
        <div class="card">
          <div class="card-body" style="padding:12px;">
            <div class="wjc-bar">
              <button class="btn btn-sm btn-primary" id="wjc-scan"><i class="fa fa-qrcode"></i> ${__("Scan Job")}</button>
              <input type="text" class="form-control input-sm" id="wjc-input"
                     placeholder="${__("Enter or scan Warehouse Job (e.g., WJ-00000123)")}">
              <button class="btn btn-sm btn-default" id="wjc-load">${__("Load")}</button>
              <a class="btn btn-sm btn-default" id="wjc-open">${__("Open Document")}</a>
            </div>
            <div id="wjc-head" class="text-muted" style="margin-top:8px;"></div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><strong>${__("Operations")}</strong></div>
          <div class="card-body" style="padding:12px;">
            <div id="wjc-ops"></div>
          </div>
        </div>
      </div>
    `);

    this.page.body.append($ui);

    this.$input = $ui.find("#wjc-input");
    this.$scan  = $ui.find("#wjc-scan");
    this.$load  = $ui.find("#wjc-load");
    this.$open  = $ui.find("#wjc-open");
    this.$head  = $ui.find("#wjc-head");
    this.$ops   = $ui.find("#wjc-ops");

    this.page.body.append(`
      <style>
        .wjc .wjc-bar{ display:flex; gap:6px; flex-wrap:wrap; align-items:center; }
        .wjc .wjc-bar #wjc-input{ min-width:220px; max-width:340px; }
        @media (max-width:480px){ .wjc .wjc-bar #wjc-input{ min-width:160px; max-width:100%; flex:1; } }

        .wjc .op-grid{ display:grid; gap:10px; }
        .wjc .op-card{ border:1px solid var(--border-color,#e5e7eb); border-radius:12px; padding:10px; background:#fff; box-shadow:0 1px 0 rgba(0,0,0,0.02); }
        .wjc .op-main{ display:flex; justify-content:space-between; gap:8px; align-items:center; }
        .wjc .op-name{ font-weight:600; }
        .wjc .op-desc{ color:#6b7280; font-size:12px; margin-top:2px; }
        .wjc .op-actions{ display:flex; gap:6px; }
        .wjc .op-actions .btn{ min-width:92px; }
        @media (max-width:480px){ .wjc .op-actions .btn{ min-width:110px; } }
        .wjc .op-times{ display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:6px; margin-top:8px; font-size:12px; color:#374151; }
        .wjc .op-times label{ font-weight:600; margin-right:6px; }
        .wjc .hidden{ display:none !important; }
      </style>
    `);
  }

  bind_events() {
    this.$scan.on("click", async () => {
      const code = await this.scan_barcode();
      if (!code) return;
      const name = this.extract_job_name(code);
      this.$input.val(name);
      await this.load_job(name);
    });

    this.$load.on("click", async () => {
      const name = this.extract_job_name(this.$input.val());
      if (!name) return frappe.show_alert({ message: __("Enter a Warehouse Job ID"), indicator: "orange" });
      await this.load_job(name);
    });

    this.$input.on("keydown", async (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        const name = this.extract_job_name(this.$input.val());
        if (name) await this.load_job(name);
      }
    });

    this.$open.on("click", () => {
      if (!this.state.job) return;
      frappe.set_route("Form", "Warehouse Job", this.state.job);
    });
  }

  extract_job_name(scanned) {
    if (!scanned) return null;
    const s = String(scanned).trim();
    const m = s.match(/(?:\/Form\/Warehouse\s*Job\/|name=|#Form\/Warehouse\s*Job\/)?([A-Z]{2,}-\d{3,})/i);
    return (m && m[1]) ? m[1].toUpperCase() : s;
  }

  async scan_barcode() {
    try {
      if (window.erpnext?.utils?.scan_barcode) {
        const v = await erpnext.utils.scan_barcode();
        if (v) return String(v).trim();
      }
    } catch {}
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
            dialog: true,
            scan_action: (val) => resolve(String(val || "").trim()),
            on_error: reject,
          });
          bs.scan?.();
        });
      }
    } catch {}
    const v = await new Promise((resolve) => {
      frappe.prompt(
        [{ fieldname: "code", fieldtype: "Data", label: __("Barcode"), reqd: 1 }],
        (vals) => resolve(String(vals.code || "").trim()),
        __("Enter / Paste Barcode"),
        __("OK")
      );
    });
    return v;
  }

  async fetch_job(name) {
    try {
      const r = await frappe.call({
        method: "frappe.client.get",
        args: { doctype: "Warehouse Job", name },
        freeze: true, freeze_message: __("Loading Warehouse Job…"),
      });
      return r?.message || null;
    } catch (e) {
      console.error(e);
      frappe.msgprint({ title: __("Not Found"), message: __("Warehouse Job {0} not found.").format(name), indicator: "red" });
      return null;
    }
  }

  fmt_dt(dt)   { return dt ? frappe.datetime.str_to_user(dt) : "-"; }
  now_dt()     { return frappe.datetime.now_datetime(); }
  to_hours(s)  { return Math.round((s / 3600) * 100) / 100; }

  compute_actual_hours(start_dt, end_dt) {
    if (!start_dt || !end_dt) return null;
    const s = frappe.datetime.str_to_obj(start_dt);
    const e = frappe.datetime.str_to_obj(end_dt);
    const diff = Math.max(0, (e - s) / 1000);
    return this.to_hours(diff);
  }

  async load_job(name) {
    this.$head.text(__("Loading…"));
    const doc = await this.fetch_job(name);
    if (!doc) { this.render_empty(); return; }

    const ops = (doc.operations || doc.warehouse_job_operations || []).slice().sort((a,b) => (a.idx||9999)-(b.idx||9999));

    this.state.job = doc.name;
    this.state.doc = doc;
    this.state.operations = ops;

    this.render_header(doc);
    this.render_operations(ops);
    frappe.show_alert({ message: __("Loaded {0}", [doc.name]), indicator: "green" });
  }

  render_header(job) {
    const bits = [
      `<b>${frappe.utils.escape_html(job.name || "")}</b>`,
      job.type ? `${__("Type")}: ${frappe.utils.escape_html(job.type)}` : "",
      job.customer ? `${__("Customer")}: ${frappe.utils.escape_html(job.customer)}` : "",
      job.company ? `${__("Company")}: ${frappe.utils.escape_html(job.company)}` : "",
      job.branch ? `${__("Branch")}: ${frappe.utils.escape_html(job.branch)}` : "",
      job.staging_area ? `${__("Staging")}: ${frappe.utils.escape_html(job.staging_area)}` : "",
      `${__("Docstatus")}: ${[__("Draft"),__("Submitted"),__("Cancelled")][job.docstatus || 0]}`
    ].filter(Boolean);
    this.$head.html(bits.join(" • "));
  }

  render_operations(rows) {
    const make_card = (r) => {
      const safe = (x) => (x == null ? "" : String(x));
      const hasStart = !!r.start_date;
      const hasEnd   = !!r.end_date;
      return `
        <div class="op-card" data-row="${frappe.utils.escape_html(r.name)}">
          <div class="op-main">
            <div class="op-left">
              <div class="op-name">${frappe.utils.escape_html(safe(r.operation) || "(?)")}</div>
              <div class="op-desc">${frappe.utils.escape_html(safe(r.description) || "")}</div>
            </div>
            <div class="op-actions">
              <button class="btn btn-sm btn-primary op-start ${hasStart ? "hidden" : ""}">${__("Start")}</button>
              <button class="btn btn-sm btn-success op-end ${hasEnd ? "hidden" : ""}">${__("End")}</button>
            </div>
          </div>
          <div class="op-times">
            <div><label>${__("Started")}:</label><span class="op-start-at">${this.fmt_dt(r.start_date)}</span></div>
            <div><label>${__("Ended")}:</label><span class="op-end-at">${this.fmt_dt(r.end_date)}</span></div>
            <div><label>${__("Actual")}:</label><span class="op-actual">${(r.actual_hours!=null && r.actual_hours!=="") ? `${r.actual_hours} h` : "-"}</span></div>
          </div>
        </div>
      `;
    };

    if (!rows?.length) {
      this.$ops.html(`<div class="text-muted">${__("No operations on this job.")}</div>`);
      return;
    }

    this.$ops.html(`<div class="op-grid">${rows.map(make_card).join("")}</div>`);
    this.bind_op_buttons();
  }

  render_empty() {
    this.$head.empty();
    this.$ops.html(`<div class="text-muted">${__("Scan a Warehouse Job to begin.")}</div>`);
  }

  bind_op_buttons() {
    const $root = this.$ops;

    $root.find(".op-start").on("click", async (ev) => {
      const $btn  = $(ev.currentTarget);
      const $card = $btn.closest(".op-card");
      const name  = $card.data("row");
      const start_dt = this.now_dt();

      const ok = await this.set_op_times(name, { start_date: start_dt });
      if (!ok) return;

      // Update UI
      $card.find(".op-start-at").text(this.fmt_dt(start_dt));
      $btn.addClass("hidden"); // hide Start button now that start_date is set

      // recompute actual if end exists
      const end_txt = $card.find(".op-end-at").text().trim();
      const end_dt = end_txt && end_txt !== "-" ? frappe.datetime.user_to_str(end_txt) : null;
      const hrs = this.compute_actual_hours(start_dt, end_dt);
      if (hrs != null) {
        await this.set_op_times(name, { actual_hours: hrs });
        $card.find(".op-actual").text(`${hrs} h`);
      }

      frappe.show_alert({ message: __("Job has started on {0}", [this.fmt_dt(start_dt)]), indicator: "green" });
    });

    $root.find(".op-end").on("click", async (ev) => {
      const $btn  = $(ev.currentTarget);
      const $card = $btn.closest(".op-card");
      const name  = $card.data("row");
      const end_dt = this.now_dt();

      const start_txt = $card.find(".op-start-at").text().trim();
      const start_dt = start_txt && start_txt !== "-" ? frappe.datetime.user_to_str(start_txt) : null;
      const hrs = this.compute_actual_hours(start_dt, end_dt);

      const payload = { end_date: end_dt };
      if (hrs != null) payload.actual_hours = hrs;

      const ok = await this.set_op_times(name, payload);
      if (!ok) return;

      // Update UI
      $card.find(".op-end-at").text(this.fmt_dt(end_dt));
      if (hrs != null) $card.find(".op-actual").text(`${hrs} h`);
      $btn.addClass("hidden"); // hide End button now that end_date is set

      frappe.show_alert({ message: __("Job was completed on {0}", [this.fmt_dt(end_dt)]), indicator: "blue" });
    });
  }

  async set_op_times(rowname, values) {
    try {
      await frappe.db.set_value("Warehouse Job Operations", rowname, values);
      return true;
    } catch (e) {
      console.error(e);
      frappe.msgprint({ title: __("Save Failed"), message: __("Could not update operation row."), indicator: "red" });
      return false;
    }
  }

  maybe_load_from_route() {
    const parts = frappe.get_route();
    if (parts && parts[0] === "warehouse-job-card" && parts[1]) {
      const name = this.extract_job_name(parts[1]);
      if (name) {
        this.$input.val(name);
        this.load_job(name);
      }
    } else {
      this.render_empty();
    }
  }
}
