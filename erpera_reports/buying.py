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
    INNER JOIN `tabItem` i ON pii.item_code = i.name
    INNER JOIN `tabItem Group` ig ON i.item_group = ig.name
    WHERE 
        pi.docstatus = 1
        AND pi.status NOT IN ('Cancelled', 'Return')
        AND pi.cost_center IS NOT NULL
        AND pi.cost_center != ''
        AND i.item_group NOT IN ('Raw Material', 'Services', 'Sub Assemblies', 'Consumable', 'Furniture', 'EXPENSE', 'FIXED ASSET')
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
    INNER JOIN `tabItem` i ON pii.item_code = i.name
    INNER JOIN `tabItem Group` ig ON i.item_group = ig.name
    WHERE 
        pi.docstatus = 1
        AND pi.status NOT IN ('Cancelled', 'Return')
        AND pi.company IS NOT NULL
        AND pi.company != ''
        AND i.item_group NOT IN ('Raw Material', 'Services', 'Sub Assemblies', 'Consumable', 'Furniture', 'EXPENSE', 'FIXED ASSET')
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
    INNER JOIN `tabItem` i ON pii.item_code = i.name
    INNER JOIN `tabItem Group` ig ON i.item_group = ig.name
    WHERE 
        pi.docstatus = 1
        AND pi.status NOT IN ('Cancelled', 'Return')
        AND i.item_group NOT IN ('Raw Material', 'Services', 'Sub Assemblies', 'Consumable', 'Furniture', 'EXPENSE', 'FIXED ASSET')
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
def get_top_buying_products_by_branch(filters=None):
    """
    Get top buying products for each branch with percentage calculations
    Returns data in multi-pie chart format with datasets for each branch
    """
    base_query = """
        SELECT 
            COALESCE(pi.cost_center, 'No Branch') as branch,
            pii.item_name,
            pii.item_code,
            SUM(pii.amount) as total_amount,
            SUM(pii.qty) as total_quantity,
            COUNT(DISTINCT pi.name) as invoice_count
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
        INNER JOIN `tabItem` i ON pii.item_code = i.name
        INNER JOIN `tabItem Group` ig ON i.item_group = ig.name
        WHERE 
            pi.docstatus = 1
            AND pi.status NOT IN ('Cancelled', 'Return')
            AND pi.cost_center IS NOT NULL 
            AND pi.cost_center != ''
            AND i.item_group NOT IN ('Raw Material', 'Services', 'Sub Assemblies', 'Consumable', 'Furniture', 'EXPENSE', 'FIXED ASSET')
    """
    
    try:
        # Apply filters
        query, params = apply_filters_to_query(base_query, filters)
        query += """
        GROUP BY pi.cost_center, pii.item_code, pii.item_name
        ORDER BY pi.cost_center, total_amount DESC
        """
        
        result = frappe.db.sql(query, params, as_dict=True)
        
        # Process data by branch
        branch_data = {}
        for row in result:
            branch = row['branch']
            if branch not in branch_data:
                branch_data[branch] = {
                    'items': [],
                    'total_branch_amount': 0
                }
            
            # Add to branch total
            amount = float(row['total_amount']) if row['total_amount'] else 0
            branch_data[branch]['total_branch_amount'] += amount
            
            # Only store top 10 items per branch
            if len(branch_data[branch]['items']) < 10:
                branch_data[branch]['items'].append({
                    'item_name': row['item_name'],
                    'amount': amount,
                    'quantity': float(row['total_quantity']) if row['total_quantity'] else 0
                })
        
        # Color palette for the pie charts
        colors = [
            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
            '#FF9F40', '#FF6384', '#C9CBCF', '#4BC0C0', '#FF9F40'
        ]
        
        # Prepare datasets for each branch
        datasets = {}
        for branch, data in branch_data.items():
            total_branch_amount = data['total_branch_amount']
            
            # Calculate percentages and prepare labels
            labels = []
            data_values = []
            background_colors = []
            
            # Process top items
            top_items_amount = 0
            for i, item in enumerate(data['items']):
                percentage = (item['amount'] / total_branch_amount) * 100
                top_items_amount += item['amount']
                label = f"{item['item_name']} ({percentage:.1f}%)"
                labels.append(label)
                data_values.append(item['amount'])
                background_colors.append(colors[i % len(colors)])
            
            # Add "Others" category if there's remaining amount
            remaining_amount = total_branch_amount - top_items_amount
            if remaining_amount > 0:
                percentage = (remaining_amount / total_branch_amount) * 100
                labels.append(f"Others ({percentage:.1f}%)")
                data_values.append(remaining_amount)
                background_colors.append('#C9CBCF')
            
            datasets[branch] = {
                'labels': labels,
                'data': data_values,
                'backgroundColor': background_colors,
                'total_amount': total_branch_amount
            }
        
        return {
            'datasets': datasets,
            'filters_applied': filters,
            'success': True
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_top_buying_products_by_branch: {str(e)}")
        return {
            'datasets': {},
            'success': False,
            'error': str(e)
        }

@frappe.whitelist()
def get_top_buying_products_by_company(filters=None):
    """
    Get top buying products for each company with percentage calculations
    Returns data in multi-pie chart format with datasets for each company
    """
    base_query = """
        SELECT 
            pi.company,
            pii.item_name,
            pii.item_code,
            SUM(pii.amount) as total_amount,
            SUM(pii.qty) as total_quantity,
            COUNT(DISTINCT pi.name) as invoice_count
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
        INNER JOIN `tabItem` i ON pii.item_code = i.name
        INNER JOIN `tabItem Group` ig ON i.item_group = ig.name
        WHERE 
            pi.docstatus = 1 
            AND pi.status NOT IN ('Cancelled', 'Return')
            AND pi.company IS NOT NULL 
            AND pi.company != ''
            AND i.item_group NOT IN ('Raw Material', 'Services', 'Sub Assemblies', 'Consumable', 'Furniture', 'EXPENSE', 'FIXED ASSET')
    """
    
    try:
        # Apply filters
        query, params = apply_filters_to_query(base_query, filters)
        query += """
        GROUP BY pi.company, pii.item_code, pii.item_name
        ORDER BY pi.company, total_amount DESC
        """
        
        result = frappe.db.sql(query, params, as_dict=True)
        
        # Process data by company
        company_data = {}
        for row in result:
            company = row['company']
            if company not in company_data:
                company_data[company] = {
                    'items': [],
                    'total_company_amount': 0
                }
            
            # Add to company total
            amount = float(row['total_amount']) if row['total_amount'] else 0
            company_data[company]['total_company_amount'] += amount
            
            # Only store top 10 items per company
            if len(company_data[company]['items']) < 10:
                company_data[company]['items'].append({
                    'item_name': row['item_name'],
                    'amount': amount,
                    'quantity': float(row['total_quantity']) if row['total_quantity'] else 0
                })
        
        # Color palette for the pie charts
        colors = [
            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
            '#FF9F40', '#FF6384', '#C9CBCF', '#4BC0C0', '#FF9F40'
        ]
        
        # Prepare datasets for each company
        datasets = {}
        for company, data in company_data.items():
            total_company_amount = data['total_company_amount']
            
            # Calculate percentages and prepare labels
            labels = []
            data_values = []
            background_colors = []
            
            # Process top items
            top_items_amount = 0
            for i, item in enumerate(data['items']):
                percentage = (item['amount'] / total_company_amount) * 100
                top_items_amount += item['amount']
                label = f"{item['item_name']} ({percentage:.1f}%)"
                labels.append(label)
                data_values.append(item['amount'])
                background_colors.append(colors[i % len(colors)])
            
            # Add "Others" category if there's remaining amount
            remaining_amount = total_company_amount - top_items_amount
            if remaining_amount > 0:
                percentage = (remaining_amount / total_company_amount) * 100
                labels.append(f"Others ({percentage:.1f}%)")
                data_values.append(remaining_amount)
                background_colors.append('#C9CBCF')
            
            datasets[company] = {
                'labels': labels,
                'data': data_values,
                'backgroundColor': background_colors,
                'total_amount': total_company_amount
            }
        
        return {
            'datasets': datasets,
            'filters_applied': filters,
            'success': True
        }
        
    except Exception as e:
        error_msg = f"Error in get_top_buying_products_by_company: {str(e)}"
        frappe.log_error(error_msg)
        return {
            'datasets': {},
            'success': False,
            'error': error_msg
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
    INNER JOIN `tabItem` i ON pii.item_code = i.name
    INNER JOIN `tabItem Group` ig ON i.item_group = ig.name
    WHERE 
        pi.docstatus = 1
        AND pi.status NOT IN ('Cancelled', 'Return')
        AND i.item_group NOT IN ('Raw Material', 'Services', 'Sub Assemblies', 'Consumable', 'Furniture', 'EXPENSE', 'FIXED ASSET')
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
    INNER JOIN `tabItem` i ON pii.item_code = i.name
    INNER JOIN `tabItem Group` ig ON i.item_group = ig.name
    WHERE 
        pi.docstatus = 1
        AND pi.status NOT IN ('Cancelled', 'Return')
        AND i.item_group NOT IN ('Raw Material', 'Services', 'Sub Assemblies', 'Consumable', 'Furniture', 'EXPENSE', 'FIXED ASSET')
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
            '#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#ff99cc'
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
        """
        
        # Execute query without LIMIT
        result = frappe.db.sql(query, params, as_dict=True)
        
        # Apply limit after query execution
        if limit and len(result) > limit:
            result = result[:limit]
        
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

@frappe.whitelist()
def get_most_expenses_head_by_branch(filters=None):
    """
    Most Expenses Head by Branch - Pie Chart
    Shows expense distribution by item groups for each branch
    Only includes expense, service, and asset items
    """
    base_query = """
        SELECT 
            COALESCE(pi.cost_center, 'No Branch') as branch,
            COALESCE(pii.item_group, 'No Item Group') as item_group,
            SUM(pii.amount) as total_amount,
            COUNT(DISTINCT pi.name) as invoice_count,
            SUM(pii.qty) as total_quantity
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
        LEFT JOIN `tabItem` i ON pii.item_code = i.name
        WHERE 
            pi.docstatus = 1
            AND pi.status NOT IN ('Cancelled', 'Return')
            AND (
                pii.item_group IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES')
                OR (i.is_stock_item = 0 AND pii.item_group IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES'))
            )
            AND pi.cost_center IS NOT NULL 
            AND pi.cost_center != ''
    """
    
    try:
        # Apply filters
        query, params = apply_filters_to_query(base_query, filters)
        query += """
        GROUP BY pi.cost_center, pii.item_group
        ORDER BY pi.cost_center, total_amount DESC
        """
        
        result = frappe.db.sql(query, params, as_dict=True)
        
        # Process data by branch
        branch_data = {}
        for row in result:
            branch = row['branch']
            if branch not in branch_data:
                branch_data[branch] = {
                    'item_groups': [],
                    'total_branch_amount': 0
                }
            
            # Add to branch total
            amount = float(row['total_amount']) if row['total_amount'] else 0
            branch_data[branch]['total_branch_amount'] += amount
            
            # Store all item groups for this branch
            branch_data[branch]['item_groups'].append({
                'item_group': row['item_group'],
                'amount': amount,
                'invoice_count': int(row['invoice_count']) if row['invoice_count'] else 0,
                'quantity': float(row['total_quantity']) if row['total_quantity'] else 0
            })
        
        # Color palette for the pie charts
        colors = [
            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
            '#FF9F40', '#FF6384', '#C9CBCF', '#4BC0C0', '#FF9F40',
            '#8DD1E1', '#D4A5A5', '#FFB347', '#87CEEB', '#DDA0DD'
        ]
        
        # Prepare datasets for each branch
        datasets = {}
        for branch, data in branch_data.items():
            total_branch_amount = data['total_branch_amount']
            
            # Sort item groups by amount (descending)
            sorted_items = sorted(data['item_groups'], key=lambda x: x['amount'], reverse=True)
            
            # Take top 10 item groups
            top_items = sorted_items[:10]
            
            # Calculate percentages and prepare labels
            labels = []
            data_values = []
            background_colors = []
            
            # Process top item groups
            top_items_amount = 0
            for i, item in enumerate(top_items):
                percentage = (item['amount'] / total_branch_amount) * 100 if total_branch_amount > 0 else 0
                top_items_amount += item['amount']
                label = f"{item['item_group']} ({percentage:.1f}%)"
                labels.append(label)
                data_values.append(item['amount'])
                background_colors.append(colors[i % len(colors)])
            
            # Add "Others" category if there are more than 10 item groups
            remaining_amount = total_branch_amount - top_items_amount
            if remaining_amount > 0:
                percentage = (remaining_amount / total_branch_amount) * 100
                labels.append(f"Others ({percentage:.1f}%)")
                data_values.append(remaining_amount)
                background_colors.append('#C9CBCF')
            
            datasets[branch] = {
                'labels': labels,
                'data': data_values,
                'backgroundColor': background_colors,
                'total_amount': total_branch_amount
            }
        
        return {
            'datasets': datasets,
            'filters_applied': filters,
            'success': True
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_most_expenses_head_by_branch: {str(e)}")
        return {
            'datasets': {},
            'success': False,
            'error': str(e)
        }

@frappe.whitelist()
def get_most_expenses_head_by_company(filters=None):
    """
    Most Expenses Head by Company - Pie Chart
    Shows expense distribution by item groups for each company
    Only includes expense, service, and asset items
    """
    base_query = """
        SELECT 
            pi.company,
            COALESCE(pii.item_group, 'No Item Group') as item_group,
            SUM(pii.amount) as total_amount,
            COUNT(DISTINCT pi.name) as invoice_count,
            SUM(pii.qty) as total_quantity
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
        LEFT JOIN `tabItem` i ON pii.item_code = i.name
        WHERE 
            pi.docstatus = 1 
            AND pi.status NOT IN ('Cancelled', 'Return')
            AND (
                pii.item_group IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES')
                OR (i.is_stock_item = 0 AND pii.item_group IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES'))
            )
            AND pi.company IS NOT NULL 
            AND pi.company != ''
    """
    
    try:
        # Apply filters
        query, params = apply_filters_to_query(base_query, filters)
        query += """
        GROUP BY pi.company, pii.item_group
        ORDER BY pi.company, total_amount DESC
        """
        
        result = frappe.db.sql(query, params, as_dict=True)
        
        # Process data by company
        company_data = {}
        for row in result:
            company = row['company']
            if company not in company_data:
                company_data[company] = {
                    'item_groups': [],
                    'total_company_amount': 0
                }
            
            # Add to company total
            amount = float(row['total_amount']) if row['total_amount'] else 0
            company_data[company]['total_company_amount'] += amount
            
            # Store all item groups for this company
            company_data[company]['item_groups'].append({
                'item_group': row['item_group'],
                'amount': amount,
                'invoice_count': int(row['invoice_count']) if row['invoice_count'] else 0,
                'quantity': float(row['total_quantity']) if row['total_quantity'] else 0
            })
        
        # Color palette for the pie charts
        colors = [
            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
            '#FF9F40', '#FF6384', '#C9CBCF', '#4BC0C0', '#FF9F40',
            '#8DD1E1', '#D4A5A5', '#FFB347', '#87CEEB', '#DDA0DD'
        ]
        
        # Prepare datasets for each company
        datasets = {}
        for company, data in company_data.items():
            total_company_amount = data['total_company_amount']
            
            # Sort item groups by amount (descending)
            sorted_items = sorted(data['item_groups'], key=lambda x: x['amount'], reverse=True)
            
            # Take top 10 item groups
            top_items = sorted_items[:10]
            
            # Calculate percentages and prepare labels
            labels = []
            data_values = []
            background_colors = []
            
            # Process top item groups
            top_items_amount = 0
            for i, item in enumerate(top_items):
                percentage = (item['amount'] / total_company_amount) * 100 if total_company_amount > 0 else 0
                top_items_amount += item['amount']
                label = f"{item['item_group']} ({percentage:.1f}%)"
                labels.append(label)
                data_values.append(item['amount'])
                background_colors.append(colors[i % len(colors)])
            
            # Add "Others" category if there are more than 10 item groups
            remaining_amount = total_company_amount - top_items_amount
            if remaining_amount > 0:
                percentage = (remaining_amount / total_company_amount) * 100
                labels.append(f"Others ({percentage:.1f}%)")
                data_values.append(remaining_amount)
                background_colors.append('#C9CBCF')
            
            datasets[company] = {
                'labels': labels,
                'data': data_values,
                'backgroundColor': background_colors,
                'total_amount': total_company_amount
            }
        
        return {
            'datasets': datasets,
            'filters_applied': filters,
            'success': True
        }
        
    except Exception as e:
        error_msg = f"Error in get_most_expenses_head_by_company: {str(e)}"
        frappe.log_error(error_msg)
        return {
            'datasets': {},
            'success': False,
            'error': error_msg
        }

@frappe.whitelist()
def get_consolidate_most_purchase_head(filters=None):
    """
    Consolidate Most Purchase Head - Single Pie Chart
    Shows top 10 highest expense categories across all companies
    Only includes expense, service, and asset items
    """
    base_query = """
        SELECT 
            COALESCE(pii.item_group, 'No Item Group') as item_group,
            SUM(pii.amount) as total_amount,
            COUNT(DISTINCT pi.name) as invoice_count,
            COUNT(DISTINCT pi.company) as company_count,
            COUNT(DISTINCT pi.cost_center) as branch_count,
            SUM(pii.qty) as total_quantity
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
        LEFT JOIN `tabItem` i ON pii.item_code = i.name
        WHERE 
            pi.docstatus = 1
            AND pi.status NOT IN ('Cancelled', 'Return')
            AND (
                pii.item_group IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES')
                OR (i.is_stock_item = 0 AND pii.item_group IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES'))
            )
    """
    
    try:
        # Apply filters
        query, params = apply_filters_to_query(base_query, filters)
        query += """
        GROUP BY pii.item_group
        ORDER BY total_amount DESC
        """
        
        result = frappe.db.sql(query, params, as_dict=True)
        
        if not result:
            return {
                'labels': [],
                'data': [],
                'backgroundColor': [],
                'message': 'No expense data found for the specified criteria',
                'success': True
            }
        
        # Calculate grand total
        grand_total = sum(float(row['total_amount']) if row['total_amount'] else 0 for row in result)
        
        if grand_total == 0:
            return {
                'labels': [],
                'data': [],
                'backgroundColor': [],
                'message': 'No expense amount found for the specified criteria',
                'success': True
            }
        
        # Take top 10 item groups
        top_items = result[:10]
        
        # Color palette for the pie chart
        colors = [
            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
            '#FF9F40', '#8DD1E1', '#D4A5A5', '#FFB347', '#87CEEB'
        ]
        
        # Prepare chart data
        labels = []
        data = []
        background_colors = []
        
        # Process top 10 item groups
        top_items_total = 0
        for i, item in enumerate(top_items):
            amount = float(item['total_amount']) if item['total_amount'] else 0
            percentage = (amount / grand_total) * 100
            top_items_total += amount
            
            # Format label with percentage and amount
            label = f"{item['item_group']} ({percentage:.1f}%) - ₹{amount:,.0f}"
            labels.append(label)
            data.append(amount)
            background_colors.append(colors[i % len(colors)])
        
        # Add "Others" category if there are more than 10 item groups
        remaining_amount = grand_total - top_items_total
        if remaining_amount > 0 and len(result) > 10:
            percentage = (remaining_amount / grand_total) * 100
            labels.append(f"Others ({percentage:.1f}%) - ₹{remaining_amount:,.0f}")
            data.append(remaining_amount)
            background_colors.append('#C9CBCF')
        
        # Calculate summary statistics
        total_invoices = sum(int(row['invoice_count']) if row['invoice_count'] else 0 for row in result)
        unique_companies = len(set(row.get('company_count', 0) for row in result if row.get('company_count')))
        unique_branches = len(set(row.get('branch_count', 0) for row in result if row.get('branch_count')))
        
        return {
            'chart_type': 'pie',
            'labels': labels,
            'data': data,
            'backgroundColor': background_colors,
            'title': f'Top 10 Expense Categories (Total: ₹{grand_total:,.0f})',
            'summary': {
                'grand_total': grand_total,
                'total_invoices': total_invoices,
                'total_item_groups': len(result),
                'top_item_groups_shown': len(top_items),
                'unique_companies': unique_companies,
                'unique_branches': unique_branches
            },
            'filters_applied': filters,
            'success': True
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_consolidate_most_purchase_head: {str(e)}")
        return {
            'chart_type': 'pie',
            'labels': [],
            'data': [],
            'backgroundColor': [],
            'error': str(e),
            'success': False
        }

@frappe.whitelist()
def get_drill_down_data(filters=None, chart_title=None, clicked_label=None, clicked_value=None):
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
        
        if filters.get('branch') and drill_type != 'branch':
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
                'supplier_code': row.get('supplier', ''),
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
def debug_supplier_data(limit=10):
    """
    Debug function to check supplier data in the database
    """
    try:
        # Get sample supplier data
        query = """
            SELECT DISTINCT
                pi.supplier_name,
                pi.supplier,
                COUNT(pi.name) as invoice_count,
                SUM(pi.total) as total_amount
            FROM `tabPurchase Invoice` pi
            INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
            WHERE 
                pi.docstatus = 1
                AND pi.status NOT IN ('Cancelled', 'Return')
                AND pii.item_group IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES')
                AND pi.supplier_name IS NOT NULL
                AND pi.supplier_name != ''
            GROUP BY pi.supplier_name, pi.supplier
            ORDER BY total_amount DESC
            LIMIT %(limit)s
        """
        
        result = frappe.db.sql(query, {'limit': limit}, as_dict=True)
        
        # Format the data like the top supplier function does
        formatted_result = []
        for row in result:
            formatted_row = {
                'supplier_name': row['supplier_name'],
                'supplier': row['supplier'],
                'invoice_count': row['invoice_count'],
                'total_amount': row['total_amount'],
                'formatted_label': f"{row['supplier_name']} (₹{row['total_amount']:,.0f})",
                'extracted_name': f"{row['supplier_name']} (₹{row['total_amount']:,.0f})".split(' (₹')[0]
            }
            formatted_result.append(formatted_row)
        
        return {
            'success': True,
            'data': formatted_result,
            'message': f'Found {len(formatted_result)} suppliers with expense transactions'
        }
        
    except Exception as e:
        frappe.log_error(f"Error in debug_supplier_data: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'data': []
        }