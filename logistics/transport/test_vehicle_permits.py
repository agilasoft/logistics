# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Vehicle permit eligibility, advance warnings, and dispatch blocking."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from logistics.transport.doctype.transport_job.transport_job import action_create_run_sheet
from logistics.transport.doctype.transport_plan.transport_plan import _find_candidate_vehicle
from logistics.transport.vehicle_permits import (
	STATUS_EXPIRED,
	STATUS_EXPIRING,
	advance_warning_days,
	banner_fingerprint,
	classify_required_permit,
	expiring_soon_sentence,
	format_expiry_date,
	get_open_permit_issues,
	get_permit_issues,
	get_vehicle_permit_banners,
	notification_subject,
	notify_vehicle_permit_alerts,
	route_is_transport,
	transport_vehicle_query,
)


class IntegrationTestVehiclePermits(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		self.suffix = frappe.generate_hash(length=6)
		self.company = frappe.db.get_value("Company", {}, "name") or self._make_company()
		self.vehicle_type = self._make_vehicle_type()
		self.permit_type = self._make_permit_type()
		self._settings_before = {
			"enforce_vehicle_permit_validation": frappe.db.get_single_value(
				"Transport Settings", "enforce_vehicle_permit_validation"
			),
			"permit_expiry_advance_warning": frappe.db.get_single_value(
				"Transport Settings", "permit_expiry_advance_warning"
			),
			"permit_notify_role": frappe.db.get_single_value("Transport Settings", "permit_notify_role"),
			"enable_constraint_system": frappe.db.get_single_value(
				"Transport Settings", "enable_constraint_system"
			),
		}

	def tearDown(self):
		for field, value in self._settings_before.items():
			frappe.db.set_single_value("Transport Settings", field, value)
		super().tearDown()

	def test_classify_expired_on_the_expiration_date_and_expiring_before_it(self):
		as_of = today()
		expired = classify_required_permit(as_of, 7, as_of)
		self.assertEqual(expired, (STATUS_EXPIRED, 0))
		tomorrow = add_days(as_of, 1)
		expiring = classify_required_permit(tomorrow, 1, as_of)
		self.assertEqual(expiring, (STATUS_EXPIRING, 1))
		self.assertIsNone(classify_required_permit(add_days(as_of, 2), 1, as_of))
		self.assertIsNone(classify_required_permit(None, 7, as_of))

	def test_enforcement_off_allows_expired_vehicle_on_run_sheet(self):
		self._configure(enabled=0, days=1)
		vehicle = self._make_vehicle("OFF1", add_days(today(), -1), required=1)
		run_sheet = self._run_sheet(vehicle)
		run_sheet.insert(ignore_permissions=True)
		self.assertTrue(run_sheet.name)

	def test_enforcement_blocks_expired_permit_and_allows_it_after_renewal(self):
		self._configure(enabled=1, days=1)
		vehicle = self._make_vehicle("EXP1", add_days(today(), -3), required=1)
		run_sheet = self._run_sheet(vehicle)
		with self.assertRaises(frappe.ValidationError) as ctx:
			run_sheet.insert(ignore_permissions=True)
		self.assertIn("LTFRB Permit", str(ctx.exception))
		self.assertIn("not eligible for dispatch", str(ctx.exception).lower())

		doc = frappe.get_doc("Transport Vehicle", vehicle)
		doc.permits[0].valid_until = add_days(today(), 10)
		doc.save(ignore_permissions=True)
		self.assertEqual(get_permit_issues(vehicle), [])
		renewed = self._run_sheet(vehicle)
		renewed.insert(ignore_permissions=True)
		self.assertTrue(renewed.name)

	def test_expiring_soon_still_allows_dispatch(self):
		self._configure(enabled=1, days=3)
		vehicle = self._make_vehicle("SOON", add_days(today(), 2), required=1)
		issues = get_permit_issues(vehicle)
		self.assertEqual(len(issues), 1)
		self.assertEqual(issues[0]["status"], STATUS_EXPIRING)
		self.assertEqual(issues[0]["remaining_days"], 2)
		self.assertIn("in 2 days", expiring_soon_sentence(issues[0]))
		self.assertIn(format_expiry_date(issues[0]["valid_until"]), expiring_soon_sentence(issues[0]))
		self.assertIn("LTFRB Permit", expiring_soon_sentence(issues[0]))
		run_sheet = self._run_sheet(vehicle)
		run_sheet.insert(ignore_permissions=True)
		self.assertTrue(run_sheet.name)

	def test_tomorrow_sentence_and_expiration_date_is_expired(self):
		self._configure(enabled=1, days=1)
		soon = self._make_vehicle("TMRW", add_days(today(), 1), required=1)
		issues = get_permit_issues(soon)
		self.assertEqual(issues[0]["remaining_days"], 1)
		sentence = expiring_soon_sentence(issues[0])
		self.assertIn("tomorrow", sentence)
		self.assertIn(format_expiry_date(add_days(today(), 1)), sentence)

		due = self._make_vehicle("TODAY", today(), required=1)
		due_issues = get_permit_issues(due)
		self.assertEqual(due_issues[0]["status"], STATUS_EXPIRED)
		self.assertEqual(due_issues[0]["remaining_days"], 0)
		with self.assertRaises(frappe.ValidationError):
			self._run_sheet(due).insert(ignore_permissions=True)

	def test_optional_expired_permit_does_not_block_or_warn(self):
		self._configure(enabled=1, days=7)
		vehicle = self._make_vehicle("OPT1", add_days(today(), -2), required=0)
		self.assertEqual(get_permit_issues(vehicle), [])
		self._run_sheet(vehicle).insert(ignore_permissions=True)

	def test_zero_warning_days_skips_advance_status(self):
		self._configure(enabled=1, days=0)
		self.assertEqual(advance_warning_days(), 0)
		vehicle = self._make_vehicle("ZERO", add_days(today(), 1), required=1)
		self.assertEqual(get_permit_issues(vehicle), [])

	def test_unchanged_open_run_sheet_can_be_saved_but_dispatch_status_is_blocked(self):
		self._configure(enabled=0, days=1)
		vehicle = self._make_vehicle("OPEN", add_days(today(), -1), required=1)
		run_sheet = self._run_sheet(vehicle)
		run_sheet.insert(ignore_permissions=True)

		self._configure(enabled=1, days=1)
		run_sheet.reload()
		run_sheet.save(ignore_permissions=True)

		run_sheet.status = "Dispatched"
		with self.assertRaises(frappe.ValidationError):
			run_sheet.save(ignore_permissions=True)

		closed = frappe.new_doc("Run Sheet")
		closed.vehicle = vehicle
		closed.status = "Completed"
		closed._doc_before_save = frappe._dict(vehicle=vehicle, status="Completed")
		self.assertFalse(closed._vehicle_permit_check_applies())
		closed.status = "Dispatched"
		self.assertTrue(closed._vehicle_permit_check_applies())

	def test_link_query_hides_expired_and_keeps_expiring(self):
		self._configure(enabled=1, days=7)
		expired = self._make_vehicle("HIDE", add_days(today(), -1), required=1)
		expiring = self._make_vehicle("SHOW", add_days(today(), 3), required=1)
		names = self._query_names()
		self.assertNotIn(expired, names)
		self.assertIn(expiring, names)

		self._configure(enabled=0, days=7)
		names = self._query_names()
		self.assertIn(expired, names)
		self.assertIn(expiring, names)

	def test_planner_skips_only_expired_vehicles(self):
		self._configure(enabled=1, days=1)
		frappe.db.set_single_value("Transport Settings", "enable_constraint_system", 0)
		valid = self._make_vehicle("PLANOK", add_days(today(), 20), required=1)
		expired = self._make_vehicle("PLANNO", add_days(today(), -1), required=1)
		frappe.db.set_value("Transport Vehicle", valid, "modified", "2000-01-01 00:00:00", update_modified=False)
		frappe.db.set_value("Transport Vehicle", expired, "modified", "2099-01-01 00:00:00", update_modified=False)
		debug = []
		chosen = _find_candidate_vehicle(
			{"vehicle_type": self.vehicle_type, "weight": 0, "volume": 0, "pallets": 0},
			debug,
		)
		self.assertEqual(chosen["name"], valid)
		self.assertTrue(any("LTFRB Permit" in line and expired in line for line in debug))

	def test_create_run_sheet_from_job_rejects_expired_vehicle(self):
		self._configure(enabled=1, days=1)
		vehicle = self._make_vehicle("JOB1", today(), required=1)
		job = frappe.new_doc("Transport Job")
		job.flags.ignore_mandatory = True
		job.flags.ignore_validate = True
		job.flags.ignore_links = True
		job.insert(ignore_permissions=True, ignore_mandatory=True, ignore_links=True)
		frappe.db.set_value("Transport Job", job.name, "docstatus", 1, update_modified=False)
		with self.assertRaises(frappe.ValidationError) as ctx:
			action_create_run_sheet(job.name, vehicle=vehicle)
		self.assertIn("LTFRB Permit", str(ctx.exception))

	def test_notifications_include_status_and_do_not_repeat(self):
		self._configure(enabled=1, days=1, role="Transport Manager")
		user = self._make_user()
		soon = self._make_vehicle("NTFY", add_days(today(), 1), required=1, plate=f"ABC-{self.suffix}")
		expired = self._make_vehicle("NTFX", add_days(today(), -1), required=1, plate=f"XYZ-{self.suffix}")
		notify_vehicle_permit_alerts()
		notify_vehicle_permit_alerts()

		soon_subjects = self._subjects(soon, user)
		expired_subjects = self._subjects(expired, user)
		self.assertEqual(len(soon_subjects), 1)
		self.assertEqual(len(expired_subjects), 1)
		soon_subject = soon_subjects[0]
		self.assertIn(f"ABC-{self.suffix}", soon_subject)
		self.assertIn("LTFRB Permit", soon_subject)
		self.assertIn("Expiring Soon", soon_subject)
		self.assertIn("tomorrow", soon_subject)
		self.assertIn(format_expiry_date(add_days(today(), 1)), soon_subject)
		expired_subject = expired_subjects[0]
		self.assertIn(f"XYZ-{self.suffix}", expired_subject)
		self.assertIn("LTFRB Permit", expired_subject)
		self.assertIn("Expired", expired_subject)
		self.assertIn(format_expiry_date(add_days(today(), -1)), expired_subject)
		self.assertEqual(notification_subject(get_permit_issues(soon)[0]), soon_subject)

	def test_banner_changes_from_expiring_to_expired_and_fingerprint_tracks_new_expirations(self):
		self._configure(enabled=1, days=1)
		vehicle = self._make_vehicle("BNR1", add_days(today(), 1), required=1, plate=f"ABC-{self.suffix}")
		payload = get_vehicle_permit_banners("doctype", "Run Sheet")
		self.assertEqual(payload["applicable"], 1)
		self.assertEqual(payload["enabled"], 1)
		self.assertIsNone(payload["expired"])
		self.assertIn("Permit Expiring Soon", payload["expiring"]["title"])
		self.assertIn(f"ABC-{self.suffix}", payload["expiring"]["body"])
		self.assertIn("tomorrow", payload["expiring"]["body"])
		first_fingerprint = payload["expiring"]["fingerprint"]

		doc = frappe.get_doc("Transport Vehicle", vehicle)
		doc.permits[0].valid_until = today()
		doc.save(ignore_permissions=True)
		self.assertEqual(get_permit_issues(vehicle)[0]["status"], STATUS_EXPIRED)
		payload = get_vehicle_permit_banners("doctype", "Run Sheet")
		self.assertIsNotNone(payload["expired"])
		self.assertIn("cannot be dispatched", payload["expired"]["body"])
		self.assertNotEqual(payload["expired"]["fingerprint"], first_fingerprint)
		self.assertNotIn(vehicle, {
			issue["vehicle"] for issue in get_open_permit_issues() if issue["status"] == STATUS_EXPIRING
		})

		self._make_vehicle("BNR2", add_days(today(), -1), required=1)
		second = banner_fingerprint(
			[issue for issue in get_open_permit_issues() if issue["status"] == STATUS_EXPIRED]
		)
		self.assertNotEqual(second, payload["expired"]["fingerprint"])

		self.assertTrue(route_is_transport("doctype", "Run Sheet"))
		self.assertFalse(route_is_transport("doctype", "Customer"))
		self.assertEqual(get_vehicle_permit_banners("doctype", "Customer")["applicable"], 0)

	def _configure(self, enabled, days, role=None):
		frappe.db.set_single_value("Transport Settings", "enforce_vehicle_permit_validation", enabled)
		frappe.db.set_single_value("Transport Settings", "permit_expiry_advance_warning", days)
		if role is not None:
			if not frappe.db.exists("Role", role):
				frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(
					ignore_permissions=True
				)
			frappe.db.set_single_value("Transport Settings", "permit_notify_role", role)

	def _make_company(self):
		company = frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": f"Permit Co {self.suffix}",
				"abbr": self.suffix[:5].upper(),
				"default_currency": "USD",
				"country": "United States",
			}
		)
		company.insert(ignore_permissions=True)
		return company.name

	def _make_vehicle_type(self):
		code = f"VPT{self.suffix}"
		frappe.get_doc(
			{
				"doctype": "Vehicle Type",
				"code": code,
				"description": code,
				"is_active": 1,
			}
		).insert(ignore_permissions=True)
		return code

	def _make_permit_type(self):
		code = f"LTFRB{self.suffix}"
		frappe.get_doc(
			{
				"doctype": "License and Permit Type",
				"code": code,
				"description": "LTFRB Permit",
				"transport": 1,
			}
		).insert(ignore_permissions=True)
		return code

	def _make_vehicle(self, code_suffix, valid_until, required, plate=None):
		code = f"VH{self.suffix}{code_suffix}"
		doc = frappe.get_doc(
			{
				"doctype": "Transport Vehicle",
				"code": code,
				"vehicle_name": f"Vehicle {code_suffix}",
				"license_plate_number": plate or code,
				"vehicle_type": self.vehicle_type,
				"company_owned": 1,
				"company": self.company,
				"is_active": 1,
				"avg_speed": 40,
				"permits": [
					{
						"permit_type": self.permit_type,
						"valid_until": valid_until,
						"required": required,
					}
				],
			}
		)
		doc.insert(ignore_permissions=True)
		return doc.name

	def _run_sheet(self, vehicle):
		run_sheet = frappe.new_doc("Run Sheet")
		run_sheet.vehicle_type = self.vehicle_type
		run_sheet.vehicle = vehicle
		run_sheet.run_date = today()
		run_sheet.status = "Draft"
		return run_sheet

	def _query_names(self):
		rows = transport_vehicle_query(
			"Transport Vehicle",
			self.suffix,
			"name",
			0,
			50,
			{"vehicle_type": self.vehicle_type, "is_active": 1},
		)
		return [row[0] for row in rows]

	def _make_user(self):
		email = f"permit.{self.suffix}@example.com"
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "Permit",
				"send_welcome_email": 0,
				"user_type": "System User",
				"roles": [{"role": "Transport Manager"}],
			}
		).insert(ignore_permissions=True)
		return email

	def _subjects(self, vehicle, user):
		return frappe.get_all(
			"Notification Log",
			filters={"document_type": "Transport Vehicle", "document_name": vehicle, "for_user": user},
			pluck="subject",
		)
