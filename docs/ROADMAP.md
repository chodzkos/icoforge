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

- [x] Rozszerzenie `converter.py` o JPG, BMP, GIF, WEBP, TIFF (Pillow obsłuży)
- [x] Obsługa braku alpha: opcja `--background` (kolor lub `transparent`)
- [x] SVG: `core/svg_loader.py` używający `cairosvg`, rasteryzacja per-rozmiar (graceful fallback bez cairosvg)
- [x] HEIC/AVIF: opcjonalny extra `pillow-heif` (`core/heic_loader.py`, graceful fallback, GUI filters)
- [x] **Per-size source** – `IcoConfig` może mieć różny `Path` na każdy rozmiar (kluczowe dla 16×16, które wymaga uproszczeń)
- [x] CLI: `--source-16 file1.png --source-32 file2.png ...` (flagi dla standardowych rozmiarów: 16, 20, 24, 32, 40, 48, 64, 96, 128, 256)
- [x] GUI: `SizeTable` (QTableWidget) z kolumnami ✓/Rozmiar/Źródło/Wybierz…, drag&drop per wiersz, podświetlenie override, context menu "Usuń override"

**Kryteria zakończenia:**
- Konwersja z każdego z formatów: PNG, JPG, BMP, GIF, WEBP, TIFF, SVG
- Per-size source działa w CLI i GUI
- Brak alpha → przezroczyste tło lub wybrany kolor (test)

---

## Faza 3 – optymalizacja PNG ✅ UKOŃCZONA

- [x] `core/optimizer.py` – funkcja `optimize_png(path, level=4, strip_metadata=True)`
- [x] Integracja `pyoxipng` (level 0–6)
- [x] Opcja Zopfli (`--slow`) dla maksymalnej kompresji
- [x] Ręczne usuwanie chunków metadanych: `tEXt`, `iTXt`, `zTXt`, `eXIf`, `tIME`, opcjonalnie `pHYs`
- [x] CLI: `icoforge-cli optimize <input> [--output] [--level 4] [--strip] [--slow]`
- [x] CLI batch: `icoforge-cli optimize *.png --in-place`
- [x] GUI: zakładka „Optymalizacja" z drag&drop folderów, postępem i raportem oszczędności

**Kryteria zakończenia:** ✅ SPEŁNIONE
- ✅ Plik wynikowy jest mniejszy o ≥10% dla typowego PNG (średnia 54% dla testowych)
- ✅ Hash zawartości pikseli niezmieniony (20/20 PNG przechodzą test bezstratności)
- ✅ Brak metadanych po `--strip` (weryfikacja PIL.Image.open().info)
- ✅ Coverage optimizera: 91% (wymagane ≥80%)
- ✅ Benchmark: 50 PNG (8.3MB) w 1.76s (wymagane < 30s)

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
