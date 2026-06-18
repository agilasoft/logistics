import frappe


def inspect():
    sps = frappe.get_all("Special Project", limit=15, order_by="creation desc")
    print("SPs:", [s.name for s in sps])
    found = False
    for sp_name in [s.name for s in sps]:
        sp = frappe.get_doc("Special Project", sp_name)
        if not sp.packages:
            continue
        for pkg in sp.packages:
            if pkg.warehouse_item or pkg.length or pkg.weight:
                if not found:
                    print(f"\nSP: {sp_name}")
                    found = True
                print(
                    f"  Pkg idx={pkg.idx} wh={pkg.warehouse_item} commodity={pkg.commodity} "
                    f"desc={pkg.description}"
                )
                print(
                    f"    length={pkg.length} width={pkg.width} height={pkg.height} "
                    f"weight={pkg.weight} volume={pkg.volume}"
                )
                print(
                    f"    dim_uom={pkg.dimension_uom} wt_uom={pkg.weight_uom} "
                    f"volume_uom={pkg.volume_uom}"
                )
                print(
                    f"    no_of_packs={pkg.no_of_packs} hs_code={pkg.hs_code} "
                    f"ref={pkg.reference_no} include_on_create={pkg.include_on_create}"
                )
        if found:
            break
