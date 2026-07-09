frappe.provide("logistics.workflow_center");

const WC_SEGMENTS = [
	{ key: "at_risk", title: __("At risk"), desc: __("Overdue or approaching critical SLA limits"), className: "at-risk" },
	{ key: "delay_risk", title: __("Delay risk"), desc: __("Already overdue and likely to block downstream work"), className: "delay-risk" },
	{ key: "penalty_risk", title: __("Penalty risk"), desc: __("Critical SLA breaches that may trigger penalties"), className: "penalty-risk" },
	{ key: "todays_tasks", title: __("Today's tasks"), desc: __("New workflow actions assigned to you today"), className: "todays-tasks" },
	{ key: "compliance_gaps", title: __("Compliance gaps"), desc: __("Missing SLA setup or incomplete workflow metadata"), className: "compliance-gaps" },
	{ key: "open_actions", title: __("Open actions"), desc: __("All visible workflow actions in your current filter"), className: "open-actions" },
];

const WC_EMPTY_MESSAGES = {
	at_risk: __("No at-risk items."),
	delay_risk: __("No delay-risk items."),
	penalty_risk: __("No penalty-risk items."),
	todays_tasks: __("No new workflow actions for you today."),
	compliance_gaps: __("No compliance gap items."),
	open_actions: __("No open workflow actions match your current filters."),
};

const WC_FILTER_API_METHODS = [
	"logistics.workflow_center.api.get_workflow_center_filter_options",
	"workflow_center.api.get_workflow_center_filter_options",
	"workflow_center.workflow_center.api.get_workflow_center_filter_options",
];

const WC_DASHBOARD_API_METHODS = [
	"logistics.workflow_center.api.get_workflow_center_dashboard",
	"workflow_center.api.get_workflow_center_dashboard",
	"workflow_center.workflow_center.api.get_workflow_center_dashboard",
];

async function wc_call_first(methods, args = {}) {
	let last_error = null;
	for (const method of methods) {
		try {
			const response = await frappe.call({ method, args, freeze: false });
			if (response?.message !== undefined) {
				return response.message;
			}
		} catch (error) {
			last_error = error;
		}
	}
	throw last_error || new Error(__("Workflow Center API is unavailable."));
}

async function wc_fallback_open_actions() {
	const response = await frappe.call({
		method: "frappe.desk.reportview.get",
		args: {
			doctype: "Workflow Action",
			fields: [
				"`tabWorkflow Action`.`name`",
				"`tabWorkflow Action`.`reference_doctype`",
				"`tabWorkflow Action`.`reference_name`",
				"`tabWorkflow Action`.`workflow_state`",
				"`tabWorkflow Action`.`modified`",
				"`tabWorkflow Action`.`creation`",
			],
			filters: [["Workflow Action", "status", "=", "Open"]],
			order_by: "`tabWorkflow Action`.`modified` desc",
			page_length: 200,
		},
		freeze: false,
	});

	const values = response?.message?.values || [];
	const items = values.map((row) => ({
		workflow_action: row[0],
		reference_doctype: row[1],
		reference_name: row[2],
		workflow_state: row[3],
		modified: row[4],
		creation: row[5],
		title: row[2],
		available_actions: [],
		permitted_role: "",
		severity: "ok",
		segment: "open_actions",
	}));

	return {
		summary: {
			counts: {
				at_risk: 0,
				delay_risk: 0,
				penalty_risk: 0,
				todays_tasks: 0,
				compliance_gaps: 0,
				open_actions: items.length,
			},
		},
		items,
	};
}

frappe.pages["workflow-center"].on_page_load = function (wrapper) {
	new logistics.workflow_center.WorkflowCenterPage(wrapper);
};

logistics.workflow_center.WorkflowCenterPage = class WorkflowCenterPage {
	constructor(wrapper) {
		this.wrapper = $(wrapper);
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Workflow Center"),
			single_column: true,
		});
		this.active_segment = "open_actions";
		this.filters = {};
		this.counts = {};
		this.items = [];
		this.filter_options = {};
		this.make_layout();
		this.load_filter_options().then(() => this.refresh());
	}

	make_layout() {
		this.$container = $(`
			<div class="wc-dashboard logistics-wc-dashboard">
				<div class="wc-header">
					<div>
						<h4 id="wc-user-name"></h4>
						<div class="text-muted" id="wc-user-meta"></div>
					</div>
					<div class="text-muted" id="wc-date"></div>
				</div>
				<div class="wc-filters">
					<select class="form-control input-sm" id="wc-filter-company"></select>
					<select class="form-control input-sm" id="wc-filter-branch"></select>
					<select class="form-control input-sm" id="wc-filter-cost-center"></select>
					<select class="form-control input-sm" id="wc-filter-profit-center"></select>
					<select class="form-control input-sm" id="wc-filter-role"></select>
					<button class="btn btn-default btn-sm" id="wc-refresh" type="button">
						<i class="fa fa-refresh"></i>
					</button>
				</div>
				<div class="wc-cards" id="wc-cards"></div>
				<div class="wc-list-header">
					<h5 id="wc-list-title"></h5>
					<div class="text-muted" id="wc-list-desc"></div>
				</div>
				<div id="wc-list"></div>
			</div>
		`);
		this.page.main.empty().append(this.$container);
		this.bind_events();
	}

	bind_events() {
		const self = this;
		this.$container.on(
			"change",
			"#wc-filter-company, #wc-filter-branch, #wc-filter-cost-center, #wc-filter-profit-center, #wc-filter-role",
			function () {
				self.collect_filters();
				self.refresh();
			}
		);
		this.$container.on("click", "#wc-refresh", () => this.refresh());
		this.$container.on("click", ".wc-card", function () {
			self.active_segment = $(this).data("segment");
			self.render_cards();
			self.render_list();
		});
		this.$container.on("click", ".wc-open-doc", function (e) {
			e.preventDefault();
			frappe.set_route("Form", $(this).data("doctype"), $(this).data("name"));
		});
	}

	collect_filters() {
		this.filters = {
			company: this.$container.find("#wc-filter-company").val() || "",
			branch: this.$container.find("#wc-filter-branch").val() || "",
			cost_center: this.$container.find("#wc-filter-cost-center").val() || "",
			profit_center: this.$container.find("#wc-filter-profit-center").val() || "",
			role: this.$container.find("#wc-filter-role").val() || "",
		};
	}

	populate_select($el, values, placeholder) {
		$el.empty();
		$el.append(`<option value="">${frappe.utils.escape_html(placeholder)}</option>`);
		(values || []).forEach((value) => {
			$el.append(`<option value="${frappe.utils.escape_html(value)}">${frappe.utils.escape_html(value)}</option>`);
		});
	}

	async load_filter_options() {
		try {
			this.filter_options = (await wc_call_first(WC_FILTER_API_METHODS)) || {};
		} catch (error) {
			this.filter_options = {
				roles: frappe.boot.user.roles || [],
				companies: [],
				branches: [],
				cost_centers: [],
				profit_centers: [],
				full_name: frappe.session.user_fullname || frappe.session.user,
				role_count: (frappe.boot.user.roles || []).length,
			};
		}

		const role_count = this.filter_options.role_count || (frappe.boot.user.roles || []).length;
		this.$container.find("#wc-user-name").text(this.filter_options.full_name || frappe.session.user);
		this.$container.find("#wc-user-meta").text(
			`${role_count} ${__("roles available for workflow filtering")}`
		);
		this.$container.find("#wc-date").text(frappe.datetime.str_to_user(frappe.datetime.get_datetime_as_string()));
		this.populate_select(this.$container.find("#wc-filter-company"), this.filter_options.companies, __("Company"));
		this.populate_select(this.$container.find("#wc-filter-branch"), this.filter_options.branches, __("Branch"));
		this.populate_select(this.$container.find("#wc-filter-cost-center"), this.filter_options.cost_centers, __("Cost Center"));
		this.populate_select(this.$container.find("#wc-filter-profit-center"), this.filter_options.profit_centers, __("Profit Center"));
		this.populate_select(this.$container.find("#wc-filter-role"), this.filter_options.roles, __("Role / User Filter"));
	}

	async refresh() {
		this.collect_filters();
		frappe.dom.freeze(__("Loading workflow actions..."));
		try {
			let data;
			try {
				data = await wc_call_first(WC_DASHBOARD_API_METHODS, { filters: this.filters });
			} catch (error) {
				data = await wc_fallback_open_actions();
			}
			this.counts = (data.summary && data.summary.counts) || {};
			this.items = data.items || [];
			this.render_cards();
			this.render_list();
		} catch (error) {
			frappe.msgprint({
				title: __("Workflow Center"),
				indicator: "red",
				message: error?.message || __("Failed to load workflow actions."),
			});
		} finally {
			frappe.dom.unfreeze();
		}
	}

	render_cards() {
		const $cards = this.$container.find("#wc-cards").empty();
		WC_SEGMENTS.forEach((seg) => {
			const count = this.counts[seg.key] || 0;
			const active = this.active_segment === seg.key ? "active" : "";
			$cards.append(`
				<div class="wc-card ${seg.className} ${active}" data-segment="${seg.key}">
					<div class="wc-card-count">${count}</div>
					<div class="wc-card-title">${seg.title}</div>
					<div class="wc-card-desc">${seg.desc}</div>
				</div>
			`);
		});
	}

	render_list() {
		const seg = WC_SEGMENTS.find((s) => s.key === this.active_segment) || WC_SEGMENTS[5];
		this.$container.find("#wc-list-title").text(seg.title);
		this.$container.find("#wc-list-desc").text(seg.desc);

		const filtered =
			this.active_segment === "open_actions"
				? this.items
				: this.items.filter((item) => item.segment === this.active_segment);
		const $list = this.$container.find("#wc-list").empty();

		if (!filtered.length) {
			$list.append(`<div class="wc-empty">${WC_EMPTY_MESSAGES[this.active_segment] || __("No items.")}</div>`);
			return;
		}

		const rows = filtered
			.map((item) => {
				const actions = (item.available_actions || []).join(", ");
				const elapsed = item.elapsed_seconds
					? frappe.datetime.comment_when(item.state_entered_at || item.modified)
					: "-";
				return `
				<tr>
					<td><a href="#" class="wc-open-doc" data-doctype="${frappe.utils.escape_html(item.reference_doctype)}" data-name="${frappe.utils.escape_html(item.reference_name)}">${frappe.utils.escape_html(item.reference_name)}</a></td>
					<td>${frappe.utils.escape_html(item.title || "")}</td>
					<td>${frappe.utils.escape_html(item.reference_doctype)}</td>
					<td>${frappe.utils.escape_html(item.workflow_state || "")}</td>
					<td>${frappe.utils.escape_html(actions)}</td>
					<td>${frappe.utils.escape_html(elapsed)}</td>
					<td><span class="wc-severity ${frappe.utils.escape_html(item.severity || "ok")}">${frappe.utils.escape_html(item.severity || "ok")}</span></td>
					<td>${frappe.utils.escape_html(item.permitted_role || "")}</td>
				</tr>
			`;
			})
			.join("");

		$list.append(`
			<div class="table-responsive">
				<table class="table table-bordered table-condensed wc-table">
					<thead>
						<tr>
							<th>${__("Document")}</th>
							<th>${__("Title")}</th>
							<th>${__("Doctype")}</th>
							<th>${__("State")}</th>
							<th>${__("Actions")}</th>
							<th>${__("Time in state")}</th>
							<th>${__("Severity")}</th>
							<th>${__("Role")}</th>
						</tr>
					</thead>
					<tbody>${rows}</tbody>
				</table>
			</div>
		`);
	}
};
