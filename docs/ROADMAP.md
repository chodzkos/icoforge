# Roadmapa

Każda faza ma kryteria zakończenia. Nie przechodź do następnej fazy bez ukończenia poprzedniej.

---

## Faza 1 – MVP konwersji PNG → ICO ✅ UKOŃCZONA

**Cel:** działający program, który zamienia PNG na multi-rozdzielczościowe ICO z poprawnym kanałem alpha.

### Rdzeń

- [x] `core/models.py` – dataclassy `SizeSpec`, `IcoConfig`, `ResampleAlgorithm`
- [x] `core/resampling.py` – wrapper na resampling Pillow z mapą algorytmów
- [x] `core/ico_writer.py` – zapis multi-resolution ICO przez `Image.save(..., sizes=[(n,n), ...])`
- [x] `core/converter.py` – `convert()` + `render_frames()` (dla GUI preview)

### CLI

- [x] `icoforge-cli convert <input> <output> --sizes 16,32,48,256`
- [x] Flagi: `--bit-depth`, `--resample`, `--keep-aspect`, `--background`
- [x] Wyjście błędów z sensownymi komunikatami

### GUI (minimum)

- [x] Okno z polem na plik wejściowy (drop + przycisk)
- [x] Checkboxy z rozmiarami + presety
- [x] Combobox z algorytmem resamplingu
- [x] Podgląd wyniku dla każdego rozmiaru (background thread)
- [x] Przycisk „Zapisz jako…" z paskiem postępu i możliwością anulowania

### Testy

- [x] `test_ico_writer.py` – sprawdza że wynikowy ICO ma żądane rozmiary
- [x] `test_converter.py` – RGBA wchodzi RGBA wychodzi, `render_frames`, tryb paletowy
- [x] `test_cli.py` – pełne testy CLI z flagami
- [x] Coverage rdzenia: 100% dla `converter.py`, 88% całości

**Kryteria zakończenia fazy 1:** ✅ SPEŁNIONE
- ✅ `icoforge-cli convert in.png out.ico --sizes 16,32,48` produkuje poprawny ICO
- ✅ Coverage rdzenia ≥ 80% (osiągnięto 88%)
- ✅ `ruff check .` i `mypy src/` przechodzą bez błędów

---

## Faza 2 – więcej formatów wejściowych

- [ ] Rozszerzenie `converter.py` o JPG, BMP, GIF, WEBP, TIFF (Pillow obsłuży)
- [ ] Obsługa braku alpha: opcja `--background` (kolor lub `transparent`)
- [ ] SVG: `core/svg_loader.py` używający `cairosvg` lub `resvg-py`, rasteryzacja per-rozmiar (nie raz, że SVG to wektor)
- [ ] HEIC/AVIF: opcjonalny extra `pillow-heif`
- [ ] **Per-size source** – `IcoConfig` może mieć różny `Path` na każdy rozmiar (kluczowe dla 16×16, które wymaga uproszczeń)
- [ ] CLI: `--source-16 file1.png --source-32 file2.png ...` lub plik YAML z konfiguracją
- [ ] GUI: lista rozmiarów z możliwością przeciągnięcia osobnego pliku na każdy wiersz

**Kryteria zakończenia:**
- Konwersja z każdego z formatów: PNG, JPG, BMP, GIF, WEBP, TIFF, SVG
- Per-size source działa w CLI i GUI
- Brak alpha → przezroczyste tło lub wybrany kolor (test)

---

## Faza 3 – optymalizacja PNG

- [ ] `core/optimizer.py` – funkcja `optimize_png(path, level=4, strip_metadata=True)`
- [ ] Integracja `pyoxipng` (level 0–6)
- [ ] Opcja Zopfli (`--slow`) dla maksymalnej kompresji
- [ ] Ręczne usuwanie chunków metadanych: `tEXt`, `iTXt`, `zTXt`, `eXIf`, `tIME`, opcjonalnie `pHYs`
- [ ] CLI: `icoforge-cli optimize <input> [--output] [--level 4] [--strip] [--slow]`
- [ ] CLI batch: `icoforge-cli optimize *.png --in-place`
- [ ] GUI: zakładka „Optymalizacja" z drag&drop folderów, postępem i raportem oszczędności

**Kryteria zakończenia:**
- Plik wynikowy jest mniejszy o ≥10% dla typowego PNG (test na referencyjnych obrazach)
- Hash zawartości pikseli niezmieniony (bezstratność – walidacja w testach)
- Brak metadanych po `--strip` (weryfikacja `pillow.info` + parser chunków)

---

## Faza 4 – edytor pikselowy

To największy etap, podziel na pod-fazy.

### 4a – canvas i wyświetlanie
- [ ] `gui/editor/canvas.py` z `QGraphicsView`/`QGraphicsScene`
- [ ] Zoom Ctrl+kółko (1x do 64x), pan środkowym, siatka w zoomie >= 8x
- [ ] Tło w szachownicę dla pikseli z alpha < 255
- [ ] Ładowanie istniejącego ICO (`core/ico_reader.py`), tabs/lista rozmiarów

### 4b – narzędzia podstawowe
- [ ] `gui/editor/tools.py` – interfejs `Tool` z `mouse_press/move/release`
- [ ] Ołówek (z rozmiarem 1–8 px)
- [ ] Gumka (alpha = 0)
- [ ] Kroplomierz (Alt = chwilowy)
- [ ] Wypełnianie (flood fill, tolerancja kolorów)

### 4c – historia
- [ ] `QUndoStack` z komendami typu `DrawPixelCommand`, `FillCommand`
- [ ] Ctrl+Z / Ctrl+Shift+Z

### 4d – paleta i kolory
- [ ] Widget palety (kolor podstawowy + zapasowy, X do swap)
- [ ] Ekstrakcja palety z obrazu (kmeans z numpy)
- [ ] Zapis / wczytanie palety (.pal lub JSON)

### 4e – narzędzia rozszerzone
- [ ] Linia, prostokąt (wypełniony / kontur)
- [ ] Zaznaczenie prostokątne + kopiuj/wklej
- [ ] Sprite-aware paste (zachowanie alpha)

**Kryteria zakończenia:**
- Można otworzyć ICO, zedytować dowolny rozmiar i zapisać z powrotem
- Wszystkie narzędzia działają z undo
- Plik wynikowy waliduje się tak samo jak ICO z fazy 1

---

## Faza 5 – tworzenie ICO od zera

- [ ] Kreator nowego ICO: wybór rozmiarów, kolor tła
- [ ] Opcja „synchronizuj rozmiary" – edycja w jednym rozmiarze automatycznie downsampluje do mniejszych
- [ ] Templates: „Windows app", „Favicon", „Game cursor"
- [ ] Eksport do różnych formatów z tego samego projektu

---

## Funkcje dodatkowe (luźne, w razie czasu)

- [ ] ICNS (ikony macOS) – eksport z tych samych źródeł
- [ ] CUR / ANI (kursory) – ICO + hotspot
- [ ] Favicon preset (`.ico` + `.png` w wielu rozmiarach + `site.webmanifest`)
- [ ] Auto-trim przezroczystych obrzeży
- [ ] Ekstrakcja ikon z `.exe` / `.dll` (`pefile`)
- [ ] Wsadowe usuwanie tła (`rembg`)
- [ ] Pakiet PyInstaller / Nuitka z installerem (Inno Setup)
- [ ] Auto-update (mała aplikacja, raczej GitHub Releases + ręczne)
