import frappe

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