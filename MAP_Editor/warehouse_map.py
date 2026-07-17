"""The warehouse as a graph of named locations.

A location is a node with a unique ``name`` and a display position ``(x, y)``; a walkable
connection is an undirected edge. This is a superset of the old ASCII grid: a grid map is
just one where every node sits on an integer lattice, so we can still import and (when the
map stays a clean grid) export ``Magazyn.txt`` for ``export.py``. Nodes off that lattice —
an island, a skew position — have nowhere to go in the ASCII format, so those maps are
saved as JSON directly instead.

The contract that matters: for a grid map, :meth:`distance_matrix` returns a structure
equal (as data, not necessarily byte-for-byte) to what ``export.py`` writes, because the
API deserialises the JSON into an order-insensitive dictionary.

No GUI code lives here; the editor renders it and the tests drive it directly.
"""

from collections import Counter, deque

NAME_WIDTH = 3   # export.py reads names as row[ci:ci+3]
CELL_WIDTH = 4   # ...and steps 4 characters per column


class MapFormatError(ValueError):
    """The text does not match the grid layout export.py can read."""


class GridExportError(ValueError):
    """The map cannot be written as an export.py-readable grid (off-lattice nodes, long names…)."""


class Node:
    __slots__ = ("id", "name", "x", "y")

    def __init__(self, id, name, x, y):
        self.id = id
        self.name = name
        self.x = x
        self.y = y

    def __repr__(self):
        return f"Node({self.id}, {self.name!r}, {self.x}, {self.y})"


class WarehouseMap:
    def __init__(self):
        self.nodes = {}          # id -> Node
        self._edges = set()      # frozenset({id, id})
        self._by_name = {}       # name -> id
        self._next_id = 0
        self.trailing_newline = False

    # -------------------------------------------------------------- construction

    def add_node(self, name, x, y):
        if name in self._by_name:
            raise ValueError(f"Duplicate location name: {name!r}")
        node = Node(self._next_id, name, x, y)
        self.nodes[node.id] = node
        self._by_name[name] = node.id
        self._next_id += 1
        return node

    def remove_node(self, node_id):
        node = self.nodes.pop(node_id)
        del self._by_name[node.name]
        self._edges = {e for e in self._edges if node_id not in e}

    def rename_node(self, node_id, name):
        node = self.nodes[node_id]
        if name == node.name:
            return
        if name in self._by_name:
            raise ValueError(f"Duplicate location name: {name!r}")
        del self._by_name[node.name]
        node.name = name
        self._by_name[name] = node_id

    def move_node(self, node_id, x, y):
        node = self.nodes[node_id]
        node.x, node.y = x, y

    def id_for(self, name):
        return self._by_name.get(name)

    # --------------------------------------------------------------------- edges

    def _key(self, a, b):
        if a == b:
            raise ValueError("A location cannot link to itself.")
        if a not in self.nodes or b not in self.nodes:
            raise KeyError("Both endpoints must exist.")
        return frozenset((a, b))

    def has_edge(self, a, b):
        return a != b and frozenset((a, b)) in self._edges

    def add_edge(self, a, b):
        self._edges.add(self._key(a, b))

    def remove_edge(self, a, b):
        self._edges.discard(self._key(a, b))

    def toggle_edge(self, a, b):
        key = self._key(a, b)
        if key in self._edges:
            self._edges.discard(key)
            return False
        self._edges.add(key)
        return True

    def set_edge(self, a, b, linked):
        if linked:
            self.add_edge(a, b)
        else:
            self.remove_edge(a, b)

    def edges(self):
        return [tuple(e) for e in self._edges]

    def neighbours(self, node_id):
        found = []
        for edge in self._edges:
            if node_id in edge:
                other = next(iter(edge - {node_id}))
                found.append(other)
        return found

    # ------------------------------------------------------------------ queries

    @property
    def n_nodes(self):
        return len(self.nodes)

    def duplicate_names(self):
        counts = Counter(node.name for node in self.nodes.values())
        return sorted(name for name, n in counts.items() if n > 1)

    def reachable_from(self, origin_id):
        seen = {origin_id}
        queue = deque([origin_id])
        adj = self._adjacency()
        while queue:
            current = queue.popleft()
            for nxt in adj[current]:
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        return seen

    def unreachable_from(self, origin_id):
        if origin_id is None or origin_id not in self.nodes:
            return sorted(self.nodes)
        return sorted(set(self.nodes) - self.reachable_from(origin_id))

    def components(self):
        remaining = set(self.nodes)
        groups = []
        adj = self._adjacency()
        while remaining:
            start = next(iter(remaining))
            seen = {start}
            queue = deque([start])
            while queue:
                current = queue.popleft()
                for nxt in adj[current]:
                    if nxt not in seen:
                        seen.add(nxt)
                        queue.append(nxt)
            groups.append(sorted(seen))
            remaining -= seen
        groups.sort(key=len, reverse=True)
        return groups

    def _adjacency(self):
        adj = {node_id: [] for node_id in self.nodes}
        for edge in self._edges:
            a, b = tuple(edge)
            adj[a].append(b)
            adj[b].append(a)
        return adj

    def top_left_id(self):
        """The node the connectivity check treats as the origin — visually top-left."""
        if not self.nodes:
            return None
        return min(self.nodes.values(), key=lambda n: (n.y, n.x)).id

    # --------------------------------------------------------- naming anomalies

    def naming_anomalies(self):
        """Nodes whose name breaks the convention their row and column agree on.

        Only meaningful where nodes share rows (same y) and columns (same x), i.e. grid-ish
        maps; a stray keystroke like ``U85A`` loses to the majority. Returns
        (node_id, actual, expected)."""
        rows = {}
        cols = {}
        for node in self.nodes.values():
            rows.setdefault(node.y, []).append(node.name)
            cols.setdefault(node.x, []).append(node.name)

        found = []
        for node in self.nodes.values():
            # A convention only exists where enough neighbours share the row and column;
            # an island or a one-off name has no majority to violate, so leave it alone.
            if len(rows[node.y]) < 3 or len(cols[node.x]) < 3:
                continue
            letters = Counter(n[:1] for n in rows[node.y] if n)
            numbers = Counter(n[1:] for n in cols[node.x] if len(n) > 1)
            if not letters or not numbers:
                continue
            expected = letters.most_common(1)[0][0] + numbers.most_common(1)[0][0]
            if node.name != expected:
                found.append((node.id, node.name, expected))
        return found

    # ------------------------------------------------------------ distance data

    def distance_matrix(self):
        """All-pairs hop distances keyed by name, ordered like export.py (row-major)."""
        order = sorted(self.nodes.values(), key=lambda n: (n.y, n.x, n.name))
        adj = self._adjacency()
        result = {}
        for node in order:
            distances = {}
            seen = {node.id}
            queue = deque([(node.id, 0)])
            while queue:
                current, dist = queue.popleft()
                if current != node.id:
                    distances[self.nodes[current].name] = dist
                for nxt in adj[current]:
                    if nxt not in seen:
                        seen.add(nxt)
                        queue.append((nxt, dist + 1))
            result[node.name] = distances
        return result

    # ------------------------------------------------------------- grid parsing

    @classmethod
    def parse(cls, text):
        """Build a map from an export.py-style ASCII grid."""
        lines = text.split("\n")
        trailing_newline = bool(lines) and lines[-1] == ""
        if trailing_newline:
            lines = lines[:-1]

        row_indices = [i for i, line in enumerate(lines) if any(ch.isalpha() for ch in line)]
        if not row_indices:
            raise MapFormatError("No location rows found (no line contains a letter).")
        for a, b in zip(row_indices, row_indices[1:]):
            if b - a != 2:
                raise MapFormatError(
                    f"Location rows on lines {a + 1} and {b + 1} are not separated by exactly "
                    "one connector line; export.py would not read them as neighbours."
                )

        first = lines[row_indices[0]]
        col_starts = []
        idx = 0
        while idx < len(first):
            if first[idx].isalpha():
                col_starts.append(idx)
                idx += CELL_WIDTH
            else:
                idx += 1
        if not col_starts:
            raise MapFormatError("No columns found in the first location row.")
        for i, start in enumerate(col_starts):
            if start != i * CELL_WIDTH:
                raise MapFormatError(
                    f"Column {i} starts at character {start}, expected {i * CELL_WIDTH}. "
                    "The importer only understands an evenly spaced grid."
                )

        wmap = cls()
        wmap.trailing_newline = trailing_newline
        grid_ids = {}  # (row, col) -> node id; blank intersections leave a hole

        # Pass 1: create the nodes.
        for r, line_no in enumerate(row_indices):
            line = lines[line_no]
            for c, start in enumerate(col_starts):
                slot = line[start:start + CELL_WIDTH].strip("-| ")
                if slot:  # export.py tolerates blank intersections; so do we
                    grid_ids[(r, c)] = wmap.add_node(slot, x=c, y=r).id

        # Pass 2: link them, now that both endpoints of every edge exist.
        for r, line_no in enumerate(row_indices):
            line = lines[line_no]
            for c, start in enumerate(col_starts):
                if (r, c) not in grid_ids:
                    continue
                sep = start + NAME_WIDTH
                if (r, c + 1) in grid_ids and sep < len(line) and line[sep] == "-":
                    wmap.add_edge(grid_ids[(r, c)], grid_ids[(r, c + 1)])
            if line_no + 2 in row_indices:
                connector = lines[line_no + 1]
                for c, start in enumerate(col_starts):
                    if (r, c) in grid_ids and (r + 1, c) in grid_ids \
                            and start < len(connector) and connector[start] == "|":
                        wmap.add_edge(grid_ids[(r, c)], grid_ids[(r + 1, c)])
        return wmap

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8") as fh:
            return cls.parse(fh.read())

    # ------------------------------------------------------------- grid export

    def is_grid(self):
        return self._grid_problem() is None

    def _grid_problem(self):
        """Why this map cannot be an export.py grid, or None if it can."""
        if not self.nodes:
            return "the map is empty"
        max_x = max(node.x for node in self.nodes.values() if isinstance(node.x, int))
        for node in self.nodes.values():
            if not (isinstance(node.x, int) and isinstance(node.y, int)):
                return f"{node.name} is off the grid (position {node.x}, {node.y})"
            if node.x < 0 or node.y < 0:
                return f"{node.name} has a negative position"
            # The last column has no separator after it, so it can hold a longer name —
            # which is exactly how the committed 'U85A' typo fits in the file at all.
            if len(node.name) > NAME_WIDTH and node.x != max_x:
                return f"{node.name!r} is longer than {NAME_WIDTH} characters and not in the last column"
            if "-" in node.name or "|" in node.name:
                return f"{node.name!r} contains a grid separator character"
        dupes = self.duplicate_names()
        if dupes:
            return f"duplicate names: {', '.join(dupes)}"
        occupied = Counter((node.y, node.x) for node in self.nodes.values())
        clash = [pos for pos, n in occupied.items() if n > 1]
        if clash:
            return f"two locations share grid cell {clash[0]}"
        return None

    def to_grid_text(self):
        problem = self._grid_problem()
        if problem is not None:
            raise GridExportError(f"Cannot export as a grid: {problem}.")

        by_pos = {(node.y, node.x): node for node in self.nodes.values()}
        n_rows = max(node.y for node in self.nodes.values()) + 1
        n_cols = max(node.x for node in self.nodes.values()) + 1

        out = []
        for r in range(n_rows):
            row_parts = []
            for c in range(n_cols):
                node = by_pos.get((r, c))
                row_parts.append((node.name if node else "").ljust(NAME_WIDTH))
                if c < n_cols - 1:
                    right = by_pos.get((r, c + 1))
                    linked = node and right and self.has_edge(node.id, right.id)
                    row_parts.append("-" if linked else " ")
            out.append("".join(row_parts))

            if r < n_rows - 1:
                conn = []
                for c in range(n_cols):
                    node = by_pos.get((r, c))
                    below = by_pos.get((r + 1, c))
                    linked = node and below and self.has_edge(node.id, below.id)
                    conn.append("|" if linked else " ")
                    if c < n_cols - 1:
                        conn.append(" " * (CELL_WIDTH - 1))
                out.append("".join(conn).rstrip())

        text = "\n".join(out)
        return text + "\n" if self.trailing_newline else text

    def save_grid(self, path):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.to_grid_text())
