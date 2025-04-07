# StatCan WDS API Connection Guide

This guide provides step-by-step instructions for connecting to the Statistics Canada Web Data Service (WDS) API and retrieving data.

## Understanding the 406 Errors

The 406 errors occur when the JSON format doesn't match exactly what the API expects. Based on our testing, here are the key findings:

1. API accepts array format for POST requests: `[{"key": "value"}]` not `{"key": "value"}`
2. Vector IDs should be numeric without the 'v' prefix (e.g., use `41690973` not `"v41690973"`)
3. Some endpoints may have unique requirements that differ from the documentation

## Step-by-Step API Testing

### Step 1: Test Basic API Connection

Use a simple GET request to test connectivity:

```python
async with aiohttp.ClientSession() as session:
    url = "https://www150.statcan.gc.ca/t1/wds/rest/getAllCubesList"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    async with session.get(url, headers=headers) as response:
        # Check if response.status == 200
```

### Step 2: Get List of Changed Cubes

Retrieve a list of cubes that have been updated recently:

```python
async with aiohttp.ClientSession() as session:
    date = "2025-04-01"  # Use appropriate date
    url = f"https://www150.statcan.gc.ca/t1/wds/rest/getChangedCubeList/{date}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    async with session.get(url, headers=headers) as response:
        data = await response.json()
        # Process response data
```

### Step 3: Get Cube Metadata

Retrieve metadata for a specific cube:

```python
async with aiohttp.ClientSession() as session:
    url = "https://www150.statcan.gc.ca/t1/wds/rest/getCubeMetadata"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = [{"productId": 18100004}]  # Note the array format
    async with session.post(url, json=payload, headers=headers) as response:
        data = await response.json()
        # Process response data
```

### Step 4: Get Vector Data

Retrieve data for a specific vector:

```python
async with aiohttp.ClientSession() as session:
    url = "https://www150.statcan.gc.ca/t1/wds/rest/getDataFromVectorsAndLatestNPeriods"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = [{"vectorId": 41690973, "latestN": 5}]  # Note: numeric ID without 'v' prefix
    async with session.post(url, json=payload, headers=headers) as response:
        data = await response.json()
        # Process response data
```

### Step 5: Get Vector Information

Retrieve metadata for a specific vector:

```python
async with aiohttp.ClientSession() as session:
    url = "https://www150.statcan.gc.ca/t1/wds/rest/getSeriesInfoFromVector"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = [{"vectorId": 41690973}]  # Note: numeric ID without 'v' prefix
    async with session.post(url, json=payload, headers=headers) as response:
        data = await response.json()
        # Process response data
```

## Common Issues and Solutions

1. **406 Not Acceptable Errors**:
   - Make sure POST requests use array format: `[{"key": "value"}]`
   - For vector IDs, use numeric format without 'v' prefix
   - Ensure proper Content-Type and Accept headers

2. **Timeout Issues**:
   - The API may occasionally time out for large requests
   - Implement retry logic with exponential backoff

3. **Unexpected Response Formats**:
   - Handle both array and object responses
   - Check for the response status before processing data

## Working Formats for Key Endpoints

| Endpoint | Method | Working Format | Notes |
|----------|--------|---------------|-------|
| getAllCubesList | GET | No payload | Returns all available cubes |
| getChangedCubeList | GET | Date in URL path | Use format: `/getChangedCubeList/YYYY-MM-DD` |
| getCubeMetadata | POST | `[{"productId": 18100004}]` | Works with both string and numeric IDs |
| getDataFromVectorsAndLatestNPeriods | POST | `[{"vectorId": 41690973, "latestN": 5}]` | Use numeric ID without 'v' prefix |
| getSeriesInfoFromVector | POST | `[{"vectorId": 41690973}]` | Use numeric ID without 'v' prefix |

## Example: Retrieving CPI Data

This example shows how to retrieve the latest Consumer Price Index data:

```python
import asyncio
import aiohttp
import json

async def get_cpi_data():
    async with aiohttp.ClientSession() as session:
        url = "https://www150.statcan.gc.ca/t1/wds/rest/getDataFromVectorsAndLatestNPeriods"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        payload = [{"vectorId": 41690973, "latestN": 5}]  # CPI All-items
        
        async with session.post(url, json=payload, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                if isinstance(data, list) and len(data) > 0:
                    vector_data = data[0].get("object", {})
                    data_points = vector_data.get("vectorDataPoint", [])
                    
                    print(f"CPI All-items (recent values):")
                    for point in data_points:
                        period = point.get("refPer", "Unknown")
                        value = point.get("value", "N/A")
                        print(f"  {period}: {value}")
                else:
                    print("Unexpected response format")
            else:
                print(f"Request failed with status: {response.status}")

if __name__ == "__main__":
    asyncio.run(get_cpi_data())
```