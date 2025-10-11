import frappe

def execute():
    # Ensure doctypes are loaded
    frappe.reload_doc("transport", "doctype", "telematics_position")
    frappe.reload_doc("transport", "doctype", "telematics_event")
    frappe.reload_doc("transport", "doctype", "telematics_temperature")
    frappe.reload_doc("transport", "doctype", "telematics_can_snapshot")

    # --- Telematics Position ---
    _add_index("Telematics Position", ["vehicle", "ts"], "idx_vehicle_ts")
    _add_index("Telematics Position", ["ts"], "idx_ts")
    # optional: coarse geo filter per vehicle (btree over floats)
    _add_index("Telematics Position", ["vehicle", "lat", "lon"], "idx_vehicle_lat_lon")

    # --- Telematics Event ---
    _add_index("Telematics Event", ["vehicle", "ts"], "idx_vehicle_ts")
    _add_index("Telematics Event", ["ts"], "idx_ts")

    # --- Telematics Temperature ---
    _add_index("Telematics Temperature", ["vehicle", "ts"], "idx_vehicle_ts")
    _add_index("Telematics Temperature", ["ts"], "idx_ts")

    # --- Telematics CAN Snapshot ---
    _add_index("Telematics CAN Snapshot", ["vehicle", "ts"], "idx_vehicle_ts")
    _add_index("Telematics CAN Snapshot", ["ts"], "idx_ts")


def _add_index(doctype: str, fields: list[str], index_name: str):
    """
    Adds an index if it doesn't already exist.
    """
    table = f"tab{doctype}"
    cols = ", ".join(f"`{f}`" for f in fields)
    # check existing
    exists = frappe.db.sql(
        """
        SELECT 1 FROM INFORMATION_SCHEMA.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND INDEX_NAME = %s
        """,
        (table, index_name),
    )
    if exists:
        return
    frappe.db.sql(f"ALTER TABLE `{table}` ADD INDEX `{index_name}` ({cols})")
