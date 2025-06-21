import frappe
import json

@frappe.whitelist()
def get_filtered_stock_data(filters=None):
    """
    Example function demonstrating the new filter system for bar charts.
    This function shows how to handle various filter types and return filtered data.
    """
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    filters = filters or {}
    
    # Build filter conditions
    conditions = []
    params = {}
    
    # Date range filters
    if filters.get('from_date'):
        conditions.append("si.posting_date >= %(from_date)s")
        params['from_date'] = filters['from_date']
    
    if filters.get('to_date'):
        conditions.append("si.posting_date <= %(to_date)s")
        params['to_date'] = filters['to_date']
    
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
    
    # Branch filter
    if filters.get('branch'):
        conditions.append("si.branch = %(branch)s")
        params['branch'] = filters['branch']
    
    # Custom filters (example for warehouse)
    if filters.get('warehouse'):
        conditions.append("sii.warehouse = %(warehouse)s")
        params['warehouse'] = filters['warehouse']
    
    # Build the WHERE clause
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    # Query with filters
    query = f"""
        SELECT 
            i.item_name,
            SUM(sii.qty) as total_qty,
            SUM(sii.amount) as total_amount
        FROM `tabSales Invoice Item` sii
        JOIN `tabSales Invoice` si ON sii.parent = si.name
        JOIN `tabItem` i ON sii.item_code = i.name
        WHERE {where_clause}
        GROUP BY i.item_name
        ORDER BY total_amount DESC
        LIMIT 10
    """
    
    try:
        result = frappe.db.sql(query, params, as_dict=True)
        
        # Prepare chart data
        labels = [row.item_name for row in result]
        data = [float(row.total_amount) for row in result]
        
        return {
            'labels': labels,
            'data': data,
            'backgroundColor': '#667eea',
            'filters_applied': filters
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_filtered_stock_data: {str(e)}")
        return {
            'labels': [],
            'data': [],
            'backgroundColor': '#667eea',
            'error': str(e)
        }

@frappe.whitelist()
def get_filter_options():
    """
    Get filter options for the chart filters.
    This function provides the available options for dropdown filters.
    """
    try:
        # Get items for item filter
        item_list = frappe.db.sql("""
            SELECT name as value, item_name as label 
            FROM `tabItem` 
            WHERE disabled = 0 
            ORDER BY item_name 
            LIMIT 100
        """, as_dict=True)
        
        # Get item groups for item group filter
        item_groups = frappe.db.sql("""
            SELECT name as value, item_group_name as label 
            FROM `tabItem Group` 
            ORDER BY item_group_name
        """, as_dict=True)
        
        # Get companies for company filter
        companies = frappe.db.sql("""
            SELECT name as value, company_name as label 
            FROM `tabCompany` 
            ORDER BY company_name
        """, as_dict=True)
        
        # Get warehouses for custom warehouse filter
        warehouses = frappe.db.sql("""
            SELECT name as value, warehouse_name as label 
            FROM `tabWarehouse` 
            WHERE is_group = 0 
            ORDER BY warehouse_name
        """, as_dict=True)
        
        return {
            'item_list': item_list,
            'item_groups': item_groups,
            'companies': companies,
            'warehouses': warehouses
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_filter_options: {str(e)}")
        return {
            'item_list': [],
            'item_groups': [],
            'companies': [],
            'warehouses': []
        }

@frappe.whitelist()
def get_comprehensive_filter_options():
    """
    Get comprehensive filter options with fallback data if database queries fail.
    This function provides both real data and sample data as fallback.
    """
    try:
        # Try to get real data from database
        item_list = frappe.db.sql("""
            SELECT name as value, item_name as label 
            FROM `tabItem` 
            WHERE disabled = 0 
            ORDER BY item_name 
            LIMIT 50
        """, as_dict=True)
        
        item_groups = frappe.db.sql("""
            SELECT name as value, item_group_name as label 
            FROM `tabItem Group` 
            ORDER BY item_group_name
            LIMIT 20
        """, as_dict=True)
        
        companies = frappe.db.sql("""
            SELECT name as value, company_name as label 
            FROM `tabCompany` 
            ORDER BY company_name
            LIMIT 10
        """, as_dict=True)
        
        branches = frappe.db.sql("""
            SELECT name as value, branch_name as label 
            FROM `tabBranch` 
            ORDER BY branch_name
            LIMIT 10
        """, as_dict=True)
        
        # If no real data, provide sample data
        if not item_list:
            item_list = [
                {'value': 'ITEM-001', 'label': 'Laptop Dell XPS 13', 'selected': False},
                {'value': 'ITEM-002', 'label': 'Wireless Mouse Logitech', 'selected': False},
                {'value': 'ITEM-003', 'label': 'Mechanical Keyboard', 'selected': False},
                {'value': 'ITEM-004', 'label': 'USB-C Cable', 'selected': False},
                {'value': 'ITEM-005', 'label': 'External Hard Drive 1TB', 'selected': False},
                {'value': 'ITEM-006', 'label': 'Wireless Headphones', 'selected': False},
                {'value': 'ITEM-007', 'label': 'Webcam HD', 'selected': False},
                {'value': 'ITEM-008', 'label': 'Monitor 24"', 'selected': False}
            ]
        
        if not item_groups:
            item_groups = [
                {'value': 'Electronics', 'label': 'Electronics', 'selected': False},
                {'value': 'Accessories', 'label': 'Accessories', 'selected': False},
                {'value': 'Computers', 'label': 'Computers', 'selected': False},
                {'value': 'Peripherals', 'label': 'Peripherals', 'selected': False},
                {'value': 'Storage', 'label': 'Storage', 'selected': False}
            ]
        
        if not companies:
            companies = [
                {'value': 'Company A', 'label': 'Company A', 'selected': False},
                {'value': 'Company B', 'label': 'Company B', 'selected': False},
                {'value': 'Company C', 'label': 'Company C', 'selected': False},
                {'value': 'Company D', 'label': 'Company D', 'selected': False}
            ]
        
        if not branches:
            branches = [
                {'value': 'Branch 1', 'label': 'Main Branch', 'selected': False},
                {'value': 'Branch 2', 'label': 'North Branch', 'selected': False},
                {'value': 'Branch 3', 'label': 'South Branch', 'selected': False},
                {'value': 'Branch 4', 'label': 'East Branch', 'selected': False},
                {'value': 'Branch 5', 'label': 'West Branch', 'selected': False}
            ]
        
        return {
            'item_list': item_list,
            'item_groups': item_groups,
            'companies': companies,
            'branches': branches
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_comprehensive_filter_options: {str(e)}")
        # Return sample data as fallback
        return {
            'item_list': [
                {'value': 'ITEM-001', 'label': 'Laptop Dell XPS 13', 'selected': False},
                {'value': 'ITEM-002', 'label': 'Wireless Mouse Logitech', 'selected': False},
                {'value': 'ITEM-003', 'label': 'Mechanical Keyboard', 'selected': False},
                {'value': 'ITEM-004', 'label': 'USB-C Cable', 'selected': False},
                {'value': 'ITEM-005', 'label': 'External Hard Drive 1TB', 'selected': False}
            ],
            'item_groups': [
                {'value': 'Electronics', 'label': 'Electronics', 'selected': False},
                {'value': 'Accessories', 'label': 'Accessories', 'selected': False},
                {'value': 'Computers', 'label': 'Computers', 'selected': False},
                {'value': 'Peripherals', 'label': 'Peripherals', 'selected': False}
            ],
            'companies': [
                {'value': 'Company A', 'label': 'Company A', 'selected': False},
                {'value': 'Company B', 'label': 'Company B', 'selected': False},
                {'value': 'Company C', 'label': 'Company C', 'selected': False}
            ],
            'branches': [
                {'value': 'Branch 1', 'label': 'Main Branch', 'selected': False},
                {'value': 'Branch 2', 'label': 'North Branch', 'selected': False},
                {'value': 'Branch 3', 'label': 'South Branch', 'selected': False},
                {'value': 'Branch 4', 'label': 'East Branch', 'selected': False}
            ]
        } 