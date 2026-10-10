# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""SPCT Job Files Detail."""

from __future__ import unicode_literals

from logistics.control_tower.module_tower import job_files_execute


def execute(filters=None):
	return job_files_execute('special_projects', filters)
