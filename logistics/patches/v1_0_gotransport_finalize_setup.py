# Copyright (c) 2026 Agilasoft. All rights reserved.
"""Go Transport integration — ship the Custom Field + permissions + settings.

This patch is idempotent and covers four pieces of the Go Transport brief that
need to materialize on every existing site:

  1. Custom Field ``Transport Vehicle.gotransport_device`` (Data, 80, in list
     view, in standard filter) — replaces the earlier *native* field of the
     same name. The DB column is preserved across the swap (Frappe never
     drops columns on its own), so any data already pinned to vehicles
     survives.
  2. Property Setter that hoists ``gotransport_device`` to ``permlevel = 1``
     so we can grant write on this single field without giving the Driver
     role write on the whole DocType.
  3. ``Driver`` role DocPerm on Transport Vehicle ``permlevel = 1`` with
     read + write — enables the mobile app's *Pair this phone* flow that
     calls ``frappe.client.set_value`` on this field.
  4. Transport Settings defaults: ``telematics_poll_interval_min`` 0 → 1
     and ``default_telematics_provider`` set to the GoTransport-typed
     provider record (if exactly one exists and the current value is empty
     or any non-GoTransport provider — falls back to a safe no-op when the
     situation is ambiguous so a human can decide).
"""

from __future__ import annotations

import frappe


GOTRANSPORT_FIELD = "gotransport_device"
GOTRANSPORT_DT = "Transport Vehicle"
DRIVER_ROLE = "Driver"
GOTRANSPORT_FIELD_PERMLEVEL = 1


def execute():
	_ensure_custom_field()
	_ensure_permlevel_property_setter()
	_ensure_driver_field_permission()
	_ensure_transport_settings_defaults()
	frappe.db.commit()


# --------------------------------------------------------------------- helpers


def _ensure_custom_field():
	"""Create / update the gotransport_device Custom Field idempotently."""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	create_custom_field(
		GOTRANSPORT_DT,
		{
			"fieldname": GOTRANSPORT_FIELD,
			"label": "Go Transport Device",
			"fieldtype": "Data",
			"length": 80,
			"in_list_view": 1,
			"in_standard_filter": 1,
			"insert_after": "telematics_external_id",
			"permlevel": GOTRANSPORT_FIELD_PERMLEVEL,
			"description": (
				"Stable device id of the Go Transport phone reporting for "
				"this vehicle. Set automatically when the driver taps "
				"<b>Pair this phone</b> in the app (writes "
				"<code>GT-v1-&lt;uuid&gt;</code> via "
				"<code>frappe.client.set_value</code>)."
			),
		},
		ignore_validate=True,
	)

	# Keep permlevel in sync when the field already existed before this patch.
	cf_name = frappe.db.get_value(
		"Custom Field", {"dt": GOTRANSPORT_DT, "fieldname": GOTRANSPORT_FIELD}, "name"
	)
	if cf_name:
		current = frappe.db.get_value("Custom Field", cf_name, "permlevel")
		if int(current or 0) != GOTRANSPORT_FIELD_PERMLEVEL:
			frappe.db.set_value(
				"Custom Field", cf_name, "permlevel", GOTRANSPORT_FIELD_PERMLEVEL,
				update_modified=False,
			)


def _ensure_permlevel_property_setter():
	"""
	Belt-and-braces: even if the field was first introduced *natively* on
	an older Logistics build, a Property Setter pins its permlevel to 1.
	Idempotent.
	"""
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	make_property_setter(
		doctype=GOTRANSPORT_DT,
		fieldname=GOTRANSPORT_FIELD,
		property="permlevel",
		value=GOTRANSPORT_FIELD_PERMLEVEL,
		property_type="Int",
		for_doctype=False,
		validate_fields_for_doctype=False,
	)


def _ensure_driver_field_permission():
	"""Grant the Driver role read+write on permlevel 1 of Transport Vehicle."""
	if not frappe.db.exists("Role", DRIVER_ROLE):
		return

	existing = frappe.db.exists(
		"Custom DocPerm",
		{"parent": GOTRANSPORT_DT, "role": DRIVER_ROLE, "permlevel": GOTRANSPORT_FIELD_PERMLEVEL},
	)
	if existing:
		frappe.db.set_value("Custom DocPerm", existing, {
			"read": 1, "write": 1,
		}, update_modified=False)
		return

	# Make sure the permlevel-0 read row exists too — Frappe's permission
	# engine requires read at permlevel 0 before higher permlevels resolve.
	if not frappe.db.exists(
		"Custom DocPerm",
		{"parent": GOTRANSPORT_DT, "role": DRIVER_ROLE, "permlevel": 0},
	):
		frappe.get_doc({
			"doctype": "Custom DocPerm",
			"parent": GOTRANSPORT_DT,
			"parenttype": "DocType",
			"parentfield": "permissions",
			"role": DRIVER_ROLE,
			"permlevel": 0,
			"read": 1,
		}).insert(ignore_permissions=True)

	frappe.get_doc({
		"doctype": "Custom DocPerm",
		"parent": GOTRANSPORT_DT,
		"parenttype": "DocType",
		"parentfield": "permissions",
		"role": DRIVER_ROLE,
		"permlevel": GOTRANSPORT_FIELD_PERMLEVEL,
		"read": 1,
		"write": 1,
	}).insert(ignore_permissions=True)
	frappe.clear_cache(doctype=GOTRANSPORT_DT)


def _ensure_transport_settings_defaults():
	"""
	Settings normalization:
	  - telematics_poll_interval_min: 0/NULL -> 1 (brief §5; 0 is undefined).
	  - default_telematics_provider: set to the single enabled GOTRANSPORT
	    provider when no provider is currently set, OR when the current
	    value is a Remora/etc. record AND there is exactly one enabled
	    GoTransport provider. We log and skip when ambiguous to avoid
	    flipping a production-critical setting silently.
	"""
	if not frappe.db.exists("DocType", "Transport Settings"):
		return

	current_interval = frappe.db.get_single_value("Transport Settings", "telematics_poll_interval_min")
	if not current_interval or int(current_interval) <= 0:
		frappe.db.set_single_value("Transport Settings", "telematics_poll_interval_min", 1)
		frappe.logger().info("v1_0_gotransport_finalize_setup: telematics_poll_interval_min -> 1")

	current_provider = frappe.db.get_single_value("Transport Settings", "default_telematics_provider")
	gotransport_providers = frappe.get_all(
		"Telematics Provider",
		filters={"provider_type": "GOTRANSPORT", "enabled": 1},
		pluck="name",
	)
	if len(gotransport_providers) == 1:
		new_provider = gotransport_providers[0]
		if not current_provider or current_provider != new_provider:
			frappe.db.set_single_value(
				"Transport Settings", "default_telematics_provider", new_provider,
			)
			frappe.logger().info(
				"v1_0_gotransport_finalize_setup: default_telematics_provider %r -> %r",
				current_provider, new_provider,
			)
	elif len(gotransport_providers) > 1:
		frappe.logger().warning(
			"v1_0_gotransport_finalize_setup: multiple enabled GOTRANSPORT "
			"providers (%s); leaving default_telematics_provider untouched.",
			gotransport_providers,
		)
