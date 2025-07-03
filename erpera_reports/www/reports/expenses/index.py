import frappe
from datetime import datetime
from erpera_reports.expense import (
    get_expense_stats,
    get_cost_center_expense_details
)

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

    # Get expense stats (only item group 'EXPENSE')
    stats = get_expense_stats(filter_from, filter_to, filter_month_from, filter_month_to, company, branch)
    context.total_expense = stats['total_expense']
    context.invoice_count = stats['invoice_count']
    context.supplier_count = stats['supplier_count']
    context.avg_invoice_value = stats['avg_invoice_value']

    # Get detailed data for each cost center for modal display, using filters
    context.cost_center_details = get_cost_center_expense_details(filter_from, filter_to, filter_month_from, filter_month_to, company, branch)

    return context
