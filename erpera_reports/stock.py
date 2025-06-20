import frappe
from frappe import _

@frappe.whitelist()
def get_total_stock():
    """
    Get total stock value for each branch and company.
    """
    
    # Branch-wise stock query
    branch_query = """
        SELECT
            wh.cost_center AS branch,
            SUM(COALESCE(b.stock_value, 0)) AS total_stock_value
        FROM `tabBin` b
        JOIN `tabWarehouse` wh ON b.warehouse = wh.name
        WHERE
            wh.cost_center IS NOT NULL
            AND wh.cost_center != ''
            AND COALESCE(b.actual_qty, 0) > 0
        GROUP BY
            wh.cost_center
        HAVING
            SUM(COALESCE(b.stock_value, 0)) > 0
        ORDER BY
            total_stock_value DESC
    """

    # Company-wise stock query
    company_query = """
        SELECT
            wh.company,
            SUM(COALESCE(b.stock_value, 0)) AS total_stock_value
        FROM `tabBin` b
        JOIN `tabWarehouse` wh ON b.warehouse = wh.name
        WHERE
            wh.company IS NOT NULL
            AND wh.company != ''
            AND COALESCE(b.actual_qty, 0) > 0
        GROUP BY
            wh.company
        HAVING
            SUM(COALESCE(b.stock_value, 0)) > 0
        ORDER BY
            total_stock_value DESC
    """

    try:
        branch_result = frappe.db.sql(branch_query, as_dict=True)
        company_result = frappe.db.sql(company_query, as_dict=True)
        
        # --- Start Debug Logging ---
        frappe.log_error("Stock Report Debug: Branch Query Result", branch_result)
        frappe.log_error("Stock Report Debug: Company Query Result", company_result)
        # --- End Debug Logging ---
        
        # Prepare branch data
        branch_labels = [row['branch'] for row in branch_result]
        branch_data = [float(row['total_stock_value']) for row in branch_result]
        
        # Prepare company data
        company_labels = [row['company'] for row in company_result]
        company_data = [float(row['total_stock_value']) for row in company_result]

        # Colors
        colors = ['#2ca02c', '#1f77b4', '#ff7f0e', '#d62728', '#9467bd', '#8c564b']

        response = {
            "branch_wise": {
                "labels": branch_labels,
                "data": branch_data,
                "backgroundColor": colors,
                "title": "Total Stock - Branch Wise"
            },
            "company_wise": {
                "labels": company_labels,
                "data": company_data,
                "backgroundColor": colors,
                "title": "Total Stock - Company Wise"
            },
            "success": True
        }

        # --- Start Debug Logging ---
        frappe.log_error("Stock Report Debug: Final Response", response)
        # --- End Debug Logging ---

        return response

    except Exception as e:
        frappe.log_error(f"Error in get_total_stock: {str(e)}")
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def get_branch_wise_stock():
    """
    Separate endpoint for branch-wise stock data only
    """
    result = get_total_stock()
    if result.get('success'):
        return result['branch_wise']
    return {"labels": [], "data": [], "error": result.get('error')}

@frappe.whitelist()
def get_company_wise_stock():
    """
    Separate endpoint for company-wise stock data only
    """
    result = get_total_stock()
    if result.get('success'):
        return result['company_wise']
    return {"labels": [], "data": [], "error": result.get('error')}
