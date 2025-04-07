# Common Statistics Canada Tables and Vectors

This document lists frequently used Statistics Canada tables and vectors for reference when implementing and testing the MCP server.

## Key Economic Indicators

### Consumer Price Index (CPI)

| Description | Product ID (PID) | Table Name | Key Vectors |
|-------------|------------------|------------|-------------|
| CPI, monthly, not seasonally adjusted | 1810000401 | Consumer Price Index, monthly, not seasonally adjusted | v41690973 (All-items, Canada)<br>v41690914 (Food, Canada)<br>v41691048 (Shelter, Canada) |
| CPI, monthly, percentage change | 1810000601 | Consumer Price Index, monthly, percentage change, not seasonally adjusted | v74804 (All-items, monthly % change, Canada)<br>v74805 (All-items excluding food and energy, monthly % change, Canada) |
| CPI, annual average | 1810000501 | Consumer Price Index, annual average, not seasonally adjusted | v41693271 (All-items, Canada) |

### Gross Domestic Product (GDP)

| Description | Product ID (PID) | Table Name | Key Vectors |
|-------------|------------------|------------|-------------|
| GDP by industry, monthly | 3610043401 | Gross domestic product (GDP) at basic prices, by industry, monthly | v65201210 (All industries, Canada)<br>v65201218 (Goods-producing industries)<br>v65201462 (Construction) |
| GDP by expenditure, quarterly | 3610010401 | Gross domestic product (GDP), expenditure-based, quarterly | v62305752 (GDP at market prices)<br>v62305753 (Household final consumption expenditure) |
| GDP by income, quarterly | 3610014001 | Gross domestic product (GDP), income-based, quarterly | v62306021 (Compensation of employees) |

### Labour Force Survey (LFS)

| Description | Product ID (PID) | Table Name | Key Vectors |
|-------------|------------------|------------|-------------|
| Labour force characteristics | 1410028701 | Labour force characteristics by sex and age group, monthly, unadjusted | v2062810 (Unemployment rate, both sexes, 15 years and over)<br>v2062811 (Employment rate, both sexes, 15 years and over) |
| Employment by industry | 1410020201 | Employment by industry, monthly, unadjusted | v2057771 (Total employed, all industries) |
| Employment by province | 1410028801 | Labour force characteristics by province, monthly, unadjusted | v2187617 (Ontario, unemployment rate) |

### International Merchandise Trade

| Description | Product ID (PID) | Table Name | Key Vectors |
|-------------|------------------|------------|-------------|
| Merchandise trade | 1210001101 | International merchandise trade by commodity, monthly | v193801 (Total exports, all countries)<br>v193825 (Total imports, all countries) |
| Merchandise trade by country | 1210001401 | Merchandise imports and exports, by country, monthly | v196493 (Exports to United States) |

### Building Permits

| Description | Product ID (PID) | Table Name | Key Vectors |
|-------------|------------------|------------|-------------|
| Building permits, monthly | 3410006601 | Building permits, by type of structure and type of work | v42065 (Total residential, Canada) |

### Retail Trade

| Description | Product ID (PID) | Table Name | Key Vectors |
|-------------|------------------|------------|-------------|
| Retail trade, monthly | 2010008001 | Retail trade sales by province and territory | v52367508 (Total, all subsectors, Canada) |

## Population and Demographics

### Population Estimates

| Description | Product ID (PID) | Table Name | Key Vectors |
|-------------|------------------|------------|-------------|
| Population estimates, quarterly | 1710000901 | Population estimates, quarterly | v1 (Canada, both sexes) |
| Population by age and sex | 1710010501 | Annual demographic estimates: Canada, provinces and territories | v466668 (Canada, both sexes, all ages) |

### Immigration Statistics

| Description | Product ID (PID) | Table Name | Key Vectors |
|-------------|------------------|------------|-------------|
| Immigrant arrivals | 1710004301 | Immigrant arrivals by province or territory | v23250 (Canada, all immigrants) |

## Business and Industry

### Manufacturing

| Description | Product ID (PID) | Table Name | Key Vectors |
|-------------|------------------|------------|-------------|
| Manufacturing sales | 1610004701 | Manufacturing sales by industry and province, monthly | v807480 (Total, manufacturing, Canada) |

### Wholesale Trade

| Description | Product ID (PID) | Table Name | Key Vectors |
|-------------|------------------|------------|-------------|
| Wholesale trade, monthly | 2010006801 | Wholesale trade, sales | v52558384 (Total, all subsectors, Canada) |

## Using These Examples

When testing the StatCan MCP server, you can use these Product IDs and Vector IDs to validate data retrieval functionality. For example:

```python
# Example: Get CPI data for All-items Canada
await wds_client.get_data_from_vectors(["v41690973"], 10)

# Example: Get GDP data for all industries
await wds_client.get_data_from_vectors(["v65201210"], 10)

# Example: Get metadata for the CPI monthly table
await wds_client.get_cube_metadata("1810000401")
```

These examples cover a wide range of common economic and demographic indicators that are frequently accessed by users of Statistics Canada data.