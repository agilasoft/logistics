import time, frappe
from .ingest import run_ingest

CACHE_KEY = "transport:telematics:last_run_ts"

def _poll_minutes() -> int:
    try:
        m = int(frappe.db.get_single_value("Transport Settings","telematics_poll_interval_min") or 5)
        return max(1, min(m, 60))
    except Exception:
        return 5

def tick():
    cache = frappe.cache()
    last_ts = cache.get_value(CACHE_KEY)
    now_ts = int(time.time())
    if last_ts and (now_ts - int(last_ts)) < (_poll_minutes() * 60):
        return
    try:
        run_ingest()
    finally:
        cache.set_value(CACHE_KEY, now_ts)
