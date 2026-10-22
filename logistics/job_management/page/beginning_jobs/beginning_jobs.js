// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

frappe.pages["beginning-jobs"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("New Shipment"),
		single_column: true,
	});
	frappe.beginning_jobs = new BeginningJobsPage(page);
};

const FREIGHT_TYPES = ["Air Shipment", "Sea Shipment"];
const FILE_TITLES = {
	"Air Shipment": __("New Air Shipment"),
	"Sea Shipment": __("New Sea Shipment"),
	"Transport Job": __("New Transport Job"),
	Declaration: __("New Declaration"),
	"Warehouse Job": __("New Warehouse Job"),
};
const PRIOR_POSTED = "Posted in Prior System";

class BeginningJobsPage {
	constructor(page) {
		this.page = page;
		$(this.page.wrapper).addClass("beginning-jobs-form");
		this.page.set_indicator(__("Not Saved"), "orange");
		this.page.set_primary_action(__("Save"), () => this.create(), "save");
		this.make();
	}

	make() {
		this.form = new frappe.ui.FieldGroup({
			body: this.page.body,
			// Tab ids are scrubbed from the layout doctype. This page has no document.
			doctype: "Beginning Jobs",
			no_submit_on_enter: true,
			fields: this.form_fields(),
		});
		this.form.make();
		const company = frappe.defaults.get_user_default("company");
		if (company) {
			this.form.set_value("company", company);
		}
		this.form.fields_dict.file_type.df.onchange = () => {
			this.refresh_title();
			this.refresh_customer_label();
			this.sync_required();
		};
		this.bind_leg_numbers();
		this.refresh_title();
		this.refresh_customer_label();
		this.sync_required();
	}

	form_fields() {
		const freight = "eval:in_list(['Air Shipment', 'Sea Shipment'], doc.file_type)";
		const not_warehouse = "eval:doc.file_type && doc.file_type!='Warehouse Job'";
		return [
			{ fieldtype: "Section Break", label: __("Shipment Details") },
			{
				fieldname: "file_type",
				label: __("File Type"),
				fieldtype: "Select",
				options: "\nAir Shipment\nSea Shipment\nTransport Job\nDeclaration\nWarehouse Job",
				reqd: 1,
			},
			{
				fieldname: "is_beginning_job",
				label: __("Beginning Job"),
				fieldtype: "Check",
				default: 1,
				read_only: 1,
				description: __(
					"Encoded from the old system by Beginning Jobs. No Sales Quote, booking, or order is required."
				),
			},
			{
				fieldname: "job_number",
				label: __("Shipment / Job Number"),
				fieldtype: "Data",
				reqd: 1,
				description: __("This number becomes the file name."),
			},
			{
				fieldname: "booking_date",
				label: __("Booking Date"),
				fieldtype: "Date",
				reqd: 1,
				default: "Today",
			},
			{
				fieldname: "job_status",
				label: __("Job Status"),
				fieldtype: "Select",
				options: "Draft",
				default: "Draft",
				read_only: 1,
			},
			{
				fieldname: "company",
				label: __("Company"),
				fieldtype: "Link",
				options: "Company",
				reqd: 1,
			},
			{
				fieldname: "direction",
				label: __("Direction"),
				fieldtype: "Select",
				options: "\nImport\nExport\nDomestic",
				depends_on: freight,
			},
			{ fieldtype: "Column Break" },
			{
				fieldname: "customer",
				label: __("Local Customer"),
				fieldtype: "Link",
				options: "Customer",
				reqd: 1,
			},
			{
				fieldname: "shipper",
				label: __("Shipper"),
				fieldtype: "Link",
				options: "Shipper",
				depends_on: not_warehouse,
			},
			{
				fieldname: "consignee",
				label: __("Consignee"),
				fieldtype: "Link",
				options: "Consignee",
				depends_on: not_warehouse,
			},
			{
				fieldname: "branch",
				label: __("Branch"),
				fieldtype: "Link",
				options: "Branch",
				reqd: 1,
			},
			{
				fieldname: "cost_center",
				label: __("Cost Center"),
				fieldtype: "Link",
				options: "Cost Center",
				reqd: 1,
			},
			{
				fieldname: "profit_center",
				label: __("Profit Center"),
				fieldtype: "Link",
				options: "Profit Center",
				reqd: 1,
			},
			{
				fieldtype: "Section Break",
				label: __("Routing"),
				depends_on: "eval:doc.file_type",
			},
			{
				fieldname: "origin_port",
				label: __("Origin Port"),
				fieldtype: "Link",
				options: "UNLOCO",
				depends_on: freight,
			},
			{
				fieldname: "destination_port",
				label: __("Destination Port"),
				fieldtype: "Link",
				options: "UNLOCO",
				depends_on: freight,
			},
			{
				fieldname: "total_weight",
				label: __("Total Weight"),
				fieldtype: "Float",
				depends_on: freight,
			},
			{
				fieldname: "total_volume",
				label: __("Total Volume"),
				fieldtype: "Float",
				depends_on: freight,
			},
			{ fieldtype: "Column Break" },
			{
				fieldname: "airline",
				label: __("Airline"),
				fieldtype: "Link",
				options: "Airline",
				depends_on: "eval:doc.file_type=='Air Shipment'",
			},
			{
				fieldname: "shipping_line",
				label: __("Shipping Line"),
				fieldtype: "Link",
				options: "Shipping Line",
				depends_on: "eval:doc.file_type=='Sea Shipment'",
			},
			{
				fieldname: "vehicle_type",
				label: __("Vehicle Type"),
				fieldtype: "Link",
				options: "Vehicle Type",
				depends_on: "eval:doc.file_type=='Transport Job'",
			},
			{
				fieldname: "warehouse_type",
				label: __("Warehouse Job Type"),
				fieldtype: "Select",
				options: "VAS\nCross Dock\nPutaway\nPick\nMove\nStocktake",
				default: "VAS",
				depends_on: "eval:doc.file_type=='Warehouse Job'",
			},
			{
				fieldname: "customs_authority",
				label: __("Customs Authority"),
				fieldtype: "Link",
				options: "Customs Authority",
				depends_on: "eval:doc.file_type=='Declaration'",
			},
			{
				fieldname: "declaration_type",
				label: __("Declaration Type"),
				fieldtype: "Link",
				options: "Declaration Type",
				depends_on: "eval:doc.file_type=='Declaration'",
			},
			{ fieldtype: "Tab Break", label: __("Services") },
			{
				fieldname: "legs",
				label: __("Services"),
				fieldtype: "Table",
				description: __(
					"Each row becomes its own file, linked to this shipment, with its own number and charges."
				),
				fields: this.service_fields(),
			},
			{ fieldtype: "Tab Break", label: __("Charges") },
			{
				fieldname: "charges",
				label: __("Charges"),
				fieldtype: "Table",
				description: __(
					"Set Revenue Invoice Status or Cost Invoice Status to Posted in Prior System when that side was already posted in the old system."
				),
				fields: this.charge_fields(),
			},
		];
	}

	service_fields() {
		return [
			{
				fieldname: "service_type",
				label: __("Service Type"),
				fieldtype: "Select",
				options: "\nAir\nSea\nTransport\nCustoms\nWarehousing\nCross-Docking",
				in_list_view: 1,
				columns: 2,
			},
			{
				fieldname: "job_number",
				label: __("Job Number"),
				fieldtype: "Data",
				in_list_view: 1,
				columns: 2,
			},
			{
				fieldname: "direction",
				label: __("Direction"),
				fieldtype: "Select",
				options: "\nImport\nExport\nDomestic",
				in_list_view: 1,
				columns: 2,
			},
			{
				fieldname: "origin_port",
				label: __("Origin Port"),
				fieldtype: "Link",
				options: "UNLOCO",
				in_list_view: 1,
				columns: 2,
			},
			{
				fieldname: "destination_port",
				label: __("Destination Port"),
				fieldtype: "Link",
				options: "UNLOCO",
				in_list_view: 1,
				columns: 2,
			},
			{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company" },
			{
				fieldname: "vehicle_type",
				label: __("Vehicle Type"),
				fieldtype: "Link",
				options: "Vehicle Type",
			},
			{
				fieldname: "location_type",
				label: __("Location Type"),
				fieldtype: "Select",
				options: "\nUNLOCO\nTransport Zone",
				onchange() {
					const grid = this.grid;
					const doctype = this.get_value() || "UNLOCO";
					["location_from", "location_to"].forEach((name) => {
						const df = (grid.docfields || []).find((field) => field.fieldname === name);
						if (df) df.options = doctype;
						const control = this.grid_row && this.grid_row.on_grid_fields_dict[name];
						if (!control) return;
						control.df.options = doctype;
						control.refresh();
					});
				},
			},
			{
				fieldname: "location_from",
				label: __("Location From"),
				fieldtype: "Link",
				options: "UNLOCO",
			},
			{
				fieldname: "location_to",
				label: __("Location To"),
				fieldtype: "Link",
				options: "UNLOCO",
			},
			{
				fieldname: "customs_authority",
				label: __("Customs Authority"),
				fieldtype: "Link",
				options: "Customs Authority",
			},
		];
	}

	charge_fields() {
		const status_options = `\nNot Requested\n${PRIOR_POSTED}`;
		return [
			{
				fieldname: "applies_to",
				label: __("Applies To"),
				fieldtype: "Select",
				options: "main",
				default: "main",
				in_list_view: 1,
				columns: 1,
			},
			{
				fieldname: "item_code",
				label: __("Item Code"),
				fieldtype: "Link",
				options: "Item",
				in_list_view: 1,
				columns: 2,
			},
			{
				fieldname: "charge_type",
				label: __("Charge Type"),
				fieldtype: "Select",
				options: "Margin\nDisbursement\nRevenue\nCost",
				default: "Margin",
				in_list_view: 1,
				columns: 1,
			},
			{
				fieldname: "quantity",
				label: __("Quantity"),
				fieldtype: "Float",
				default: "1",
				in_list_view: 1,
				columns: 1,
			},
			{
				fieldname: "unit_rate",
				label: __("Unit Rate"),
				fieldtype: "Currency",
				in_list_view: 1,
				columns: 1,
			},
			{
				fieldname: "currency",
				label: __("Currency"),
				fieldtype: "Link",
				options: "Currency",
				in_list_view: 1,
				columns: 1,
			},
			{
				fieldname: "bill_to",
				label: __("Bill To"),
				fieldtype: "Link",
				options: "Customer",
				in_list_view: 1,
				columns: 2,
			},
			{
				fieldname: "pay_to",
				label: __("Pay To"),
				fieldtype: "Link",
				options: "Supplier",
				in_list_view: 1,
				columns: 1,
			},
			{
				fieldname: "sales_invoice_status",
				label: __("Revenue Invoice Status"),
				fieldtype: "Select",
				options: status_options,
				default: "Not Requested",
				in_list_view: 1,
				columns: 2,
			},
			{
				fieldname: "purchase_invoice_status",
				label: __("Cost Invoice Status"),
				fieldtype: "Select",
				options: status_options,
				default: "Not Requested",
				in_list_view: 1,
				columns: 2,
			},
			{ fieldname: "description", label: __("Description"), fieldtype: "Data" },
			{
				fieldname: "unit_cost",
				label: __("Unit Cost"),
				fieldtype: "Currency",
			},
			{
				fieldname: "cost_currency",
				label: __("Cost Currency"),
				fieldtype: "Link",
				options: "Currency",
			},
		];
	}

	refresh_title() {
		const file_type = this.form.get_value("file_type");
		this.page.set_title(FILE_TITLES[file_type] || __("New Shipment"));
	}

	refresh_customer_label() {
		const file_type = this.form.get_value("file_type");
		const field = this.form.get_field("customer");
		if (!field) return;
		const local_customer = !file_type || FREIGHT_TYPES.includes(file_type);
		field.df.label = local_customer ? __("Local Customer") : __("Customer");
		field.refresh();
	}

	sync_required() {
		const file_type = this.form.get_value("file_type");
		const freight = FREIGHT_TYPES.includes(file_type);
		const reqd = {
			direction: freight,
			shipper: freight,
			consignee: freight,
			origin_port: freight,
			destination_port: freight,
			total_weight: file_type === "Air Shipment",
			total_volume: file_type === "Air Shipment",
			customs_authority: file_type === "Declaration",
		};
		Object.keys(reqd).forEach((name) => {
			const field = this.form.get_field(name);
			if (!field) return;
			field.df.reqd = reqd[name] ? 1 : 0;
			field.refresh();
		});
		this.form.refresh_dependency();
	}

	bind_leg_numbers() {
		const grid = this.form.get_field("legs").grid;
		const refresh = grid.refresh.bind(grid);
		grid.refresh = (...args) => {
			const result = refresh(...args);
			this.refresh_charge_targets();
			return result;
		};
	}

	refresh_charge_targets() {
		const legs = this.form.get_value("legs") || [];
		const numbers = [];
		legs.forEach((row) => {
			const number = ((row && row.job_number) || "").trim();
			if (number && !numbers.includes(number)) numbers.push(number);
		});
		const options = ["main"].concat(numbers).join("\n");
		const grid = this.form.get_field("charges").grid;
		const df = (grid.docfields || []).find((field) => field.fieldname === "applies_to");
		if (!df || df.options === options) return;
		df.options = options;
		(grid.grid_rows || []).forEach((row) => {
			if (row.doc.applies_to && row.doc.applies_to !== "main" && !numbers.includes(row.doc.applies_to)) {
				row.doc.applies_to = "main";
			}
		});
		grid.refresh();
	}

	missing_required() {
		this.form.refresh_dependency();
		const file_type = this.form.get_value("file_type");
		const freight = FREIGHT_TYPES.includes(file_type);
		const required = [
			"file_type",
			"job_number",
			"company",
			"customer",
			"booking_date",
			"branch",
			"cost_center",
			"profit_center",
		];
		if (freight) {
			required.push("direction", "shipper", "consignee", "origin_port", "destination_port");
		}
		if (file_type === "Air Shipment") {
			required.push("total_weight", "total_volume");
		}
		if (file_type === "Declaration") {
			required.push("customs_authority");
		}
		return required
			.filter((name) => !this.form.get_value(name))
			.map((name) => {
				const field = this.form.get_field(name);
				return (field && field.df.label) || __(name);
			});
	}

	header_payload() {
		const names = [
			"job_number",
			"company",
			"customer",
			"booking_date",
			"direction",
			"shipper",
			"consignee",
			"origin_port",
			"destination_port",
			"total_weight",
			"total_volume",
			"branch",
			"cost_center",
			"profit_center",
			"airline",
			"shipping_line",
			"vehicle_type",
			"warehouse_type",
			"customs_authority",
			"declaration_type",
		];
		const header = {};
		names.forEach((name) => {
			const value = this.form.get_value(name);
			if (value) header[name] = value;
		});
		return header;
	}

	clean_row(row) {
		const copy = {};
		Object.keys(row || {}).forEach((key) => {
			if (key === "idx" || key === "name" || key.startsWith("__")) return;
			const value = row[key];
			if (value !== undefined && value !== null && value !== "") copy[key] = value;
		});
		return copy;
	}

	service_rows() {
		return (this.form.get_value("legs") || [])
			.map((row) => this.clean_row(row))
			.filter((row) => Object.keys(row).length);
	}

	charge_rows() {
		return (this.form.get_value("charges") || [])
			.map((row) => this.clean_row(row))
			.filter((row) => this.charge_started(row))
			.map((row) => ({
				applies_to: row.applies_to || "main",
				item_code: row.item_code,
				description: row.description,
				charge_type: row.charge_type,
				quantity: row.quantity,
				unit_rate: row.unit_rate,
				currency: row.currency,
				unit_cost: row.unit_cost,
				cost_currency: row.cost_currency,
				bill_to: row.bill_to,
				pay_to: row.pay_to,
				revenue_posted: row.sales_invoice_status === PRIOR_POSTED ? 1 : 0,
				cost_posted: row.purchase_invoice_status === PRIOR_POSTED ? 1 : 0,
			}));
	}

	charge_started(row) {
		if (
			row.item_code ||
			row.description ||
			row.unit_rate ||
			row.unit_cost ||
			row.currency ||
			row.cost_currency ||
			row.bill_to ||
			row.pay_to
		) {
			return true;
		}
		if (row.sales_invoice_status === PRIOR_POSTED || row.purchase_invoice_status === PRIOR_POSTED) {
			return true;
		}
		if (row.charge_type && row.charge_type !== "Margin") return true;
		if (row.quantity && Number(row.quantity) !== 1) return true;
		if (row.applies_to && row.applies_to !== "main") return true;
		return false;
	}

	create() {
		const missing = this.missing_required();
		if (missing.length) {
			frappe.msgprint({
				title: __("Missing Values Required"),
				message: __("Fill required fields: {0}", [missing.join(", ")]),
				indicator: "red",
			});
			return;
		}
		const legs = this.service_rows();
		const incomplete_leg = legs.find((row) => !row.service_type || !row.job_number);
		if (incomplete_leg) {
			frappe.msgprint({
				title: __("Services"),
				message: __("Each service needs a service type and a job number."),
				indicator: "red",
			});
			return;
		}
		const started = (this.form.get_value("charges") || [])
			.map((row) => this.clean_row(row))
			.filter((row) => this.charge_started(row));
		if (started.some((row) => !row.item_code)) {
			frappe.msgprint({
				title: __("Charges"),
				message: __("Each charge needs an Item Code."),
				indicator: "red",
			});
			return;
		}
		const payload = {
			file_type: this.form.get_value("file_type"),
			header: this.header_payload(),
			legs,
			charges: this.charge_rows(),
		};
		frappe.call({
			method: "logistics.job_management.page.beginning_jobs.beginning_jobs.create_beginning_job",
			args: { payload },
			freeze: true,
			freeze_message: __("Saving"),
			callback: (r) => {
				if (!r.message) return;
				frappe.show_alert({
					message: __("Beginning job {0} created", [r.message.name]),
					indicator: "green",
				});
				frappe.set_route("Form", r.message.doctype, r.message.name);
			},
		});
	}
}
