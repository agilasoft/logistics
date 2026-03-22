// Account filters: WIP (Income+WIP), Revenue Liability (Asset), Cost Accrual (Expense+Accrual), Accrued (Liability only)

const PARAM_ACCOUNT_FIELDS = [
	"wip_account",
	"revenue_liability_account",
	"cost_accrual_account",
	"accrued_cost_liability_account",
];

function param_account_filters(company, fieldname) {
	if (!company) {
		return [["name", "=", ""]];
	}
	const f = [
		["Account", "company", "=", company],
		["Account", "is_group", "=", 0],
	];
	if (fieldname === "wip_account") {
		f.push(["Account", "account_type", "=", "Income Account"]);
		f.push(["Account", "job_profit_account_type", "=", "WIP"]);
	} else if (fieldname === "revenue_liability_account") {
		f.push(["Account", "root_type", "=", "Asset"]);
	} else if (fieldname === "cost_accrual_account") {
		f.push(["Account", "account_type", "=", "Expense Account"]);
		f.push(["Account", "job_profit_account_type", "=", "Accrual"]);
	} else if (fieldname === "accrued_cost_liability_account") {
		f.push(["Account", "root_type", "=", "Liability"]);
	}
	return f;
}

function bind_parameter_account_queries(frm) {
	const c = frm.doc.company;
	PARAM_ACCOUNT_FIELDS.forEach((fieldname) => {
		frm.set_query(fieldname, "recognition_parameters", function () {
			return { filters: param_account_filters(c, fieldname) };
		});
	});
}

frappe.ui.form.on("Recognition Policy Settings", {
	refresh(frm) {
		bind_parameter_account_queries(frm);
	},
	company(frm) {
		(frm.doc.recognition_parameters || []).forEach((row) => {
			PARAM_ACCOUNT_FIELDS.forEach((fn) => {
				row[fn] = "";
			});
		});
		frm.refresh_field("recognition_parameters");
		bind_parameter_account_queries(frm);
	},
});
