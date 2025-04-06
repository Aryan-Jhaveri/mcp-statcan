# Statistics Canada WDS Data Structures Reference

This document describes the data structures returned by the Statistics Canada Web Data Service (WDS) API.

## Common Response Structure

All API responses follow this general structure:

```json
{
  "status": "SUCCESS",
  "object": [
    // Response data specific to the API method
  ]
}
```

In case of an error:

```json
{
  "status": "FAILED",
  "object": "Error message describing what went wrong"
}
```

## Specific Data Structures

### Cube Metadata (`getCubeMetadata`)

```json
{
  "status": "SUCCESS",
  "object": {
    "productId": "1810000601",
    "cansimId": "18-10-0060",
    "cubeTitleEn": "Consumer Price Index (CPI), monthly, percentage change, not seasonally adjusted",
    "cubeTitleFr": "Indice des prix à la consommation (IPC), mensuel, variation en pourcentage, non désaisonnalisée",
    "cubeStartDate": "1986-01-01",
    "cubeEndDate": "2021-08-01",
    "releaseTime": "2021-09-15T08:30",
    "preChartTextEn": "Text that appears before chart",
    "preChartTextFr": "Texte qui apparaît avant le graphique",
    "dimension": [
      {
        "dimensionNameEn": "Geography",
        "dimensionNameFr": "Géographie",
        "member": [
          {
            "memberId": "1.1.1",
            "memberNameEn": "Canada",
            "memberNameFr": "Canada"
          },
          // Additional members...
        ]
      },
      // Additional dimensions...
    ],
    "footnote": [
      {
        "footnoteId": "1",
        "footnoteEn": "Footnote text in English",
        "footnoteFr": "Texte de la note de bas de page en français"
      },
      // Additional footnotes...
    ],
    "subject": [
      {
        "subjectCode": "2",
        "subjectEn": "Consumer price indexes",
        "subjectFr": "Indices des prix à la consommation"
      },
      // Additional subjects...
    ],
    "survey": [
      {
        "surveyCode": "2301",
        "surveyEn": "Consumer Price Index",
        "surveyFr": "Indice des prix à la consommation"
      },
      // Additional surveys...
    ],
    "frequency": "4",
    "frequencyDescEn": "Monthly",
    "frequencyDescFr": "Mensuelle",
    "archive": false,
    "correction": false,
    "cubeErrorCode": "0"
  }
}
```

### Series Information (`getSeriesInfoFromVector`)

```json
{
  "status": "SUCCESS",
  "object": [
    {
      "vectorId": "v74804",
      "productId": "1810000601",
      "coordinate": ["1.1.1", "1.1", "1"],
      "frequencyCode": "4",
      "securityLevel": "0",
      "SeriesTitleEn": "Consumer Price Index, All-items, Canada",
      "SeriesTitleFr": "Indice des prix à la consommation, Ensemble, Canada",
      "scalarFactorCode": "0",
      "UOM": "2",
      "UOMEn": "Percent",
      "UOMFr": "Pourcentage",
      "terminated": false,
      "decimals": 1,
      "SeriesDescEn": "Series description in English",
      "SeriesDescFr": "Description de la série en français",
      "memberUomCode": "2",
      "releaseTime": "2021-09-15T08:30",
      "startDate": "1986-01-01",
      "endDate": "2021-08-01"
    }
  ]
}
```

### Time Series Data (`getDataFromVectorsAndLatestNPeriods`)

```json
{
  "status": "SUCCESS",
  "object": [
    {
      "vectorId": "v74804",
      "coordinate": ["1.1.1", "1.1", "1"],
      "vectorDataPoint": [
        {
          "refPer": "2021-08-01",
          "refPer2": "August 2021",
          "value": "4.1",
          "decimals": 1,
          "scalarFactorCode": "0",
          "scalarFactorDescEn": "units",
          "scalarFactorDescFr": "unités",
          "symbol": "",
          "symbolCode": "0",
          "statusCode": "0",
          "securityLevelCode": "0",
          "releaseTime": "2021-09-15T08:30",
          "frequencyCode": "4"
        },
        // Additional data points...
      ],
      "responseStatusCode": "10",
      "productId": "1810000601",
      "SeriesTitleEn": "Consumer Price Index, All-items, Canada",
      "SeriesTitleFr": "Indice des prix à la consommation, Ensemble, Canada"
    },
    // Additional vectors...
  ]
}
```

### Changed Cube List (`getChangedCubeList`)

```json
{
  "status": "SUCCESS",
  "object": [
    {
      "productId": "1810000601",
      "cansimId": "18-10-0060",
      "cubeTitleEn": "Consumer Price Index (CPI), monthly, percentage change, not seasonally adjusted",
      "cubeTitleFr": "Indice des prix à la consommation (IPC), mensuel, variation en pourcentage, non désaisonnalisée",
      "cubeStartDate": "1986-01-01",
      "cubeEndDate": "2021-08-01",
      "releaseTime": "2021-09-15T08:30",
      "productTitle": "Consumer Price Index",
      "frequency": "4",
      "archive": false,
      "errorCode": "0"
    },
    // Additional cubes...
  ]
}
```

### Changed Series List (`getChangedSeriesList`)

```json
{
  "status": "SUCCESS",
  "object": [
    {
      "vectorId": "v74804",
      "productId": "1810000601",
      "coordinate": ["1.1.1", "1.1", "1"],
      "frequencyCode": "4",
      "securityLevel": "0",
      "SeriesTitleEn": "Consumer Price Index, All-items, Canada",
      "SeriesTitleFr": "Indice des prix à la consommation, Ensemble, Canada",
      "scalarFactorCode": "0",
      "UOM": "2",
      "terminated": false,
      "decimals": 1,
      "SeriesDescEn": "Series description in English",
      "SeriesDescFr": "Description de la série en français",
      "cubeErrorCode": "0",
      "releaseTime": "2021-09-15T08:30"
    },
    // Additional series...
  ]
}
```

### All Cubes List (`getAllCubesList`)

```json
{
  "status": "SUCCESS",
  "object": [
    {
      "productId": "1810000601",
      "cansimId": "18-10-0060",
      "cubeTitleEn": "Consumer Price Index (CPI), monthly, percentage change, not seasonally adjusted",
      "cubeTitleFr": "Indice des prix à la consommation (IPC), mensuel, variation en pourcentage, non désaisonnalisée",
      "cubeStartDate": "1986-01-01",
      "cubeEndDate": "2021-08-01",
      "releaseTime": "2021-09-15T08:30",
      "frequency": "4",
      "archive": false,
      "errorCode": "0",
      "productTitleEn": "Consumer Price Index",
      "productTitleFr": "Indice des prix à la consommation",
      "urlEn": "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810000601",
      "urlFr": "https://www150.statcan.gc.ca/t1/tbl1/fr/tv.action?pid=1810000601"
    },
    // Additional cubes...
  ]
}
```

### Code Sets (`getCodeSets`)

```json
{
  "status": "SUCCESS",
  "object": {
    "symbolCodes": [
      {
        "symbolCode": "0",
        "symbol": " ",
        "symbolDescEn": "No symbol",
        "symbolDescFr": "Aucun symbole"
      },
      // Additional symbol codes...
    ],
    "statusCodes": [
      {
        "statusCode": "0",
        "statusDescEn": "Normal",
        "statusDescFr": "Normale"
      },
      // Additional status codes...
    ],
    "securityLevelCodes": [
      {
        "securityLevelCode": "0",
        "securityLevelDescEn": "Public",
        "securityLevelDescFr": "Publique"
      },
      // Additional security level codes...
    ],
    "scalarFactorCodes": [
      {
        "scalarFactorCode": "0",
        "scalarFactorDescEn": "units",
        "scalarFactorDescFr": "unités"
      },
      // Additional scalar factor codes...
    ],
    "frequencyCodes": [
      {
        "frequencyCode": "1",
        "frequencyDescEn": "Annual",
        "frequencyDescFr": "Annuelle"
      },
      // Additional frequency codes...
    ],
    "memberUomCodes": [
      {
        "memberUomCode": "0",
        "memberUomDescEn": "Percent",
        "memberUomDescFr": "Pourcentage"
      },
      // Additional UOM codes...
    ],
    "subjectCodes": [
      {
        "subjectCode": "10",
        "subjectEn": "Population and demography",
        "subjectFr": "Population et démographie"
      },
      // Additional subject codes...
    ]
  }
}
```

## Full Table Downloads

### CSV Format (`getFullTableDownloadCSV`)

The response is a CSV file with the following format:

```csv
"REF_DATE","GEO","DGUID","Products and product groups","UOM","UOM_ID","SCALAR_FACTOR","SCALAR_ID","VECTOR","COORDINATE","VALUE","STATUS","SYMBOL","TERMINATED","DECIMALS"
"1986-01","Canada","","All-items","Percent","0","units","0","v74804","1.1.1.1.1","4.4","","","","1"
"1986-02","Canada","","All-items","Percent","0","units","0","v74804","1.1.1.1.1","4.1","","","","1"
...
```

### SDMX Format (`getFullTableDownloadSDMX`)

The response is an SDMX-ML file in XML format. SDMX (Statistical Data and Metadata Exchange) is an ISO standard for exchanging statistical data.

## Key Data Fields

### Common Fields

- **status**: Indicates whether the request was successful ("SUCCESS") or not ("FAILED").
- **object**: Contains the response data or error message.

### Cube Fields

- **productId**: 10-digit unique identifier for a cube (table).
- **cansimId**: Legacy identifier in the format "xx-xx-xxxx".
- **cubeTitleEn/Fr**: Title of the cube in English/French.
- **cubeStartDate/EndDate**: First and last dates for which data is available.
- **releaseTime**: When the data was last released, in ISO format with timezone.
- **frequency**: Code indicating how often the data is updated (see Frequency Codes).
- **archive**: Boolean indicating if the cube is archived.
- **correction**: Boolean indicating if the cube has been corrected.

### Series Fields

- **vectorId**: Unique identifier for a time series, typically starting with "v".
- **coordinate**: Array of dimension member values that uniquely identify the series.
- **SeriesTitleEn/Fr**: Title of the series in English/French.
- **frequencyCode**: Code indicating how often the data is updated.
- **scalarFactorCode**: Code indicating the scale of the values (e.g., thousands, millions).
- **UOM**: Unit of measure code.

### Data Point Fields

- **refPer**: Reference period for the data point, typically in YYYY-MM-DD format.
- **refPer2**: Human-readable reference period.
- **value**: The actual data value, as a string.
- **statusCode**: Code indicating the status of the data point.
- **symbolCode**: Code indicating any symbols associated with the data point.
- **decimals**: Number of decimal places in the value.