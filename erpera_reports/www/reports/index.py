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
    """Get dashboard summary data"""
    
    # Get current month date range
    today = getdate(nowdate())
    start_of_month = today.replace(day=1)
    end_of_month = add_months(start_of_month, 1) - timedelta(days=1)
    
    # Get previous month for comparison
    prev_month_start = add_months(start_of_month, -1)
    prev_month_end = start_of_month - timedelta(days=1)
    
    try:
        # Purchase Orders data
        purchase_orders = get_purchase_orders_summary(start_of_month, end_of_month, prev_month_start, prev_month_end)
        
        # Purchase Receipts data
        purchase_receipts = get_purchase_receipts_summary(start_of_month, end_of_month, prev_month_start, prev_month_end)
        
        # Purchase Invoices data
        purchase_invoices = get_purchase_invoices_summary(start_of_month, end_of_month, prev_month_start, prev_month_end)
        
        # Suppliers data
        suppliers = get_suppliers_summary()
        
        # Outstanding data
        outstanding = get_outstanding_summary()
        
        return {
            "purchase_orders": purchase_orders,
            "purchase_receipts": purchase_receipts,
            "purchase_invoices": purchase_invoices,
            "suppliers": suppliers,
            "outstanding": outstanding
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_dashboard_data: {str(e)}")
        return {
            "purchase_orders": {"count": 0, "amount_growth": 0},
            "purchase_receipts": {"count": 0, "amount_growth": 0},
            "purchase_invoices": {"count": 0, "amount_growth": 0},
            "suppliers": {"total_suppliers": 0, "active_suppliers": 0},
            "outstanding": {"total_outstanding": 0, "overdue_count": 0}
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
