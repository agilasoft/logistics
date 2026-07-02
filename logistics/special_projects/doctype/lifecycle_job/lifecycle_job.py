# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Lifecycle Job: a main-service job (Air/Sea/Transport/Customs/Warehouse/Special Project) that
participates in a Special Project's (or Exhibit's) lifecycle. These rows drive the project's
lifecycle stage gating and act as planned booking/order seeds — they are NOT operational-doc
internal jobs (those still use ``Internal Job Detail``)."""

from frappe.model.document import Document

from logistics.special_projects.lifecycle_job_display import lifecycle_job_line_display_label


_HISTORICAL_LINK_FIELDS = frozenset({"job_no", "order_no"})


class LifecycleJob(Document):
	def get_title(self):
		label = lifecycle_job_line_display_label(self)
		return label or self.name

	def get_invalid_links(self, is_submittable=False):
		invalid_links, cancelled_links = super().get_invalid_links(is_submittable=is_submittable)
		# job_no / order_no are historical pointers; linked operational docs may be cancelled while parent still saves.
		cancelled_links = [c for c in cancelled_links if c[0] not in _HISTORICAL_LINK_FIELDS]
		return invalid_links, cancelled_links
