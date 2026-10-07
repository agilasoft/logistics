const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const nav = require("../public/js/driver_nav.js");

function stop(id, lat, lng, extra) {
	return Object.assign(
		{
			id: id,
			leg: id.split(":")[0],
			kind: id.endsWith("delivery") ? "delivery" : "pickup",
			lat: lat,
			lng: lng,
			done: false,
			address: lat + "," + lng,
		},
		extra || {}
	);
}

const run = [
	stop("LEG-1:pickup", 14.55, 121.02),
	stop("LEG-1:delivery", 14.58, 121.05),
	stop("LEG-2:pickup", 14.6, 121.08),
	stop("LEG-2:delivery", 14.62, 121.11),
];

test("the route includes every remaining stop, not only the next pin", () => {
	const origin = { lat: 14.54, lng: 121.0 };
	const plan = nav.buildRoutePlan(run, origin);
	assert.equal(plan.originIsDriver, true);
	assert.equal(plan.included.length, 4);
	assert.equal(plan.waypoints.length, 3);
	assert.deepEqual(
		plan.waypoints.map((waypoint) => waypoint.location),
		[
			{ lat: 14.55, lng: 121.02 },
			{ lat: 14.58, lng: 121.05 },
			{ lat: 14.6, lng: 121.08 },
		]
	);
	assert.deepEqual(plan.destination, { lat: 14.62, lng: 121.11 });
	assert.equal(plan.omitted, 0);
	plan.waypoints.forEach((waypoint) => assert.equal(waypoint.stopover, true));
});

test("completed stops drop off the route and the rest stay in order", () => {
	const stops = run.map((item) => Object.assign({}, item, { done: item.id === "LEG-1:pickup" }));
	const plan = nav.buildRoutePlan(stops, { lat: 14.56, lng: 121.03 });
	assert.deepEqual(
		plan.included.map((item) => item.id),
		["LEG-1:delivery", "LEG-2:pickup", "LEG-2:delivery"]
	);
	assert.equal(plan.waypoints.length, 2);
	assert.deepEqual(plan.destination, { lat: 14.62, lng: 121.11 });
});

test("without a GPS fix the first remaining stop is the start of the same run", () => {
	const plan = nav.buildRoutePlan(run, null);
	assert.equal(plan.originIsDriver, false);
	assert.deepEqual(plan.origin, { lat: 14.55, lng: 121.02 });
	assert.equal(plan.waypoints.length, 2);
	assert.deepEqual(plan.destination, { lat: 14.62, lng: 121.11 });
});

test("a single remaining stop is the destination", () => {
	const only = [stop("LEG-9:delivery", 14.7, 121.2)];
	const parked = nav.buildRoutePlan(only, null);
	assert.equal(parked.origin, null);
	assert.deepEqual(parked.destination, { lat: 14.7, lng: 121.2 });
	const driving = nav.buildRoutePlan(only, { lat: 14.6, lng: 121.1 });
	assert.equal(driving.waypoints.length, 0);
	assert.deepEqual(driving.destination, { lat: 14.7, lng: 121.2 });
});

test("address-only stops stay on the route", () => {
	const stops = [
		{ id: "LEG-3:pickup", leg: "LEG-3", kind: "pickup", done: false, address: "1 Dock Road" },
		{ id: "LEG-3:delivery", leg: "LEG-3", kind: "delivery", done: false, place: "North Gate" },
	];
	const plan = nav.buildRoutePlan(stops, { lat: 1, lng: 2 });
	assert.deepEqual(
		plan.waypoints.map((waypoint) => waypoint.location),
		["1 Dock Road"]
	);
	assert.equal(plan.destination, "North Gate");
});

test("directions waypoint cap keeps the next stops and reports the rest", () => {
	const stops = [];
	for (let index = 0; index < 30; index += 1) {
		stops.push(stop("LEG-" + index + ":delivery", 14 + index / 100, 121));
	}
	const plan = nav.buildRoutePlan(stops, { lat: 13, lng: 120 });
	assert.equal(plan.waypoints.length, nav.MAX_WAYPOINTS);
	assert.equal(plan.included.length, nav.MAX_WAYPOINTS + 1);
	assert.equal(plan.omitted, 4);
	assert.equal(plan.included[0].id, "LEG-0:delivery");
});

test("fallback map link carries the rest of the run, not the next pin alone", () => {
	const origin = { lat: 14.54, lng: 121.0 };
	const url = new URL(nav.mapsFallbackUrl(run, origin));
	assert.equal(url.searchParams.get("origin"), "14.54,121");
	assert.equal(url.searchParams.get("destination"), "14.62,121.11");
	assert.deepEqual(url.searchParams.get("waypoints").split("|"), [
		"14.55,121.02",
		"14.58,121.05",
		"14.6,121.08",
	]);
	assert.equal(url.searchParams.get("travelmode"), "driving");
	const nextPinOnly = "https://www.google.com/maps/dir/?api=1&destination=14.55,121.02";
	assert.notEqual(url.toString(), nextPinOnly);
});

test("url fallback still includes nine intermediate stops when the run is longer", () => {
	const stops = [];
	for (let index = 0; index < 15; index += 1) {
		stops.push(stop("LEG-" + index + ":delivery", 10 + index, 20));
	}
	const url = new URL(nav.mapsFallbackUrl(stops, { lat: 9, lng: 19 }));
	assert.equal(url.searchParams.get("waypoints").split("|").length, nav.URL_WAYPOINTS);
	assert.equal(url.searchParams.get("destination"), "19,20");
});

test("traffic durations accumulate to each stop and only drops are saved", () => {
	const plan = nav.buildRoutePlan(run, { lat: 14.54, lng: 121.0 });
	const route = nav.readRoute({
		routes: [
			{
				legs: [
					{ duration: { value: 600 }, duration_in_traffic: { value: 900 }, distance: { value: 3000 }, steps: [] },
					{ duration: { value: 300 }, duration_in_traffic: { value: 300 }, distance: { value: 2000 }, steps: [] },
					{ duration_in_traffic: { value: 1200 }, distance: { value: 8000 }, steps: [] },
					{ duration_in_traffic: { value: 600 }, distance: { value: 4000 }, steps: [] },
				],
			},
		],
	});
	assert.equal(route.traffic, true);
	const eta = nav.etasFromLegs(route.legs, plan.included, true);
	assert.equal(eta.dock.id, "LEG-1:pickup");
	assert.equal(eta.dock.seconds, 900);
	assert.equal(eta.dock.km, 3);
	assert.equal(eta.stops[1].id, "LEG-1:delivery");
	assert.equal(eta.stops[1].seconds, 1200);
	assert.equal(eta.stops[1].km, 5);
	assert.deepEqual(
		eta.deliveries.map((row) => row.leg),
		["LEG-1", "LEG-2"]
	);
	assert.equal(eta.deliveries[0].eta_min, 20);
	assert.equal(eta.deliveries[1].eta_min, 50);
	assert.equal(eta.deliveries[1].eta_km, 17);
});

test("planned route without a driver fix measures ETAs from the first stop", () => {
	const plan = nav.buildRoutePlan(run, null);
	const legs = [
		{ seconds: 600, meters: 1000 },
		{ seconds: 600, meters: 1000 },
		{ seconds: 600, meters: 1000 },
	];
	const eta = nav.etasFromLegs(legs, plan.included, false);
	assert.equal(eta.stops.length, 3);
	assert.equal(eta.dock.id, "LEG-1:delivery");
	assert.equal(eta.deliveries[0].eta_min, 10);
});

test("the dock clock counts down between route refreshes", () => {
	const fetchedAt = Date.parse("2026-10-05T03:00:00Z");
	const snapshot = { seconds: 12 * 60, fetchedAt: fetchedAt };
	assert.equal(nav.liveSeconds(snapshot, fetchedAt), 720);
	assert.equal(nav.liveSeconds(snapshot, fetchedAt + 90000), 630);
	const label = nav.formatEtaLabel(nav.liveSeconds(snapshot, fetchedAt + 90000), 4.2, fetchedAt + 90000);
	assert.match(label, /^10 min 30 sec · 4\.2 km · arrive /);
	assert.match(nav.formatEtaLabel(25, 0.4, fetchedAt), /^25 sec · 0\.4 km · arrive /);
	assert.match(nav.formatEtaLabel(10, 0.1, fetchedAt), /^Arriving · 0\.1 km$/);
});

test("turn-by-turn advances as the truck reaches the maneuver", () => {
	const steps = [
		{ end: { lat: 14.55, lng: 121.02 }, instruction: "Turn left onto EDSA" },
		{ end: { lat: 14.56, lng: 121.03 }, instruction: "Continue onto C-5" },
	];
	assert.equal(nav.pickStepIndex(steps, { lat: 14.5, lng: 121.0 }), 0);
	assert.equal(nav.pickStepIndex(steps, { lat: 14.55, lng: 121.02 }), 1);
	assert.equal(nav.stripHtml("Turn left onto <b>EDSA</b>"), "Turn left onto EDSA");
	assert.equal(nav.maneuverHeading("turn-left"), -90);
});

test("the route refreshes as the truck moves and on a timer while driving", () => {
	assert.equal(nav.shouldRefreshRoute(null, 1000), true);
	assert.equal(nav.shouldRefreshRoute({ lastAt: 0, movedMeters: 10 }, 20000), false);
	assert.equal(nav.shouldRefreshRoute({ lastAt: 0, movedMeters: 80 }, 20000), true);
	assert.equal(nav.shouldRefreshRoute({ lastAt: 0, movedMeters: 0 }, 45000), true);
});

test("turn-by-turn keeps going through every leg of the run", () => {
	const steps = nav.routeSteps([
		{ steps: [{ instruction: "Turn left onto EDSA" }, { instruction: "Continue" }] },
		{ steps: [{ instruction: "Arrive at the dock" }] },
	]);
	assert.deepEqual(
		steps.map((step) => step.instruction),
		["Turn left onto EDSA", "Continue", "Arrive at the dock"]
	);
});

test("the dock ETA counts down and shortens as the truck drives closer", () => {
	const fetchedAt = Date.parse("2026-10-05T03:00:00Z");
	const snapshot = { seconds: 12 * 60, km: 10, fetchedAt: fetchedAt, traffic: true };
	const parked = nav.followEta(snapshot, 5000, 5000, fetchedAt + 90000);
	assert.equal(parked.seconds, 630);
	assert.equal(parked.km, 10);
	assert.equal(parked.traffic, true);
	const driving = nav.followEta(snapshot, 5000, 3000, fetchedAt + 10000);
	assert.equal(driving.km, 6);
	assert.equal(driving.seconds, 432);
	const arrived = nav.followEta(snapshot, 5000, 0, fetchedAt + 10000);
	assert.equal(arrived.km, 0);
	assert.equal(arrived.seconds, 0);
	assert.equal(nav.formatEtaLabel(arrived.seconds, arrived.km, fetchedAt), "Arriving");
	const away = nav.followEta(snapshot, 5000, 6500, fetchedAt + 10000);
	assert.equal(away.km, 10);
	assert.equal(away.seconds, 710);
});

test("without a traffic snapshot the ETA still follows the truck", () => {
	const far = nav.routeMeters(run, { lat: 14.5, lng: 120.98 });
	const near = nav.routeMeters(run, { lat: 14.549, lng: 121.015 });
	assert.ok(near < far);
	const before = nav.geometricEta(far, 40);
	const after = nav.geometricEta(near, 40);
	assert.ok(after.seconds < before.seconds);
	assert.ok(after.km < before.km);
	assert.equal(nav.geometricEta(0, 40).seconds, 0);
});

test("stop list ETAs shrink when the remaining path gets shorter", () => {
	const rows = [
		{ id: "LEG-1:pickup", seconds: 600, km: 5 },
		{ id: "LEG-1:delivery", seconds: 1200, km: 10 },
	];
	const fetchedAt = 1_000_000;
	const ticked = nav.tickStops(rows, fetchedAt, fetchedAt + 90_000, 10000, 10000);
	assert.equal(ticked[0].seconds, 510);
	assert.equal(ticked[1].minutes, 19);
	const closer = nav.tickStops(rows, fetchedAt, fetchedAt + 5_000, 10000, 8000);
	assert.equal(closer[0].seconds, 480);
	assert.equal(closer[0].km, 4);
	assert.equal(closer[1].km, 8);
	const straight = nav.progressEtas(run, { lat: 14.54, lng: 121.0 }, 90);
	assert.equal(straight[0].id, "LEG-1:pickup");
	assert.equal(straight.length, 4);
	assert.ok(straight[3].seconds > straight[0].seconds);
});

test("guidance can point along the run before the first maneuver arrives", () => {
	assert.equal(nav.compass({ lat: 0, lng: 0 }, { lat: 1, lng: 0 }), "north");
	assert.equal(nav.compass({ lat: 0, lng: 0 }, { lat: 0, lng: 1 }), "east");
	assert.ok(nav.bearingDegrees({ lat: 14.5, lng: 121 }, { lat: 14.6, lng: 121 }) < 20);
});

test("the driver page opens on navigation and stays in the app", () => {
	const html = fs.readFileSync(path.join(__dirname, "../www/driver.html"), "utf8");
	assert.match(html, /id="driver-app"[^>]*data-screen="route"/);
	assert.match(html, /showScreen\("route"\)/);
	assert.doesNotMatch(html, /data-screen="map"/);
	assert.doesNotMatch(html, /window\.open\(\s*navApi\.mapsFallbackUrl/);
	assert.doesNotMatch(html, /window\.open\(mapsUrl/);
	assert.match(html, /navApi\.routeSteps/);
	assert.match(html, /navApi\.followEta/);
});
