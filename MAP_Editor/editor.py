"""Graphical editor for the warehouse map.

The map is a graph of named locations. You can:
  * click the gap between two neighbouring slots to connect or disconnect them (drag to paint a run);
  * drag from one slot onto another to link them even when they are not grid neighbours;
  * double-click empty space to add a slot, double-click a slot to rename it, Delete to remove it.

After every edit the tool re-checks connectivity: a slot you can no longer walk to from the
top-left turns red at once, instead of silently becoming an unreachable location in the
distance map.

    python editor.py [Magazyn.txt]
"""

import json
import math
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont, filedialog, messagebox, simpledialog, ttk

from warehouse_map import GridExportError, MapFormatError, WarehouseMap

# Default version; the release workflow overwrites this line with the git tag at build time,
# so a packaged build reports the release it came from.
__version__ = "1.1.0"

# A PyInstaller one-file build unpacks to a temp dir (sys._MEIPASS), so the sample map
# ships inside the bundle and the repo-relative paths only exist when running from source.
FROZEN = getattr(sys, "frozen", False)
if FROZEN:
    BUNDLE = Path(sys._MEIPASS)
    DEFAULT_MAP = BUNDLE / "Magazyn.txt"
    API_DIR = Path("__no_api_in_standalone_build__")
    DIALOG_DIR = Path.home()
else:
    HERE = Path(__file__).resolve().parent
    DEFAULT_MAP = HERE.parent / "MAP_Generator" / "Magazyn.txt"
    API_DIR = HERE.parent / "WarehouseRouteApi" / "WarehouseRouteApi"
    DIALOG_DIR = DEFAULT_MAP.parent if DEFAULT_MAP.exists() else Path.home()

MARGIN = 56
ZOOMS = [0.45, 0.6, 0.8, 1.0, 1.4]
DEFAULT_ZOOM = 2
BASE_CELL_W, BASE_CELL_H = 58, 46
BASE_FONT_PX = 13
TEXT_ZOOM_FLOOR = 0.6

MONO_CANDIDATES = ["Noto Sans Mono", "DejaVu Sans Mono", "Liberation Mono",
                   "Nimbus Mono PS", "Courier"]

BG = "#f4f5f7"
GRID_BG = "#ffffff"
CELL_FILL, CELL_LINE, CELL_TEXT = "#ffffff", "#c9ced6", "#2b2f36"
LINK, LINK_HOVER = "#5b6472", "#2563eb"
GAP_LINE = "#e6e9ed"
CUT_FILL, CUT_LINE = "#fde2e2", "#dc2626"
ODD_FILL, ODD_LINE = "#fdf0d5", "#c77700"
SELECT_LINE = "#2563eb"
RUBBER = "#2563eb"
HEADER_TEXT = "#8b929c"


class EditorApp:
    def __init__(self, root, path=None):
        self.root = root
        self.map = None
        self.path = None
        self.dirty = False
        self.zoom = DEFAULT_ZOOM
        self.cut = set()
        self.odd = {}
        self.undo = []
        self.selected = None
        self.pos_to_id = {}
        self.cell_items = {}
        self.edge_items = {}
        self.paint = None           # link-gap painting: True=connect, False=disconnect
        self.drag_from = None       # node id an edge-drag started on
        self.rubber = None
        self.hover_gap = None

        root.title("Warehouse Map Editor")
        root.geometry("1280x760")
        root.configure(bg=BG)
        self.mono = self._pick_mono()
        self._build_toolbar()
        self._build_canvas()
        self._build_status()
        self._bind_keys()

        if path:
            self.load(path)
        elif DEFAULT_MAP.exists():
            self.load(DEFAULT_MAP)
        else:
            self.set_status("Open a warehouse map, or double-click to start a new one.")

    # ------------------------------------------------------------------- chrome

    @staticmethod
    def _pick_mono():
        available = set(tkfont.families())
        for family in MONO_CANDIDATES:
            if family in available:
                return family
        return tkfont.nametofont("TkFixedFont").actual("family")

    def grid_font(self):
        return (self.mono, -max(7, round(BASE_FONT_PX * ZOOMS[self.zoom])))

    def _build_toolbar(self):
        bar = tk.Frame(self.root, bg=BG, padx=10, pady=8)
        bar.pack(fill="x")
        for label, command in [("Open", self.on_open), ("Save", self.on_save),
                               ("Save as", self.on_save_as)]:
            ttk.Button(bar, text=label, command=command, width=8).pack(side="left", padx=(0, 4))
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(bar, text="Undo", command=self.on_undo, width=8).pack(side="left", padx=(0, 4))
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(bar, text="Generate JSON", command=self.on_generate, width=14).pack(side="left")
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(bar, text="-", command=lambda: self.on_zoom(-1), width=3).pack(side="left")
        self.zoom_label = tk.Label(bar, text="", bg=BG, fg=HEADER_TEXT, width=6)
        self.zoom_label.pack(side="left")
        ttk.Button(bar, text="+", command=lambda: self.on_zoom(1), width=3).pack(side="left")

        legend = tk.Frame(bar, bg=BG)
        legend.pack(side="right")
        for colour, text in [(CUT_LINE, "cut off"), (ODD_LINE, "odd name")]:
            tk.Label(legend, text="  ", bg=colour).pack(side="left", padx=(10, 4))
            tk.Label(legend, text=text, bg=BG, fg=HEADER_TEXT).pack(side="left")

    def _build_canvas(self):
        wrap = tk.Frame(self.root, bg=BG)
        wrap.pack(fill="both", expand=True, padx=10)
        self.canvas = tk.Canvas(wrap, bg=GRID_BG, highlightthickness=1, highlightbackground="#dcdfe4")
        xbar = ttk.Scrollbar(wrap, orient="horizontal", command=self.canvas.xview)
        ybar = ttk.Scrollbar(wrap, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=xbar.set, yscrollcommand=ybar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        ybar.grid(row=0, column=1, sticky="ns")
        xbar.grid(row=1, column=0, sticky="ew")
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)

        self.canvas.bind("<Button-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Double-Button-1>", self.on_double)
        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<Leave>", lambda _e: self.set_hover(None))
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-2, "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(2, "units"))
        self.canvas.bind("<Shift-Button-4>", lambda e: self.canvas.xview_scroll(-4, "units"))
        self.canvas.bind("<Shift-Button-5>", lambda e: self.canvas.xview_scroll(4, "units"))

    def _build_status(self):
        bar = tk.Frame(self.root, bg=BG, padx=12, pady=7)
        bar.pack(fill="x")
        self.health = tk.Label(bar, text="", bg=BG, anchor="e", font=("TkDefaultFont", 10, "bold"))
        self.health.pack(side="right")
        self.status = tk.Label(bar, text="", bg=BG, fg="#4b515b", anchor="w")
        self.status.pack(side="left", fill="x", expand=True)

    def _bind_keys(self):
        self.root.bind("<Control-s>", lambda _e: self.on_save())
        self.root.bind("<Control-o>", lambda _e: self.on_open())
        self.root.bind("<Control-z>", lambda _e: self.on_undo())
        self.root.bind("<Delete>", lambda _e: self.delete_selected())
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------------------------------------------------------------- geometry

    @property
    def cell_w(self):
        return BASE_CELL_W * ZOOMS[self.zoom]

    @property
    def cell_h(self):
        return BASE_CELL_H * ZOOMS[self.zoom]

    def centre(self, x, y):
        return MARGIN + x * self.cell_w, MARGIN + y * self.cell_h

    def node_at(self, cx, cy):
        """The node whose box contains the point, or None."""
        if not self.map:
            return None
        bw, bh = self.cell_w * 0.5, self.cell_h * 0.42
        for node in self.map.nodes.values():
            px, py = self.centre(node.x, node.y)
            if abs(cx - px) <= bw and abs(cy - py) <= bh:
                return node.id
        return None

    def gap_at(self, cx, cy):
        """The neighbouring grid pair whose midpoint is nearest the cursor: (a_id, b_id)."""
        if not self.map or not self.pos_to_id:
            return None
        tol = min(self.cell_w, self.cell_h) * 0.45
        best, best_d = None, tol
        r = round((cy - MARGIN) / self.cell_h)
        c = math.floor((cx - MARGIN) / self.cell_w)
        if (c, r) in self.pos_to_id and (c + 1, r) in self.pos_to_id:
            mx, my = MARGIN + (c + 0.5) * self.cell_w, MARGIN + r * self.cell_h
            d = math.hypot(cx - mx, cy - my)
            if d < best_d:
                best, best_d = (self.pos_to_id[(c, r)], self.pos_to_id[(c + 1, r)]), d
        r = math.floor((cy - MARGIN) / self.cell_h)
        c = round((cx - MARGIN) / self.cell_w)
        if (c, r) in self.pos_to_id and (c, r + 1) in self.pos_to_id:
            mx, my = MARGIN + c * self.cell_w, MARGIN + (r + 0.5) * self.cell_h
            d = math.hypot(cx - mx, cy - my)
            if d < best_d:
                best, best_d = (self.pos_to_id[(c, r)], self.pos_to_id[(c, r + 1)]), d
        return best

    def snap_cell(self, cx, cy):
        """Nearest integer lattice cell to a canvas point."""
        return (round((cx - MARGIN) / self.cell_w), round((cy - MARGIN) / self.cell_h))

    # ----------------------------------------------------------------- drawing

    def redraw(self):
        self.canvas.delete("all")
        self.cell_items.clear()
        self.edge_items.clear()
        if not self.map:
            return
        zoom = ZOOMS[self.zoom]
        show_text = zoom >= TEXT_ZOOM_FLOOR
        font = self.grid_font()
        measured = tkfont.Font(family=font[0], size=font[1])
        box_w = min(self.cell_w * 0.82, measured.measure("W88") + 10 * zoom)
        box_h = min(self.cell_h * 0.62, measured.metrics("linespace") + 6 * zoom)

        self.pos_to_id = {(n.x, n.y): n.id for n in self.map.nodes.values()
                          if isinstance(n.x, int) and isinstance(n.y, int)}

        # Edges first, so the boxes sit on top of the link ends.
        for a, b in self.map.edges():
            self._draw_edge(a, b)
        # Grid-gap ghosts: faint hint of where a missing neighbour link could go.
        self._draw_gap_ghosts()

        for node in self.map.nodes.values():
            x, y = self.centre(node.x, node.y)
            rect = self.canvas.create_rectangle(x - box_w / 2, y - box_h / 2,
                                                x + box_w / 2, y + box_h / 2,
                                                fill=CELL_FILL, outline=CELL_LINE, width=1)
            text = self.canvas.create_text(x, y, text=node.name if show_text else "",
                                           fill=CELL_TEXT, font=font)
            self.cell_items[node.id] = (rect, text)
            self._paint_cell(node.id)

        xs = [n.x for n in self.map.nodes.values()]
        ys = [n.y for n in self.map.nodes.values()]
        x0, _ = self.centre(min(xs), min(ys))
        x1, y1 = self.centre(max(xs), max(ys))
        self.canvas.configure(scrollregion=(0, 0, x1 + MARGIN, y1 + MARGIN))
        self.zoom_label.configure(text=f"{int(zoom * 100)}%")

    def _draw_gap_ghosts(self):
        for (x, y), a in self.pos_to_id.items():
            for dx, dy in ((1, 0), (0, 1)):
                b = self.pos_to_id.get((x + dx, y + dy))
                if b is not None and not self.map.has_edge(a, b):
                    ax, ay = self.centre(x, y)
                    bx, by = self.centre(x + dx, y + dy)
                    mx, my = (ax + bx) / 2, (ay + by) / 2
                    if dx:
                        coords = (mx - self.cell_w * 0.08, my, mx + self.cell_w * 0.08, my)
                    else:
                        coords = (mx, my - self.cell_h * 0.08, mx, my + self.cell_h * 0.08)
                    item = self.canvas.create_line(*coords, fill=GAP_LINE,
                                                   width=max(1, 1.5 * ZOOMS[self.zoom]))
                    self.edge_items[frozenset((a, b))] = item

    def _draw_edge(self, a, b):
        na, nb = self.map.nodes[a], self.map.nodes[b]
        ax, ay = self.centre(na.x, na.y)
        bx, by = self.centre(nb.x, nb.y)
        item = self.canvas.create_line(ax, ay, bx, by, fill=LINK,
                                       width=max(2, 3 * ZOOMS[self.zoom]), capstyle="round")
        self.edge_items[frozenset((a, b))] = item

    def _repaint_pair(self, a, b):
        """Redraw just one pair's connector after a toggle — cheaper than a full redraw."""
        key = frozenset((a, b))
        old = self.edge_items.pop(key, None)
        if old is not None:
            self.canvas.delete(old)
        na, nb = self.map.nodes[a], self.map.nodes[b]
        if self.map.has_edge(a, b):
            self._draw_edge(a, b)
        elif isinstance(na.x, int) and isinstance(nb.x, int) and abs(na.x - nb.x) + abs(na.y - nb.y) == 1:
            # a grid-adjacent pair keeps a faint ghost where the link could go
            ax, ay = self.centre(na.x, na.y)
            bx, by = self.centre(nb.x, nb.y)
            mx, my = (ax + bx) / 2, (ay + by) / 2
            if na.y == nb.y:
                coords = (mx - self.cell_w * 0.08, my, mx + self.cell_w * 0.08, my)
            else:
                coords = (mx, my - self.cell_h * 0.08, mx, my + self.cell_h * 0.08)
            self.edge_items[key] = self.canvas.create_line(
                *coords, fill=GAP_LINE, width=max(1, 1.5 * ZOOMS[self.zoom]))
        # boxes must stay above any freshly drawn connector
        for nid in (a, b):
            if nid in self.cell_items:
                self.canvas.tag_raise(self.cell_items[nid][0])
                self.canvas.tag_raise(self.cell_items[nid][1])

    def _paint_cell(self, node_id):
        item = self.cell_items.get(node_id)
        if not item:
            return
        rect, _ = item
        if node_id in self.cut:
            self.canvas.itemconfigure(rect, fill=CUT_FILL, outline=CUT_LINE, width=2)
        elif node_id in self.odd:
            self.canvas.itemconfigure(rect, fill=ODD_FILL, outline=ODD_LINE, width=2)
        elif node_id == self.selected:
            self.canvas.itemconfigure(rect, fill=CELL_FILL, outline=SELECT_LINE, width=2)
        else:
            self.canvas.itemconfigure(rect, fill=CELL_FILL, outline=CELL_LINE, width=1)

    # -------------------------------------------------------------- validation

    def revalidate(self):
        if not self.map:
            return
        was_cut = self.cut
        self.cut = set(self.map.unreachable_from(self.map.top_left_id()))
        self.odd = {nid: (actual, expected) for nid, actual, expected in self.map.naming_anomalies()}
        for nid in was_cut | self.cut | set(self.odd):
            self._paint_cell(nid)
        self._report_health()

    def _report_health(self):
        parts = []
        if self.cut:
            names = ", ".join(self.map.nodes[n].name for n in sorted(self.cut)[:4])
            more = f" +{len(self.cut) - 4} more" if len(self.cut) > 4 else ""
            parts.append(("#dc2626", f"{len(self.cut)} cut off: {names}{more}"))
        if self.odd:
            first = sorted(self.odd)[0]
            actual, expected = self.odd[first]
            more = f" +{len(self.odd) - 1} more" if len(self.odd) > 1 else ""
            parts.append(("#c77700", f"{len(self.odd)} odd name: {actual} (expected {expected}){more}"))
        dupes = self.map.duplicate_names()
        if dupes:
            parts.insert(0, ("#dc2626", f"duplicate name: {dupes[0]}"))
        if parts:
            colour, text = parts[0]
            if len(parts) > 1:
                text += "   |   " + parts[1][1]
            self.health.configure(text=text, fg=colour)
        else:
            self.health.configure(text="all slots reachable", fg="#15803d")

    # ------------------------------------------------------------ interaction

    def set_hover(self, gap):
        if gap == self.hover_gap:
            return
        self.hover_gap = gap
        # Hover feedback is drawn cheaply as a transient highlight line.
        self.canvas.delete("hoverline")
        if gap:
            a, b = gap
            na, nb = self.map.nodes[a], self.map.nodes[b]
            ax, ay = self.centre(na.x, na.y)
            bx, by = self.centre(nb.x, nb.y)
            self.canvas.create_line(ax, ay, bx, by, fill=LINK_HOVER,
                                    width=max(2, 3 * ZOOMS[self.zoom]), dash=(3, 3),
                                    tags="hoverline")
            for nid in (a, b):
                self.canvas.tag_raise(self.cell_items[nid][0])
                self.canvas.tag_raise(self.cell_items[nid][1])

    def on_motion(self, event):
        if self.drag_from is not None:
            return
        cx, cy = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.set_hover(self.gap_at(cx, cy) if self.node_at(cx, cy) is None else None)

    def on_press(self, event):
        if not self.map:
            return
        cx, cy = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        gap = self.gap_at(cx, cy)
        node = self.node_at(cx, cy)
        if gap and node is None:
            a, b = gap
            self.paint = not self.map.has_edge(a, b)
            self.undo.append([])
            self._toggle_edge(a, b, self.paint)
        elif node is not None:
            self.drag_from = node
            self.select(node)

    def on_drag(self, event):
        cx, cy = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        if self.paint is not None:
            gap = self.gap_at(cx, cy)
            if gap:
                self._toggle_edge(gap[0], gap[1], self.paint)
            return
        if self.drag_from is not None:
            self.canvas.delete("rubber")
            ax, ay = self.centre(self.map.nodes[self.drag_from].x, self.map.nodes[self.drag_from].y)
            self.canvas.create_line(ax, ay, cx, cy, fill=RUBBER, width=2, dash=(4, 3), tags="rubber")

    def on_release(self, event):
        cx, cy = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        if self.paint is not None:
            self.paint = None
            if self.undo and not self.undo[-1]:
                self.undo.pop()
            return
        if self.drag_from is not None:
            self.canvas.delete("rubber")
            target = self.node_at(cx, cy)
            if target is not None and target != self.drag_from:
                self.undo.append([])
                self._toggle_edge(self.drag_from, target, not self.map.has_edge(self.drag_from, target))
                if not self.undo[-1]:
                    self.undo.pop()
            self.drag_from = None

    def on_double(self, event):
        if not self.map:
            self.new_map()
            return
        cx, cy = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        node = self.node_at(cx, cy)
        if node is not None:
            self.rename_node(node)
        else:
            self.add_node_at(cx, cy)

    # ------------------------------------------------------------- edit actions

    def _toggle_edge(self, a, b, linked):
        if self.map.has_edge(a, b) == linked:
            return
        if self.undo:
            self.undo[-1].append(("edge", a, b, not linked))
        self.map.set_edge(a, b, linked)
        self._repaint_pair(a, b)
        self.mark_dirty()
        self.revalidate()

    def select(self, node_id):
        previous, self.selected = self.selected, node_id
        if previous is not None:
            self._paint_cell(previous)
        if node_id is not None:
            self._paint_cell(node_id)
            self.set_status(f"Selected {self.map.nodes[node_id].name}. "
                            "Double-click to rename, Delete to remove, drag to another slot to link.")

    def rename_node(self, node_id):
        current = self.map.nodes[node_id].name
        new = simpledialog.askstring("Rename location", "New name:", initialvalue=current, parent=self.root)
        if not new or new == current:
            return
        try:
            self.undo.append([("rename", node_id, current)])
            self.map.rename_node(node_id, new)
        except ValueError as exc:
            self.undo.pop()
            messagebox.showerror("Cannot rename", str(exc))
            return
        _, text = self.cell_items[node_id]
        self.canvas.itemconfigure(text, text=new)
        self.mark_dirty()
        self.revalidate()

    def add_node_at(self, cx, cy):
        col, row = self.snap_cell(cx, cy)
        col, row = max(0, col), max(0, row)
        suggestion = ""
        # Offer the grid-conventional name if the row/column already agree on one.
        rows = [n.name for n in self.map.nodes.values() if n.y == row]
        cols = [n.name for n in self.map.nodes.values() if n.x == col]
        if rows and cols:
            suggestion = rows[0][:1] + cols[0][1:]
        name = simpledialog.askstring("Add location",
                                      f"Name for the new slot at column {col}, row {row}:",
                                      initialvalue=suggestion, parent=self.root)
        if not name:
            return
        if (col, row) in self.pos_to_id:
            messagebox.showerror("Occupied", f"There is already a slot at column {col}, row {row}.")
            return
        try:
            node = self.map.add_node(name, col, row)
        except ValueError as exc:
            messagebox.showerror("Cannot add", str(exc))
            return
        self.undo.append([("add", node.id)])
        self.mark_dirty()
        self.redraw()
        self.revalidate()
        self.select(node.id)

    def delete_selected(self):
        if self.selected is None:
            return
        node = self.map.nodes[self.selected]
        if not messagebox.askyesno("Delete location", f"Remove {node.name} and its links?"):
            return
        removed_edges = [(a, b) for a, b in self.map.edges() if self.selected in (a, b)]
        self.undo.append([("remove", node.name, node.x, node.y,
                           [self.map.nodes[b if a == self.selected else a].name
                            for a, b in removed_edges])])
        self.map.remove_node(self.selected)
        self.selected = None
        self.mark_dirty()
        self.redraw()
        self.revalidate()

    def on_undo(self):
        if not self.undo:
            self.set_status("Nothing to undo.")
            return
        for entry in reversed(self.undo.pop()):
            kind = entry[0]
            if kind == "edge":
                _, a, b, previous = entry
                self.map.set_edge(a, b, previous)
            elif kind == "rename":
                _, node_id, previous = entry
                self.map.rename_node(node_id, previous)
            elif kind == "add":
                self.map.remove_node(entry[1])
            elif kind == "remove":
                _, name, x, y, neighbour_names = entry
                node = self.map.add_node(name, x, y)
                for other in neighbour_names:
                    oid = self.map.id_for(other)
                    if oid is not None:
                        self.map.add_edge(node.id, oid)
        self.mark_dirty()
        self.redraw()
        self.revalidate()

    def on_zoom(self, step):
        target = max(0, min(len(ZOOMS) - 1, self.zoom + step))
        if target != self.zoom:
            self.zoom = target
            self.redraw()
            self.revalidate()

    # ------------------------------------------------------------------- files

    def new_map(self):
        if not self.confirm_discard():
            return
        self.map = WarehouseMap()
        self.path = None
        self.selected = None
        self.undo.clear()
        self.dirty = False
        self.redraw()
        self.revalidate()
        self.set_status("New empty map. Double-click to add the first slot.")

    def load(self, path):
        try:
            loaded = WarehouseMap.load(path)
        except (MapFormatError, OSError) as exc:
            messagebox.showerror("Cannot open map", str(exc))
            return
        self.map, self.path = loaded, Path(path)
        self.selected = None
        self.undo.clear()
        self.dirty = False
        self.redraw()
        self.revalidate()
        self.set_status(f"{self.path.parent.name}/{self.path.name}  —  {self.map.n_nodes} slots")
        self.root.title(f"Warehouse Map Editor — {self.path.name}")

    def on_open(self):
        if not self.confirm_discard():
            return
        path = filedialog.askopenfilename(
            title="Open warehouse map",
            initialdir=str(DIALOG_DIR),
            filetypes=[("Warehouse map", "*.txt"), ("All files", "*.*")])
        if path:
            self.load(path)

    def on_save(self):
        if not self.map:
            return
        if not self.map.is_grid():
            messagebox.showinfo(
                "Not a grid",
                "This map has slots that don't sit on the grid, so it can't be written as "
                f"Magazyn.txt for export.py.\n\n({self.map._grid_problem()})\n\n"
                "Use Generate JSON to build the distance map directly instead.")
            return
        if not self.path:
            return self.on_save_as()
        if self.cut and not messagebox.askyesno(
                "Save anyway?",
                f"{len(self.cut)} slot(s) can't be reached from the top-left. "
                "They will become unreachable locations. Save anyway?"):
            return
        try:
            self.map.save_grid(self.path)
        except (OSError, GridExportError) as exc:
            messagebox.showerror("Cannot save", str(exc))
            return
        self.dirty = False
        self.root.title(f"Warehouse Map Editor — {self.path.name}")
        self.set_status(f"Saved {self.path}")

    def on_save_as(self):
        if not self.map:
            return
        path = filedialog.asksaveasfilename(
            title="Save warehouse map", defaultextension=".txt",
            initialdir=str(self.path.parent if self.path else DIALOG_DIR),
            initialfile=self.path.name if self.path else "Magazyn.txt",
            filetypes=[("Warehouse map", "*.txt"), ("All files", "*.*")])
        if path:
            self.path = Path(path)
            self.on_save()

    def on_generate(self):
        if not self.map:
            return
        if self.cut and not messagebox.askyesno(
                "Generate anyway?",
                f"{len(self.cut)} slot(s) are cut off and will have no distances. Continue?"):
            return
        if self.map.duplicate_names():
            messagebox.showerror("Duplicate names",
                                 f"Fix duplicate names first: {', '.join(self.map.duplicate_names())}")
            return
        target = filedialog.asksaveasfilename(
            title="Generate distance map", defaultextension=".json",
            initialdir=str(DIALOG_DIR), initialfile="mapa_odleglosci.json",
            filetypes=[("Distance map", "*.json")])
        if not target:
            return
        self.set_status("Generating distance map — this takes a few seconds…")
        self.root.configure(cursor="watch")
        threading.Thread(target=self._generate_worker, args=(Path(target),), daemon=True).start()

    def _generate_worker(self, target):
        try:
            matrix = self.map.distance_matrix()
            with open(target, "w", encoding="utf-8") as fh:
                json.dump(matrix, fh, indent=2, ensure_ascii=False)
            size = target.stat().st_size / 1024 / 1024
            self.root.after(0, self._generate_done, target, len(matrix), size, None)
        except Exception as exc:
            self.root.after(0, self._generate_done, target, 0, 0, exc)

    def _generate_done(self, target, count, size, error):
        self.root.configure(cursor="")
        if error:
            messagebox.showerror("Generation failed", str(error))
            self.set_status("Generation failed.")
            return
        self.set_status(f"Wrote {count} locations to {target} ({size:.0f} MB)")
        api_copy = API_DIR / "mapa_odleglosci.json"
        if api_copy.exists() and target.resolve() != api_copy.resolve() and messagebox.askyesno(
                "Copy to the API?",
                f"Also overwrite the API's copy?\n\n{api_copy}\n\n"
                "The API reads that file at startup, so it needs the same map."):
            try:
                api_copy.write_bytes(target.read_bytes())
                self.set_status(f"Wrote {target} and updated {api_copy}")
            except OSError as exc:
                messagebox.showerror("Cannot copy", str(exc))

    # ------------------------------------------------------------------- misc

    def mark_dirty(self):
        if not self.dirty:
            self.dirty = True
            name = self.path.name if self.path else "untitled"
            self.root.title(f"Warehouse Map Editor — {name} *")

    def set_status(self, text):
        self.status.configure(text=text)

    def confirm_discard(self):
        if not self.dirty:
            return True
        return messagebox.askyesno("Discard changes?", "The map has unsaved changes. Discard them?")

    def on_close(self):
        if self.confirm_discard():
            self.root.destroy()


def selftest(outfile=None):
    """Headless check that a packaged build can find its data and load a map.

    Exercises the bundled sample map, the warehouse_map import and path resolution
    without opening a window, so the release workflow can smoke-test the executable on a
    runner with no display. A windowed (console=False) build has no stdout on Windows, so
    the result is also written to outfile when given — that is what CI actually reads."""
    if DEFAULT_MAP.exists():
        wmap = WarehouseMap.load(DEFAULT_MAP)
        msg = f"SELFTEST OK: loaded {DEFAULT_MAP.name}, {wmap.n_nodes} locations, grid={wmap.is_grid()}"
        code = 0
    else:
        msg = f"SELFTEST FAILED: bundled map not found at {DEFAULT_MAP}"
        code = 1
    print(msg)
    if outfile:
        Path(outfile).write_text(msg + "\n", encoding="utf-8")
    return code


def main():
    args = [a for a in sys.argv[1:] if a]
    if args and args[0] in ("--version", "-V"):
        print(f"MAP Editor {__version__}")
        return
    if args and args[0] in ("--selftest", "--check"):
        sys.exit(selftest(args[1] if len(args) > 1 else None))
    path = args[0] if args else None
    root = tk.Tk()
    try:
        ttk.Style().theme_use("clam")
    except tk.TclError:
        pass
    EditorApp(root, path)
    root.mainloop()


if __name__ == "__main__":
    main()
