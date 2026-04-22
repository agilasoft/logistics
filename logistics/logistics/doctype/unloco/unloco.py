"""
UNLOCO DocType
Auto-populate UNLOCO details when creating new records
"""

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class UNLOCO(Document):
    def _consume_unloco_autopopulate_skip(self) -> bool:
        """
        After ``populate_unlocode_details(refresh_external=True)``, ``save()`` runs
        ``validate`` / ``before_save``, each of which would call ``get_unlocode_data``
        against the database row that is not updated yet — wiping merged fields
        (notably Function-derived checkboxes). Skip those two rounds when requested.
        """
        n = getattr(self, "_unloco_skip_autopopulate_rounds", 0) or 0
        if n <= 0:
            return False
        self._unloco_skip_autopopulate_rounds = n - 1
        return True

    def _should_run_autopopulate_on_save(self) -> bool:
        """
        Re-fetching on every save would call ``get_unlocode_data`` against the **database** row,
        which is still the pre-save snapshot, and would overwrite checkbox (and other) edits the
        user just made on the form. Only re-run when the code changes, on first insert, or when
        Auto-Populate is turned on for an existing row.
        """
        if self.is_new():
            return True
        previous = self.get_doc_before_save()
        if not previous:
            return False
        if (previous.get("unlocode") or "").strip().upper() != (self.unlocode or "").strip().upper():
            return True
        if cint(self.auto_populate) and not cint(previous.get("auto_populate")):
            return True
        return False

    def validate(self):
        """Validate UNLOCO document"""
        # Validate UNLOCO code format
        if self.unlocode and len(self.unlocode) != 5:
            frappe.throw(_("UNLOCO code must be exactly 5 characters long"))

        if self.status:
            field = frappe.get_meta("UNLOCO").get_field("status")
            if field and field.options:
                allowed = {line.strip() for line in field.options.split("\n") if line.strip()}
                if self.status.strip() not in allowed:
                    frappe.throw(
                        _("Status must be one of the UN/LOCODE values defined for this DocType."),
                        title=_("Invalid Status"),
                    )

    def populate_unlocode_details(self, refresh_external=False):
        """Populate UNLOCO details from database or external sources."""
        try:
            from logistics.air_freight.utils.unlocode_utils import (
                populate_unlocode_details as fetch_unlocode_payload,
                unwrap_populate_result,
                update_document_fields,
            )

            result = fetch_unlocode_payload(self.unlocode, refresh_external=refresh_external)
            details = unwrap_populate_result(result)

            if details:
                # Same application path as whitelist ``populate_unlocode_details(..., doc=…)``:
                # do not skip falsy check values (0 / False) or keys would stay stale on save.
                update_document_fields(self, details)
                if refresh_external:
                    # See _consume_unloco_autopopulate_skip (validate + before_save).
                    self._unloco_skip_autopopulate_rounds = 2

        except Exception as e:
            frappe.log_error(f"UNLOCO details population error: {str(e)}")

    def before_save(self):
        """Auto-populate only when UNLOCO code or auto-populate flag changes (see ``_should_run_autopopulate_on_save``)."""
        if not self.auto_populate or not self.unlocode or self._consume_unloco_autopopulate_skip():
            return
        if self._should_run_autopopulate_on_save():
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


@frappe.whitelist()
def start_update_all_unloco():
    """
    Queue a background job to re-run DataHub / overlay population on every UNLOCO row.

    Requires System Manager and UNLOCO write permission.
    """
    frappe.only_for("System Manager")
    if not frappe.has_permission("UNLOCO", "write"):
        frappe.throw(_("Not permitted to update UNLOCO"))

    frappe.enqueue(
        "logistics.logistics.doctype.unloco.unloco.run_update_all_unloco_job",
        queue="long",
        timeout=4 * 60 * 60,
        job_name="unloco_update_all_from_sources",
        enqueue_after_commit=True,
    )

    return {"queued": True}


def run_update_all_unloco_job():
    """
    Background: build the same field dict as desk populate via ``get_unlocode_data`` +
    ``populate_fields_from_data`` (with ``refresh_external``), overlay UNECE Function from the
    cached code-list for every ``has_*`` column, then ``frappe.db.set_value`` so checkboxes
    persist without relying on ``Document.save`` or the HTTP whitelist response shape.
    """
    batch_size = 100
    updated = 0
    try:
        from logistics.air_freight.utils.datahub_unlocode import (
            ensure_datahub_un_locode_files,
            is_datahub_un_locode_enabled,
        )
        from logistics.air_freight.utils.datahub_unlocode import (
            function_field_to_unloco_capabilities,
            get_codelist_function_field,
        )
        from logistics.air_freight.utils.unlocode_utils import get_unlocode_data, populate_fields_from_data

        if is_datahub_un_locode_enabled():
            ensure_datahub_un_locode_files()

        table_columns = set(frappe.get_meta("UNLOCO").get_valid_columns())
        # Never bulk-overwrite identity / audit columns from populate payload.
        skip_columns = frozenset({"name", "unlocode", "creation", "owner"})
        _has_keys = (
            "has_post",
            "has_customs",
            "has_unload",
            "has_airport",
            "has_rail",
            "has_road",
            "has_store",
            "has_terminal",
            "has_discharge",
            "has_seaport",
            "has_outport",
        )

        names = frappe.get_all("UNLOCO", pluck="name", order_by="name")
        batch_count = 0
        for name in names:
            try:
                code = (frappe.db.get_value("UNLOCO", name, "unlocode") or "").strip().upper()
                if len(code) != 5:
                    continue
                # Same core logic as desk ``populate_unlocode_details`` (avoid unwrap / HTTP-only edge cases).
                raw = get_unlocode_data(code, refresh_external=True)
                if not raw:
                    frappe.log_error(
                        f"UNLOCO Update All: no get_unlocode_data for name={name} code={code}",
                        "UNLOCO Update All: missing data",
                    )
                    continue
                raw.setdefault("unlocode", code)
                details = populate_fields_from_data(raw)
                row_updates = {
                    k: v
                    for k, v in details.items()
                    if k in table_columns and k not in skip_columns
                }
                fn = get_codelist_function_field(code)
                if fn:
                    for k, v in function_field_to_unloco_capabilities(fn).items():
                        if k in table_columns and k not in skip_columns and k in _has_keys:
                            row_updates[k] = 1 if v else 0
                if not row_updates:
                    continue
                row_updates["last_updated"] = frappe.utils.now()
                frappe.db.set_value("UNLOCO", name, row_updates, update_modified=True)
                updated += 1
            except Exception as e:
                frappe.log_error(
                    frappe.get_traceback(),
                    f"UNLOCO Update All: {name}: {e!s}",
                )
            batch_count += 1
            if batch_count >= batch_size:
                frappe.db.commit()
                batch_count = 0
        frappe.db.commit()
        frappe.logger().info(f"UNLOCO Update All finished: {updated} row(s) updated")
    except Exception:
        frappe.log_error(frappe.get_traceback(), "UNLOCO Update All job")
        raise
