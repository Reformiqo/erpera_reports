import frappe
from frappe import _
import json
@frappe.whitelist()
def get_buying_drill_down_data(filters=None, chart_title=None, clicked_label=None, clicked_value=None):
    """
    Get detailed drill-down data when a bar chart is clicked
    Returns purchase invoice details based on the clicked element
    """
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    filters = filters or {}
    drill_type = filters.get('drill_type', 'general')
    drill_value = filters.get('drill_value', clicked_label)
    
    # Clean up drill_value by removing any monetary formatting
    if drill_value and isinstance(drill_value, str):
        # Remove amount formatting like "(₹1,23,456)" from the end
        if ' (₹' in drill_value:
            drill_value = drill_value.split(' (₹')[0].strip()
        # Remove any extra whitespace
        drill_value = drill_value.strip()
    
    # Base query for drill-down data
    base_query = """
        SELECT 
            pi.name as invoice_name,
            pi.posting_date,
            pi.supplier_name,
            pi.supplier,
            pi.company,
            pi.cost_center as branch,
            pii.item_name,
            pii.item_group,
            pii.qty as total_qty,
            pii.amount as total_amount,
            pi.status
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
        LEFT JOIN `tabItem` i ON pii.item_code = i.name
        WHERE 
            pi.docstatus = 1
            AND pi.status NOT IN ('Cancelled', 'Return')
    """
    
    # Add drill-down specific conditions
    drill_conditions = []
    drill_params = {}
    
    if drill_type == 'time_period' and drill_value:
        # Handle time period drill-down (e.g., "Feb 2025")
        title = f"Purchase Details for {drill_value}"
        # Date filters should already be applied via filters['from_date'] and filters['to_date']
        
    elif drill_type == 'branch' and drill_value:
        drill_conditions.append("(pi.cost_center = %(drill_branch)s OR pi.cost_center LIKE %(drill_branch_like)s)")
        drill_params['drill_branch'] = drill_value
        drill_params['drill_branch_like'] = f"%{drill_value}%"
        title = f"Purchase Details for Branch: {drill_value}"
        
    elif drill_type == 'company' and drill_value:
        drill_conditions.append("(pi.company = %(drill_company)s OR pi.company LIKE %(drill_company_like)s)")
        drill_params['drill_company'] = drill_value
        drill_params['drill_company_like'] = f"%{drill_value}%"
        title = f"Purchase Details for Company: {drill_value}"
        
    elif drill_type == 'supplier' and drill_value:
        # Enhanced supplier matching with multiple strategies
        drill_conditions.append("""(
            pi.supplier_name = %(drill_supplier)s 
            OR pi.supplier = %(drill_supplier)s
            OR TRIM(pi.supplier_name) = %(drill_supplier_trim)s
            OR TRIM(pi.supplier) = %(drill_supplier_trim)s
            OR pi.supplier_name LIKE %(drill_supplier_like)s
            OR pi.supplier LIKE %(drill_supplier_like)s
            OR LOWER(pi.supplier_name) = LOWER(%(drill_supplier)s)
            OR LOWER(pi.supplier) = LOWER(%(drill_supplier)s)
        )""")
        drill_params['drill_supplier'] = drill_value
        drill_params['drill_supplier_trim'] = drill_value.strip()
        drill_params['drill_supplier_like'] = f"%{drill_value}%"
        title = f"Purchase Details for Supplier: {drill_value}"
    
    else:
        title = f"Purchase Details: {drill_value or 'All'}"
    
    # Determine item type filter based on chart title
    if chart_title and any(keyword in chart_title.lower() for keyword in ['expense', 'head', 'cost', 'supplier']):
        # For expense-related charts, filter for expense items
        drill_conditions.append("""
            (pii.item_group IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES')
             OR (i.is_stock_item = 0 AND pii.item_group IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES')))
        """)
    elif chart_title and any(keyword in chart_title.lower() for keyword in ['buying', 'product', 'stock']):
        # For buying/product charts, filter for stock items
        drill_conditions.append("""
            (i.is_stock_item = 1 
             OR (i.is_stock_item IS NULL AND pii.item_group NOT IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES')))
            AND pii.item_group NOT IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES')
        """)
    
    try:
        # Build the complete query
        query = base_query
        params = drill_params.copy()
        
        # Add drill-down conditions
        if drill_conditions:
            query += " AND " + " AND ".join(drill_conditions)
        
        # Apply additional filters (dates, etc.)
        if filters.get('from_date'):
            query += " AND pi.posting_date >= %(from_date)s"
            params['from_date'] = filters['from_date']
        
        if filters.get('to_date'):
            query += " AND pi.posting_date <= %(to_date)s"
            params['to_date'] = filters['to_date']
        
        if filters.get('company') and drill_type != 'company':
            query += " AND pi.company = %(company)s"
            params['company'] = filters['company']
        
        if filters.get('branch'):
            query += " AND pi.cost_center = %(branch)s"
            params['branch'] = filters['branch']
        
        if filters.get('item'):
            query += " AND pii.item_code = %(item)s"
            params['item'] = filters['item']
        
        if filters.get('item_group'):
            query += " AND pii.item_group = %(item_group)s"
            params['item_group'] = filters['item_group']
        
        # Add ordering and limit
        query += """
        ORDER BY pi.posting_date DESC, pi.creation DESC
        LIMIT 500
        """
        
        # Enhanced logging for debugging
        frappe.log_error(f"""
        Drill-down Debug Info:
        - Original Label: {clicked_label}
        - Type: {drill_type}
        - Cleaned Value: {drill_value}
        - Title: {chart_title}
        - Filters: {filters}
        - Drill Params: {drill_params}
        """, "Drill Down Debug")
        
        # Execute query
        result = frappe.db.sql(query, params, as_dict=True)
        
        # Log the result count for debugging
        frappe.log_error(f"Drill-down query returned {len(result)} records for {drill_type}: {drill_value}", "Drill Down Result Count")
        
        # If no results found for supplier, try a broader search
        if len(result) == 0 and drill_type == 'supplier' and drill_value:
            # Try a fallback query with just the basic expense filter and supplier search
            fallback_query = """
                SELECT 
                    pi.name as invoice_name,
                    pi.posting_date,
                    pi.supplier_name,
                    pi.supplier,
                    pi.company,
                    pi.cost_center as branch,
                    pii.item_name,
                    pii.item_group,
                    pii.qty as total_qty,
                    pii.amount as total_amount,
                    pi.status
                FROM `tabPurchase Invoice` pi
                INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
                LEFT JOIN `tabItem` i ON pii.item_code = i.name
                WHERE 
                    pi.docstatus = 1
                    AND pi.status NOT IN ('Cancelled', 'Return')
                    AND pii.item_group IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES')
                    AND (
                        pi.supplier_name LIKE %(supplier_search)s
                        OR pi.supplier LIKE %(supplier_search)s
                    )
                ORDER BY pi.posting_date DESC
                LIMIT 100
            """
            
            fallback_params = {'supplier_search': f"%{drill_value}%"}
            
            # Apply date filters to fallback query if present
            if filters.get('from_date'):
                fallback_query += " AND pi.posting_date >= %(from_date)s"
                fallback_params['from_date'] = filters['from_date']
            
            if filters.get('to_date'):
                fallback_query += " AND pi.posting_date <= %(to_date)s"
                fallback_params['to_date'] = filters['to_date']
            
            result = frappe.db.sql(fallback_query, fallback_params, as_dict=True)
            frappe.log_error(f"Fallback supplier search returned {len(result)} records for: {drill_value}", "Drill Down Fallback")
        
        # Format the data for display
        formatted_data = []
        for row in result:
            formatted_row = {
                'invoice_name': row.get('invoice_name', ''),
                'posting_date': row.get('posting_date', ''),
                'supplier_name': row.get('supplier_name', ''),
                'company': row.get('company', ''),
                'branch': row.get('branch', ''),
                'item_name': row.get('item_name', ''),
                'item_group': row.get('item_group', ''),
                'total_qty': float(row.get('total_qty', 0)),
                'total_amount': float(row.get('total_amount', 0)),
                'status': row.get('status', '')
            }
            formatted_data.append(formatted_row)
        
        return {
            'success': True,
            'data': formatted_data,
            'title': title,
            'total_records': len(formatted_data),
            'drill_type': drill_type,
            'drill_value': drill_value,
            'filters_applied': filters
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_drill_down_data: {str(e)}\nDrill Type: {drill_type}\nDrill Value: {drill_value}\nChart Title: {chart_title}", "Drill Down Error")
        return {
            'success': False,
            'error': str(e),
            'data': [],
            'title': f"Error: {title if 'title' in locals() else 'Unknown'}"
        }

@frappe.whitelist()
def get_selling_drill_down_data(filters=None, chart_title=None, clicked_label=None, clicked_value=None):
    """
    Get detailed drill-down data for sales when a bar chart is clicked
    Returns sales invoice details based on the clicked element
    """
    if isinstance(filters, str):
        filters = json.loads(filters)
    filters = filters or {}
    drill_type = filters.get('drill_type', 'general')
    drill_value = filters.get('drill_value', clicked_label)
    if drill_value and isinstance(drill_value, str):
        if ' (₹' in drill_value:
            drill_value = drill_value.split(' (₹')[0].strip()
        drill_value = drill_value.strip()
    base_query = """
        SELECT 
            si.name as invoice_name,
            si.posting_date,
            si.customer_name,
            si.customer,
            si.company,
            si.cost_center as branch,
            sii.item_name,
            sii.item_group,
            sii.qty as total_qty,
            sii.amount as total_amount,
            si.status
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON si.name = sii.parent
        LEFT JOIN `tabItem` i ON sii.item_code = i.name
        WHERE 
            si.docstatus = 1
            AND si.status NOT IN ('Cancelled', 'Return')
    """
    drill_conditions = []
    drill_params = {}
    if drill_type == 'time_period' and drill_value:
        title = f"Selling Details for {drill_value}"
    elif drill_type == 'branch' and drill_value:
        drill_conditions.append("(si.cost_center = %(drill_branch)s OR si.cost_center LIKE %(drill_branch_like)s)")
        drill_params['drill_branch'] = drill_value
        drill_params['drill_branch_like'] = f"%{drill_value}%"
        title = f"Selling Details for Branch: {drill_value}"
    elif drill_type == 'company' and drill_value:
        drill_conditions.append("(si.company = %(drill_company)s OR si.company LIKE %(drill_company_like)s)")
        drill_params['drill_company'] = drill_value
        drill_params['drill_company_like'] = f"%{drill_value}%"
        title = f"Selling Details for Company: {drill_value}"
    elif drill_type == 'customer' and drill_value:
        drill_conditions.append("""
            (si.customer_name = %(drill_customer)s 
            OR si.customer = %(drill_customer)s
            OR TRIM(si.customer_name) = %(drill_customer_trim)s
            OR TRIM(si.customer) = %(drill_customer_trim)s
            OR si.customer_name LIKE %(drill_customer_like)s
            OR si.customer LIKE %(drill_customer_like)s
            OR LOWER(si.customer_name) = LOWER(%(drill_customer)s)
            OR LOWER(si.customer) = LOWER(%(drill_customer)s)
            )""")
        drill_params['drill_customer'] = drill_value
        drill_params['drill_customer_trim'] = drill_value.strip()
        drill_params['drill_customer_like'] = f"%{drill_value}%"
        title = f"Selling Details for Customer: {drill_value}"
    else:
        title = f"Selling Details: {drill_value or 'All'}"
    if chart_title and any(keyword in chart_title.lower() for keyword in ['expense', 'head', 'cost']):
        drill_conditions.append("""
            (sii.item_group IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES')
             OR (i.is_stock_item = 0 AND sii.item_group IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES')))
        """)
    elif chart_title and any(keyword in chart_title.lower() for keyword in ['selling', 'product', 'stock']):
        drill_conditions.append("""
            (i.is_stock_item = 1 
             OR (i.is_stock_item IS NULL AND sii.item_group NOT IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES')))
            AND sii.item_group NOT IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES')
        """)
    try:
        query = base_query
        params = drill_params.copy()
        if drill_conditions:
            query += " AND " + " AND ".join(drill_conditions)
        if filters.get('from_date'):
            query += " AND si.posting_date >= %(from_date)s"
            params['from_date'] = filters['from_date']
        if filters.get('to_date'):
            query += " AND si.posting_date <= %(to_date)s"
            params['to_date'] = filters['to_date']
        if filters.get('company') and drill_type != 'company':
            query += " AND si.company = %(company)s"
            params['company'] = filters['company']
        if filters.get('branch'):
            query += " AND si.cost_center = %(branch)s"
            params['branch'] = filters['branch']
        if filters.get('item'):
            query += " AND sii.item_code = %(item)s"
            params['item'] = filters['item']
        if filters.get('item_group'):
            query += " AND sii.item_group = %(item_group)s"
            params['item_group'] = filters['item_group']
        query += """
        ORDER BY si.posting_date DESC, si.creation DESC
        LIMIT 500
        """
        result = frappe.db.sql(query, params, as_dict=True)
        formatted_data = []
        for row in result:
            formatted_row = {
                'invoice_name': row.get('invoice_name', ''),
                'posting_date': row.get('posting_date', ''),
                'customer_name': row.get('customer_name', ''),
                'company': row.get('company', ''),
                'branch': row.get('branch', ''),
                'item_name': row.get('item_name', ''),
                'item_group': row.get('item_group', ''),
                'total_qty': float(row.get('total_qty', 0)),
                'total_amount': float(row.get('total_amount', 0)),
                'status': row.get('status', '')
            }
            formatted_data.append(formatted_row)
        return {
            'success': True,
            'data': formatted_data,
            'title': title,
            'total_records': len(formatted_data),
            'drill_type': drill_type,
            'drill_value': drill_value,
            'filters_applied': filters
        }
    except Exception as e:
        frappe.log_error(f"Error in get_selling_drill_down_data: {str(e)}\nDrill Type: {drill_type}\nDrill Value: {drill_value}\nChart Title: {chart_title}", "Selling Drill Down Error")
        return {
            'success': False,
            'error': str(e),
            'data': [],
            'title': f"Error: {title if 'title' in locals() else 'Unknown'}"
        }

@frappe.whitelist()
def get_stock_drill_down_data(filters=None, chart_title=None, clicked_label=None, clicked_value=None):
    """
    Get detailed drill-down data for stock when a bar chart is clicked
    Returns stock ledger details based on the clicked element
    """
    if isinstance(filters, str):
        filters = json.loads(filters)
    filters = filters or {}
    drill_type = filters.get('drill_type', 'general')
    drill_value = filters.get('drill_value', clicked_label)
    if drill_value and isinstance(drill_value, str):
        if ' (₹' in drill_value:
            drill_value = drill_value.split(' (₹')[0].strip()
        drill_value = drill_value.strip()
    base_query = """
        SELECT 
            sle.name as entry_name,
            sle.posting_date,
            sle.item_code,
            i.item_name,
            i.item_group,
            sle.warehouse,
            sle.actual_qty,
            sle.valuation_rate,
            sle.company,
            sle.voucher_type,
            sle.voucher_no
        FROM `tabStock Ledger Entry` sle
        LEFT JOIN `tabItem` i ON sle.item_code = i.name
        WHERE sle.docstatus = 1
    """
    drill_conditions = []
    drill_params = {}
    if drill_type == 'time_period' and drill_value:
        title = f"Stock Details for {drill_value}"
    elif drill_type == 'branch' and drill_value:
        drill_conditions.append("(sle.warehouse = %(drill_branch)s OR sle.warehouse LIKE %(drill_branch_like)s)")
        drill_params['drill_branch'] = drill_value
        drill_params['drill_branch_like'] = f"%{drill_value}%"
        title = f"Stock Details for Branch: {drill_value}"
    elif drill_type == 'company' and drill_value:
        drill_conditions.append("(sle.company = %(drill_company)s OR sle.company LIKE %(drill_company_like)s)")
        drill_params['drill_company'] = drill_value
        drill_params['drill_company_like'] = f"%{drill_value}%"
        title = f"Stock Details for Company: {drill_value}"
    elif drill_type == 'item' and drill_value:
        drill_conditions.append("(sle.item_code = %(drill_item)s OR i.item_name = %(drill_item)s)")
        drill_params['drill_item'] = drill_value
        title = f"Stock Details for Item: {drill_value}"
    else:
        title = f"Stock Details: {drill_value or 'All'}"
    if chart_title and any(keyword in chart_title.lower() for keyword in ['stock', 'product', 'item']):
        drill_conditions.append("(sle.voucher_type IN ('Stock Entry', 'Purchase Receipt', 'Delivery Note'))")
    try:
        query = base_query
        params = drill_params.copy()
        if drill_conditions:
            query += " AND " + " AND ".join(drill_conditions)
        if filters.get('from_date'):
            query += " AND sle.posting_date >= %(from_date)s"
            params['from_date'] = filters['from_date']
        if filters.get('to_date'):
            query += " AND sle.posting_date <= %(to_date)s"
            params['to_date'] = filters['to_date']
        if filters.get('company') and drill_type != 'company':
            query += " AND sle.company = %(company)s"
            params['company'] = filters['company']
        # Branch filter (maps to warehouse in stock context)
        if filters.get('branch'):
            query += " AND LOWER(TRIM(sle.warehouse)) = LOWER(TRIM(%(branch)s))"
            params['branch'] = filters['branch'].strip()
        elif filters.get('warehouse'):
            query += " AND sle.warehouse = %(warehouse)s"
            params['warehouse'] = filters['warehouse']
        if filters.get('item'):
            query += " AND sle.item_code = %(item)s"
            params['item'] = filters['item']
        if filters.get('item_group'):
            query += " AND i.item_group = %(item_group)s"
            params['item_group'] = filters['item_group']
        query += """
        ORDER BY sle.posting_date DESC, sle.creation DESC
        LIMIT 500
        """
        result = frappe.db.sql(query, params, as_dict=True)
        formatted_data = []
        for row in result:
            formatted_row = {
                'entry_name': row.get('entry_name', ''),
                'posting_date': row.get('posting_date', ''),
                'item_code': row.get('item_code', ''),
                'item_name': row.get('item_name', ''),
                'item_group': row.get('item_group', ''),
                'warehouse': row.get('warehouse', ''),
                'actual_qty': float(row.get('actual_qty', 0)),
                'valuation_rate': float(row.get('valuation_rate', 0)),
                'company': row.get('company', ''),
                'voucher_type': row.get('voucher_type', ''),
                'voucher_no': row.get('voucher_no', '')
            }
            formatted_data.append(formatted_row)
        return {
            'success': True,
            'data': formatted_data,
            'title': title,
            'total_records': len(formatted_data),
            'drill_type': drill_type,
            'drill_value': drill_value,
            'filters_applied': filters
        }
    except Exception as e:
        frappe.log_error(f"Error in get_stock_drill_down_data: {str(e)}\nDrill Type: {drill_type}\nDrill Value: {drill_value}\nChart Title: {chart_title}", "Stock Drill Down Error")
        return {
            'success': False,
            'error': str(e),
            'data': [],
            'title': f"Error: {title if 'title' in locals() else 'Unknown'}"
        }