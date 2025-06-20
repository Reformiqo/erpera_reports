import frappe
def get_context(context):
    context.active_page = "buying"

@frappe.whitelist()
def total_buying():
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
        DATE_FORMAT(pi.posting_date, '%b %Y') AS month_year,
        DATE_FORMAT(pi.posting_date, '%Y-%m') AS sort_date,
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
        AND pi.posting_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
        AND pi.cost_center IS NOT NULL
        AND pi.cost_center != ''
    GROUP BY 
        pi.cost_center,
        DATE_FORMAT(pi.posting_date, '%Y-%m'),
        DATE_FORMAT(pi.posting_date, '%b %Y')
    ORDER BY 
        pi.cost_center,
        sort_date
    """
    
    # Query for company-wise data
    company_query = """
    SELECT
        COALESCE(pi.company, 'Unknown Company') AS company,
        DATE_FORMAT(pi.posting_date, '%b %Y') AS month_year,
        DATE_FORMAT(pi.posting_date, '%Y-%m') AS sort_date,
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
        AND pi.posting_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
        AND pi.company IS NOT NULL
        AND pi.company != ''
    GROUP BY 
        pi.company,
        DATE_FORMAT(pi.posting_date, '%Y-%m'),
        DATE_FORMAT(pi.posting_date, '%b %Y')
    ORDER BY 
        pi.company,
        sort_date
    """
    
    # Summary query for overall totals
    summary_query = """
    SELECT
        DATE_FORMAT(pi.posting_date, '%b %Y') AS month_year,
        DATE_FORMAT(pi.posting_date, '%Y-%m') AS sort_date,
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
        AND pi.posting_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
    GROUP BY 
        DATE_FORMAT(pi.posting_date, '%Y-%m'),
        DATE_FORMAT(pi.posting_date, '%b %Y')
    ORDER BY sort_date
    """
    
    try:
        # Execute queries
        branch_result = frappe.db.sql(branch_query, as_dict=True)
        company_result = frappe.db.sql(company_query, as_dict=True)
        summary_result = frappe.db.sql(summary_query, as_dict=True)
        
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
                "filter_criteria": "Stock items only (excluding expense & service items)"
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
def get_branch_wise_buying():
    """
    Separate endpoint for branch-wise data only
    """
    result = total_buying()
    if result.get('success'):
        return result['branch_wise']
    return {"labels": [], "datasets": [], "error": result.get('error')}

@frappe.whitelist()
def get_company_wise_buying():
    """
    Separate endpoint for company-wise data only
    """
    result = total_buying()
    if result.get('success'):
        return result['company_wise']
    return {"labels": [], "datasets": [], "error": result.get('error')}

@frappe.whitelist()
def get_buying_summary():
    """
    Separate endpoint for summary data only
    """
    result = total_buying()
    if result.get('success'):
        return result['summary']
    return {"labels": [], "data": [], "error": result.get('error')}

@frappe.whitelist()
def get_sample_doughnut_chart_data():
    """
    Sample API for doughnut chart data
    """
    return {
        "labels": ["Red", "Blue", "Yellow", "Green"],
        "data": [12, 19, 3, 5],
        "backgroundColor": ["#ff6384", "#36a2eb", "#ffce56", "#4bc0c0"]
    }

@frappe.whitelist()
def get_top_buying_product_pie(branch=None, company=None, limit=5):
    """
    Top Buying Product Pie Chart
    Branch wise and company wise different chart
    Only choose items in stock (not expense or service items)
    """
    filters = []
    params = []
    if branch:
        filters.append("pi.cost_center = %s")
        params.append(branch)
    if company:
        filters.append("pi.company = %s")
        params.append(company)
    filters.append("i.is_stock_item = 1")
    filters.append("pi.docstatus = 1")
    filters.append("pi.status NOT IN ('Cancelled', 'Return')")
    filters.append("pii.item_group NOT IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES')")
    where_clause = " AND ".join(filters)
    sql = f"""
        SELECT pii.item_name, SUM(pii.amount) as total_amount
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
        LEFT JOIN `tabItem` i ON pii.item_code = i.name
        WHERE {where_clause}
        GROUP BY pii.item_name
        ORDER BY total_amount DESC
        LIMIT %s
    """
    params.append(limit)
    result = frappe.db.sql(sql, params, as_dict=True)
    color_palette = [
        '#ff6384', '#36a2eb', '#ffce56', '#4bc0c0', '#9966ff',
        '#f67019', '#f53794', '#acc236', '#166a8f', '#00a950'
    ]
    labels = [row['item_name'] for row in result]
    data = [row['total_amount'] for row in result]
    backgroundColor = [color_palette[i % len(color_palette)] for i in range(len(labels))]
    return {
        "labels": labels,
        "data": data,
        "backgroundColor": backgroundColor
    } 
@frappe.whitelist()
def consolidated_total_buying():
    """
    Chart Name: Consolidate Total Buying
    Chart Type: Bar
    Note 1: All the company's buying shows in one bar chart using different colour for each company or branch
    Note 2: Only Choose item which is in stock not choose expense or service item
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
        DATE_FORMAT(pi.posting_date, '%b %Y') AS month_year,
        DATE_FORMAT(pi.posting_date, '%Y-%m') AS sort_date,
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
        AND pi.posting_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
    GROUP BY 
        entity_name,
        pi.company,
        pi.cost_center,
        DATE_FORMAT(pi.posting_date, '%Y-%m'),
        DATE_FORMAT(pi.posting_date, '%b %Y')
    ORDER BY 
        pi.company,
        pi.cost_center,
        sort_date
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
        AND pi.posting_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
    GROUP BY entity_name
    ORDER BY total_amount DESC
    """
    
    try:
        # Execute queries
        consolidated_result = frappe.db.sql(consolidated_query, as_dict=True)
        entity_totals_result = frappe.db.sql(entity_totals_query, as_dict=True)
        
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
            '#c2c2f0', '#ffb3e6', '#c4e17f', '#76d7c4', '#f7dc6f',
            '#bb8fce', '#85c1e9', '#f8c471', '#82e0aa', '#f1948a'
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
        
        # Calculate monthly totals for additional insight
        monthly_totals = []
        for month in sorted_months:
            monthly_total = sum([entity_data[entity].get(month, 0) for entity in entity_data.keys()])
            monthly_totals.append(monthly_total)
        
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
            "summary": {
                "total_entities": len(datasets),
                "grand_total": grand_total,
                "monthly_totals": monthly_totals,
                "date_range": "Last 12 months",
                "top_entity": entity_order[0] if entity_order else "N/A",
                "top_entity_amount": datasets[0]['entity_total'] if datasets else 0
            },
            "metadata": {
                "filter_criteria": "Stock items only (excluding expense & service items)",
                "entities": [ds['label'] for ds in datasets],
                "months_covered": len(sorted_months)
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
def get_entity_summary():
    """
    Get summary of all entities with their totals for a single-bar-per-entity chart
    """
    try:
        result = consolidated_total_buying()
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
def get_top_supplier_for_expenses_raw_bar(branch=None, company=None, limit=5):
    """
    Top Supplier For Expenses Raw Bar
    Branch wise and company wise different chart
    Only for item which is expense, service item and Asset buying supplier
    """
    filters = []
    params = []
    if branch:
        filters.append("pi.cost_center = %s")
        params.append(branch)
    if company:
        filters.append("pi.company = %s")
        params.append(company)
    filters.append("pi.docstatus = 1")
    filters.append("pi.status NOT IN ('Cancelled', 'Return')")
    filters.append("pii.item_group IN ('EXPENSE', 'FIXED ASSET', 'Service', 'SERVICES')")
    where_clause = " AND ".join(filters)
    sql = f"""
        SELECT pi.supplier, SUM(pii.amount) as total_amount
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
        WHERE {where_clause}
        GROUP BY pi.supplier
        ORDER BY total_amount DESC
        LIMIT %s
    """
    params.append(limit)
    result = frappe.db.sql(sql, params, as_dict=True)
    color_palette = [
        '#ff6384', '#36a2eb', '#ffce56', '#4bc0c0', '#9966ff',
        '#f67019', '#f53794', '#acc236', '#166a8f', '#00a950'
    ]
    labels = [row['supplier'] for row in result]
    data = [row['total_amount'] for row in result]
    backgroundColor = [color_palette[i % len(color_palette)] for i in range(len(labels))]
    return {
        "labels": labels,
        "data": data,
        "backgroundColor": backgroundColor
    }