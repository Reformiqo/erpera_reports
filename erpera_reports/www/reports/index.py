import frappe
from frappe import _
from datetime import datetime, timedelta
from frappe.utils import nowdate, add_months, add_days, getdate

def format_currency(value):
    
    try:
        return f"₹{float(value):,.2f}"
    except Exception:
        return f"₹{value}"

def get_context(context):
    """Get context data for the main dashboard page"""
    context.title = _("ERPera Reports Dashboard")
    context.active_page = "dashboard"
    # Get filters from URL args
    args = frappe.request.args
    from_date = args.get('from_date')
    to_date = args.get('to_date')
    company = args.get('company')
    branch = args.get('branch')
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
    filter_from = from_date or fy_start
    filter_to = to_date or fy_end
    filter_month_from = from_date or current_date.replace(day=1).strftime("%Y-%m-%d")
    filter_month_to = to_date or current_date.strftime("%Y-%m-%d")

    # Build extra conditions for company/branch
    extra_si = ""
    extra_args = {}
    if from_date:
        extra_si += " AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s"
        extra_args['from_date'] = from_date
        extra_args['to_date'] = to_date
    if company:
        extra_si += " AND si.company = %(company)s"
        extra_args['company'] = company
    if branch:
        extra_si += " AND si.cost_center = %(branch)s"
        extra_args['branch'] = branch

    # Query for total sales, invoice count (fiscal year or filtered)
    fy_stats_query = f"""
        SELECT
            SUM(grand_total) AS total_sales,
            COUNT(name) AS invoice_count
        FROM `tabSales Invoice` si
        WHERE docstatus = 1
        {extra_si}
    """
    fy_sales_stats = frappe.db.sql(fy_stats_query, extra_args, as_dict=True)[0] or {}

    # Query for average sale value (current month or filtered)
    
    extra_pi = ""
    extra_pi_args = {}
    if from_date:
        extra_pi += " AND pi.posting_date BETWEEN %(from_date)s AND %(to_date)s"
        extra_pi_args['from_date'] = from_date
        extra_pi_args['to_date'] = to_date
    if company:
        extra_pi += " AND pi.company = %(company)s"
        extra_pi_args['company'] = company
    if branch:
        extra_pi += " AND pi.cost_center = %(branch)s"
        extra_pi_args['branch'] = branch
    purchase_query = f"""
        SELECT
            SUM(grand_total) AS total_amount,
            COUNT(DISTINCT supplier) AS unique_suppliers,
            SUM(outstanding_amount) AS total_outstanding
        FROM `tabPurchase Invoice` pi
        WHERE docstatus = 1
        {extra_pi}
    """
    purchase_stats = frappe.db.sql(purchase_query, extra_pi_args, as_dict=True)[0] or {}

    # Stock summary (SKUs, stock value, efficiency)
    total_skus_result = frappe.db.sql("""
        SELECT COUNT(DISTINCT item_code) as total_skus
        FROM `tabItem`
        WHERE disabled = 0
    """, as_dict=True)
    total_skus = total_skus_result[0].total_skus if total_skus_result else 0
    # For demo, use 0 for total_stock_value and efficiency_score
    total_stock_value = 0
    efficiency_score = 0

    # Format and set context variables for number cards
    total_sales = fy_sales_stats.get('total_sales') or 0
    invoice_count = fy_sales_stats.get('invoice_count') or 0
    month_total_sales =   0
    month_invoice_count =  0
    avg_invoice_value = month_total_sales / month_invoice_count if month_invoice_count > 0 else 0
    context.total_sales = f"₹{total_sales:,.0f}"
    context.invoice_count = f"{invoice_count:,}"
    context.avg_invoice_value = f"₹{avg_invoice_value:,.0f}"
    context.total_amount = f"₹{(purchase_stats.get('total_amount') or 0):,.0f}"
    context.unique_suppliers = f"{purchase_stats.get('unique_suppliers') or 0:,}"
    context.total_outstanding = f"₹{(purchase_stats.get('total_outstanding') or 0):,.0f}"
    context.total_skus = f"{total_skus:,}"
    context.total_stock_value = f"₹{total_stock_value:,.0f}"
    context.efficiency_score = f"{efficiency_score:,}"

    # Fetch companies, branches, items, item groups for filters
    companies = frappe.get_all(
        "Company",
        fields=["name as value", "company_name as label"],
        filters={"is_group": 0}
    )
    branches = frappe.get_all(
        "Cost Center",
        fields=["name as value", "cost_center_name as label"],
        filters={"is_group": 0}
    )
    items = frappe.get_all(
        "Item",
        fields=["name as value", "item_name as label"],
        filters={"is_stock_item": 1, "item_group": ["!=", "Raw Material", "Services", "Sub Assemblies", "Consumable", "Furniture", "EXPENSE", "FIXED ASSET"]}
    )
    item_groups = frappe.get_all(
        "Item Group",
        fields=["name as value", "name as label"],
        filters={"is_group": 0, "item_group_name": ["!=", "Raw Material", "Services", "Sub Assemblies", "Consumable", "Furniture", "EXPENSE", "FIXED ASSET"]}
    )
    context.company_list = companies
    context.branch_list = branches
    context.item_list = items
    context.item_group_list = item_groups

    # Get detailed data for each cost center for modal display, using filters
    context.sales_details = get_sales_details(filter_from, filter_to, company, branch)
    context.purchase_details = get_purchase_details(filter_from, filter_to, company, branch)
    context.stock_details = get_stock_details(warehouse, company)
    return context

def get_sales_details(start_date, end_date, company=None, branch=None):
    """
    Get detailed sales statistics for each branch to display in modal, using filters if provided
    """
    extra_si = ""
    args = {'start_date': start_date, 'end_date': end_date}
    if company:
        extra_si += " AND si.company = %(company)s"
        args['company'] = company
    if branch:
        extra_si += " AND si.cost_center = %(branch)s"
        args['branch'] = branch
    sales_by_branch_query = f"""
        SELECT 
            si.cost_center,
            cc.cost_center_name,
            COALESCE(SUM(si.grand_total), 0) AS total_sales,
            COUNT(si.name) AS total_invoices,
            COALESCE(AVG(si.grand_total), 0) AS avg_invoice_value
        FROM `tabSales Invoice` si
        LEFT JOIN `tabCost Center` cc ON si.cost_center = cc.name
        WHERE si.posting_date BETWEEN %(start_date)s AND %(end_date)s
        AND si.docstatus = 1
        AND si.cost_center IS NOT NULL
        {extra_si}
        GROUP BY si.cost_center, cc.cost_center_name
        ORDER BY total_sales DESC
    """
    sales_by_branch = frappe.db.sql(sales_by_branch_query, args, as_dict=True)
    result = []
    for row in sales_by_branch:
        result.append({
            'name': row.get('cost_center', 'Unknown'),
            'display_name': row.get('cost_center_name', row.get('cost_center', 'Unknown')),
            'total_sales': format_currency(row.get('total_sales', 0)),
            'total_invoices': f"{row.get('total_invoices', 0):,}",
            'avg_invoice_value': format_currency(row.get('avg_invoice_value', 0))
        })
    return result

def get_purchase_details(start_date, end_date, company=None, branch=None):
    """
    Get detailed purchase statistics for each branch to display in modal, using filters if provided
    """
    extra_pi = ""
    args = {'start_date': start_date, 'end_date': end_date}
    if company:
        extra_pi += " AND pi.company = %(company)s"
        args['company'] = company
    if branch:
        extra_pi += " AND pi.cost_center = %(branch)s"
        args['branch'] = branch
    purchase_by_branch_query = f"""
        SELECT 
            pi.cost_center,
            cc.cost_center_name,
            COALESCE(SUM(pi.grand_total), 0) AS total_amount,
            COUNT(DISTINCT pi.supplier) AS unique_suppliers,
            COALESCE(SUM(pi.outstanding_amount), 0) AS total_outstanding
        FROM `tabPurchase Invoice` pi
        LEFT JOIN `tabCost Center` cc ON pi.cost_center = cc.name
        WHERE pi.posting_date BETWEEN %(start_date)s AND %(end_date)s
        AND pi.docstatus = 1
        AND pi.cost_center IS NOT NULL
        {extra_pi}
        GROUP BY pi.cost_center, cc.cost_center_name
        ORDER BY total_amount DESC
    """
    purchase_by_branch = frappe.db.sql(purchase_by_branch_query, args, as_dict=True)
    result = []
    for row in purchase_by_branch:
        result.append({
            'name': row.get('cost_center', 'Unknown'),
            'display_name': row.get('cost_center_name', row.get('cost_center', 'Unknown')),
            'total_amount': format_currency(row.get('total_amount', 0)),
            'unique_suppliers': f"{row.get('unique_suppliers', 0):,}",
            'total_outstanding': format_currency(row.get('total_outstanding', 0))
        })
    return result

def get_stock_details(warehouse=None, company=None):
    """
    Get detailed stock statistics for each warehouse to display in modal, using filters if provided
    """
    extra_sle = ""
    args = {}
    if warehouse:
        extra_sle += " AND sle.warehouse = %(warehouse)s"
        args['warehouse'] = warehouse
    if company:
        extra_sle += " AND sle.company = %(company)s"
        args['company'] = company
    stock_by_warehouse_query = f"""
        SELECT 
            sle.warehouse,
            w.warehouse_name,
            COUNT(DISTINCT sle.item_code) AS total_skus,
            COALESCE(SUM(sle.actual_qty * sle.valuation_rate), 0) AS total_stock_value,
            ROUND(
                (COUNT(DISTINCT CASE WHEN sle.actual_qty > 0 THEN sle.item_code END) * 100.0) / 
                COUNT(DISTINCT sle.item_code), 1
            ) AS efficiency_score
        FROM `tabStock Ledger Entry` sle
        INNER JOIN `tabItem` item ON sle.item_code = item.name
        LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name
        WHERE item.is_stock_item = 1 
        AND sle.warehouse IS NOT NULL
        {extra_sle}
        GROUP BY sle.warehouse, w.warehouse_name
        ORDER BY total_stock_value DESC
    """
    stock_by_warehouse = frappe.db.sql(stock_by_warehouse_query, args, as_dict=True)
    result = []
    for row in stock_by_warehouse:
        result.append({
            'name': row.get('warehouse', 'Unknown'),
            'display_name': row.get('warehouse_name', row.get('warehouse', 'Unknown')),
            'total_skus': f"{row.get('total_skus', 0):,}",
            'total_stock_value': format_currency(row.get('total_stock_value', 0)),
            'efficiency_score': f"{row.get('efficiency_score', 0):.1f}%"
        })
    return result

@frappe.whitelist()
def get_dashboard_data(from_date=None, to_date=None, company=None, branch=None):
    """Get dashboard summary data for sales, purchase, and stock"""
    today = getdate(nowdate())
    if not from_date:
        from_date = today.replace(day=1)
    if not to_date:
        to_date = add_months(today.replace(day=1), 1) - timedelta(days=1)
    # Ensure dates are date objects
    if isinstance(from_date, str):
        from_date = getdate(from_date)
    if isinstance(to_date, str):
        to_date = getdate(to_date)
    # Debug log
    frappe.log_error(f"Dashboard filters: from_date={from_date}, to_date={to_date}, company={company}, branch={branch}")
    # Sales summary
    sales_filters = ""
    sales_args = [from_date, to_date]
    if company:
        sales_filters += " AND company = %s"
        sales_args.append(company)
    if branch:
        sales_filters += " AND cost_center = %s"
        sales_args.append(branch)
    sales = frappe.db.sql(f"""
        SELECT 
            COALESCE(SUM(grand_total), 0) as total_sales,
            COUNT(*) as total_invoices,
            COALESCE(AVG(grand_total), 0) as avg_invoice_value
        FROM `tabSales Invoice`
        WHERE posting_date BETWEEN %s AND %s
        AND docstatus = 1
        {sales_filters}
    """, tuple(sales_args), as_dict=True)[0]
    # Purchase summary
    purchase_filters = ""
    purchase_args = [from_date, to_date]
    if company:
        purchase_filters += " AND company = %s"
        purchase_args.append(company)
    if branch:
        purchase_filters += " AND cost_center = %s"
        purchase_args.append(branch)
    purchase = frappe.db.sql(f"""
        SELECT 
            COALESCE(SUM(grand_total), 0) as total_amount,
            COUNT(DISTINCT supplier) as unique_suppliers,
            COALESCE(SUM(outstanding_amount), 0) as total_outstanding
        FROM `tabPurchase Invoice`
        WHERE posting_date BETWEEN %s AND %s
        AND docstatus = 1
        {purchase_filters}
    """, tuple(purchase_args), as_dict=True)[0]
    # Stock summary (SKUs, stock value, efficiency)
    total_skus = frappe.db.sql("""
        SELECT COUNT(DISTINCT item_code) as total_skus
        FROM `tabItem`
        WHERE disabled = 0
    """, as_dict=True)[0].total_skus
    # For demo, use 0 for total_stock_value and efficiency_score
    total_stock_value = 0
    efficiency_score = 0
    return {
        "sales": {
            "total_sales": format_currency(sales.total_sales or 0),
            "total_invoices": int(sales.total_invoices or 0),
            "avg_invoice_value": format_currency(sales.avg_invoice_value or 0)
        },
        "purchase": {
            "total_amount": format_currency(purchase.total_amount or 0),
            "unique_suppliers": int(purchase.unique_suppliers or 0),
            "total_outstanding": format_currency(purchase.total_outstanding or 0)
        },
        "stock": {
            "total_skus": int(total_skus or 0),
            "total_stock_value": format_currency(total_stock_value),
            "efficiency_score": int(efficiency_score)
        }
    }

def get_purchase_orders_summary(start_date, end_date, prev_start, prev_end):
    """Get purchase orders summary for current and previous month"""
    
    # Current month data
    current_data = frappe.db.sql("""
        SELECT 
            COUNT(*) as count,
            COALESCE(SUM(grand_total), 0) as total_amount,
            COUNT(CASE WHEN status = 'Draft' THEN 1 END) as draft_count,
            COUNT(CASE WHEN status = 'To Receive and Bill' THEN 1 END) as pending_count
        FROM `tabPurchase Order`
        WHERE transaction_date BETWEEN %s AND %s
        AND docstatus != 2
    """, (start_date, end_date), as_dict=True)[0]
    
    # Previous month data for comparison
    prev_data = frappe.db.sql("""
        SELECT COALESCE(SUM(grand_total), 0) as total_amount
        FROM `tabPurchase Order`
        WHERE transaction_date BETWEEN %s AND %s
        AND docstatus != 2
    """, (prev_start, prev_end), as_dict=True)[0]
    
    # Calculate growth
    amount_growth = 0
    if prev_data.total_amount > 0:
        amount_growth = round(((current_data.total_amount - prev_data.total_amount) / prev_data.total_amount) * 100, 1)
    
    return {
        "count": current_data.count,
        "total_amount": current_data.total_amount,
        "draft_count": current_data.draft_count,
        "pending_count": current_data.pending_count,
        "amount_growth": amount_growth
    }

def get_purchase_receipts_summary(start_date, end_date, prev_start, prev_end):
    """Get purchase receipts summary for current and previous month"""
    
    # Current month data
    current_data = frappe.db.sql("""
        SELECT 
            COUNT(*) as count,
            COALESCE(SUM(grand_total), 0) as total_amount,
            COUNT(CASE WHEN status = 'Draft' THEN 1 END) as draft_count,
            COUNT(CASE WHEN status = 'To Bill' THEN 1 END) as to_bill_count
        FROM `tabPurchase Receipt`
        WHERE posting_date BETWEEN %s AND %s
        AND docstatus != 2
    """, (start_date, end_date), as_dict=True)[0]
    
    # Previous month data for comparison
    prev_data = frappe.db.sql("""
        SELECT COALESCE(SUM(grand_total), 0) as total_amount
        FROM `tabPurchase Receipt`
        WHERE posting_date BETWEEN %s AND %s
        AND docstatus != 2
    """, (prev_start, prev_end), as_dict=True)[0]
    
    # Calculate growth
    amount_growth = 0
    if prev_data.total_amount > 0:
        amount_growth = round(((current_data.total_amount - prev_data.total_amount) / prev_data.total_amount) * 100, 1)
    
    return {
        "count": current_data.count,
        "total_amount": current_data.total_amount,
        "draft_count": current_data.draft_count,
        "to_bill_count": current_data.to_bill_count,
        "amount_growth": amount_growth
    }

def get_purchase_invoices_summary(start_date, end_date, prev_start, prev_end):
    """Get purchase invoices summary for current and previous month"""
    
    # Current month data
    current_data = frappe.db.sql("""
        SELECT 
            COUNT(*) as count,
            COALESCE(SUM(grand_total), 0) as total_amount,
            COUNT(CASE WHEN status = 'Draft' THEN 1 END) as draft_count,
            COUNT(CASE WHEN status = 'Overdue' THEN 1 END) as overdue_count
        FROM `tabPurchase Invoice`
        WHERE posting_date BETWEEN %s AND %s
        AND docstatus != 2
    """, (start_date, end_date), as_dict=True)[0]
    
    # Previous month data for comparison
    prev_data = frappe.db.sql("""
        SELECT COALESCE(SUM(grand_total), 0) as total_amount
        FROM `tabPurchase Invoice`
        WHERE posting_date BETWEEN %s AND %s
        AND docstatus != 2
    """, (prev_start, prev_end), as_dict=True)[0]
    
    # Calculate growth
    amount_growth = 0
    if prev_data.total_amount > 0:
        amount_growth = round(((current_data.total_amount - prev_data.total_amount) / prev_data.total_amount) * 100, 1)
    
    return {
        "count": current_data.count,
        "total_amount": current_data.total_amount,
        "draft_count": current_data.draft_count,
        "overdue_count": current_data.overdue_count,
        "amount_growth": amount_growth
    }

def get_suppliers_summary():
    """Get suppliers summary"""
    
    data = frappe.db.sql("""
        SELECT 
            COUNT(*) as total_suppliers,
            COUNT(CASE WHEN disabled = 0 THEN 1 END) as active_suppliers,
            COUNT(CASE WHEN disabled = 1 THEN 1 END) as inactive_suppliers
        FROM `tabSupplier`
    """, as_dict=True)[0]
    
    return data

def get_outstanding_summary():
    """Get outstanding amount summary"""
    
    data = frappe.db.sql("""
        SELECT 
            COUNT(*) as invoice_count,
            COALESCE(SUM(outstanding_amount), 0) as total_outstanding,
            COUNT(CASE WHEN due_date < CURDATE() AND outstanding_amount > 0 THEN 1 END) as overdue_count,
            COALESCE(SUM(CASE WHEN due_date < CURDATE() THEN outstanding_amount ELSE 0 END), 0) as overdue_amount
        FROM `tabPurchase Invoice`
        WHERE docstatus = 1 
        AND outstanding_amount > 0
    """, as_dict=True)[0]
    
    return data
