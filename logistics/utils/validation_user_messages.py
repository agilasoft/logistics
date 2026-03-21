# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""User-facing detail text for validation errors (what went wrong and how to fix it)."""

from frappe import _


def etd_eta_freight_invalid_message():
	return _(
		"Estimated departure (ETD) is after estimated arrival (ETA). "
		"A consignment cannot arrive before it departs.\n\n"
		"What to do: In the dates section, set ETD to the same day as ETA or an earlier day, "
		"or set ETA to the same day as ETD or a later day. Check for typos if the dates came from a quote or import. "
		"Then save again."
	)


def etd_eta_freight_title():
	return _("Invalid ETD and ETA")


def atd_ata_freight_invalid_message():
	return _(
		"Actual departure (ATD) is after actual arrival (ATA). "
		"Recorded times must show that the shipment left on or before it arrived.\n\n"
		"What to do: Correct ATD and/or ATA so departure is on or before arrival (the same date is allowed). "
		"If you are back-filling from paperwork, match the sequence on the MAWB/HAWB or carrier status. Then save again."
	)


def atd_ata_freight_title():
	return _("Invalid ATD and ATA")


def declaration_etd_eta_invalid_message():
	return _(
		"Expected departure (ETD) is after expected arrival (ETA). "
		"The declared journey cannot show arrival before departure.\n\n"
		"What to do: Update ETD and/or ETA on this document so departure is on or before arrival, "
		"then save. If these dates are copied from a booking or shipment, fix them at the source or override here."
	)


def declaration_etd_eta_title():
	return _("Invalid expected departure and arrival")


def milestone_planned_range_invalid_message():
	return _(
		"Planned Start is after Planned End. The planned window must start on or before it ends.\n\n"
		"What to do: On this milestone row, set Planned Start to the same moment as Planned End or earlier, "
		"or move Planned End later. If dates were calculated from a template, check offset days on the template item."
	)


def milestone_actual_range_invalid_message():
	return _(
		"Actual Start is after Actual End. Actual times must show the milestone began on or before it finished.\n\n"
		"What to do: Correct Actual Start and/or Actual End on this milestone row. "
		"If you use “capture” actions, set the end only after the start, or edit both manually. Then save again."
	)


def milestone_date_validation_title():
	return _("Invalid milestone dates")


def booking_date_future_warning_message():
	return _(
		"The booking date is later than today.\n\n"
		"What to do: If the job was really booked for a future date, you can leave it. "
		"If the date was entered by mistake, change it to the correct booking date before continuing."
	)


def booking_date_future_warning_title():
	return _("Booking date in the future")
