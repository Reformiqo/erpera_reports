import frappe
from frappe import _
from datetime import datetime, timedelta
from frappe.utils import nowdate, add_months, add_days, getdate

def get_context(context):
    """Get context data for the main dashboard page"""
    context.title = _("ERPera Reports Dashboard")
    context.summary_cards = get_dashboard_data()
    return context

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
