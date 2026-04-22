# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from frappe import _


def get_data():
	return [
		{
			"label": _("Cash Advance"),
			"items": [
				{
					"type": "doctype",
					"name": "Cash Advance Request",
					"label": _("Cash Advance Request"),
					"description": _("Employee cash advance requests"),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Cash Advance Liquidation",
					"label": _("Cash Advance Liquidation"),
					"description": _("Liquidate against a cash advance request"),
					"onboard": 0,
				},
				{
					"type": "doctype",
					"name": "Cash Advance Settings",
					"label": _("Cash Advance Settings"),
					"description": _("A/R Employee account for journal entries"),
					"onboard": 0,
				},
			],
		}
	]
