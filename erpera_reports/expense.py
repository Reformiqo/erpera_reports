import frappe
from frappe import _
from frappe import whitelist

EXPENSE_GROUPS = ("EXPENSE", "Expense", "Expenses", "Expenses Head")

def get_expense_stats(fy_from, fy_to, month_from, month_to, company=None, branch=None):
    """
    Returns a dict with total_expense, invoice_count, supplier_count, avg_invoice_value
    Only for item group 'EXPENSE'.
    """
    extra_pi = ""
    args = {'from_date': fy_from, 'to_date': fy_to, 'month_from': month_from, 'month_to': month_to}
    if company:
        extra_pi += " AND pi.company = %(company)s"
        args['company'] = company
    if branch:
        extra_pi += " AND pi.cost_center = %(branch)s"
        args['branch'] = branch
    expense_group_filter = f"pii.item_group IN {EXPENSE_GROUPS}"
    # Total expense (fiscal year or filtered)
    total_expense_query = f"""
        SELECT SUM(pii.amount) as total_amount
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
        LEFT JOIN `tabItem` i ON pii.item_code = i.name
        WHERE pi.docstatus = 1
        AND pi.status NOT IN ('Cancelled', 'Return')
        {extra_pi}
        AND {expense_group_filter}
    """
    total_expense_result = frappe.db.sql(total_expense_query, args, as_dict=True)[0] or {}
    total_expense = total_expense_result.get('total_amount') or 0

    # Total invoices (fiscal year or filtered)
    total_invoices_query = f"""
        SELECT COUNT(DISTINCT pi.name) as invoice_count
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
        LEFT JOIN `tabItem` i ON pii.item_code = i.name
        WHERE pi.docstatus = 1
        AND pi.status NOT IN ('Cancelled', 'Return')
        {extra_pi}
        AND {expense_group_filter}
    """
    total_invoices_result = frappe.db.sql(total_invoices_query, args, as_dict=True)[0] or {}
    total_invoices = total_invoices_result.get('invoice_count') or 0

    # Unique suppliers (fiscal year or filtered)
    unique_suppliers_query = f"""
        SELECT COUNT(DISTINCT pi.supplier) as supplier_count
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
        LEFT JOIN `tabItem` i ON pii.item_code = i.name
        WHERE pi.docstatus = 1
        AND pi.status NOT IN ('Cancelled', 'Return')
        {extra_pi}
        AND {expense_group_filter}
    """
    unique_suppliers_result = frappe.db.sql(unique_suppliers_query, args, as_dict=True)[0] or {}
    unique_suppliers = unique_suppliers_result.get('supplier_count') or 0

    # Average expense value (current month or filtered)
    avg_expense_query = f"""
        SELECT COALESCE(AVG(pi.grand_total), 0) as avg_amount
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
        LEFT JOIN `tabItem` i ON pii.item_code = i.name
        WHERE pi.docstatus = 1
        AND pi.status NOT IN ('Cancelled', 'Return')
        {extra_pi}
        AND {expense_group_filter}
    """
    avg_expense_result = frappe.db.sql(avg_expense_query, args, as_dict=True)[0] or {}
    avg_expense = avg_expense_result.get('avg_amount') or 0

    return {
        'total_expense': f"₹{total_expense:,.0f}",
        'invoice_count': f"{total_invoices:,}",
        'supplier_count': f"{unique_suppliers:,}",
        'avg_invoice_value': f"₹{avg_expense:,.0f}"
    }

def get_cost_center_expense_details(fy_start, fy_end, month_start, month_end, company=None, branch=None):
    """
    Returns a list of dicts for each cost center with stats for only item group 'EXPENSE'.
    """
    extra_pi = ""
    args = {'fy_start': fy_start, 'fy_end': fy_end, 'month_start': month_start, 'month_end': month_end}
    if company:
        extra_pi += " AND pi.company = %(company)s"
        args['company'] = company
    if branch:
        extra_pi += " AND pi.cost_center = %(branch)s"
        args['branch'] = branch
    expense_group_filter = f"pii.item_group IN {EXPENSE_GROUPS}"
    # Fiscal year data by cost center
    fy_by_cost_center_query = f"""
        SELECT 
            pi.cost_center,
            cc.cost_center_name,
            SUM(pii.amount) AS total_expense,
            COUNT(DISTINCT pi.name) AS invoice_count,
            COUNT(DISTINCT pi.supplier) AS supplier_count
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
        LEFT JOIN `tabItem` i ON pii.item_code = i.name
        LEFT JOIN `tabCost Center` cc ON pi.cost_center = cc.name
        WHERE pi.docstatus = 1 
        AND pi.status NOT IN ('Cancelled', 'Return')
        {extra_pi}
        AND {expense_group_filter}
        GROUP BY pi.cost_center, cc.cost_center_name
        ORDER BY total_expense DESC
    """
    fy_by_cost_center = frappe.db.sql(fy_by_cost_center_query, args, as_dict=True)
    # Current month data by cost center
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
        {extra_pi}
        AND {expense_group_filter}
        GROUP BY pi.cost_center, cc.cost_center_name
        ORDER BY avg_invoice_value DESC
    """
    month_by_cost_center = frappe.db.sql(month_by_cost_center_query, args, as_dict=True)
    # Combine data
    cost_center_data = {}
    for row in fy_by_cost_center:
        cost_center = row.get('cost_center', 'Unknown')
        cost_center_data[cost_center] = {
            'name': cost_center,
            'display_name': row.get('cost_center_name', cost_center),
            'total_expense': row.get('total_expense', 0),
            'invoice_count': row.get('invoice_count', 0),
            'supplier_count': row.get('supplier_count', 0),
            'avg_invoice_value': 0
        }
    for row in month_by_cost_center:
        cost_center = row.get('cost_center', 'Unknown')
        if cost_center not in cost_center_data:
            cost_center_data[cost_center] = {
                'name': cost_center,
                'display_name': row.get('cost_center_name', cost_center),
                'total_expense': 0,
                'invoice_count': 0,
                'supplier_count': 0,
                'avg_invoice_value': 0
            }
        cost_center_data[cost_center]['avg_invoice_value'] = row.get('avg_invoice_value', 0)
    result = []
    for cost_center, data in cost_center_data.items():
        result.append({
            'name': data['name'],
            'display_name': data['display_name'],
            'total_expense': f"₹{data['total_expense']:,.0f}",
            'invoice_count': f"{data['invoice_count']:,}",
            'supplier_count': f"{data['supplier_count']:,}",
            'avg_invoice_value': f"₹{data['avg_invoice_value']:,.0f}"
        })
    return result

@frappe.whitelist()
def get_expense_by_branch(filters=None):
    """
    Returns expense totals by branch for item group 'EXPENSE'.
    """
    if isinstance(filters, str):
        import json
        filters = json.loads(filters)
    filters = filters or {}
    args = {}
    where = ["1=1", f"pii.item_group IN {EXPENSE_GROUPS}"]
    if filters.get('from_date'):
        where.append("pi.posting_date >= %(from_date)s")
        args['from_date'] = filters['from_date']
    if filters.get('to_date'):
        where.append("pi.posting_date <= %(to_date)s")
        args['to_date'] = filters['to_date']
    if filters.get('company'):
        where.append("pi.company = %(company)s")
        args['company'] = filters['company']
    if filters.get('branch'):
        where.append("pi.cost_center = %(branch)s")
        args['branch'] = filters['branch']
    sql = f"""
        SELECT pi.cost_center, cc.cost_center_name, SUM(pii.amount) as total
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
        LEFT JOIN `tabCost Center` cc ON pi.cost_center = cc.name
        WHERE pi.docstatus = 1 AND pi.status NOT IN ('Cancelled', 'Return') AND {' AND '.join(where)}
        GROUP BY pi.cost_center, cc.cost_center_name
        ORDER BY total DESC
    """
    rows = frappe.db.sql(sql, args, as_dict=True)
    labels = [row['cost_center_name'] or row['cost_center'] for row in rows]
    data = [row['total'] for row in rows]
    return {
        'labels': labels,
        'data': data,
        'datasets': None
    }

@frappe.whitelist()
def get_expense_by_company(filters=None):
    """
    Returns expense totals by company for item group 'EXPENSE'.
    """
    if isinstance(filters, str):
        import json
        filters = json.loads(filters)
    filters = filters or {}
    args = {}
    where = ["1=1", f"pii.item_group IN {EXPENSE_GROUPS}"]
    if filters.get('from_date'):
        where.append("pi.posting_date >= %(from_date)s")
        args['from_date'] = filters['from_date']
    if filters.get('to_date'):
        where.append("pi.posting_date <= %(to_date)s")
        args['to_date'] = filters['to_date']
    if filters.get('company'):
        where.append("pi.company = %(company)s")
        args['company'] = filters['company']
    sql = f"""
        SELECT pi.company, SUM(pii.amount) as total
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
        WHERE pi.docstatus = 1 AND pi.status NOT IN ('Cancelled', 'Return') AND {' AND '.join(where)}
        GROUP BY pi.company
        ORDER BY total DESC
    """
    rows = frappe.db.sql(sql, args, as_dict=True)
    labels = [row['company'] for row in rows]
    data = [row['total'] for row in rows]
    return {
        'labels': labels,
        'data': data,
        'datasets': None
    }

@frappe.whitelist()
def get_expense_summary(filters=None):
    """
    Returns expense summary by expense head (item group = 'EXPENSE') for the given filters.
    """
    if isinstance(filters, str):
        import json
        filters = json.loads(filters)
    filters = filters or {}
    args = {}
    where = ["1=1", f"pii.item_group IN {EXPENSE_GROUPS}"]
    if filters.get('from_date'):
        where.append("pi.posting_date >= %(from_date)s")
        args['from_date'] = filters['from_date']
    if filters.get('to_date'):
        where.append("pi.posting_date <= %(to_date)s")
        args['to_date'] = filters['to_date']
    if filters.get('company'):
        where.append("pi.company = %(company)s")
        args['company'] = filters['company']
    if filters.get('branch'):
        where.append("pi.cost_center = %(branch)s")
        args['branch'] = filters['branch']
    sql = f"""
        SELECT pii.item_group, SUM(pii.amount) as total
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
        WHERE pi.docstatus = 1 AND pi.status NOT IN ('Cancelled', 'Return') AND {' AND '.join(where)}
        GROUP BY pii.item_group
        ORDER BY total DESC
    """
    rows = frappe.db.sql(sql, args, as_dict=True)
    labels = [row['item_group'] for row in rows]
    data = [row['total'] for row in rows]
    return {
        'labels': labels,
        'data': data,
        'datasets': None
    }
