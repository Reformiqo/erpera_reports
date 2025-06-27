import frappe
from datetime import datetime

def get_context(context):
    """
    Get context for the selling reports page.
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
    
    # Add the lists to the context
    context.company_list = companies
    context.branch_list = branches
    context.item_list = items
    context.item_group_list = item_groups
    
    # Calculate dynamic periods
    current_date = datetime.now()
    current_month = current_date.strftime("%B")  # Full month name (e.g., "July")
    current_year = current_date.year
    
    # Calculate fiscal year (assuming April to March fiscal year)
    if current_date.month >= 4:  # April onwards
        fiscal_year = f"FY {current_year}-{str(current_year + 1)[2:]}"
    else:  # January to March
        fiscal_year = f"FY {current_year - 1}-{str(current_year)[2:]}"
    
    # Add periods to context
    context.current_fiscal_year = fiscal_year
    context.current_month = current_month
    
    # Calculate statistics for number cards with current fiscal year filter
    if current_date.month >= 4:  # April onwards
        fy_start = f"{current_year}-04-01"
        fy_end = f"{current_year + 1}-03-31"
    else:  # January to March
        fy_start = f"{current_year - 1}-04-01"
        fy_end = f"{current_year}-03-31"
    
    # Query for total sales and invoice count (fiscal year)
    fy_stats_query = """
        SELECT
            SUM(total) AS total_sales,
            COUNT(name) AS invoice_count,
            COUNT(DISTINCT customer) AS customer_count
        FROM `tabSales Invoice`
        WHERE docstatus = 1 AND status NOT IN ('Cancelled', 'Return')
        AND posting_date BETWEEN %s AND %s
    """
    fy_sales_stats = frappe.db.sql(fy_stats_query, (fy_start, fy_end), as_dict=True)[0] or {}
    
    # Query for average sale value (current month)
    current_month_start = current_date.replace(day=1).strftime("%Y-%m-%d")
    current_month_end = current_date.strftime("%Y-%m-%d")
    
    month_stats_query = """
        SELECT
            SUM(total) AS month_total_sales,
            COUNT(name) AS month_invoice_count
        FROM `tabSales Invoice`
        WHERE docstatus = 1 AND status NOT IN ('Cancelled', 'Return')
        AND posting_date BETWEEN %s AND %s
    """
    month_sales_stats = frappe.db.sql(month_stats_query, (current_month_start, current_month_end), as_dict=True)[0] or {}

    # Calculate values
    total_sales = fy_sales_stats.get('total_sales') or 0
    invoice_count = fy_sales_stats.get('invoice_count') or 0
    customer_count = fy_sales_stats.get('customer_count') or 0
    
    month_total_sales = month_sales_stats.get('month_total_sales') or 0
    month_invoice_count = month_sales_stats.get('month_invoice_count') or 0
    avg_invoice_value = month_total_sales / month_invoice_count if month_invoice_count > 0 else 0

    # Add formatted stats to the context
    context.total_sales = f"₹{total_sales:,.0f}"
    context.invoice_count = f"{invoice_count:,}"
    context.customer_count = f"{customer_count:,}"
    context.avg_invoice_value = f"₹{avg_invoice_value:,.0f}"
    
    # Get detailed data for each cost center for modal display
    context.cost_center_details = get_cost_center_details(fy_start, fy_end, current_month_start, current_month_end)
    
    return context

def get_cost_center_details(fy_start, fy_end, month_start, month_end):
    """
    Get detailed statistics for each cost center to display in modal
    """
    # Query for fiscal year data by cost center
    fy_by_cost_center_query = """
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
        AND si.posting_date BETWEEN %s AND %s
        AND si.cost_center IS NOT NULL
        GROUP BY si.cost_center, cc.cost_center_name
        ORDER BY total_sales DESC
    """
    
    fy_by_cost_center = frappe.db.sql(fy_by_cost_center_query, (fy_start, fy_end), as_dict=True)
    
    # Query for current month data by cost center
    month_by_cost_center_query = """
        SELECT 
            si.cost_center,
            cc.cost_center_name,
            SUM(si.total) AS month_total_sales,
            COUNT(si.name) AS month_invoice_count
        FROM `tabSales Invoice` si
        LEFT JOIN `tabCost Center` cc ON si.cost_center = cc.name
        WHERE si.docstatus = 1 
        AND si.status NOT IN ('Cancelled', 'Return')
        AND si.posting_date BETWEEN %s AND %s
        AND si.cost_center IS NOT NULL
        GROUP BY si.cost_center, cc.cost_center_name
        ORDER BY month_total_sales DESC
    """
    
    month_by_cost_center = frappe.db.sql(month_by_cost_center_query, (month_start, month_end), as_dict=True)
    
    # Create a dictionary to combine the data
    cost_center_data = {}
    
    # Process fiscal year data
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
    
    # Process current month data
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
        
        # Calculate average invoice value for current month
        month_invoice_count = row.get('month_invoice_count', 0)
        month_total_sales = row.get('month_total_sales', 0)
        if month_invoice_count > 0:
            cost_center_data[cost_center]['avg_invoice_value'] = month_total_sales / month_invoice_count
    
    # Convert to list and format values
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

