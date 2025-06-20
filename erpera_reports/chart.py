import frappe 

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