// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

/**
 * Shared countdown / overdue timers for Time Sensitive Case and flagged operational docs.
 * Uses a server-time offset so client clock drift does not distort remaining time.
 */
frappe.provide("logistics.time_sensitive");

(function () {
	let serverOffsetMs = 0;
	let offsetReady = false;

	function syncServerOffset() {
		return frappe
			.call({
				method: "logistics.time_sensitive.api.get_timer_payload",
				args: { doctype: "User", name: frappe.session.user },
			})
			.then((r) => {
				try {
					const serverNow = frappe.datetime.str_to_obj(
						(r.message && r.message.server_now) || frappe.datetime.now_datetime()
					);
					serverOffsetMs = serverNow.getTime() - Date.now();
				} catch (e) {
					serverOffsetMs = 0;
				}
				offsetReady = true;
			})
			.fail(() => {
				try {
					const serverNow = frappe.datetime.str_to_obj(frappe.datetime.now_datetime());
					serverOffsetMs = serverNow.getTime() - Date.now();
				} catch (e) {
					serverOffsetMs = 0;
				}
				offsetReady = true;
			});
	}

	function nowWithOffset() {
		return new Date(Date.now() + serverOffsetMs);
	}

	function parseDeadline(deadline) {
		if (!deadline) return null;
		try {
			return frappe.datetime.str_to_obj(deadline);
		} catch (e) {
			return null;
		}
	}

	function formatCountdown(seconds) {
		if (seconds === null || seconds === undefined || isNaN(seconds)) return "";
		const overdue = seconds < 0;
		let secs = Math.abs(Math.floor(seconds));
		const days = Math.floor(secs / 86400);
		secs %= 86400;
		const hours = Math.floor(secs / 3600);
		secs %= 3600;
		const mins = Math.floor(secs / 60);
		secs %= 60;
		const parts = [];
		if (days) parts.push(days + "d");
		parts.push(String(hours).padStart(2, "0") + "h");
		parts.push(String(mins).padStart(2, "0") + "m");
		parts.push(String(secs).padStart(2, "0") + "s");
		const label = parts.join(" ");
		return overdue ? "OVERDUE " + label : label;
	}

	function secondsUntil(deadline) {
		const target = parseDeadline(deadline);
		if (!target) return null;
		return (target.getTime() - nowWithOffset().getTime()) / 1000;
	}

	function indicatorColor(seconds, atRiskHours) {
		if (seconds === null) return "blue";
		if (seconds < 0) return "red";
		const atRiskSec = (atRiskHours || 4) * 3600;
		if (seconds <= atRiskSec) return "orange";
		return "blue";
	}

	/**
	 * Mount a live timer into an HTML field or page element.
	 * @param {Object} opts - { $wrapper, deadline, atRiskHours, label }
	 * @returns {Function} stop
	 */
	function mountTimer(opts) {
		const $el = opts.$wrapper;
		if (!$el || !$el.length) return () => {};
		let stopped = false;

		function tick() {
			if (stopped) return;
			const secs = secondsUntil(opts.deadline);
			const text = formatCountdown(secs);
			const color = indicatorColor(secs, opts.atRiskHours);
			const prefix = opts.label ? opts.label + ": " : "";
			$el.html(
				`<span class="indicator-pill ${color} time-sensitive-timer" title="${frappe.utils.escape_html(
					opts.deadline || ""
				)}">${frappe.utils.escape_html(prefix + text)}</span>`
			);
		}

		if (!offsetReady) {
			syncServerOffset().always(() => {
				tick();
			});
		} else {
			tick();
		}
		const handle = setInterval(tick, 1000);
		return () => {
			stopped = true;
			clearInterval(handle);
		};
	}

	function setFormIndicator(frm, deadline, atRiskHours) {
		if (!frm || !deadline) return;
		const secs = secondsUntil(deadline);
		const text = formatCountdown(secs);
		const color = indicatorColor(secs, atRiskHours);
		frm.page.set_indicator(text || __("Time Sensitive"), color);
	}

	function titleWithTimerIcon(value, doc) {
		if (!cint(doc.is_time_sensitive) && doc.doctype !== "Time Sensitive Case") {
			return value;
		}
		const icon = frappe.utils.icon("timer", "sm");
		const tip = [doc.ts_case_type || doc.case_type_name || "", doc.critical_deadline || ""]
			.filter(Boolean)
			.join(" · ");
		return `<span title="${frappe.utils.escape_html(tip)}">${icon} ${frappe.utils.escape_html(
			value || doc.name
		)}</span>`;
	}

	function getListIndicator(doc) {
		const status = doc.sla_status || doc.status;
		if (status === "Breached" || (doc.critical_deadline && secondsUntil(doc.critical_deadline) < 0)) {
			return [__("Breached"), "red", "sla_status,=,Breached"];
		}
		if (status === "At Risk") {
			return [__("At Risk"), "orange", "sla_status,=,At Risk"];
		}
		if (["Activated", "In Execution"].includes(doc.status)) {
			return [__(doc.status), "blue", "status,=," + doc.status];
		}
		if (doc.status === "Delivered" || status === "Completed") {
			return [__("Delivered"), "green", "status,=,Delivered"];
		}
		return [__(doc.status || status || "Draft"), "gray", "status,=," + (doc.status || "")];
	}

	function bindRealtimeToasts() {
		if (logistics.time_sensitive._realtime_bound) return;
		logistics.time_sensitive._realtime_bound = true;
		frappe.realtime.on("time_sensitive_alert", (data) => {
			if (!data) return;
			frappe.show_alert(
				{
					message: __(data.subject || "Time Sensitive Alert"),
					indicator: data.indicator || "orange",
				},
				8
			);
		});
	}

	function cint(v) {
		return parseInt(v, 10) ? 1 : 0;
	}

	// Kick off offset sync once
	$(document).ready(() => {
		syncServerOffset();
		bindRealtimeToasts();
	});

	logistics.time_sensitive.timer = {
		syncServerOffset,
		secondsUntil,
		formatCountdown,
		indicatorColor,
		mountTimer,
		setFormIndicator,
		titleWithTimerIcon,
		getListIndicator,
		bindRealtimeToasts,
	};
})();
