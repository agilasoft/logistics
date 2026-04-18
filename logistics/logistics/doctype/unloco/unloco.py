"""
UNLOCO DocType
Auto-populate UNLOCO details when creating new records
"""

import json

import frappe
from frappe import _
from frappe.model.document import Document


class UNLOCO(Document):
    def validate(self):
        """Validate UNLOCO document"""
        # Validate UNLOCO code format
        if self.unlocode and len(self.unlocode) != 5:
            frappe.throw(_("UNLOCO code must be exactly 5 characters long"))

        # Auto-populate details if enabled
        if self.auto_populate and self.unlocode:
            self.populate_unlocode_details()

        if self.status:
            field = frappe.get_meta("UNLOCO").get_field("status")
            if field and field.options:
                allowed = {line.strip() for line in field.options.split("\n") if line.strip()}
                if self.status.strip() not in allowed:
                    frappe.throw(
                        _("Status must be one of the UN/LOCODE values defined for this DocType."),
                        title=_("Invalid Status"),
                    )

    def populate_unlocode_details(self):
        """Populate UNLOCO details from database or external sources"""
        try:
            from logistics.air_freight.utils.unlocode_utils import (
                populate_unlocode_details,
                unwrap_populate_result,
            )

            result = populate_unlocode_details(self.unlocode)
            details = unwrap_populate_result(result)

            if details:
                for field_name, field_value in details.items():
                    if hasattr(self, field_name) and field_value is not None:
                        setattr(self, field_name, field_value)

                self.last_updated = frappe.utils.now()

        except Exception as e:
            frappe.log_error(f"UNLOCO details population error: {str(e)}")

    def before_save(self):
        """Auto-populate details before saving"""
        if self.auto_populate and self.unlocode:
            self.populate_unlocode_details()


def import_unloco_codes_impl(codes):
    """
    Create UNLOCO documents for a list of normalized 5-character codes (internal / background job).
    Skips codes that already exist. Each new doc uses auto_populate.
    """
    created = []
    skipped = []
    errors = []

    for code in codes:
        if len(code) != 5:
            errors.append({"code": code or "", "error": _("UNLOCO code must be exactly 5 characters")})
            continue

        if frappe.db.exists("UNLOCO", code):
            skipped.append(code)
            continue

        try:
            doc = frappe.get_doc(
                {
                    "doctype": "UNLOCO",
                    "unlocode": code,
                    "auto_populate": 1,
                }
            )
            doc.insert()
            created.append(code)
        except Exception as e:
            errors.append({"code": code, "error": str(e)})

    return {"created": created, "skipped": skipped, "errors": errors}


@frappe.whitelist()
def import_unloco_codes(codes):
    """
    Create multiple UNLOCO documents from codes (strings or {unlocode} rows).
    Each new document uses auto_populate so validate/before_save fill details (DataHub / samples / inference).
    """
    if not frappe.has_permission("UNLOCO", "create"):
        frappe.throw(_("Not permitted to create UNLOCO"))

    if isinstance(codes, str):
        codes = json.loads(codes)

    if not codes or not isinstance(codes, list):
        frappe.throw(_("Provide a non-empty list of UNLOCO codes"))

    if len(codes) > 500:
        frappe.throw(_("Maximum 500 codes per request. Use Data Import for larger batches."))

    normalized = []
    errors = []

    for item in codes:
        if isinstance(item, str):
            code = item.strip().upper()
        else:
            code = (item.get("unlocode") or "").strip().upper()

        if len(code) != 5:
            errors.append({"code": code or "", "error": _("UNLOCO code must be exactly 5 characters")})
            continue

        normalized.append(code)

    result = import_unloco_codes_impl(normalized)
    result["errors"] = errors + result["errors"]
    return result


@frappe.whitelist()
def start_get_all_unloco():
    """
    Queue a long worker job to create UNLOCO for every code in the cached DataHub code-list.
    Existing documents are skipped. Requires System Manager and UNLOCO create permission.
    """
    frappe.only_for("System Manager")
    if not frappe.has_permission("UNLOCO", "create"):
        frappe.throw(_("Not permitted to create UNLOCO"))

    from logistics.air_freight.utils.datahub_unlocode import ensure_datahub_un_locode_files, is_datahub_un_locode_enabled

    if not is_datahub_un_locode_enabled():
        frappe.throw(_("DataHub UN/LOCODE is disabled for this site (use_datahub_un_locode)."))

    if not ensure_datahub_un_locode_files():
        frappe.throw(
            _("Could not download or read the UN/LOCODE codelist from DataHub. Check connectivity and Error Log."),
            title=_("DataHub UN/LOCODE"),
        )

    frappe.enqueue(
        "logistics.logistics.doctype.unloco.unloco.run_get_all_unloco_job",
        queue="long",
        timeout=4 * 60 * 60,
        job_name="unloco_get_all_from_datahub",
        enqueue_after_commit=True,
    )

    return {"queued": True}


def run_get_all_unloco_job():
    """Background: stream codes from cached code-list and insert in batches."""
    from logistics.air_freight.utils.datahub_unlocode import iter_unlocode_codes_from_codelist_cache

    batch_size = 200
    batch = []
    try:
        for code in iter_unlocode_codes_from_codelist_cache():
            batch.append(code)
            if len(batch) >= batch_size:
                import_unloco_codes_impl(batch)
                frappe.db.commit()
                batch = []
        if batch:
            import_unloco_codes_impl(batch)
            frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "UNLOCO Get All from DataHub job")
        raise
