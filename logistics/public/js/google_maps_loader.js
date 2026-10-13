// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

// Load the Maps JavaScript API with loading=async and a callback.
// Script onload fires before the API is ready when loading=async is set, and
// omitting loading=async logs a performance warning on every desk map.
(function (root) {
	"use strict";

	var CALLBACK = "__logisticsGoogleMapsLoaded";
	var pending = [];
	var started = false;

	function ready() {
		return !!(root.google && root.google.maps && root.google.maps.Map);
	}

	function flush(err) {
		var waiters = pending.splice(0, pending.length);
		waiters.forEach(function (fn) {
			try {
				fn(err);
			} catch (e) {
				console.error(e);
			}
		});
	}

	function poll(left) {
		if (ready()) {
			started = false;
			flush();
			return;
		}
		if (left <= 0) {
			started = false;
			flush(new Error("gmaps_timeout"));
			return;
		}
		setTimeout(function () {
			poll(left - 1);
		}, 50);
	}

	function loadGoogleMaps(apiKey, done) {
		if (typeof done !== "function") {
			done = function () {};
		}
		if (ready()) {
			done();
			return;
		}
		pending.push(done);
		if (started) {
			return;
		}
		if (root.document && root.document.querySelector('script[src*="maps.googleapis.com/maps/api/js"]')) {
			started = true;
			poll(120);
			return;
		}
		if (!apiKey) {
			flush(new Error("missing_google_maps_key"));
			return;
		}
		started = true;
		root[CALLBACK] = function () {
			started = false;
			flush();
		};
		var script = root.document.createElement("script");
		script.async = true;
		script.src =
			"https://maps.googleapis.com/maps/api/js?key=" +
			encodeURIComponent(apiKey) +
			"&v=weekly&libraries=geometry&loading=async&callback=" +
			CALLBACK;
		script.onerror = function () {
			started = false;
			flush(new Error("gmaps_load"));
		};
		root.document.head.appendChild(script);
	}

	root.logistics = root.logistics || {};
	root.logistics.load_google_maps = loadGoogleMaps;
})(typeof window !== "undefined" ? window : this);
