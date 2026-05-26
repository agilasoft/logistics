# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Lifecycle Job: a main-service job (Air/Sea/Transport/Customs/Warehouse/Special Project) that
participates in a Special Project's (or Exhibit's) lifecycle. These rows drive the project's
lifecycle stage gating and act as planned booking/order seeds — they are NOT operational-doc
internal jobs (those still use ``Internal Job Detail``)."""

from frappe.model.document import Document


class LifecycleJob(Document):
	pass
