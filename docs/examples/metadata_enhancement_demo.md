# Metadata Enhancement Demo: StatCan MCP Server

This document demonstrates how the enhanced metadata handling features ensure proper unit display and citation in analysis results.

## Example: Analyzing Unemployment Rate Trends

When analyzing unemployment rate data from Statistics Canada, the following improvements are now in place:

### 1. Enhanced Data Storage

When storing unemployment rate data:

```python
store_dataset(
    series_id="v111955426",
    data=[...],  # Time series data points
    metadata={
        "title": "Unemployment rate",
        "productId": "1410001701",
        "uomDesc": "Percent",
        "scalarFactorDesc": "Units",
        "frequencyDesc": "Monthly"
    }
)
```

Response now includes complete metadata context:
```
Successfully stored dataset 'v111955426' (Percent) from Statistics Canada Table 1410001701 with 60 data points in the database.
```

### 2. Enhanced Analysis Results

When running analysis on stored data:

```python
analysis = analyze_dataset(
    series_id="v111955426",
    analysis_type="trends"
)
```

The results now include:

```json
{
  "slope": 0.0023,
  "intercept": 5.6724,
  "r_squared": 0.7835,
  "trend_direction": "increasing",
  "trend_strength": "strong",
  "annual_change_rate": 0.0276,
  "units_of_measurement": "Percent",
  "title": "Unemployment rate (Percent) - Table 1410001701",
  "interpretation": "Trend analysis for Unemployment rate (Percent):\n- The data shows a strong increasing trend.\n- Annual change rate: 0.03 Percent per year.\n- Model fit (R-squared): 0.784\n\nSource: Statistics Canada, Table 1410001701",
  "citation": {
    "product_id": "1410001701",
    "source": "Statistics Canada",
    "url": "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410001701"
  }
}
```

### 3. Proper Citation Information

When generating a citation:

```python
citation = get_citation(pid="1410001701", format="apa")
```

The response now includes frequency and date range information:

```json
{
  "citation": "Statistics Canada. (April 5, 2024). Labour force characteristics by gender and detailed age group, monthly, unadjusted for seasonality (Monthly) (Table 1410001701). Retrieved from https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410001701",
  "url": "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410001701",
  "format": "apa",
  "details": {
    "title": "Labour force characteristics by gender and detailed age group, monthly, unadjusted for seasonality",
    "release_date": "April 5, 2024",
    "product_id": "1410001701",
    "frequency": "Monthly",
    "start_date": "1976-01-01",
    "end_date": "2024-03-01"
  }
}
```

### 4. Integration with Visualization

When creating visualizations, proper metadata is passed to the Vega-Lite MCP server:

```
View result from create_chart from mcp-vegalite (isaacwasserman/mcp-vegalite-server) {
  "data": [...],
  "mark": "line",
  "encoding": {
    "x": {"field": "date", "type": "temporal", "title": "Date"},
    "y": {"field": "value", "type": "quantitative", "title": "Unemployment Rate (Percent)"}
  },
  "title": "Unemployment Rate (Percent) - Table 1410001701"
}
```

## Benefits of Enhanced Metadata

1. **Improved Data Understanding**:
   - Users always know what units they're looking at (Percent, Dollars, Index points, etc.)
   - Data is properly attributed to its source table
   - Temporal context (frequency, date range) is clearly indicated

2. **Academic Integrity**:
   - Proper citations in multiple formats (APA, MLA, Chicago)
   - Consistent attribution of source data
   - Clear tracking of data lineage

3. **Analysis Context**:
   - Trend analyses include correct units of measurement
   - Statistics include proper scale factors (thousands, millions, etc.)
   - Visualizations properly label axes with units

4. **Long-term Data Storage**:
   - Complete preservation of metadata in persistent database
   - Source table references remain with the data
   - Units of measurement stay connected to the values

This enhancement ensures that users of the StatCan MCP server always have complete context about what data they're working with, how it's measured, and where it comes from.