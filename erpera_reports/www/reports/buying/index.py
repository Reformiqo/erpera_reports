import frappe
from datetime import datetime

def get_context(context):
    """
    Get context for the buying reports page.
    This function fetches data for the filter dropdowns and number card statistics.
    """
    
    # Fetch companies
    companies = frappe.get_all(
        "Company",
        fields=["name as value", "company_name as label"],
        filters={"is_group": 0}
    )
    
    # Fetch branches (cost centers)
    branches = frappe.get_all(
        "Cost Center",
        fields=["name as value", "cost_center_name as label"],
        filters={"is_group": 0}
    )
    
    # Fetch items (stock items only for buying)
    items = frappe.get_all(
        "Item",
        fields=["name as value", "item_name as label"],
        filters={"is_stock_item": 1}
    )
    
    # Fetch item groups
    item_groups = frappe.get_all(
        "Item Group",
        fields=["name as value", "name as label"],
        filters={"is_group": 0}
    )
    
    # Fetch suppliers
    suppliers = frappe.get_all(
        "Supplier",
        fields=["name as value", "supplier_name as label"],
        filters={"disabled": 0}
    )
    
    # Add the lists to the context
    context.company_list = companies
    context.branch_list = branches
    context.item_list = items
    context.item_group_list = item_groups
    context.supplier_list = suppliers
    
    # Calculate dynamic periods
    current_date = datetime.now()
    current_month = current_date.strftime("%B")  # Full month name (e.g., "July")
    current_year = current_date.year
    
    # Calculate fiscal year (assuming April to March fiscal year)
    if current_date.month >= 4:  # April onwards
        fiscal_year = f"FY {current_year}-{str(current_year + 1)[2:]}"
        fy_start = f"{current_year}-04-01"
        fy_end = f"{current_year + 1}-03-31"
    else:  # January to March
        fiscal_year = f"FY {current_year - 1}-{str(current_year)[2:]}"
        fy_start = f"{current_year - 1}-04-01"
        fy_end = f"{current_year}-03-31"
    
    # Add periods to context
    context.current_fiscal_year = fiscal_year
    context.current_month = current_month
    
    # Calculate statistics for number cards
    # Total purchase amount (current fiscal year)
    total_purchase_query = """
        SELECT SUM(pii.amount) as total_amount
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
        LEFT JOIN `tabItem` i ON pii.item_code = i.name
        WHERE pi.docstatus = 1
        AND pi.status NOT IN ('Cancelled', 'Return')
        AND pi.posting_date BETWEEN %s AND %s
        AND (
            i.is_stock_item = 1 
            OR (i.is_stock_item IS NULL AND pii.item_group NOT IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES'))
        )
    """
    total_purchase_result = frappe.db.sql(total_purchase_query, (fy_start, fy_end), as_dict=True)[0] or {}
    total_purchase = total_purchase_result.get('total_amount') or 0
    
    # Total purchase invoices (current fiscal year)
    total_invoices_query = """
        SELECT COUNT(DISTINCT pi.name) as invoice_count
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
        LEFT JOIN `tabItem` i ON pii.item_code = i.name
        WHERE pi.docstatus = 1
        AND pi.status NOT IN ('Cancelled', 'Return')
        AND pi.posting_date BETWEEN %s AND %s
        AND (
            i.is_stock_item = 1 
            OR (i.is_stock_item IS NULL AND pii.item_group NOT IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES'))
        )
    """
    total_invoices_result = frappe.db.sql(total_invoices_query, (fy_start, fy_end), as_dict=True)[0] or {}
    total_invoices = total_invoices_result.get('invoice_count') or 0
    
    # Unique suppliers (current fiscal year)
    unique_suppliers_query = """
        SELECT COUNT(DISTINCT pi.supplier) as supplier_count
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
        LEFT JOIN `tabItem` i ON pii.item_code = i.name
        WHERE pi.docstatus = 1
        AND pi.status NOT IN ('Cancelled', 'Return')
        AND pi.posting_date BETWEEN %s AND %s
        AND (
            i.is_stock_item = 1 
            OR (i.is_stock_item IS NULL AND pii.item_group NOT IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES'))
        )
    """
    unique_suppliers_result = frappe.db.sql(unique_suppliers_query, (fy_start, fy_end), as_dict=True)[0] or {}
    unique_suppliers = unique_suppliers_result.get('supplier_count') or 0
    
    # Average purchase value (current month)
    current_month_start = current_date.replace(day=1).strftime("%Y-%m-%d")
    current_month_end = current_date.strftime("%Y-%m-%d")
    
    avg_purchase_query = """
        SELECT 
            COALESCE(AVG(pi.grand_total), 0) as avg_amount
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
        LEFT JOIN `tabItem` i ON pii.item_code = i.name
        WHERE pi.docstatus = 1
        AND pi.status NOT IN ('Cancelled', 'Return')
        AND pi.posting_date BETWEEN %s AND %s
        AND (
            i.is_stock_item = 1 
            OR (i.is_stock_item IS NULL AND pii.item_group NOT IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES'))
        )
    """
    avg_purchase_result = frappe.db.sql(avg_purchase_query, (current_month_start, current_month_end), as_dict=True)[0] or {}
    avg_purchase = avg_purchase_result.get('avg_amount') or 0

    # Add formatted stats to the context
    context.total_purchase = f"₹{total_purchase:,.0f}"
    context.invoice_count = f"{total_invoices:,}"
    context.supplier_count = f"{unique_suppliers:,}"
    context.avg_invoice_value = f"₹{avg_purchase:,.0f}"
    
    return context
