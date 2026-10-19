# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import json
import unittest

from logistics.desk.list_settings_payload import (
	ListSettingsPayloadError,
	sanitize_listview_payload,
	sanitize_removed_fields,
)

FIELDS = {"name", "status", "customer", "status_field"}


class TestListSettingsPayload(unittest.TestCase):
	def test_keeps_only_known_list_settings(self):
		payload = sanitize_listview_payload(
			{
				"name": "ToDo",
				"owner": "Administrator",
				"disable_count": "1",
				"show_tags": 0,
				"fields": [{"fieldname": "status", "label": "Status", "width": "120"}],
			},
			FIELDS,
		)
		self.assertEqual(payload["disable_count"], 1)
		self.assertEqual(payload["show_tags"], 0)
		self.assertNotIn("name", payload)
		self.assertNotIn("owner", payload)
		columns = json.loads(payload["fields"])
		self.assertEqual(columns, [{"fieldname": "status", "label": "Status", "width": 120}])

	def test_rejects_unknown_column(self):
		with self.assertRaises(ListSettingsPayloadError):
			sanitize_listview_payload(
				{"fields": [{"fieldname": "secret", "label": "Secret"}]},
				FIELDS,
			)

	def test_rejects_bad_checkbox(self):
		with self.assertRaises(ListSettingsPayloadError):
			sanitize_listview_payload({"allow_edit": "maybe"}, FIELDS)

	def test_removed_fields_must_belong_to_the_doctype(self):
		self.assertEqual(sanitize_removed_fields(["customer"], FIELDS), ["customer"])
		with self.assertRaises(ListSettingsPayloadError):
			sanitize_removed_fields(["secret"], FIELDS)
		with self.assertRaises(ListSettingsPayloadError):
			sanitize_removed_fields("customer", FIELDS)

	def test_status_column_keeps_its_type(self):
		payload = sanitize_listview_payload(
			{"fields": [{"fieldname": "status_field", "label": "Status", "type": "Status"}]},
			FIELDS,
		)
		self.assertEqual(
			json.loads(payload["fields"]),
			[{"fieldname": "status_field", "label": "Status", "type": "Status"}],
		)


if __name__ == "__main__":
	unittest.main()
