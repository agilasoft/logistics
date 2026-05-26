# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Transport API package — delegates to logistics.transport.api module (api.py)
so driver mobile endpoints stay in one implementation file.
"""

import importlib.util
from pathlib import Path

_api_py = Path(__file__).resolve().parent.parent / "api.py"
_spec = importlib.util.spec_from_file_location("logistics.transport._api_py", _api_py)
_api_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_api_mod)

build_operations_from_template = _api_mod.build_operations_from_template
get_address_latlon = _api_mod.get_address_latlon
get_run_sheet_bundle = _api_mod.get_run_sheet_bundle
apply_leg_driver_updates = _api_mod.apply_leg_driver_updates
update_driver_location = _api_mod.update_driver_location
resolve_driver_for_user = _api_mod.resolve_driver_for_user
RUN_SHEET_BUNDLE_LEG_FIELDS = _api_mod.RUN_SHEET_BUNDLE_LEG_FIELDS
DRIVER_LEG_UPDATE_FIELDS = _api_mod.DRIVER_LEG_UPDATE_FIELDS
_enrich_leg_for_mobile = _api_mod._enrich_leg_for_mobile
