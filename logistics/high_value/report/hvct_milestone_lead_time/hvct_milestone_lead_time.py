# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""HVCT Milestone Lead Time."""

from __future__ import unicode_literals

from logistics.control_tower.module_tower import lead_time_execute


def execute(filters=None):
	return lead_time_execute('high_value', filters)
