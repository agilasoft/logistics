# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt
from __future__ import unicode_literals

import json

from logistics.analytics_reports.management_reports import run_management_report

REF_DOCTYPE = 'Transport Job'
HANDLER_ID = 'pipeline_mix'
OPTIONS = json.loads('{"field":"dg_compliance_status"}')


def execute(filters=None):
	return run_management_report(REF_DOCTYPE, HANDLER_ID, filters, OPTIONS)
