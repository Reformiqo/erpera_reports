import frappe
from datetime import datetime

def get_context(context):
    """
    Get context for the stock reports page.
    This function fetches data for the filter dropdowns and number card statistics.
    Now uses filters from frappe.request.args.get for from_date, to_date, company, warehouse.
    """
    context.active_page = "stock"
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
    context.company_list = companies
    context.warehouse_list = warehouses
    context.item_list = items
    context.item_group_list = item_groups

    # Get filters from URL args
    args = frappe.request.args
    from_date = args.get('from_date')
    to_date = args.get('to_date')
    company = args.get('company')
    warehouse = args.get('warehouse')

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
    # For most cards, default to fiscal year; for low stock, default to current month
    filter_from = from_date or fy_start
    filter_to = to_date or fy_end
    filter_month_from = from_date or current_date.replace(day=1).strftime("%Y-%m-%d")
    filter_month_to = to_date or current_date.strftime("%Y-%m-%d")

    # Build extra conditions for company/warehouse
    extra_item = ""
    extra_sle = ""
    extra_args = {}
    if company:
        extra_item += " AND item.company = %(company)s"
        extra_sle += " AND sle.company = %(company)s"
        extra_args['company'] = company
    if warehouse:
        extra_item += " AND sle.warehouse = %(warehouse)s"
        extra_sle += " AND sle.warehouse = %(warehouse)s"
        extra_args['warehouse'] = warehouse

    # Total items
    total_items_query = f"""
        SELECT COUNT(DISTINCT sle.item_code) as item_count
        FROM `tabStock Ledger Entry` sle
        INNER JOIN `tabItem` item ON sle.item_code = item.name
        WHERE item.is_stock_item = 1
        AND sle.posting_date BETWEEN %(from_date)s AND %(to_date)s
        {extra_item}
    """
    total_items_result = frappe.db.sql(total_items_query, dict(from_date=filter_from, to_date=filter_to, **extra_args), as_dict=True)[0] or {}
    total_items = total_items_result.get('item_count') or 0

    # Total warehouses
    total_warehouses_query = f"""
        SELECT COUNT(DISTINCT sle.warehouse) as warehouse_count
        FROM `tabStock Ledger Entry` sle
        WHERE sle.posting_date BETWEEN %(from_date)s AND %(to_date)s
        AND sle.warehouse IS NOT NULL
        {extra_sle}
    """
    total_warehouses_result = frappe.db.sql(total_warehouses_query, dict(from_date=filter_from, to_date=filter_to, **extra_args), as_dict=True)[0] or {}
    total_warehouses = total_warehouses_result.get('warehouse_count') or 0

    # Total stock value
    stock_value_query = f"""
        SELECT SUM(sle.actual_qty * sle.valuation_rate) as total_value
        FROM `tabStock Ledger Entry` sle
        INNER JOIN `tabItem` item ON sle.item_code = item.name
        WHERE item.is_stock_item = 1
        AND sle.posting_date BETWEEN %(from_date)s AND %(to_date)s
        AND sle.actual_qty > 0
        {extra_item}
    """
    stock_value_result = frappe.db.sql(stock_value_query, dict(from_date=filter_from, to_date=filter_to, **extra_args), as_dict=True)[0] or {}
    total_stock_value = stock_value_result.get('total_value') or 0

    # Low stock items (current month or filtered)
    low_stock_query = f"""
        SELECT COUNT(DISTINCT item.name) as low_stock_count
        FROM `tabItem` item
        LEFT JOIN (
            SELECT item_code, SUM(actual_qty) as current_stock
            FROM `tabStock Ledger Entry`
            WHERE posting_date BETWEEN %(from_date)s AND %(to_date)s
            GROUP BY item_code
        ) stock ON item.name = stock.item_code
        WHERE item.is_stock_item = 1
        AND (stock.current_stock IS NULL OR stock.current_stock <= item.safety_stock)
        AND item.safety_stock > 0
        {extra_item}
    """
    low_stock_result = frappe.db.sql(low_stock_query, dict(from_date=filter_month_from, to_date=filter_month_to, **extra_args), as_dict=True)[0] or {}
    low_stock_items = low_stock_result.get('low_stock_count') or 0

    context.total_items = f"{total_items:,}"
    context.total_warehouses = f"{total_warehouses:,}"
    context.total_stock_value = f"₹{total_stock_value:,.0f}"
    context.low_stock_items = f"{low_stock_items:,}"

    # Get detailed data for each warehouse for modal display, using filters
    context.warehouse_details = get_warehouse_details(filter_from, filter_to, filter_month_from, filter_month_to, company, warehouse)
    return context

def get_warehouse_details(fy_start, fy_end, month_start, month_end, company=None, warehouse=None):
    """
    Get detailed statistics for each warehouse to display in modal, using filters if provided
    """
    extra_sle = ""
    extra_item = ""
    args = {'fy_start': fy_start, 'fy_end': fy_end, 'month_start': month_start, 'month_end': month_end}
    if company:
        extra_item += " AND item.company = %(company)s"
        extra_sle += " AND sle.company = %(company)s"
        args['company'] = company
    if warehouse:
        extra_item += " AND sle.warehouse = %(warehouse)s"
        extra_sle += " AND sle.warehouse = %(warehouse)s"
        args['warehouse'] = warehouse
    # Fiscal year data by warehouse
    fy_by_warehouse_query = f"""
        SELECT 
            sle.warehouse,
            w.warehouse_name,
            COUNT(DISTINCT sle.item_code) AS total_items,
            COUNT(DISTINCT sle.warehouse) AS total_warehouses,
            SUM(sle.actual_qty * sle.valuation_rate) AS total_stock_value
        FROM `tabStock Ledger Entry` sle
        INNER JOIN `tabItem` item ON sle.item_code = item.name
        LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name
        WHERE item.is_stock_item = 1 
        AND sle.posting_date BETWEEN %(fy_start)s AND %(fy_end)s
        AND sle.warehouse IS NOT NULL
        {extra_item}
        GROUP BY sle.warehouse, w.warehouse_name
        ORDER BY total_stock_value DESC
    """
    fy_by_warehouse = frappe.db.sql(fy_by_warehouse_query, args, as_dict=True)
    # Current month low stock data by warehouse
    month_by_warehouse_query = f"""
        SELECT 
            sle.warehouse,
            w.warehouse_name,
            COUNT(DISTINCT CASE 
                WHEN (stock.current_stock IS NULL OR stock.current_stock <= item.safety_stock) 
                AND item.safety_stock > 0 
                THEN item.name 
            END) AS low_stock_items
        FROM `tabStock Ledger Entry` sle
        INNER JOIN `tabItem` item ON sle.item_code = item.name
        LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name
        LEFT JOIN (
            SELECT item_code, warehouse, SUM(actual_qty) as current_stock
            FROM `tabStock Ledger Entry`
            WHERE posting_date BETWEEN %(month_start)s AND %(month_end)s
            GROUP BY item_code, warehouse
        ) stock ON item.name = stock.item_code AND sle.warehouse = stock.warehouse
        WHERE item.is_stock_item = 1 
        AND sle.posting_date BETWEEN %(month_start)s AND %(month_end)s
        AND sle.warehouse IS NOT NULL
        {extra_item}
        GROUP BY sle.warehouse, w.warehouse_name
        ORDER BY low_stock_items DESC
    """
    month_by_warehouse = frappe.db.sql(month_by_warehouse_query, args, as_dict=True)
    warehouse_data = {}
    for row in fy_by_warehouse:
        warehouse = row.get('warehouse', 'Unknown')
        warehouse_data[warehouse] = {
            'name': warehouse,
            'display_name': row.get('warehouse_name', warehouse),
            'total_items': row.get('total_items', 0),
            'total_warehouses': row.get('total_warehouses', 0),
            'total_stock_value': row.get('total_stock_value', 0),
            'low_stock_items': 0
        }
    for row in month_by_warehouse:
        warehouse = row.get('warehouse', 'Unknown')
        if warehouse not in warehouse_data:
            warehouse_data[warehouse] = {
                'name': warehouse,
                'display_name': row.get('warehouse_name', warehouse),
                'total_items': 0,
                'total_warehouses': 0,
                'total_stock_value': 0,
                'low_stock_items': 0
            }
        warehouse_data[warehouse]['low_stock_items'] = row.get('low_stock_items', 0)
    result = []
    for warehouse, data in warehouse_data.items():
        result.append({
            'name': data['name'],
            'display_name': data['display_name'],
            'total_items': f"{data['total_items']:,}",
            'total_warehouses': f"{data['total_warehouses']:,}",
            'total_stock_value': f"₹{data['total_stock_value']:,.0f}",
            'low_stock_items': f"{data['low_stock_items']:,}"
        })
    return result