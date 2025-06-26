import frappe
from datetime import datetime

def get_context(context):
    """
    Get context for the stock reports page.
    This function fetches data for the filter dropdowns and number card statistics.
    """
    
    # Fetch companies
    companies = frappe.get_all(
        "Company",
        fields=["name as value", "company_name as label"],
        filters={"is_group": 0}
    )
    
    # Fetch warehouses
    warehouses = frappe.get_all(
        "Warehouse",
        fields=["name as value", "warehouse_name as label"],
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
    context.warehouse_list = warehouses
    context.item_list = items
    context.item_group_list = item_groups
    
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
    # Total items (current fiscal year data)
    total_items_query = """
        SELECT COUNT(DISTINCT sle.item_code) as item_count
        FROM `tabStock Ledger Entry` sle
        INNER JOIN `tabItem` item ON sle.item_code = item.name
        WHERE item.is_stock_item = 1 
        AND sle.posting_date BETWEEN %s AND %s
    """
    total_items_result = frappe.db.sql(total_items_query, (fy_start, fy_end), as_dict=True)[0] or {}
    total_items = total_items_result.get('item_count') or 0
    
    # Total warehouses (active in current fiscal year)
    total_warehouses_query = """
        SELECT COUNT(DISTINCT sle.warehouse) as warehouse_count
        FROM `tabStock Ledger Entry` sle
        WHERE sle.posting_date BETWEEN %s AND %s
        AND sle.warehouse IS NOT NULL
    """
    total_warehouses_result = frappe.db.sql(total_warehouses_query, (fy_start, fy_end), as_dict=True)[0] or {}
    total_warehouses = total_warehouses_result.get('warehouse_count') or 0
    
    # Total stock value (current fiscal year transactions)
    stock_value_query = """
        SELECT SUM(sle.actual_qty * sle.valuation_rate) as total_value
        FROM `tabStock Ledger Entry` sle
        INNER JOIN `tabItem` item ON sle.item_code = item.name
        WHERE item.is_stock_item = 1 
        AND sle.posting_date BETWEEN %s AND %s
        AND sle.actual_qty > 0
    """
    stock_value_result = frappe.db.sql(stock_value_query, (fy_start, fy_end), as_dict=True)[0] or {}
    total_stock_value = stock_value_result.get('total_value') or 0
    
    # Low stock items (current month data)
    current_month_start = current_date.replace(day=1).strftime("%Y-%m-%d")
    current_month_end = current_date.strftime("%Y-%m-%d")
    
    low_stock_query = """
        SELECT COUNT(DISTINCT item.name) as low_stock_count
        FROM `tabItem` item
        LEFT JOIN (
            SELECT item_code, SUM(actual_qty) as current_stock
            FROM `tabStock Ledger Entry`
            WHERE posting_date BETWEEN %s AND %s
            GROUP BY item_code
        ) stock ON item.name = stock.item_code
        WHERE item.is_stock_item = 1 
        AND (stock.current_stock IS NULL OR stock.current_stock <= item.safety_stock)
        AND item.safety_stock > 0
    """
    low_stock_result = frappe.db.sql(low_stock_query, (current_month_start, current_month_end), as_dict=True)[0] or {}
    low_stock_items = low_stock_result.get('low_stock_count') or 0

    # Add formatted stats to the context
    context.total_items = f"{total_items:,}"
    context.total_warehouses = f"{total_warehouses:,}"
    context.total_stock_value = f"₹{total_stock_value:,.0f}"
    context.low_stock_items = f"{low_stock_items:,}"
    
    return context