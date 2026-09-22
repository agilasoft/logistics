

Air Booking + Air Shipment only:

    from logistics.utils.clear_operational_transactions import clear_air_transactions
    clear_air_transactions(dry_run=True)
    clear_air_transactions(dry_run=False, confirm_site="atndemo.s.frappe.cloud")
AIR_SUPPORTING = [
	"Air Shipment IATA Transaction",
	"Dangerous Goods Declaration",
	"Air Consolidation",
	"Master Air Waybill",
]

AIR_CORE = ["Air Shipment", "Air Booking"]


def clear_air_transactions(dry_run=True, confirm_site=None):
	"""Cancel and delete Air Booking and Air Shipment transactions on the current site.

	Also removes air consolidations, MAWBs, IATA/DGD rows, and Job Number /
	Linked Service / Internal Job records that point at those air documents.
	Invoices and masters are kept; links to the deleted air docs are cleared.
	"""
	site = frappe.local.site
	if not dry_run and confirm_site != site:
		frappe.throw(
			f"Pass confirm_site='{site}' to delete on this site. "
			"Live delete refused without an explicit matching site name."
		)

	targets = [dt for dt in (AIR_SUPPORTING + AIR_CORE) if frappe.db.exists("DocType", dt)]
	delete_set = set(targets) | {"Air Booking", "Air Shipment"}

	print(f"Site: {site}")
	print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
	print("")

	counts = []
	total = 0
	for dt in targets:
		n = _safe_count(dt)
		counts.append((dt, n))
		total += n
		print(f"  {dt}: {n}")

	job_numbers = _air_job_numbers()
	linked_services = _air_linked_services()
	internal_jobs = _air_internal_jobs()
	print(f"  Job Number (Air Booking/Shipment): {len(job_numbers)}")
	print(f"  Linked Service (air parent/usage): {len(linked_services)}")
	print(f"  Internal Job (air parent): {len(internal_jobs)}")
	total += len(job_numbers) + len(linked_services) + len(internal_jobs)
	print(f"\nTotal documents: {total}")

	if dry_run:
		print("\nDry run only. Run again with dry_run=False to delete.")
		return {
			"dry_run": True,
			"site": site,
			"counts": counts,
			"job_numbers": len(job_numbers),
			"linked_services": len(linked_services),
			"internal_jobs": len(internal_jobs),
			"total": total,
		}

	frappe.set_user("Administrator")
	frappe.flags.ignore_links = True

	print("\nUnlinking invoices and other documents that are not being deleted...")
	_unlink_external(AIR_CORE, delete_set)
	frappe.db.commit()

	deleted = []
	failed = []

	scoped = [
		("Job Number", job_numbers),
		("Linked Service", linked_services),
		("Internal Job", internal_jobs),
	]
	for dt, names in scoped:
		if not names:
			continue
		print(f"\n{dt}: {len(names)}")
		for i, name in enumerate(names, 1):
			try:
				_cancel_and_delete(dt, name)
				deleted.append((dt, name))
			except Exception as e:
				failed.append((dt, name, str(e)[:240]))
				print(f"  FAIL {name}: {e}")
			if i % 20 == 0:
				frappe.db.commit()
				print(f"  ... {i}/{len(names)}")
		frappe.db.commit()

	for dt in targets:
		names = frappe.get_all(dt, pluck="name")
		if not names:
			continue
		print(f"\n{dt}: {len(names)}")
		for i, name in enumerate(names, 1):
			try:
				_cancel_and_delete(dt, name)
				deleted.append((dt, name))
			except Exception as e:
				failed.append((dt, name, str(e)[:240]))
				print(f"  FAIL {name}: {e}")
			if i % 20 == 0:
				frappe.db.commit()
				print(f"  ... {i}/{len(names)}")
		frappe.db.commit()

	print(f"\nDeleted: {len(deleted)}")
	print(f"Failed: {len(failed)}")
	if failed:
		for dt, name, err in failed[:50]:
			print(f"  {dt} {name}: {err}")
		if len(failed) > 50:
			print(f"  ... and {len(failed) - 50} more")
	else:
		print("Done.")

	return {
		"dry_run": False,
		"site": site,
		"deleted": len(deleted),
		"failed": failed,
		"counts_before": counts,
	}


def _air_job_numbers():
	if not frappe.db.exists("DocType", "Job Number"):
		return []
	return frappe.get_all(
		"Job Number",
		filters={"job_type": ("in", AIR_CORE)},
		pluck="name",
	)


def _air_linked_services():
	if not frappe.db.exists("DocType", "Linked Service"):
		return []
	names = set(
		frappe.get_all(
			"Linked Service",
			filters={"parent_booking_type": ("in", AIR_CORE)},
			pluck="name",
		)
	)
	if frappe.db.exists("DocType", "Linked Service Usage"):
		for row in frappe.get_all(
			"Linked Service Usage",
			filters={"used_on_doctype": ("in", AIR_CORE)},
			fields=["parent"],
		):
			if row.parent:
				names.add(row.parent)
	return sorted(names)


def _air_internal_jobs():
	if not frappe.db.exists("DocType", "Internal Job"):
		return []
	return frappe.get_all(
		"Internal Job",
		filters={"parent_booking_type": ("in", AIR_CORE)},
		pluck="name",
	)
