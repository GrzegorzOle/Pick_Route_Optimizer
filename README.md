# Pick Route Optimizer

This repository contains three related projects that work together to build a distance matrix for a warehouse layout and serve an API that computes optimal picking routes.

![Warehouse layout](Img/magazyn.jpeg)

## Downloads

Ready-to-run, self-contained builds are on the **[Releases page](https://github.com/GrzegorzOle/Pick_Route_Optimizer/releases/latest)** — each has its runtime bundled inside, so there is nothing to install.

| Component | Windows | Linux |
|-----------|---------|-------|
| **Route API server** | [WarehouseRouteApi-windows-x64.zip](https://github.com/GrzegorzOle/Pick_Route_Optimizer/releases/latest/download/WarehouseRouteApi-windows-x64.zip) | [WarehouseRouteApi-linux-x64.zip](https://github.com/GrzegorzOle/Pick_Route_Optimizer/releases/latest/download/WarehouseRouteApi-linux-x64.zip) |
| **Map editor** | [MapEditor-windows.exe](https://github.com/GrzegorzOle/Pick_Route_Optimizer/releases/latest/download/MapEditor-windows.exe) | [MapEditor-linux](https://github.com/GrzegorzOle/Pick_Route_Optimizer/releases/latest/download/MapEditor-linux) |

The server zip contains the executable plus `mapa_odleglosci.json`; unzip and run the executable (see [`WarehouseRouteApi/readme.md`](WarehouseRouteApi/readme.md)). The map editor is a single file — run it directly (see [`MAP_Editor/README.md`](MAP_Editor/README.md)). These builds are produced automatically by [`.github/workflows/release.yml`](.github/workflows/release.yml) on every `v*` tag.

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

### `MAP_Editor`

- **Purpose**: A graphical editor for the warehouse map — a safer alternative to hand‑editing `Magazyn.txt`, where a single misplaced character silently disconnects a location and only surfaces later as an unreachable slot.
- **Key points**:
  - Models the map as a graph, so it can add locations anywhere (including off the regular grid), rename, delete, and connect any two slots.
  - Re‑checks reachability after every edit and highlights a cut‑off location in red at once.
  - Exports `Magazyn.txt` for `export.py`, or generates `mapa_odleglosci.json` directly.
- **How to run**:
  ```bash
  cd MAP_Editor
  python editor.py
  ```
  Needs only Python 3 with Tkinter (both in the standard library). See [`MAP_Editor/README.md`](MAP_Editor/README.md).

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
  The API will be available at `http://localhost:5139`, with Swagger UI at `/swagger` (see `launchSettings.json`).

See [`WarehouseRouteApi/readme.md`](WarehouseRouteApi/readme.md) for the full endpoint reference.

## Typical workflow
1. **Generate the distance map**:
   ```bash
   cd MAP_Generator
   python export.py
   ```
   This creates `mapa_odleglosci.json`. Alternatively, edit the map in `MAP_Editor` and generate the distance map from there.
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
   curl -X POST http://localhost:5139/api/route/optimal \
        -H "Content-Type: application/json" \
        -d '{"startLocation":"A05","stopLocation":"M05","locations":["B04","C07"]}'
   ```
   The response contains the optimal picking order:
   ```json
   {
     "startLocation": "A05",
     "stopLocation": "M05",
     "route": [
       { "location": "B04", "distance": 2 },
       { "location": "C07", "distance": 4 }
     ],
     "totalDistance": 20
   }
   ```
   Each `distance` is the leg walked to reach that location. `route` omits the start and stop,
   but `totalDistance` covers the whole walk — including the legs to the start and stop.

## Repository layout
```
Pick_Route_Optimizer/
├─ MAP_Generator/          # Python script to build the distance matrix
│   ├─ export.py
│   ├─ Magazyn.txt          # Textual warehouse layout
│   └─ mapa_odleglosci.json (generated)
├─ MAP_Editor/             # Graphical editor for the warehouse map
│   ├─ editor.py            # Tkinter UI
│   └─ warehouse_map.py     # graph model (parsing, validation, JSON export)
└─ WarehouseRouteApi/      # ASP.NET Core API using OR‑Tools
    └─ WarehouseRouteApi/   # Source code
        ├─ Controllers/
        ├─ Models/
        ├─ RoutePlanner.cs
        └─ appsettings.json
```

Feel free to adapt the scripts and API to match your specific warehouse configuration.
