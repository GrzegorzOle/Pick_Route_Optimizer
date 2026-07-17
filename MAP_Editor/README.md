# MAP Editor

A graphical editor for the warehouse map that `MAP_Generator` turns into the distance
matrix. Editing the ASCII `Magazyn.txt` by hand is error-prone: a single space where a `|`
belongs silently cuts a location off from the rest of the warehouse, and the mistake only
surfaces later as an unreachable slot in `mapa_odleglosci.json`.

This editor makes the connections clickable and re-checks reachability after every edit.

![The editor with a cut-off location highlighted in red](../Img/map_editor.png)

## Download (no Python needed)

Grab a ready-to-run build from the [Releases page](../../releases) — a single self-contained
file with Python and Tkinter bundled inside. Nothing to install.

- **Windows:** `MapEditor-windows.exe` — double-click to run.
- **Linux:** `MapEditor-linux` — `chmod +x MapEditor-linux` then `./MapEditor-linux`.

Each build ships with a sample warehouse map, so it opens ready to edit; use **Open** to load
your own `Magazyn.txt`.

## Running it from source

```bash
cd MAP_Editor
python editor.py            # opens ../MAP_Generator/Magazyn.txt by default
python editor.py other.txt  # or a specific file
```

Needs only Python 3 with Tkinter (both in the standard library) — nothing to install.

## The model: a graph, not a fixed grid

Internally the map is a **graph** — each location is a node with a name and a position, each
walkable connection is an edge. A regular warehouse is just the special case where every node
sits on an integer lattice. This is what lets the editor do things the ASCII format cannot:

- **Add a slot anywhere** — including off the regular grid (an island, a skew dock), which
  `Magazyn.txt` has no way to represent.
- **Rename** a slot, **delete** one, **add a whole new aisle**.
- **Link any two slots**, not only grid neighbours.

## What you can do

- **Click** the gap between two neighbouring slots to connect/disconnect them; **drag** to
  paint a run of gaps in one stroke.
- **Drag from one slot onto another** to link them even when they aren't grid neighbours.
- **Double-click empty space** to add a slot (it suggests the grid-conventional name);
  **double-click a slot** to rename it; select one and press **Delete** to remove it.
- A slot you can no longer reach from the top-left turns **red** immediately, with a count in
  the status bar — the mistake this tool exists to catch.
- A slot whose name breaks the convention its row and column agree on turns **amber** (this
  is how it flags the `U85A` typo described below).
- **Ctrl+Z** undoes, **Ctrl+S** saves, `+`/`-` zoom.
- **Generate JSON** builds `mapa_odleglosci.json` directly and offers to copy it into the API
  project — no separate `export.py` run or manual copy.

## Saving: grid vs JSON

- If the map is still a clean grid, **Save** writes `Magazyn.txt` exactly as `export.py`
  expects, so the existing pipeline keeps working unchanged.
- If the map has off-grid slots (or names too long for the fixed-width columns), it can't be
  written as `Magazyn.txt`. Save says so and points you to **Generate JSON**, which produces
  the distance map directly from the graph.

## Known data issue it surfaces

The committed map ends in `U85A` instead of `U85` — a stray keystroke that `export.py`
faithfully turned into a location of that name. So the warehouse has a `U85A` and no `U85`
at all, and asking the API for `U85` returns "outside the warehouse". Open the map and the
bottom-right slot is flagged amber; double-click it, rename to `U85`, then Save (or Generate
JSON) to fix both the text file and the distance matrix.

## Packaging a release

Builds are produced by [`.github/workflows/release.yml`](../.github/workflows/release.yml).
Push a version tag and it builds the Windows and Linux executables on their own runners
(PyInstaller can't cross-compile), smoke-tests each, and publishes a GitHub Release:

```bash
git tag v1.0.0
git push origin v1.0.0
```

You can also run the workflow manually from the Actions tab to build and test without
releasing. To build locally on your own machine:

```bash
cd MAP_Editor
pip install pyinstaller
pyinstaller --clean --noconfirm editor.spec   # produces dist/MapEditor(.exe)
./dist/MapEditor --selftest                    # headless check: loads the bundled map
```

## Files

- `warehouse_map.py` — the graph model: parsing, editing, connectivity, grid export and JSON
  generation. No GUI; this is what the tests drive.
- `editor.py` — the Tkinter interface. `--selftest` loads the bundled map and exits (used to
  smoke-test packaged builds without a display).
- `editor.spec` — PyInstaller recipe for the one-file, self-contained executable.
- `test_warehouse_map.py` — checks the model against the real `Magazyn.txt`: that the grid
  round-trips, that the distance matrix **equals** what `export.py` writes (and what it would
  write from a file the editor saved), and that off-grid edits, renames and new rows behave.
  Run with `python test_warehouse_map.py`.
