import frappe
from datetime import datetime

def get_context(context):
    """
    Get context for the selling reports page.
    This function fetches data for the filter dropdowns and number card statistics.
    Now uses filters from frappe.request.args.get for from_date, to_date, company, branch.
    """
    context.active_page = "selling"
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
    # Fetch items
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
    context.company_list = companies
    context.branch_list = branches
    context.item_list = items
    context.item_group_list = item_groups

    # Get filters from URL args
    args = frappe.request.args
    from_date = args.get('from_date')
    to_date = args.get('to_date')
    company = args.get('company')
    branch = args.get('branch')

    # Calculate dynamic periods (defaults)
    current_date = datetime.now()
    current_month = current_date.strftime("%B")
    current_year = current_date.year
    if current_date.month >= 4:
        fiscal_year = f"FY {current_year}-{str(current_year + 1)[2:]}"
        fy_start = f"{current_year}-04-01"
        fy_end = f"{current_year + 1}-03-31"
    else:
        fiscal_year = f"FY {current_year - 1}-{str(current_year)[2:]}"
        fy_start = f"{current_year - 1}-04-01"
        fy_end = f"{current_year}-03-31"
    context.current_fiscal_year = fiscal_year
    context.current_month = current_month

    # Use filters or defaults for number cards
    filter_from = from_date or fy_start
    filter_to = to_date or fy_end
    filter_month_from = from_date or current_date.replace(day=1).strftime("%Y-%m-%d")
    filter_month_to = to_date or current_date.strftime("%Y-%m-%d")

    # Build extra conditions for company/branch
    extra_si = ""
    extra_args = {}
    if company:
        extra_si += " AND si.company = %(company)s"
        extra_args['company'] = company
    if branch:
        extra_si += " AND si.cost_center = %(branch)s"
        extra_args['branch'] = branch

    # Query for total sales, invoice count, customer count (fiscal year or filtered)
    fy_stats_query = f"""
        SELECT
            SUM(total) AS total_sales,
            COUNT(name) AS invoice_count
        FROM `tabSales Invoice` si
        WHERE docstatus = 1 AND status NOT IN ('Cancelled', 'Return')
        AND posting_date BETWEEN %(from_date)s AND %(to_date)s
        {extra_si}
    """
    fy_sales_stats = frappe.db.sql(fy_stats_query, dict(from_date=filter_from, to_date=filter_to, **extra_args), as_dict=True)[0] or {}

    # Query for average sale value (current month or filtered)
    month_stats_query = f"""
        SELECT
            SUM(total) AS month_total_sales,
            COUNT(name) AS month_invoice_count
        FROM `tabSales Invoice` si
        WHERE docstatus = 1 AND status NOT IN ('Cancelled', 'Return')
        AND posting_date BETWEEN %(from_date)s AND %(to_date)s
        {extra_si}
    """
   
    month_sales_stats = frappe.db.sql(month_stats_query, dict(from_date=filter_month_from, to_date=filter_month_to, **extra_args), as_dict=True)[0] or {}

    # Calculate values
    total_sales = fy_sales_stats.get('total_sales') or 0
    invoice_count = fy_sales_stats.get('invoice_count') or 0
    customer_count = fy_sales_stats.get('customer_count') or 0
    month_total_sales = month_sales_stats.get('month_total_sales') or 0
    month_invoice_count = month_sales_stats.get('month_invoice_count') or 0
    avg_invoice_value = month_total_sales / month_invoice_count if month_invoice_count > 0 else 0

    context.total_sales = f"₹{total_sales:,.0f}"
    context.invoice_count = f"{invoice_count:,}"
    context.customer_count = frappe.db.count("Customer")
    context.avg_invoice_value = f"₹{avg_invoice_value:,.0f}"

    # Get detailed data for each cost center for modal display, using filters
    context.cost_center_details = get_cost_center_details(filter_from, filter_to, filter_month_from, filter_month_to, company, branch)
    return context

def get_cost_center_details(fy_start, fy_end, month_start, month_end, company=None, branch=None):
    """
    Get detailed statistics for each cost center to display in modal, using filters if provided
    """
    extra_si = ""
    args = {'fy_start': fy_start, 'fy_end': fy_end, 'month_start': month_start, 'month_end': month_end}
    if company:
        extra_si += " AND si.company = %(company)s"
        args['company'] = company
    if branch:
        extra_si += " AND si.cost_center = %(branch)s"
        args['branch'] = branch
    # Fiscal year data by cost center
    fy_by_cost_center_query = f"""
        SELECT 
            si.cost_center,
            cc.cost_center_name,
            SUM(si.total) AS total_sales,
            COUNT(si.name) AS invoice_count,
            COUNT(DISTINCT si.customer) AS customer_count
        FROM `tabSales Invoice` si
        LEFT JOIN `tabCost Center` cc ON si.cost_center = cc.name
        WHERE si.docstatus = 1 
        AND si.status NOT IN ('Cancelled', 'Return')
        AND si.posting_date BETWEEN %(fy_start)s AND %(fy_end)s
        AND si.cost_center IS NOT NULL
        {extra_si}
        GROUP BY si.cost_center, cc.cost_center_name
        ORDER BY total_sales DESC
    """
    fy_by_cost_center = frappe.db.sql(fy_by_cost_center_query, args, as_dict=True)
    # Current month data by cost center
    month_by_cost_center_query = f"""
        SELECT 
            si.cost_center,
            cc.cost_center_name,
            SUM(si.total) AS month_total_sales,
            COUNT(si.name) AS month_invoice_count
        FROM `tabSales Invoice` si
        LEFT JOIN `tabCost Center` cc ON si.cost_center = cc.name
        WHERE si.docstatus = 1 
        AND si.status NOT IN ('Cancelled', 'Return')
        AND si.posting_date BETWEEN %(month_start)s AND %(month_end)s
        AND si.cost_center IS NOT NULL
        {extra_si}
        GROUP BY si.cost_center, cc.cost_center_name
        ORDER BY month_total_sales DESC
    """
    month_by_cost_center = frappe.db.sql(month_by_cost_center_query, args, as_dict=True)
    cost_center_data = {}
    for row in fy_by_cost_center:
        cost_center = row.get('cost_center', 'Unknown')
        cost_center_data[cost_center] = {
            'name': cost_center,
            'display_name': row.get('cost_center_name', cost_center),
            'total_sales': row.get('total_sales', 0),
            'invoice_count': row.get('invoice_count', 0),
            'customer_count': row.get('customer_count', 0),
            'month_total_sales': 0,
            'month_invoice_count': 0,
            'avg_invoice_value': 0
        }
    for row in month_by_cost_center:
        cost_center = row.get('cost_center', 'Unknown')
        if cost_center not in cost_center_data:
            cost_center_data[cost_center] = {
                'name': cost_center,
                'display_name': row.get('cost_center_name', cost_center),
                'total_sales': 0,
                'invoice_count': 0,
                'customer_count': 0,
                'month_total_sales': 0,
                'month_invoice_count': 0,
                'avg_invoice_value': 0
            }
        cost_center_data[cost_center]['month_total_sales'] = row.get('month_total_sales', 0)
        cost_center_data[cost_center]['month_invoice_count'] = row.get('month_invoice_count', 0)
        month_invoice_count = row.get('month_invoice_count', 0)
        month_total_sales = row.get('month_total_sales', 0)
        if month_invoice_count > 0:
            cost_center_data[cost_center]['avg_invoice_value'] = month_total_sales / month_invoice_count
    result = []
    for cost_center, data in cost_center_data.items():
        result.append({
            'name': data['name'],
            'display_name': data['display_name'],
            'total_sales': f"₹{data['total_sales']:,.0f}",
            'invoice_count': f"{data['invoice_count']:,}",
            'customer_count': f"{data['customer_count']:,}",
            'avg_invoice_value': f"₹{data['avg_invoice_value']:,.0f}"
        })
    return result

