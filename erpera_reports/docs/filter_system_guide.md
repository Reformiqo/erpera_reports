# Bar Chart Filter System Guide

## Overview
The enhanced bar chart filter system provides a comprehensive filtering solution for stock management reports. It includes both static and dynamic filter options, with automatic population from database queries.

## Features

### Core Features
- **Collapsible Filter Panels**: Clean, organized filter interface
- **Date Range Filters**: From and to date selection
- **Item Filters**: Filter by specific items or item groups
- **Company & Branch Filters**: Multi-level organizational filtering
- **Dynamic Population**: Automatic loading of filter options from database
- **Fallback Data**: Sample data when database queries fail
- **Real-time Updates**: Charts update automatically when filters change

### Enhanced Features
- **Comprehensive Filter Options**: New `get_comprehensive_filter_options()` function
- **Database Integration**: Real data from Item, Item Group, Company, and Branch tables
- **Error Handling**: Graceful fallback to sample data
- **Performance Optimization**: Limited query results for better performance

## Usage

### Basic Implementation
```html
{% set chart_config = {
    'chart_id': 'my-chart',
    'title': 'My Chart',
    'backgroundColor': '#667eea',
    'chart_type': 'bar',
    'width': '100%',
    'data_url': '/api/method/erpera_reports.erpera_reports.api.get_filtered_stock_data',
    'filters': {
        'item_list': [],
        'item_groups': [],
        'companies': [],
        'branches': []
    }
} %}
{% include "erpera_reports/templates/includes/bar.html" %}
```

### Dynamic Filter Population
```javascript
// Load filter options when page loads
document.addEventListener('DOMContentLoaded', function() {
    frappe.call({
        method: 'erpera_reports.erpera_reports.api.get_comprehensive_filter_options',
        callback: function(r) {
            if (r.message) {
                populateFilterOptions(r.message);
            }
        }
    });
});

function populateFilterOptions(options) {
    // Populate item filters
    if (options.item_list) {
        populateFilterDropdown('item_list', options.item_list);
    }
    
    // Populate item group filters
    if (options.item_groups) {
        populateFilterDropdown('item_groups', options.item_groups);
    }
    
    // Populate company filters
    if (options.companies) {
        populateFilterDropdown('companies', options.companies);
    }
    
    // Populate branch filters
    if (options.branches) {
        populateFilterDropdown('branches', options.branches);
    }
}
```

## Backend API Functions

### 1. get_filtered_stock_data()
Retrieves filtered stock data based on various criteria.

**Parameters:**
- `filters` (dict): Filter criteria including:
  - `from_date`: Start date for filtering
  - `to_date`: End date for filtering
  - `item`: Specific item code
  - `item_group`: Item group filter
  - `company`: Company filter
  - `branch`: Branch filter
  - `warehouse`: Custom warehouse filter

**Returns:**
```json
{
    "labels": ["Item 1", "Item 2", "Item 3"],
    "data": [1000, 2000, 3000],
    "backgroundColor": "#667eea",
    "filters_applied": {...}
}
```

### 2. get_comprehensive_filter_options()
Provides comprehensive filter options with database integration and fallback data.

**Returns:**
```json
{
    "item_list": [
        {"value": "ITEM-001", "label": "Laptop Dell XPS 13", "selected": false},
        {"value": "ITEM-002", "label": "Wireless Mouse Logitech", "selected": false}
    ],
    "item_groups": [
        {"value": "Electronics", "label": "Electronics", "selected": false},
        {"value": "Accessories", "label": "Accessories", "selected": false}
    ],
    "companies": [
        {"value": "Company A", "label": "Company A", "selected": false},
        {"value": "Company B", "label": "Company B", "selected": false}
    ],
    "branches": [
        {"value": "Branch 1", "label": "Main Branch", "selected": false},
        {"value": "Branch 2", "label": "North Branch", "selected": false}
    ]
}
```

### 3. get_filter_options()
Legacy function for basic filter options.

## Advanced Filter Configuration

### Custom Filter Types
You can add custom filter types by extending the filter configuration:

```html
{% set chart_config = {
    'filters': {
        'item_list': [],
        'item_groups': [],
        'companies': [],
        'branches': [],
        'custom': [
            {
                'name': 'warehouse',
                'label': 'Warehouse',
                'type': 'select',
                'options': []
            },
            {
                'name': 'status',
                'label': 'Status',
                'type': 'select',
                'options': [
                    {'value': 'active', 'label': 'Active'},
                    {'value': 'inactive', 'label': 'Inactive'}
                ]
            }
        ]
    }
} %}
```

### Filter Options API
The system automatically handles filter option population through the `get_comprehensive_filter_options()` function, which:

1. **Queries Real Data**: Attempts to fetch data from database tables
2. **Provides Fallback**: Returns sample data if database queries fail
3. **Limits Results**: Restricts query results for performance
4. **Handles Errors**: Logs errors and provides graceful degradation

## Database Integration

### Tables Used
- `tabItem`: For item list options
- `tabItem Group`: For item group options
- `tabCompany`: For company options
- `tabBranch`: For branch options
- `tabWarehouse`: For warehouse options (custom filter)

### Query Optimization
- Limited results (50 items, 20 groups, 10 companies, 10 branches)
- Disabled items are excluded
- Only non-group warehouses are included
- Results are ordered alphabetically

## Best Practices

### 1. Performance
- Use the comprehensive filter options function for better performance
- Limit the number of filter options displayed
- Cache filter options when possible

### 2. User Experience
- Provide meaningful default values
- Include "Select All" or "Clear All" options where appropriate
- Show loading states during filter population

### 3. Error Handling
- Always provide fallback data
- Log errors for debugging
- Show user-friendly error messages

### 4. Data Consistency
- Use consistent naming conventions
- Ensure filter options match available data
- Validate filter values before applying

## Troubleshooting

### Common Issues

1. **Empty Filter Dropdowns**
   - Check if database tables exist and have data
   - Verify the API function is accessible
   - Check browser console for JavaScript errors

2. **Charts Not Updating**
   - Ensure filter change events are properly bound
   - Verify the data URL is correct
   - Check network requests in browser developer tools

3. **Performance Issues**
   - Reduce the number of filter options
   - Implement caching for filter options
   - Optimize database queries

### Debug Mode
Enable debug logging by checking the browser console and Frappe logs for detailed error information.

## Examples

### Complete Implementation Example
See `erpera_reports/templates/pages/stock_dashboard_with_filters.html` for a complete working example.

### API Usage Example
```python
# Frontend JavaScript
frappe.call({
    method: 'erpera_reports.erpera_reports.api.get_comprehensive_filter_options',
    callback: function(r) {
        console.log('Filter options:', r.message);
    }
});

# Backend Python
@frappe.whitelist()
def get_comprehensive_filter_options():
    try:
        # Database queries here
        return {
            'item_list': [...],
            'item_groups': [...],
            'companies': [...],
            'branches': [...]
        }
    except Exception as e:
        frappe.log_error(f"Error: {str(e)}")
        return fallback_data
```

## Migration Guide

### From Static to Dynamic Filters
1. Replace static filter arrays with empty arrays
2. Add JavaScript to populate filters dynamically
3. Use the comprehensive filter options function
4. Test with both real data and fallback scenarios

### Backward Compatibility
The system maintains backward compatibility with existing static filter configurations while providing enhanced dynamic capabilities. 