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
    
    return context

