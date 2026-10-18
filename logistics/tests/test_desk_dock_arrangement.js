const test = require("node:test");
const assert = require("node:assert/strict");

const dock = require("../public/js/desk_main_sidebar_visibility_fix.js");

function entry(link_to, icon) {
	return {
		link_type: "Sidebar",
		link_to: link_to,
		label: link_to,
		icon: icon || link_to.toLowerCase().replace(/ /g, "_"),
	};
}

test("CargoNext keeps its module rail, in order, and drops anything else", () => {
	const entries = [
		entry("Pricing Center", "pricing"),
		entry("Old Line Icon", "ship"),
		entry("Air Freight", "air_freight"),
		entry("Sea Freight", "sea_freight"),
	];
	const arranged = dock.arrange_dock(entries, { app_name: "logistics" }, () => {
		throw new Error("CargoNext must not use another app's dock arrangement");
	});

	assert.deepEqual(
		arranged.map((row) => row.link_to),
		["Air Freight", "Sea Freight", "Pricing Center"]
	);
	assert.equal(arranged[0].icon, "air_freight");
	assert.equal(arranged.some((row) => row.link_to === "Old Line Icon"), false);
});

test("GoConnect keeps the dock and icons Frappe resolved for it", () => {
	const entries = [
		entry("Vessel Tracking", "vessel_tracking"),
		entry("Flight Tracking", "flight_tracking"),
		entry("Telematics", "telematics"),
	];
	const app = { app_name: "goconnect" };
	let seen = null;
	const arranged = dock.arrange_dock(entries, app, (rows, target) => {
		seen = { rows, target };
		return rows.map((row) => Object.assign({}, row, { icon: row.icon + "-kept" }));
	});

	assert.equal(seen.target, app);
	assert.deepEqual(
		arranged.map((row) => [row.link_to, row.icon]),
		[
			["Vessel Tracking", "vessel_tracking-kept"],
			["Flight Tracking", "flight_tracking-kept"],
			["Telematics", "telematics-kept"],
		]
	);
});

test("GoConnect's logo uses the orange brand tile", () => {
	const rows = [
		{ title: "Vessel Tracking", icon: "vessel_tracking" },
		{ title: "GoConnect", icon: "goconnect" },
	];
	const tiles = new Set(["goconnect", "vessel_tracking"]);
	assert.equal(
		dock.goconnect_brand_icon(rows, (name) => tiles.has(name)),
		"goconnect"
	);
});

test("a black line-art mark is not used as the GoConnect logo", () => {
	const rows = [{ title: "GoConnect", icon: "goconnect" }];
	assert.equal(dock.goconnect_brand_icon(rows, () => false), null);
});

test("the Home shell's orange icon is the GoConnect logo when the symbol has another name", () => {
	const rows = [
		{ title: "Vessel Tracking", icon: "vessel" },
		{ link_to: "Home", icon: "go_home" },
	];
	const tiles = new Set(["vessel", "go_home"]);
	assert.equal(
		dock.goconnect_brand_icon(rows, (name) => tiles.has(name)),
		"go_home"
	);
});

test("a dock call with no app still follows the CargoNext rail", () => {
	const arranged = dock.arrange_dock(
		[entry("Transport"), entry("Air Freight"), entry("GoConnect")],
		null,
		() => {
			throw new Error("a legacy call has no other app to delegate to");
		}
	);
	assert.deepEqual(
		arranged.map((row) => row.link_to),
		["Air Freight", "Transport"]
	);
});
