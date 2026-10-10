# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""SUCT Module Volumes."""

from __future__ import unicode_literals

from logistics.control_tower.module_tower import volumes_execute


def execute(filters=None):
	return volumes_execute('sustainability', filters)
