# Pick Route Optimizer

This repository contains two related projects that work together to generate a distance matrix for a warehouse layout and to serve an API that can compute optimal picking routes.

## Projects

### `MAP_Generator`

- **Purpose**: Parses a textual representation of the warehouse (`Magazyn.txt`) and builds a graph of locations.
- **Key script**: `export.py`
  - Reads `Magazyn.txt`, identifies rows and columns of storage locations, and builds a bidirectional graph.
  - Performs a breadth‑first‑search from every node to compute the shortest‑path distance (in steps) to every other node.
  - Writes the result to `mapa_odleglosci.json` – a JSON object where each key is a location name and the value is a map of other locations with their distances.
- **How to run**:
  ```bash
  cd MAP_Generator
  python export.py
  ```
  The script produces `mapa_odleglosci.json` in the same directory.

### `WarehouseRouteApi`

- **Purpose**: Exposes an HTTP API (ASP.NET Core) that uses Google OR‑Tools to solve the Vehicle Routing Problem (VRP) for picking routes inside the warehouse.
- **Key parts**:
  - `Controllers/RouteController.cs` – defines the `/api/route` endpoint.
  - `Models/DTOs.cs` – data transfer objects for request/response payloads.
  - `RoutePlanner.cs` – contains the OR‑Tools logic that reads the distance matrix from `mapa_odleglosci.json` and computes an optimized route.
- **Configuration**:
  - The generated `mapa_odleglosci.json` should be placed in the same folder as the API binary (the project already copies it during build).
  - Adjust `appsettings.json` if you need to change the server URL or ports.
- **How to run**:
  ```bash
  cd WarehouseRouteApi/WarehouseRouteApi
  dotnet run
  ```
  The API will be available at `http://localhost:5000` (or the port defined in `launchSettings.json`).

## Typical workflow
1. **Generate the distance map**:
   ```bash
   cd MAP_Generator
   python export.py
   ```
   This creates `mapa_odleglosci.json`.
2. **Copy the map to the API project** (if not automatically copied):
   ```bash
   cp MAP_Generator/mapa_odleglosci.json WarehouseRouteApi/WarehouseRouteApi/
   ```
3. **Start the API**:
   ```bash
   cd WarehouseRouteApi/WarehouseRouteApi
   dotnet run
   ```
4. **Request a route** (example using `curl`):
   ```bash
   curl -X POST http://localhost:5000/api/route \
        -H "Content-Type: application/json" \
        -d '{"start":"A1","end":"B5","items":["C3","D2"]}'
   ```
   The response contains the optimal picking order.

## Repository layout
```
Pick_Route_Optimizer/
├─ MAP_Generator/          # Python script to build the distance matrix
│   ├─ export.py
│   ├─ Magazyn.txt          # Textual warehouse layout
│   └─ mapa_odleglosci.json (generated)
└─ WarehouseRouteApi/      # ASP.NET Core API using OR‑Tools
    └─ WarehouseRouteApi/   # Source code
        ├─ Controllers/
        ├─ Models/
        ├─ RoutePlanner.cs
        └─ appsettings.json
```

Feel free to adapt the scripts and API to match your specific warehouse configuration.
