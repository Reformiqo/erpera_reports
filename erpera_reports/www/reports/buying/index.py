import frappe
from datetime import datetime

def get_context(context):
    """
    Get context for the buying reports page.
    This function fetches data for the filter dropdowns and number card statistics.
    Now uses filters from frappe.request.args.get for from_date, to_date, company, branch.
    """
    context.active_page = "buying"
    
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
        filters={"is_stock_item": 1, "item_group": ["!=", "Raw Material", "Services", "Sub Assemblies", "Consumable", "Furniture", "EXPENSE", "FIXED ASSET"]}
    )
    
    # Fetch item groups
    item_groups = frappe.get_all(
        "Item Group",
        fields=["name as value", "name as label"],
        filters={"is_group": 0, "item_group_name": ["!=", "Raw Material", "Services", "Sub Assemblies", "Consumable", "Furniture", "EXPENSE", "FIXED ASSET"]}
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
    
    # Get filters from URL args
    args = frappe.request.args
    from_date = args.get('from_date')
    to_date = args.get('to_date')
    company = args.get('company')
    branch = args.get('branch')
    
    # Calculate dynamic periods (defaults)
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
    
    # Use filters or defaults for number cards
    filter_from = from_date or fy_start
    filter_to = to_date or fy_end
    filter_month_from = from_date or current_date.replace(day=1).strftime("%Y-%m-%d")
    filter_month_to = to_date or current_date.strftime("%Y-%m-%d")
    
    # Build extra conditions for company/branch
    extra_pi = ""
    extra_args = {}
    if company:
        extra_pi += " AND pi.company = %(company)s"
        extra_args['company'] = company
    if branch:
        extra_pi += " AND pi.cost_center = %(branch)s"
        extra_args['branch'] = branch
    
    # Calculate statistics for number cards
    # Total purchase amount (fiscal year or filtered)
    total_purchase_query = f"""
        SELECT SUM(pii.amount) as total_amount
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
        LEFT JOIN `tabItem` i ON pii.item_code = i.name
        WHERE pi.docstatus = 1
        AND pi.status NOT IN ('Cancelled', 'Return')
        AND pi.posting_date BETWEEN %(from_date)s AND %(to_date)s
        {extra_pi}
        AND (
            i.is_stock_item = 1 
            OR (i.is_stock_item IS NULL AND pii.item_group NOT IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES'))
        )
    """
    total_purchase_result = frappe.db.sql(total_purchase_query, dict(from_date=filter_from, to_date=filter_to, **extra_args), as_dict=True)[0] or {}
    total_purchase = total_purchase_result.get('total_amount') or 0
    
    # Total purchase invoices (fiscal year or filtered)
    total_invoices_query = f"""
        SELECT COUNT(DISTINCT pi.name) as invoice_count
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
        LEFT JOIN `tabItem` i ON pii.item_code = i.name
        WHERE pi.docstatus = 1
        AND pi.status NOT IN ('Cancelled', 'Return')
        AND pi.posting_date BETWEEN %(from_date)s AND %(to_date)s
        {extra_pi}
        AND (
            i.is_stock_item = 1 
            OR (i.is_stock_item IS NULL AND pii.item_group NOT IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES'))
        )
    """
    total_invoices_result = frappe.db.sql(total_invoices_query, dict(from_date=filter_from, to_date=filter_to, **extra_args), as_dict=True)[0] or {}
    total_invoices = total_invoices_result.get('invoice_count') or 0
    
    # Unique suppliers (fiscal year or filtered)
    unique_suppliers_query = f"""
        SELECT COUNT(DISTINCT pi.supplier) as supplier_count
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
        LEFT JOIN `tabItem` i ON pii.item_code = i.name
        WHERE pi.docstatus = 1
        AND pi.status NOT IN ('Cancelled', 'Return')
        AND pi.posting_date BETWEEN %(from_date)s AND %(to_date)s
        {extra_pi}
        AND (
            i.is_stock_item = 1 
            OR (i.is_stock_item IS NULL AND pii.item_group NOT IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES'))
        )
    """
    unique_suppliers_result = frappe.db.sql(unique_suppliers_query, dict(from_date=filter_from, to_date=filter_to, **extra_args), as_dict=True)[0] or {}
    unique_suppliers = unique_suppliers_result.get('supplier_count') or 0
    
    # Average purchase value (current month or filtered)
    avg_purchase_query = f"""
        SELECT 
            COALESCE(AVG(pi.grand_total), 0) as avg_amount
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
        LEFT JOIN `tabItem` i ON pii.item_code = i.name
        WHERE pi.docstatus = 1
        AND pi.status NOT IN ('Cancelled', 'Return')
        AND pi.posting_date BETWEEN %(from_date)s AND %(to_date)s
        {extra_pi}
        AND (
            i.is_stock_item = 1 
            OR (i.is_stock_item IS NULL AND pii.item_group NOT IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES'))
        )
    """
    avg_purchase_result = frappe.db.sql(avg_purchase_query, dict(from_date=filter_month_from, to_date=filter_month_to, **extra_args), as_dict=True)[0] or {}
    avg_purchase = avg_purchase_result.get('avg_amount') or 0

    # Add formatted stats to the context
    context.total_purchase = f"₹{total_purchase:,.0f}"
    context.invoice_count = f"{total_invoices:,}"
    context.supplier_count = f"{unique_suppliers:,}"
    context.avg_invoice_value = f"₹{avg_purchase:,.0f}"
    
    # Get detailed data for each cost center for modal display, using filters
    context.cost_center_details = get_cost_center_details(filter_from, filter_to, filter_month_from, filter_month_to, company, branch)
    
    return context

def get_cost_center_details(fy_start, fy_end, month_start, month_end, company=None, branch=None):
    """
    Get detailed statistics for each cost center to display in modal, using filters if provided
    """
    extra_pi = ""
    args = {'fy_start': fy_start, 'fy_end': fy_end, 'month_start': month_start, 'month_end': month_end}
    if company:
        extra_pi += " AND pi.company = %(company)s"
        args['company'] = company
    if branch:
        extra_pi += " AND pi.cost_center = %(branch)s"
        args['branch'] = branch
    # Query for fiscal year data by cost center
    fy_by_cost_center_query = f"""
        SELECT 
            pi.cost_center,
            cc.cost_center_name,
            SUM(pii.amount) AS total_purchase,
            COUNT(DISTINCT pi.name) AS invoice_count,
            COUNT(DISTINCT pi.supplier) AS supplier_count
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
        LEFT JOIN `tabItem` i ON pii.item_code = i.name
        LEFT JOIN `tabCost Center` cc ON pi.cost_center = cc.name
        WHERE pi.docstatus = 1 
        AND pi.status NOT IN ('Cancelled', 'Return')
        AND pi.posting_date BETWEEN %(fy_start)s AND %(fy_end)s
        AND pi.cost_center IS NOT NULL
        {extra_pi}
        AND (
            i.is_stock_item = 1 
            OR (i.is_stock_item IS NULL AND pii.item_group NOT IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES'))
        )
        GROUP BY pi.cost_center, cc.cost_center_name
        ORDER BY total_purchase DESC
    """
    
    fy_by_cost_center = frappe.db.sql(fy_by_cost_center_query, args, as_dict=True)
    
    # Query for current month data by cost center
    month_by_cost_center_query = f"""
        SELECT 
            pi.cost_center,
            cc.cost_center_name,
            COALESCE(AVG(pi.grand_total), 0) AS avg_invoice_value
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
        LEFT JOIN `tabItem` i ON pii.item_code = i.name
        LEFT JOIN `tabCost Center` cc ON pi.cost_center = cc.name
        WHERE pi.docstatus = 1 
        AND pi.status NOT IN ('Cancelled', 'Return')
        AND pi.posting_date BETWEEN %(month_start)s AND %(month_end)s
        AND pi.cost_center IS NOT NULL
        {extra_pi}
        AND (
            i.is_stock_item = 1 
            OR (i.is_stock_item IS NULL AND pii.item_group NOT IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES'))
        )
        GROUP BY pi.cost_center, cc.cost_center_name
        ORDER BY avg_invoice_value DESC
    """
    
    month_by_cost_center = frappe.db.sql(month_by_cost_center_query, args, as_dict=True)
    
    # Create a dictionary to combine the data
    cost_center_data = {}
    
    # Process fiscal year data
    for row in fy_by_cost_center:
        cost_center = row.get('cost_center', 'Unknown')
        cost_center_data[cost_center] = {
            'name': cost_center,
            'display_name': row.get('cost_center_name', cost_center),
            'total_purchase': row.get('total_purchase', 0),
            'invoice_count': row.get('invoice_count', 0),
            'supplier_count': row.get('supplier_count', 0),
            'avg_invoice_value': 0
        }
    
    # Process current month data
    for row in month_by_cost_center:
        cost_center = row.get('cost_center', 'Unknown')
        if cost_center not in cost_center_data:
            cost_center_data[cost_center] = {
                'name': cost_center,
                'display_name': row.get('cost_center_name', cost_center),
                'total_purchase': 0,
                'invoice_count': 0,
                'supplier_count': 0,
                'avg_invoice_value': 0
            }
        
        cost_center_data[cost_center]['avg_invoice_value'] = row.get('avg_invoice_value', 0)
    
    # Convert to list and format values
    result = []
    for cost_center, data in cost_center_data.items():
        result.append({
            'name': data['name'],
            'display_name': data['display_name'],
            'total_purchase': f"₹{data['total_purchase']:,.0f}",
            'invoice_count': f"{data['invoice_count']:,}",
            'supplier_count': f"{data['supplier_count']:,}",
            'avg_invoice_value': f"₹{data['avg_invoice_value']:,.0f}"
        })
    
    return result
