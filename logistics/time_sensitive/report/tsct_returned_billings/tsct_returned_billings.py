# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""TSCT Returned Billings."""

from __future__ import unicode_literals

from logistics.control_tower.module_tower import returned_execute


def execute(filters=None):
	return returned_execute('time_sensitive', filters)
