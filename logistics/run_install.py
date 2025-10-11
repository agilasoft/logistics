#!/usr/bin/env python3

import frappe
from frappe import _

def run_install():
    """Run the install script"""
    from logistics.install import after_install
    after_install()

if __name__ == "__main__":
    run_install()
