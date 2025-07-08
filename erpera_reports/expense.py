import frappe
from frappe import _
from frappe import whitelist

EXPENSE_GROUPS = ("EXPENSE", "Expense", "Expenses", "Expenses Head")

def get_expense_stats(fy_from=None, fy_to=None, month_from=None, month_to=None, company=None, branch=None):
    """
    Returns a dict with total_expense, total_salaries, total_rents, total_electric_bill
    Based on GL Entry for expense accounts.
    """
    args = {'from_date': fy_from, 'to_date': fy_to, 'month_from': month_from, 'month_to': month_to}
    
    # Build WHERE conditions
    where_conditions = [ "acc.account_type = 'Expense'",
        "gle.debit > 0"]
    if fy_from:
        where_conditions.append("gle.posting_date BETWEEN %(from_date)s AND %(to_date)s")
        args['from_date'] = fy_from
        args['to_date'] = fy_to
    if month_from:
        where_conditions.append("gle.posting_date BETWEEN %(month_from)s AND %(month_to)s")
        args['month_from'] = month_from
        args['month_to'] = month_to
        
    if company:
        where_conditions.append("gle.company = %(company)s")
        args['company'] = company
    if branch:
        where_conditions.append("gle.cost_center = %(branch)s")
        args['branch'] = branch

    where_clause = " AND ".join(where_conditions)

    # Total Expense (all expense accounts)
    total_expense_query = """
        SELECT SUM(gle.debit) as total_amount
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON gle.account = acc.name
        WHERE """ + where_clause
    
    total_expense_result = frappe.db.sql(total_expense_query, args, as_dict=True)[0] or {}
    total_expense = total_expense_result.get('total_amount') or 0

    # Total Salaries (accounts containing 'salary' or 'payroll')
    salary_conditions = [
        "LOWER(acc.account_name) LIKE '%salary%'",
        "LOWER(acc.account_name) LIKE '%payroll%'",
        "LOWER(acc.account_name) LIKE '%wage%'",
        "LOWER(acc.account_name) LIKE '%compensation%'"
    ]
    salary_where = where_clause + " AND (" + " OR ".join(salary_conditions) + ")"
    
    total_salaries_query = """
        SELECT SUM(gle.debit) as total_amount
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON gle.account = acc.name
        WHERE """ + salary_where
    
    total_salaries_result = frappe.db.sql(total_salaries_query, args, as_dict=True)[0] or {}
    total_salaries = total_salaries_result.get('total_amount') or 0

    # Total Rents (accounts containing 'rent')
    rent_conditions = [
        "LOWER(acc.account_name) LIKE '%rent%'",
        "LOWER(acc.account_name) LIKE '%lease%'",
        "LOWER(acc.account_name) LIKE '%premises%'"
    ]
    rent_where = where_clause + " AND (" + " OR ".join(rent_conditions) + ")"
    
    total_rents_query = """
        SELECT SUM(gle.debit) as total_amount
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON gle.account = acc.name
        WHERE """ + rent_where
    
    total_rents_result = frappe.db.sql(total_rents_query, args, as_dict=True)[0] or {}
    total_rents = total_rents_result.get('total_amount') or 0

    # Total Electric Bill (accounts containing 'electric' or 'power')
    electric_conditions = [
        "LOWER(acc.account_name) LIKE '%electric%'",
        "LOWER(acc.account_name) LIKE '%power%'",
        "LOWER(acc.account_name) LIKE '%electricity%'",
        "LOWER(acc.account_name) LIKE '%utility%'"
    ]
    electric_where = where_clause + " AND (" + " OR ".join(electric_conditions) + ")"
    
    total_electric_bill_query = """
        SELECT SUM(gle.debit) as total_amount
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON gle.account = acc.name
        WHERE """ + electric_where
    
    total_electric_bill_result = frappe.db.sql(total_electric_bill_query, args, as_dict=True)[0] or {}
    total_electric_bill = total_electric_bill_result.get('total_amount') or 0

    return {
        'total_expense': f"₹{total_expense:,.0f}",
        'total_salaries': f"₹{total_salaries:,.0f}",
        'total_rents': f"₹{total_rents:,.0f}",
        'total_electric_bill': f"₹{total_electric_bill:,.0f}"
    }

def get_cost_center_expense_details(fy_start, fy_end, month_start, month_end, company=None, branch=None):
    """
    Returns a list of dicts for each cost center with stats based on GL Entry for expense accounts.
    """
    args = {'fy_start': fy_start, 'fy_end': fy_end, 'month_start': month_start, 'month_end': month_end}
    
    # Build WHERE conditions
    where_conditions = [
        "gle.posting_date BETWEEN %(fy_start)s AND %(fy_end)s",
        "acc.account_type = 'Expense'",
        "gle.debit > 0"
    ]
    
    if company:
        where_conditions.append("gle.company = %(company)s")
        args['company'] = company
    if branch:
        where_conditions.append("gle.cost_center = %(branch)s")
        args['branch'] = branch

    where_clause = " AND ".join(where_conditions)

    # Total Expense by cost center
    total_expense_query = """
        SELECT 
            gle.cost_center,
            cc.cost_center_name,
            SUM(gle.debit) AS total_expense
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON gle.account = acc.name
        LEFT JOIN `tabCost Center` cc ON gle.cost_center = cc.name
        WHERE """ + where_clause + """
        GROUP BY gle.cost_center, cc.cost_center_name
        ORDER BY total_expense DESC
    """
    total_expense_by_cost_center = frappe.db.sql(total_expense_query, args, as_dict=True)

    # Total Salaries by cost center
    salary_conditions = [
        "LOWER(acc.account_name) LIKE '%salary%'",
        "LOWER(acc.account_name) LIKE '%payroll%'",
        "LOWER(acc.account_name) LIKE '%wage%'",
        "LOWER(acc.account_name) LIKE '%compensation%'"
    ]
    salary_where = where_clause + " AND (" + " OR ".join(salary_conditions) + ")"
    
    total_salaries_query = """
        SELECT 
            gle.cost_center,
            cc.cost_center_name,
            SUM(gle.debit) AS total_salaries
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON gle.account = acc.name
        LEFT JOIN `tabCost Center` cc ON gle.cost_center = cc.name
        WHERE """ + salary_where + """
        GROUP BY gle.cost_center, cc.cost_center_name
        ORDER BY total_salaries DESC
    """
    total_salaries_by_cost_center = frappe.db.sql(total_salaries_query, args, as_dict=True)

    # Total Rents by cost center
    rent_conditions = [
        "LOWER(acc.account_name) LIKE '%rent%'",
        "LOWER(acc.account_name) LIKE '%lease%'",
        "LOWER(acc.account_name) LIKE '%premises%'"
    ]
    rent_where = where_clause + " AND (" + " OR ".join(rent_conditions) + ")"
    
    total_rents_query = """
        SELECT 
            gle.cost_center,
            cc.cost_center_name,
            SUM(gle.debit) AS total_rents
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON gle.account = acc.name
        LEFT JOIN `tabCost Center` cc ON gle.cost_center = cc.name
        WHERE """ + rent_where + """
        GROUP BY gle.cost_center, cc.cost_center_name
        ORDER BY total_rents DESC
    """
    total_rents_by_cost_center = frappe.db.sql(total_rents_query, args, as_dict=True)

    # Total Electric Bill by cost center
    electric_conditions = [
        "LOWER(acc.account_name) LIKE '%electric%'",
        "LOWER(acc.account_name) LIKE '%power%'",
        "LOWER(acc.account_name) LIKE '%electricity%'",
        "LOWER(acc.account_name) LIKE '%utility%'"
    ]
    electric_where = where_clause + " AND (" + " OR ".join(electric_conditions) + ")"
    
    total_electric_bill_query = """
        SELECT 
            gle.cost_center,
            cc.cost_center_name,
            SUM(gle.debit) AS total_electric_bill
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON gle.account = acc.name
        LEFT JOIN `tabCost Center` cc ON gle.cost_center = cc.name
        WHERE """ + electric_where + """
        GROUP BY gle.cost_center, cc.cost_center_name
        ORDER BY total_electric_bill DESC
    """
    total_electric_bill_by_cost_center = frappe.db.sql(total_electric_bill_query, args, as_dict=True)

    # Combine data
    cost_center_data = {}
    
    # Process total expense data
    for row in total_expense_by_cost_center:
        cost_center = row.get('cost_center', 'Unknown')
        cost_center_data[cost_center] = {
            'name': cost_center,
            'display_name': row.get('cost_center_name', cost_center),
            'total_expense': row.get('total_expense', 0),
            'total_salaries': 0,
            'total_rents': 0,
            'total_electric_bill': 0
        }
    
    # Process total salaries data
    for row in total_salaries_by_cost_center:
        cost_center = row.get('cost_center', 'Unknown')
        if cost_center not in cost_center_data:
            cost_center_data[cost_center] = {
                'name': cost_center,
                'display_name': row.get('cost_center_name', cost_center),
                'total_expense': 0,
                'total_salaries': 0,
                'total_rents': 0,
                'total_electric_bill': 0
            }
        cost_center_data[cost_center]['total_salaries'] = row.get('total_salaries', 0)
    
    # Process total rents data
    for row in total_rents_by_cost_center:
        cost_center = row.get('cost_center', 'Unknown')
        if cost_center not in cost_center_data:
            cost_center_data[cost_center] = {
                'name': cost_center,
                'display_name': row.get('cost_center_name', cost_center),
                'total_expense': 0,
                'total_salaries': 0,
                'total_rents': 0,
                'total_electric_bill': 0
            }
        cost_center_data[cost_center]['total_rents'] = row.get('total_rents', 0)
    
    # Process total electric bill data
    for row in total_electric_bill_by_cost_center:
        cost_center = row.get('cost_center', 'Unknown')
        if cost_center not in cost_center_data:
            cost_center_data[cost_center] = {
                'name': cost_center,
                'display_name': row.get('cost_center_name', cost_center),
                'total_expense': 0,
                'total_salaries': 0,
                'total_rents': 0,
                'total_electric_bill': 0
            }
        cost_center_data[cost_center]['total_electric_bill'] = row.get('total_electric_bill', 0)

    result = []
    for cost_center, data in cost_center_data.items():
        result.append({
            'name': data['name'],
            'display_name': data['display_name'],
            'total_expense': f"₹{data['total_expense']:,.0f}",
            'total_salaries': f"₹{data['total_salaries']:,.0f}",
            'total_rents': f"₹{data['total_rents']:,.0f}",
            'total_electric_bill': f"₹{data['total_electric_bill']:,.0f}"
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
    where = []
    args = {}
    if filters.get('from_date'):
        where.append("gl.posting_date >= %(from_date)s")
        args['from_date'] = filters['from_date']
    if filters.get('to_date'):
        where.append("gl.posting_date <= %(to_date)s")
        args['to_date'] = filters['to_date']
    if filters.get('company'):
        where.append("gl.company = %(company)s")
        args['company'] = filters['company']
    if filters.get('branch'):
        where.append("gl.cost_center = %(branch)s")
        args['branch'] = filters['branch']
    accounts = frappe.db.get_list('Account', {'account_name': ['like', '%electric%', '%rent%', '%salary%', '%expense%']}, pluck='name')
    for account in accounts:
        where.append("gl.account = %(account)s")
        args['account'] = account
    sql = f"""
        SELECT gl.cost_center, cc.cost_center_name, SUM(gl.debit) as total
        FROM `tabGL Entry` gl
        INNER JOIN `tabAccount` acc ON gl.account = acc.name
        LEFT JOIN `tabCost Center` cc ON gl.cost_center = cc.name
        WHERE {' AND '.join(where)}
        GROUP BY gl.cost_center, cc.cost_center_name
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
    where = []
    if filters.get('from_date'):
        where.append("gl.posting_date >= %(from_date)s")
        args['from_date'] = filters['from_date']
    if filters.get('to_date'):
        where.append("gl.posting_date <= %(to_date)s")
        args['to_date'] = filters['to_date']
    if filters.get('company'):
        where.append("gl.company = %(company)s")
        args['company'] = filters['company']
    accounts = frappe.db.get_list('Account', {'account_name': ['like', '%electric%', '%rent%', '%salary%', '%expense%']}, pluck='name')
    for account in accounts:
        where.append("gl.account = %(account)s")
        args['account'] = account
    sql = f"""
        SELECT gl.company, SUM(gl.debit) as total
        FROM `tabGL Entry` gl
        INNER JOIN `tabAccount` acc ON gl.account = acc.name
        WHERE {' AND '.join(where)}
        GROUP BY gl.company
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
    where = []
    if filters.get('from_date'):
        where.append("gl.posting_date >= %(from_date)s")
        args['from_date'] = filters['from_date']
    if filters.get('to_date'):
        where.append("gl.posting_date <= %(to_date)s")
        args['to_date'] = filters['to_date']
    if filters.get('company'):
        where.append("gl.company = %(company)s")
        args['company'] = filters['company']
    if filters.get('branch'):
        where.append("gl.cost_center = %(branch)s")
        args['branch'] = filters['branch']
    accounts = frappe.db.get_list('Account', {'account_name': ['like', '%electric%', '%rent%', '%salary%', '%expense%']}, pluck='name')
    for account in accounts:
        where.append("gl.account = %(account)s")
        args['account'] = account
    sql = f"""
        SELECT acc.account_name, SUM(gl.debit) as total
        FROM `tabGL Entry` gl
        INNER JOIN `tabAccount` acc ON gl.account = acc.name
        WHERE {' AND '.join(where)}
        GROUP BY acc.account_name
        ORDER BY total DESC
    """
    rows = frappe.db.sql(sql, args, as_dict=True)
    labels = [row['account_name'] for row in rows]
    data = [row['total'] for row in rows]
    return {
        'labels': labels,
        'data': data,
        'datasets': None
    }

@frappe.whitelist()
def get_consolidated_expense(filters=None):
    """
    Returns consolidated expense data across all companies and branches.
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
        SELECT 
            CASE 
                WHEN pi.cost_center IS NOT NULL AND pi.cost_center != '' 
                THEN CONCAT(COALESCE(pi.company, 'Unknown'), ' - ', pi.cost_center)
                ELSE COALESCE(pi.company, 'Unknown Company')
            END AS entity_name,
            SUM(pii.amount) as total
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
        WHERE pi.docstatus = 1 AND pi.status NOT IN ('Cancelled', 'Return') AND {' AND '.join(where)}
        GROUP BY entity_name
        ORDER BY total DESC
    """
    rows = frappe.db.sql(sql, args, as_dict=True)
    labels = [row['entity_name'] for row in rows]
    data = [row['total'] for row in rows]
    return {
        'labels': labels,
        'data': data,
        'datasets': None
    }

@frappe.whitelist()
def get_entity_wise_expense(filters=None):
    """
    Returns expense data by entity (company-branch combination).
    """
    return get_consolidated_expense(filters)

@frappe.whitelist()
def get_consolidated_expiry_expense(filters=None):
    """
    Returns consolidated expiry expense data.
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
        SELECT 
            CASE 
                WHEN pi.cost_center IS NOT NULL AND pi.cost_center != '' 
                THEN CONCAT(COALESCE(pi.company, 'Unknown'), ' - ', pi.cost_center)
                ELSE COALESCE(pi.company, 'Unknown Company')
            END AS entity_name,
            SUM(pii.amount) as total
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
        WHERE pi.docstatus = 1 AND pi.status NOT IN ('Cancelled', 'Return') AND {' AND '.join(where)}
        GROUP BY entity_name
        ORDER BY total DESC
    """
    rows = frappe.db.sql(sql, args, as_dict=True)
    labels = [row['entity_name'] for row in rows]
    data = [row['total'] for row in rows]
    return {
        'labels': labels,
        'data': data,
        'datasets': None
    }

@frappe.whitelist()
def get_branch_wise_expiry_expense(filters=None):
    """
    Returns branch-wise expiry expense data.
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
def get_company_wise_expiry_expense(filters=None):
    """
    Returns company-wise expiry expense data.
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
def get_expiry_expense_summary(filters=None):
    """
    Returns expiry expense summary data.
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

@frappe.whitelist()
def get_expiry_demand_comparison(filters=None):
    """
    Returns expiry vs demand comparison data.
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

@frappe.whitelist()
def get_consolidated_expired_items(filters=None):
    """
    Returns consolidated expired items data.
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
        SELECT 
            CASE 
                WHEN pi.cost_center IS NOT NULL AND pi.cost_center != '' 
                THEN CONCAT(COALESCE(pi.company, 'Unknown'), ' - ', pi.cost_center)
                ELSE COALESCE(pi.company, 'Unknown Company')
            END AS entity_name,
            SUM(pii.amount) as total
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
        WHERE pi.docstatus = 1 AND pi.status NOT IN ('Cancelled', 'Return') AND {' AND '.join(where)}
        GROUP BY entity_name
        ORDER BY total DESC
    """
    rows = frappe.db.sql(sql, args, as_dict=True)
    labels = [row['entity_name'] for row in rows]
    data = [row['total'] for row in rows]
    return {
        'labels': labels,
        'data': data,
        'datasets': None
    }

@frappe.whitelist()
def get_branch_wise_in_out_quantity(filters=None):
    """
    Returns branch-wise in/out quantity data.
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
def get_company_wise_in_out_quantity(filters=None):
    """
    Returns company-wise in/out quantity data.
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
def get_consolidate_in_out_quantity(filters=None):
    """
    Returns consolidated in/out quantity data.
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
        SELECT 
            CASE 
                WHEN pi.cost_center IS NOT NULL AND pi.cost_center != '' 
                THEN CONCAT(COALESCE(pi.company, 'Unknown'), ' - ', pi.cost_center)
                ELSE COALESCE(pi.company, 'Unknown Company')
            END AS entity_name,
            SUM(pii.amount) as total
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
        WHERE pi.docstatus = 1 AND pi.status NOT IN ('Cancelled', 'Return') AND {' AND '.join(where)}
        GROUP BY entity_name
        ORDER BY total DESC
    """
    rows = frappe.db.sql(sql, args, as_dict=True)
    labels = [row['entity_name'] for row in rows]
    data = [row['total'] for row in rows]
    return {
        'labels': labels,
        'data': data,
        'datasets': None
    }
