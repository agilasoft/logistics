# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt
from __future__ import unicode_literals

import json

from logistics.analytics_reports.management_reports import run_management_report

REF_DOCTYPE = 'Sales Quote'
HANDLER_ID = 'owner_workload'
OPTIONS = json.loads('{}')


def execute(filters=None):
	return run_management_report(REF_DOCTYPE, HANDLER_ID, filters, OPTIONS)
