"""Drives the graph model against the real Magazyn.txt and the JSON export.py produced.

The contracts that matter:
  * importing the grid gives the same graph, and re-exporting it reproduces the file;
  * the distance matrix equals (as data) what export.py writes and what it would write
    from a file the editor saved;
  * off-grid nodes, renames and new rows behave, and are correctly refused for grid export.

Run: python test_warehouse_map.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from warehouse_map import GridExportError, MapFormatError, WarehouseMap

GENERATOR = Path(__file__).resolve().parent.parent / "MAP_Generator"
MAP_TXT = GENERATOR / "Magazyn.txt"
MAP_JSON = GENERATOR / "mapa_odleglosci.json"

failures = []


def check(name, condition, detail=""):
    print(f"  {'PASS' if condition else 'FAIL'}  {name}" + ("" if condition or not detail else f"\n        {detail}"))
    if not condition:
        failures.append(name)


def graph_signature(wmap):
    """Names + name-keyed edges, independent of internal node ids."""
    names = {(n.y, n.x): n.name for n in wmap.nodes.values()}
    edges = frozenset(
        frozenset((wmap.nodes[a].name, wmap.nodes[b].name)) for a, b in wmap.edges()
    )
    return names, edges


print("Importing the real Magazyn.txt")
original_text = MAP_TXT.read_text(encoding="utf-8")
wmap = WarehouseMap.parse(original_text)

check("1640 locations", wmap.n_nodes == 1640, f"got {wmap.n_nodes}")
check("A04 present at top-left", wmap.id_for("A04") is not None)
check("origin is the top-left node", wmap.nodes[wmap.top_left_id()].name == "A04",
      f"got {wmap.nodes[wmap.top_left_id()].name}")
check("no duplicate names", wmap.duplicate_names() == [])
check("no trailing newline preserved", wmap.trailing_newline is False)

print("\nGrid round-trip: parse -> to_grid_text -> parse")
reparsed = WarehouseMap.parse(wmap.to_grid_text())
check("graph survives a grid save/load", graph_signature(reparsed) == graph_signature(wmap))
check("re-export is byte-identical to the import", reparsed.to_grid_text() == wmap.to_grid_text())

print("\nDistance matrix vs the committed mapa_odleglosci.json (takes a moment)")
expected = json.loads(MAP_JSON.read_text(encoding="utf-8"))
actual = wmap.distance_matrix()
check("same location set", set(actual) == set(expected), f"{len(actual)} vs {len(expected)}")
check("equal as data to export.py output", actual == expected,
      "the model disagrees with the generator about the graph")

print("\nWhat the editor saves is what export.py reads")
with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    (tmp / "Magazyn.txt").write_text(wmap.to_grid_text(), encoding="utf-8")
    (tmp / "export.py").write_bytes((GENERATOR / "export.py").read_bytes())
    run = subprocess.run([sys.executable, "export.py"], cwd=tmp, capture_output=True, text=True)
    check("export.py accepts the saved grid", run.returncode == 0, run.stderr.strip())
    if run.returncode == 0:
        regenerated = json.loads((tmp / "mapa_odleglosci.json").read_text(encoding="utf-8"))
        check("its JSON equals the committed one", regenerated == expected)

print("\nConnectivity")
check("the real map is one connected component", len(wmap.components()) == 1)
check("nothing is unreachable", wmap.unreachable_from(wmap.top_left_id()) == [])

cut = WarehouseMap.parse(original_text)
u85 = cut.id_for("U85A")  # the real bottom-right node (see naming anomaly below)
for nb in list(cut.neighbours(u85)):
    cut.remove_edge(u85, nb)
check("cutting a node loose makes it unreachable",
      cut.unreachable_from(cut.top_left_id()) == [u85])
check("the cut map has two components", len(cut.components()) == 2)

print("\nNaming anomalies (the typo class this tool exists to catch)")
anomalies = wmap.naming_anomalies()
check("finds the U85A typo and nothing else",
      anomalies == [(wmap.id_for("U85A"), "U85A", "U85")], f"got {anomalies}")
fixed = WarehouseMap.parse(original_text)
fixed.rename_node(fixed.id_for("U85A"), "U85")
check("renaming clears the anomaly", fixed.naming_anomalies() == [])
check("rename updates the name index", fixed.id_for("U85") is not None and fixed.id_for("U85A") is None)

print("\nEditing: add a row, add an off-grid cell")
edited = WarehouseMap.parse(original_text)
# A new aisle 'V' below U, linked down from row U.
for c in range(82):
    v = edited.add_node(f"V{c + 4:02d}", x=c, y=20)
    u = edited.id_for(f"U{c + 4:02d}") if c + 4 != 89 else None
check("adding a full row keeps it grid-exportable", edited.is_grid(), edited._grid_problem())
check("new row lifts the count to 1722", edited.n_nodes == 1722, f"got {edited.n_nodes}")

island = WarehouseMap.parse(original_text)
node = island.add_node("DOCK", x=0.0, y=-1.5)  # off the lattice, long name
island.add_edge(node.id, island.id_for("A04"))
check("an off-grid node is reachable through its edge",
      island.unreachable_from(island.top_left_id()) == [])
check("off-grid map cannot be a grid", not island.is_grid())
try:
    island.to_grid_text()
    check("grid export is refused for an off-grid map", False, "no error raised")
except GridExportError:
    check("grid export is refused for an off-grid map", True)
mtx = island.distance_matrix()
check("but JSON generation still works off-grid", "DOCK" in mtx and mtx["A04"]["DOCK"] == 1)

print("\nValidation guards")
dup = WarehouseMap.parse("A04-A05\n")
try:
    dup.add_node("A04", 5, 5)
    check("duplicate name is rejected", False)
except ValueError:
    check("duplicate name is rejected", True)
for label, text in [("no letters", "----\n----"), ("rows not alternating", "A04-A05\nB04-B05")]:
    try:
        WarehouseMap.parse(text)
        check(f"rejects malformed: {label}", False, "no error")
    except MapFormatError:
        check(f"rejects malformed: {label}", True)

print()
if failures:
    print(f"FAILED: {len(failures)} check(s): {', '.join(failures)}")
    sys.exit(1)
print("All checks passed.")
