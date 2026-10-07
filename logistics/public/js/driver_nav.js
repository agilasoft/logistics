/* Driver run navigation.
 * The route is every remaining stop, in order. The next pin is only the first
 * arrival on that route.
 */
(function (root, factory) {
	const api = factory();
	if (typeof module === "object" && module.exports) {
		module.exports = api;
	}
	root.DriverNav = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
	const MAX_WAYPOINTS = 25;
	const URL_WAYPOINTS = 9;
	const STEP_ADVANCE_METERS = 35;

	function stopPoint(stop) {
		if (!stop) return null;
		const lat = Number(stop.lat);
		const lng = Number(stop.lng);
		if (Number.isFinite(lat) && Number.isFinite(lng)) {
			return { lat: lat, lng: lng };
		}
		const address = String(stop.address || stop.place || "").trim();
		return address || null;
	}

	function remainingStops(stops) {
		return (stops || []).filter(function (stop) {
			return stop && !stop.done && stopPoint(stop);
		});
	}

	function asDriverOrigin(origin) {
		if (!origin) return null;
		const lat = Number(origin.lat);
		const lng = Number(origin.lng);
		if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
		return { lat: lat, lng: lng };
	}

	function buildRoutePlan(stops, origin, maxWaypoints) {
		const max = maxWaypoints == null ? MAX_WAYPOINTS : maxWaypoints;
		const pending = remainingStops(stops);
		if (!pending.length) return null;
		const driver = asDriverOrigin(origin);

		if (driver) {
			const included = pending.slice(0, Math.min(pending.length, max + 1));
			return {
				origin: driver,
				originIsDriver: true,
				destination: stopPoint(included[included.length - 1]),
				waypoints: included.slice(0, -1).map(function (stop) {
					return { location: stopPoint(stop), stopover: true };
				}),
				included: included,
				omitted: pending.length - included.length,
			};
		}

		if (pending.length === 1) {
			return {
				origin: null,
				originIsDriver: false,
				destination: stopPoint(pending[0]),
				waypoints: [],
				included: pending.slice(),
				omitted: 0,
			};
		}

		const included = pending.slice(0, Math.min(pending.length, max + 2));
		return {
			origin: stopPoint(included[0]),
			originIsDriver: false,
			destination: stopPoint(included[included.length - 1]),
			waypoints: included.slice(1, -1).map(function (stop) {
				return { location: stopPoint(stop), stopover: true };
			}),
			included: included,
			omitted: pending.length - included.length,
		};
	}

	function formatPoint(point) {
		if (point && typeof point === "object") return point.lat + "," + point.lng;
		return String(point || "");
	}

	function mapsFallbackUrl(stops, origin) {
		const plan = buildRoutePlan(stops, origin, URL_WAYPOINTS);
		if (!plan || !plan.destination) return "https://www.google.com/maps";
		const params = new URLSearchParams();
		params.set("api", "1");
		params.set("travelmode", "driving");
		if (plan.origin) params.set("origin", formatPoint(plan.origin));
		params.set("destination", formatPoint(plan.destination));
		if (plan.waypoints.length) {
			params.set(
				"waypoints",
				plan.waypoints
					.map(function (waypoint) {
						return formatPoint(waypoint.location);
					})
					.join("|")
			);
		}
		return "https://www.google.com/maps/dir/?" + params.toString();
	}

	function latLng(value) {
		if (!value) return null;
		if (typeof value.lat === "function" && typeof value.lng === "function") {
			return { lat: Number(value.lat()), lng: Number(value.lng()) };
		}
		const lat = Number(value.lat);
		const lng = Number(value.lng != null ? value.lng : value.lon);
		if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
		return { lat: lat, lng: lng };
	}

	function stripHtml(value) {
		return String(value || "")
			.replace(/<[^>]*>/g, " ")
			.replace(/&nbsp;/g, " ")
			.replace(/&amp;/g, "&")
			.replace(/\s+/g, " ")
			.trim();
	}

	function readStep(step) {
		const distance = step.distance || {};
		return {
			end: step.end || latLng(step.end_location),
			start: step.start || latLng(step.start_location),
			instruction: step.instruction || stripHtml(step.instructions || step.html_instructions || ""),
			maneuver: step.maneuver || "",
			meters: distance.value || step.meters || 0,
		};
	}

	function readLeg(leg) {
		const duration = leg.duration_in_traffic || leg.duration || {};
		const distance = leg.distance || {};
		return {
			seconds: duration.value || 0,
			meters: distance.value || 0,
			traffic: Boolean(leg.duration_in_traffic && leg.duration_in_traffic.value),
			steps: (leg.steps || []).map(readStep),
		};
	}

	function readRoute(result) {
		const route = result && result.routes ? result.routes[0] : result || {};
		const legs = (route.legs || []).map(readLeg);
		return {
			legs: legs,
			traffic: legs.some(function (leg) {
				return leg.traffic;
			}),
		};
	}

	function etasFromLegs(legs, included, originIsDriver) {
		const arrivals = originIsDriver ? included || [] : (included || []).slice(1);
		let seconds = 0;
		let meters = 0;
		const stops = [];
		const deliveries = [];
		arrivals.forEach(function (stop, index) {
			const leg = legs[index] || {};
			seconds += leg.seconds || 0;
			meters += leg.meters || 0;
			const row = {
				id: stop.id,
				leg: stop.leg,
				kind: stop.kind,
				seconds: seconds,
				minutes: Math.max(1, Math.round(seconds / 60)),
				km: Math.round((meters / 1000) * 10) / 10,
			};
			stops.push(row);
			if (stop.kind === "delivery" && stop.leg) {
				deliveries.push({ leg: stop.leg, eta_min: row.minutes, eta_km: row.km });
			}
		});
		return { stops: stops, deliveries: deliveries, dock: stops[0] || null };
	}

	function distanceMeters(a, b) {
		if (!a || !b || a.lat == null || b.lat == null) return Infinity;
		const earth = 6371000;
		const p1 = (a.lat * Math.PI) / 180;
		const p2 = (b.lat * Math.PI) / 180;
		const dLat = ((b.lat - a.lat) * Math.PI) / 180;
		const dLng = ((b.lng - a.lng) * Math.PI) / 180;
		const h =
			Math.sin(dLat / 2) * Math.sin(dLat / 2) +
			Math.cos(p1) * Math.cos(p2) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
		return 2 * earth * Math.asin(Math.min(1, Math.sqrt(h)));
	}

	function pickStepIndex(steps, position, threshold) {
		const limit = threshold == null ? STEP_ADVANCE_METERS : threshold;
		if (!steps || !steps.length || !position) return 0;
		for (let index = 0; index < steps.length; index += 1) {
			const end = steps[index].end;
			if (!end) return index;
			if (distanceMeters(position, end) > limit) return index;
		}
		return steps.length - 1;
	}

	function shouldRefreshRoute(state, now, minMoveMeters, maxIntervalMs) {
		const move = minMoveMeters == null ? 80 : minMoveMeters;
		const interval = maxIntervalMs == null ? 45000 : maxIntervalMs;
		if (!state || state.lastAt == null) return true;
		const elapsed = now - state.lastAt;
		if (elapsed >= interval) return true;
		return (state.movedMeters || 0) >= move;
	}

	function liveSeconds(snapshot, now) {
		if (!snapshot) return null;
		return Math.max(0, snapshot.seconds - (now - snapshot.fetchedAt) / 1000);
	}

	function formatMeters(meters) {
		const value = Number(meters);
		if (!Number.isFinite(value)) return "";
		if (value >= 1000) {
			const km = Math.round((value / 1000) * 10) / 10;
			return (km >= 10 ? Math.round(km) : km) + " km";
		}
		if (value < 30) return Math.max(0, Math.round(value)) + " m";
		return Math.round(value / 10) * 10 + " m";
	}

	function formatClock(date) {
		let hours = date.getHours();
		const minutes = date.getMinutes();
		const suffix = hours >= 12 ? "PM" : "AM";
		hours = hours % 12 || 12;
		const mm = minutes < 10 ? "0" + minutes : String(minutes);
		return hours + ":" + mm + " " + suffix;
	}

	function formatKm(km) {
		const value = Number(km);
		if (!Number.isFinite(value)) return "";
		if (value >= 10) return Math.round(value) + " km";
		const rounded = Math.round(value * 10) / 10;
		return rounded.toFixed(1).replace(/\.0$/, "") + " km";
	}

	function formatEtaLabel(seconds, km, now) {
		const remain = Math.max(0, Number(seconds) || 0);
		const distance = formatKm(km);
		if (remain < 20) {
			if (!distance || Number(km) < 0.05) return "Arriving";
			return "Arriving · " + distance;
		}
		const total = Math.round(remain);
		const mins = Math.floor(total / 60);
		const secs = total % 60;
		const time = mins <= 0 ? secs + " sec" : mins + " min " + String(secs).padStart(2, "0") + " sec";
		const clock = formatClock(new Date(now + remain * 1000));
		const parts = [time];
		if (distance) parts.push(distance);
		parts.push("arrive " + clock);
		return parts.join(" · ");
	}

	function routeSteps(legs) {
		const steps = [];
		(legs || []).forEach(function (leg) {
			(leg.steps || []).forEach(function (step) {
				steps.push(step);
			});
		});
		return steps;
	}

	function routeMeters(stops, origin) {
		const pending = remainingStops(stops);
		let cursor = asDriverOrigin(origin);
		let meters = 0;
		pending.forEach(function (stop) {
			const point = stopPoint(stop);
			if (!point || typeof point !== "object") return;
			if (cursor) {
				const segment = distanceMeters(cursor, point);
				if (Number.isFinite(segment)) meters += segment;
			}
			cursor = point;
		});
		return meters;
	}

	function followEta(snapshot, anchorMeters, currentMeters, now) {
		if (!snapshot) return null;
		const moment = now == null ? snapshot.fetchedAt : now;
		const elapsed = Math.max(0, (moment - (snapshot.fetchedAt || moment)) / 1000);
		let seconds = Math.max(0, (Number(snapshot.seconds) || 0) - elapsed);
		let km = Number(snapshot.km);
		if (!Number.isFinite(km)) km = 0;
		const anchor = Number(anchorMeters);
		const current = Number(currentMeters);
		if (km > 0 && Number.isFinite(anchor) && Number.isFinite(current) && anchor > 0 && current < anchor) {
			const ratio = Math.max(0, current / anchor);
			const nextKm = km * ratio;
			const paced = (Number(snapshot.seconds) || 0) * ratio;
			seconds = Math.min(seconds, Math.max(0, paced));
			km = nextKm;
		}
		return {
			seconds: seconds,
			km: Math.round(km * 10) / 10,
			traffic: Boolean(snapshot.traffic),
		};
	}

	function geometricEta(meters, speedKph) {
		const distance = Number(meters);
		if (!Number.isFinite(distance)) return null;
		const km = Math.round((Math.max(0, distance) / 1000) * 10) / 10;
		const speed = Number(speedKph);
		const pace = Number.isFinite(speed) && speed >= 8 ? speed : 40;
		const seconds = km <= 0 ? 0 : (km / pace) * 3600;
		return { seconds: seconds, km: km, traffic: false };
	}

	function tickStops(rows, fetchedAt, now, anchorMeters, currentMeters) {
		const elapsed = Math.max(0, (now - (fetchedAt || now)) / 1000);
		const anchor = Number(anchorMeters);
		const current = Number(currentMeters);
		const moved = Number.isFinite(anchor) && Number.isFinite(current) && anchor > 0 && current < anchor - 30;
		const ratio = moved ? Math.max(0, current / anchor) : 1;
		return (rows || []).map(function (row) {
			const base = Number(row.seconds);
			const baseSeconds = Number.isFinite(base) ? base : (Number(row.minutes) || 0) * 60;
			const ticked = Math.max(0, baseSeconds - elapsed);
			const scaled = baseSeconds * ratio;
			const seconds = moved ? Math.min(ticked, scaled) : ticked;
			const kmFactor = baseSeconds > 0 ? seconds / baseSeconds : ratio;
			return {
				id: row.id,
				seconds: seconds,
				minutes: seconds <= 0 ? 0 : Math.max(1, Math.round(seconds / 60)),
				km: Math.round((Number(row.km) || 0) * kmFactor * 10) / 10,
			};
		});
	}

	function progressEtas(stops, origin, secPerKm) {
		const pace = Number(secPerKm);
		const perKm = Number.isFinite(pace) && pace > 0 ? pace : 90;
		const pending = remainingStops(stops);
		let cursor = asDriverOrigin(origin);
		let seconds = 0;
		let meters = 0;
		const rows = [];
		pending.forEach(function (stop) {
			const point = stopPoint(stop);
			if (!point || typeof point !== "object") return;
			if (!cursor) {
				cursor = point;
				return;
			}
			const segment = distanceMeters(cursor, point);
			if (!Number.isFinite(segment)) return;
			meters += segment;
			seconds += (segment / 1000) * perKm;
			rows.push({
				id: stop.id,
				leg: stop.leg,
				kind: stop.kind,
				seconds: seconds,
				minutes: Math.max(1, Math.round(seconds / 60)),
				km: Math.round((meters / 1000) * 10) / 10,
			});
			cursor = point;
		});
		return rows;
	}

	function bearingDegrees(from, to) {
		if (!from || !to || from.lat == null || to.lat == null) return null;
		const lat1 = (Number(from.lat) * Math.PI) / 180;
		const lat2 = (Number(to.lat) * Math.PI) / 180;
		const dLng = ((Number(to.lng) - Number(from.lng)) * Math.PI) / 180;
		const y = Math.sin(dLng) * Math.cos(lat2);
		const x = Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLng);
		const deg = (Math.atan2(y, x) * 180) / Math.PI;
		return Number.isFinite(deg) ? deg : null;
	}

	function compass(from, to) {
		const deg = bearingDegrees(from, to);
		if (deg == null) return "";
		const names = ["north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"];
		return names[Math.round(((deg + 360) % 360) / 45) % 8];
	}

	function maneuverHeading(maneuver) {
		const headings = {
			"turn-left": -90,
			"turn-sharp-left": -135,
			"turn-slight-left": -45,
			"turn-right": 90,
			"turn-sharp-right": 135,
			"turn-slight-right": 45,
			"uturn-left": 180,
			"uturn-right": 180,
			straight: 0,
			"ramp-left": -45,
			"ramp-right": 45,
			"fork-left": -30,
			"fork-right": 30,
			merge: 0,
			"roundabout-left": -90,
			"roundabout-right": 90,
		};
		return Object.prototype.hasOwnProperty.call(headings, maneuver) ? headings[maneuver] : 0;
	}

	return {
		MAX_WAYPOINTS: MAX_WAYPOINTS,
		URL_WAYPOINTS: URL_WAYPOINTS,
		stopPoint: stopPoint,
		remainingStops: remainingStops,
		buildRoutePlan: buildRoutePlan,
		mapsFallbackUrl: mapsFallbackUrl,
		readRoute: readRoute,
		etasFromLegs: etasFromLegs,
		distanceMeters: distanceMeters,
		pickStepIndex: pickStepIndex,
		shouldRefreshRoute: shouldRefreshRoute,
		liveSeconds: liveSeconds,
		formatMeters: formatMeters,
		formatEtaLabel: formatEtaLabel,
		routeSteps: routeSteps,
		routeMeters: routeMeters,
		followEta: followEta,
		geometricEta: geometricEta,
		tickStops: tickStops,
		progressEtas: progressEtas,
		bearingDegrees: bearingDegrees,
		compass: compass,
		stripHtml: stripHtml,
		maneuverHeading: maneuverHeading,
	};
});
