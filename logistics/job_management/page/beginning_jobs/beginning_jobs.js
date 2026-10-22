// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

frappe.pages["beginning-jobs"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Beginning Jobs"),
		single_column: true,
	});
	frappe.beginning_jobs = new BeginningJobsPage(page);
};

class BeginningJobsPage {
	constructor(page) {
		this.page = page;
		this.legs = [];
		this.charges = [];
		this.controls = {};
		this.make();
	}

	make() {
		this.page.set_primary_action(__("Create File"), () => this.create(), "add");
		const $body = $(this.page.body);
		$body.html(`
			<div class="beginning-jobs-page">
				<section class="bj-card">
					<h4>${__("Main file")}</h4>
					<p class="bj-help">${__(
						"Encode a pending shipment from the old system. The number you enter becomes the file name. Milestones, tasks, and documents are added the same way as a normal shipment."
					)}</p>
					<div class="bj-grid" data-section="main"></div>
				</section>
				<section class="bj-card">
					<div class="bj-toolbar">
						<h4>${__("Linked services")}</h4>
						<button class="btn btn-default btn-sm" data-action="add-leg">${__("Add Linked Service")}</button>
					</div>
					<p class="bj-help">${__(
						"Optional. Each service becomes its own file, linked to the main file, with its own number and charges."
					)}</p>
					<div data-section="legs"></div>
				</section>
				<section class="bj-card">
					<div class="bj-toolbar">
						<h4>${__("Charges")}</h4>
						<button class="btn btn-default btn-sm" data-action="add-charge">${__("Add Charge")}</button>
					</div>
					<p class="bj-help">${__(
						"Tick revenue or cost when that side was already posted in the old system. Unticked sides can still be invoiced here."
					)}</p>
					<div data-section="charges"></div>
				</section>
			</div>
		`);
		this.$main = $body.find('[data-section="main"]');
		this.$legs = $body.find('[data-section="legs"]');
		this.$charges = $body.find('[data-section="charges"]');
		this.add_main_fields();
		$body.on("click", "[data-action='add-leg']", () => this.add_leg());
		$body.on("click", "[data-action='add-charge']", () => this.add_charge());
		this.add_charge();
	}

	control(parent, df) {
		const field = frappe.ui.form.make_control({
			parent,
			df,
			render_input: true,
		});
		return field;
	}

	add_main_fields() {
		const fields = [
			{ fieldname: "file_type", label: __("File Type"), fieldtype: "Select", options: "\nAir Shipment\nSea Shipment\nTransport Job\nDeclaration\nWarehouse Job", reqd: 1 },
			{ fieldname: "job_number", label: __("Shipment / Job Number"), fieldtype: "Data", reqd: 1 },
			{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", reqd: 1, default: frappe.defaults.get_user_default("company") },
			{ fieldname: "customer", label: __("Customer"), fieldtype: "Link", options: "Customer", reqd: 1 },
			{ fieldname: "booking_date", label: __("Booking Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today() },
			{ fieldname: "direction", label: __("Direction"), fieldtype: "Select", options: "\nImport\nExport\nDomestic" },
			{ fieldname: "shipper", label: __("Shipper"), fieldtype: "Link", options: "Shipper" },
			{ fieldname: "consignee", label: __("Consignee"), fieldtype: "Link", options: "Consignee" },
			{ fieldname: "origin_port", label: __("Origin Port"), fieldtype: "Link", options: "UNLOCO" },
			{ fieldname: "destination_port", label: __("Destination Port"), fieldtype: "Link", options: "UNLOCO" },
			{ fieldname: "total_weight", label: __("Total Weight"), fieldtype: "Float" },
			{ fieldname: "total_volume", label: __("Total Volume"), fieldtype: "Float" },
			{ fieldname: "branch", label: __("Branch"), fieldtype: "Link", options: "Branch", reqd: 1 },
			{ fieldname: "cost_center", label: __("Cost Center"), fieldtype: "Link", options: "Cost Center", reqd: 1 },
			{ fieldname: "profit_center", label: __("Profit Center"), fieldtype: "Link", options: "Profit Center", reqd: 1 },
			{ fieldname: "shipping_line", label: __("Shipping Line"), fieldtype: "Link", options: "Shipping Line" },
			{ fieldname: "vehicle_type", label: __("Vehicle Type"), fieldtype: "Link", options: "Vehicle Type" },
			{ fieldname: "warehouse_type", label: __("Warehouse Job Type"), fieldtype: "Select", options: "VAS\nCross Dock\nPutaway\nPick\nMove\nStocktake", default: "VAS" },
			{ fieldname: "customs_authority", label: __("Customs Authority"), fieldtype: "Link", options: "Customs Authority" },
			{ fieldname: "declaration_type", label: __("Declaration Type"), fieldtype: "Link", options: "Declaration Type" },
		];
		fields.forEach((df) => {
			const $wrap = $('<div class="bj-field"></div>').appendTo(this.$main);
			this.controls[df.fieldname] = this.control($wrap.get(0), df);
			if (df.default) {
				this.controls[df.fieldname].set_value(df.default);
			}
		});
		this.controls.file_type.df.onchange = () => this.toggle_main_fields();
		this.toggle_main_fields();
	}

	toggle_main_fields() {
		const file_type = this.value("file_type");
		const freight = file_type === "Air Shipment" || file_type === "Sea Shipment";
		const show = {
			direction: freight,
			shipper: file_type && file_type !== "Warehouse Job",
			consignee: file_type && file_type !== "Warehouse Job",
			origin_port: freight,
			destination_port: freight,
			total_weight: freight,
			total_volume: freight,
			shipping_line: file_type === "Sea Shipment",
			vehicle_type: file_type === "Transport Job",
			warehouse_type: file_type === "Warehouse Job",
			customs_authority: file_type === "Declaration",
			declaration_type: file_type === "Declaration",
		};
		Object.keys(show).forEach((name) => {
			const control = this.controls[name];
			if (!control) return;
			control.$wrapper.closest(".bj-field").toggle(!!show[name]);
		});
	}

	value(name) {
		const control = this.controls[name];
		return control ? control.get_value() : null;
	}

	add_leg() {
		const id = frappe.utils.get_random(8);
		const $row = $(`<div class="bj-row" data-leg="${id}"><div class="bj-grid"></div><div class="bj-row-actions"><button class="btn btn-xs btn-default" data-remove-leg="${id}">${__("Remove")}</button></div></div>`);
		this.$legs.append($row);
		const fields = {};
		const specs = [
			{ fieldname: "service_type", label: __("Service Type"), fieldtype: "Select", options: "\nAir\nSea\nTransport\nCustoms\nWarehousing\nCross-Docking", reqd: 1 },
			{ fieldname: "job_number", label: __("Job Number"), fieldtype: "Data", reqd: 1 },
			{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company" },
			{ fieldname: "direction", label: __("Direction"), fieldtype: "Select", options: "\nImport\nExport\nDomestic" },
			{ fieldname: "origin_port", label: __("Origin Port"), fieldtype: "Link", options: "UNLOCO" },
			{ fieldname: "destination_port", label: __("Destination Port"), fieldtype: "Link", options: "UNLOCO" },
			{ fieldname: "vehicle_type", label: __("Vehicle Type"), fieldtype: "Link", options: "Vehicle Type" },
			{ fieldname: "location_type", label: __("Location Type"), fieldtype: "Select", options: "\nUNLOCO\nTransport Zone" },
			{ fieldname: "location_from", label: __("Location From"), fieldtype: "Link", options: "UNLOCO" },
			{ fieldname: "location_to", label: __("Location To"), fieldtype: "Link", options: "UNLOCO" },
			{ fieldname: "customs_authority", label: __("Customs Authority"), fieldtype: "Link", options: "Customs Authority" },
		];
		specs.forEach((df) => {
			const $wrap = $('<div class="bj-field"></div>').appendTo($row.find(".bj-grid"));
			fields[df.fieldname] = this.control($wrap.get(0), df);
		});
		fields.job_number.df.onchange = () => this.refresh_charge_targets();
		fields.location_type.df.onchange = () => {
			const location_doctype = fields.location_type.get_value() || "UNLOCO";
			["location_from", "location_to"].forEach((name) => {
				fields[name].df.options = location_doctype;
				fields[name].refresh();
			});
		};
		this.legs.push({ id, fields, $row });
		$row.on("click", `[data-remove-leg="${id}"]`, () => this.remove_leg(id));
	}

	remove_leg(id) {
		this.legs = this.legs.filter((leg) => leg.id !== id);
		this.$legs.find(`[data-leg="${id}"]`).remove();
		this.refresh_charge_targets();
	}

	add_charge() {
		const id = frappe.utils.get_random(8);
		const $row = $(`<div class="bj-row" data-charge="${id}"><div class="bj-grid"></div><div class="bj-row-actions"><button class="btn btn-xs btn-default" data-remove-charge="${id}">${__("Remove")}</button></div></div>`);
		this.$charges.append($row);
		const fields = {};
		const specs = [
			{ fieldname: "applies_to", label: __("Applies To"), fieldtype: "Select", options: this.charge_target_options(), default: "main" },
			{ fieldname: "item_code", label: __("Item"), fieldtype: "Link", options: "Item", reqd: 1 },
			{ fieldname: "description", label: __("Description"), fieldtype: "Data" },
			{ fieldname: "charge_type", label: __("Charge Type"), fieldtype: "Select", options: "Margin\nDisbursement\nRevenue\nCost", default: "Margin" },
			{ fieldname: "quantity", label: __("Quantity"), fieldtype: "Float", default: 1 },
			{ fieldname: "unit_rate", label: __("Sell Rate"), fieldtype: "Currency" },
			{ fieldname: "currency", label: __("Sell Currency"), fieldtype: "Link", options: "Currency" },
			{ fieldname: "unit_cost", label: __("Cost Rate"), fieldtype: "Currency" },
			{ fieldname: "cost_currency", label: __("Cost Currency"), fieldtype: "Link", options: "Currency" },
			{ fieldname: "bill_to", label: __("Bill To"), fieldtype: "Link", options: "Customer" },
			{ fieldname: "pay_to", label: __("Pay To"), fieldtype: "Link", options: "Supplier" },
			{ fieldname: "revenue_posted", label: __("Revenue posted in prior system"), fieldtype: "Check" },
			{ fieldname: "cost_posted", label: __("Cost posted in prior system"), fieldtype: "Check" },
		];
		specs.forEach((df) => {
			const $wrap = $('<div class="bj-field"></div>').appendTo($row.find(".bj-grid"));
			fields[df.fieldname] = this.control($wrap.get(0), df);
			if (df.default !== undefined) {
				fields[df.fieldname].set_value(df.default);
			}
		});
		this.charges.push({ id, fields, $row });
		$row.on("click", `[data-remove-charge="${id}"]`, () => {
			this.charges = this.charges.filter((row) => row.id !== id);
			$row.remove();
		});
	}

	charge_target_options() {
		const options = ["main"];
		this.legs.forEach((leg) => {
			const number = leg.fields.job_number && leg.fields.job_number.get_value();
			if (number) options.push(number);
		});
		return options.join("\n");
	}

	refresh_charge_targets() {
		const options = this.charge_target_options();
		this.charges.forEach((row) => {
			const control = row.fields.applies_to;
			const current = control.get_value();
			control.df.options = options;
			control.refresh();
			if (options.split("\n").includes(current)) {
				control.set_value(current);
			} else {
				control.set_value("main");
			}
		});
	}

	missing_required() {
		const file_type = this.value("file_type");
		const required = ["file_type", "job_number", "company", "customer", "booking_date", "branch", "cost_center", "profit_center"];
		if (file_type === "Air Shipment" || file_type === "Sea Shipment") {
			required.push("direction", "shipper", "consignee", "origin_port", "destination_port");
		}
		if (file_type === "Air Shipment") {
			required.push("total_weight", "total_volume");
		}
		if (file_type === "Declaration") {
			required.push("customs_authority");
		}
		return required
			.filter((name) => !this.value(name))
			.map((name) => (this.controls[name] && this.controls[name].df.label) || __(name));
	}

	header_payload() {
		const names = [
			"job_number", "company", "customer", "booking_date", "direction", "shipper", "consignee",
			"origin_port", "destination_port", "total_weight", "total_volume", "branch", "cost_center", "profit_center",
			"shipping_line", "vehicle_type", "warehouse_type", "customs_authority", "declaration_type",
		];
		const header = {};
		names.forEach((name) => {
			const value = this.value(name);
			if (value) header[name] = value;
		});
		return header;
	}

	create() {
		const missing = this.missing_required();
		if (missing.length) {
			frappe.msgprint({
				title: __("Beginning Jobs"),
				message: __("Fill required fields: {0}", [missing.join(", ")]),
				indicator: "red",
			});
			return;
		}
		this.refresh_charge_targets();
		const payload = {
			file_type: this.value("file_type"),
			header: this.header_payload(),
			legs: this.legs.map((leg) => {
				const row = {};
				Object.keys(leg.fields).forEach((name) => {
					const value = leg.fields[name].get_value();
					if (value) row[name] = value;
				});
				return row;
			}),
			charges: this.charges.map((row) => {
				const charge = {};
				Object.keys(row.fields).forEach((name) => {
					const value = row.fields[name].get_value();
					if (value !== undefined && value !== null && value !== "") charge[name] = value;
				});
				return charge;
			}).filter((row) => row.item_code),
		};
		frappe.call({
			method: "logistics.job_management.page.beginning_jobs.beginning_jobs.create_beginning_job",
			args: { payload },
			freeze: true,
			freeze_message: __("Creating beginning job"),
			callback: (r) => {
				if (!r.message) return;
				frappe.show_alert({ message: __("Beginning job {0} created", [r.message.name]), indicator: "green" });
				frappe.set_route("Form", r.message.doctype, r.message.name);
			},
		});
	}
}
