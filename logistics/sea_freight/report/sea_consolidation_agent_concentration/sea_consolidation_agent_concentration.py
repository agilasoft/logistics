# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt
from __future__ import unicode_literals

import json

from logistics.analytics_reports.management_reports import run_management_report

REF_DOCTYPE = 'Sea Consolidation'
HANDLER_ID = 'top_value'
OPTIONS = json.loads('{"field":"consolidation_agent","limit":15}')


def execute(filters=None):
	return run_management_report(REF_DOCTYPE, HANDLER_ID, filters, OPTIONS)
