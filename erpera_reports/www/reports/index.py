import frappe
from frappe import _
from datetime import datetime, timedelta
from frappe.utils import nowdate, add_months, add_days, getdate

def get_context(context):
    """Get context data for the main dashboard page"""
    context.title = _("ERPera Reports Dashboard")
    context.summary_cards = get_dashboard_data()
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
    
    # Get detailed data for each branch/warehouse for modal display
    today = getdate(nowdate())
    start_of_month = today.replace(day=1)
    end_of_month = add_months(start_of_month, 1) - timedelta(days=1)
    
    context.sales_details = get_sales_details(start_of_month, end_of_month)
    context.purchase_details = get_purchase_details(start_of_month, end_of_month)
    context.stock_details = get_stock_details()
    
    return context

def get_sales_details(start_date, end_date):
    """
    Get detailed sales statistics for each branch to display in modal
    """
    # Query for sales data by branch
    sales_by_branch_query = """
        SELECT 
            si.cost_center,
            cc.cost_center_name,
            COALESCE(SUM(si.grand_total), 0) AS total_sales,
            COUNT(si.name) AS total_invoices,
            COALESCE(AVG(si.grand_total), 0) AS avg_invoice_value
        FROM `tabSales Invoice` si
        LEFT JOIN `tabCost Center` cc ON si.cost_center = cc.name
        WHERE si.posting_date BETWEEN %s AND %s
        AND si.docstatus = 1
        AND si.cost_center IS NOT NULL
        GROUP BY si.cost_center, cc.cost_center_name
        ORDER BY total_sales DESC
    """
    
    sales_by_branch = frappe.db.sql(sales_by_branch_query, (start_date, end_date), as_dict=True)
    
    # Convert to list and format values
    result = []
    for row in sales_by_branch:
        result.append({
            'name': row.get('cost_center', 'Unknown'),
            'display_name': row.get('cost_center_name', row.get('cost_center', 'Unknown')),
            'total_sales': f"₹{row.get('total_sales', 0):,.0f}",
            'total_invoices': f"{row.get('total_invoices', 0):,}",
            'avg_invoice_value': f"₹{row.get('avg_invoice_value', 0):,.0f}"
        })
    
    return result

def get_purchase_details(start_date, end_date):
    """
    Get detailed purchase statistics for each branch to display in modal
    """
    # Query for purchase data by branch
    purchase_by_branch_query = """
        SELECT 
            pi.cost_center,
            cc.cost_center_name,
            COALESCE(SUM(pi.grand_total), 0) AS total_amount,
            COUNT(DISTINCT pi.supplier) AS unique_suppliers,
            COALESCE(SUM(pi.outstanding_amount), 0) AS total_outstanding
        FROM `tabPurchase Invoice` pi
        LEFT JOIN `tabCost Center` cc ON pi.cost_center = cc.name
        WHERE pi.posting_date BETWEEN %s AND %s
        AND pi.docstatus = 1
        AND pi.cost_center IS NOT NULL
        GROUP BY pi.cost_center, cc.cost_center_name
        ORDER BY total_amount DESC
    """
    
    purchase_by_branch = frappe.db.sql(purchase_by_branch_query, (start_date, end_date), as_dict=True)
    
    # Convert to list and format values
    result = []
    for row in purchase_by_branch:
        result.append({
            'name': row.get('cost_center', 'Unknown'),
            'display_name': row.get('cost_center_name', row.get('cost_center', 'Unknown')),
            'total_amount': f"₹{row.get('total_amount', 0):,.0f}",
            'unique_suppliers': f"{row.get('unique_suppliers', 0):,}",
            'total_outstanding': f"₹{row.get('total_outstanding', 0):,.0f}"
        })
    
    return result

def get_stock_details():
    """
    Get detailed stock statistics for each warehouse to display in modal
    """
    # Query for stock data by warehouse
    stock_by_warehouse_query = """
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
        GROUP BY sle.warehouse, w.warehouse_name
        ORDER BY total_stock_value DESC
    """
    
    stock_by_warehouse = frappe.db.sql(stock_by_warehouse_query, as_dict=True)
    
    # Convert to list and format values
    result = []
    for row in stock_by_warehouse:
        result.append({
            'name': row.get('warehouse', 'Unknown'),
            'display_name': row.get('warehouse_name', row.get('warehouse', 'Unknown')),
            'total_skus': f"{row.get('total_skus', 0):,}",
            'total_stock_value': f"₹{row.get('total_stock_value', 0):,.0f}",
            'efficiency_score': f"{row.get('efficiency_score', 0):.1f}%"
        })
    
    return result

@frappe.whitelist()
def get_dashboard_data():
    """Get dashboard summary data for sales, purchase, and stock"""
    today = getdate(nowdate())
    start_of_month = today.replace(day=1)
    end_of_month = add_months(start_of_month, 1) - timedelta(days=1)
    prev_month_start = add_months(start_of_month, -1)
    prev_month_end = start_of_month - timedelta(days=1)
    

    try:
        # Sales summary
        sales = frappe.db.sql("""
            SELECT 
                COALESCE(SUM(grand_total), 0) as total_sales,
                COUNT(*) as total_invoices,
                COALESCE(AVG(grand_total), 0) as avg_invoice_value
            FROM `tabSales Invoice`
            WHERE posting_date BETWEEN %s AND %s
            AND docstatus = 1
        """, (start_of_month, end_of_month), as_dict=True)[0]

        # Purchase summary
        purchase = frappe.db.sql("""
            SELECT 
                COALESCE(SUM(grand_total), 0) as total_amount,
                COUNT(DISTINCT supplier) as unique_suppliers,
                COALESCE(SUM(outstanding_amount), 0) as total_outstanding
            FROM `tabPurchase Invoice`
            WHERE posting_date BETWEEN %s AND %s
            AND docstatus = 1
        """, (start_of_month, end_of_month), as_dict=True)[0]

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
                "total_sales": int(sales.total_sales or 0),
                "total_invoices": int(sales.total_invoices or 0),
                "avg_invoice_value": int(sales.avg_invoice_value or 0)
            },
            "purchase": {
                "total_amount": int(purchase.total_amount or 0),
                "unique_suppliers": int(purchase.unique_suppliers or 0),
                "total_outstanding": int(purchase.total_outstanding or 0)
            },
            "stock": {
                "total_skus": int(total_skus or 0),
                "total_stock_value": int(total_stock_value),
                "efficiency_score": int(efficiency_score)
            }
        }
    except Exception as e:
        frappe.log_error(f"Error in get_dashboard_data: {str(e)}")
        return {
            "sales": {"total_sales": 0, "total_invoices": 0, "avg_invoice_value": 0},
            "purchase": {"total_amount": 0, "unique_suppliers": 0, "total_outstanding": 0},
            "stock": {"total_skus": 0, "total_stock_value": 0, "efficiency_score": 0}
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
