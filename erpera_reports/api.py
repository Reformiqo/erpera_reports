import frappe


cost_centers = {
    "Stores - HKE": "Main - HKE",
    "Store Cause Way - HKE": "Causeway - HKE",
    "Store Palanpur - HKE": "Palanpur - HKE"
}

@frappe.whitelist(allow_guest=True)
def update_stock_entry_cost_center():
    # get all stock entry details in which cost center is not set 
    details = frappe.db.get_list("Stock Entry Detail", {"cost_center": ""}, ["*"])
    for detail in details:
        doc = frappe.get_doc("Stock Entry Detail", detail.name)
        if doc.t_warehouse == "Stores - HKE":
            frappe.db.sql("""
                UPDATE `tabStock Entry Detail`
                SET cost_center = 'Main - HKE'
                WHERE name = %s
            """, (doc.name))
        
        elif doc.t_warehouse == "Store Cause Way - HKE":
            frappe.db.sql("""
                UPDATE `tabStock Entry Detail`
                SET cost_center = 'Causeway - HKE'
                WHERE name = %s
            """, (doc.name))
        
        elif doc.t_warehouse == "Store Palanpur - HKE":
            frappe.db.sql("""
                UPDATE `tabStock Entry Detail`
                SET cost_center = 'Palanpur - HKE'
                WHERE name = %s
            """, (doc.name))
    frappe.db.commit()
    return "Stock Entry Cost Center Updated"

