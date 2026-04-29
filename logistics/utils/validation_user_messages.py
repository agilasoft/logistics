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


def milestone_actual_end_without_start_message():
	return _(
		"Actual End is set but Actual Start is empty. A milestone cannot be completed before it starts.\n\n"
		"What to do: Enter Actual Start first (or at the same time), then set Actual End."
	)


def milestone_completed_before_planned_start_message():
	return _(
		"Actual End is earlier than Planned Start. This records the milestone as completed before the planned timeline begins.\n\n"
		"What to do: Adjust Planned Start and/or Actual End so completion is on or after the planned start, "
		"or disable strict milestone schedule validation in Logistics Settings if early completion should be allowed."
	)


def milestone_date_validation_title():
	return _("Invalid milestone dates")


def milestone_actual_future_dates_message(field_labels_str):
	return _(
		"{0} cannot be later than the current date and time. Actual dates record events that have already occurred.\n\n"
		"What to do: Correct those fields to a past or present moment, or clear them until the milestone happens. "
		"Use Planned Start and Planned End for future scheduling."
	).format(field_labels_str)


def booking_date_future_warning_message():
	return _(
		"The booking date is later than today.\n\n"
		"What to do: If the job was really booked for a future date, you can leave it. "
		"If the date was entered by mistake, change it to the correct booking date before continuing."
	)


def booking_date_future_warning_title():
	return _("Booking date in the future")
