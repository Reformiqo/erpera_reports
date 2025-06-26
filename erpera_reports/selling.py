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

@frappe.whitelist()
def get_total_branch_wise_selling(filters=None):
    """
    Chart Name: Total Selling
    Chart Type: Bar
    Note 1: Branch wise and company wise different chart
    """
    
    # Main query for branch-wise data
    branch_query = """
    SELECT
        COALESCE(si.cost_center, 'Unknown Branch') AS branch,
        DATE_FORMAT(si.posting_date, '%%b %%Y') AS month_year,
        DATE_FORMAT(si.posting_date, '%%Y-%%m') AS sort_date,
        SUM(sii.amount) AS total_amount,
        COUNT(DISTINCT si.name) AS invoice_count
    FROM `tabSales Invoice` si
    INNER JOIN `tabSales Invoice Item` sii ON si.name = sii.parent
    INNER JOIN `tabItem` i ON sii.item_code = i.name
    INNER JOIN `tabItem Group` ig ON i.item_group = ig.name
    WHERE 
        si.docstatus = 1
        AND si.status NOT IN ('Cancelled', 'Return')
        AND si.cost_center IS NOT NULL
        AND si.cost_center != ''
        AND i.item_group NOT IN ('Raw Material', 'Services', 'Sub Assemblies', 'Consumable', 'Furniture', 'EXPENSE', 'FIXED ASSET')
        
    """
    
    # Query for company-wise data
    company_query = """
    SELECT
        COALESCE(si.company, 'Unknown Company') AS company,
        DATE_FORMAT(si.posting_date, '%%b %%Y') AS month_year,
        DATE_FORMAT(si.posting_date, '%%Y-%%m') AS sort_date,
        SUM(sii.amount) AS total_amount,
        COUNT(DISTINCT si.name) AS invoice_count
    FROM `tabSales Invoice` si
    INNER JOIN `tabSales Invoice Item` sii ON si.name = sii.parent
    INNER JOIN `tabItem` i ON sii.item_code = i.name
    INNER JOIN `tabItem Group` ig ON i.item_group = ig.name
    WHERE 
        si.docstatus = 1
        AND si.status NOT IN ('Cancelled', 'Return')
        AND si.company IS NOT NULL
        AND si.company != ''
        AND i.item_group NOT IN ('Raw Material', 'Services', 'Sub Assemblies', 'Consumable', 'Furniture', 'EXPENSE', 'FIXED ASSET')
        
    """
    
    # Summary query for overall totals
    summary_query = """
    SELECT
        DATE_FORMAT(si.posting_date, '%%b %%Y') AS month_year,
        DATE_FORMAT(si.posting_date, '%%Y-%%m') AS sort_date,
        SUM(sii.amount) AS total_amount,
        COUNT(DISTINCT si.name) AS invoice_count,
        COUNT(DISTINCT si.cost_center) AS branch_count,
        COUNT(DISTINCT si.company) AS company_count
    FROM `tabSales Invoice` si
    INNER JOIN `tabSales Invoice Item` sii ON si.name = sii.parent
    INNER JOIN `tabItem` i ON sii.item_code = i.name
    INNER JOIN `tabItem Group` ig ON i.item_group = ig.name
    WHERE 
        si.docstatus = 1
        AND si.status NOT IN ('Cancelled', 'Return')
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
            si.cost_center,
            DATE_FORMAT(si.posting_date, '%%Y-%%m'),
            DATE_FORMAT(si.posting_date, '%%b %%Y')
        ORDER BY 
            si.cost_center,
            sort_date
        """
        
        company_query += """
        GROUP BY 
            si.company,
            DATE_FORMAT(si.posting_date, '%%Y-%%m'),
            DATE_FORMAT(si.posting_date, '%%b %%Y')
        ORDER BY 
            si.company,
            sort_date
        """
        
        summary_query += """
        GROUP BY 
            DATE_FORMAT(si.posting_date, '%%Y-%%m'),
            DATE_FORMAT(si.posting_date, '%%b %%Y')
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
                "title": "Total Selling - Branch Wise"
            },
            "company_wise": {
                "labels": all_months,
                "datasets": company_datasets,
                "title": "Total Selling - Company Wise"
            },
            "summary": {
                "labels": summary_labels,
                "data": summary_data,
                "title": "Total Selling - Overall Summary"
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
        frappe.log_error(f"Error in total_selling query: {str(e)}")
        return {
            "chart_type": "bar",
            "branch_wise": {"labels": [], "datasets": []},
            "company_wise": {"labels": [], "datasets": []},
            "summary": {"labels": [], "data": []},
            "error": str(e),
            "success": False
        }

@frappe.whitelist()
def get_branch_wise_selling(filters=None):
    """
    Separate endpoint for branch-wise data only
    """
    result = get_total_branch_wise_selling(filters)
    if result.get('success'):
        return result['branch_wise']
    return {"labels": [], "datasets": [], "error": result.get('error')}

@frappe.whitelist()
def get_company_wise_selling(filters=None):
    """
    Separate endpoint for company-wise data only
    """
    result = get_total_branch_wise_selling(filters)
    if result.get('success'):
        return result['company_wise']
    return {"labels": [], "datasets": [], "error": result.get('error')}

@frappe.whitelist()
def get_selling_summary(filters=None):
    """
    Separate endpoint for summary data only
    """
    result = get_total_branch_wise_selling(filters)
    if result.get('success'):
        return result['summary']
    return {"labels": [], "data": [], "error": result.get('error')}

@frappe.whitelist()
def consolidated_total_selling(filters=None):
    """
    Chart Name: Consolidate Total Selling
    Chart Type: Bar
    Note: All the company's selling shows in one bar chart using different colour for each company or branch
    """
    
    # Query to get consolidated data by company and branch
    consolidated_query = """
    SELECT
        CASE 
            WHEN si.cost_center IS NOT NULL AND si.cost_center != '' 
            THEN CONCAT(COALESCE(si.company, 'Unknown'), ' - ', si.cost_center)
            ELSE COALESCE(si.company, 'Unknown Company')
        END AS entity_name,
        COALESCE(si.company, 'Unknown Company') AS company,
        COALESCE(si.cost_center, 'No Branch') AS branch,
        DATE_FORMAT(si.posting_date, '%%b %%Y') AS month_year,
        DATE_FORMAT(si.posting_date, '%%Y-%%m') AS sort_date,
        SUM(sii.amount) AS total_amount,
        COUNT(DISTINCT si.name) AS invoice_count,
        SUM(sii.qty) AS total_qty
    FROM `tabSales Invoice` si
    INNER JOIN `tabSales Invoice Item` sii ON si.name = sii.parent
    INNER JOIN `tabItem` i ON sii.item_code = i.name
    INNER JOIN `tabItem Group` ig ON i.item_group = ig.name
    WHERE 
        si.docstatus = 1
        AND si.status NOT IN ('Cancelled', 'Return')
        AND i.item_group NOT IN ('Raw Material', 'Services', 'Sub Assemblies', 'Consumable', 'Furniture', 'EXPENSE', 'FIXED ASSET')
        
    """
    
    # Query to get entity totals for sorting
    entity_totals_query = """
    SELECT
        CASE 
            WHEN si.cost_center IS NOT NULL AND si.cost_center != '' 
            THEN CONCAT(COALESCE(si.company, 'Unknown'), ' - ', si.cost_center)
            ELSE COALESCE(si.company, 'Unknown Company')
        END AS entity_name,
        SUM(sii.amount) AS total_amount
    FROM `tabSales Invoice` si
    INNER JOIN `tabSales Invoice Item` sii ON si.name = sii.parent
    INNER JOIN `tabItem` i ON sii.item_code = i.name
    INNER JOIN `tabItem Group` ig ON i.item_group = ig.name
    WHERE 
        si.docstatus = 1
        AND si.status NOT IN ('Cancelled', 'Return')
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
            si.company,
            si.cost_center,
            DATE_FORMAT(si.posting_date, '%%Y-%%m'),
            DATE_FORMAT(si.posting_date, '%%b %%Y')
        ORDER BY 
            si.company,
            si.cost_center,
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
            "title": "Consolidated Total Selling - All Companies & Branches",
            "chart_options": {
                "responsive": True,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"Total Selling by Company/Branch (Grand Total: ₹{grand_total:,.0f})"
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
        frappe.log_error(f"Error in consolidated_total_selling query: {str(e)}")
        return {
            "chart_type": "bar",
            "labels": [],
            "datasets": [],
            "error": str(e),
            "success": False
        }

@frappe.whitelist()
def get_entity_wise_selling(filters=None):
    """
    Get summary of all entities with their totals for a single-bar-per-entity chart
    """
    try:
        result = consolidated_total_selling(filters)
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
def get_top_customers_raw_bar(filters=None, branch=None, company=None, limit=10):
    """
    Top Customers Raw Bar Chart
    Branch wise and company wise different chart
    Shows top customers by sales amount
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
            si.customer_name,
            si.customer,
            COUNT(DISTINCT si.name) as invoice_count,
            SUM(si.total) as total_amount,
            SUM(si.net_total) as net_amount,
            AVG(si.total) as avg_invoice_value
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON si.name = sii.parent
        INNER JOIN `tabItem` i ON sii.item_code = i.name
        INNER JOIN `tabItem Group` ig ON i.item_group = ig.name
        WHERE 
            si.docstatus = 1
            AND si.status NOT IN ('Cancelled', 'Return')
            AND i.item_group NOT IN ('Raw Material', 'Services', 'Sub Assemblies', 'Consumable', 'Furniture', 'EXPENSE', 'FIXED ASSET')
            
    """
    
    try:
        # Apply filters
        query, params = apply_filters_to_query(base_query, filters)
        query += """
        GROUP BY si.customer, si.customer_name
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
            # Format the label to include customer name and total amount
            label = f"{row['customer_name']} (₹{row['total_amount']:,.0f})"
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
        frappe.log_error(f"Error in get_top_customers_raw_bar: {str(e)}")
        return {
            "labels": [],
            "data": [],
            "backgroundColor": []
        }

@frappe.whitelist()
def get_top_customers_by_branch(filters=None):
    """
    Get top customers for each branch with color grouping
    """
    base_query = """
        SELECT 
            si.cost_center as branch,
            si.customer_name,
            SUM(si.total) as total_amount,
            COUNT(DISTINCT si.name) as invoice_count
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON si.name = sii.parent
        INNER JOIN `tabItem` i ON sii.item_code = i.name
        INNER JOIN `tabItem Group` ig ON i.item_group = ig.name
        WHERE 
            si.docstatus = 1 
            AND si.status NOT IN ('Cancelled', 'Return')
            AND si.cost_center IS NOT NULL 
            AND si.cost_center != ''
            AND i.item_group NOT IN ('Raw Material', 'Services', 'Sub Assemblies', 'Consumable', 'Furniture', 'EXPENSE', 'FIXED ASSET')
            
    """
    
    try:
        # Apply filters
        query, params = apply_filters_to_query(base_query, filters)
        query += """
        GROUP BY si.cost_center, si.customer_name
        ORDER BY si.cost_center, total_amount DESC
        """
        
        result = frappe.db.sql(query, params, as_dict=True)
        
        # Color palette for branches
        branch_colors = {
            'Main - HKE': '#36a2eb',      # Blue
            'Palanpur - HKE': '#ff6384',  # Red
            'Causeway - HKE': '#4bc0c0',  # Teal
            'Default': '#ffce56'          # Yellow
        }
        
        # Process data by branch
        branch_data = {}
        for row in result:
            branch = row['branch']
            if branch not in branch_data:
                branch_data[branch] = []
            
            # Only take top 5 customers per branch
            if len(branch_data[branch]) < 5:
                branch_data[branch].append({
                    'customer': row['customer_name'],
                    'amount': float(row['total_amount'])
                })
        
        # Get all unique customers across branches
        all_customers = set()
        for branch_customers in branch_data.values():
            for customer in branch_customers:
                all_customers.add(customer['customer'])
        
        # Sort customers by total amount
        customer_labels = sorted(list(all_customers))
        
        # Create datasets (one per branch)
        datasets = []
        for branch, customers in branch_data.items():
            # Create a map of customer to amount for this branch
            customer_amounts = {c['customer']: c['amount'] for c in customers}
            
            # Create dataset with amounts for all customers (0 if customer not in this branch)
            data = [customer_amounts.get(customer, 0) for customer in customer_labels]
            
            datasets.append({
                'label': branch,
                'data': data,
                'backgroundColor': branch_colors.get(branch, branch_colors['Default'])
            })
        
        # Format customer labels with their total amounts
        formatted_labels = []
        for customer in customer_labels:
            total = sum(d['data'][customer_labels.index(customer)] for d in datasets)
            formatted_labels.append(f"{customer} (₹{total:,.0f})")
        
        return {
            "labels": formatted_labels,
            "datasets": datasets,
            "filters_applied": filters
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_top_customers_by_branch: {str(e)}")
        return {
            "labels": [],
            "datasets": []
        }

@frappe.whitelist()
def get_top_customers_by_company(filters=None):
    """
    Get top customers for each company
    """
    base_query = """
        SELECT 
            si.company,
            si.customer_name,
            SUM(si.total) as total_amount
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON si.name = sii.parent
        INNER JOIN `tabItem` i ON sii.item_code = i.name
        INNER JOIN `tabItem Group` ig ON i.item_group = ig.name
        WHERE 
            si.docstatus = 1 
            AND si.status NOT IN ('Cancelled', 'Return')
            AND si.company IS NOT NULL 
            AND si.company != ''
            AND i.item_group NOT IN ('Raw Material', 'Services', 'Sub Assemblies', 'Consumable', 'Furniture', 'EXPENSE', 'FIXED ASSET')
            
    """
    
    try:
        # Apply filters
        query, params = apply_filters_to_query(base_query, filters)
        query += """
        GROUP BY si.company, si.customer_name
        ORDER BY si.company, total_amount DESC
        """
        
        result = frappe.db.sql(query, params, as_dict=True)
        
        # Color palette for the bars
        color_palette = [
            '#ff6384', '#36a2eb', '#ffce56', '#4bc0c0', '#9966ff',
            '#f67019', '#f53794', '#acc236', '#166a8f', '#00a950'
        ]
        
        # Process data by company
        company_data = {}
        for row in result:
            company = row['company']
            if company not in company_data:
                company_data[company] = {
                    'labels': [],
                    'data': [],
                    'backgroundColor': []
                }
            
            # Only take top 5 customers per company
            if len(company_data[company]['labels']) < 5:
                label = f"{row['customer_name']} (₹{row['total_amount']:,.0f})"
                company_data[company]['labels'].append(label)
                company_data[company]['data'].append(float(row['total_amount']))
                company_data[company]['backgroundColor'].append(
                    color_palette[len(company_data[company]['labels']) - 1]
                )
        
        # Combine all company data
        labels = []
        data = []
        backgroundColor = []
        
        for company, company_info in company_data.items():
            # Add company name as a section header
            if company_info['labels']:
                if labels:  # Add spacing between companies
                    labels.append("")
                    data.append(0)
                    backgroundColor.append('transparent')
                labels.append(f"--- {company} ---")
                data.append(0)
                backgroundColor.append('transparent')
                
                labels.extend(company_info['labels'])
                data.extend(company_info['data'])
                backgroundColor.extend(company_info['backgroundColor'])
        
        return {
            "labels": labels,
            "data": data,
            "backgroundColor": backgroundColor,
            "filters_applied": filters
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_top_customers_by_company: {str(e)}")
        return {
            "labels": [],
            "data": [],
            "backgroundColor": []
        }

@frappe.whitelist()
def get_consolidated_top_customers(filters=None):
    """
    Get consolidated top 10 customers across all companies
    """
    base_query = """
        SELECT 
            si.customer_name,
            si.customer,
            COUNT(DISTINCT si.name) as invoice_count,
            SUM(si.total) as total_amount,
            GROUP_CONCAT(DISTINCT si.company) as companies
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON si.name = sii.parent
        INNER JOIN `tabItem` i ON sii.item_code = i.name
        INNER JOIN `tabItem Group` ig ON i.item_group = ig.name
        WHERE 
            si.docstatus = 1 
            AND si.status NOT IN ('Cancelled', 'Return')
            AND i.item_group NOT IN ('Raw Material', 'Services', 'Sub Assemblies', 'Consumable', 'Furniture', 'EXPENSE', 'FIXED ASSET')
            
    """
    
    try:
        # Apply filters
        query, params = apply_filters_to_query(base_query, filters)
        query += """
        GROUP BY si.customer, si.customer_name
        ORDER BY total_amount DESC
        LIMIT 10
        """
        
        result = frappe.db.sql(query, params, as_dict=True)
        
        # Color gradient from blue to purple
        colors = [
            '#3498db', '#4b6cb7', '#6254b2', '#783bad', '#8e22a8',
            '#a40aa3', '#ba009e', '#d00099', '#e60095', '#ff0090'
        ]
        
        labels = []
        data = []
        backgroundColor = []
        
        for i, row in enumerate(result):
            # Format label with customer name, amount and companies
            amount_formatted = f"₹{float(row['total_amount']):,.0f}"
            companies = row['companies'].replace(',', ', ')
            label = f"{row['customer_name']} ({amount_formatted}) - {companies}"
            
            labels.append(label)
            data.append(float(row['total_amount']))
            backgroundColor.append(colors[i])
        
        return {
            "labels": labels,
            "data": data,
            "backgroundColor": backgroundColor,
            "filters_applied": filters
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_consolidated_top_customers: {str(e)}")
        return {
            "labels": [],
            "data": [],
            "backgroundColor": []
        }

@frappe.whitelist()
def get_top_selling_products_by_branch(filters=None):
    """
    Get top selling products for each branch with percentage calculations
    """
    base_query = """
        SELECT 
            si.cost_center as branch,
            sii.item_name,
            sii.item_code,
            SUM(sii.amount) as total_amount,
            SUM(sii.qty) as total_quantity,
            COUNT(DISTINCT si.name) as invoice_count
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON si.name = sii.parent
        INNER JOIN `tabItem` i ON sii.item_code = i.name
        INNER JOIN `tabItem Group` ig ON i.item_group = ig.name
        WHERE 
            si.docstatus = 1 
            AND si.status NOT IN ('Cancelled', 'Return')
            AND si.cost_center IS NOT NULL 
            AND si.cost_center != ''
            AND i.item_group NOT IN ('Raw Material', 'Services', 'Sub Assemblies', 'Consumable', 'Furniture', 'EXPENSE', 'FIXED ASSET')
            
    """
    
    try:
        # Apply filters
        query, params = apply_filters_to_query(base_query, filters)
        query += """
        GROUP BY si.cost_center, sii.item_code, sii.item_name
        ORDER BY si.cost_center, total_amount DESC
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
            branch_data[branch]['total_branch_amount'] += float(row['total_amount'])
            
            # Only store top 10 items per branch
            if len(branch_data[branch]['items']) < 10:
                branch_data[branch]['items'].append({
                    'item_name': row['item_name'],
                    'amount': float(row['total_amount']),
                    'quantity': float(row['total_quantity'])
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
        frappe.log_error(f"Error in get_top_selling_products_by_branch: {str(e)}")
        return {
            'datasets': {},
            'success': False,
            'error': str(e)
        }

@frappe.whitelist()
def get_top_selling_products_by_company(filters=None):
    """
    Get top selling products for each company with percentage calculations
    """
    base_query = """
        SELECT 
            si.company,
            sii.item_name,
            sii.item_code,
            SUM(sii.amount) as total_amount,
            SUM(sii.qty) as total_quantity,
            COUNT(DISTINCT si.name) as invoice_count,
            COUNT(DISTINCT si.company) as company_count
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON si.name = sii.parent
        INNER JOIN `tabItem` i ON sii.item_code = i.name
        INNER JOIN `tabItem Group` ig ON i.item_group = ig.name
        WHERE 
            si.docstatus = 1 
            AND si.status NOT IN ('Cancelled', 'Return')
            AND si.company IS NOT NULL 
            AND si.company != ''
            AND i.item_group NOT IN ('Raw Material', 'Services', 'Sub Assemblies', 'Consumable', 'Furniture', 'EXPENSE', 'FIXED ASSET')
            
    """
    
    try:
        # Apply filters
        query, params = apply_filters_to_query(base_query, filters)
        query += """
        GROUP BY si.company, sii.item_code, sii.item_name
        ORDER BY si.company, total_amount DESC
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
        error_msg = f"Error in get_top_selling_products_by_company: {str(e)}"
        frappe.log_error(error_msg)
        return {
            'datasets': {},
            'success': False,
            'error': error_msg
        }

@frappe.whitelist()
def get_consolidated_top_selling_products(filters=None):
    """
    Get consolidated top 10 selling products across all companies
    Shows overall top selling products regardless of company
    """
    base_query = """
        SELECT 
            sii.item_name,
            sii.item_code,
            SUM(sii.amount) as total_amount,
            SUM(sii.qty) as total_quantity,
            COUNT(DISTINCT si.name) as invoice_count,
            COUNT(DISTINCT si.company) as company_count,
            GROUP_CONCAT(DISTINCT si.company) as companies
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON si.name = sii.parent
        INNER JOIN `tabItem` i ON sii.item_code = i.name
        INNER JOIN `tabItem Group` ig ON i.item_group = ig.name
        WHERE 
            si.docstatus = 1 
            AND si.status NOT IN ('Cancelled', 'Return')
            AND i.item_group NOT IN ('Raw Material', 'Services', 'Sub Assemblies', 'Consumable', 'Furniture', 'EXPENSE', 'FIXED ASSET')
            
    """
    
    try:
        # Apply filters
        query, params = apply_filters_to_query(base_query, filters)
        query += """
        GROUP BY sii.item_code, sii.item_name
        ORDER BY total_amount DESC
        LIMIT 10
        """
        
        result = frappe.db.sql(query, params, as_dict=True)
        
        if not result:
            return {
                'labels': [],
                'data': [],
                'backgroundColor': [],
                'success': True,
                'message': 'No data found'
            }
        
        # Calculate total amount for percentage calculations
        total_amount = sum(float(row['total_amount']) for row in result)
        
        # Color palette - gradient from blue to purple
        colors = [
            '#3498db', '#4b6cb7', '#6254b2', '#783bad', '#8e22a8',
            '#a40aa3', '#ba009e', '#d00099', '#e60095', '#ff0090'
        ]
        
        # Prepare data for chart
        labels = []
        data = []
        backgroundColor = []
        tooltips = []
        
        for i, row in enumerate(result):
            amount = float(row['total_amount'])
            percentage = (amount / total_amount) * 100
            companies = row['companies'].replace(',', ', ')
            
            # Format label with item name and percentage
            label = f"{row['item_name']} ({percentage:.1f}%)"
            tooltip = (f"{row['item_name']}\n"
                      f"Amount: ₹{amount:,.2f}\n"
                      f"Quantity: {row['total_quantity']}\n"
                      f"Companies: {companies}")
            
            labels.append(label)
            data.append(amount)
            backgroundColor.append(colors[i])
            tooltips.append(tooltip)
        
        return {
            'labels': labels,
            'data': data,
            'backgroundColor': backgroundColor,
            'tooltips': tooltips,
            'total_amount': total_amount,
            'filters_applied': filters,
            'success': True
        }
        
    except Exception as e:
        error_msg = f"Error in get_consolidated_top_selling_products: {str(e)}"
        frappe.log_error(error_msg)
        return {
            'labels': [],
            'data': [],
            'backgroundColor': [],
            'success': False,
            'error': error_msg
        }
