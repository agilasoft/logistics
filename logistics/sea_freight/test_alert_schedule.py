# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import pathlib
import unittest
from types import SimpleNamespace

from logistics.sea_freight.alert_schedule import (
	DAILY_SEA_ALERT_TASKS,
	HOURLY_SEA_ALERT_TASKS,
	alerts_enabled,
	log_check_completed,
)


class TestSeaAlertGates(unittest.TestCase):
	def test_missing_settings_leave_alerts_on(self):
		self.assertTrue(alerts_enabled(None, "enable_delay_alerts"))
		self.assertTrue(alerts_enabled(None, "enable_penalty_alerts"))

	def test_explicit_off_disables_alerts(self):
		settings = SimpleNamespace(enable_delay_alerts=0, enable_penalty_alerts=0)
		self.assertFalse(alerts_enabled(settings, "enable_delay_alerts"))
		self.assertFalse(alerts_enabled(settings, "enable_penalty_alerts"))

	def test_explicit_on_enables_alerts(self):
		settings = {"enable_delay_alerts": 1, "enable_penalty_alerts": 1}
		self.assertTrue(alerts_enabled(settings, "enable_delay_alerts"))
		self.assertTrue(alerts_enabled(settings, "enable_penalty_alerts"))

	def test_scheduler_registers_hourly_and_daily_tasks(self):
		self.assertEqual(
			HOURLY_SEA_ALERT_TASKS,
			(
				"logistics.sea_freight.tasks.check_sea_shipment_delays",
				"logistics.sea_freight.tasks.check_sea_shipment_penalties",
				"logistics.sea_freight.tasks.check_container_penalties",
			),
		)
		self.assertEqual(
			DAILY_SEA_ALERT_TASKS,
			("logistics.sea_freight.tasks.check_impending_penalties",),
		)
		hooks = pathlib.Path(__file__).resolve().parents[1] / "hooks.py"
		text = hooks.read_text(encoding="utf-8")
		hourly_at = text.index('"hourly"')
		daily_at = text.index('"daily"')
		hourly_block = text[hourly_at:daily_at]
		daily_block = text[daily_at:text.index("# Testing")]
		self.assertIn("*HOURLY_SEA_ALERT_TASKS", hourly_block)
		self.assertNotIn("*HOURLY_SEA_ALERT_TASKS", daily_block)
		self.assertIn("*DAILY_SEA_ALERT_TASKS", daily_block)
		self.assertNotIn("*DAILY_SEA_ALERT_TASKS", hourly_block)


class TestSeaAlertCompletionLog(unittest.TestCase):
	def test_completed_check_uses_the_logger(self):
		logged = []

		class Logger:
			def info(self, *args, **kwargs):
				logged.append(("info", args, kwargs))

			def error(self, *args, **kwargs):
				logged.append(("error", args, kwargs))

		log_check_completed(Logger(), "Sea Shipment Delay Check Completed", "Checked 2 shipments, 1 alerts sent")
		self.assertEqual(logged[0][0], "info")
		self.assertEqual(logged[0][1][1], "Sea Shipment Delay Check Completed")
