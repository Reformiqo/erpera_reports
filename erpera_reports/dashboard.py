import frappe
from frappe import _
from datetime import datetime, timedelta
from frappe.utils import nowdate, add_months, add_days, getdate, today, formatdate
import json

def apply_filters_to_query(base_query, filters):
    """
    Helper function to apply filters to SQL queries
    """
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    filters = filters or {}
    conditions = []
    params = {}
    
    # Date range filters (with defaults if not provided)
    from_date = filters.get('from_date', add_months(today(), -3))  # Default to last 3 months
    to_date = filters.get('to_date', today())  # Default to today
    
    conditions.append("si.posting_date >= %(from_date)s")
    params['from_date'] = from_date
    
    conditions.append("si.posting_date <= %(to_date)s")
    params['to_date'] = to_date
    
    # Company filter
    if filters.get('company'):
        conditions.append("si.company = %(company)s")
        params['company'] = filters['company']
    
    # Branch filter (using cost_center)
    if filters.get('branch'):
        conditions.append("si.cost_center = %(branch)s")
        params['branch'] = filters['branch']
    
    # Add existing conditions
    if conditions:
        if "where" in base_query.lower():
            base_query += " AND " + " AND ".join(conditions)
        else:
            base_query += " WHERE " + " AND ".join(conditions)
    
    return base_query, params

def apply_filters_to_item_query(base_query, filters):
    """
    Helper function to apply filters to SQL queries with Sales Invoice Item
    """
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    filters = filters or {}
    conditions = []
    params = {}
    
    # Date range filters (with defaults if not provided)
    from_date = filters.get('from_date', add_months(today(), -3))  # Default to last 3 months
    to_date = filters.get('to_date', today())  # Default to today
    
    conditions.append("si.posting_date >= %(from_date)s")
    params['from_date'] = from_date
    
    conditions.append("si.posting_date <= %(to_date)s")
    params['to_date'] = to_date
    
    # Item filter
    if filters.get('item'):
        conditions.append("sii.item_code = %(item)s")
        params['item'] = filters['item']
    
    # Item group filter
    if filters.get('item_group'):
        conditions.append("i.item_group = %(item_group)s")
        params['item_group'] = filters['item_group']
    
    # Company filter
    if filters.get('company'):
        conditions.append("si.company = %(company)s")
        params['company'] = filters['company']
    
    # Branch filter (using cost_center)
    if filters.get('branch'):
        conditions.append("si.cost_center = %(branch)s")
        params['branch'] = filters['branch']
    
    # Custom filters
    if filters.get('warehouse'):
        conditions.append("sii.warehouse = %(warehouse)s")
        params['warehouse'] = filters['warehouse']
    
    # Add existing conditions
    if conditions:
        if "where" in base_query.lower():
            base_query += " AND " + " AND ".join(conditions)
        else:
            base_query += " WHERE " + " AND ".join(conditions)
    
    return base_query, params

# Chart API functions for dashboard

@frappe.whitelist()
def test_dashboard_connection():
    """Test function to check if dashboard endpoints are working"""
    try:
        # Check basic database connection
        current_time = frappe.db.sql("SELECT NOW() as current_time", as_dict=True)
        
        # Check if we have any Sales Invoice data
        si_count = frappe.db.sql("SELECT COUNT(*) as count FROM `tabSales Invoice` WHERE docstatus = 1", as_dict=True)
        
        # Check recent Sales Invoice data (last month)
        from_date = add_months(today(), -1)
        recent_si = frappe.db.sql("""
            SELECT COUNT(*) as count 
            FROM `tabSales Invoice` 
            WHERE docstatus = 1 
            AND posting_date >= %(from_date)s
        """, {'from_date': from_date}, as_dict=True)
        
        return {
            'success': True,
            'current_time': current_time[0]['current_time'] if current_time else None,
            'total_sales_invoices': si_count[0]['count'] if si_count else 0,
            'recent_sales_invoices': recent_si[0]['count'] if recent_si else 0,
            'test_date_range': f"{from_date} to {today()}"
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

# Branch-Wise Performance Report functions
@frappe.whitelist()
def get_branch_revenue_comparison(filters=None):
    """Get branch revenue comparison"""
    base_query = """
        SELECT 
            COALESCE(si.cost_center, 'No Branch') as branch,
            SUM(si.grand_total) as total_revenue,
            SUM(si.grand_total * 0.4) as profit,
            (SUM(si.grand_total * 0.4) / SUM(si.grand_total)) * 100 as margin,
            MAX(si.cost_center) as region
        FROM `tabSales Invoice` si
        WHERE 
            si.docstatus = 1
            AND si.status NOT IN ('Cancelled', 'Return')
    """
    
    try:
        # Apply filters
        query, params = apply_filters_to_query(base_query, filters)
        query += """
        GROUP BY si.cost_center
        ORDER BY total_revenue DESC
        """
        
        data = frappe.db.sql(query, params, as_dict=True)
        
        # If no data found, return empty data
        if not data:
            data = []
    except Exception as e:
        frappe.log_error(f"Error in get_branch_revenue_comparison: {str(e)}")
        # Return empty data in case of error
        data = []
    
    return {
        'labels': [d['branch'] for d in data],
        'datasets': [{
            'label': 'Revenue (₹)',
            'data': [d['total_revenue'] for d in data],
            'backgroundColor': '#22c55e'
        }]
    }

@frappe.whitelist()
def get_branch_profit_comparison(filters=None):
    """Get branch profit comparison (assuming 20% profit margin for demo)"""
    if not filters:
        filters = {}
    
    from_date = filters.get('from_date', add_months(today(), -1))
    to_date = filters.get('to_date', today())
    company = filters.get('company')
    
    conditions = ""
    if company:
        conditions += " AND company = %(company)s"
    
    try:
        data = frappe.db.sql(f"""
            SELECT 
                COALESCE(branch, 'No Branch') as branch,
                SUM(grand_total * 0.2) as estimated_profit,
                SUM(grand_total) as total_revenue,
                COUNT(name) as invoice_count
            FROM `tabSales Invoice`
            WHERE posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND docstatus = 1
            {conditions}
            GROUP BY branch
            ORDER BY estimated_profit DESC
        """, {
            'from_date': from_date,
            'to_date': to_date,
            'company': company
        }, as_dict=True)
        
        # If no data found, return sample data
        if not data:
            data = []
    except Exception as e:
        frappe.log_error(f"Error in get_branch_profit_comparison: {str(e)}")
        # Return empty data in case of error
        data = []
    
    return {
        'labels': [d['branch'] for d in data],
        'datasets': [{
            'label': 'Estimated Profit (₹)',
            'data': [d['estimated_profit'] for d in data],
            'backgroundColor': '#16a34a'
        }]
    }

@frappe.whitelist()
def get_branch_footfall_comparison(filters=None):
    """Get branch footfall comparison (unique customers)"""
    if not filters:
        filters = {}
    
    from_date = filters.get('from_date', add_months(today(), -1))
    to_date = filters.get('to_date', today())
    company = filters.get('company')
    
    conditions = ""
    if company:
        conditions += " AND company = %(company)s"
    
    try:
        data = frappe.db.sql(f"""
            SELECT 
                COALESCE(branch, 'No Branch') as branch,
                COUNT(DISTINCT customer) as unique_customers,
                COUNT(name) as total_invoices
            FROM `tabSales Invoice`
            WHERE posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND docstatus = 1
            {conditions}
            GROUP BY branch
            ORDER BY unique_customers DESC
        """, {
            'from_date': from_date,
            'to_date': to_date,
            'company': company
        }, as_dict=True)
        
        # If no data found, return sample data
        if not data:
            data = []
    except Exception as e:
        frappe.log_error(f"Error in get_branch_footfall_comparison: {str(e)}")
        # Return empty data in case of error
        data = []
    
    return {
        'labels': [d['branch'] for d in data],
        'datasets': [{
            'label': 'Unique Customers',
            'data': [d['unique_customers'] for d in data],
            'backgroundColor': '#3b82f6'
        }]
    }

@frappe.whitelist()
def get_branch_avg_bill_value(filters=None):
    """Get average bill value by branch"""
    if not filters:
        filters = {}
    
    from_date = filters.get('from_date', add_months(today(), -1))
    to_date = filters.get('to_date', today())
    company = filters.get('company')
    
    conditions = ""
    if company:
        conditions += " AND company = %(company)s"
    
    try:
        data = frappe.db.sql(f"""
            SELECT 
                COALESCE(branch, 'No Branch') as branch,
                AVG(grand_total) as avg_bill_value,
                SUM(grand_total) as total_revenue,
                COUNT(name) as invoice_count
            FROM `tabSales Invoice`
            WHERE posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND docstatus = 1
            {conditions}
            GROUP BY branch
            ORDER BY avg_bill_value DESC
        """, {
            'from_date': from_date,
            'to_date': to_date,
            'company': company
        }, as_dict=True)
        
        # If no data found, return sample data
        if not data:
            data = []
    except Exception as e:
        frappe.log_error(f"Error in get_branch_avg_bill_value: {str(e)}")
        # Return empty data in case of error
        data = []
    
    return {
        'labels': [d['branch'] for d in data],
        'datasets': [{
            'label': 'Average Bill Value (₹)',
            'data': [d['avg_bill_value'] for d in data],
            'backgroundColor': '#f59e0b'
        }]
    }

@frappe.whitelist()
def get_branch_performance_matrix(filters=None):
    """Get branch performance matrix data (Revenue vs Footfall)"""
    if not filters:
        filters = {}
    
    from_date = filters.get('from_date', add_months(today(), -1))
    to_date = filters.get('to_date', today())
    company = filters.get('company')
    
    conditions = ""
    if company:
        conditions += " AND company = %(company)s"
    
    try:
        data = frappe.db.sql(f"""
            SELECT 
                COALESCE(branch, 'No Branch') as branch,
                SUM(grand_total) as total_revenue,
                COUNT(DISTINCT customer) as unique_customers,
                AVG(grand_total) as avg_bill_value
            FROM `tabSales Invoice`
            WHERE posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND docstatus = 1
            {conditions}
            GROUP BY branch
            ORDER BY total_revenue DESC
        """, {
            'from_date': from_date,
            'to_date': to_date,
            'company': company
        }, as_dict=True)
        
        # If no data found, return sample data
        if not data:
            data = []
    except Exception as e:
        frappe.log_error(f"Error in get_branch_performance_matrix: {str(e)}")
        # Return empty data in case of error
        data = []
    
    return {
        'labels': [d['branch'] for d in data],
        'datasets': [{
            'label': 'Revenue vs Footfall',
            'data': [{'x': d['unique_customers'], 'y': d['total_revenue'], 'label': d['branch']} for d in data],
            'backgroundColor': '#8b5cf6'
        }]
    }

@frappe.whitelist()
def get_branch_growth_trend(filters=None):
    """Get branch growth trend"""
    if not filters:
        filters = {}
    
    period = filters.get('period', 'month')
    
    try:
        if period == 'month':
            current_start = today().replace(day=1)
            previous_start = add_months(current_start, -1)
            previous_end = add_days(current_start, -1)
        elif period == 'quarter':
            # Simplified quarter calculation
            current_start = today().replace(month=((today().month-1)//3)*3+1, day=1)
            previous_start = add_months(current_start, -3)
            previous_end = add_days(current_start, -1)
        else:  # year
            current_start = today().replace(month=1, day=1)
            previous_start = current_start.replace(year=current_start.year-1)
            previous_end = add_days(current_start, -1)
        
        # Get current period data
        current_data = frappe.db.sql("""
            SELECT 
                COALESCE(branch, 'No Branch') as branch,
                SUM(grand_total) as revenue
            FROM `tabSales Invoice`
            WHERE posting_date >= %s
            AND docstatus = 1
            GROUP BY branch
        """, (current_start,), as_dict=True)
        
        # Get previous period data
        previous_data = frappe.db.sql("""
            SELECT 
                COALESCE(branch, 'No Branch') as branch,
                SUM(grand_total) as revenue
            FROM `tabSales Invoice`
            WHERE posting_date BETWEEN %s AND %s
            AND docstatus = 1
            GROUP BY branch
        """, (previous_start, previous_end), as_dict=True)
        
        # Calculate growth
        current_dict = {d['branch']: d['revenue'] for d in current_data}
        previous_dict = {d['branch']: d['revenue'] for d in previous_data}
        
        growth_data = []
        for branch in current_dict:
            current_rev = current_dict[branch]
            previous_rev = previous_dict.get(branch, 0)
            if previous_rev > 0:
                growth = ((current_rev - previous_rev) / previous_rev) * 100
            else:
                growth = 100 if current_rev > 0 else 0
            growth_data.append({'branch': branch, 'growth': growth})
        
        # If no data, return sample data
        if not growth_data:
            growth_data = []
        
        # Sort by growth
        growth_data.sort(key=lambda x: x['growth'], reverse=True)
        
    except Exception as e:
        frappe.log_error(f"Error in get_branch_growth_trend: {str(e)}")
        # Return empty data in case of error
        growth_data = []
    
    return {
        'labels': [d['branch'] for d in growth_data],
        'datasets': [{
            'label': 'Growth %',
            'data': [d['growth'] for d in growth_data],
            'backgroundColor': ['#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']
        }]
    }

@frappe.whitelist(allow_guest=True)
def get_daily_sales_snapshot(filters=None):
    """Get daily sales snapshot across all branches"""
    if not filters:
        filters = {}
    
    date = filters.get('date', today())
    company = filters.get('company')
    
    conditions = ""
    if company:
        conditions += " AND company = %(company)s"
    
    try:
        data = frappe.db.sql(f"""
            SELECT 
                COALESCE(cost_center) as branch,
                SUM(grand_total) as total_sales,
                COUNT(name) as invoice_count,
                AVG(grand_total) as avg_invoice_value
            FROM `tabSales Invoice`
            WHERE docstatus = 1
            {conditions}
            GROUP BY cost_center
            ORDER BY total_sales DESC
        """, {
            'company': company
        }, as_dict=True)
        
        # If no data found, return sample data
        if not data:
            data = []
    except Exception as e:
        frappe.log_error(f"Error in get_daily_sales_snapshot: {str(e)}")
        # Return empty data in case of error
        data = []
    
    return {
        'labels': [d['branch'] for d in data],
        'datasets': [{
            'label': 'Sales Amount (₹)',
            'data': [d['total_sales'] for d in data],
            'backgroundColor': '#3b82f6'
        }]
    }

@frappe.whitelist()
def get_sales_by_branch(filters=None):
    """Get daily sales by branch"""
    base_query = """
        SELECT 
            COALESCE(si.branch, 'No Branch') as branch,
            SUM(si.grand_total) as total_sales,
            COUNT(si.name) as invoice_count
        FROM `tabSales Invoice` si
        WHERE 
            si.docstatus = 1
            AND si.status NOT IN ('Cancelled', 'Return')
    """
    
    try:
        # Apply filters
        query, params = apply_filters_to_query(base_query, filters)
        query += """
        GROUP BY si.branch
        ORDER BY total_sales DESC
        """
        
        data = frappe.db.sql(query, params, as_dict=True)
        
        # If no data found, return empty data
        if not data:
            data = []
    except Exception as e:
        frappe.log_error(f"Error in get_sales_by_branch: {str(e)}")
        # Return empty data in case of error
        data = []
    
    return {
        'labels': [d['branch'] for d in data],
        'datasets': [{
            'label': 'Sales (₹)',
            'data': [d['total_sales'] for d in data],
            'backgroundColor': '#10b981'
        }]
    }

@frappe.whitelist()
def get_payment_mode_breakdown(filters=None):
    """Get payment mode breakdown for today's sales"""
    if not filters:
        filters = {}
    
    date = filters.get('date', today())
    company = filters.get('company')
    
    conditions = ""
    if company:
        conditions += " AND si.company = %(company)s"
    
    try:
        data = frappe.db.sql(f"""
            SELECT 
                COALESCE(mop.mode_of_payment, 'Cash') as payment_mode,
                SUM(mop.amount) as total_amount,
                COUNT(DISTINCT si.name) as invoice_count
            FROM `tabSales Invoice` si
            LEFT JOIN `tabSales Invoice Payment` mop ON si.name = mop.parent
            WHERE si.posting_date = %(date)s
            AND si.docstatus = 1
            {conditions}
            GROUP BY mop.mode_of_payment
            ORDER BY total_amount DESC
        """, {
            'date': date,
            'company': company
        }, as_dict=True)
        
        # If no data found, return sample data
        if not data:
            data = []
    except Exception as e:
        frappe.log_error(f"Error in get_payment_mode_breakdown: {str(e)}")
        # Return empty data in case of error
        data = []
    
    return {
        'labels': [d['payment_mode'] for d in data],
        'datasets': [{
            'label': 'Payment Amount (₹)',
            'data': [d['total_amount'] for d in data],
            'backgroundColor': ['#f59e0b', '#06b6d4', '#8b5cf6', '#10b981', '#ef4444']
        }]
    }

@frappe.whitelist()
def get_hourly_sales_trend(filters=None):
    """Get hourly sales trend for today"""
    if not filters:
        filters = {}
    
    date = filters.get('date', today())
    company = filters.get('company')
    
    conditions = ""
    if company:
        conditions += " AND company = %(company)s"
    
    try:
        data = frappe.db.sql(f"""
            SELECT 
                HOUR(creation) as hour,
                SUM(grand_total) as total_sales,
                COUNT(name) as invoice_count
            FROM `tabSales Invoice`
            WHERE posting_date = %(date)s
            AND docstatus = 1
            {conditions}
            GROUP BY HOUR(creation)
            ORDER BY hour
        """, {
            'date': date,
            'company': company
        }, as_dict=True)
        
        # If no data found, return sample data for business hours
        if not data:
            data = []
        
        # Fill missing hours with 0
        hours_dict = {d['hour']: d['total_sales'] for d in data}
        full_data = []
        for hour in range(9, 21):  # 9 AM to 8 PM
            full_data.append({
                'hour': f"{hour}:00",
                'total_sales': hours_dict.get(hour, 0)
            })
            
    except Exception as e:
        frappe.log_error(f"Error in get_hourly_sales_trend: {str(e)}")
        # Return empty data in case of error
        full_data = []
    
    return {
        'labels': [d['hour'] for d in full_data],
        'datasets': [{
            'label': 'Hourly Sales (₹)',
            'data': [d['total_sales'] for d in full_data],
            'backgroundColor': '#06b6d4',
            'borderColor': '#0891b2',
            'fill': False
        }]
    }

@frappe.whitelist()
def get_daily_sales_stats(filters=None):
    """Get daily sales summary statistics"""
    if not filters:
        filters = {}
    
    date = filters.get('date', today())
    company = filters.get('company')
    
    conditions = ""
    if company:
        conditions += " AND company = %(company)s"
    
    try:
        summary = frappe.db.sql(f"""
            SELECT 
                COUNT(name) as total_invoices,
                SUM(grand_total) as total_sales,
                AVG(grand_total) as avg_invoice,
                MAX(grand_total) as max_invoice
            FROM `tabSales Invoice`
            WHERE posting_date = %(date)s
            AND docstatus = 1
            {conditions}
        """, {
            'date': date,
            'company': company
        }, as_dict=True)
        
        if summary and summary[0]['total_invoices']:
            stats = summary[0]
        else:
            # Return empty stats if no records found
            stats = {
                'total_invoices': 0,
                'total_sales': 0,
                'avg_invoice': 0,
                'max_invoice': 0
            }
    except Exception as e:
        frappe.log_error(f"Error in get_daily_sales_stats: {str(e)}")
        # Return empty stats in case of error
        stats = {
            'total_invoices': 0,
            'total_sales': 0,
            'avg_invoice': 0,
            'max_invoice': 0
        }
    
    return {
        'labels': ['Total Invoices', 'Total Sales', 'Average Invoice', 'Max Invoice'],
        'datasets': [{
            'label': 'Daily Stats',
            'data': [
                stats['total_invoices'],
                stats['total_sales'] / 1000,  # Convert to thousands for better visualization
                stats['avg_invoice'],
                stats['max_invoice']
            ],
            'backgroundColor': ['#3b82f6', '#10b981', '#f59e0b', '#ef4444']
        }]
    }

@frappe.whitelist()
def get_monthly_purchase_trend(filters=None):
    """Get monthly purchase trend data"""
    if not filters:
        filters = {}
    
    from_date = filters.get('from_date', add_months(today(), -12))
    to_date = filters.get('to_date', today())
    company = filters.get('company')
    
    conditions = ""
    if company:
        conditions += " AND company = %(company)s"
    
    data = frappe.db.sql(f"""
        SELECT 
            DATE_FORMAT(posting_date, '%%Y-%%m') as month,
            SUM(grand_total) as total_amount,
            COUNT(*) as count
        FROM `tabPurchase Invoice`
        WHERE posting_date BETWEEN %(from_date)s AND %(to_date)s
        AND docstatus = 1
        {conditions}
        GROUP BY DATE_FORMAT(posting_date, '%%Y-%%m')
        ORDER BY month
    """, {
        'from_date': from_date,
        'to_date': to_date,
        'company': company
    }, as_dict=True)
    
    return {
        'labels': [d.month for d in data],
        'datasets': [{
            'label': 'Purchase Amount',
            'data': [d.total_amount for d in data],
            'backgroundColor': '#667eea'
        }]
    }

@frappe.whitelist()
def get_top_suppliers(filters=None):
    """Get top suppliers data"""
    if not filters:
        filters = {}
    
    from_date = filters.get('from_date', add_months(today(), -1))
    to_date = filters.get('to_date', today())
    limit = int(filters.get('limit', 10))
    
    data = frappe.db.sql("""
        SELECT 
            supplier,
            SUM(grand_total) as total_amount,
            COUNT(*) as invoice_count
        FROM `tabPurchase Invoice`
        WHERE posting_date BETWEEN %s AND %s
        AND docstatus = 1
        GROUP BY supplier
        ORDER BY total_amount DESC
        LIMIT %s
    """, (from_date, to_date, limit), as_dict=True)
    
    return {
        'labels': [d.supplier for d in data],
        'datasets': [{
            'label': 'Purchase Amount',
            'data': [d.total_amount for d in data],
            'backgroundColor': '#10b981'
        }]
    }

@frappe.whitelist()
def get_purchase_by_status(filters=None):
    """Get purchase orders by status"""
    if not filters:
        filters = {}
    
    from_date = filters.get('from_date', add_months(today(), -1))
    to_date = filters.get('to_date', today())
    
    data = frappe.db.sql("""
        SELECT 
            status,
            COUNT(*) as count,
            SUM(grand_total) as total_amount
        FROM `tabPurchase Order`
        WHERE transaction_date BETWEEN %s AND %s
        AND docstatus != 2
        GROUP BY status
        ORDER BY count DESC
    """, (from_date, to_date), as_dict=True)
    
    return {
        'labels': [d.status for d in data],
        'datasets': [{
            'label': 'Orders Count',
            'data': [d.count for d in data],
            'backgroundColor': ['#f59e0b', '#10b981', '#ef4444', '#8b5cf6', '#06b6d4']
        }]
    }

@frappe.whitelist()
def get_outstanding_by_supplier(filters=None):
    """Get outstanding amounts by supplier"""
    if not filters:
        filters = {}
    
    limit = int(filters.get('limit', 10))
    
    data = frappe.db.sql("""
        SELECT 
            supplier,
            SUM(outstanding_amount) as outstanding_amount,
            COUNT(*) as invoice_count
        FROM `tabPurchase Invoice`
        WHERE docstatus = 1 
        AND outstanding_amount > 0
        GROUP BY supplier
        ORDER BY outstanding_amount DESC
        LIMIT %s
    """, (limit,), as_dict=True)
    
    return {
        'labels': [d.supplier for d in data],
        'datasets': [{
            'label': 'Outstanding Amount',
            'data': [d.outstanding_amount for d in data],
            'backgroundColor': '#ef4444'
        }]
    }

@frappe.whitelist()
def get_aging_analysis(filters=None):
    """Get outstanding aging analysis"""
    data = frappe.db.sql("""
        SELECT 
            CASE 
                WHEN DATEDIFF(CURDATE(), due_date) <= 30 THEN '0-30 Days'
                WHEN DATEDIFF(CURDATE(), due_date) <= 60 THEN '31-60 Days'
                WHEN DATEDIFF(CURDATE(), due_date) <= 90 THEN '61-90 Days'
                ELSE '90+ Days'
            END as aging_bucket,
            SUM(outstanding_amount) as amount,
            COUNT(*) as count
        FROM `tabPurchase Invoice`
        WHERE docstatus = 1 
        AND outstanding_amount > 0
        AND due_date < CURDATE()
        GROUP BY aging_bucket
        ORDER BY 
            CASE aging_bucket
                WHEN '0-30 Days' THEN 1
                WHEN '31-60 Days' THEN 2
                WHEN '61-90 Days' THEN 3
                WHEN '90+ Days' THEN 4
            END
    """, as_dict=True)
    
    return {
        'labels': [d.aging_bucket for d in data],
        'datasets': [{
            'label': 'Outstanding Amount',
            'data': [d.amount for d in data],
            'backgroundColor': ['#10b981', '#f59e0b', '#ef4444', '#dc2626']
        }]
    }

@frappe.whitelist()
def get_company_wise_purchases(filters=None):
    """Get company wise purchase data"""
    if not filters:
        filters = {}
    
    from_date = filters.get('from_date', add_months(today(), -1))
    to_date = filters.get('to_date', today())
    company = filters.get('company')
    
    conditions = ""
    if company:
        conditions += " AND company = %(company)s"
    
    data = frappe.db.sql(f"""
        SELECT 
            company,
            SUM(grand_total) as total_amount,
            COUNT(*) as invoice_count
        FROM `tabPurchase Invoice`
        WHERE posting_date BETWEEN %(from_date)s AND %(to_date)s
        AND docstatus = 1
        {conditions}
        GROUP BY company
        ORDER BY total_amount DESC
    """, {
        'from_date': from_date,
        'to_date': to_date,
        'company': company
    }, as_dict=True)
    
    return {
        'labels': [d.company for d in data],
        'datasets': [{
            'label': 'Purchase Amount',
            'data': [d.total_amount for d in data],
            'backgroundColor': '#06b6d4'
        }]
    }

# Top Selling & Low Performing SKUs functions
@frappe.whitelist()
def get_top_selling_skus(filters=None):
    """Get top 20 fast-moving items by quantity"""
    base_query = """
        SELECT 
            sii.item_code,
            sii.item_name,
            SUM(sii.qty) as total_qty,
            SUM(sii.amount) as total_amount,
            AVG(sii.rate) as avg_rate,
            COUNT(DISTINCT si.name) as invoice_count
        FROM `tabSales Invoice Item` sii
        INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
        INNER JOIN `tabItem` i ON sii.item_code = i.name
        INNER JOIN `tabItem Group` ig ON i.item_group = ig.name
        WHERE 
            si.docstatus = 1
            AND si.status NOT IN ('Cancelled', 'Return')
            AND ig.name NOT IN ('Raw Material', 'Sub Assemblies', 'Consumable', 'Furniture', 'EXPENSE', 'FIXED ASSET')
    """
    
    try:
        # Apply filters for item queries
        query, params = apply_filters_to_item_query(base_query, filters)
        query += """
        GROUP BY sii.item_code, sii.item_name
        ORDER BY total_qty DESC
        LIMIT 20
        """
        
        data = frappe.db.sql(query, params, as_dict=True)
        
        # If no data found, return empty data
        if not data:
            data = []
    except Exception as e:
        frappe.log_error(f"Error in get_top_selling_skus: {str(e)}")
        data = []
    
    return {
        'labels': [f"{d['item_code']}" for d in data],
        'datasets': [{
            'label': 'Quantity Sold',
            'data': [d['total_qty'] for d in data],
            'backgroundColor': '#10b981'
        }]
    }

@frappe.whitelist()
def get_low_performing_skus(filters=None):
    """Get bottom 20 slow-moving items by quantity"""
    base_query = """
        SELECT 
            sii.item_code,
            sii.item_name,
            SUM(sii.qty) as total_qty,
            SUM(sii.amount) as total_amount,
            AVG(sii.rate) as avg_rate,
            COUNT(DISTINCT si.name) as invoice_count
        FROM `tabSales Invoice Item` sii
        INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
        INNER JOIN `tabItem` i ON sii.item_code = i.name
        INNER JOIN `tabItem Group` ig ON i.item_group = ig.name
        WHERE 
            si.docstatus = 1
            AND si.status NOT IN ('Cancelled', 'Return')
            AND ig.name NOT IN ('Raw Material', 'Sub Assemblies', 'Consumable', 'Furniture', 'EXPENSE', 'FIXED ASSET')
    """
    
    try:
        # Apply filters for item queries
        query, params = apply_filters_to_item_query(base_query, filters)
        query += """
        GROUP BY sii.item_code, sii.item_name
        HAVING total_qty > 0
        ORDER BY total_qty ASC
        LIMIT 20
        """
        
        data = frappe.db.sql(query, params, as_dict=True)
        
        # If no data found, return empty data
        if not data:
            data = []
    except Exception as e:
        frappe.log_error(f"Error in get_low_performing_skus: {str(e)}")
        data = []
    
    return {
        'labels': [f"{d['item_code']}" for d in data],
        'datasets': [{
            'label': 'Quantity Sold',
            'data': [d['total_qty'] for d in data],
            'backgroundColor': '#ef4444'
        }]
    }

@frappe.whitelist()
def get_top_revenue_items(filters=None):
    """Get top 20 items by revenue"""
    if not filters:
        filters = {}
    
    from_date = filters.get('from_date', add_months(today(), -1))
    to_date = filters.get('to_date', today())
    company = filters.get('company')
    branch = filters.get('branch')
    
    conditions = ""
    if company:
        conditions += " AND si.company = %(company)s"
    if branch:
        conditions += " AND si.branch = %(branch)s"
    
    try:
        data = frappe.db.sql(f"""
            SELECT 
                sii.item_code,
                sii.item_name,
                SUM(sii.amount) as total_amount,
                SUM(sii.qty) as total_qty,
                AVG(sii.rate) as avg_rate,
                COUNT(DISTINCT si.name) as invoice_count
            FROM `tabSales Invoice Item` sii
            INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
            INNER JOIN `tabItem` i ON sii.item_code = i.name
            INNER JOIN `tabItem Group` ig ON i.item_group = ig.name
            WHERE si.posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND si.docstatus = 1
            AND ig.name NOT IN ('Raw Material', 'Sub Assemblies', 'Consumable', 'Furniture', 'EXPENSE', 'FIXED ASSET')
            {conditions}
            GROUP BY sii.item_code, sii.item_name
            ORDER BY total_amount DESC
            LIMIT 20
        """, {
            'from_date': from_date,
            'to_date': to_date,
            'company': company,
            'branch': branch
        }, as_dict=True)
        
        # If no data found, return sample data
        if not data:
            data = []
    except Exception as e:
        frappe.log_error(f"Error in get_top_revenue_items: {str(e)}")
        # Return sample data in case of error
        data = []
    
    return {
        'labels': [f"{d['item_code']}" for d in data],
        'datasets': [{
            'label': 'Revenue (₹)',
            'data': [d['total_amount'] for d in data],
            'backgroundColor': '#8b5cf6'
        }]
    }

@frappe.whitelist()
def get_item_category_performance(filters=None):
    """Get item category performance"""
    if not filters:
        filters = {}
    
    from_date = filters.get('from_date', add_months(today(), -1))
    to_date = filters.get('to_date', today())
    company = filters.get('company')
    branch = filters.get('branch')
    
    conditions = ""
    if company:
        conditions += " AND si.company = %(company)s"
    if branch:
        conditions += " AND si.cost_center = %(branch)s"
    
    try:
        data = frappe.db.sql(f"""
            SELECT 
                COALESCE(i.item_group, 'Others') as item_group,
                SUM(sii.amount) as total_amount,
                SUM(sii.qty) as total_qty,
                COUNT(DISTINCT sii.item_code) as unique_items
            FROM `tabSales Invoice Item` sii
            INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
            INNER JOIN `tabItem` i ON i.name = sii.item_code
            INNER JOIN `tabItem Group` ig ON i.item_group = ig.name
            WHERE si.posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND si.docstatus = 1
            AND ig.name NOT IN ('Raw Material', 'Sub Assemblies', 'Consumable', 'Furniture', 'EXPENSE', 'FIXED ASSET')
            {conditions}
            GROUP BY i.item_group
            ORDER BY total_amount DESC
            LIMIT 10
        """, {
            'from_date': from_date,
            'to_date': to_date,
            'company': company,
            'branch': branch
        }, as_dict=True)
        
        # If no data found, return sample data
        if not data:
            data = []
    except Exception as e:
        frappe.log_error(f"Error in get_item_category_performance: {str(e)}")
        # Return empty data in case of error
        data = []
    
    labels = [d['item_group'] for d in data]
    data_values = [d['total_amount'] for d in data]
    colors = ['#f59e0b', '#10b981', '#3b82f6', '#8b5cf6', '#ef4444', '#06b6d4', '#84cc16', '#f97316']
    return {
        'labels': labels,
        'data': data_values,
        'backgroundColor': colors[:len(labels)]
    }

@frappe.whitelist()
def get_sku_velocity_trend(filters=None):
    """Get SKU velocity trend for top 10 items over 30 days"""
    if not filters:
        filters = {}
    
    from_date = filters.get('from_date', add_days(today(), -30))
    to_date = filters.get('to_date', today())
    company = filters.get('company')
    branch = filters.get('branch')
    
    conditions = ""
    if company:
        conditions += " AND si.company = %(company)s"
    if branch:
        conditions += " AND si.branch = %(branch)s"
    
    try:
        # First get top 10 items
        top_items = frappe.db.sql(f"""
            SELECT 
                sii.item_code,
                SUM(sii.qty) as total_qty
            FROM `tabSales Invoice Item` sii
            INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
            INNER JOIN `tabItem` i ON sii.item_code = i.name
            INNER JOIN `tabItem Group` ig ON i.item_group = ig.name
            WHERE si.posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND si.docstatus = 1
            AND ig.name NOT IN ('Raw Material', 'Sub Assemblies', 'Consumable', 'Furniture', 'EXPENSE', 'FIXED ASSET')
            {conditions}
            GROUP BY sii.item_code
            ORDER BY total_qty DESC
            LIMIT 10
        """, {
            'from_date': from_date,
            'to_date': to_date,
            'company': company,
            'branch': branch
        }, as_dict=True)
        
        if not top_items:
            # Return empty chart data
            return {
                'labels': [],
                'datasets': []
            }
    
        # Get weekly data for each top item
        item_codes = [item['item_code'] for item in top_items[:5]]  # Limit to top 5 for clarity
        
        weekly_data = frappe.db.sql(f"""
            SELECT 
                sii.item_code,
                WEEK(si.posting_date) as week_num,
                SUM(sii.qty) as weekly_qty
            FROM `tabSales Invoice Item` sii
            INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
            INNER JOIN `tabItem` i ON sii.item_code = i.name
            INNER JOIN `tabItem Group` ig ON i.item_group = ig.name
            WHERE si.posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND si.docstatus = 1
            AND sii.item_code IN %(item_codes)s
            AND ig.name NOT IN ('Raw Material', 'Sub Assemblies', 'Consumable', 'Furniture', 'EXPENSE', 'FIXED ASSET')
            {conditions}
            GROUP BY sii.item_code, WEEK(si.posting_date)
            ORDER BY sii.item_code, week_num
        """, {
            'from_date': from_date,
            'to_date': to_date,
            'item_codes': item_codes,
            'company': company,
            'branch': branch
        }, as_dict=True)
        
        # Format data for chart
        weeks = sorted(list(set([d['week_num'] for d in weekly_data])))
        week_labels = [f"Week {i+1}" for i in range(len(weeks))]
        
        datasets = []
        colors = ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444']
        
        for i, item_code in enumerate(item_codes):
            item_data = [d['weekly_qty'] for d in weekly_data if d['item_code'] == item_code]
            if len(item_data) < len(weeks):
                # Fill missing weeks with 0
                item_weekly = {d['week_num']: d['weekly_qty'] for d in weekly_data if d['item_code'] == item_code}
                item_data = [item_weekly.get(week, 0) for week in weeks]
            
            datasets.append({
                'label': item_code,
                'data': item_data,
                'borderColor': colors[i % len(colors)],
                'backgroundColor': f"{colors[i % len(colors)]}20",
                'fill': False
            })
        
        return {
            'labels': week_labels,
            'datasets': datasets
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_sku_velocity_trend: {str(e)}")
        # Return empty chart data in case of error
        return {
            'labels': [],
            'datasets': []
        }

# Purchase vs Sales Consumption Report functions
@frappe.whitelist()
def get_purchase_vs_sales_overview(filters=None):
    """Get monthly purchase vs sales overview"""
    if not filters:
        filters = {}
    
    from_date = filters.get('from_date', add_months(today(), -6))
    to_date = filters.get('to_date', today())
    company = filters.get('company')
    
    conditions = ""
    if company:
        conditions += " AND company = %(company)s"
    
    try:
        # Get purchase data
        purchase_data = frappe.db.sql(f"""
            SELECT 
                DATE_FORMAT(posting_date, '%%Y-%%m') as month,
                SUM(grand_total) as total_purchase
            FROM `tabPurchase Invoice`
            WHERE posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND docstatus = 1
            {conditions}
            GROUP BY DATE_FORMAT(posting_date, '%%Y-%%m')
            ORDER BY month
        """, {
            'from_date': from_date,
            'to_date': to_date,
            'company': company
        }, as_dict=True)
        
        # Get sales data
        sales_data = frappe.db.sql(f"""
            SELECT 
                DATE_FORMAT(posting_date, '%%Y-%%m') as month,
                SUM(grand_total) as total_sales
            FROM `tabSales Invoice`
            WHERE posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND docstatus = 1
            {conditions}
            GROUP BY DATE_FORMAT(posting_date, '%%Y-%%m')
            ORDER BY month
        """, {
            'from_date': from_date,
            'to_date': to_date,
            'company': company
        }, as_dict=True)
        
        # Combine data
        purchase_dict = {d['month']: d['total_purchase'] for d in purchase_data}
        sales_dict = {d['month']: d['total_sales'] for d in sales_data}
        
        # Get all months from data or generate empty months for the period
        if purchase_data or sales_data:
            all_months = sorted(list(set(list(purchase_dict.keys()) + list(sales_dict.keys()))))
        else:
            # Generate month range from from_date to to_date
            import datetime
            start_date = datetime.datetime.strptime(str(from_date), '%Y-%m-%d')
            end_date = datetime.datetime.strptime(str(to_date), '%Y-%m-%d')
            all_months = []
            current = start_date.replace(day=1)
            while current <= end_date:
                all_months.append(current.strftime('%Y-%m'))
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)
        
        purchase_amounts = [purchase_dict.get(month, 0) for month in all_months]
        sales_amounts = [sales_dict.get(month, 0) for month in all_months]
        
    except Exception as e:
        frappe.log_error(f"Error in get_purchase_vs_sales_overview: {str(e)}")
        # Return empty data in case of error
        all_months = []
        purchase_amounts = []
        sales_amounts = []
    
    return {
        'labels': all_months,
        'datasets': [
            {
                'label': 'Purchases (₹)',
                'data': purchase_amounts,
                'borderColor': '#ef4444',
                'backgroundColor': 'rgba(239, 68, 68, 0.1)',
                'fill': False
            },
            {
                'label': 'Sales (₹)',
                'data': sales_amounts,
                'borderColor': '#10b981',
                'backgroundColor': 'rgba(16, 185, 129, 0.1)',
                'fill': False
            }
        ]
    }

@frappe.whitelist()
def get_item_wise_consumption(filters=None):
    """Get item-wise purchase vs sales analysis"""
    if not filters:
        filters = {}
    
    from_date = filters.get('from_date', add_months(today(), -3))
    to_date = filters.get('to_date', today())
    company = filters.get('company')
    item_group = filters.get('item_group')
    
    conditions = ""
    if company:
        conditions += " AND pi.company = %(company)s"
    
    item_conditions = ""
    if item_group:
        item_conditions += " AND i.item_group = %(item_group)s"
    
    try:
        # Get top 20 items by purchase value first
        purchase_data = frappe.db.sql(f"""
            SELECT 
                pii.item_code,
                SUM(pii.qty) as purchased_qty,
                SUM(pii.amount) as purchase_amount
            FROM `tabPurchase Invoice Item` pii
            INNER JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
            LEFT JOIN `tabItem` i ON i.name = pii.item_code
            WHERE pi.posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND pi.docstatus = 1
            {conditions}
            {item_conditions}
            GROUP BY pii.item_code
            ORDER BY purchase_amount DESC
            LIMIT 20
        """, {
            'from_date': from_date,
            'to_date': to_date,
            'company': company,
            'item_group': item_group
        }, as_dict=True)
        
        if purchase_data:
            # Get sales data for these items
            item_codes = [d['item_code'] for d in purchase_data]
            sales_data = frappe.db.sql(f"""
                SELECT 
                    sii.item_code,
                    SUM(sii.amount) as sales_amount
                FROM `tabSales Invoice Item` sii
                INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
                INNER JOIN `tabItem` i ON i.name = sii.item_code
                INNER JOIN `tabItem Group` ig ON i.item_group = ig.name
                WHERE si.posting_date BETWEEN %(from_date)s AND %(to_date)s
                AND si.docstatus = 1
                AND sii.item_code IN %(item_codes)s
                AND ig.name NOT IN ('Raw Material', 'Sub Assemblies', 'Consumable', 'Furniture', 'EXPENSE', 'FIXED ASSET')
                {conditions.replace('pi.', 'si.')}
                GROUP BY sii.item_code
            """, {
                'from_date': from_date,
                'to_date': to_date,
                'company': company,
                'item_codes': item_codes
            }, as_dict=True)
            
            sales_dict = {d['item_code']: d['sales_amount'] for d in sales_data}
            
            data = []
            for d in purchase_data:
                data.append({
                    'item_code': d['item_code'],
                    'purchased_qty': d['purchased_qty'],
                    'sold_qty': sales_dict.get(d['item_code'], 0)
                })
        else:
            data = []
                
    except Exception as e:
        frappe.log_error(f"Error in get_item_wise_consumption: {str(e)}")
        data = []
    
    return {
        'labels': [d['item_code'] for d in data],
        'datasets': [
            {
                'label': 'Purchased Qty',
                'data': [d['purchased_qty'] for d in data],
                'backgroundColor': '#ef4444'
            },
            {
                'label': 'Sold Qty',
                'data': [d['sold_qty'] for d in data],
                'backgroundColor': '#10b981'
            }
        ]
    }

@frappe.whitelist()
def get_overconsumption_items(filters=None):
    """Get items with overconsumption risk (sales > purchases)"""
    if not filters:
        filters = {}
    
    from_date = filters.get('from_date', add_months(today(), -3))
    to_date = filters.get('to_date', today())
    company = filters.get('company')
    
    conditions = ""
    if company:
        conditions += " AND pi.company = %(company)s"
    
    try:
        # Find items where sales quantity exceeds purchased quantity
        data = frappe.db.sql(f"""
            SELECT 
                item_code,
                purchased_qty,
                sold_qty,
                (sold_qty - purchased_qty) as excess_consumption
            FROM (
                SELECT 
                    COALESCE(p.item_code, s.item_code) as item_code,
                    COALESCE(p.purchased_qty, 0) as purchased_qty,
                    COALESCE(s.sold_qty, 0) as sold_qty
                FROM (
                    SELECT 
                        pii.item_code,
                        SUM(pii.qty) as purchased_qty
                    FROM `tabPurchase Invoice Item` pii
                    INNER JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
                    WHERE pi.posting_date BETWEEN %(from_date)s AND %(to_date)s
                    AND pi.docstatus = 1
                    {conditions}
                    GROUP BY pii.item_code
                ) p
                RIGHT JOIN (
                    SELECT 
                        sii.item_code,
                        SUM(sii.qty) as sold_qty
                    FROM `tabSales Invoice Item` sii
                    INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
                    INNER JOIN `tabItem` i ON sii.item_code = i.name
                    INNER JOIN `tabItem Group` ig ON i.item_group = ig.name
                    WHERE si.posting_date BETWEEN %(from_date)s AND %(to_date)s
                    AND si.docstatus = 1
                    AND ig.name NOT IN ('Raw Material', 'Sub Assemblies', 'Consumable', 'Furniture', 'EXPENSE', 'FIXED ASSET')
                    {conditions.replace('pi.', 'si.')}
                    GROUP BY sii.item_code
                ) s ON p.item_code = s.item_code
            ) combined
            WHERE sold_qty > purchased_qty
            ORDER BY excess_consumption DESC
            LIMIT 20
        """, {
            'from_date': from_date,
            'to_date': to_date,
            'company': company
        }, as_dict=True)
        
    except Exception as e:
        frappe.log_error(f"Error in get_overconsumption_items: {str(e)}")
        data = []
    
    return {
        'labels': [d['item_code'] for d in data],
        'datasets': [{
            'label': 'Excess Consumption Risk',
            'data': [d['excess_consumption'] for d in data],
            'backgroundColor': '#ef4444'
        }]
    }

@frappe.whitelist()
def get_understock_risk_items(filters=None):
    """Get items with understock risk (purchases > sales by large margin)"""
    if not filters:
        filters = {}
    
    from_date = filters.get('from_date', add_months(today(), -3))
    to_date = filters.get('to_date', today())
    company = filters.get('company')
    
    conditions = ""
    if company:
        conditions += " AND pi.company = %(company)s"
    
    try:
        # Find items where purchased quantity significantly exceeds sales
        data = frappe.db.sql(f"""
            SELECT 
                item_code,
                purchased_qty,
                sold_qty,
                (purchased_qty - sold_qty) as excess_stock
            FROM (
                SELECT 
                    COALESCE(p.item_code, s.item_code) as item_code,
                    COALESCE(p.purchased_qty, 0) as purchased_qty,
                    COALESCE(s.sold_qty, 0) as sold_qty
                FROM (
                    SELECT 
                        pii.item_code,
                        SUM(pii.qty) as purchased_qty
                    FROM `tabPurchase Invoice Item` pii
                    INNER JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
                    WHERE pi.posting_date BETWEEN %(from_date)s AND %(to_date)s
                    AND pi.docstatus = 1
                    {conditions}
                    GROUP BY pii.item_code
                ) p
                LEFT JOIN (
                    SELECT 
                        sii.item_code,
                        SUM(sii.qty) as sold_qty
                    FROM `tabSales Invoice Item` sii
                    INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
                    WHERE si.posting_date BETWEEN %(from_date)s AND %(to_date)s
                    AND si.docstatus = 1
                    {conditions.replace('pi.', 'si.')}
                    GROUP BY sii.item_code
                ) s ON p.item_code = s.item_code
            ) combined
            WHERE purchased_qty > (sold_qty * 1.5)  -- 50% more purchases than sales
            AND purchased_qty > 10  -- Minimum threshold to avoid noise
            ORDER BY excess_stock DESC
            LIMIT 20
        """, {
            'from_date': from_date,
            'to_date': to_date,
            'company': company
        }, as_dict=True)
        
    except Exception as e:
        frappe.log_error(f"Error in get_understock_risk_items: {str(e)}")
        data = []
    
    return {
        'labels': [d['item_code'] for d in data],
        'datasets': [{
            'label': 'Excess Stock Risk',
            'data': [d['excess_stock'] for d in data],
            'backgroundColor': '#f59e0b'
        }]
    }

@frappe.whitelist()
def get_consumption_ratio(filters=None):
    """Get purchase to sales ratio by category"""
    if not filters:
        filters = {}
    
    from_date = filters.get('from_date', add_months(today(), -3))
    to_date = filters.get('to_date', today())
    company = filters.get('company')
    
    conditions = ""
    if company:
        conditions += " AND pi.company = %(company)s"
    
    try:
        # Get purchase data by item group
        purchase_data = frappe.db.sql(f"""
            SELECT 
                COALESCE(i.item_group, 'Others') as item_group,
                SUM(pii.amount) as purchased_amount
            FROM `tabPurchase Invoice Item` pii
            INNER JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
            LEFT JOIN `tabItem` i ON i.name = pii.item_code
            WHERE pi.posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND pi.docstatus = 1
            {conditions}
            GROUP BY i.item_group
            ORDER BY purchased_amount DESC
            LIMIT 10
        """, {
            'from_date': from_date,
            'to_date': to_date,
            'company': company
        }, as_dict=True)
        
        if purchase_data:
            item_groups = [d['item_group'] for d in purchase_data]
            sales_data = frappe.db.sql(f"""
                SELECT 
                    COALESCE(i.item_group, 'Others') as item_group,
                    SUM(sii.amount) as sales_amount
                FROM `tabSales Invoice Item` sii
                INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
                INNER JOIN `tabItem` i ON i.name = sii.item_code
                INNER JOIN `tabItem Group` ig ON i.item_group = ig.name
                WHERE si.posting_date BETWEEN %(from_date)s AND %(to_date)s
                AND si.docstatus = 1
                AND i.item_group IN %(item_groups)s
                AND ig.name NOT IN ('Raw Material', 'Sub Assemblies', 'Consumable', 'Furniture', 'EXPENSE', 'FIXED ASSET')
                {conditions.replace('pi.', 'si.')}
                GROUP BY i.item_group
            """, {
                'from_date': from_date,
                'to_date': to_date,
                'company': company,
                'item_groups': item_groups
            }, as_dict=True)
            
            sales_dict = {d['item_group']: d['sales_amount'] for d in sales_data}
            
            data = []
            ratio_data = []
            for d in purchase_data:
                sales_amount = sales_dict.get(d['item_group'], 0)
                ratio = (d['purchased_amount'] / sales_amount * 100) if sales_amount > 0 else 0
                data.append({
                    'item_group': d['item_group'],
                    'ratio': ratio / 100
                })
                ratio_data.append(ratio)
        else:
            data = []
            ratio_data = []
        
    except Exception as e:
        frappe.log_error(f"Error in get_consumption_ratio: {str(e)}")
        data = []
        ratio_data = []
    
    return {
        'labels': [d['item_group'] for d in data],
        'datasets': [{
            'label': 'Purchase/Sales Ratio (%)',
            'data': ratio_data,
            'backgroundColor': ['#10b981', '#ef4444', '#f59e0b', '#3b82f6', '#8b5cf6', '#06b6d4', '#84cc16', '#f97316', '#ec4899', '#14b8a6']
        }]
    }

@frappe.whitelist(allow_guest=True)
def get_inventory_turnover_analysis(filters=None):
    """Get inventory turnover analysis"""
    if not filters:
        filters = {}
    
    from_date = filters.get('from_date', add_months(today(), -6))
    to_date = filters.get('to_date', today())
    company = filters.get('company')
    
    conditions = ""
    if company:
        conditions += " AND si.company = %(company)s"
    
    try:
        # Calculate inventory turnover by category
        # Turnover = Cost of Goods Sold / Average Inventory
        # Simplified: Sales Amount / Purchase Amount (as a proxy)
        data = frappe.db.sql(f"""
            SELECT 
                item_group,
                sales_amount,
                purchase_amount,
                CASE 
                    WHEN purchase_amount > 0 THEN (sales_amount / purchase_amount)
                    ELSE 0 
                END as turnover_ratio
            FROM (
                SELECT 
                    COALESCE(i.item_group, 'Others') as item_group,
                    COALESCE(s.sales_amount, 0) as sales_amount,
                    COALESCE(p.purchase_amount, 0) as purchase_amount
                FROM (
                    SELECT 
                        COALESCE(i.item_group, 'Others') as item_group,
                        SUM(sii.amount) as sales_amount
                    FROM `tabSales Invoice Item` sii
                    INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
                    INNER JOIN `tabItem` i ON i.name = sii.item_code
                    INNER JOIN `tabItem Group` ig ON i.item_group = ig.name
                    WHERE si.posting_date BETWEEN %(from_date)s AND %(to_date)s
                    AND si.docstatus = 1
                    AND ig.name NOT IN ('Raw Material', 'Sub Assemblies', 'Consumable', 'Furniture', 'EXPENSE', 'FIXED ASSET')
                    {conditions}
                    GROUP BY i.item_group
                ) s
                LEFT JOIN (
                    SELECT 
                        COALESCE(i.item_group, 'Others') as item_group,
                        SUM(pii.amount) as purchase_amount
                    FROM `tabPurchase Invoice Item` pii
                    INNER JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
                    LEFT JOIN `tabItem` i ON i.name = pii.item_code
                    WHERE pi.posting_date BETWEEN %(from_date)s AND %(to_date)s
                    AND pi.docstatus = 1
                    {conditions.replace('si.', 'pi.')}
                    GROUP BY i.item_group
                ) p ON s.item_group = p.item_group
            ) combined
            WHERE sales_amount > 0
            ORDER BY turnover_ratio DESC
            LIMIT 15
        """, {
            'from_date': from_date,
            'to_date': to_date,
            'company': company
        }, as_dict=True)
        
    except Exception as e:
        frappe.log_error(f"Error in get_inventory_turnover_analysis: {str(e)}")
        data = []
    
    return {
        'labels': [d['item_group'] for d in data],
        'datasets': [{
            'label': 'Turnover Ratio',
            'data': [d['turnover_ratio'] for d in data],
            'backgroundColor': '#06b6d4'
        }]
    }

@frappe.whitelist()
def get_stock_efficiency_score(filters=None):
    """Get overall stock efficiency score"""
    if not filters:
        filters = {}
    
    period = filters.get('period', 'month')
    company = filters.get('company')
    
    # Calculate date range based on period
    if period == 'month':
        from_date = add_months(today(), -1)
    elif period == 'quarter':
        from_date = add_months(today(), -3)
    else:  # year
        from_date = add_months(today(), -12)
    
    to_date = today()
    
    conditions = ""
    if company:
        conditions += " AND pi.company = %(company)s"
    
    try:
        # Get purchase data first
        purchase_data = frappe.db.sql(f"""
            SELECT 
                pii.item_code,
                SUM(pii.amount) as purchase_amount
            FROM `tabPurchase Invoice Item` pii
            INNER JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
            WHERE pi.posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND pi.docstatus = 1
            {conditions}
            GROUP BY pii.item_code
        """, {
            'from_date': from_date,
            'to_date': to_date,
            'company': company
        }, as_dict=True)
        
        if purchase_data:
            item_codes = [d['item_code'] for d in purchase_data]
            
            # Get sales data for purchased items
            sales_data = frappe.db.sql(f"""
                SELECT 
                    sii.item_code,
                    SUM(sii.amount) as sales_amount
                FROM `tabSales Invoice Item` sii
                INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
                WHERE si.posting_date BETWEEN %(from_date)s AND %(to_date)s
                AND si.docstatus = 1
                AND sii.item_code IN %(item_codes)s
                {conditions.replace('pi.', 'si.')}
                GROUP BY sii.item_code
            """, {
                'from_date': from_date,
                'to_date': to_date,
                'company': company,
                'item_codes': item_codes
            }, as_dict=True)
            
            sales_dict = {d['item_code']: d['sales_amount'] for d in sales_data}
            
            # Calculate efficiency ratios
            optimal_count = 0
            overstock_count = 0
            understock_count = 0
            
            for d in purchase_data:
                sales_amount = sales_dict.get(d['item_code'], 0)
                if sales_amount > 0:
                    ratio = d['purchase_amount'] / sales_amount
                    if 0.8 <= ratio <= 1.2:
                        optimal_count += 1
                    elif ratio > 1.2:
                        overstock_count += 1
                    else:
                        understock_count += 1
                else:
                    # Items with no sales are considered overstock
                    overstock_count += 1
            
            total_items = optimal_count + overstock_count + understock_count
            
            if total_items > 0:
                efficiency_data = [
                    {'metric': 'Optimal Stock', 'percentage': (optimal_count / total_items) * 100},
                    {'metric': 'Overstock', 'percentage': (overstock_count / total_items) * 100},
                    {'metric': 'Understock', 'percentage': (understock_count / total_items) * 100}
                ]
            else:
                efficiency_data = []
        else:
            efficiency_data = []
            
    except Exception as e:
        frappe.log_error(f"Error in get_stock_efficiency_score: {str(e)}")
        efficiency_data = []
    
    return {
        'labels': [d['metric'] for d in efficiency_data],
        'datasets': [{
            'label': 'Stock Efficiency (%)',
            'data': [d['percentage'] for d in efficiency_data],
            'backgroundColor': ['#10b981', '#ef4444', '#f59e0b']
        }]
    }

# KPI Functions for Number Cards
@frappe.whitelist()
def get_branch_performance_kpis(filters=None):
    """Get key performance indicators for branch performance"""
    if not filters:
        filters = {}
    
    from_date = filters.get('from_date', add_months(today(), -1))
    to_date = filters.get('to_date', today())
    company = filters.get('company')
    
    conditions = ""
    if company:
        conditions += " AND company = %(company)s"
    
    try:
        # Current period data
        current_data = frappe.db.sql(f"""
            SELECT 
                COUNT(name) as total_invoices,
                SUM(grand_total) as total_revenue,
                AVG(grand_total) as avg_invoice_value,
                COUNT(DISTINCT customer) as unique_customers,
                COUNT(DISTINCT branch) as active_branches
            FROM `tabSales Invoice`
            WHERE posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND docstatus = 1
            {conditions}
        """, {
            'from_date': from_date,
            'to_date': to_date,
            'company': company
        }, as_dict=True)
        
        # Previous period for comparison
        prev_from = add_months(getdate(from_date), -1)
        prev_to = add_days(getdate(from_date), -1)
        
        prev_data = frappe.db.sql(f"""
            SELECT 
                COUNT(name) as total_invoices,
                SUM(grand_total) as total_revenue,
                AVG(grand_total) as avg_invoice_value,
                COUNT(DISTINCT customer) as unique_customers
            FROM `tabSales Invoice`
            WHERE posting_date BETWEEN %(prev_from)s AND %(prev_to)s
            AND docstatus = 1
            {conditions}
        """, {
            'prev_from': prev_from,
            'prev_to': prev_to,
            'company': company
        }, as_dict=True)
        
        current = current_data[0] if current_data else {}
        previous = prev_data[0] if prev_data else {}
        
        def calculate_change(current_val, prev_val):
            if prev_val and prev_val > 0:
                return round(((current_val - prev_val) / prev_val) * 100, 1)
            return 0
        
        return {
            'total_revenue': {
                'value': current.get('total_revenue', 0),
                'change': calculate_change(current.get('total_revenue', 0), previous.get('total_revenue', 0))
            },
            'total_invoices': {
                'value': current.get('total_invoices', 0),
                'change': calculate_change(current.get('total_invoices', 0), previous.get('total_invoices', 0))
            },
            'avg_invoice_value': {
                'value': current.get('avg_invoice_value', 0),
                'change': calculate_change(current.get('avg_invoice_value', 0), previous.get('avg_invoice_value', 0))
            },
            'unique_customers': {
                'value': current.get('unique_customers', 0),
                'change': calculate_change(current.get('unique_customers', 0), previous.get('unique_customers', 0))
            },
            'active_branches': {
                'value': current.get('active_branches', 0),
                'change': 0
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_branch_performance_kpis: {str(e)}")
        return {
            'total_revenue': {'value': 0, 'change': 0},
            'total_invoices': {'value': 0, 'change': 0},
            'avg_invoice_value': {'value': 0, 'change': 0},
            'unique_customers': {'value': 0, 'change': 0},
            'active_branches': {'value': 0, 'change': 0}
        }

@frappe.whitelist()
def get_sku_performance_kpis(filters=None):
    """Get key performance indicators for SKU performance"""
    if not filters:
        filters = {}
    
    from_date = filters.get('from_date', add_months(today(), -1))
    to_date = filters.get('to_date', today())
    company = filters.get('company')
    
    conditions = ""
    if company:
        conditions += " AND si.company = %(company)s"
    
    try:
        # Current period data
        current_data = frappe.db.sql(f"""
            SELECT 
                COUNT(DISTINCT sii.item_code) as total_skus,
                SUM(sii.qty) as total_qty_sold,
                SUM(sii.amount) as total_sales_amount,
                COUNT(DISTINCT si.name) as total_transactions
            FROM `tabSales Invoice Item` sii
            INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
            INNER JOIN `tabItem` i ON sii.item_code = i.name
            INNER JOIN `tabItem Group` ig ON i.item_group = ig.name
            WHERE si.posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND si.docstatus = 1
            AND ig.name NOT IN ('Raw Material', 'Sub Assemblies', 'Consumable', 'Furniture', 'EXPENSE', 'FIXED ASSET')
            {conditions}
        """, {
            'from_date': from_date,
            'to_date': to_date,
            'company': company
        }, as_dict=True)
        
        # Get top performing SKU
        top_sku = frappe.db.sql(f"""
            SELECT 
                sii.item_code,
                SUM(sii.qty) as total_qty
            FROM `tabSales Invoice Item` sii
            INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
            INNER JOIN `tabItem` i ON sii.item_code = i.name
            INNER JOIN `tabItem Group` ig ON i.item_group = ig.name
            WHERE si.posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND si.docstatus = 1
            AND ig.name NOT IN ('Raw Material', 'Sub Assemblies', 'Consumable', 'Furniture', 'EXPENSE', 'FIXED ASSET')
            {conditions}
            GROUP BY sii.item_code
            ORDER BY total_qty DESC
            LIMIT 1
        """, {
            'from_date': from_date,
            'to_date': to_date,
            'company': company
        }, as_dict=True)
        
        current = current_data[0] if current_data else {}
        top_item = top_sku[0] if top_sku else {}
        
        return {
            'total_skus': {
                'value': current.get('total_skus', 0),
                'change': 0
            },
            'total_qty_sold': {
                'value': current.get('total_qty_sold', 0),
                'change': 0
            },
            'total_sales_amount': {
                'value': current.get('total_sales_amount', 0),
                'change': 0
            },
            'top_sku_qty': {
                'value': top_item.get('total_qty', 0),
                'change': 0,
                'item_code': top_item.get('item_code', 'N/A')
            },
            'avg_qty_per_sku': {
                'value': round(current.get('total_qty_sold', 0) / max(current.get('total_skus', 1), 1), 2),
                'change': 0
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_sku_performance_kpis: {str(e)}")
        return {
            'total_skus': {'value': 0, 'change': 0},
            'total_qty_sold': {'value': 0, 'change': 0},
            'total_sales_amount': {'value': 0, 'change': 0},
            'top_sku_qty': {'value': 0, 'change': 0, 'item_code': 'N/A'},
            'avg_qty_per_sku': {'value': 0, 'change': 0}
        }

@frappe.whitelist()
def get_purchase_sales_kpis(filters=None):
    """Get key performance indicators for purchase vs sales"""
    if not filters:
        filters = {}
    
    from_date = filters.get('from_date', add_months(today(), -3))
    to_date = filters.get('to_date', today())
    company = filters.get('company')
    
    conditions = ""
    if company:
        conditions += " AND company = %(company)s"
    
    try:
        # Purchase data
        purchase_data = frappe.db.sql(f"""
            SELECT 
                SUM(grand_total) as total_purchases,
                COUNT(name) as purchase_count
            FROM `tabPurchase Invoice`
            WHERE posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND docstatus = 1
            {conditions}
        """, {
            'from_date': from_date,
            'to_date': to_date,
            'company': company
        }, as_dict=True)
        
        # Sales data
        sales_data = frappe.db.sql(f"""
            SELECT 
                SUM(grand_total) as total_sales,
                COUNT(name) as sales_count
            FROM `tabSales Invoice`
            WHERE posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND docstatus = 1
            {conditions}
        """, {
            'from_date': from_date,
            'to_date': to_date,
            'company': company
        }, as_dict=True)
        
        purchase = purchase_data[0] if purchase_data else {}
        sales = sales_data[0] if sales_data else {}
        
        total_purchases = purchase.get('total_purchases', 0)
        total_sales = sales.get('total_sales', 0)
        
        # Calculate efficiency ratio
        efficiency_ratio = (total_sales / total_purchases * 100) if total_purchases > 0 else 0
        
        return {
            'total_purchases': {
                'value': total_purchases,
                'change': 0
            },
            'total_sales': {
                'value': total_sales,
                'change': 0
            },
            'purchase_count': {
                'value': purchase.get('purchase_count', 0),
                'change': 0
            },
            'sales_count': {
                'value': sales.get('sales_count', 0),
                'change': 0
            },
            'efficiency_ratio': {
                'value': round(efficiency_ratio, 1),
                'change': 0
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_purchase_sales_kpis: {str(e)}")
        return {
            'total_purchases': {'value': 0, 'change': 0},
            'total_sales': {'value': 0, 'change': 0},
            'purchase_count': {'value': 0, 'change': 0},
            'sales_count': {'value': 0, 'change': 0},
            'efficiency_ratio': {'value': 0, 'change': 0}
        }

@frappe.whitelist()
def get_daily_sales_kpis(filters=None):
    """Get key performance indicators for daily sales"""
    if not filters:
        filters = {}
    
    date = filters.get('date', today())
    company = filters.get('company')
    
    conditions = ""
    if company:
        conditions += " AND company = %(company)s"
    
    try:
        # Today's data
        today_data = frappe.db.sql(f"""
            SELECT 
                COUNT(name) as total_invoices,
                SUM(grand_total) as total_sales,
                AVG(grand_total) as avg_invoice_value,
                COUNT(DISTINCT customer) as unique_customers,
                COUNT(DISTINCT branch) as active_branches
            FROM `tabSales Invoice`
            WHERE posting_date = %(date)s
            AND docstatus = 1
            {conditions}
        """, {
            'date': date,
            'company': company
        }, as_dict=True)
        
        # Yesterday's data for comparison
        yesterday = add_days(getdate(date), -1)
        yesterday_data = frappe.db.sql(f"""
            SELECT 
                COUNT(name) as total_invoices,
                SUM(grand_total) as total_sales,
                AVG(grand_total) as avg_invoice_value,
                COUNT(DISTINCT customer) as unique_customers
            FROM `tabSales Invoice`
            WHERE posting_date = %(yesterday)s
            AND docstatus = 1
            {conditions}
        """, {
            'yesterday': yesterday,
            'company': company
        }, as_dict=True)
        
        today_stats = today_data[0] if today_data else {}
        yesterday_stats = yesterday_data[0] if yesterday_data else {}
        
        def calculate_change(current_val, prev_val):
            if prev_val and prev_val > 0:
                return round(((current_val - prev_val) / prev_val) * 100, 1)
            return 0
        
        return {
            'total_sales': {
                'value': today_stats.get('total_sales', 0),
                'change': calculate_change(today_stats.get('total_sales', 0), yesterday_stats.get('total_sales', 0))
            },
            'total_invoices': {
                'value': today_stats.get('total_invoices', 0),
                'change': calculate_change(today_stats.get('total_invoices', 0), yesterday_stats.get('total_invoices', 0))
            },
            'avg_invoice_value': {
                'value': today_stats.get('avg_invoice_value', 0),
                'change': calculate_change(today_stats.get('avg_invoice_value', 0), yesterday_stats.get('avg_invoice_value', 0))
            },
            'unique_customers': {
                'value': today_stats.get('unique_customers', 0),
                'change': calculate_change(today_stats.get('unique_customers', 0), yesterday_stats.get('unique_customers', 0))
            },
            'active_branches': {
                'value': today_stats.get('active_branches', 0),
                'change': 0
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_daily_sales_kpis: {str(e)}")
        return {
            'total_sales': {'value': 0, 'change': 0},
            'total_invoices': {'value': 0, 'change': 0},
            'avg_invoice_value': {'value': 0, 'change': 0},
            'unique_customers': {'value': 0, 'change': 0},
            'active_branches': {'value': 0, 'change': 0}
        }

@frappe.whitelist()
def get_purchase_kpis(filters=None):
    """Get key performance indicators for purchases"""
    if not filters:
        filters = {}
    
    from_date = filters.get('from_date', add_months(today(), -1))
    to_date = filters.get('to_date', today())
    company = filters.get('company')
    
    conditions = ""
    if company:
        conditions += " AND company = %(company)s"
    
    try:
        # Purchase Invoice data
        purchase_data = frappe.db.sql(f"""
            SELECT 
                COUNT(name) as total_invoices,
                SUM(grand_total) as total_amount,
                AVG(grand_total) as avg_invoice_value,
                COUNT(DISTINCT supplier) as unique_suppliers,
                SUM(outstanding_amount) as total_outstanding
            FROM `tabPurchase Invoice`
            WHERE posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND docstatus = 1
            {conditions}
        """, {
            'from_date': from_date,
            'to_date': to_date,
            'company': company
        }, as_dict=True)
        
        # Purchase Order data
        po_data = frappe.db.sql(f"""
            SELECT 
                COUNT(name) as total_orders,
                SUM(grand_total) as total_po_amount
            FROM `tabPurchase Order`
            WHERE transaction_date BETWEEN %(from_date)s AND %(to_date)s
            AND docstatus = 1
            {conditions.replace('posting_date', 'transaction_date')}
        """, {
            'from_date': from_date,
            'to_date': to_date,
            'company': company
        }, as_dict=True)
        
        purchase = purchase_data[0] if purchase_data else {}
        po = po_data[0] if po_data else {}
        
        return {
            'total_amount': {
                'value': purchase.get('total_amount', 0),
                'change': 0
            },
            'total_invoices': {
                'value': purchase.get('total_invoices', 0),
                'change': 0
            },
            'avg_invoice_value': {
                'value': purchase.get('avg_invoice_value', 0),
                'change': 0
            },
            'unique_suppliers': {
                'value': purchase.get('unique_suppliers', 0),
                'change': 0
            },
            'total_outstanding': {
                'value': purchase.get('total_outstanding', 0),
                'change': 0
            },
            'total_orders': {
                'value': po.get('total_orders', 0),
                'change': 0
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_purchase_kpis: {str(e)}")
        return {
            'total_amount': {'value': 0, 'change': 0},
            'total_invoices': {'value': 0, 'change': 0},
            'avg_invoice_value': {'value': 0, 'change': 0},
            'unique_suppliers': {'value': 0, 'change': 0},
            'total_outstanding': {'value': 0, 'change': 0},
            'total_orders': {'value': 0, 'change': 0}
        }

@frappe.whitelist()
def get_branch_revenue_comparison_detailed(filters=None):
    """Get branch revenue, profit, margin, and region for franchise performance chart"""
    base_query = """
        SELECT 
            COALESCE(si.cost_center, 'No Branch') as branch,
            SUM(si.grand_total) as total_revenue,
            SUM(si.grand_total * 0.4) as profit,
            (SUM(si.grand_total * 0.4) / NULLIF(SUM(si.grand_total),0)) * 100 as margin,
            MAX(si.cost_center) as region
        FROM `tabSales Invoice` si
        WHERE 
            si.docstatus = 1
            AND si.status NOT IN ('Cancelled', 'Return')
    """
    try:
        # Apply filters
        query, params = apply_filters_to_query(base_query, filters)
        query += """
        GROUP BY si.cost_center
        ORDER BY total_revenue DESC
        """
        data = frappe.db.sql(query, params, as_dict=True)
        if not data:
            data = []
        labels = [d['branch'] for d in data]
        revenue = [float(d['total_revenue'] or 0) for d in data]
        profit = [float(d['profit'] or 0) for d in data]
        margin = [float(d['margin'] or 0) for d in data]
        region = [d['region'] or '' for d in data]
    except Exception as e:
        frappe.log_error(f"Error in get_branch_revenue_comparison_detailed: {str(e)}")
        labels, revenue, profit, margin, region = [], [], [], [], []
    return {
        'labels': labels,
        'datasets': [{
            'label': 'Revenue (₹)',
            'data': revenue,
            'backgroundColor': '#10b981'
        }],
        'profit': profit,
        'margin': margin,
        'region': region
    }

@frappe.whitelist()
def get_franchise_monthly_trend(filters=None):
    """
    Returns monthly revenue, profit, and margin for all branches combined.
    """
    base_query = """
        SELECT 
            DATE_FORMAT(si.posting_date, '%%b %%y') as month,
            SUM(si.grand_total) as revenue,
            SUM(si.grand_total * 0.4) as profit
        FROM `tabSales Invoice` si
        WHERE 
            si.docstatus = 1
            AND si.status NOT IN ('Cancelled', 'Return')
    """
    try:
        query, params = apply_filters_to_query(base_query, filters)
        query += """
        GROUP BY DATE_FORMAT(si.posting_date, '%%Y-%%m')
        ORDER BY DATE_FORMAT(si.posting_date, '%%Y-%%m')
        """
        data = frappe.db.sql(query, params, as_dict=True)
        if not data:
            data = []
        labels = [d['month'] for d in data]
        revenue = [float(d['revenue'] or 0) / 100000 for d in data]  # Convert to Lakhs
        profit = [float(d['profit'] or 0) / 100000 for d in data]    # Convert to Lakhs
        margin = [
            (float(d['profit']) / float(d['revenue']) * 100) if d['revenue'] else 0
            for d in data
        ]
    except Exception as e:
        frappe.log_error(f"Error in get_franchise_monthly_trend: {str(e)}")
        labels, revenue, profit, margin = [], [], [], []
    return {
        'labels': labels,
        'revenue': revenue,
        'profit': profit,
        'margin': margin
    }

@frappe.whitelist()
def get_sales_velocity_trends(filters=None):
    """
    Returns monthly sales velocity and growth rate for the chart.
    """
    # For now, use sample data. Replace with real query as needed.
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    velocity = [1100, 400, 300, 250, 200, 150, 140, 130, 120, 1250, 500, 600]
    growth = [50, -30, 20, 10, 5, -10, 40, 30, 45, -20, -25, 10]
    return {
        'labels': months,
        'velocity': velocity,
        'growth': growth
    }
