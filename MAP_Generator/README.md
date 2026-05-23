# MAP Generator

A Python utility that parses a text-based warehouse map, builds a bidirectional graph of storage locations, computes all-pairs shortest distances using Breadth-First Search (BFS), and exports the result as a JSON distance map — intended for use by a pick-route optimizer.

---

## Table of Contents

- [Overview](#overview)
- [Project Structure](#project-structure)
- [How It Works](#how-it-works)
  - [1. Reading the Warehouse Map](#1-reading-the-warehouse-map)
  - [2. Identifying Locations](#2-identifying-locations)
  - [3. Building the Graph](#3-building-the-graph)
  - [4. Computing Distances (BFS)](#4-computing-distances-bfs)
  - [5. Exporting to JSON](#5-exporting-to-json)
- [Input Format — `Magazyn.txt`](#input-format--magazyntxt)
- [Output Format — `mapa_odleglosci.json`](#output-format--mapa_odleglosci-json)
- [Running the Script](#running-the-script)
- [Building a Standalone Executable](#building-a-standalone-executable)
- [Dependencies](#dependencies)

---

## Overview

The **MAP Generator** is the first step in a warehouse pick-route optimization pipeline. It takes a plain-text representation of a warehouse floor (`Magazyn.txt`) and converts it into a machine-readable distance matrix (`mapa_odleglosci.json`). The distance matrix stores the minimum hop-count (number of steps) between every pair of named storage locations, which can then be consumed by a route planner.

---

## Project Structure

```
MAP_Generator/
├── export.py               # Main script
├── export.spec             # PyInstaller build specification
├── Magazyn.txt             # Warehouse map (input)
├── mapa_odleglosci.json    # Generated distance map (output)
└── build/                  # PyInstaller build artefacts
```

---

## How It Works

### 1. Reading the Warehouse Map

`export.py` opens `Magazyn.txt` (UTF-8 encoded) and reads it line by line, stripping trailing newline characters. The file represents the physical layout of warehouse aisles and storage locations using ASCII art.

```python
with open('Magazyn.txt', encoding='utf-8') as f:
    lines = [l.rstrip('\n') for l in f]
```

---

### 2. Identifying Locations

The script scans the file to find:

- **Location rows** — lines that contain at least one alphabetic character. Each such line holds a sequence of named storage slots.
- **Column positions** — within the first location row, every slot that starts with a letter is recorded. Slots are exactly 4 characters wide (e.g. `A04-`, `B05-`), so the script advances by 4 characters after each found slot.

Each location is given a **name** consisting of a letter (aisle/row) and a two-digit number (column), e.g. `A04`, `B17`, `T85`.

The warehouse in `Magazyn.txt` spans:
- **Rows**: `A` through `U` (20 rows of storage locations)
- **Columns**: `04` through `85` (82 columns per row)

Total locations: **~1 640 named slots**.

---

### 3. Building the Graph

A **bidirectional, unweighted graph** is constructed. For each location the script checks four possible neighbours:

| Direction | Condition |
|-----------|-----------|
| **Right** | The character immediately after the 3-character name (at offset `+3`) is `-` |
| **Left**  | The character immediately before the name (at offset `-1`) is `-` |
| **Down**  | Two lines below in the same column exists a location, and the intermediate line contains `\|` at that column |
| **Up**    | Two lines above in the same column exists a location, and the intermediate line contains `\|` at that column |

Both directions of every found connection are added, and duplicate edges are removed by converting each adjacency list to a sorted set.

```
A04 - A05 - A06 - ... - A85   ← connected by '-' characters
 |     |     |
B04 - B05 - B06 - ...         ← connected by '|' characters
```

Not all vertical connections exist — some rows have gaps in the `|` separator line, meaning those pairs of locations are **not** directly connected (e.g. between rows B and C some columns are missing vertical links).

---

### 4. Computing Distances (BFS)

For every location in the graph, a standard **Breadth-First Search (BFS)** is run to find the shortest path (in hops) to every other reachable location:

```python
def bfs(start, graph):
    distances = {}
    visited = set()
    queue = deque([(start, 0)])
    while queue:
        curr, dist = queue.popleft()
        if curr in visited:
            continue
        visited.add(curr)
        if curr != start:
            distances[curr] = dist
        for nei in graph[curr]:
            if nei not in visited:
                queue.append((nei, dist + 1))
    return distances
```

Each edge has uniform weight **1**, so BFS guarantees the optimal (minimum hop) distance. The self-distance is omitted from each result entry.

The all-pairs BFS produces a complete `N × N` distance matrix (where `N` is the total number of locations).

---

### 5. Exporting to JSON

The resulting distance matrix is written to `mapa_odleglosci.json`:

```python
with open('mapa_odleglosci.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)
```

---

## Input Format — `Magazyn.txt`

The warehouse map is a plain-text ASCII art file. The layout rules are:

- **Location rows** contain named slots separated by `-` characters.  
  Each slot occupies exactly **4 characters**: 3 for the name + 1 separator.  
  Example: `A04-A05-A06-A07-...`

- **Connector rows** (between two location rows) contain `|` characters at the column positions of locations that are connected vertically.  
  Example: `|   |   |   |` means every third location has a vertical link, while gaps indicate no connection.

- Location names follow the pattern `<Letter><TwoDigitNumber>`, e.g. `A04`, `M42`, `U85`.

### Excerpt

```
A04-A05-A06-A07-A08-...
|   |   |   |   |   ...
B04-B05-B06-B07-B08-...
|                   ...      ← sparse vertical connections
C04-C05-C06-C07-C08-...
```

---

## Output Format — `mapa_odleglosci.json`

The output is a JSON object where:

- **Keys** are location names (strings), e.g. `"A04"`.
- **Values** are objects mapping every other reachable location to its BFS hop-distance (integer).

### Example (abbreviated)

```json
{
  "A04": {
    "A05": 1,
    "A06": 2,
    "B04": 1,
    "B05": 2,
    ...
  },
  "A05": {
    "A04": 1,
    "A06": 1,
    ...
  },
  ...
}
```

This file is the direct input consumed by the pick-route optimizer to plan the shortest traversal order for a list of picking locations.

---

## Running the Script

Ensure Python 3 is installed, then run:

```bash
python export.py
```

Both `export.py` and `Magazyn.txt` must be in the **same working directory**. The output file `mapa_odleglosci.json` will be created (or overwritten) in the same directory.

---

## Building a Standalone Executable

The project includes a [PyInstaller](https://pyinstaller.org/) specification file (`export.spec`) to package the script as a self-contained executable (no Python installation required on the target machine).

### Build command

```bash
pyinstaller export.spec
```

The compiled executable will be placed in the `build/export/` directory. Copy it alongside `Magazyn.txt` and run:

```bash
./export        # Linux / macOS
export.exe      # Windows
```

### PyInstaller build settings (from `export.spec`)

| Setting | Value |
|---------|-------|
| Entry point | `export.py` |
| Console mode | `True` (no GUI window) |
| UPX compression | Enabled |
| Debug mode | Disabled |

---

## Dependencies

| Dependency | Source | Notes |
|------------|--------|-------|
| `json` | Python standard library | Serialising the distance map |
| `collections.deque` | Python standard library | Efficient BFS queue |
| `PyInstaller` | Third-party (`pip install pyinstaller`) | Only required to build the executable |

No external packages are required to run `export.py` directly.

