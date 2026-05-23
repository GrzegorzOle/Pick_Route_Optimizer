# Warehouse Route API

Warehouse Route API is an ASP.NET Core Web API that calculates an optimized picking path between warehouse locations using a distance matrix and Google OR-Tools.

## Overview

The service exposes endpoints to:

- compute an optimized route with explicit start and stop points,
- list all known warehouse locations,
- return distance between two selected locations.

Key defaults:

- default `startLocation`: `A05`
- default `stopLocation`: `M05`
- distance matrix file: `WarehouseRouteApi/mapa_odleglosci.json`

## Technology

- .NET 8 (`net8.0`)
- ASP.NET Core Web API
- Google OR-Tools (`Google.OrTools`)
- Swagger / OpenAPI (`Swashbuckle.AspNetCore`)

## Repository Layout

- `WarehouseRouteApi.sln` - solution
- `WarehouseRouteApi/WarehouseRouteApi.csproj` - project file and package references
- `WarehouseRouteApi/Program.cs` - dependency registration and middleware pipeline
- `WarehouseRouteApi/Controllers/RouteController.cs` - REST endpoints
- `WarehouseRouteApi/RoutePlanner.cs` - optimization logic
- `WarehouseRouteApi/WarehouseGraph.cs` - JSON distance matrix loader
- `WarehouseRouteApi/. Models/DTOs.cs` - request/response models
- `WarehouseRouteApi/mapa_odleglosci.json` - matrix data

## Requirements

- .NET SDK 8 or newer

## Build and Run

Run from the repository root:

```bash
dotnet restore "WarehouseRouteApi.sln"
dotnet build "WarehouseRouteApi.sln"
dotnet run --project "WarehouseRouteApi/WarehouseRouteApi.csproj"
```

Based on `WarehouseRouteApi/Properties/launchSettings.json`, the HTTP profile uses:

- `http://localhost:5139`
- Swagger UI: `http://localhost:5139/swagger`

## API

Base path: `api/route`

### POST `api/route/optimal`

Calculates an optimized route that starts at `startLocation` and ends at `stopLocation`.

Request example:

```json
{
  "startLocation": "A05",
  "stopLocation": "M05",
  "locations": ["B04", "C07", "D10"],
  "searchMetaheuristic": 3
}
```

Rules:

- `startLocation` is optional (default: `A05`)
- `stopLocation` is optional (default: `M05`)
- `locations` must be present (`null` is rejected)
- every location must exist in the matrix
- response omits start and stop in the `route` list

Response example:

```json
{
  "startLocation": "A05",
  "route": [
    { "location": "B04", "distance": 2 },
    { "location": "C07", "distance": 3 },
    { "location": "D10", "distance": 4 }
  ],
  "totalDistance": 9
}
```

Known error messages:

- `400 Bad Request`: `"Provide at least one intermediate location."`
- `400 Bad Request`: `"Locations outside the warehouse."`

### GET `api/route/locations`

Returns all available location codes sorted alphabetically.

### GET `api/route/distance/{from}/{to}`

Returns distance as an integer. If the edge is missing, the endpoint returns `404` with `9999`.

## Optimization Notes

- Distances are stored as `Dictionary<string, Dictionary<string, int>>`.
- Missing edges are treated as cost `9999`.
- `searchMetaheuristic` currently maps to OR-Tools `FirstSolutionStrategy` values in range `0..17`.
- Fallback strategy is `3` (`PathCheapestArc`) when input is outside the supported range.

## Quick API Test

```bash
curl -X POST "http://localhost:5139/api/route/optimal" \
  -H "Content-Type: application/json" \
  -d '{
    "startLocation": "A05",
    "stopLocation": "M05",
    "locations": ["B04", "C07", "D10"],
    "searchMetaheuristic": 3
  }'
```

## Suggested Next Improvements

- add validation attributes and standardized error payloads,
- add unit and integration tests,
- clean up nullable warnings,
- optionally rename `mapa_odleglosci.json` to an English filename.

