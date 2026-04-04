# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Generate "Complete field reference" markdown from DocType JSON (parent + child tables).

Run from repo root:
  python logistics/setup/generate_wiki_field_references.py

Updates logistics/wiki_content/*.md where a matching doctype JSON exists, using markers:
  <!-- wiki-field-reference:start -->
  ...
  <!-- wiki-field-reference:end -->

Each row is: **Label (Field name)** | **Type** | **Description** — description uses the
field’s DocType ``description`` when set, plus standard freight / ERPNext semantics.
"""

from __future__ import unicode_literals

import json
import os
import re
from collections import OrderedDict

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOGISTICS_APP = os.path.join(REPO_ROOT, "logistics")
WIKI_DIR = os.path.join(LOGISTICS_APP, "wiki_content")

MARKER_START = "<!-- wiki-field-reference:start -->"
MARKER_END = "<!-- wiki-field-reference:end -->"

# Wiki file stem -> list of doctype *folder* names (under */doctype/<name>/). Used when the
# markdown page is not named after a single DocType but the guide should still embed full schemas.
WIKI_FIELD_STEMS_OVERRIDE = {
	"document_management": ["job_document", "document_list_template"],
	"milestone_tracking": ["job_milestone", "logistics_milestone"],
	"default_details_and_relationships": ["shipper", "consignee", "freight_agent"],
	"credit_management": ["credit_hold_lift_request"],
}

# Wiki stem -> markdown body (no markers). Inserted when there is no generated schema.
WIKI_STATIC_FIELD_SECTION = {
	"sales_quote_calculation_method": """## Complete field reference

_Calculation-method options and charge behaviour live on **Sales Quote** and its charge child tables. For every field (including calculation methods, tariffs, and breaks), see the **Complete field reference** section on:_

- [Sales Quote](welcome/sales-quote)""",
	"charges_tariff_revenue_cost_pattern": """## Complete field reference

_Charges, tariffs, revenue and cost fields are defined on operational DocTypes (bookings, shipments, orders, jobs, declarations, etc.). Each of these wiki pages ends with a **Complete field reference** generated from the app schema:_

- [Sales Quote](welcome/sales-quote) (source quote lines)
- [Air Booking](welcome/air-booking), [Air Shipment](welcome/air-shipment), [Sea Booking](welcome/sea-booking), [Sea Shipment](welcome/sea-shipment)
- [Transport Order](welcome/transport-order), [Transport Job](welcome/transport-job)
- [Declaration Order](welcome/declaration-order), [Declaration](welcome/declaration)
- [Warehouse Job](welcome/warehouse-job)
- [Change Request](welcome/change-request)""",
	"sales_quote_separate_billings_and_internal_job": """## Complete field reference

_Fields mentioned here (**Separate Billings per Service Type**, **Internal Job**, **Main Job**, routing, charges) are on **Sales Quote** and on each Booking / Order / Job DocType. Full column lists:_

- [Sales Quote](welcome/sales-quote)
- [Air Booking](welcome/air-booking), [Sea Booking](welcome/sea-booking), [Transport Order](welcome/transport-order), [Declaration Order](welcome/declaration-order), [Declaration](welcome/declaration)""",
	"customer_portal": """## Complete field reference

_Portal list views use the same DocTypes as desk. Full field lists:_

- [Transport Job](welcome/transport-job)
- [Warehouse Job](welcome/warehouse-job)
- _Stock balance views use standard ERPNext stock data (Item, Warehouse, Bin); see ERPNext documentation for those masters._""",
	"getting_started": """## Complete field reference

_Setup and transaction **DocTypes** each have a dedicated wiki page with a **Complete field reference** section (generated from JSON). Start from [Logistics Settings](welcome/logistics-settings), module settings (e.g. [Sea Freight Settings](welcome/sea-freight-settings)), then open the transaction or master page for the document you use._""",
	"recent_platform_updates": """## Complete field reference

_Features listed here touch many DocTypes. Open the relevant guide; each includes a **Complete field reference** where the document is a logistics DocType (e.g. [Sales Quote](welcome/sales-quote), [Air Booking](welcome/air-booking), [Transport Order](welcome/transport-order))._""",
	"transport_order_intermodule_field_copy": """## Complete field reference

_Header and package fields are on the transport and freight DocTypes. Full schemas:_

- [Transport Order](welcome/transport-order), [Transport Job](welcome/transport-job)
- [Air Shipment](welcome/air-shipment), [Sea Shipment](welcome/sea-shipment)
- [Inbound Order](welcome/inbound-order) _(when created from shipment)_""",
	"job_management_module": """## Complete field reference

_Recognition, jobs, and GL behaviour use fields on operational documents and settings. See **Complete field reference** on:_

- [General Job](welcome/general-job), [Logistics Settings](welcome/logistics-settings)
- [Air Shipment](welcome/air-shipment), [Sea Shipment](welcome/sea-shipment), [Transport Job](welcome/transport-job), [Warehouse Job](welcome/warehouse-job), [Declaration](welcome/declaration)
- [Sales Quote](welcome/sales-quote)""",
	"revenue_recognition_policy_accounts_and_dates": """## Complete field reference

_Policy fields live on **Logistics Settings** (and related operational documents). Full column lists:_

- [Logistics Settings](welcome/logistics-settings)
- [General Job](welcome/general-job), [Warehouse Job](welcome/warehouse-job)""",
	"proforma_gl_entries": """## Complete field reference

_GL rows use standard ERPNext **Journal Entry** / **GL Entry** structures plus logistics dimensions. Operational sources (with full field references on their wiki pages):_

- [General Job](welcome/general-job), [Air Shipment](welcome/air-shipment), [Sea Shipment](welcome/sea-shipment), [Transport Job](welcome/transport-job), [Warehouse Job](welcome/warehouse-job), [Declaration](welcome/declaration)""",
	"wip_accrual_reversal_on_invoicing_design": """## Complete field reference

_Design doc; implementation fields are on invoices and jobs. See:_

- [Logistics Settings](welcome/logistics-settings)
- [Air Shipment](welcome/air-shipment), [Sea Shipment](welcome/sea-shipment), [Transport Job](welcome/transport-job), [Declaration](welcome/declaration), [General Job](welcome/general-job)""",
	"internal_and_intercompany_billing": """## Complete field reference

_Billing uses fields on customer/supplier invoices and on logistics jobs/shipments. Full schemas on:_

- [Sales Quote](welcome/sales-quote), [Change Request](welcome/change-request)
- [Air Shipment](welcome/air-shipment), [Sea Shipment](welcome/sea-shipment), [Transport Job](welcome/transport-job), [Warehouse Job](welcome/warehouse-job), [Declaration](welcome/declaration)
- [Intercompany Module](welcome/intercompany-module) _(overview)_""",
	"intercompany_module": """## Complete field reference

_See **Complete field reference** on the documents you invoice or receive:_

- [Air Shipment](welcome/air-shipment), [Sea Shipment](welcome/sea-shipment), [Transport Job](welcome/transport-job), [Declaration](welcome/declaration), [Warehouse Job](welcome/warehouse-job)""",
	"sea_freight_module": """## Complete field reference

_Module transactions and masters (each page lists all fields):_

- [Sea Booking](welcome/sea-booking), [Sea Shipment](welcome/sea-shipment), [Sea Consolidation](welcome/sea-consolidation), [Master Bill](welcome/master-bill)
- [Shipper](welcome/shipper), [Consignee](welcome/consignee), [Container Type](welcome/container-type)
- [Sea Freight Settings](welcome/sea-freight-settings)""",
	"air_freight_module": """## Complete field reference

_Module transactions and masters:_

- [Air Booking](welcome/air-booking), [Air Shipment](welcome/air-shipment), [Air Consolidation](welcome/air-consolidation), [Master Air Waybill](welcome/master-air-waybill)
- [ULD Type](welcome/uld-type), [Air Freight Settings](welcome/air-freight-settings)""",
	"transport_module": """## Complete field reference

_Module transactions and masters:_

- [Transport Order](welcome/transport-order), [Transport Job](welcome/transport-job), [Transport Consolidation](welcome/transport-consolidation)
- [Transport Leg](welcome/transport-leg), [Transport Plan](welcome/transport-plan), [Run Sheet](welcome/run-sheet), [Proof of Delivery](welcome/proof-of-delivery)
- [Transport Template](welcome/transport-template), [Load Type](welcome/load-type), [Transport Settings](welcome/transport-settings)""",
	"customs_module": """## Complete field reference

_Module transactions and masters:_

- [Declaration Order](welcome/declaration-order), [Declaration](welcome/declaration)
- [Commodity](welcome/commodity), [Customs Authority](welcome/customs-authority), [Customs Settings](welcome/customs-settings)""",
	"warehousing_module": """## Complete field reference

_Module transactions and masters:_

- [Inbound Order](welcome/inbound-order), [Release Order](welcome/release-order), [Transfer Order](welcome/transfer-order), [VAS Order](welcome/vas-order), [Stocktake Order](welcome/stocktake-order)
- [Warehouse Job](welcome/warehouse-job), [Warehouse Contract](welcome/warehouse-contract), [Gate Pass](welcome/gate-pass), [Periodic Billing](welcome/periodic-billing)
- [Storage Location](welcome/storage-location), [Handling Unit Type](welcome/handling-unit-type), [Warehouse Settings](welcome/warehouse-settings)""",
	"sustainability_module": """## Complete field reference

_Sustainability metrics attach to operational documents; see their wiki pages for **Complete field reference** (e.g. [Sea Shipment](welcome/sea-shipment), [Air Shipment](welcome/air-shipment), [Transport Job](welcome/transport-job), [Warehouse Job](welcome/warehouse-job))._""",
	"special_projects_module": """## Complete field reference

_Special projects use [General Job](welcome/general-job) and related logistics documents; open the relevant doc wiki page for the full field table._""",
	"pages_overview": """## Complete field reference

_Mobile/page UIs surface fields from:_

- [Run Sheet](welcome/run-sheet), [Warehouse Job](welcome/warehouse-job), [Stocktake Order](welcome/stocktake-order)""",
	"reports_overview": """## Complete field reference

_Reports read submitted transactions; each source DocType is documented on its wiki page (**Complete field reference**), e.g. [Sea Shipment](welcome/sea-shipment), [Air Shipment](welcome/air-shipment), [Declaration](welcome/declaration), [Warehouse Job](welcome/warehouse-job)._""",
	"glossary": """## Complete field reference

_This page is a term index only. For every column on a form, open the DocType’s wiki page (e.g. from the module intro links); those pages include **Complete field reference** generated from the app._""",
	"customs_workflow_guide": """## Complete field reference

_Workflow uses **Declaration Order** and **Declaration** (and related masters). Full field lists:_

- [Declaration Order](welcome/declaration-order), [Declaration](welcome/declaration)
- [Commodity](welcome/commodity), [Customs Authority](welcome/customs-authority), [Customs Settings](welcome/customs-settings)
- [Document Management](welcome/document-management) _(Job Document & templates)_""",
	"cargonext_v1_astraea_press_release": """## Complete field reference

_Product announcement only. For schema documentation see [Getting Started](welcome/getting-started) and module transaction pages._""",
}


def _esc_cell(s):
	if s is None:
		return ""
	t = str(s).replace("\n", " ").replace("|", "\\|").strip()
	return t


def _load_doctype_index():
	"""Map DocType name (as in JSON \"name\" and Table options) -> absolute path."""
	index = {}
	for dirpath, _dirnames, filenames in os.walk(LOGISTICS_APP):
		if "/doctype/" not in dirpath.replace("\\", "/"):
			continue
		for fn in filenames:
			if not fn.endswith(".json"):
				continue
			path = os.path.join(dirpath, fn)
			try:
				with open(path, "r", encoding="utf-8") as f:
					data = json.load(f)
			except (json.JSONDecodeError, OSError):
				continue
			if data.get("doctype") != "DocType":
				continue
			name = data.get("name")
			if name:
				index[name] = path
	return index


def _fields_by_name(meta):
	by = OrderedDict()
	for row in meta.get("fields") or []:
		fn = row.get("fieldname")
		if fn:
			by[fn] = row
	return by


def _ordered_fieldnames(meta):
	order = meta.get("field_order") or []
	by = _fields_by_name(meta)
	seen = set()
	out = []
	for fn in order:
		if fn in by:
			out.append(fn)
			seen.add(fn)
	for fn in by:
		if fn not in seen:
			out.append(fn)
	return out


def _label_with_fieldname(field):
	fn = field.get("fieldname") or ""
	lb = (field.get("label") or "").strip()
	if lb:
		return "%s (`%s`)" % (lb, fn)
	return "`%s`" % fn if fn else "—"


def _purpose_enter_for_field(field):
	"""
	Return (purpose, what_to_enter) for wiki guidance.
	Purpose = role on the document / in the workflow. What to enter = practical input for users.
	"""
	ft = field.get("fieldtype") or ""
	opts = (field.get("options") or "").strip()
	label = (field.get("label") or "").strip()
	fn = (field.get("fieldname") or "").lower()
	lb_l = label.lower()

	def _pe(purpose, enter):
		return purpose, enter

	if ft == "Tab Break":
		return _pe(
			"Organises the form into tabs so related fields are easier to scan and edit.",
			"No data — click the tab to show or hide its fields.",
		)
	if ft == "Section Break":
		return _pe(
			"Visual grouping and optional heading for the fields that follow (improves long freight forms).",
			"No data — informational layout only.",
		)
	if ft == "Column Break":
		return _pe(
			"Continues the current row in a second column (standard ERP two-column layout).",
			"No data — layout only.",
		)
	if ft == "HTML":
		return _pe(
			"Shows calculated or static HTML (KPIs, dashboards, embedded help, milestone views).",
			"Nothing to type — content is rendered by the system.",
		)
	if ft == "Button":
		return _pe(
			"Runs an action (open a dialog, populate child rows, recalculate, sync from template).",
			"Click the button; follow prompts. Any data you add is usually stored in other fields or child tables.",
		)
	if ft == "Table":
		if opts:
			return _pe(
				"Stores repeating **%s** lines (child records) such as packages, charges, legs, or documents."
				% opts,
				"Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows.",
			)
		return _pe(
			"Repeating grid of related line items on this document.",
			"Add rows and complete each line; save the parent document.",
		)
	if ft == "Table MultiSelect":
		if opts:
			return _pe(
				"Links this record to many **%s** rows in one control (tags / multi-link pattern)." % opts,
				"Pick one or more existing **%s** records from the picker." % opts,
			)
		return _pe(
			"Multi-select links to other records.",
			"Choose multiple linked documents from the list.",
		)
	if ft == "Link":
		if opts:
			return _pe(
				"Creates a controlled reference to **%s** so party, place, item, or document data stays consistent for reporting and integrations."
				% opts,
				"Type to search or click the link icon; select an existing **%s**. Create the master first if it does not exist."
				% opts,
			)
		return _pe(
			"Points to another DocType record (single link).",
			"Search and select the target document name.",
		)
	if ft == "Dynamic Link":
		if opts:
			return _pe(
				"References another document whose **DocType** is chosen in field **%s** (same pattern as ERPNext Dynamic Link)."
				% opts,
				"First set the DocType field, then pick the document **name** for that type.",
			)
		return _pe(
			"Polymorphic link: DocType + document ID pair.",
			"Choose document type, then the specific document.",
		)
	if ft in ("Select", "Autocomplete"):
		if opts:
			choices = ", ".join(x.strip() for x in opts.split("\n") if x.strip())
			if len(choices) > 220:
				choices = choices[:217] + "…"
			return _pe(
				"Constrains input to predefined values (compliance, mode, status, or internal classification).",
				"Pick exactly one value from the list: %s." % choices,
			)
		return _pe(
			"Single choice from a configured list.",
			"Select one option from the dropdown.",
		)
	if ft == "Check":
		return _pe(
			"Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label).",
			"Tick **Yes** / enabled, untick **No** / disabled.",
		)
	if ft == "Data":
		if "email" in fn:
			return _pe(
				"Contact email for notices, portal, or authority correspondence.",
				"A valid email address (one line), e.g. name@company.com.",
			)
		if "phone" in fn or "tel" in fn or "mobile" in fn or "fax" in fn:
			return _pe(
				"Voice or fax contact for parties, drivers, or brokers.",
				"Phone or fax in local or international format; include country code when needed.",
			)
		if "website" in fn or "url" in fn or fn.endswith("_uri"):
			return _pe(
				"Web address for tracking, authority, or carrier portals.",
				"Full URL including https:// where applicable.",
			)
		if "postal" in fn or "zip" in fn or fn in ("pincode", "pin_code"):
			return _pe(
				"Postal routing for addresses and customs paperwork.",
				"Official postal or ZIP code for the city shown.",
			)
		if "city" in fn:
			return _pe(
				"City or locality for routing, addresses, and manifests.",
				"City name as used on commercial documents.",
			)
		if "state" in fn or "province" in fn:
			return _pe(
				"Sub-national region for compliance and address blocks.",
				"State, province, or region name or code per local practice.",
			)
		if "address" in fn or "street" in fn or fn.endswith("_line_1") or fn.endswith("_line_2"):
			return _pe(
				"Street-level address for pick-up, delivery, or registered office.",
				"Building, street, suite — match what appears on invoices or B/L.",
			)
		if "country" in fn and "code" in fn:
			return _pe(
				"ISO or internal country code for filtering and filings.",
				"Use your site’s standard (often ISO 3166 alpha-2).",
			)
		if any(
			x in fn
			for x in (
				"awb",
				"hbl",
				"mbl",
				"booking_ref",
				"reference_no",
				"container_no",
				"seal_no",
				"declaration_no",
				"invoice_no",
			)
		) or "_bl" in fn:
			return _pe(
				"Carrier, customs, or commercial reference printed on transport or customs documents.",
				"The exact identifier from the MAWB/HAWB, B/L, container interchange, or tax invoice.",
			)
		if "naming_series" in fn or fn == "series":
			return _pe(
				"Chooses which document number sequence applies (ERPNext naming series).",
				"Pick the series your organisation configured for this site or document type.",
			)
		if "timezone" in fn or "time_zone" in fn:
			return _pe(
				"Time zone for SLA windows, cut-offs, and local-time display.",
				"Use the format your organisation standardises (e.g. IANA **Region/City** or a short code from your master list).",
			)
		if "code" in fn and fn not in ("postal_code", "zip_code", "barcode"):
			return _pe(
				"Short stable code for lists, integrations, and EDI (often uppercase).",
				"Unique code within this master; match what customs, carriers, or APIs expect.",
			)
		return _pe(
			"Short free-text for codes, references, or labels that are not master-linked.",
			"Type the value as it should appear on print/PDF (no line breaks).",
		)
	if ft == "Small Text":
		if "email" in fn:
			return _pe("Compact email field.", "One email address.")
		if "phone" in fn or "tel" in fn:
			return _pe("Compact phone field.", "Phone number as used operationally.")
		return _pe(
			"Short note or identifier where a full **Text** field is not needed.",
			"One line of text; keep it brief for list views.",
		)
	if ft == "Text":
		return _pe(
			"Multi-line narrative (instructions, clauses, template text).",
			"Free text across multiple lines; use line breaks where helpful.",
		)
	if ft == "Long Text":
		return _pe(
			"Long remarks: cargo description, marks & numbers, special instructions, legal text.",
			"Enter the full operational or legal wording; paste from external docs if allowed by policy.",
		)
	if ft == "Int":
		if "day" in fn or "offset" in fn or "days" in lb_l:
			return _pe(
				"Whole-day offset or SLA duration (e.g. days before ETD, processing days).",
				"Integer only (no decimals); sign follows your process (negative = before event).",
			)
		if "sequence" in fn or "seq" in fn or "order" in fn:
			return _pe(
				"Sort order or sequence number for lists and templates.",
				"Whole number; lower usually appears first unless the form states otherwise.",
			)
		return _pe(
			"Whole number (counts, packages, TEU count, integer quantities).",
			"Digits only; no decimal point.",
		)
	if ft == "Float":
		if "weight" in fn or "mass" in lb_l or "kg" in lb_l:
			return _pe(
				"Mass for rating, load planning, and DG limits.",
				"Numeric weight; unit is implied by the label (often kg) — match company standard.",
			)
		if "volume" in fn or "cbm" in lb_l or "cu" in lb_l:
			return _pe(
				"Volume for chargeable calculations and vessel/air capacity.",
				"Decimal cubic measure per your label (e.g. CBM).",
			)
		if (fn.endswith("_rate") or fn == "rate" or fn.endswith("unit_rate")) and "strategy" not in fn:
			return _pe(
				"Unit rate or ratio used with quantity/UOM in charge calculations.",
				"Decimal per your pricing rules; respect minimums/maximums on the charge line if shown.",
			)
		return _pe(
			"Decimal quantity or measurement (weight, volume, count with decimals).",
			"Enter a number using site decimal precision.",
		)
	if ft == "Currency":
		co = opts or "currency"
		return _pe(
			"Money amount in the document’s commercial context (freight, duty, insured value).",
			"Amount in the currency indicated by field **%s** on this form (or company default)."
			% co,
		)
	if ft == "Date":
		toks = set(x for x in fn.replace("-", "_").split("_") if x)
		if "etd" in toks:
			return _pe(
				"Planned departure date for planning, cut-offs, and customer communication.",
				"Pick the expected departure date (local or agreed time zone).",
			)
		if "eta" in toks:
			return _pe(
				"Planned arrival for routing and consignee readiness.",
				"Expected arrival date at destination.",
			)
		if "atd" in toks:
			return _pe(
				"Actual departure for performance and milestone tracking.",
				"Set when departure is confirmed.",
			)
		if "ata" in toks:
			return _pe(
				"Actual arrival for POD and billing triggers.",
				"Set when cargo or conveyance arrived.",
			)
		if "cut" in lb_l or "cutoff" in fn or "cut_off" in fn:
			return _pe(
				"Carrier or terminal cut-off controlling booking and documentation.",
				"Official cut-off date (do not miss for loading or filing).",
			)
		if "booking" in fn and "date" in fn:
			return _pe(
				"Commercial booking date for audit trail and document dating.",
				"Date the booking was made or accepted.",
			)
		return _pe(
			"Calendar date for the business event described by the label.",
			"Choose the date from the picker; must reflect operational truth.",
		)
	if ft == "Datetime":
		return _pe(
			"Exact timestamp for events, SLAs, or audit (more precise than **Date** alone).",
			"Pick date and time; use the time zone your process expects (often local site).",
		)
	if ft == "Time":
		return _pe(
			"Clock time for shifts, gate hours, or cut-off times without a full date.",
			"Time only (HH:MM or per ERPNext control).",
		)
	if ft in ("Attach", "Attach Image"):
		return _pe(
			"Stores evidence: B/L, AWB, permits, POD scans, certificates.",
			"Upload PDF/image from disk or drag-and-drop; use clear filenames; respect max size limits.",
		)
	if ft == "Image":
		return _pe(
			"Image asset (photos of cargo, damage, ID).",
			"Upload an image file supported by the browser.",
		)
	if ft == "Read Only":
		return _pe(
			"Shows a value calculated or loaded elsewhere; avoids manual edits that would desync billing or stock.",
			"You cannot edit here; change source fields or run the action that refreshes this value.",
		)
	if ft == "Barcode":
		return _pe(
			"Scan-driven identification for warehouse or gate processes.",
			"Scan with a wedge scanner or type the barcode string.",
		)
	if ft == "Duration":
		return _pe(
			"Elapsed time between events (transit, dwell).",
			"Enter duration per control (hours/days) as configured.",
		)
	if ft == "Percent":
		return _pe(
			"Percentage for margins, duty rates, or capacity use.",
			"Numeric percent (often 0–100); confirm whether the form expects whole percent or fraction.",
		)
	if ft == "Icon":
		return _pe(
			"Visual icon for milestones or workspace navigation.",
			"Pick an icon from the selector.",
		)
	if ft == "JSON":
		return _pe(
			"Machine-readable payload for integrations or extensions.",
			"Valid JSON only — usually maintained by admins or integrations, not casual users.",
		)
	if ft == "Code":
		return _pe(
			"Script or configuration snippet for advanced behaviour.",
			"Paste or edit code only if authorised; syntax must match what the doctype expects.",
		)
	if ft == "Color":
		return _pe(
			"UI colour for badges or highlights.",
			"Choose a colour from the picker.",
		)
	if ft == "Geolocation":
		return _pe(
			"Pin on a map for yard, gate, or delivery location.",
			"Set coordinates via map control or paste lat/long if supported.",
		)
	if ft == "Rating":
		return _pe(
			"Qualitative score (service quality, risk).",
			"Select stars or score per control definition.",
		)
	if ft == "Phone":
		return _pe(
			"Structured phone entry (ERPNext **Phone** field).",
			"Enter number; country code as prompted.",
		)
	if ft == "Signature":
		return _pe(
			"Captures sign-off on delivery or authorisation.",
			"Sign on screen or attached pad per device.",
		)
	if ft == "Heading":
		return _pe(
			"Static title within the form.",
			"No input.",
		)
	if ft == "Fold":
		return _pe(
			"Collapsible region to shorten long forms.",
			"Expand/collapse only; no stored value.",
		)
	if ft == "Naming Series":
		return _pe(
			"Determines the numbering prefix/pattern for new document IDs.",
			"Select the series; the system assigns the next ID on save.",
		)
	return _pe(
		"Field type **%s** — stores or displays data per Frappe standard behaviour." % ft,
		"Enter or select a value appropriate to the label; see ERPNext docs for this field type if unsure.",
	)


def _compose_field_description(field):
	"""Merge DocType JSON description with purpose, what to enter, and behaviour flags."""
	doc = (field.get("description") or "").strip()
	purpose, enter = _purpose_enter_for_field(field)
	low = doc.lower()

	parts = []
	if doc:
		parts.append(
			"**From definition:** %s **Purpose:** %s **What to enter:** %s"
			% (doc, purpose, enter)
		)
	else:
		parts.append("**Purpose:** %s **What to enter:** %s" % (purpose, enter))

	extras = []
	if field.get("read_only") and "read" not in low and "readonly" not in low and "system" not in low:
		extras.append(
			"**Behaviour:** Read-only here — value comes from calculation, another field, or workflow."
		)
	if field.get("mandatory") and "required" not in low and "mandatory" not in low:
		extras.append("**Behaviour:** Required when the document is saved or submitted (per validation rules).")
	if field.get("hidden") and "hidden" not in low:
		extras.append("**Behaviour:** Hidden in default layout; may still be set by import, API, or script.")
	ff = field.get("fetch_from")
	if ff and ff not in doc:
		extras.append(
			"**Behaviour:** Auto-filled from `%s` when the link/source changes — verify after edits."
			% ff
		)
	if extras:
		parts.append(" ".join(extras))
	return " ".join(parts)


def _field_row(field):
	ft = field.get("fieldtype") or ""
	return (
		_label_with_fieldname(field),
		ft,
		_compose_field_description(field),
	)


def _table_md(rows):
	lines = [
		"| Label (Field name) | Type | Description |",
		"| --- | --- | --- |",
	]
	for r in rows:
		lines.append(
			"| %s | %s | %s |"
			% tuple(_esc_cell(x) for x in r)
		)
	return "\n".join(lines)


def _generate_for_doctype(doctype_name, index, visited_stack):
	if doctype_name in visited_stack:
		return "\n_(circular reference: %s)_\n" % doctype_name
	path = index.get(doctype_name)
	if not path:
		return "\n_(DocType JSON not found in app: %s)_\n" % doctype_name

	with open(path, "r", encoding="utf-8") as f:
		meta = json.load(f)

	title = meta.get("name") or doctype_name
	by = _fields_by_name(meta)
	parts = []

	rows = []
	for fn in _ordered_fieldnames(meta):
		f = by[fn]
		rows.append(_field_row(f))
	parts.append(_table_md(rows))

	visited_stack = visited_stack + (doctype_name,)

	for fn in _ordered_fieldnames(meta):
		f = by[fn]
		ft = f.get("fieldtype")
		opts = (f.get("options") or "").strip()
		if ft == "Table" and opts and opts in index:
			parts.append(
				"\n#### Child table: %s (field `%s` on parent)\n"
				% (_esc_cell(opts), _esc_cell(fn))
			)
			parts.append(_generate_for_doctype(opts, index, visited_stack))
		elif ft == "Table MultiSelect" and opts and opts in index:
			parts.append(
				"\n#### Child table (multi): %s (field `%s` on parent)\n"
				% (_esc_cell(opts), _esc_cell(fn))
			)
			parts.append(_generate_for_doctype(opts, index, visited_stack))

	return "\n".join(parts)


def _find_doctype_json_path(stem):
	"""Resolve module/doctype/{stem}/{stem}.json under the logistics app package."""
	suffix = "/doctype/%s" % stem
	for dirpath, _dirnames, filenames in os.walk(LOGISTICS_APP):
		norm = dirpath.replace("\\", "/")
		if "__pycache__" in norm:
			continue
		if not norm.endswith(suffix):
			continue
		candidate = os.path.join(dirpath, "%s.json" % stem)
		if os.path.isfile(candidate):
			return candidate
	return None


def build_reference_block(stem, index):
	stems_to_render = []
	if stem in WIKI_FIELD_STEMS_OVERRIDE:
		stems_to_render = list(WIKI_FIELD_STEMS_OVERRIDE[stem])
	else:
		path = _find_doctype_json_path(stem)
		if path:
			stems_to_render = [stem]

	if not stems_to_render:
		return None

	sections = []
	for st in stems_to_render:
		p = _find_doctype_json_path(st)
		if not p:
			continue
		with open(p, "r", encoding="utf-8") as f:
			meta = json.load(f)
		dn = meta.get("name")
		if dn:
			sections.append((dn, _generate_for_doctype(dn, index, ())))

	if not sections:
		return None

	if len(sections) == 1:
		doctype_name, body = sections[0]
		intro = (
			"_All fields from DocType **%s** and nested child tables, in form order "
			"(including layout breaks). Columns: **Label** with technical **field name** in backticks, "
			"**Type**, and **Description** (from the DocType definition and standard freight/ERP semantics)._"
			% _esc_cell(doctype_name)
		)
		body_out = body.strip()
	else:
		names = ", ".join("**%s**" % _esc_cell(t[0]) for t in sections)
		intro = (
			"_All fields from DocTypes %s (subsections below) and their nested child tables, "
			"in form order. Columns: **Label** (`field name`), **Type**, **Description**._"
			% names
		)
		parts = []
		for title, sec_body in sections:
			parts.append("### %s\n\n%s" % (_esc_cell(title), sec_body.strip()))
		body_out = "\n\n".join(parts)

	if stem == "credit_management":
		body_out += (
			"\n\n_Customer credit-tab logistics fields (`logistics_credit_status`, etc.) are "
			"custom fields on ERPNext **Customer** (see app fixtures). Credit-control toggles and "
			"subject DocTypes are on **Logistics Settings** — see [Logistics Settings](welcome/logistics-settings)._"
		)

	block = "\n".join(
		[
			MARKER_START,
			"",
			"## Complete field reference",
			"",
			intro,
			"",
			body_out,
			"",
			MARKER_END,
		]
	)
	return block


def _wrap_static_field_section(md_body):
	return "\n".join([MARKER_START, "", md_body.strip(), "", MARKER_END])


def _find_insertion_line(lines):
	"""Insert before the last top-level ## heading that looks like 'Related …'."""
	related_re = re.compile(r"^## .*(Related|Documentation|articles|Code and DocTypes)\b", re.I)
	for i in range(len(lines) - 1, -1, -1):
		if related_re.match(lines[i].rstrip()):
			return i
	return len(lines)


def patch_markdown(path, block):
	with open(path, "r", encoding="utf-8") as f:
		text = f.read()

	if MARKER_START in text and MARKER_END in text:
		pattern = re.compile(
			re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END),
			re.DOTALL,
		)
		new_text = pattern.sub(block.strip(), text, count=1)
	else:
		lines = text.splitlines(keepends=True)
		idx = _find_insertion_line(lines)
		prefix = "".join(lines[:idx])
		suffix = "".join(lines[idx:])
		sep = "\n\n" if prefix and not prefix.endswith("\n\n") else "\n"
		if prefix and not prefix.endswith("\n"):
			sep = "\n" + sep
		new_text = prefix + sep + block + "\n\n" + suffix

	with open(path, "w", encoding="utf-8") as f:
		f.write(new_text)


def main():
	index = _load_doctype_index()
	updated = 0
	for name in sorted(os.listdir(WIKI_DIR)):
		if not name.endswith(".md") or name == "README.md":
			continue
		stem = name[:-3]
		block = build_reference_block(stem, index)
		if not block:
			static = WIKI_STATIC_FIELD_SECTION.get(stem)
			if static:
				block = _wrap_static_field_section(static)
		if not block:
			continue
		patch_markdown(os.path.join(WIKI_DIR, name), block)
		updated += 1
		print("updated", name)

	print("Done. Patched %s wiki markdown file(s)." % updated)


if __name__ == "__main__":
	main()
