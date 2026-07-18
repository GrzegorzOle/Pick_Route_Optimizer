# Warehouse Route API — serwer tras / route server

Ten pakiet zawiera gotowy serwer z **wbudowanym środowiskiem .NET** (nic nie instalujesz)
oraz mapę odległości `mapa_odleglosci.json`.
This package contains a ready-to-run server with the **.NET runtime bundled inside** (nothing
to install) plus the distance map `mapa_odleglosci.json`.

> ⚠️ Rozpakuj **cały** folder i uruchamiaj program z jego wnętrza — serwer czyta
> `mapa_odleglosci.json` z katalogu, w którym leży plik wykonywalny.
> Unzip the **whole** folder and run the program from inside it — the server reads
> `mapa_odleglosci.json` from the directory next to the executable.

---

## 🇵🇱 Polski

### Uruchomienie — Windows
1. Rozpakuj zip (prawym przyciskiem → „Wyodrębnij wszystko").
2. Wejdź do rozpakowanego folderu i otwórz **Wiersz polecenia** w tym miejscu.
3. Uruchom serwer na wybranym porcie (np. 5139):
   ```
   set ASPNETCORE_URLS=http://localhost:5139
   WarehouseRouteApi.exe
   ```
   Gdyby pojawił się ekran SmartScreen: „Więcej informacji" → „Uruchom mimo to".

### Uruchomienie — Linux
```
unzip WarehouseRouteApi-linux-x64.zip -d serwer
cd serwer
chmod +x WarehouseRouteApi
ASPNETCORE_URLS=http://localhost:5139 ./WarehouseRouteApi
```

> Bez ustawienia `ASPNETCORE_URLS` serwer nasłuchuje domyślnie pod `http://localhost:5000`.

### Sprawdzenie, że działa
W drugim oknie:
```
curl http://localhost:5139/api/route/locations
```
Zwróci listę wszystkich lokalizacji magazynu. Interaktywna dokumentacja (Swagger) jest pod
`http://localhost:5139/swagger` — otwórz ten adres w przeglądarce.

### Wyznaczenie trasy
```
curl -X POST http://localhost:5139/api/route/optimal ^
  -H "Content-Type: application/json" ^
  -d "{\"startLocation\":\"A05\",\"stopLocation\":\"M05\",\"locations\":[\"B04\",\"C07\"]}"
```
- `startLocation` / `stopLocation` — punkt startu i końca (opcjonalne; domyślnie `A05` / `M05`).
- `locations` — lista lokalizacji do odwiedzenia (wymagana, min. 1). Kody są niewrażliwe na
  wielkość liter.
- W odpowiedzi `route` to kolejność zbierania (bez startu i końca), a `totalDistance` to długość
  **całej** trasy — łącznie z dojściem do startu i końca, więc jest większe niż suma pól `distance`.

### Podmiana mapy
Aby użyć innego układu magazynu, podmień plik `mapa_odleglosci.json` obok programu (wygeneruj go
w **MAP Editor** albo skryptem `export.py`) i uruchom serwer ponownie.

---

## 🇬🇧 English

### Run — Windows
1. Unzip the archive (right-click → "Extract All").
2. Open a **Command Prompt** inside the extracted folder.
3. Start the server on a port of your choice (e.g. 5139):
   ```
   set ASPNETCORE_URLS=http://localhost:5139
   WarehouseRouteApi.exe
   ```
   If SmartScreen appears: "More info" → "Run anyway".

### Run — Linux
```
unzip WarehouseRouteApi-linux-x64.zip -d server
cd server
chmod +x WarehouseRouteApi
ASPNETCORE_URLS=http://localhost:5139 ./WarehouseRouteApi
```

> With no `ASPNETCORE_URLS`, the server listens on `http://localhost:5000` by default.

### Check it works
In a second window:
```
curl http://localhost:5139/api/route/locations
```
This returns every warehouse location. Interactive docs (Swagger) live at
`http://localhost:5139/swagger` — open it in a browser.

### Ask for a route
```
curl -X POST http://localhost:5139/api/route/optimal \
  -H "Content-Type: application/json" \
  -d '{"startLocation":"A05","stopLocation":"M05","locations":["B04","C07"]}'
```
- `startLocation` / `stopLocation` — fixed endpoints (optional; default `A05` / `M05`).
- `locations` — stops to visit (required, at least one). Codes are case-insensitive.
- In the response, `route` is the picking order (start and stop omitted) and `totalDistance` is the
  length of the **whole** walk — including the legs into the start and stop, so it is larger than the
  sum of the `distance` fields.

### Swap the map
To use a different warehouse layout, replace `mapa_odleglosci.json` next to the program (generate it
with **MAP Editor** or the `export.py` script) and restart the server.
