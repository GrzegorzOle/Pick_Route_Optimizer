## 📦 Co pobrać / What to download

Wszystkie pliki są **samodzielne** — mają wbudowane środowisko uruchomieniowe, więc nic nie
instalujesz. All files are **self-contained** — the runtime is bundled in, nothing to install.

| Program | Windows | Linux |
|---|---|---|
| **Serwer tras / Route API** | `WarehouseRouteApi-windows-x64.zip` | `WarehouseRouteApi-linux-x64.zip` |
| **Edytor mapy / Map editor** | `MapEditor-windows.exe` | `MapEditor-linux` |

---

### 🚚 Serwer tras / Route API server

Rozpakuj **cały** zip i uruchom program z jego wnętrza (czyta `mapa_odleglosci.json` obok siebie).
Unzip the **whole** archive and run the program from inside it.

**Windows** — w rozpakowanym folderze / in the extracted folder:
```
set ASPNETCORE_URLS=http://localhost:5139
WarehouseRouteApi.exe
```
**Linux:**
```
chmod +x WarehouseRouteApi
ASPNETCORE_URLS=http://localhost:5139 ./WarehouseRouteApi
```
Sprawdź / check: otwórz `http://localhost:5139/swagger` w przeglądarce.
Pełna instrukcja jest w pliku `README.md` w zipie. Full instructions are in `README.md` inside the zip.

### 🗺️ Edytor mapy / Map editor

- **Windows:** `MapEditor-windows.exe` — kliknij dwukrotnie / double-click to run.
- **Linux:** `chmod +x MapEditor-linux` → `./MapEditor-linux`

Otwiera się z przykładową mapą; użyj **Open**, aby wczytać własny `Magazyn.txt`, a **Generate JSON**,
aby zbudować `mapa_odleglosci.json` dla serwera.
Opens with a sample map; use **Open** to load your own `Magazyn.txt`, and **Generate JSON** to build
`mapa_odleglosci.json` for the server.

---
