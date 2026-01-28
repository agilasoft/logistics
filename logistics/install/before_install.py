# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _


def before_install():
    """Run before installation of the logistics app
    
    Note: UOMs are user-defined and should be created manually in the UOM master.
    Users must configure default UOMs in Transport Capacity Settings after installation.
    """
    # UOMs are user-defined - no automatic creation
    # Users must create UOMs in the UOM master and configure them in Transport Capacity Settings
    pass


