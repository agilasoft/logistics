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
      title: "",
      single_column: true,
    });
    this.state = { job: null, doc: null, operations: [] };
    this.make_layout();
    this.bind_events();
    this.maybe_load_from_route();
  }

  make_layout() {
    const $ui = $(`
      <div class="wjc-container">
        <div class="wjc-header">
          <div class="wjc-header-main">
            <div class="wjc-header-left">
              <h1>WAREHOUSE JOB CARD</h1>
              <p>Operations Management</p>
            </div>
            <div class="wjc-header-details">
              <div class="wjc-detail-item">
                <label><i class="fa fa-info-circle"></i> Status:</label>
                <span id="wjc-status">Ready</span>
              </div>
              <div class="wjc-detail-item">
                <label><i class="fa fa-briefcase"></i> Current Job:</label>
                <span id="wjc-current-job">-</span>
              </div>
              <div class="wjc-detail-item">
                <label><i class="fa fa-building"></i> Company:</label>
                <span id="wjc-company">-</span>
              </div>
              <div class="wjc-detail-item">
                <label><i class="fa fa-map-marker"></i> Branch:</label>
                <span id="wjc-branch">-</span>
              </div>
            </div>
          </div>
        </div>

        <div class="wjc-main-content">
          <div class="wjc-search-section">
            <div class="wjc-search-form">
              <div class="wjc-input-wrapper">
                <input type="text" id="wjc-input" placeholder="Enter or scan Warehouse Job (e.g., WJ-00000123)">
                <i class="fa fa-qrcode wjc-scan-icon" id="wjc-scan"></i>
              </div>
              <button id="wjc-load">Load</button>
            </div>
            <div id="wjc-head" class="wjc-job-info wjc-clickable-card"></div>
          </div>

          <div class="wjc-results-section" id="wjc-results">
            <div class="wjc-results-content" id="wjc-ops">
              <div class="wjc-waiting-state">
                <i class="fa fa-cogs"></i>
                <h3>Ready to Load</h3>
                <p>Enter a Warehouse Job ID to begin</p>
              </div>
            </div>
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
        .wjc-container {
          max-width: 1200px;
          margin: 0 auto;
          padding: 20px;
        }
        
        /* Hide built-in page title */
        .page-title {
          display: none !important;
        }
        
        .page-header {
          display: none !important;
        }
        
        .wjc-header {
          background: #fff;
          border: 1px solid #ddd;
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 20px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .wjc-header-main {
          display: flex;
          justify-content: space-between;
          padding-bottom: 12px;
          border-bottom: 1px solid #eee;
          margin-bottom: 12px;
        }
        
        .wjc-header-left h1 {
          font-size: 24px;
          font-weight: 700;
          color: #007bff;
          margin: 0 0 4px 0;
        }
        
        .wjc-header-left p {
          font-size: 14px;
          color: #666;
          margin: 0;
        }
        
        .wjc-header-details {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 16px;
        }
        
        .wjc-detail-item {
          display: flex;
          flex-direction: column;
        }
        
        .wjc-detail-item label {
          font-size: 12px;
          color: #666;
          font-weight: 600;
          margin-bottom: 2px;
        }
        
        .wjc-detail-item span {
          font-size: 14px;
          color: #000;
          font-weight: 500;
        }
        
        .wjc-main-content {
          display: flex;
          gap: 20px;
        }
        
        .wjc-search-section {
          width: 350px;
          background: #f8f9fa;
          border: 1px solid #ddd;
          border-radius: 8px;
          padding: 24px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .wjc-search-form {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        
        .wjc-input-wrapper {
          position: relative;
          display: flex;
          align-items: center;
        }
        
        .wjc-search-form input {
          padding: 12px 40px 12px 16px;
          font-size: 16px;
          border: 2px solid #ddd;
          border-radius: 6px;
          outline: none;
          transition: border-color 0.3s;
          width: 100%;
        }
        
        .wjc-search-form input:focus {
          border-color: #007bff;
        }
        
        .wjc-scan-icon {
          position: absolute;
          right: 12px;
          color: #007bff;
          cursor: pointer;
          font-size: 18px;
          transition: color 0.3s;
        }
        
        .wjc-scan-icon:hover {
          color: #0056b3;
        }
        
        .wjc-search-form button, .wjc-search-form a {
          padding: 12px 24px;
          font-size: 16px;
          font-weight: 600;
          background: #007bff;
          color: white;
          border: none;
          border-radius: 6px;
          cursor: pointer;
          transition: background-color 0.3s;
          text-decoration: none;
          text-align: center;
          display: inline-block;
        }
        
        .wjc-search-form button:hover, .wjc-search-form a:hover {
          background: #0056b3;
        }
        
        .wjc-job-info {
          margin-top: 16px;
          padding: 16px;
          background: #fff;
          border: 1px solid #e5e7eb;
          border-radius: 12px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.08);
          font-size: 14px;
          color: #666;
          cursor: pointer;
          transition: all 0.3s ease;
          border-left: 4px solid #007bff;
        }
        
        .wjc-job-info:hover {
          box-shadow: 0 8px 24px rgba(0,0,0,0.12);
          transform: translateY(-2px);
        }
        
        .wjc-job-info.wjc-clickable-card {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        
        .wjc-job-info-line {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 4px 0;
        }
        
        .wjc-job-info-label {
          font-weight: 600;
          color: #333;
          min-width: 80px;
        }
        
        .wjc-job-info-value {
          color: #666;
          text-align: right;
          flex: 1;
        }
        
        .wjc-results-section {
          flex: 1;
          background: #fff;
          border: 1px solid #ddd;
          border-radius: 8px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          padding: 24px;
        }
        
        .wjc-waiting-state {
          text-align: center;
          color: #666;
        }
        
        .wjc-waiting-state i {
          font-size: 48px;
          color: #007bff;
          margin-bottom: 16px;
          display: block;
        }
        
        .wjc-waiting-state h3 {
          font-size: 20px;
          font-weight: 600;
          margin: 0 0 8px 0;
          color: #000;
        }
        
        .wjc-waiting-state p {
          font-size: 14px;
          margin: 0;
          color: #000;
        }
        
        /* Warehouse Job Dashboard BOX Cards Style */
        .op-grid{ 
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        
        .op-card{ 
          background: white;
          border: 1px solid #e5e7eb;
          border-radius: 12px;
          padding: 16px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.08);
          transition: all 0.3s ease;
          border-left: 4px solid #667eea;
          cursor: pointer;
          margin-bottom: 8px;
        }
        
        .op-card:hover {
          box-shadow: 0 8px 24px rgba(0,0,0,0.12);
          transform: translateY(-2px);
        }
        
        .op-main{ 
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 12px;
        }
        
        .op-left {
          flex: 1;
        }
        
        .op-name{ 
          margin: 0;
          font-size: 16px;
          font-weight: 700;
          color: #333;
          line-height: 1.2;
          margin-bottom: 4px;
        }
        
        .op-desc{ 
          font-size: 12px;
          color: #6c757d;
          line-height: 1.4;
          margin-bottom: 8px;
        }
        
        .op-actions{ 
          display: flex;
          gap: 6px;
          flex-shrink: 0;
        }
        
        .op-actions .btn{ 
          padding: 4px 8px;
          font-size: 10px;
          font-weight: 600;
          border-radius: 4px;
          transition: all 0.2s ease;
          min-width: 50px;
        }
        
        .op-actions .btn:hover {
          transform: translateY(-1px);
        }
        
        .op-times{ 
          display: flex;
          justify-content: space-between;
          gap: 8px;
          margin-top: 8px;
          font-size: 10px;
          color: #6c757d;
        }
        
        .op-times > div {
          display: flex;
          flex-direction: column;
          align-items: center;
          text-align: center;
          flex: 1;
        }
        
        .op-times label{ 
          font-weight: 600;
          margin-bottom: 2px;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        
        .op-times span {
          font-weight: 500;
          color: #333;
          font-size: 11px;
        }
        
        .status-badge {
          padding: 2px 6px;
          border-radius: 10px;
          font-size: 10px;
          font-weight: 500;
          text-transform: uppercase;
          background: #f8f9fa;
          color: #6c757d;
          border: 1px solid #e9ecef;
        }
        
        .status-badge.completed {
          background: #d4edda;
          color: #155724;
          border-color: #c3e6cb;
        }
        
        .status-badge.in-progress {
          background: #cfe2ff;
          color: #084298;
          border-color: #b6d7ff;
        }
        
        .status-badge.pending {
          background: #fff3cd;
          color: #856404;
          border-color: #ffeaa7;
        }
        
        .wjc .hidden{ 
          display: none !important; 
        }
        
        @media (max-width: 768px) {
          .wjc-container {
            padding: 10px;
          }
          
          .wjc-header-main {
            flex-direction: column;
            gap: 16px;
          }
          
          .wjc-header-details {
            grid-template-columns: 1fr;
            gap: 12px;
          }
          
          .wjc-main-content {
            flex-direction: column;
            gap: 16px;
          }
          
          .wjc-search-section {
            width: 100%;
            padding: 16px;
          }
          
          .wjc-results-section {
            padding: 16px;
          }
          
          .wjc-input-wrapper input {
            font-size: 16px; /* Prevents zoom on iOS */
          }
          
          .wjc-search-form button {
            padding: 10px 16px;
            font-size: 14px;
          }
          
          .op-card {
            padding: 12px;
            margin-bottom: 8px;
          }
          
          .op-main {
            flex-direction: column;
            gap: 8px;
            align-items: flex-start;
          }
          
          .op-actions {
            width: 100%;
            justify-content: space-between;
          }
          
          .op-actions .btn {
            flex: 1;
            min-width: 0;
            margin: 0 4px;
          }
          
          .op-times {
            flex-direction: column;
            gap: 8px;
          }
          
          .op-times > div {
            flex-direction: row;
            justify-content: space-between;
            align-items: center;
          }
        }
        
        @media (max-width: 480px) {
          .wjc-container {
            padding: 5px;
          }
          
          .wjc-header {
            padding: 12px;
          }
          
          .wjc-header-left h1 {
            font-size: 20px;
          }
          
          .wjc-search-section,
          .wjc-results-section {
            padding: 12px;
          }
          
          .wjc-job-info {
            padding: 12px;
          }
          
          .wjc-job-info-line {
            flex-direction: column;
            align-items: flex-start;
            gap: 4px;
          }
          
          .wjc-job-info-value {
            text-align: left;
          }
        }
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

    // Job info card click handler
    this.page.body.on("click", ".wjc-clickable-card", () => {
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
    this.update_status("Loading", name);
    const doc = await this.fetch_job(name);
    if (!doc) { this.render_empty(); return; }

    const ops = (doc.operations || doc.warehouse_job_operations || []).slice().sort((a,b) => (a.idx||9999)-(b.idx||9999));

    this.state.job = doc.name;
    this.state.doc = doc;
    this.state.operations = ops;

    this.render_header(doc);
    this.render_operations(ops);
    this.update_status("Loaded", doc.name);
    this.update_header_info(doc);
    frappe.show_alert({ message: __("Loaded {0}", [doc.name]), indicator: "green" });
  }

  render_header(job) {
    const statusText = [__("Draft"),__("Submitted"),__("Cancelled")][job.docstatus || 0];
    
    this.$head.html(`
      <div class="wjc-job-info-line">
        <span class="wjc-job-info-label"><i class="fa fa-tag"></i> ${__("Job ID")}:</span>
        <span class="wjc-job-info-value"><b>${frappe.utils.escape_html(job.name || "")}</b></span>
      </div>
      ${job.type ? `
        <div class="wjc-job-info-line">
          <span class="wjc-job-info-label"><i class="fa fa-cogs"></i> ${__("Type")}:</span>
          <span class="wjc-job-info-value">${frappe.utils.escape_html(job.type)}</span>
        </div>
      ` : ""}
      ${job.customer ? `
        <div class="wjc-job-info-line">
          <span class="wjc-job-info-label"><i class="fa fa-user"></i> ${__("Customer")}:</span>
          <span class="wjc-job-info-value">${frappe.utils.escape_html(job.customer)}</span>
        </div>
      ` : ""}
      ${job.staging_area ? `
        <div class="wjc-job-info-line">
          <span class="wjc-job-info-label"><i class="fa fa-warehouse"></i> ${__("Staging")}:</span>
          <span class="wjc-job-info-value">${frappe.utils.escape_html(job.staging_area)}</span>
        </div>
      ` : ""}
      <div class="wjc-job-info-line">
        <span class="wjc-job-info-label"><i class="fa fa-check-circle"></i> ${__("Status")}:</span>
        <span class="wjc-job-info-value">${statusText}</span>
      </div>
    `);
  }

  render_operations(rows) {
    const make_card = (r) => {
      const safe = (x) => (x == null ? "" : String(x));
      const hasStart = !!r.start_date;
      const hasEnd   = !!r.end_date;
      const status = hasEnd ? "completed" : hasStart ? "in-progress" : "pending";
      const statusText = hasEnd ? "COMPLETED" : hasStart ? "IN PROGRESS" : "PENDING";
      
      return `
        <div class="op-card" data-row="${frappe.utils.escape_html(r.name)}">
          <div class="op-main">
            <div class="op-left">
              <div class="op-name">${frappe.utils.escape_html(safe(r.operation) || "(?)")}</div>
              <div class="op-desc">${frappe.utils.escape_html(safe(r.description) || "")}</div>
            </div>
            <div class="op-actions">
              <span class="status-badge ${status}">${statusText}</span>
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
      this.$ops.html(`
        <div class="wjc-waiting-state">
          <i class="fa fa-exclamation-triangle"></i>
          <h3>No Operations</h3>
          <p>No operations found on this job</p>
        </div>
      `);
      return;
    }

    this.$ops.html(`<div class="op-grid">${rows.map(make_card).join("")}</div>`);
    this.bind_op_buttons();
  }

  update_status(status, currentJob) {
    const $status = this.page.body.find("#wjc-status");
    const $currentJob = this.page.body.find("#wjc-current-job");
    
    if ($status.length) $status.text(status);
    if ($currentJob.length) $currentJob.text(currentJob || "-");
  }

  update_header_info(job) {
    const $company = this.page.body.find("#wjc-company");
    const $branch = this.page.body.find("#wjc-branch");
    
    if ($company.length) $company.text(job.company || "-");
    if ($branch.length) $branch.text(job.branch || "-");
  }

  render_empty() {
    this.$head.empty();
    this.update_status("Ready", "-");
    this.update_header_info({ company: "-", branch: "-" });
    this.$ops.html(`
      <div class="wjc-waiting-state">
        <i class="fa fa-cogs"></i>
        <h3>Ready to Load</h3>
        <p>Enter a Warehouse Job ID to begin</p>
      </div>
    `);
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
