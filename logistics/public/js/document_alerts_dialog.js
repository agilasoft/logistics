// Document alert cards: click opens dialog with list and Attach / View in form
(function () {
	if (typeof frappe === "undefined") return;

	function escape_html(str) {
		if (str == null) return "";
		var s = String(str);
		return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
	}

	function get_category_label(category) {
		const labels = {
			pending: "Pending",
			overdue: "Overdue",
			expiring_soon: "Expiring Soon",
			received: "Received",
			total: "All Documents",
			pending_permits: "Pending Permits",
			exemptions: "Exemptions"
		};
		return labels[category] || category;
	}

	window.logistics_show_document_list_dialog = function (doctype, docname, category, frm) {
		frappe.call({
			method: "logistics.document_management.api.get_document_list_for_category",
			args: { doctype: doctype, docname: docname, category: category },
			callback: function (r) {
				if (!r.message || !r.message.documents) {
					frappe.msgprint({ title: __("Documents"), message: __("No documents in this category."), indicator: "blue" });
					return;
				}
				const data = r.message.documents;
				const category_label = get_category_label(r.message.category);

				let table_html = `
					<div class="doc-alerts-dialog-table-wrapper" style="max-height: 400px; overflow: auto;">
						<table class="table table-bordered table-condensed" style="margin: 0;">
							<thead>
								<tr>
									<th>${__("Document Type")}</th>
									<th>${__("Status")}</th>
									<th>${__("Date Required")}</th>
									<th>${__("Expiry")}</th>
									<th>${__("Attachment")}</th>
									<th style="width: 90px;">${__("Actions")}</th>
								</tr>
							</thead>
							<tbody>
				`;
				data.forEach(function (row) {
					const dateReq = row.date_required ? frappe.datetime.str_to_user(row.date_required) : "—";
					const expiry = row.expiry_date ? frappe.datetime.str_to_user(row.expiry_date) : "—";
					const att = row.has_attachment
						? `<a href="${row.attachment}" target="_blank" class="btn btn-xs btn-default">${__("View")}</a>`
						: "—";
					table_html += `
						<tr data-idx="${row.idx}">
							<td>${escape_html(row.document_type || row.document_name || "")}</td>
							<td>${escape_html(row.status || "")}</td>
							<td>${dateReq}</td>
							<td>${expiry}</td>
							<td>${att}</td>
							<td>
								<button class="btn btn-xs btn-primary doc-alert-attach-btn" data-idx="${row.idx}">${__("Attach")}</button>
							</td>
						</tr>
					`;
				});
				table_html += "</tbody></table></div>";

				const d = new frappe.ui.Dialog({
					title: __("Document Management") + " – " + category_label,
					size: "large",
					primary_action_label: __("View in Form"),
					primary_action: function () {
						d.hide();
						if (frm && frm.layout && frm.layout.select_tab) {
							frm.layout.select_tab("documents_tab");
						}
					},
					fields: [{ fieldtype: "HTML", fieldname: "table_html", options: table_html }]
				});

				d.show();

				d.$wrapper.find(".doc-alert-attach-btn").on("click", function () {
					const idx = $(this).data("idx");
					new frappe.ui.FileUploader({
						on_success: function (file) {
							if (!file || !file.file_url) return;
							frappe.call({
								method: "logistics.document_management.api.set_document_attachment",
								args: { doctype: doctype, docname: docname, idx: idx, file_url: file.file_url },
								callback: function (r) {
									if (r.message && r.message.ok) {
										frappe.show_alert({ message: __("Attachment updated."), indicator: "green" }, 3);
										d.hide();
										if (frm && frm.reload_doc) frm.reload_doc();
									} else {
										frappe.msgprint({ title: __("Error"), message: (r.message && r.message.message) || __("Update failed."), indicator: "red" });
									}
								}
							});
						}
					});
				});
			}
		});
	};

	// Collapsible dashboard alerts: per-level groups (Critical, Warnings, Information), default collapsed
	window.logistics_group_and_collapse_dash_alerts = function ($container) {
		if (!$container || !$container.length) return;
		const $section = $container.find(".dash-alerts-section");
		if (!$section.length) return;
		const $items = $section.find(".dash-alert-item");
		if (!$items.length) return;

		const groups = { danger: [], warning: [], info: [] };
		const order = ["danger", "warning", "info"];
		const labels = {
			danger: __("There are %s critical alerts"),
			warning: __("There are %s warnings"),
			info: __("There are %s information alerts")
		};

		$items.each(function () {
			const $el = $(this);
			const level = $el.hasClass("danger") ? "danger" : $el.hasClass("warning") ? "warning" : "info";
			groups[level].push($el[0].outerHTML);
		});

		let groupsHtml = "";
		order.forEach(function (level) {
			const items = groups[level];
			if (!items || items.length === 0) return;
			const count = items.length;
			const label = labels[level].replace("%s", count);
			const groupClass = "dash-alert-group dash-alert-group-" + level + " collapsed";
			groupsHtml += "<div class=\"" + groupClass + "\">";
			groupsHtml += "<div class=\"dash-alert-group-header\" data-level=\"" + level + "\">";
			groupsHtml += "<i class=\"fa fa-chevron-right dash-alert-group-chevron\"></i>";
			groupsHtml += "<span class=\"dash-alert-group-title\">" + label + "</span>";
			groupsHtml += "</div>";
			groupsHtml += "<div class=\"dash-alert-group-body\">" + items.join("") + "</div>";
			groupsHtml += "</div>";
		});

		$section.html(groupsHtml);

		// Per-level group collapse/expand
		$section.find(".dash-alert-group-header").on("click", function () {
			const $header = $(this);
			const $group = $header.closest(".dash-alert-group");
			const $body = $group.find(".dash-alert-group-body");
			const $chevron = $header.find(".dash-alert-group-chevron");
			const collapsed = $group.hasClass("collapsed");
			if (collapsed) {
				$body.slideDown(200);
				$group.removeClass("collapsed");
				$chevron.removeClass("fa-chevron-right").addClass("fa-chevron-down");
			} else {
				$body.slideUp(200);
				$group.addClass("collapsed");
				$chevron.removeClass("fa-chevron-down").addClass("fa-chevron-right");
			}
		});
	};

	window.logistics_bind_document_alert_cards = function ($container) {
		if (!$container || !$container.length) return;
		const $wrapper = $container.find(".doc-alerts-cards-wrapper");
		if (!$wrapper.length) return;
		const doctype = $wrapper.attr("data-doctype");
		const docname = $wrapper.attr("data-docname");
		if (!doctype || !docname) return;
		const frm = cur_frm;
		$wrapper.off("click.doc-cards").on("click.doc-cards", ".doc-alert-card", function () {
			const category = $(this).attr("data-category");
			if (!category) return;
			// For Declaration and Declaration Order: Pending Permits and Exemptions navigate to Permits tab
			if ((doctype === "Declaration" || doctype === "Declaration Order") && (category === "pending_permits" || category === "exemptions")) {
				if (frm && frm.layout && frm.layout.select_tab) {
					frm.layout.select_tab("permits_tab");
				}
				return;
			}
			logistics_show_document_list_dialog(doctype, docname, category, frm);
		});
	};
})();
