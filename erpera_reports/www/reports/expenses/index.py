import frappe
from datetime import datetime



def get_context(context):
    """
    Get context for the expenses dashboard page.
    This function fetches data for the filter dropdowns and number card statistics.
    Only includes item group 'EXPENSE'.
    """
    context.active_page = "expenses"

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
    # Fetch only item groups that are 'EXPENSE'
    item_groups = frappe.get_all(
        "Item Group",
        fields=["name as value", "name as label"],
        filters={"is_group": 0, "name": "EXPENSE"}
    )
    # Fetch suppliers
    suppliers = frappe.get_all(
        "Supplier",
        fields=["name as value", "supplier_name as label"],
        filters={"disabled": 0}
    )
    context.company_list = companies
    context.branch_list = branches
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
    current_month = current_date.strftime("%B")
    current_year = current_date.year
    # Fiscal year (April to March)
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
    extra_gle = ""
    extra_args = {}
    if company and company.strip():
        extra_gle += " AND gle.company = %(company)s"
        extra_args['company'] = company
    if branch and branch.strip():
        extra_gle += " AND gle.cost_center = %(branch)s"
        extra_args['branch'] = branch

    # Query for Total Expense (all expense accounts)
    total_expense_query = f"""
        SELECT SUM(gle.debit) AS total_expense
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON gle.account = acc.name
        WHERE acc.account_type = 'Expense' AND gle.debit > 0
        AND gle.posting_date BETWEEN {filter_from} AND {filter_to}
    """
    total_expense_result = frappe.db.sql(total_expense_query, as_dict=True)[0] or {}
    total_expense = total_expense_result.get('total_expense') or 0

    # Query for Total Salaries (accounts containing salary, payroll, wage, compensation)
    total_salaries_query = f"""
        SELECT SUM(gle.debit) AS total_salaries
        FROM `tabGL Entry` gle
        WHERE gle.account = 'Salary - HKE'
        AND gle.debit > 0
    """
    total_salaries_result = frappe.db.sql(total_salaries_query, as_dict=True)[0] or {}
    total_salaries = total_salaries_result.get('total_salaries') or 0

    # Query for Total Rents (accounts containing rent, lease, premises)
    total_rents_query = f"""
        SELECT SUM(gle.debit) AS total_rents
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON gle.account = acc.name
        WHERE acc.account_type = 'Expense' AND gle.debit > 0
        AND gle.posting_date BETWEEN {filter_from} AND {filter_to}
        AND (LOWER(acc.account_name) LIKE '%rent%' 
             OR LOWER(acc.account_name) LIKE '%lease%' 
             OR LOWER(acc.account_name) LIKE '%premises%')
    """
    total_rents_result = frappe.db.sql(total_rents_query, as_dict=True)[0] or {}
    total_rents = total_rents_result.get('total_rents') or 0

    # Query for Total Electric Bill (accounts containing electric, power, electricity, utility)
    total_electric_bill_query = f"""
        SELECT SUM(gle.debit) AS total_electric_bill
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON gle.account = acc.name
        WHERE acc.account_type = 'Expense' AND gle.debit > 0
        AND gle.posting_date BETWEEN {filter_from} AND {filter_to}
        AND (LOWER(acc.account_name) LIKE '%electric%' 
             OR LOWER(acc.account_name) LIKE '%power%' 
             OR LOWER(acc.account_name) LIKE '%electricity%' 
             OR LOWER(acc.account_name) LIKE '%utility%')
    """
    total_electric_bill_result = frappe.db.sql(total_electric_bill_query, as_dict=True)[0] or {}
    total_electric_bill = total_electric_bill_result.get('total_electric_bill') or 0

    # Add expense stats to context
    context.total_expense = f"₹{total_expense:,.0f}"
    context.total_salaries = f"₹{total_salaries:,.0f}"
    context.total_rents = f"₹{total_rents:,.0f}"
    context.total_electric_bill = f"₹{total_electric_bill:,.0f}"

    # Get detailed data for each cost center for modal display, using filters
    context.cost_center_details = 0

    return context
