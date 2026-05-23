import json
from collections import deque

# Wczytaj plik
with open('Magazyn.txt', encoding='utf-8') as f:
    lines = [l.rstrip('\n') for l in f]

# Identyfikacja rzędów i kolumn lokalizacji
row_indices = [i for i, line in enumerate(lines) if any(c.isalpha() for c in line)]
col_indices = []
idx = 0
line0 = lines[row_indices[0]]
while idx < len(line0):
    if line0[idx].isalpha():
        col_indices.append(idx)
        idx += 4
    else:
        idx += 1

# Mapa lokalizacji: {(rząd, kolumna): "nazwa"}
lokacje = {}
for r in row_indices:
    row = lines[r]
    for ci in col_indices:
        name = row[ci:ci+3].strip()
        if name:
            lokacje[(r, ci)] = row[ci:ci+4].strip('-| ')

mapa_lok = {v: k for k, v in lokacje.items()}  # "nazwa": (r, ci)

# Tworzenie grafu DWUKIERUNKOWEGO
graph = {naz: [] for naz in mapa_lok}
for (r, ci), naz in lokacje.items():
    # W PRAWO
    if (r, ci+4) in lokacje:
        sep_pos = ci + 3
        if sep_pos < len(lines[r]) and lines[r][sep_pos] == '-':
            other = lokacje[(r, ci+4)]
            graph[naz].append(other)
            graph[other].append(naz)
    # W LEWO
    if (r, ci-4) in lokacje:
        sep_pos = ci - 1
        if sep_pos >= 0 and lines[r][sep_pos] == '-':
            other = lokacje[(r, ci-4)]
            graph[naz].append(other)
            graph[other].append(naz)
    # W DÓŁ
    if (r+2, ci) in lokacje and (r+1) < len(lines):
        if ci < len(lines[r+1]) and lines[r+1][ci] == '|':
            other = lokacje[(r+2, ci)]
            graph[naz].append(other)
            graph[other].append(naz)
    # W GÓRĘ
    if (r-2, ci) in lokacje and (r-1) >= 0:
        if ci < len(lines[r-1]) and lines[r-1][ci] == '|':
            other = lokacje[(r-2, ci)]
            graph[naz].append(other)
            graph[other].append(naz)

# Usuwamy powielenia sąsiadów
for key in graph:
    graph[key] = list(sorted(set(graph[key])))

# BFS "każdy do każdego"
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

result = {}
for naz in graph:
    result[naz] = bfs(naz, graph)

with open('mapa_odleglosci.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)
