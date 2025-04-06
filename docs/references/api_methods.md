# Statistics Canada WDS API Methods Reference

This document contains all the available API methods for the Statistics Canada Web Data Service (WDS), along with their parameters and descriptions.

## Base URL

```
https://www150.statcan.gc.ca/t1/wds/rest/
```

## Authentication

All requests require a `user_id` parameter, which can be set to "0" for anonymous access.

## Service Limits

- Maximum 50 requests per second total across all users
- Maximum 25 requests per second per IP address
- Data updates daily at 8:30am EST
- Service unavailable from 12am to 8:30am EST

## API Methods

### Product Change Listings

#### `getChangedSeriesList`

Get a list of series that have been updated within a specified time period.

**Endpoint:** `/getChangedSeriesList`  
**Method:** POST  
**Parameters:**
- `lastUpdatedDays` (Integer): Number of days to look back for updates

**Example Request:**
```json
{
  "user_id": "0",
  "lastUpdatedDays": 1
}
```

#### `getChangedCubeList`

Get a list of cubes (tables) that have been updated within a specified time period.

**Endpoint:** `/getChangedCubeList`  
**Method:** POST  
**Parameters:**
- `lastUpdatedDays` (Integer): Number of days to look back for updates

**Example Request:**
```json
{
  "user_id": "0",
  "lastUpdatedDays": 1
}
```

### Cube Metadata and Series Information

#### `getCubeMetadata`

Get metadata for a specific cube (table).

**Endpoint:** `/getCubeMetadata`  
**Method:** POST  
**Parameters:**
- `productId` (String): The 10-digit product ID (PID) for the cube

**Example Request:**
```json
{
  "user_id": "0",
  "productId": "1810000601"
}
```

#### `getSeriesInfoFromCubePidCoord`

Get information about a time series by specifying the cube and dimension coordinates.

**Endpoint:** `/getSeriesInfoFromCubePidCoord`  
**Method:** POST  
**Parameters:**
- `productId` (String): The 10-digit product ID (PID) for the cube
- `coordinate` (String Array): Array of dimension member values

**Example Request:**
```json
{
  "user_id": "0",
  "productId": "1810000601",
  "coordinate": ["1.1.1", "1.1", "1"]
}
```

#### `getSeriesInfoFromVector`

Get information about a time series by vector ID.

**Endpoint:** `/getSeriesInfoFromVector`  
**Method:** POST  
**Parameters:**
- `vectorId` (String): The vector ID of the time series

**Example Request:**
```json
{
  "user_id": "0",
  "vectorId": "v74804"
}
```

#### `getAllCubesList`

Get a list of all available cubes (tables).

**Endpoint:** `/getAllCubesList`  
**Method:** POST  
**Parameters:** None (beyond user_id)

**Example Request:**
```json
{
  "user_id": "0"
}
```

#### `getAllCubesListLite`

Get a lightweight list of all available cubes (tables) with minimal metadata.

**Endpoint:** `/getAllCubesListLite`  
**Method:** POST  
**Parameters:** None (beyond user_id)

**Example Request:**
```json
{
  "user_id": "0"
}
```

### Data Access Methods

#### `getChangedSeriesDataFromCubePidCoord`

Get data for a time series that has been updated, specifying cube and coordinates.

**Endpoint:** `/getChangedSeriesDataFromCubePidCoord`  
**Method:** POST  
**Parameters:**
- `productId` (String): The 10-digit product ID (PID) for the cube
- `coordinate` (String Array): Array of dimension member values
- `lastUpdatedDays` (Integer): Number of days to look back for updates

**Example Request:**
```json
{
  "user_id": "0",
  "productId": "1810000601",
  "coordinate": ["1.1.1", "1.1", "1"],
  "lastUpdatedDays": 30
}
```

#### `getChangedSeriesDataFromVector`

Get data for a time series that has been updated, specifying the vector ID.

**Endpoint:** `/getChangedSeriesDataFromVector`  
**Method:** POST  
**Parameters:**
- `vectorId` (String): The vector ID of the time series
- `lastUpdatedDays` (Integer): Number of days to look back for updates

**Example Request:**
```json
{
  "user_id": "0",
  "vectorId": "v74804",
  "lastUpdatedDays": 30
}
```

#### `getDataFromCubePidCoordAndLatestNPeriods`

Get the latest N periods of data for a time series by cube and coordinates.

**Endpoint:** `/getDataFromCubePidCoordAndLatestNPeriods`  
**Method:** POST  
**Parameters:**
- `productId` (String): The 10-digit product ID (PID) for the cube
- `coordinate` (String Array): Array of dimension member values
- `latestN` (Integer): Number of latest periods to retrieve

**Example Request:**
```json
{
  "user_id": "0",
  "productId": "1810000601",
  "coordinate": ["1.1.1", "1.1", "1"],
  "latestN": 10
}
```

#### `getDataFromVectorsAndLatestNPeriods`

Get the latest N periods of data for one or more vector IDs.

**Endpoint:** `/getDataFromVectorsAndLatestNPeriods`  
**Method:** POST  
**Parameters:**
- `vectors` (String Array): Array of vector IDs
- `latestN` (Integer): Number of latest periods to retrieve

**Example Request:**
```json
{
  "user_id": "0",
  "vectors": ["v74804", "v74805"],
  "latestN": 10
}
```

#### `getBulkVectorDataByRange`

Get data for multiple vectors over a specific reference period range.

**Endpoint:** `/getBulkVectorDataByRange`  
**Method:** POST  
**Parameters:**
- `vectorIds` (String Array): Array of vector IDs
- `startDataPointReferenceDate` (String): Start date in format "YYYY-MM-DD"
- `endDataPointReferenceDate` (String): End date in format "YYYY-MM-DD"

**Example Request:**
```json
{
  "user_id": "0",
  "vectorIds": ["v74804", "v74805"],
  "startDataPointReferenceDate": "2019-01-01",
  "endDataPointReferenceDate": "2019-12-31"
}
```

#### `getDataFromVectorByReferencePeriodRange`

Get data for a single vector over a specific reference period range.

**Endpoint:** `/getDataFromVectorByReferencePeriodRange`  
**Method:** POST  
**Parameters:**
- `vectorId` (String): The vector ID of the time series
- `startRefPeriod` (String): Start date in format "YYYY-MM-DD"
- `endRefPeriod` (String): End date in format "YYYY-MM-DD"

**Example Request:**
```json
{
  "user_id": "0",
  "vectorId": "v74804",
  "startRefPeriod": "2019-01-01",
  "endRefPeriod": "2019-12-31"
}
```

#### `getFullTableDownloadCSV`

Download an entire cube (table) in CSV format.

**Endpoint:** `/getFullTableDownloadCSV`  
**Method:** POST  
**Parameters:**
- `productId` (String): The 10-digit product ID (PID) for the cube
- `startDataPointReferenceDate` (String, optional): Start date in format "YYYY-MM-DD"
- `endDataPointReferenceDate` (String, optional): End date in format "YYYY-MM-DD"

**Example Request:**
```json
{
  "user_id": "0",
  "productId": "1810000601"
}
```

#### `getFullTableDownloadSDMX`

Download an entire cube (table) in SDMX format.

**Endpoint:** `/getFullTableDownloadSDMX`  
**Method:** POST  
**Parameters:**
- `productId` (String): The 10-digit product ID (PID) for the cube
- `startDataPointReferenceDate` (String, optional): Start date in format "YYYY-MM-DD"
- `endDataPointReferenceDate` (String, optional): End date in format "YYYY-MM-DD"

**Example Request:**
```json
{
  "user_id": "0",
  "productId": "1810000601"
}
```

### Supplemental Information

#### `getCodeSets`

Get all code sets used in the WDS.

**Endpoint:** `/getCodeSets`  
**Method:** POST  
**Parameters:** None (beyond user_id)

**Example Request:**
```json
{
  "user_id": "0"
}
```

## Response Format

All responses are JSON objects with the following structure:

```json
{
  "status": "SUCCESS",
  "object": [ ... ]
}
```

If an error occurs, the status will be "FAILED" and the object will contain error information:

```json
{
  "status": "FAILED",
  "object": "Error message"
}
```