import frappe
from frappe import _
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
    
    # Date range filters
    if filters.get('from_date'):
        conditions.append("pi.posting_date >= %(from_date)s")
        params['from_date'] = filters['from_date']
    
    if filters.get('to_date'):
        conditions.append("pi.posting_date <= %(to_date)s")
        params['to_date'] = filters['to_date']
    
    # Item filter
    if filters.get('item'):
        conditions.append("pii.item_code = %(item)s")
        params['item'] = filters['item']
    
    # Item group filter
    if filters.get('item_group'):
        conditions.append("i.item_group = %(item_group)s")
        params['item_group'] = filters['item_group']
    
    # Company filter
    if filters.get('company'):
        conditions.append("pi.company = %(company)s")
        params['company'] = filters['company']
    
    # Branch filter
    if filters.get('branch'):
        conditions.append("pi.cost_center = %(branch)s")
        params['branch'] = filters['branch']
    
    # Custom filters
    if filters.get('warehouse'):
        conditions.append("pii.warehouse = %(warehouse)s")
        params['warehouse'] = filters['warehouse']
    
    # Add existing conditions
    if conditions:
        if "where" in base_query.lower():
            base_query += " AND " + " AND ".join(conditions)
        else:
            base_query += " WHERE " + " AND ".join(conditions)
    
    return base_query, params

@frappe.whitelist()
def get_mota_chart_data(filters=None):
    return {
        "labels": ["Jan", "Apr", "May", "Jun"],
        "data": [84200, 28100, 85800, 62500],
        "filters_applied": filters
    }

@frappe.whitelist()
def get_total_branch_wise_buying(filters=None):
    """
    Chart Name: Total Buying
    Chart Type: Bar
    Note 1: Branch wise and company wise different chart
    Note 2: Only Choose item which is in stock not choose expense or service item
    """
    
    # Main query for branch-wise data
    branch_query = """
    SELECT
        COALESCE(pi.cost_center, 'Unknown Branch') AS branch,
        DATE_FORMAT(pi.posting_date, '%%b %%Y') AS month_year,
        DATE_FORMAT(pi.posting_date, '%%Y-%%m') AS sort_date,
        SUM(pii.amount) AS total_amount,
        COUNT(DISTINCT pi.name) AS invoice_count
    FROM `tabPurchase Invoice` pi
    INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
    LEFT JOIN `tabItem` i ON pii.item_code = i.name
    WHERE 
        pi.docstatus = 1
        AND pi.status NOT IN ('Cancelled', 'Return')
        AND (
            i.is_stock_item = 1 
            OR (i.is_stock_item IS NULL AND pii.item_group NOT IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES'))
        )
        AND pii.item_group NOT IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES')
        AND pi.cost_center IS NOT NULL
        AND pi.cost_center != ''
    """
    
    # Query for company-wise data
    company_query = """
    SELECT
        COALESCE(pi.company, 'Unknown Company') AS company,
        DATE_FORMAT(pi.posting_date, '%%b %%Y') AS month_year,
        DATE_FORMAT(pi.posting_date, '%%Y-%%m') AS sort_date,
        SUM(pii.amount) AS total_amount,
        COUNT(DISTINCT pi.name) AS invoice_count
    FROM `tabPurchase Invoice` pi
    INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
    LEFT JOIN `tabItem` i ON pii.item_code = i.name
    WHERE 
        pi.docstatus = 1
        AND pi.status NOT IN ('Cancelled', 'Return')
        AND (
            i.is_stock_item = 1 
            OR (i.is_stock_item IS NULL AND pii.item_group NOT IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES'))
        )
        AND pii.item_group NOT IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES')
        AND pi.company IS NOT NULL
        AND pi.company != ''
    """
    
    # Summary query for overall totals
    summary_query = """
    SELECT
        DATE_FORMAT(pi.posting_date, '%%b %%Y') AS month_year,
        DATE_FORMAT(pi.posting_date, '%%Y-%%m') AS sort_date,
        SUM(pii.amount) AS total_amount,
        COUNT(DISTINCT pi.name) AS invoice_count,
        COUNT(DISTINCT pi.cost_center) AS branch_count,
        COUNT(DISTINCT pi.company) AS company_count
    FROM `tabPurchase Invoice` pi
    INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
    LEFT JOIN `tabItem` i ON pii.item_code = i.name
    WHERE 
        pi.docstatus = 1
        AND pi.status NOT IN ('Cancelled', 'Return')
        AND (
            i.is_stock_item = 1 
            OR (i.is_stock_item IS NULL AND pii.item_group NOT IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES'))
        )
        AND pii.item_group NOT IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES')
    """
    
    try:
        # Apply filters to queries
        branch_query, branch_params = apply_filters_to_query(branch_query, filters)
        company_query, company_params = apply_filters_to_query(company_query, filters)
        summary_query, summary_params = apply_filters_to_query(summary_query, filters)
        
        # Add GROUP BY and ORDER BY clauses
        branch_query += """
        GROUP BY 
            pi.cost_center,
            DATE_FORMAT(pi.posting_date, '%%Y-%%m'),
            DATE_FORMAT(pi.posting_date, '%%b %%Y')
        ORDER BY 
            pi.cost_center,
            sort_date
        """
        
        company_query += """
        GROUP BY 
            pi.company,
            DATE_FORMAT(pi.posting_date, '%%Y-%%m'),
            DATE_FORMAT(pi.posting_date, '%%b %%Y')
        ORDER BY 
            pi.company,
            sort_date
        """
        
        summary_query += """
        GROUP BY 
            DATE_FORMAT(pi.posting_date, '%%Y-%%m'),
            DATE_FORMAT(pi.posting_date, '%%b %%Y')
        ORDER BY sort_date
        """
        
        # Execute queries
        branch_result = frappe.db.sql(branch_query, branch_params, as_dict=True)
        company_result = frappe.db.sql(company_query, company_params, as_dict=True)
        summary_result = frappe.db.sql(summary_query, summary_params, as_dict=True)
        
        # Process branch-wise data
        branch_data = {}
        branch_months = set()
        
        for row in branch_result:
            branch = row['branch']
            month = row['month_year']
            amount = float(row['total_amount']) if row['total_amount'] else 0
            
            if branch not in branch_data:
                branch_data[branch] = {}
            branch_data[branch][month] = amount
            branch_months.add(month)
        
        # Process company-wise data
        company_data = {}
        company_months = set()
        
        for row in company_result:
            company = row['company']
            month = row['month_year']
            amount = float(row['total_amount']) if row['total_amount'] else 0
            
            if company not in company_data:
                company_data[company] = {}
            company_data[company][month] = amount
            company_months.add(month)
        
        # Sort months chronologically
        all_months = sorted(list(branch_months.union(company_months)), 
                           key=lambda x: frappe.utils.getdate(f"01 {x}"))
        
        # Prepare branch chart data
        branch_datasets = []
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']
        
        for i, branch in enumerate(sorted(branch_data.keys())):
            data_points = []
            for month in all_months:
                data_points.append(branch_data[branch].get(month, 0))
            
            branch_datasets.append({
                'label': branch,
                'data': data_points,
                'backgroundColor': colors[i % len(colors)],
                'borderColor': colors[i % len(colors)],
                'borderWidth': 1
            })
        
        # Prepare company chart data
        company_datasets = []
        
        for i, company in enumerate(sorted(company_data.keys())):
            data_points = []
            for month in all_months:
                data_points.append(company_data[company].get(month, 0))
            
            company_datasets.append({
                'label': company,
                'data': data_points,
                'backgroundColor': colors[i % len(colors)],
                'borderColor': colors[i % len(colors)],
                'borderWidth': 1
            })
        
        # Prepare summary data
        summary_labels = [row['month_year'] for row in summary_result]
        summary_data = [float(row['total_amount']) if row['total_amount'] else 0 for row in summary_result]
        
        return {
            "chart_type": "bar",
            "branch_wise": {
                "labels": all_months,
                "datasets": branch_datasets,
                "title": "Total Buying - Branch Wise"
            },
            "company_wise": {
                "labels": all_months,
                "datasets": company_datasets,
                "title": "Total Buying - Company Wise"
            },
            "summary": {
                "labels": summary_labels,
                "data": summary_data,
                "title": "Total Buying - Overall Summary"
            },
            "metadata": {
                "total_branches": len(branch_data),
                "total_companies": len(company_data),
                "date_range": "Last 12 months",
                "filters_applied": filters
            },
            "success": True
        }
        
    except Exception as e:
        frappe.log_error(f"Error in total_buying query: {str(e)}")
        return {
            "chart_type": "bar",
            "branch_wise": {"labels": [], "datasets": []},
            "company_wise": {"labels": [], "datasets": []},
            "summary": {"labels": [], "data": []},
            "error": str(e),
            "success": False
        }

@frappe.whitelist()
def get_branch_wise_buying(filters=None):
    """
    Separate endpoint for branch-wise data only
    """
    result = get_total_branch_wise_buying(filters)
    if result.get('success'):
        return result['branch_wise']
    return {"labels": [], "datasets": [], "error": result.get('error')}

@frappe.whitelist()
def get_company_wise_buying(filters=None):
    """
    Separate endpoint for company-wise data only
    """
    result = get_total_branch_wise_buying(filters)
    if result.get('success'):
        return result['company_wise']
    return {"labels": [], "datasets": [], "error": result.get('error')}

@frappe.whitelist()
def get_buying_summary(filters=None):
    """
    Separate endpoint for summary data only
    """
    result = get_total_branch_wise_buying(filters)
    if result.get('success'):
        return result['summary']
    return {"labels": [], "data": [], "error": result.get('error')}

@frappe.whitelist()
def get_top_buying_product_pie(filters=None, branch=None, company=None, limit=5):
    """
    Top Buying Products Pie Chart
    Branch wise and company wise different chart
    """
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    filters = filters or {}
    
    # Merge filters with parameters
    if branch:
        filters['branch'] = branch
    if company:
        filters['company'] = company
    
    base_query = """
        SELECT 
            pii.item_name,
            pii.item_code,
            SUM(pii.amount) as total_amount,
            SUM(pii.qty) as total_quantity,
            COUNT(DISTINCT pi.name) as invoice_count
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
        LEFT JOIN `tabItem` i ON pii.item_code = i.name
        WHERE 
            pi.docstatus = 1
            AND pi.status NOT IN ('Cancelled', 'Return')
            AND (
                i.is_stock_item = 1 
                OR (i.is_stock_item IS NULL AND pii.item_group NOT IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES'))
            )
            AND pii.item_group NOT IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES')
    """
    
    try:
        # Apply filters
        query, params = apply_filters_to_query(base_query, filters)
        query += """
        GROUP BY pii.item_code, pii.item_name
        ORDER BY total_amount DESC
        LIMIT %s
        """
        params['limit'] = limit
        
        result = frappe.db.sql(query, params, as_dict=True)
        
        # Color palette for the pie chart
        color_palette = [
            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
            '#FF9F40', '#FF6384', '#C9CBCF', '#4BC0C0', '#FF9F40'
        ]
        
        # Process the data
        labels = []
        data = []
        backgroundColor = []
        
        for i, row in enumerate(result):
            # Format the label to include item name and total amount
            label = f"{row['item_name']} (₹{row['total_amount']:,.0f})"
            labels.append(label)
            data.append(float(row['total_amount']))
            backgroundColor.append(color_palette[i % len(color_palette)])
        
        return {
            "labels": labels,
            "data": data,
            "backgroundColor": backgroundColor,
            "filters_applied": filters
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_top_buying_product_pie: {str(e)}")
        return {
            "labels": [],
            "data": [],
            "backgroundColor": []
        }

@frappe.whitelist()
def consolidated_total_buying(filters=None):
    """
    Chart Name: Consolidate Total Buying
    Chart Type: Bar
    Note: All the company's buying shows in one bar chart using different colour for each company or branch
    """
    
    # Query to get consolidated data by company and branch
    consolidated_query = """
    SELECT
        CASE 
            WHEN pi.cost_center IS NOT NULL AND pi.cost_center != '' 
            THEN CONCAT(COALESCE(pi.company, 'Unknown'), ' - ', pi.cost_center)
            ELSE COALESCE(pi.company, 'Unknown Company')
        END AS entity_name,
        COALESCE(pi.company, 'Unknown Company') AS company,
        COALESCE(pi.cost_center, 'No Branch') AS branch,
        DATE_FORMAT(pi.posting_date, '%%b %%Y') AS month_year,
        DATE_FORMAT(pi.posting_date, '%%Y-%%m') AS sort_date,
        SUM(pii.amount) AS total_amount,
        COUNT(DISTINCT pi.name) AS invoice_count,
        SUM(pii.qty) AS total_qty
    FROM `tabPurchase Invoice` pi
    INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
    LEFT JOIN `tabItem` i ON pii.item_code = i.name
    WHERE 
        pi.docstatus = 1
        AND pi.status NOT IN ('Cancelled', 'Return')
        AND (
            i.is_stock_item = 1 
            OR (i.is_stock_item IS NULL AND pii.item_group NOT IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES'))
        )
        AND pii.item_group NOT IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES')
    """
    
    # Query to get entity totals for sorting
    entity_totals_query = """
    SELECT
        CASE 
            WHEN pi.cost_center IS NOT NULL AND pi.cost_center != '' 
            THEN CONCAT(COALESCE(pi.company, 'Unknown'), ' - ', pi.cost_center)
            ELSE COALESCE(pi.company, 'Unknown Company')
        END AS entity_name,
        SUM(pii.amount) AS total_amount
    FROM `tabPurchase Invoice` pi
    INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
    LEFT JOIN `tabItem` i ON pii.item_code = i.name
    WHERE 
        pi.docstatus = 1
        AND pi.status NOT IN ('Cancelled', 'Return')
        AND (
            i.is_stock_item = 1 
            OR (i.is_stock_item IS NULL AND pii.item_group NOT IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES'))
        )
        AND pii.item_group NOT IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES')
    """
    
    try:
        # Apply filters to queries
        consolidated_query, consolidated_params = apply_filters_to_query(consolidated_query, filters)
        entity_totals_query, entity_totals_params = apply_filters_to_query(entity_totals_query, filters)
        
        # Add GROUP BY and ORDER BY clauses
        consolidated_query += """
        GROUP BY 
            entity_name,
            pi.company,
            pi.cost_center,
            DATE_FORMAT(pi.posting_date, '%%Y-%%m'),
            DATE_FORMAT(pi.posting_date, '%%b %%Y')
        ORDER BY 
            pi.company,
            pi.cost_center,
            sort_date
        """
        
        entity_totals_query += """
        GROUP BY entity_name
        ORDER BY total_amount DESC
        """
        
        # Execute queries
        consolidated_result = frappe.db.sql(consolidated_query, consolidated_params, as_dict=True)
        entity_totals_result = frappe.db.sql(entity_totals_query, entity_totals_params, as_dict=True)
        
        if not consolidated_result:
            return {
                "chart_type": "bar",
                "labels": [],
                "datasets": [],
                "message": "No data found for the specified criteria",
                "success": True
            }
        
        # Process consolidated data
        entity_data = {}
        all_months = set()
        
        for row in consolidated_result:
            entity = row['entity_name']
            month = row['month_year']
            amount = float(row['total_amount']) if row['total_amount'] else 0
            
            if entity not in entity_data:
                entity_data[entity] = {}
            entity_data[entity][month] = amount
            all_months.add(month)
        
        # Sort months chronologically
        sorted_months = sorted(list(all_months), 
                              key=lambda x: frappe.utils.getdate(f"01 {x}"))
        
        # Get entity order by total amount (descending)
        entity_order = [row['entity_name'] for row in entity_totals_result]
        
        # Color palette for different entities
        color_palette = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
            '#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#ff99cc',
            '#c2c2f0', '#ffb3e6', '#c4e17f', '#76d7c4', '#f7dc6f'
        ]
        
        # Prepare datasets for each entity
        datasets = []
        
        for i, entity in enumerate(entity_order):
            if entity in entity_data:
                data_points = []
                for month in sorted_months:
                    data_points.append(entity_data[entity].get(month, 0))
                
                # Calculate total for this entity
                entity_total = sum(data_points)
                
                datasets.append({
                    'label': f"{entity} (₹{entity_total:,.0f})",
                    'data': data_points,
                    'backgroundColor': color_palette[i % len(color_palette)],
                    'borderColor': color_palette[i % len(color_palette)],
                    'borderWidth': 1,
                    'entity_total': entity_total
                })
        
        # Calculate grand total
        grand_total = sum([ds['entity_total'] for ds in datasets])
        
        return {
            "chart_type": "bar",
            "labels": sorted_months,
            "datasets": datasets,
            "title": "Consolidated Total Buying - All Companies & Branches",
            "chart_options": {
                "responsive": True,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"Total Buying by Company/Branch (Grand Total: ₹{grand_total:,.0f})"
                    },
                    "legend": {
                        "display": True,
                        "position": "right"
                    }
                },
                "scales": {
                    "x": {
                        "title": {
                            "display": True,
                            "text": "Month"
                        }
                    },
                    "y": {
                        "title": {
                            "display": True,
                            "text": "Amount (₹)"
                        },
                        "ticks": {
                            "callback": "function(value) { return '₹' + value.toLocaleString(); }"
                        }
                    }
                }
            },
            "metadata": {
                "filters_applied": filters,
                "total_entities": len(datasets)
            },
            "success": True
        }
        
    except Exception as e:
        frappe.log_error(f"Error in consolidated_total_buying query: {str(e)}")
        return {
            "chart_type": "bar",
            "labels": [],
            "datasets": [],
            "error": str(e),
            "success": False
        }

@frappe.whitelist()
def get_entity_summary(filters=None):
    """
    Get summary of all entities with their totals for a single-bar-per-entity chart
    """
    try:
        result = consolidated_total_buying(filters)
        if result.get('success') and result.get('datasets'):
            labels = []
            data = []
            backgroundColors = []
            for dataset in result['datasets']:
                labels.append(dataset['label'].split(' (₹')[0])  # Remove amount from label
                data.append(dataset['entity_total'])
                backgroundColors.append(dataset['backgroundColor'])
            return {
                'labels': labels,
                'data': data,
                'backgroundColor': backgroundColors,
                'filters_applied': filters,
                'success': True
            }
        else:
            return {
                'labels': [],
                'data': [],
                'backgroundColor': [],
                'error': result.get('error', 'No data found'),
                'success': False
            }
    except Exception as e:
        return {
            'labels': [],
            'data': [],
            'backgroundColor': [],
            'error': str(e),
            'success': False
        }

@frappe.whitelist()
def total_buying(filters=None):
    return get_total_branch_wise_buying(filters)

@frappe.whitelist()
def get_top_supplier_for_expenses_raw_bar(filters=None, branch=None, company=None, limit=5):
    """
    Top Suppliers for Expenses Raw Bar Chart
    Branch wise and company wise different chart
    Shows top suppliers by expense amount
    """
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    filters = filters or {}
    
    # Merge filters with parameters
    if branch:
        filters['branch'] = branch
    if company:
        filters['company'] = company
    
    base_query = """
        SELECT 
            pi.supplier_name,
            pi.supplier,
            COUNT(DISTINCT pi.name) as invoice_count,
            SUM(pi.total) as total_amount,
            SUM(pi.net_total) as net_amount,
            AVG(pi.total) as avg_invoice_value
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
        WHERE 
            pi.docstatus = 1
            AND pi.status NOT IN ('Cancelled', 'Return')
            AND pii.item_group IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES')
    """
    
    try:
        # Apply filters
        query, params = apply_filters_to_query(base_query, filters)
        query += """
        GROUP BY pi.supplier, pi.supplier_name
        ORDER BY total_amount DESC
        LIMIT %s
        """
        params['limit'] = limit
        
        result = frappe.db.sql(query, params, as_dict=True)
        
        # Color palette for the bars
        color_palette = [
            '#ff6384', '#36a2eb', '#ffce56', '#4bc0c0', '#9966ff',
            '#f67019', '#f53794', '#acc236', '#166a8f', '#00a950',
            '#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#ff99cc'
        ]
        
        # Process the data
        labels = []
        data = []
        backgroundColor = []
        
        for i, row in enumerate(result):
            # Format the label to include supplier name and total amount
            label = f"{row['supplier_name']} (₹{row['total_amount']:,.0f})"
            labels.append(label)
            data.append(float(row['total_amount']))
            backgroundColor.append(color_palette[i % len(color_palette)])
        
        return {
            "labels": labels,
            "data": data,
            "backgroundColor": backgroundColor,
            "filters_applied": filters
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_top_supplier_for_expenses_raw_bar: {str(e)}")
        return {
            "labels": [],
            "data": [],
            "backgroundColor": []
        }