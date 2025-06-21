import frappe

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
        filters={"is_stock_item": 1}
    )
    
    # Fetch item groups
    item_groups = frappe.get_all(
        "Item Group",
        fields=["name as value", "name as label"],
        filters={"is_group": 0}
    )
    
    # Add the lists to the context
    context.company_list = companies
    context.branch_list = branches
    context.item_list = items
    context.item_group_list = item_groups
    
    # Calculate statistics for number cards
    stats_query = """
        SELECT
            SUM(total) AS total_sales,
            COUNT(name) AS invoice_count,
            COUNT(DISTINCT customer) AS customer_count
        FROM `tabSales Invoice`
        WHERE docstatus = 1 AND status NOT IN ('Cancelled', 'Return')
    """
    sales_stats = frappe.db.sql(stats_query, as_dict=True)[0] or {}

    total_sales = sales_stats.get('total_sales') or 0
    invoice_count = sales_stats.get('invoice_count') or 0
    customer_count = sales_stats.get('customer_count') or 0
    avg_invoice_value = total_sales / invoice_count if invoice_count > 0 else 0

    # Add formatted stats to the context
    context.total_sales = f"₹{total_sales:,.0f}"
    context.invoice_count = f"{invoice_count:,}"
    context.customer_count = f"{customer_count:,}"
    context.avg_invoice_value = f"₹{avg_invoice_value:,.0f}"
    
    return context

