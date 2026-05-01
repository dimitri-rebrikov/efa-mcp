# Abstract

The project shall implement a MCP server for the EFA API.

EFA API is the transit information API provided by several public transportation companies in Germany.

# EFA API Documentation links

The EFA API documentation:
-  [Short API Presentation with Examples](https://mobidata-bw.de/daten/portal/efa-json/EFA_JSON_API_Training_EN_2.9.pdf)
 - [API description](https://www.mobidata-bw.de/data/Dokumentation-EFA_JSON_Schnittstelle_V2.pdf)
 - [Error Codes](https://www.mobidata-bw.de/data/EFA9_Errorcodes_V1.2.pdf)
 - [JSON Schema](https://mobidata-bw.de/daten/publikationen/JSON_Schema_10.6.21.17.zip)

# Implementation technology
The MCP Server shall be implemented using Pyntons FastMCP.
The start of the MCP Server shall be done using uvx for example:
```
{
  "mcpServers": {
    "my-github-tools": {
      "command": "uvx",
      "args": [
        "--from", "git+https://github.com/your-user/my-tools",
        "python", "main.py"
      ]
    }
  }
}
```

# MCP Server Functionalities

The MCP Server shall provide following functionalities:

# Set default url over environment variable
- the default default value is https://www.efa.de/efa/

# Set url of the EFA API provider during runtime
- Input: the url of the api provider which then is used for all operations

# List available EFA API provide with additional info
- Output: 
 the processed information about available EFA API provided  by https://github.com/public-transport/transport-apis 


## Find Stop
Input: 
- name of the stop 
Output: 
- name of the matching stop
- id of the matching stop
Remark: the stop with the flag isBest shall be taken

## Departure Monitor
Inputs:
- id of the stop 
- time of departure (optional). 
- amount of departures to show (optional)
Output:
- For each departure
 - planned departure time
 - estimated departure time
 - type of transport
 - number or designation of transport
 - direction
Remark: set flag userRealtime=1

## Trip Request
Inputs:
 - id of the origin stop
 - id of the destination stop
 - time (optional)
 - is the provided date/time for departure of arrival (optional)
Outputs:
- For every connection
 - For every transport
   - type of transport
   - number or designation of transport
   - direction
   - departure station 
   - planned departure time
   - estimated departure time
   - arrival station
   - planned arrival time
   - estimated arrival time




