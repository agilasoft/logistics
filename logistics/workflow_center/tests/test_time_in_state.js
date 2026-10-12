const assert = require("assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const page = path.resolve(__dirname, "../../public/js/workflow_center.js");
const source = fs.readFileSync(page, "utf8");

const RAW_TIMESTAMP =
	'<span class="frappe-timestamp " data-timestamp="2026-10-12 09:37:07.257413" title="10-12-2026 09:37:07">1 hour ago</span>';

function load(datetime) {
	const sandbox = {
		__: (value) => value,
		console,
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
		datetime,
		utils: {
			escape_html(value) {
				return String(value);
			},
		},
	};
	vm.runInNewContext(source, sandbox, { filename: page });
	return sandbox;
}

function textOf(html) {
	return html.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
}

const fromCommentWhen = load({
	comment_when() {
		return RAW_TIMESTAMP;
	},
	str_to_user() {
		return "10-12-2026 09:37:07";
	},
});
const html = fromCommentWhen.wc_time_in_state({
	state_entered_at: "2026-10-12 09:37:07.257413",
	elapsed_seconds: 3600,
});
assert.strictEqual(textOf(html), "1 hour ago");
assert.ok(html.startsWith('<span class="frappe-timestamp"'));
assert.ok(!html.includes("&lt;span"));
assert.ok(!html.includes("data-timestamp=\"<"));
assert.ok(html.includes('title="10-12-2026 09:37:07"'));

const fromPrettyDate = load({
	prettyDate() {
		return "2 hours ago";
	},
	comment_when() {
		return RAW_TIMESTAMP;
	},
	str_to_user() {
		return "10-12-2026 09:29:17";
	},
});
const pretty = fromPrettyDate.wc_time_in_state({
	modified: "2026-10-12 09:29:17.298001",
});
assert.strictEqual(textOf(pretty), "2 hours ago");
assert.ok(!pretty.includes("<span class=\"frappe-timestamp \""), pretty);

const hostile = load({
	prettyDate() {
		return '<img src=x onerror="alert(1)">';
	},
	str_to_user() {
		return '"><script>alert(1)</script>';
	},
});
const safe = hostile.wc_time_in_state({
	state_entered_at: '"><script>alert(1)</script>',
});
assert.ok(!safe.includes("<script>"));
assert.ok(!safe.includes("<img"));
assert.ok(safe.includes("&lt;script&gt;"));
assert.ok(!textOf(safe).includes("<"));

assert.strictEqual(fromCommentWhen.wc_time_in_state({}), "-");

console.log("time in state renders as text");
console.log(html);
