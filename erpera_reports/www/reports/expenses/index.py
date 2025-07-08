import frappe
from datetime import datetime
from erpnext.accounts.utils import get_balance_on


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

    # Query for Total Expense (all expense accounts) like salary, rent, electric, etc.
    expense_accounts = frappe.db.get_list('Account', {'account_name': ['like', '%expense%', '%salary%', '%rent%', '%electric%']})
    total_expense = 0
    for account in expense_accounts:
        total_expense += get_balance_on(account = account.name, date = filter_to, start_date = filter_from, company = company, cost_center = branch)

    # Query for Total Salaries (accounts containing salary, payroll, wage, compensation)
    # Get all accounts that contain 'salary' in their name
    
    salary_accounts = frappe.db.get_list('Account', {'account_name': ['like', '%salary%']})
    total_salaries = 0
    for account in salary_accounts:
        total_salaries += get_balance_on(account = account.name, date = filter_to, start_date = filter_from, company = company)
    
    

    # Query for Total Rents (accounts containing rent, lease, premises)
    rent_accounts = frappe.db.get_list('Account', {'account_name': ['like', '%rent%']})
    total_rents = 0
    for account in rent_accounts:
        total_rents += get_balance_on(account = account.name, date = filter_to, start_date = filter_from, company = company, cost_center = branch)
    
    # Query for Total Electric Bill (accounts containing electric, power, electricity, utility)
    electric_accounts = frappe.db.get_list('Account', {'account_name': ['like', '%electric%']})
    total_electric_bill = 0
    for account in electric_accounts:
        total_electric_bill += get_balance_on(account = account.name, date = filter_to, start_date = filter_from, company = company, cost_center = branch)

    # Add expense stats to context
    context.total_expense = f"₹{total_expense:,.0f}"
    context.total_salaries = f"₹{total_salaries:,.0f}"
    context.total_rents = f"₹{total_rents:,.0f}"
    context.total_electric_bill = f"₹{total_electric_bill:,.0f}"

    # Get detailed data for each cost center for modal display, using filters
    context.cost_center_details = 0

    return context
