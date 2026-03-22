/**
 * Job Profit Account Type on Account: Profit/WIP/Accrual only for Income Account & Expense Account;
 * other account types may only use Disbursements.
 */
frappe.ui.form.on("Account", {
	refresh(frm) {
		logistics_account_job_profit_set_options(frm);
	},
	account_type(frm) {
		logistics_account_job_profit_set_options(frm);
	},
});

function logistics_account_job_profit_set_options(frm) {
	const fieldname = "job_profit_account_type";
	if (!frm.get_field(fieldname)) {
		return;
	}
	const at = (frm.doc.account_type || "").trim();
	const plTypes = ["Income Account", "Expense Account"];
	const opts = plTypes.includes(at)
		? ["Profit", "WIP", "Accrual", "Disbursements"]
		: ["Disbursements"];
	const optstr = "\n" + opts.join("\n");
	frm.set_df_property(fieldname, "options", optstr);
	const cur = (frm.doc[fieldname] || "").trim();
	if (cur && !opts.includes(cur)) {
		frm.set_value(fieldname, "");
	} else {
		frm.refresh_field(fieldname);
	}
}
