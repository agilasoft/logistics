frappe.pages['warehouse-job-scanner'].on_page_load = function(wrapper) {
  new WarehouseJobScannerPage(wrapper);
};

class WarehouseJobScannerPage {
  constructor(wrapper) {
    this.wrapper = $(wrapper);
    this.page = frappe.ui.make_app_page({
      parent: wrapper,
      title: __("Warehouse Job Scanner"),
      single_column: true,
    });

    this.state = {
      job: null, // job name
      header: null,
      operations: [],
    };

    this.make_layout();
    this.bind_events();
  }

  make_layout() {
    const $body = $(`
      <div class="whs-job-scan space-y-5">

        <div class="card">
          <div class="card-body" style="padding: 16px;">
            <div class="flex items-center gap-2">
              <input type="text" class="form-control input-sm" placeholder="${__("Scan or enter Warehouse Job")}" id="wj-input" style="max-width: 320px;">
              <button class="btn btn-sm btn-primary" id="wj-scan-btn"><i class="fa fa-qrcode"></i> ${__("Scan")}</button>
              <button class="btn btn-sm btn-default" id="wj-load-btn">${__("Load")}</button>
            </div>
            <div id="wj-header" class="text-muted" style="margin-top:8px;"></div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><strong>${__("Operations")}</strong></div>
          <div class="card-body" style="padding: 12px;">
            <div class="text-muted" style="margin-bottom:8px;">${__("Update actual start/end; duration is computed and saved")}</div>
            <div id="ops-table"></div>
            <div class="flex gap-2" style="margin-top: 10px;">
              <button class="btn btn-sm btn-primary" id="ops-save-btn">${__("Save Operation Times")}</button>
              <span id="ops-save-status" class="text-muted"></span>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><strong>${__("Post by Scan")}</strong></div>
          <div class="card-body" style="padding: 12px;">
            <div class="grid" style="display:grid;grid-template-columns: repeat(6, minmax(140px, 1fr));gap:8px;">
              <div class="form-group">
                <label>${__("Action")}</label>
                <select class="form-control input-sm" id="post-action">
                  <option>Receiving</option>
                  <option>Pick</option>
                  <option>Putaway</option>
                  <option>Release</option>
                </select>
              </div>
              <div class="form-group" style="position:relative;">
                <label>${__("Location")}</label>
                <input class="form-control input-sm" id="post-location" placeholder="${__("Scan/Enter Location")}">
                <button class="btn btn-default btn-xs scan-inline" id="scan-location" title="${__("Scan with Camera")}"
                        style="position:absolute;right:6px;top:24px;"><i class="fa fa-qrcode"></i></button>
              </div>
              <div class="form-group" style="position:relative;">
                <label>${__("Handling Unit")}</label>
                <input class="form-control input-sm" id="post-hu" placeholder="${__("Scan/Enter HU")}">
                <button class="btn btn-default btn-xs scan-inline" id="scan-hu" title="${__("Scan with Camera")}"
                        style="position:absolute;right:6px;top:24px;"><i class="fa fa-qrcode"></i></button>
              </div>
              <div class="form-group">
                <label>${__("Qty (optional)")}</label>
                <input type="number" step="any" class="form-control input-sm" id="post-qty" placeholder="e.g. 5">
              </div>
              <div class="form-group">
                <label>${__("Item (optional)")}</label>
                <input class="form-control input-sm" id="post-item" placeholder="${__("Filter by Item")}">
              </div>
              <div class="form-group" style="align-self:end;">
                <button class="btn btn-sm btn-success" id="post-now">${__("Post")}</button>
              </div>
            </div>
            <div id="post-result" class="text-muted" style="margin-top:8px;"></div>
          </div>
        </div>

      </div>
    `);

    this.page.body.append($body);
    this.$wjInput = $body.find('#wj-input');
    this.$wjHeader = $body.find('#wj-header');
    this.$wjScanBtn = $body.find('#wj-scan-btn');
    this.$wjLoadBtn = $body.find('#wj-load-btn');

    this.$opsTable = $body.find('#ops-table');
    this.$opsSaveBtn = $body.find('#ops-save-btn');
    this.$opsSaveStatus = $body.find('#ops-save-status');

    this.$postAction = $body.find('#post-action');
    this.$postLoc = $body.find('#post-location');
    this.$postHU = $body.find('#post-hu');
    this.$postQty = $body.find('#post-qty');
    this.$postItem = $body.find('#post-item');
    this.$postNow = $body.find('#post-now');
    this.$scanLoc = $body.find('#scan-location');
    this.$scanHU = $body.find('#scan-hu');
    this.$postResult = $body.find('#post-result');
  }

  bind_events() {
    this.$wjScanBtn.on('click', async () => {
      const v = await this.scan_barcode();
      if (v) {
        this.$wjInput.val(v);
        await this.load_job_from_scan(v);
      }
    });
    this.$wjLoadBtn.on('click', async () => {
      const v = (this.$wjInput.val() || '').trim();
      if (!v) return;
      await this.load_job_from_scan(v);
    });
    this.$wjInput.on('keydown', async (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        const v = (this.$wjInput.val() || '').trim();
        if (!v) return;
        await this.load_job_from_scan(v);
      }
    });

    this.$opsSaveBtn.on('click', async () => {
      await this.save_operations();
    });

    this.$postNow.on('click', async () => {
      await this.post_by_scan();
    });

    this.$scanLoc.on('click', async () => {
      const v = await this.scan_barcode();
      if (v) this.$postLoc.val(v);
    });
    this.$scanHU.on('click', async () => {
      const v = await this.scan_barcode();
      if (v) this.$postHU.val(v);
    });
  }

  // --- scanner helper with graceful fallbacks ---
  async scan_barcode() {
    try {
      if (window.erpnext?.utils?.scan_barcode) {
        const code = await erpnext.utils.scan_barcode();
        if (code) return String(code).trim();
      }
    } catch (e) { /* ignore */ }
    try {
      if (frappe.ui && typeof frappe.ui.Scanner === 'function') {
        return await new Promise((resolve, reject) => {
          const scanner = new frappe.ui.Scanner({
            dialog: true,
            multiple: false,
            on_scan: (data) => resolve(String((data?.decodedText || data?.code || data?.content || data || '')).trim()),
            on_error: (err) => reject(err),
          });
          scanner.make?.(); scanner.open?.();
        });
      }
    } catch (e) { /* ignore */ }
    const v = await new Promise((resolve) => {
      frappe.prompt([{ fieldname: "code", fieldtype: "Data", label: __("Barcode"), reqd: 1 }],
        (vals) => resolve(String(vals.code || "").trim()),
        __("Enter / Paste Barcode"),
        __("OK"));
    });
    return v;
  }

  async load_job_from_scan(scanned) {
    this.$wjHeader.html(__("Resolving…"));
    try {
      const r1 = await frappe.call({
        method: "logistics.warehousing.api.resolve_warehouse_job",
        args: { scanned }
      });
      const name = r1?.message?.name;
      if (!name) {
        this.$wjHeader.html(`<span class="text-danger">${frappe.utils.escape_html(r1?.message?.message || __("Not found"))}</span>`);
        return;
      }
      this.state.job = name;

      const r2 = await frappe.call({
        method: "logistics.warehousing.api.get_warehouse_job_overview",
        args: { warehouse_job: name },
        freeze: true,
        freeze_message: __("Loading Warehouse Job…"),
      });
      const d = r2?.message || {};
      this.state.header = d.header || null;
      this.state.operations = d.operations || [];
      this.render_header();
      this.render_operations();
      frappe.show_alert({ message: __("Loaded {0}", [name]), indicator: "green" });
    } catch (e) {
      console.error(e);
      this.$wjHeader.html(`<span class="text-danger">${__("Error loading job. See console.")}</span>`);
    }
  }

  render_header() {
    const h = this.state.header || {};
    const ds_label = (h.docstatus === 0 ? __("Draft") : (h.docstatus === 1 ? __("Submitted") : __("Cancelled")));
    const bits = [
      `<b>${frappe.utils.escape_html(h.name || "")}</b>`,
      h.type ? `${__("Type")}: ${frappe.utils.escape_html(h.type)}` : "",
      h.customer ? `${__("Customer")}: ${frappe.utils.escape_html(h.customer)}` : "",
      h.company ? `${__("Company")}: ${frappe.utils.escape_html(h.company)}` : "",
      h.branch ? `${__("Branch")}: ${frappe.utils.escape_html(h.branch)}` : "",
      h.staging_area ? `${__("Staging")}: ${frappe.utils.escape_html(h.staging_area)}` : "",
      `${__("Docstatus")}: ${ds_label}`,
    ].filter(Boolean);
    this.$wjHeader.html(bits.join(" • "));
  }

  render_operations() {
    const rows = this.state.operations || [];
    if (!rows.length) {
      this.$opsTable.html(`<div class="text-muted">${__("No operations found on this job.")}</div>`);
      return;
    }

    const nowISO = frappe.datetime.now_datetime();

    const $tbl = $(`
      <table class="table table-bordered table-condensed">
        <thead>
          <tr>
            <th style="width:50px;">#</th>
            <th>${__("Operation")}</th>
            <th>${__("Description")}</th>
            <th style="width:180px;">${__("Start")}</th>
            <th style="width:180px;">${__("End")}</th>
            <th style="width:100px;">${__("Hours")}</th>
            <th style="width:180px;">${__("Quick Set")}</th>
          </tr>
        </thead>
        <tbody></tbody>
      </table>
    `);

    const $tbody = $tbl.find('tbody');
    rows.forEach((r, i) => {
      const tr = $(`
        <tr data-row=${frappe.utils.escape_html(r.name || "")}>
          <td>${(r.idx || (i+1))}</td>
          <td>${frappe.utils.escape_html(r.operation || "")}</td>
          <td>${frappe.utils.escape_html(r.description || "")}</td>
          <td><input type="datetime-local" class="form-control input-sm op-start"></td>
          <td><input type="datetime-local" class="form-control input-sm op-end"></td>
          <td class="op-hours text-right">${(r.actual_hours != null ? r.actual_hours : "")}</td>
          <td class="flex gap-1">
            <button class="btn btn-xs btn-default start-now">${__("Start Now")}</button>
            <button class="btn btn-xs btn-default end-now">${__("End Now")}</button>
            <button class="btn btn-xs btn-default clear">${__("Clear")}</button>
          </td>
        </tr>
      `);

      // Set existing values if present
      const s = r.start_datetime ? this.to_local_input(r.start_datetime) : "";
      const e = r.end_datetime ? this.to_local_input(r.end_datetime) : "";
      tr.find('.op-start').val(s);
      tr.find('.op-end').val(e);

      tr.find('.start-now').on('click', () => {
        tr.find('.op-start').val(this.to_local_input(frappe.datetime.now_datetime()));
        this.compute_row_hours(tr);
      });
      tr.find('.end-now').on('click', () => {
        tr.find('.op-end').val(this.to_local_input(frappe.datetime.now_datetime()));
        this.compute_row_hours(tr);
      });
      tr.find('.clear').on('click', () => {
        tr.find('.op-start').val("");
        tr.find('.op-end').val("");
        tr.find('.op-hours').text("");
      });
      tr.find('.op-start, .op-end').on('change', () => this.compute_row_hours(tr));

      $tbody.append(tr);
      // initial compute
      this.compute_row_hours(tr);
    });

    this.$opsTable.html($tbl);
  }

  to_local_input(dt_str) {
    // dt_str is server format; we want "YYYY-MM-DDTHH:mm"
    const m = moment(dt_str);
    return m.isValid() ? m.format("YYYY-MM-DDTHH:mm") : "";
  }

  from_local_input(input_val) {
    // browser local -> ISO string Frappe understands
    if (!input_val) return null;
    const m = moment(input_val);
    return m.isValid() ? m.format("YYYY-MM-DD HH:mm:ss") : null;
  }

  compute_row_hours($tr) {
    const s = this.from_local_input($tr.find('.op-start').val());
    const e = this.from_local_input($tr.find('.op-end').val());
    if (!s || !e) { $tr.find('.op-hours').text(""); return; }
    const ms = moment(e).diff(moment(s), 'seconds');
    const hrs = Math.max(0, ms) / 3600.0;
    $tr.find('.op-hours').text(hrs.toFixed(2));
  }

  async save_operations() {
    if (!this.state.job) {
      frappe.msgprint(__("Scan/load a Warehouse Job first.")); return;
    }
    // build updates
    const updates = [];
    this.$opsTable.find('tbody tr').each((_, el) => {
      const $tr = $(el);
      const name = $tr.attr('data-row');
      const s = this.from_local_input($tr.find('.op-start').val());
      const e = this.from_local_input($tr.find('.op-end').val());
      if (!name) return;
      if (s || e) {
        updates.push({ name, start_datetime: s, end_datetime: e });
      }
    });
    if (!updates.length) {
      frappe.show_alert({ message: __("Nothing to save."), indicator: "orange" });
      return;
    }

    try {
      this.$opsSaveStatus.text(__("Saving…"));
      const r = await frappe.call({
        method: "logistics.warehousing.api.update_job_operations_times",
        args: { warehouse_job: this.state.job, updates_json: JSON.stringify(updates) },
        freeze: true, freeze_message: __("Saving operation times…"),
      });
      const upd = r?.message?.updated || 0;
      this.$opsSaveStatus.text(__("Saved {0} row(s).", [upd]));
      frappe.show_alert({ message: __("Operation times updated"), indicator: "green" });

      // Refresh overview to reflect computed actual_hours from server
      await this.reload_overview();
    } catch (e) {
      console.error(e);
      this.$opsSaveStatus.text(__("Error"));
      frappe.msgprint({ title: __("Error"), message: __("Failed to save. See console."), indicator: "red" });
    }
  }

  async reload_overview() {
    if (!this.state.job) return;
    const r2 = await frappe.call({
      method: "logistics.warehousing.api.get_warehouse_job_overview",
      args: { warehouse_job: this.state.job },
    });
    const d = r2?.message || {};
    this.state.header = d.header || null;
    this.state.operations = d.operations || [];
    this.render_header();
    this.render_operations();
  }

  async post_by_scan() {
    if (!this.state.job) { frappe.msgprint(__("Scan/load a Warehouse Job first.")); return; }

    const action = (this.$postAction.val() || "").trim();
    const loc = (this.$postLoc.val() || "").trim();
    const hu  = (this.$postHU.val() || "").trim();
    const qty = parseFloat(this.$postQty.val() || "0");
    const item= (this.$postItem.val() || "").trim();

    if (!action) { frappe.msgprint(__("Select an Action")); return; }
    // For Pick/Putaway, we typically want at least Location or HU; but let server filter.

    try {
      const r = await frappe.call({
        method: "logistics.warehousing.api.post_job_by_scan",
        args: {
          warehouse_job: this.state.job,
          action, location_code: loc || null, handling_unit_code: hu || null,
          qty: isNaN(qty) || qty <= 0 ? null : qty,
          item: item || null,
        },
        freeze: true, freeze_message: __("Posting…"),
      });
      const m = r?.message || {};
      const msg = m.message || __("Posted.");
      this.$postResult.html(frappe.utils.escape_html(msg));
      frappe.show_alert({ message: msg, indicator: "green" });

      // Repaint header after posting (statuses, etc.)
      await this.reload_overview();
    } catch (e) {
      console.error(e);
      this.$postResult.html(`<span class="text-danger">${__("Error posting. See console.")}</span>`);
    }
  }
}
