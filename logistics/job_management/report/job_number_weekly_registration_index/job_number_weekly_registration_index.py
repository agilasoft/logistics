# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt
from __future__ import unicode_literals

import json

from logistics.analytics_reports.management_reports import run_management_report

REF_DOCTYPE = 'Job Number'
HANDLER_ID = 'trend_weekly_count'
OPTIONS = json.loads('{}')


def execute(filters=None):
	return run_management_report(REF_DOCTYPE, HANDLER_ID, filters, OPTIONS)
