# Statistics Canada WDS Code Sets Reference

This document contains the various code sets and reference information used in the Statistics Canada Web Data Service (WDS).

## Status Codes

Status codes indicate the current state of a data point.

| Code | Name | Description |
|------|------|-------------|
| 0 | Normal | The data point is reliable and available for use. |
| 1 | Preliminary | The data point is preliminary and subject to revision. |
| 2 | Revised Normal | The data point has been revised from a previous value. |
| 3 | Revised Preliminary | The data point has been revised from a previous value but is still preliminary. |
| 4 | Discontinued | The data point has been discontinued. |
| 5 | Archived | The data point has been archived. |
| 6 | Suppressed | The data point has been suppressed for confidentiality or reliability reasons. |
| 7 | Withdrawn | The data point has been withdrawn. |
| 8 | Break in Series | There is a break in the time series at this point due to methodology changes. |
| 9 | Not Available | The data point is not available. |
| 10 | Not Applicable | The data point is not applicable for this series. |
| 11 | Terminated | The data point has been terminated. |
| 12 | Missing | The data point is missing. |

## Symbol Codes

Symbol codes provide additional context about a data point.

| Code | Symbol | Description |
|------|--------|-------------|
| 0 | No symbol | No symbol is associated with this data point. |
| 1 | p | Preliminary data. |
| 2 | r | Revised data. |
| 3 | x | Suppressed to meet confidentiality requirements. |
| 4 | e | Estimate. |
| 5 | f | Forecast. |
| 6 | ... | Not available. |
| 7 | .. | Not applicable or not available. |
| 8 | - | Zero or rounded to zero. |
| 9 | F | Too unreliable to be published. |

## Scalar Factor Codes

Scalar factor codes indicate the scale at which the data is presented.

| Code | Name | Description |
|------|------|-------------|
| 0 | Units | Data is presented in units. |
| 1 | Tens | Data is presented in tens (x10). |
| 2 | Hundreds | Data is presented in hundreds (x100). |
| 3 | Thousands | Data is presented in thousands (x1,000). |
| 4 | Tens of thousands | Data is presented in tens of thousands (x10,000). |
| 5 | Hundreds of thousands | Data is presented in hundreds of thousands (x100,000). |
| 6 | Millions | Data is presented in millions (x1,000,000). |
| 7 | Tens of millions | Data is presented in tens of millions (x10,000,000). |
| 8 | Hundreds of millions | Data is presented in hundreds of millions (x100,000,000). |
| 9 | Billions | Data is presented in billions (x1,000,000,000). |
| 10 | Trillions | Data is presented in trillions (x1,000,000,000,000). |
| -1 | Tenths | Data is presented in tenths (x0.1). |
| -2 | Hundredths | Data is presented in hundredths (x0.01). |
| -3 | Thousandths | Data is presented in thousandths (x0.001). |
| -4 | Ten-thousandths | Data is presented in ten-thousandths (x0.0001). |
| -5 | Hundred-thousandths | Data is presented in hundred-thousandths (x0.00001). |
| -6 | Millionths | Data is presented in millionths (x0.000001). |

## Frequency Codes

Frequency codes indicate how often data is collected or published.

| Code | Name | Description |
|------|------|-------------|
| 1 | Annual | Data is published annually. |
| 2 | Semi-annual | Data is published twice per year. |
| 3 | Quarterly | Data is published every three months. |
| 4 | Monthly | Data is published monthly. |
| 5 | Semi-monthly | Data is published twice per month. |
| 6 | Bi-weekly | Data is published every two weeks. |
| 7 | Weekly | Data is published weekly. |
| 8 | Daily | Data is published daily. |
| 9 | Occasional | Data is published on an irregular basis. |
| 10 | Biennial | Data is published every two years. |
| 11 | Quadrennial | Data is published every four years. |
| 12 | Quinquennial | Data is published every five years. |
| 13 | Decennial | Data is published every ten years. |

## Security Level Codes

Security level codes indicate the sensitivity and accessibility of the data.

| Code | Name | Description |
|------|------|-------------|
| 0 | Public | The data is publicly available. |
| 1 | Protected | The data is protected and has limited access. |
| 2 | Confidential | The data is confidential and has restricted access. |
| 3 | Secret | The data has highly restricted access. |
| 4 | Top Secret | The data has extremely restricted access. |

## Member UOM Codes

Member Unit of Measure (UOM) codes indicate the measurement unit used for the data.

| Code | Name | Description |
|------|------|-------------|
| 0 | Percent | Data is measured as a percentage. |
| 1 | Dollars | Data is measured in dollars. |
| 2 | Number | Data is measured as a count or number. |
| 3 | Kilograms | Data is measured in kilograms. |
| 4 | Litres | Data is measured in litres. |
| 5 | Metres | Data is measured in metres. |
| 6 | Square metres | Data is measured in square metres. |
| 7 | Cubic metres | Data is measured in cubic metres. |
| 8 | Hectares | Data is measured in hectares. |
| 9 | Hours | Data is measured in hours. |
| 10 | Index | Data is measured as an index. |
| 11 | Rate | Data is measured as a rate. |

## Subject Codes

Subject codes categorize data by topic area. The WDS includes numerous subject codes; below is a sample of common ones:

| Code | Name | Description |
|------|------|-------------|
| 10 | Population and demography | Data related to population statistics and demographics. |
| 20 | Health | Data related to health and healthcare. |
| 30 | Education | Data related to education and learning. |
| 40 | Labour | Data related to employment and the workforce. |
| 50 | Income | Data related to personal and household income. |
| 60 | Business | Data related to businesses and industries. |
| 70 | Economic accounts | Data related to national and regional economic accounts. |
| 80 | International trade | Data related to imports, exports, and trade balances. |
| 90 | Agriculture | Data related to farming and agricultural production. |
| 100 | Construction | Data related to construction activity. |
| 110 | Manufacturing | Data related to manufacturing activity. |
| 120 | Retail | Data related to retail trade. |
| 130 | Prices | Data related to consumer and producer prices. |

## Error Codes

Common error codes you may encounter when using the WDS API:

| HTTP Code | Description | Typical Cause |
|-----------|-------------|--------------|
| 400 | Bad Request | Missing or invalid parameters in the request. |
| 401 | Unauthorized | Authentication failed or is missing. |
| 403 | Forbidden | The requested operation is not allowed. |
| 404 | Not Found | The requested resource does not exist. |
| 409 | Conflict | The service is unavailable, typically during updates (12am-8:30am EST). |
| 429 | Too Many Requests | The rate limit has been exceeded. |
| 500 | Internal Server Error | An error occurred on the server. |
| 503 | Service Unavailable | The service is temporarily unavailable. |

## Important Identifiers

### Product ID (PID)

A 10-digit unique identifier for a cube (table). Examples:
- 1810000601: Consumer Price Index
- 3610040001: Gross Domestic Product (GDP)

### Vector ID

A unique identifier for a specific time series, typically starts with "v" followed by numbers. Examples:
- v74804: Consumer Price Index, All-items, Canada
- v65201210: GDP at basic prices, Construction

### Coordinates

Coordinates represent specific dimension values within a cube. They are specified as an array of strings, where each string represents a dimension member value. The order of the coordinates must match the order of dimensions in the cube.

Example: `["1.1.1", "1.1", "1"]` might represent:
- Dimension 1: Geography = Canada (1.1.1)
- Dimension 2: Product = All items (1.1)
- Dimension 3: Time = Latest period (1)