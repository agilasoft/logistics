const assert = require("assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const page = path.resolve(__dirname, "../../public/js/workflow_center.js");
const source = fs.readFileSync(page, "utf8");

function escapeHtml(value) {
	return String(value == null ? "" : value)
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;");
}

function load() {
	const sandbox = {
		__: (value, args) => {
			let text = String(value);
			(args || []).forEach((arg, index) => {
				text = text.replace("{" + index + "}", arg);
			});
			return text;
		},
		console,
		Promise,
	};
	sandbox.frappe = {
		provide(namespace) {
			let obj = sandbox;
			for (const part of namespace.split(".")) {
				obj[part] = obj[part] || {};
				obj = obj[part];
			}
		},
		pages: { "workflow-center": {} },
		datetime: {
			prettyDate() {
				return "8 minutes ago";
			},
			str_to_user(value) {
				return value;
			},
		},
		utils: { escape_html: escapeHtml },
		confirm() {},
		call() {},
		show_alert() {},
		dom: { freeze() {}, unfreeze() {} },
		set_route() {},
	};
	vm.runInNewContext(source, sandbox, { filename: page });
	return sandbox;
}

function recorder() {
	const rec = {
		chunks: [],
		empty() {
			return rec;
		},
		append(html) {
			rec.chunks.push(String(html));
			return rec;
		},
		text() {
			return rec;
		},
		find() {
			return rec;
		},
	};
	return rec;
}

const sandbox = load();
const quote = sandbox.wc_actions_markup({
	reference_doctype: "Sales Quote",
	reference_name: "SQU000000098",
	available_actions: ["Submit for Approval", "For Revision"],
});
assert.strictEqual((quote.match(/wc-apply-action/g) || []).length, 2);
assert.ok(quote.includes('data-action="Submit for Approval"'));
assert.ok(quote.includes('data-action="For Revision"'));
assert.ok(quote.includes('data-doctype="Sales Quote"'));
assert.ok(quote.includes('data-name="SQU000000098"'));
assert.ok(quote.includes(">Submit for Approval<"));
assert.ok(quote.includes(">For Revision<"));
assert.ok(quote.includes('type="button"'));

assert.strictEqual(
	sandbox.wc_actions_markup({
		reference_doctype: "Sales Quote",
		reference_name: "SQU000000097",
		available_actions: [],
	}),
	""
);
assert.strictEqual(sandbox.wc_actions_markup(null), "");

const hostile = sandbox.wc_actions_markup({
	reference_doctype: 'Sales "Quote"',
	reference_name: "SQ<1>",
	available_actions: ['<img src=x onerror="alert(1)">'],
});
assert.ok(!hostile.includes("<img"));
assert.ok(!hostile.includes("<script"));
assert.ok(hostile.includes("&lt;img"));
assert.ok(hostile.includes('data-doctype="Sales &quot;Quote&quot;"'));
assert.ok(hostile.includes('data-name="SQ&lt;1&gt;"'));

const list = recorder();
const pageObj = Object.create(sandbox.logistics.workflow_center.WorkflowCenterPage.prototype);
pageObj.$container = { find: () => list };
pageObj.active_segment = "open_actions";
pageObj.items = [
	{
		reference_doctype: "Sales Quote",
		reference_name: "SQU000000098",
		title: "SQU000000098",
		workflow_state: "Draft",
		available_actions: ["Submit for Approval"],
		severity: "ok",
		permitted_role: "Sales User",
		state_entered_at: "2026-10-14 05:40:00",
	},
	{
		reference_doctype: "Air Booking",
		reference_name: "ABK-000000056",
		title: "ABK-000000056",
		workflow_state: "Working",
		available_actions: ["Convert to Shipment", "For Revision"],
		severity: "ok",
		permitted_role: "Air Freight User",
		state_entered_at: "2026-10-14 02:00:00",
	},
];
pageObj.render_list();
const html = list.chunks.join("\n");
assert.ok(html.includes('data-action="Submit for Approval"'), html);
assert.ok(html.includes('data-action="Convert to Shipment"'), html);
assert.ok(html.includes('data-action="For Revision"'), html);
assert.ok(!html.includes("&lt;button"), html);
assert.ok(html.includes("8 minutes ago"));

assert.ok(source.includes('this.$container.on("click", ".wc-apply-action"'));

const calls = [];
sandbox.frappe.confirm = (message, yes) => calls.push({ type: "confirm", message, yes });
sandbox.frappe.call = (request) => calls.push({ type: "call", request });
sandbox.frappe.show_alert = (alert) => calls.push({ type: "alert", alert });
let refreshed = 0;
pageObj.refresh = () => {
	refreshed += 1;
	return Promise.resolve();
};
pageObj._applying = false;

pageObj.apply_action("", "SQU000000098", "Submit for Approval");
pageObj.apply_action("Sales Quote", "SQU000000098", "");
assert.strictEqual(calls.length, 0);

pageObj.apply_action("Sales Quote", "SQU000000098", "Submit for Approval");
assert.strictEqual(calls.length, 1);
assert.strictEqual(
	calls[0].message,
	"Apply Submit for Approval to Sales Quote SQU000000098?"
);
calls[0].yes();
const request = calls[1].request;
assert.strictEqual(request.method, "frappe.model.workflow.apply_workflow");
assert.strictEqual(request.args.action, "Submit for Approval");
assert.strictEqual(request.args.doc.doctype, "Sales Quote");
assert.strictEqual(request.args.doc.name, "SQU000000098");
assert.strictEqual(request.freeze, true);
assert.strictEqual(pageObj._applying, true);
pageObj.apply_action("Sales Quote", "SQU000000098", "Submit for Approval");
assert.strictEqual(calls.length, 2);

request.callback({ message: { name: "SQU000000098" } });
assert.strictEqual(calls[2].alert.message, "Submit for Approval applied to SQU000000098");
assert.strictEqual(refreshed, 1);
setTimeout(() => {
	assert.strictEqual(pageObj._applying, false);

	pageObj._applying = false;
	calls.length = 0;
	pageObj.apply_action("Air Booking", "ABK-000000056", "Convert to Shipment");
	calls[0].yes();
	calls[1].request.error(new Error("Not a valid Workflow Action"));
	assert.strictEqual(refreshed, 1);
	assert.strictEqual(pageObj._applying, false);

	pageObj.apply_action("Air Booking", "ABK-000000056", "For Revision");
	calls[2].yes();
	calls[3].request.callback({ exc: "ValidationError" });
	assert.strictEqual(refreshed, 1);
	assert.strictEqual(pageObj._applying, false);

	const attack = '<img src=x onerror="alert(1)">';
	pageObj.apply_action("Sales Quote", "SQ<1>", attack);
	assert.ok(!calls[4].message.includes("<img"));
	assert.ok(calls[4].message.includes("&lt;img"));
	calls[4].yes();
	assert.strictEqual(calls[5].request.args.action, attack);
	assert.ok(!calls[5].request.freeze_message.includes("<img"));

	console.log("workflow center action buttons apply the workflow");
}, 0);
