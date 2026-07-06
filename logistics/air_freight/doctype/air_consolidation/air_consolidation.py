import math

import frappe
from frappe.exceptions import ValidationError
from frappe.model.document import Document
from frappe import _
from frappe.utils import add_days, cint, cstr, flt, getdate, get_datetime, today
import json
from datetime import datetime, timedelta

from logistics.air_freight.air_consolidation_routing import (
	_default_route_timing_fields,
	consolidation_route_row_from_shipment_header,
	consolidation_route_row_from_shipment_leg,
	routing_signature_from_consolidation_route,
	routing_signature_from_shipment,
	shipment_legs_for_consolidation_copy,
)
from logistics.utils.consolidation_plan import (
	AIR_ALIGNMENT_PREVIEW_MAX_ROWS,
	air_shipment_allowed_on_plan,
	air_shipment_matches_plan_filter,
	assert_air_consolidation_plan_requirements,
	assert_air_plan_fields_for_filter_match,
	conflicting_submitted_air_planning_elsewhere,
	count_filtered_air_shipments,
	get_air_shipment_names_from_consolidation,
	get_filtered_air_shipment_names,
	prevent_consolidation_cargo_edit_when_planning_submitted,
	validate_minimum_air_consolidation_shipments,
	validate_minimum_air_planning_shipments,
)


class AirConsolidation(Document):
    @frappe.whitelist()
    def get_dashboard_html(self):
        """Generate HTML for Dashboard tab: consolidation details, milestones, documents and header alerts."""
        try:
            from logistics.document_management.api import (
                get_dashboard_alerts_html,
                get_document_alerts_html,
            )
            from logistics.document_management.dashboard_layout import build_run_sheet_style_dashboard

            status = self.get("status") or "Draft"
            status_badge_html = f'<span class="dash-status-badge {(status or "draft").lower().replace(" ", "_")}">{frappe.utils.escape_html(status)}</span>'
            header_items = [
                ("Status", status),
                ("Consolidation Date", str(self.consolidation_date) if self.consolidation_date else "—"),
                ("Type", self.consolidation_type or "—"),
                ("Origin", self.origin_airport or "—"),
                ("Destination", self.destination_airport or "—"),
                ("Departure", str(self.departure_date) if self.departure_date else "—"),
                ("Arrival", str(self.arrival_date) if self.arrival_date else "—"),
                ("Airline", self.airline or "—"),
                ("Packages", str(self.total_packages or 0)),
                ("Weight", frappe.format_value(self.total_weight or 0, df=dict(fieldtype="Float"))),
                ("Volume", frappe.format_value(self.total_volume or 0, df=dict(fieldtype="Float"))),
            ]
            alerts_html = get_dashboard_alerts_html("Air Consolidation", self.name or "new")
            try:
                doc_alerts_html = get_document_alerts_html("Air Consolidation", self.name or "new")
            except Exception:
                doc_alerts_html = ""

            milestone_rows = list(self.get("milestones") or [])
            milestone_details = {}
            if milestone_rows:
                names = [m.milestone for m in milestone_rows if m.milestone]
                if names:
                    for lm in frappe.get_all(
                        "Logistics Milestone",
                        filters={"name": ["in", names]},
                        fields=["name", "description"],
                    ):
                        milestone_details[lm.name] = lm.description or lm.name

            cards_html = ""
            for i, m in enumerate(milestone_rows, 1):
                st = (m.status or "Planned").lower().replace(" ", "-")
                desc = milestone_details.get(m.milestone, m.milestone or "Milestone")
                planned = frappe.utils.format_datetime(m.planned_end) if m.planned_end else "—"
                actual = frappe.utils.format_datetime(m.actual_end) if m.actual_end else "—"
                cards_html += f"""
                <div class="dash-card {st}">
                    <div class="card-header"><h5>{desc}</h5><span class="card-num">#{i}</span></div>
                    <div class="card-details">Planned: {planned}<br>Actual: {actual}</div>
                    <span class="card-badge {st}">{m.status or "Planned"}</span>
                </div>"""

            if not cards_html:
                cards_html = '<div class="text-muted">No milestones. Use Get Milestones in Milestones tab. Manage planned shipments in the Shipments tab.</div>'

            return build_run_sheet_style_dashboard(
                header_title=self.name or "Air Consolidation",
                header_subtitle="Air Consolidation",
                header_items=header_items,
                status_badge_html=status_badge_html,
                alerts_html=alerts_html,
                cards_html=cards_html,
                map_points=[],
                map_id_prefix="ac-dash-map",
                doc_alerts_html=doc_alerts_html,
                straight_line=True,
                origin_label=self.origin_airport or "—",
                destination_label=self.destination_airport or "—",
                hide_map=True,
                cards_full_width=True,
            )
        except Exception as e:
            frappe.log_error(f"Air Consolidation get_dashboard_html: {str(e)}", "Air Consolidation Dashboard")
            return "<div class='alert alert-warning'>Error loading dashboard.</div>"

    def validate(self):
        """Validate Air Consolidation document"""
        self._prevent_planning_lines_edit_when_submitted()
        self._prevent_cargo_edit_when_planning_submitted()
        self.validate_dates()
        self.validate_route_consistency()
        self.calculate_consolidation_metrics()
        self.validate_capacity_constraints()
        self.validate_attached_jobs_compatibility()
        self.validate_jobs_not_in_multiple_consolidations()
        self.validate_dangerous_goods_compliance()
        self.validate_accounts()
        self._validate_consolidation_planning_lines()
        self._rollup_is_high_value_from_shipments()
        assert_air_consolidation_plan_requirements(self)

    def _rollup_is_high_value_from_shipments(self):
        """Set is_high_value=1 if any linked Air Shipment is tagged high value."""
        shipments = [
            getattr(r, "air_shipment", None)
            for r in (self.get("consolidation_planning_lines") or [])
            if getattr(r, "air_shipment", None)
        ]
        if not shipments:
            return
        try:
            hv = frappe.db.get_all(
                "Air Shipment",
                filters={"name": ["in", shipments], "is_high_value": 1},
                limit=1,
                pluck="name",
            )
        except Exception:
            return
        if hv:
            self.is_high_value = 1

    def _prevent_planning_lines_edit_when_submitted(self):
        if getattr(self.flags, "ignore_planning_lines_lock", False):
            return
        if getattr(frappe.flags, "in_install", False) or getattr(frappe.flags, "in_migrate", False):
            return
        if getattr(frappe.flags, "in_import", False):
            return
        if self.is_new():
            return
        if (self.air_planning_status or "Draft") != "Submitted":
            return
        prev = self.get_doc_before_save()
        if not prev:
            return

        def shipment_tuple(doc):
            return tuple(
                sorted(
                    getattr(r, "air_shipment", None)
                    for r in (doc.consolidation_planning_lines or [])
                    if getattr(r, "air_shipment", None)
                )
            )

        if shipment_tuple(prev) != shipment_tuple(self):
            frappe.throw(
                _(
                    "Planned shipments cannot be changed while planning status is Submitted. "
                    "Reset planned shipments to draft if you need to edit the list."
                ),
                title=_("Planning locked"),
            )

    def _prevent_cargo_edit_when_planning_submitted(self):
        prevent_consolidation_cargo_edit_when_planning_submitted(
            self,
            planning_status_field="air_planning_status",
            container_field=None,
        )

    def _validate_consolidation_planning_lines(self):
        from logistics.utils.consolidation_plan import get_previous_planning_line_shipments

        rows = self.get("consolidation_planning_lines") or []
        prev_planned = get_previous_planning_line_shipments(self, "air_shipment")
        seen = set()
        for row in rows:
            sh = row.air_shipment
            if not sh:
                continue
            if sh in seen:
                frappe.throw(_("Air Shipment {0} is duplicated in planning lines.").format(sh))
            seen.add(sh)
            ok, msg = air_shipment_allowed_on_plan(sh, retain_existing=(sh in prev_planned))
            if not ok:
                frappe.throw(msg)
            origin = frappe.db.get_value("Air Shipment", sh, "origin_port")
            dest = frappe.db.get_value("Air Shipment", sh, "destination_port")
            if self.origin_airport and origin and origin != self.origin_airport:
                frappe.throw(
                    _("Air Shipment {0} origin {1} does not match consolidation origin {2}.").format(
                        sh, origin, self.origin_airport
                    )
                )
            if self.destination_airport and dest and dest != self.destination_airport:
                frappe.throw(
                    _("Air Shipment {0} destination {1} does not match consolidation destination {2}.").format(
                        sh, dest, self.destination_airport
                    )
                )
            if (self.air_planning_status or "Draft") == "Draft":
                if conflicting_submitted_air_planning_elsewhere(
                    sh, self.name if not self.is_new() else None
                ):
                    frappe.throw(
                        _(
                            "Air Shipment {0} is already reserved on another consolidation's submitted planning."
                        ).format(sh),
                        title=_("Planning Conflict"),
                    )
            if self._consolidation_has_definitive_routing():
                self._validate_shipment_routing_matches_consolidation(sh)

    def _consolidation_has_definitive_routing(self) -> bool:
        """True when consolidation routes include a concrete flight (not empty / TBA placeholder)."""
        if not self.get("consolidation_routes"):
            return False
        sig = self._consolidation_main_routing_signature()
        if not sig:
            return False
        flight = (sig[3] or "").strip()
        return bool(flight) and flight != "TBA"

    def _consolidation_main_routing_signature(self):
        row = self._air_plan_route_fallback_row()
        if not row:
            return None
        return routing_signature_from_consolidation_route(row)

    def _validate_shipment_routing_matches_consolidation(self, air_shipment: str) -> None:
        """Require shipment Main route to match consolidation routing when routes are definitive."""
        if not self._consolidation_has_definitive_routing():
            return
        consol_sig = self._consolidation_main_routing_signature()
        if not consol_sig:
            return
        ship_sig = routing_signature_from_shipment(air_shipment)
        if not (ship_sig[3] or "").strip():
            return
        if ship_sig == consol_sig:
            return
        frappe.throw(
            _(
                "Air Shipment {0} routing (flight/carrier/ports/ETD) does not match this consolidation's "
                "routing legs. Use the same route or copy routing from that shipment first."
            ).format(air_shipment),
            title=_("Route mismatch"),
        )

    def _populate_consolidation_routes_from_air_shipment(self, air_shipment: str, replace: bool = False) -> None:
        """Copy Air Shipment routing_legs into consolidation_routes."""
        job = frappe.get_doc("Air Shipment", air_shipment)
        if replace:
            self.set("consolidation_routes", [])

        legs = shipment_legs_for_consolidation_copy(job)
        if legs:
            for leg in legs:
                row = consolidation_route_row_from_shipment_leg(leg, job)
                if row.get("origin_airport") and row.get("destination_airport"):
                    self.append("consolidation_routes", row)
        else:
            if job.origin_port and job.destination_port:
                self.append("consolidation_routes", consolidation_route_row_from_shipment_header(job))

    def _set_single_direct_route_from_shipment(self, air_shipment: str) -> None:
        """Set one Direct route from shipment header O/D and Main leg flight details."""
        job = frappe.get_doc("Air Shipment", air_shipment)
        if not self.origin_airport and job.origin_port:
            self.origin_airport = job.origin_port
        if not self.destination_airport and job.destination_port:
            self.destination_airport = job.destination_port

        main_leg = None
        for leg in shipment_legs_for_consolidation_copy(job):
            if (getattr(leg, "type", None) or "").strip() == "Main":
                main_leg = leg
                break

        if main_leg:
            row = consolidation_route_row_from_shipment_leg(main_leg, job)
        else:
            row = consolidation_route_row_from_shipment_header(job)

        origin = self.origin_airport or job.origin_port
        dest = self.destination_airport or job.destination_port
        row["origin_airport"] = origin
        row["destination_airport"] = dest
        row["route_type"] = "Direct"

        self.set("consolidation_routes", [])
        if origin and dest:
            self.append("consolidation_routes", row)
        self._sync_consolidation_header_from_routes()

    def _sync_consolidation_header_from_routes(self) -> None:
        """Backfill header airline/flight/ports/ETD from the primary consolidation route."""
        row = self._air_plan_route_fallback_row()
        if not row:
            return
        if not self.origin_airport and row.origin_airport:
            self.origin_airport = row.origin_airport
        if not self.destination_airport and row.destination_airport:
            self.destination_airport = row.destination_airport
        if not self.airline and row.airline:
            self.airline = row.airline
        if not (self.flight_number or "").strip() and row.flight_number:
            self.flight_number = row.flight_number
        if not self.departure_date and row.departure_date:
            dep = row.departure_date
            dep_time = getattr(row, "departure_time", None)
            if dep_time:
                self.departure_date = get_datetime(f"{dep} {dep_time}")
            else:
                self.departure_date = get_datetime(str(dep))
        if not self.arrival_date and row.arrival_date:
            arr = row.arrival_date
            arr_time = getattr(row, "arrival_time", None)
            if arr_time:
                self.arrival_date = get_datetime(f"{arr} {arr_time}")
            else:
                self.arrival_date = get_datetime(str(arr))

    def _maybe_populate_routes_from_added_shipment(self, air_shipment: str) -> None:
        if not air_shipment:
            return
        if self._consolidation_has_definitive_routing():
            self._validate_shipment_routing_matches_consolidation(air_shipment)
            return
        if not self.get("consolidation_routes"):
            self._set_single_direct_route_from_shipment(air_shipment)

    @frappe.whitelist()
    def populate_routing_from_air_shipment(self, air_shipment=None):
        """Replace consolidation routes from one Air Shipment's routing legs."""
        if not air_shipment:
            lines = self.get("consolidation_planning_lines") or []
            for row in lines:
                if getattr(row, "air_shipment", None):
                    air_shipment = row.air_shipment
                    break
        if not air_shipment:
            frappe.throw(
                _("Select an Air Shipment or add one to the planned list first."),
                title=_("No shipment"),
            )
        self._populate_consolidation_routes_from_air_shipment(air_shipment, replace=True)
        self._sync_consolidation_header_from_routes()
        self.save()
        return {"message": _("Routing legs copied from Air Shipment {0}.").format(air_shipment)}

    @frappe.whitelist()
    def populate_routing_from_airports(self):
        """One Direct route from header origin/destination (aligned with Sea Consolidation)."""
        if not self.origin_airport or not self.destination_airport:
            return {"message": _("Set Origin Airport and Destination Airport first.")}
        self.set("consolidation_routes", [])
        dep = getdate(self.departure_date) if self.departure_date else today()
        arr = getdate(self.arrival_date) if self.arrival_date else add_days(dep, 1)
        self.append(
            "consolidation_routes",
            {
                "route_type": "Direct",
                "origin_airport": self.origin_airport,
                "destination_airport": self.destination_airport,
                "airline": self.airline,
                "flight_number": (self.flight_number or "").strip() or "TBA",
                "departure_date": dep,
                "arrival_date": arr,
                "dangerous_goods_allowed": 1,
                **_default_route_timing_fields(),
            },
        )
        self.save()
        return {"message": _("Routing leg created from origin to destination.")}

    def before_save(self):
        """Actions before saving the document"""
        # Apply settings defaults if this is a new document
        if self.is_new():
            self.apply_settings_defaults()
        
        self.update_consolidation_status()
        self.calculate_total_charges()
        self.optimize_consolidation_ratio()
        # Job Number will be created in after_insert method
    
    def after_insert(self):
        """Create Job Number after document is inserted"""
        # Apply settings defaults if not already applied
        if not hasattr(self, '_settings_applied'):
            self.apply_settings_defaults()
        
        # Create job costing if enabled in settings
        settings = self.get_air_freight_settings()
        if settings and settings.auto_create_job_costing:
            self.create_job_number_if_needed()
        
        # Save the document to persist changes
        if self.job_number:
            self.save(ignore_permissions=True)
    
    def on_update(self):
        """Actions after document update"""
        self.update_related_air_freight_jobs()
        self.send_consolidation_notifications()
        if getattr(self, "auto_send_eawb", 0) and self.master_awb:
            if self.is_new() or self.has_value_changed("auto_send_eawb") or self.has_value_changed("master_awb"):
                try:
                    mawb_status = frappe.db.get_value("Master Air Waybill", self.master_awb, "eawb_status")
                    if mawb_status not in ("Accepted", "Submitted"):
                        from logistics.air_freight.iata_cargo_xml.eawb_service import (
                            auto_send_eawb_for_consolidation,
                        )

                        auto_send_eawb_for_consolidation(self.name)
                except Exception:
                    frappe.log_error(frappe.get_traceback(), "Air Consolidation auto-send e-AWB")

    def before_submit(self):
        if not self.consolidation_packages:
            frappe.throw(_("At least one package must be added to the consolidation"))
        if not self.consolidation_routes:
            frappe.throw(_("At least one route must be defined for the consolidation"))
        validate_minimum_air_consolidation_shipments(self)
        if get_air_shipment_names_from_consolidation(self) and (self.air_planning_status or "Draft") != "Submitted":
            frappe.throw(
                _("Submit the planned shipment list (Planning status) before submitting the consolidation."),
                title=_("Planning required"),
            )

    def _air_plan_route_fallback_row(self):
        """Prefer child route matching header O/D; else first route (main leg data often lives here)."""
        routes = self.get("consolidation_routes") or []
        if not routes:
            return None
        ho, hd = self.origin_airport, self.destination_airport
        for row in routes:
            ro = getattr(row, "origin_airport", None)
            rd = getattr(row, "destination_airport", None)
            if ho and hd and ro == ho and rd == hd:
                return row
        return routes[0]

    def _air_plan_match_dict(self):
        dep = self.departure_date
        airline = self.airline
        flight_number = self.flight_number
        r = self._air_plan_route_fallback_row()
        if r:
            if not dep:
                # Route table uses Date; strict match uses calendar day only (getdate on target).
                dep = getattr(r, "departure_date", None) or dep
            if not airline:
                airline = getattr(r, "airline", None)
            if not (flight_number or "").strip():
                flight_number = getattr(r, "flight_number", None)
        return {
            "company": self.company,
            "branch": self.branch,
            "origin_airport": self.origin_airport,
            "destination_airport": self.destination_airport,
            "target_departure": dep,
            "airline": airline,
            "flight_number": flight_number,
        }

    def _merged_air_plan_match_dict_from_dialog(self, filter_overrides):
        keys = (
            "company",
            "branch",
            "origin_airport",
            "destination_airport",
            "target_departure",
            "airline",
            "flight_number",
        )
        base = dict(self._air_plan_match_dict())
        o = filter_overrides or {}
        if isinstance(o, str):
            o = frappe.parse_json(o) or {}
        if not isinstance(o, dict):
            o = {}
        # Explicit empty override clears that criterion so users can e.g. filter by airline only
        # without Company/Branch/Flight from the consolidation header still being applied.
        for key in keys:
            if key not in o:
                continue
            val = o[key]
            if val is None or (isinstance(val, str) and not str(val).strip()):
                base[key] = None
                continue
            base[key] = val
        return base

    @frappe.whitelist()
    def preview_matching_air_shipments(self, filter_overrides=None):
        """Return all filter-matching shipments (one scrollable list; capped for safety).

        Matching uses plan criteria only (company, branch, ports, dates, airline, flight, etc.).
        Document ``name`` may use any naming series (e.g. ASP-, legacy prefixes); none are excluded by ID pattern.
        """
        # Do not reload from DB: the dialog reads frm.doc (including unsaved edits). Reloading
        # would query with stale header fields while the UI still shows the user's criteria.
        if self.is_new():
            return {"error": _("Save the consolidation first.")}

        merged = self._merged_air_plan_match_dict_from_dialog(filter_overrides)
        try:
            assert_air_plan_fields_for_filter_match(merged)
        except ValidationError as e:
            return {"error": cstr(getattr(e, "message", e))}

        total_count = count_filtered_air_shipments(merged)
        candidates = get_filtered_air_shipment_names(
            merged,
            offset=0,
            limit=AIR_ALIGNMENT_PREVIEW_MAX_ROWS,
        )
        present = {
            r.air_shipment
            for r in (self.get("consolidation_planning_lines") or [])
            if getattr(r, "air_shipment", None)
        }

        rows = []
        for name in candidates:
            shipment = frappe.db.get_value(
                "Air Shipment",
                name,
                [
                    "name",
                    "job_status",
                    "origin_port",
                    "destination_port",
                    "airline",
                    "etd",
                    "company",
                    "branch",
                ],
                as_dict=True,
            ) or {}

            row = {"name": name, "job_status": shipment.get("job_status") or "", "row_type": "eligible"}
            if shipment.get("company") and shipment.get("branch"):
                row["subtitle"] = "{0} · {1}".format(
                    shipment.get("company"),
                    shipment.get("branch"),
                )
            if name in present:
                row["row_type"] = "already"
                row["origin_port"] = shipment.get("origin_port") or ""
                row["destination_port"] = shipment.get("destination_port") or ""
                row["airline"] = shipment.get("airline") or ""
                row["etd"] = shipment.get("etd")
                rows.append(row)
                continue
            ok, msg = air_shipment_allowed_on_plan(name)
            if not ok:
                row["row_type"] = "blocked"
                row["reason"] = cstr(msg)
                rows.append(row)
                continue
            if conflicting_submitted_air_planning_elsewhere(name, self.name):
                row["row_type"] = "blocked"
                row["reason"] = _("Reserved on another consolidation's submitted planning.")
                rows.append(row)
                continue
            row["origin_port"] = shipment.get("origin_port") or ""
            row["destination_port"] = shipment.get("destination_port") or ""
            row["airline"] = shipment.get("airline") or ""
            row["etd"] = shipment.get("etd")
            rows.append(row)

        addable = len([r for r in rows if r.get("row_type") == "eligible"])
        banner = _("{0} match(es); {1} can be added").format(total_count, addable)
        if total_count > AIR_ALIGNMENT_PREVIEW_MAX_ROWS:
            banner += " · " + _("Showing first {0} rows; narrow filters if you need the rest.").format(
                AIR_ALIGNMENT_PREVIEW_MAX_ROWS
            )
        return {
            "rows": rows,
            "message": banner,
            "total_count": total_count,
        }

    @frappe.whitelist()
    def apply_selected_air_shipments_to_planning(self, shipment_names, filter_overrides=None):
        """Append shipments chosen in the alignment dialog."""
        names = frappe.parse_json(shipment_names) if isinstance(shipment_names, str) else shipment_names
        if not names:
            frappe.throw(_("Select at least one shipment."), title=_("Nothing selected"))

        merged = self._merged_air_plan_match_dict_from_dialog(filter_overrides)
        try:
            assert_air_plan_fields_for_filter_match(merged)
        except ValidationError as e:
            frappe.throw(cstr(getattr(e, "message", e)))

        self.reload()
        if (self.air_planning_status or "Draft") == "Submitted":
            frappe.throw(_("Cannot add shipments after planning is submitted."), title=_("Planning locked"))

        added, skipped = [], []
        seen = set()
        routes_definitive = self._consolidation_has_definitive_routing()
        for nm in names:
            if nm in seen:
                continue
            seen.add(nm)
            if not air_shipment_matches_plan_filter(nm, merged):
                skipped.append(nm)
                continue
            ok, msg = air_shipment_allowed_on_plan(nm)
            if not ok:
                frappe.throw(cstr(msg))
            if conflicting_submitted_air_planning_elsewhere(nm, self.name):
                frappe.throw(_("Air Shipment {0} cannot be reserved on this consolidation.").format(nm))
            if routes_definitive:
                self._validate_shipment_routing_matches_consolidation(nm)
            self.append("consolidation_planning_lines", {"air_shipment": nm})
            self._append_consolidation_packages_from_air_shipment(nm)
            if not routes_definitive and not self.get("consolidation_routes"):
                self._set_single_direct_route_from_shipment(nm)
                routes_definitive = self._consolidation_has_definitive_routing()
            added.append(nm)

        self.save()
        msg = _("{0} added").format(len(added))
        if skipped:
            msg += " · " + _("{0} not applied (criteria changed or not eligible).").format(len(skipped))
        return {"added": added, "skipped": skipped, "message": msg}

    @frappe.whitelist()
    def fetch_matching_air_shipments(self):
        self.reload()
        if (self.air_planning_status or "Draft") == "Submitted":
            frappe.throw(_("Cannot fetch shipments after planning is submitted."), title=_("Planning locked"))
        if self.is_new():
            frappe.throw(_("Save the consolidation before fetching shipments."), title=_("Save required"))
        assert_air_plan_fields_for_filter_match(self._air_plan_match_dict())
        candidates = get_filtered_air_shipment_names(self._air_plan_match_dict())
        present = {
            r.air_shipment
            for r in (self.get("consolidation_planning_lines") or [])
            if getattr(r, "air_shipment", None)
        }
        added, already_present, skipped = [], [], []
        routes_definitive = self._consolidation_has_definitive_routing()
        for name in candidates:
            if name in present:
                already_present.append(name)
                continue
            ok, msg = air_shipment_allowed_on_plan(name)
            if not ok:
                skipped.append({"shipment": name, "reason": msg})
                continue
            if conflicting_submitted_air_planning_elsewhere(name, self.name):
                skipped.append(
                    {
                        "shipment": name,
                        "reason": _("Reserved on another consolidation's submitted planning."),
                    }
                )
                continue
            if routes_definitive:
                try:
                    self._validate_shipment_routing_matches_consolidation(name)
                except ValidationError as e:
                    skipped.append({"shipment": name, "reason": cstr(getattr(e, "message", e))})
                    continue
            self.append("consolidation_planning_lines", {"air_shipment": name})
            self._append_consolidation_packages_from_air_shipment(name)
            if not routes_definitive and not self.get("consolidation_routes"):
                self._set_single_direct_route_from_shipment(name)
                routes_definitive = self._consolidation_has_definitive_routing()
            added.append(name)
            present.add(name)
        self.save()
        return {"added": added, "already_present": already_present, "skipped": skipped}

    @frappe.whitelist()
    def submit_air_planning(self):
        self.reload()
        if (self.air_planning_status or "Draft") == "Submitted":
            frappe.throw(_("Planning is already submitted."), title=_("Already submitted"))
        if not self.get("consolidation_planning_lines"):
            frappe.throw(
                _("Add at least one shipment to planning before submitting."), title=_("No Lines")
            )
        validate_minimum_air_planning_shipments(self)
        self.air_planning_status = "Submitted"
        if not self.planning_owner:
            self.planning_owner = frappe.session.user
        self.save()
        return self.air_planning_status

    @frappe.whitelist()
    def cancel_air_planning_submit(self):
        self.reload()
        if (self.air_planning_status or "Draft") != "Submitted":
            frappe.throw(_("Planning is not submitted."), title=_("Not submitted"))
        if self.docstatus != 0:
            frappe.throw(
                _("Cancel planning only while the consolidation is still draft (not submitted)."),
                title=_("Not allowed"),
            )
        self.air_planning_status = "Draft"
        self.planning_owner = None
        self.save()
        return self.air_planning_status
    
    def validate_route_consistency(self):
        """Validate route consistency and connectivity"""
        if len(self.consolidation_routes) > 1:
            for i, route in enumerate(self.consolidation_routes):
                if i > 0:
                    # Check if destination of previous route matches origin of current route
                    prev_route = self.consolidation_routes[i-1]
                    if prev_route.destination_airport != route.origin_airport:
                        frappe.throw(
                            _("Route {0}: Origin airport must match destination of previous route").format(i + 1)
                        )
    
    def validate_capacity_constraints(self):
        """Validate capacity constraints for all routes"""
        total_weight = flt(self.total_weight or 0)
        total_volume = flt(self.total_volume or 0)
        for i, route in enumerate(self.consolidation_routes, start=1):
            if route.cargo_capacity_kg and total_weight > route.cargo_capacity_kg:
                frappe.throw(_("Route {0}: Total weight exceeds cargo capacity").format(i))

            if route.cargo_capacity_volume and total_volume > route.cargo_capacity_volume:
                frappe.throw(_("Route {0}: Total volume exceeds cargo capacity").format(i))
    
    def validate_attached_jobs_compatibility(self):
        """Validate that attached Air Shipments are compatible for consolidation"""
        if not self.consolidation_packages:
            return
        
        # Get all attached Air Shipments
        attached_jobs = []
        for package in self.consolidation_packages:
            if package.air_freight_job:
                attached_jobs.append(package.air_freight_job)
        
        if not attached_jobs:
            return
        
        # Get job details
        jobs_data = frappe.get_all(
            "Air Shipment",
            filters={"name": ["in", attached_jobs]},
            fields=["name", "origin_port", "destination_port", "service_level", "contains_dangerous_goods", "direction"]
        )
        
        if not jobs_data:
            return
        
        # Check all jobs have same origin and destination airports
        first_job = jobs_data[0]
        for job in jobs_data[1:]:
            if job.origin_port != first_job.origin_port:
                frappe.throw(
                    _("Air Shipment {0} has different origin port ({1}) than other shipments ({2}). All shipments in a consolidation must have the same origin and destination.").format(
                        job.name, job.origin_port, first_job.origin_port
                    ),
                    title=_("Consolidation Compatibility Error")
                )
            
            if job.destination_port != first_job.destination_port:
                frappe.throw(
                    _("Air Shipment {0} has different destination port ({1}) than other shipments ({2}). All shipments in a consolidation must have the same origin and destination.").format(
                        job.name, job.destination_port, first_job.destination_port
                    ),
                    title=_("Consolidation Compatibility Error")
                )
            
            # Check direction compatibility
            if job.direction != first_job.direction:
                frappe.throw(
                    _("Air Shipment {0} has different direction ({1}) than other shipments ({2}). All shipments in a consolidation must have the same direction.").format(
                        job.name, job.direction, first_job.direction
                    ),
                    title=_("Consolidation Compatibility Error")
                )
    
    def validate_jobs_not_in_multiple_consolidations(self):
        """Validate that Air Shipments are not already in another consolidation"""
        if not self.consolidation_packages:
            return
        
        # Get all attached Air Shipments
        attached_jobs = []
        for package in self.consolidation_packages:
            if package.air_freight_job:
                attached_jobs.append(package.air_freight_job)
        
        if not attached_jobs:
            return
        
        # Check if any of these jobs are already in another consolidation
        existing_consolidations = frappe.get_all(
            "Air Consolidation Packages",
            filters={
                "air_freight_job": ["in", attached_jobs],
                "parent": ["!=", self.name]
            },
            fields=["parent", "air_freight_job"],
            group_by="air_freight_job"
        )
        
        if existing_consolidations:
            for consolidation in existing_consolidations:
                frappe.throw(
                    _("Air Shipment {0} is already included in consolidation {1}. A shipment can only be in one consolidation at a time.").format(
                        consolidation.air_freight_job, consolidation.parent
                    ),
                    title=_("Consolidation Conflict Error")
                )
    
    def calculate_consolidation_metrics(self):
        """Calculate consolidation metrics"""
        packages = self.consolidation_packages or []

        if packages:
            self.total_packages = sum(package.package_count or 0 for package in packages)
            self.total_weight = sum(package.package_weight or 0 for package in packages)
            self.total_volume = sum(package.package_volume or 0 for package in packages)
        else:
            self.total_packages = 0
            self.total_weight = 0
            self.total_volume = 0

        from logistics.utils.measurements import IATA_VOLUMETRIC_DENSITY_KG_M3

        settings = self.get_air_freight_settings()
        volume_to_weight_factor = IATA_VOLUMETRIC_DENSITY_KG_M3
        chargeable_weight_calculation = "Higher of Both"

        if settings:
            volume_to_weight_factor = settings.volume_to_weight_factor or IATA_VOLUMETRIC_DENSITY_KG_M3
            chargeable_weight_calculation = settings.chargeable_weight_calculation or "Higher of Both"

        volume_weight = (self.total_volume or 0) * volume_to_weight_factor

        if chargeable_weight_calculation == "Actual Weight":
            self.chargeable_weight = self.total_weight or 0
        elif chargeable_weight_calculation == "Volume Weight":
            self.chargeable_weight = volume_weight
        else:
            self.chargeable_weight = max(self.total_weight or 0, volume_weight)

        if self.total_weight and self.total_weight > 0:
            self.consolidation_ratio = (self.chargeable_weight / self.total_weight) * 100
        else:
            self.consolidation_ratio = 0
    
    def validate_dangerous_goods_compliance(self):
        """Validate dangerous goods compliance for consolidation"""
        dg_packages = [p for p in self.consolidation_packages if p.contains_dangerous_goods]
        
        if dg_packages:
            # Check if all routes allow dangerous goods
            for i, route in enumerate(self.consolidation_routes, start=1):
                if not route.dangerous_goods_allowed:
                    frappe.throw(
                        _("Route {0} does not allow dangerous goods, but consolidation contains DG packages").format(i)
                    )
            
            # Validate DG segregation requirements
            self.validate_dg_segregation(dg_packages)
    
    def validate_dg_segregation(self, dg_packages):
        """Validate dangerous goods segregation requirements"""
        dg_classes = [p.dg_class for p in dg_packages if p.dg_class]
        
        # Check for incompatible DG classes
        incompatible_pairs = [
            ("1", "2"),  # Explosives with gases
            ("3", "5"),  # Flammable liquids with oxidizing substances
            ("4", "5"),  # Flammable solids with oxidizing substances
        ]
        
        for class1, class2 in incompatible_pairs:
            if class1 in dg_classes and class2 in dg_classes:
                frappe.throw(_("Incompatible dangerous goods classes {0} and {1} cannot be consolidated together".format(class1, class2)))
    
    def update_consolidation_status(self):
        """Update consolidation status based on current data"""
        if self.status == "Draft":
            if self.consolidation_packages and self.consolidation_routes:
                self.status = "Planning"
        elif self.status == "Planning":
            if self.master_awb:
                self.status = "Ready for Departure"
        elif self.status == "Ready for Departure":
            if self.departure_date and self.departure_date <= frappe.utils.now():
                self.status = "In Transit"
        elif self.status == "In Transit":
            if self.arrival_date and self.arrival_date <= frappe.utils.now():
                self.status = "Delivered"

    def _distinct_air_shipment_count_for_charges(self) -> int:
        """Distinct Air Shipments on cargo plus planning lines (same spirit as before_submit)."""
        names = set(get_air_shipment_names_from_consolidation(self))
        for row in self.get("consolidation_planning_lines") or []:
            sh = getattr(row, "air_shipment", None)
            if sh:
                names.add(sh)
        return len(names)

    def _sync_air_charge_quantity_from_parent(self, charge) -> None:
        """Per Unit quantity from consolidation metrics + unit_type (same as charge engine / desk)."""
        if charge.revenue_calculation_method != "Per Unit":
            return
        uom = (getattr(charge, "unit_of_measure", None) or "").strip().lower()
        if uom == "shipment":
            charge.quantity = flt(self._distinct_air_shipment_count_for_charges())
            return
        unit_type = getattr(charge, "unit_type", None)
        if not unit_type:
            return
        from logistics.utils.charges_calculation import get_quantity_from_parent_by_unit_type

        charge.quantity = flt(get_quantity_from_parent_by_unit_type(self, unit_type))

    def calculate_total_charges(self):
        """Calculate total charges for the consolidation"""
        total_charges = 0
        
        cw = flt(self.chargeable_weight or 0)
        for charge in self.consolidation_charges:
            if charge.revenue_calculation_method == "Per Unit":
                self._sync_air_charge_quantity_from_parent(charge)
                # Align with shared charge engine and child row validate: unit_rate × quantity.
                charge.base_amount = charge.unit_rate * flt(charge.quantity or 0)
            elif charge.revenue_calculation_method == "Flat Rate":
                charge.base_amount = charge.unit_rate
            elif charge.revenue_calculation_method == "Percentage":
                charge.base_amount = charge.unit_rate * (cw * 0.01)
            
            # Calculate discount (must set discount_amount; unsaved rows can leave it None)
            if charge.discount_percentage and charge.base_amount is not None:
                charge.discount_amount = flt(charge.base_amount) * (
                    flt(charge.discount_percentage) / 100
                )
            else:
                charge.discount_amount = 0

            # Calculate total amount
            charge.total_amount = (
                flt(charge.base_amount)
                - flt(charge.discount_amount)
                + flt(charge.surcharge_amount)
            )
            
            total_charges += charge.total_amount
        
        # Calculate cost per kg
        if cw > 0:
            self.cost_per_kg = total_charges / cw
        else:
            self.cost_per_kg = 0
    
    def optimize_consolidation_ratio(self):
        """Optimize consolidation ratio for better space utilization"""
        tw = flt(self.total_weight or 0)
        tv = flt(self.total_volume or 0)
        if tw > 0 and tv > 0:
            # Get settings for volume to weight factor
            from logistics.utils.measurements import IATA_VOLUMETRIC_DENSITY_KG_M3

            settings = self.get_air_freight_settings()
            standard_density = IATA_VOLUMETRIC_DENSITY_KG_M3
            
            if settings:
                standard_density = settings.volume_to_weight_factor or IATA_VOLUMETRIC_DENSITY_KG_M3
            
            # Calculate density
            density = tw / tv
            
            if density < standard_density:
                # Low density cargo - volume weight applies
                cw = flt(self.chargeable_weight or 0)
                self.consolidation_ratio = (cw / tw) * 100
            else:
                # High density cargo - actual weight applies
                self.consolidation_ratio = 100
    
    def update_related_air_freight_jobs(self):
        """Update related Air Shipments with consolidation information"""
        for package in self.consolidation_packages:
            if package.air_freight_job:
                # Update the Air Shipment with consolidation reference
                frappe.db.set_value("Air Shipment", package.air_freight_job, {
                    "consolidation_reference": self.name,
                    "consolidation_status": package.consolidation_status
                })
    
    def send_consolidation_notifications(self):
        """Send notifications for consolidation status changes"""
        if self.status in ["Ready for Departure", "In Transit", "Delivered"]:
            # Get all related customers
            customers = set()
            for package in self.consolidation_packages:
                if package.shipper:
                    customers.add(package.shipper)
                if package.consignee:
                    customers.add(package.consignee)
            
            # Send notifications
            for customer in customers:
                self.send_customer_notification(customer)
    
    def send_customer_notification(self, customer):
        """Send notification to customer about consolidation status"""
        subject = f"Consolidation {self.name} - Status Update"
        message = f"""
        Your consolidation {self.name} status has been updated to: {self.status}
        
        Route: {self.origin_airport} → {self.destination_airport}
        Departure: {self.departure_date}
        Arrival: {self.arrival_date}
        
        Please contact us for any questions.
        """
        
        frappe.sendmail(
            recipients=[customer],
            subject=subject,
            message=message
        )

    def _package_references_in_use_air(self):
        refs = set()
        for row in self.get("consolidation_packages") or []:
            ref = getattr(row, "package_reference", None)
            if ref:
                refs.add(ref)
        return refs

    def _allocate_consolidation_package_reference_air(self, air_shipment, idx, line_reference_no, used_refs):
        """Stable unique ``package_reference`` for Air Consolidation Packages (autoname + global unique)."""

        def _is_free(candidate):
            if not candidate:
                return False
            if candidate in used_refs:
                return False
            return not frappe.db.exists("Air Consolidation Packages", candidate)

        raw = (line_reference_no or "").strip()
        if _is_free(raw):
            used_refs.add(raw)
            return raw
        base = "{0}-P{1}".format(air_shipment, idx)
        ref = base
        suffix = 1
        while not _is_free(ref):
            suffix += 1
            ref = "{0}-{1}".format(base, suffix)
        used_refs.add(ref)
        return ref

    def _emergency_contact_from_air_pkg_line(self, sp):
        parts = []
        for f in ("emergency_contact_name", "emergency_contact_phone", "emergency_contact_email"):
            v = getattr(sp, f, None)
            if v is None:
                continue
            s = str(v).strip()
            if s:
                parts.append(s)
        return " / ".join(parts) if parts else ""

    @staticmethod
    def _other_commodity_code_for_consolidation(code):
        """Return a value safe for ``consolidation_packages.commodity`` (Link: Other Commodity Code).

        Package lines on Air Shipment use Link ``Commodity``; names may differ or point to missing rows.
        """
        if code is None:
            return None
        name = cstr(code).strip()
        if not name:
            return None
        return name if frappe.db.exists("Other Commodity Code", name) else None

    def _first_consolidation_commodity_from_air_shipment(self, job):
        for sp in job.get("packages") or []:
            oc = self._other_commodity_code_for_consolidation(getattr(sp, "commodity", None))
            if oc:
                return oc
        return None

    def _air_consolidation_row_dg_fields(self, sp, job):
        """Return (contains_dg, dg_class, un_number, proper_shipping_name, emergency_contact) for child validation."""
        line_dg = bool(
            getattr(sp, "dg_substance", None)
            or (getattr(sp, "dg_class", None) or "").strip()
            or (getattr(sp, "un_number", None) or "").strip()
        )
        emergency = self._emergency_contact_from_air_pkg_line(sp)
        dg_c = (getattr(sp, "dg_class", None) or "").strip() or None
        un = (getattr(sp, "un_number", None) or "").strip() or None
        psn = (getattr(sp, "proper_shipping_name", None) or "").strip() or None
        if line_dg and dg_c and un and psn and emergency:
            return True, dg_c, un, psn, emergency
        if line_dg or (job.contains_dangerous_goods and not line_dg):
            # Incomplete DG data on line or header-only DG — store as non-DG row so save validates.
            return False, None, None, None, None
        return False, None, None, None, None

    def _append_one_air_consolidation_package_row(
        self,
        air_shipment,
        job,
        *,
        package_reference,
        package_type,
        package_count,
        package_weight,
        package_volume,
        commodity,
        description,
        contains_dangerous_goods,
        dg_class,
        un_number,
        proper_shipping_name,
        emergency_contact,
        temperature_controlled,
        min_temperature,
        max_temperature,
    ):
        row = self.append(
            "consolidation_packages",
            {
                "package_reference": package_reference,
                "air_freight_job": air_shipment,
                "shipper": job.shipper,
                "consignee": job.consignee,
                "package_type": package_type,
                "package_count": package_count,
                "package_weight": package_weight,
                "package_volume": package_volume,
                "commodity": commodity,
                "description": description or "",
                "contains_dangerous_goods": 1 if contains_dangerous_goods else 0,
                "dg_class": dg_class or None,
                "un_number": un_number or None,
                "proper_shipping_name": proper_shipping_name or None,
                "emergency_contact": emergency_contact or None,
                "temperature_controlled": 1 if temperature_controlled else 0,
                "min_temperature": min_temperature,
                "max_temperature": max_temperature,
            },
        )
        return row

    def _append_consolidation_packages_from_air_shipment(self, air_shipment):
        """Mirror Air Shipment package lines into ``consolidation_packages`` (or one header summary row).

        Skips if any consolidation package row already exists for this shipment on this document.
        Used when shipments are added via planning alignment (same pattern as Sea Consolidation).
        """
        if not air_shipment:
            return []
        if self.name and frappe.db.exists(
            "Air Consolidation Packages",
            {"air_freight_job": air_shipment, "parent": self.name},
        ):
            return []

        job = frappe.get_doc("Air Shipment", air_shipment)
        used_refs = self._package_references_in_use_air()
        appended = []
        pkg_lines = [r for r in (job.get("packages") or []) if r is not None]

        if pkg_lines:
            for i, sp in enumerate(pkg_lines, start=1):
                n_packs = flt(getattr(sp, "no_of_packs", 0) or 0)
                if n_packs > 0:
                    pack_count = max(1, cint(math.ceil(n_packs)))
                else:
                    pack_count = 1
                w = flt(getattr(sp, "weight", 0) or 0)
                v = flt(getattr(sp, "volume", 0) or 0)
                if w <= 0:
                    tw = flt(getattr(job, "total_weight", None) or getattr(job, "weight", None) or 0)
                    w = tw / len(pkg_lines) if tw else 0
                if w <= 0:
                    w = 0.01
                line_ref = getattr(sp, "reference_no", None)
                pkg_ref = self._allocate_consolidation_package_reference_air(
                    air_shipment, i, line_ref, used_refs
                )
                dg_ok, dg_c, un, psn, emerg = self._air_consolidation_row_dg_fields(sp, job)
                temp_flag = bool(getattr(sp, "temp_controlled", 0))
                row = self._append_one_air_consolidation_package_row(
                    air_shipment,
                    job,
                    package_reference=pkg_ref,
                    package_type="Box",
                    package_count=pack_count,
                    package_weight=w,
                    package_volume=v,
                    commodity=self._other_commodity_code_for_consolidation(getattr(sp, "commodity", None)),
                    description=getattr(sp, "goods_description", None) or "",
                    contains_dangerous_goods=dg_ok,
                    dg_class=dg_c,
                    un_number=un,
                    proper_shipping_name=psn,
                    emergency_contact=emerg,
                    temperature_controlled=temp_flag,
                    min_temperature=getattr(sp, "min_temperature", None) if temp_flag else None,
                    max_temperature=getattr(sp, "max_temperature", None) if temp_flag else None,
                )
                appended.append(row)
        else:
            pkg_ref = self._allocate_consolidation_package_reference_air(air_shipment, 1, None, used_refs)
            tw = flt(getattr(job, "total_weight", None) or getattr(job, "weight", None) or 0)
            if tw <= 0:
                tw = 0.01
            row = self._append_one_air_consolidation_package_row(
                air_shipment,
                job,
                package_reference=pkg_ref,
                package_type="Box",
                package_count=max(1, cint(job.packs or 1)),
                package_weight=tw,
                package_volume=flt(getattr(job, "total_volume", None) or getattr(job, "volume", None) or 0),
                commodity=None,
                description=getattr(job, "description", None) or "",
                contains_dangerous_goods=False,
                dg_class=None,
                un_number=None,
                proper_shipping_name=None,
                emergency_contact=None,
                temperature_controlled=0,
                min_temperature=None,
                max_temperature=None,
            )
            appended.append(row)

        return appended

    @frappe.whitelist()
    def add_package_from_job(self, air_freight_job):
        """Add package from Air Shipment to consolidation"""
        job = frappe.get_doc("Air Shipment", air_freight_job)
        
        # Check if job is already in consolidation
        existing_package = frappe.db.exists("Air Consolidation Packages", {
            "air_freight_job": air_freight_job,
            "parent": self.name
        })
        
        if existing_package:
            frappe.throw(_("This Air Shipment is already included in this consolidation"))
        
        # Add package to consolidation
        package = self.append("consolidation_packages", {})
        package.air_freight_job = air_freight_job
        package.shipper = job.shipper
        package.consignee = job.consignee
        package.package_type = "Box"  # Default, can be updated
        package.package_count = job.packs or 1
        package.package_weight = getattr(job, "total_weight", None) or getattr(job, "weight", None) or 0
        package.package_volume = getattr(job, "total_volume", None) or getattr(job, "volume", None) or 0
        package.commodity = self._first_consolidation_commodity_from_air_shipment(job)
        package.description = getattr(job, "description", None) or ""
        package.contains_dangerous_goods = job.contains_dangerous_goods or 0
        
        self.save()
        return package
    
    @frappe.whitelist()
    def optimize_route_selection(self):
        """Optimize route selection based on cost and time"""
        if not self.consolidation_routes:
            return
        
        # Calculate cost and time for each route
        route_scores = []
        for route in self.consolidation_routes:
            score = self.calculate_route_score(route)
            route_scores.append((route, score))
        
        # Sort by score (lower is better)
        route_scores.sort(key=lambda x: x[1])

        # Child row order follows idx (same pattern as Sea Consolidation Routes without route_sequence)
        for i, (route, score) in enumerate(route_scores, start=1):
            route.idx = i

        self.save()
        return route_scores
    
    def calculate_route_score(self, route):
        """Calculate optimization score for a route"""
        # Factors: cost, time, capacity utilization
        cost_factor = route.total_cost_per_kg or 0
        time_factor = route.transit_time_hours or 0
        capacity_factor = 1 - (route.utilization_percentage or 0) / 100
        
        # Weighted score (lower is better)
        score = (cost_factor * 0.5) + (time_factor * 0.3) + (capacity_factor * 0.2)
        return score
    
    @frappe.whitelist()
    def generate_consolidation_report(self):
        """Generate consolidation report"""
        report_data = {
            "consolidation_id": self.name,
            "status": self.status,
            "total_packages": self.total_packages,
            "total_weight": self.total_weight,
            "total_volume": self.total_volume,
            "chargeable_weight": self.chargeable_weight,
            "consolidation_ratio": self.consolidation_ratio,
            "cost_per_kg": self.cost_per_kg,
            "routes": [],
            "packages": []
        }
        
        # Add route information (sequence = row order in grid)
        for seq, route in enumerate(self.consolidation_routes, start=1):
            report_data["routes"].append({
                "sequence": seq,
                "origin": route.origin_airport,
                "destination": route.destination_airport,
                "airline": route.airline,
                "flight_number": route.flight_number,
                "departure": route.departure_date,
                "arrival": route.arrival_date,
                "status": route.route_status
            })
        
        # Add package information
        for package in self.consolidation_packages:
            report_data["packages"].append({
                "reference": package.package_reference,
                "air_freight_job": package.air_freight_job,
                "shipper": package.shipper,
                "consignee": package.consignee,
                "weight": package.package_weight,
                "volume": package.package_volume,
                "status": package.consolidation_status
            })
        
        return report_data
    
    @frappe.whitelist()
    def check_capacity_availability(self):
        """Check capacity availability for all routes"""
        capacity_info = []
        
        for seq, route in enumerate(self.consolidation_routes, start=1):
            available_weight = route.available_capacity_kg or 0
            available_volume = route.available_capacity_volume or 0
            
            weight_utilization = (self.total_weight / available_weight * 100) if available_weight > 0 else 0
            volume_utilization = (self.total_volume / available_volume * 100) if available_volume > 0 else 0
            
            capacity_info.append({
                "sequence": seq,
                "available_weight": available_weight,
                "available_volume": available_volume,
                "weight_utilization": weight_utilization,
                "volume_utilization": volume_utilization,
                "status": "Available" if weight_utilization < 100 and volume_utilization < 100 else "Full"
            })
        
        return capacity_info
    
    @frappe.whitelist()
    def calculate_cost_breakdown(self):
        """Calculate detailed cost breakdown for consolidation"""
        cost_breakdown = {
            "total_cost": 0,
            "cost_per_kg": 0,
            "charges": []
        }
        
        for charge in self.consolidation_charges:
            charge_info = {
                "type": charge.charge_type,
                "category": charge.charge_category,
                "basis": charge.revenue_calculation_method,
                "unit_rate": charge.unit_rate,
                "quantity": charge.quantity,
                "base_amount": charge.base_amount,
                "discount": charge.discount_amount,
                "surcharge": charge.surcharge_amount,
                "total": charge.total_amount
            }
            cost_breakdown["charges"].append(charge_info)
            cost_breakdown["total_cost"] += charge.total_amount
        
        if self.chargeable_weight > 0:
            cost_breakdown["cost_per_kg"] = cost_breakdown["total_cost"] / self.chargeable_weight
        
        return cost_breakdown
    
    @frappe.whitelist()
    def add_air_freight_job(self, air_freight_job):
        """Add an Air Shipment to the consolidation"""
        # Check if job is already in consolidation
        existing_package = frappe.db.exists("Air Consolidation Packages", {
            "air_freight_job": air_freight_job,
            "parent": self.name
        })
        
        if existing_package:
            frappe.throw(_("This Air Shipment is already included in this consolidation"))
        
        # Validate house type: only consolidation types can be added (not Standard House or Break Bulk)
        job = frappe.get_doc("Air Shipment", air_freight_job)
        allowed = ("Co-load Master", "Blind Co-load Master", "Co-load House", "Buyer's Consol Lead", "Shipper's Consol Lead")
        if job.house_type not in allowed:
            frappe.throw(_(
                "Air Shipment with House Type '{0}' cannot be added to consolidation. "
                "Only Co-load Master, Blind Co-load Master, Co-load House, Buyer's Consol Lead, or Shipper's Consol Lead are allowed."
            ).format(job.house_type or "Standard House"))
        
        # Validate origin and destination match consolidation header
        if self.origin_airport and job.origin_port != self.origin_airport:
            frappe.throw(_(
                "Air Shipment {0} origin port ({1}) does not match consolidation origin ({2})."
            ).format(air_freight_job, job.origin_port or "-", self.origin_airport))
        if self.destination_airport and job.destination_port != self.destination_airport:
            frappe.throw(_(
                "Air Shipment {0} destination port ({1}) does not match consolidation destination ({2})."
            ).format(air_freight_job, job.destination_port or "-", self.destination_airport))

        self._maybe_populate_routes_from_added_shipment(air_freight_job)

        # Add package to consolidation
        package = self.append("consolidation_packages", {})
        package.air_freight_job = air_freight_job
        
        # Get job details (job already fetched above for house_type validation)
        package.shipper = job.shipper
        package.consignee = job.consignee
        package.package_type = "Box"  # Default, can be updated
        package.package_count = job.packs or 1
        package.package_weight = getattr(job, "total_weight", None) or getattr(job, "weight", None) or 0
        package.package_volume = getattr(job, "total_volume", None) or getattr(job, "volume", None) or 0
        package.commodity = self._first_consolidation_commodity_from_air_shipment(job)
        package.description = getattr(job, "description", None) or ""
        package.contains_dangerous_goods = job.contains_dangerous_goods or 0
        
        self.save()
        return package
    
    @frappe.whitelist()
    def remove_air_freight_job(self, air_freight_job):
        """Remove an Air Shipment from the consolidation"""
        # Remove from consolidation packages
        packages_to_remove = []
        for package in self.consolidation_packages:
            if package.air_freight_job == air_freight_job:
                packages_to_remove.append(package)
        
        for package in packages_to_remove:
            self.remove(package)
        
        # Clear consolidation reference from the job
        frappe.db.set_value("Air Shipment", air_freight_job, {
            "consolidation_reference": None,
            "consolidation_status": None
        })
        
        self.save()
        return True
    
    @frappe.whitelist()
    def allocate_costs(self, allocation_method="weight"):
        """Set package cost_allocation % by weight, volume, or equal split per air shipment (aligned with Sea Consolidation)."""
        method = (allocation_method or "weight").lower()
        if method not in ("weight", "volume", "equal"):
            frappe.throw(_("Allocation method must be weight, volume, or equal"))

        basis_map = {"weight": "Weight", "volume": "Volume", "equal": "Equal"}
        self.package_allocation_basis = basis_map[method]

        pkgs = list(self.get("consolidation_packages") or [])
        if not pkgs:
            self.save()
            return True

        if method == "weight":
            tw = flt(self.total_weight) or 1.0
            for p in pkgs:
                w = flt(getattr(p, "package_weight", None) or 0)
                if w:
                    p.cost_allocation = (w / tw) * 100
                else:
                    p.cost_allocation = 0
        elif method == "volume":
            tv = flt(self.total_volume) or 1.0
            for p in pkgs:
                v = flt(getattr(p, "package_volume", None) or 0)
                if v:
                    p.cost_allocation = (v / tv) * 100
                else:
                    p.cost_allocation = 0
        else:
            from collections import Counter

            jobs = [getattr(p, "air_freight_job", None) for p in pkgs if getattr(p, "air_freight_job", None)]
            n_jobs = len(set(jobs)) or 1
            per_job_pct = 100.0 / float(n_jobs)
            counts = Counter(jobs)
            for p in pkgs:
                j = getattr(p, "air_freight_job", None)
                if not j:
                    p.cost_allocation = 0
                    continue
                cnt = counts[j] or 1
                p.cost_allocation = per_job_pct / float(cnt)

        self.save()
        return True
    
    def validate_dates(self):
        """Validate date fields"""
        # Validate departure date is before arrival date
        if self.departure_date and self.arrival_date:
            if self.departure_date >= self.arrival_date:
                frappe.throw(_("Departure date must be before arrival date"), 
                    title=_("Date Validation Error"))
        
        # Warn if consolidation date is in the future
        if self.consolidation_date:
            from frappe.utils import getdate, today
            if getdate(self.consolidation_date) > getdate(today()):
                frappe.msgprint(_("Consolidation date is in the future. Please verify this is correct."), 
                    indicator="orange", title=_("Date Warning"))
    
    def validate_accounts(self):
        """Validate accounting fields"""
        if not self.company:
            frappe.throw(_("Company is required"), title=_("Validation Error"))
        
        # Validate cost center belongs to company
        if self.cost_center:
            cost_center_company = frappe.get_cached_value("Cost Center", self.cost_center, "company")
            if cost_center_company and cost_center_company != self.company:
                frappe.throw(_("Cost Center {0} does not belong to Company {1}").format(
                    self.cost_center, self.company), title=_("Validation Error"))
        
        # Validate profit center belongs to company
        if self.profit_center:
            profit_center_company = frappe.get_cached_value("Profit Center", self.profit_center, "company")
            if profit_center_company and profit_center_company != self.company:
                frappe.throw(_("Profit Center {0} does not belong to Company {1}").format(
                    self.profit_center, self.company), title=_("Validation Error"))
        
        # Validate branch belongs to company
        if self.branch:
            branch_company = frappe.get_cached_value("Branch", self.branch, "company")
            if branch_company and branch_company != self.company:
                frappe.throw(_("Branch {0} does not belong to Company {1}").format(
                    self.branch, self.company), title=_("Validation Error"))
    
    def get_air_freight_settings(self):
        """Get Air Freight Settings for the company"""
        if not self.company:
            return None
        
        try:
            from logistics.air_freight.doctype.air_freight_settings.air_freight_settings import AirFreightSettings
            return AirFreightSettings.get_settings(self.company)
        except Exception as e:
            frappe.log_error(f"Error getting Air Freight Settings: {str(e)}", "Air Consolidation - Get Settings")
            return None
    
    def apply_settings_defaults(self):
        """Apply default values from Air Freight Settings"""
        if hasattr(self, '_settings_applied'):
            return
        
        settings = self.get_air_freight_settings()
        if not settings:
            return
        
        # Apply general settings
        if not self.branch and settings.default_branch:
            self.branch = settings.default_branch
        if not self.cost_center and settings.default_cost_center:
            self.cost_center = settings.default_cost_center
        if not self.profit_center and settings.default_profit_center:
            self.profit_center = settings.default_profit_center
        
        # Apply consolidation settings
        if not self.consolidation_type and settings.default_consolidation_type:
            self.consolidation_type = settings.default_consolidation_type
        
        # Mark as applied
        self._settings_applied = True
    
    def create_job_number_if_needed(self):
        """Create Job Number when document is first saved"""
        # Check settings for auto-create job costing
        settings = self.get_air_freight_settings()
        if settings and not settings.auto_create_job_costing:
            return
        
        # Only create if job_number is not set
        if not self.job_number:
            # Check if this is the first save (no existing Job Number)
            existing_job_ref = frappe.db.get_value("Job Number", {
                "job_type": "Air Consolidation",
                "job_no": self.name
            })
            
            if not existing_job_ref:
                # Create Job Number
                job_ref = frappe.new_doc("Job Number")
                job_ref.job_type = "Air Consolidation"
                job_ref.job_no = self.name
                job_ref.company = self.company
                job_ref.branch = self.branch
                job_ref.cost_center = self.cost_center
                job_ref.profit_center = self.profit_center
                # Leave recognition_date blank - will be filled in separate function
                # Use air consolidation's consolidation_date instead
                job_ref.job_open_date = self.consolidation_date
                job_ref.insert(ignore_permissions=True)
                
                # Set the job_number field
                self.job_number = job_ref.name
                
                frappe.msgprint(_("Job Number {0} created successfully").format(job_ref.name))


@frappe.whitelist()
def populate_routing_from_air_shipment(docname, air_shipment=None):
	"""API: copy routing legs from an Air Shipment onto the consolidation."""
	doc = frappe.get_doc("Air Consolidation", docname)
	return doc.populate_routing_from_air_shipment(air_shipment=air_shipment)


@frappe.whitelist()
def populate_routing_from_airports(docname):
	"""API: one Direct consolidation route from header airports."""
	doc = frappe.get_doc("Air Consolidation", docname)
	return doc.populate_routing_from_airports()
