# Gotowe prompty dla Claude Code

Wklej poniższe polecenia bezpośrednio do sesji Claude Code.
Kolejność odzwierciedla kolejność faz w ROADMAP.md.

---

## 🚀 Prompt startowy (uruchom jako pierwszy w każdej sesji)

```
Przeczytaj CLAUDE.md i docs/ROADMAP.md. Powiedz mi:
1. Na której gałęzi Git jesteśmy teraz (uruchom: git branch --show-current)
2. Na którym etapie jest projekt (jakie rzeczy są już zaimplementowane)
3. Co powinienem zrobić jako następne
4. Czy wszystkie testy przechodzą (uruchom pytest)
Jeśli jesteśmy na main i zaczynamy nową fazę, powiedz mi jaką komendą
utworzyć gałąź roboczą dla tej fazy.
```

---

## FAZA 1 – Konwersja PNG → ICO

### 🌿 Gałąź robocza – utwórz zanim zaczniesz

```
Utwórz gałąź roboczą dla fazy 1:
git checkout main
git pull origin main
git checkout -b feature/phase-1-png-to-ico
git push -u origin feature/phase-1-png-to-ico
Potwierdź: git branch --show-current
Wszystkie commity tej fazy idą na tę gałąź.
Po każdym kroku rób commit z opisowym message, np:
"feat: implement SizeSpec and IcoConfig models"
"feat: add Lanczos resampling wrapper"
```

### Krok 1.1 – Modele danych

```
Zaimplementuj modele danych w src/icoforge/core/models.py zgodnie z 
dokumentacją w CLAUDE.md. Przed napisaniem kodu pokaż mi plan w punktach.
Upewnij się że wszystkie dataclassy mają:
- type hints
- walidację w __post_init__
- docstringi
Napisz też testy w tests/test_models.py i upewnij się że przechodzą.
```

### Krok 1.2 – Algorytmy skalowania

```
Zaimplementuj src/icoforge/core/resampling.py:
- Mapowanie naszego enum ResampleAlgorithm na wartości Pillow
- Funkcję recommend_for_size(target_size, is_pixel_art) która zwraca 
  optymalny algorytm dla danego rozmiaru
- Testy sprawdzające że mapowanie działa dla wszystkich algorytmów
```

### Krok 1.3 – Zapis ICO

```
Zaimplementuj src/icoforge/core/ico_writer.py:
- Funkcja write_ico(target, images) która zapisuje multi-resolution ICO
- Walidacja że rozmiary obrazów zgadzają się ze specyfikacją
- Testy: sprawdź że wynikowy ICO zawiera żądane rozmiary (użyj PIL.Image.open)
```

### Krok 1.4 – Pipeline konwersji

```
Zaimplementuj pełny pipeline w src/icoforge/core/converter.py:
- Funkcja convert(source, target, config, progress=None)
- Obsługa kanału alpha (RGBA)
- Obsługa braku alpha (JPG) z opcją background color
- Callback postępu progress(float 0..1)
- Testy: konwersja PNG z alpha, bez alpha, z nieistniejącym plikiem
Uruchom pytest po implementacji i napraw wszystkie błędy.
```

### Krok 1.5 – CLI

```
Zaimplementuj CLI w src/icoforge/cli.py:
- Komenda: icoforge-cli convert <source> <target> --sizes 16,32,48,256
- Flagi: --resample (lanczos/bicubic/nearest/box), --background (transparent/#rrggbb)
- Preset: --sizes windows (cały zestaw Windows), --sizes favicon (16,32,48)
- Pasek postępu w terminalu (click.echo z \r)
- Sensowne komunikaty błędów

Przetestuj ręcznie: pobierz jakiś PNG z internetu i skonwertuj.
```

### Krok 1.6 – Główne okno GUI (szkielet)

```
Zaimplementuj główne okno aplikacji w src/icoforge/gui/main_window.py używając PySide6:
- Klasa MainWindow(QMainWindow) z tytułem "IcoForge"
- Domyślny rozmiar 900x600, możliwość zmiany rozmiaru
- Centralny widget z QHBoxLayout: po lewej panel ustawień (1/3 szerokości),
  po prawej obszar podglądu (2/3 szerokości)
- Menubar z menu: File (Open, Save As, Exit), Help (About)
- Statusbar na dole z miejscem na komunikaty
- Funkcja main() w src/icoforge/gui/main_window.py i podpięcie pod
  run_gui() w __main__.py
- Po uruchomieniu `icoforge` (lub `python -m icoforge`) okno powinno się otworzyć
Nie implementuj jeszcze logiki konwersji – tylko pusty szkielet z layoutem.
Uruchom i pokaż mi że się otwiera.
```

### Krok 1.7 – Wczytywanie pliku (przycisk + drag & drop)

```
Dodaj do MainWindow obsługę wczytywania pliku źródłowego:
- Stwórz widget src/icoforge/gui/widgets/file_drop_zone.py
- FileDropZone(QFrame) - duży obszar z napisem "Przeciągnij plik PNG tutaj
  lub kliknij aby wybrać", obsługuje dragEnterEvent i dropEvent
- Kliknięcie otwiera QFileDialog z filtrem na obsługiwane formaty
- Po wybraniu pliku: sygnał file_loaded(Path) emitowany przez widget
- W MainWindow podłącz sygnał do metody on_file_loaded(path) która:
  - Wyświetla nazwę pliku w statusbar
  - Wyświetla podgląd oryginału w prawym panelu (QLabel z QPixmap)
  - Zapamiętuje ścieżkę w self.source_path
- Walidacja: jeśli plik nieobsługiwany (zła rozszerzenie) → QMessageBox.warning
```

### Krok 1.8 – Panel ustawień konwersji

```
Stwórz src/icoforge/gui/widgets/settings_panel.py - lewy panel z opcjami:
- Klasa SettingsPanel(QWidget) z QVBoxLayout
- Sekcja "Rozmiary" - QGroupBox z checkboxami dla wszystkich standardowych
  rozmiarów (16, 20, 24, 32, 40, 48, 64, 96, 128, 256). Domyślnie zaznaczone:
  16, 32, 48, 256
- Sekcja "Presety" - QComboBox z opcjami: "Custom", "Favicon (16/32/48)",
  "Windows App (all)", "Web (16/32/64/128)". Wybór presetu zaznacza odpowiednie
  checkboxy
- Sekcja "Algorytm skalowania" - QComboBox z wartościami z ResampleAlgorithm
  (Lanczos jako default), z tooltipem opisującym kiedy używać każdego
- Sekcja "Tło dla braku alpha" - radio buttons: "Przezroczyste" (default)
  lub "Kolor" + QPushButton otwierający QColorDialog
- Metoda get_config() -> IcoConfig która zwraca skonfigurowany obiekt
- Sygnał settings_changed() emitowany przy każdej zmianie
- Dodaj panel jako lewą kolumnę w MainWindow
```

### Krok 1.9 – Podgląd rozmiarów + zapis

```
Rozszerz MainWindow o podgląd i zapis:
- Stwórz widget src/icoforge/gui/widgets/preview_panel.py
- PreviewPanel(QScrollArea) wyświetlający siatkę miniatur dla każdego
  wybranego rozmiaru (QLabel z QPixmap odpowiedniego wymiaru + etykieta
  "16x16", "32x32" itp.)
- Aktualizacja podglądu gdy zmieni się: plik źródłowy LUB ustawienia
- Renderowanie podglądu w background thread (żeby nie blokować UI dla
  dużych obrazów) - użyj QThreadPool + QRunnable, NIE odwołuj się do core
  z głównego wątku
- Przycisk "Zapisz jako..." w toolbarze lub na dole okna
- Klik otwiera QFileDialog.getSaveFileName z filtrem "*.ico"
- Po wyborze ścieżki: wywołanie core.converter.convert() w background thread
  z callback'iem postępu aktualizującym QProgressBar w statusbar
- Po zakończeniu: QMessageBox z informacją o sukcesie i opcją otwarcia folderu
- Obsługa błędów: każdy wyjątek z core → QMessageBox.critical z czytelnym komunikatem
```

### Krok 1.10 – Threading i pasek postępu

```
Wyodrębnij pracę z wątkami do osobnego modułu i ulepsz feedback dla użytkownika:
- Stwórz src/icoforge/gui/workers.py z klasą ConversionWorker(QRunnable)
- Sygnały (przez QObject signals helper): progress(float), finished(Path), error(str)
- Worker wywołuje core.converter.convert() i przekazuje progress przez sygnał
- W MainWindow: QProgressBar w statusbar pokazujący postęp 0-100%
- Disable przycisków konwersji w trakcie pracy, enable po zakończeniu
- Anulowanie konwersji: przycisk "Anuluj" + flag w workerze sprawdzana w callback
  (czysta przerwa, bez kill thread)
- Test ręczny: konwersja dużego obrazu (np. 4000x4000 PNG) - UI nie zamarza,
  progress bar płynnie się aktualizuje
```

### Krok 1.11 – Sprawdzenie jakości i scalenie z main

```
Końcowa kontrola fazy 1:
1. pytest --cov=icoforge -v (pokaż coverage, core powinno mieć ≥75%)
2. ruff check . i ruff format .
3. mypy src/
4. Uruchom GUI: icoforge - sprawdź pełny flow:
   - drag & drop pliku PNG
   - wybór rozmiarów przez preset i ręcznie
   - podgląd aktualizuje się
   - zapis do ICO działa
   - wynik otwiera się w Eksploratorze Windows (sprawdź właściwości ikony)
5. Uruchom CLI: icoforge-cli convert (jakiś-plik).png test.ico --sizes windows
6. Napraw wszystkie znalezione problemy
7. Zaktualizuj sekcję "Status" w README.md - oznacz fazę 1 jako ukończoną
8. Końcowy commit na gałęzi roboczej:
   git add .
   git commit -m "feat: complete phase 1 - PNG to ICO conversion with GUI and CLI"
   git push origin feature/phase-1-png-to-ico

Teraz poczekaj na moje potwierdzenie że wszystko działa poprawnie,
a dopiero potem scal z main:
9. git checkout main
   git pull origin main
   git merge --no-ff feature/phase-1-png-to-ico -m "feat: merge phase 1 - PNG to ICO complete"
   git push origin main
10. Usuń gałąź roboczą:
    git branch -d feature/phase-1-png-to-ico
    git push origin --delete feature/phase-1-png-to-ico
11. Potwierdź że main jest aktualny:
    git log --oneline -3
    pytest -v
```

---

## FAZA 2 – Więcej formatów wejściowych

### 🌿 Gałąź robocza – utwórz zanim zaczniesz

```
Utwórz gałąź roboczą dla fazy 2:
git checkout main
git pull origin main
git checkout -b feature/phase-2-formats
git push -u origin feature/phase-2-formats
Potwierdź: git branch --show-current
Po każdym kroku rób commit na tę gałąź.
```

### Krok 2.1 – Formaty przez Pillow

```
Rozszerz converter.py o obsługę formatów: JPG, BMP, GIF, WEBP, TIFF.
Dla formatów bez kanału alpha (JPG, BMP) użyj opcji background z ConversionConfig.
Napisz testy dla każdego formatu. Użyj małych fixture images w tests/fixtures/.
```

### Krok 2.2 – SVG

```
Dodaj obsługę SVG jako formatu wejściowego:
- Stwórz src/icoforge/core/svg_loader.py
- Użyj cairosvg (dodaj do pyproject.toml jako opcjonalny extra "svg")
- SVG musi być rasteryzowany osobno dla każdego rozmiaru (to główna zaleta SVG)
- Graceful fallback jeśli cairosvg nie jest zainstalowany (informacja dla użytkownika)
- Testy z prostym SVG (możesz użyć inline SVG jako string w fixture)
```

### Krok 2.3 – Per-size source (CLI i rdzeń)

```
Dodaj obsługę per-size source w SizeSpec i converter.py:
- SizeSpec.source_override: Path | None
- Jeśli ustawione, użyj tego pliku zamiast głównego source dla tego rozmiaru
- CLI: --source-16 path.png --source-32 path2.png (opcjonalne flagi)
- Testy: konwersja z różnym plikiem dla 16px i 256px
```

### Krok 2.4 – HEIC i AVIF

```
Dodaj obsługę formatów HEIC i AVIF jako opcjonalny extra:
- Dodaj do pyproject.toml: [project.optional-dependencies] heic = ["pillow-heif>=0.16.0"]
- Stwórz src/icoforge/core/heic_loader.py z funkcją load_heic(path) -> Image
- Przy imporcie pillow-heif rejestruje się automatycznie w Pillow przez
  register_heif_opener() – wywołaj to przy starcie aplikacji (w __main__.py)
- Graceful fallback: jeśli pillow-heif nie zainstalowane → czytelny komunikat
  "Format HEIC/AVIF wymaga: pip install icoforge[heic]"
- Rozszerz filtry w FileDropZone i QFileDialog o *.heic *.avif *.heif
- Testy: fixture z małym HEIC (możesz wygenerować programowo przez Pillow+pillow-heif),
  sprawdź że konwersja do ICO daje poprawny wynik
```

### Krok 2.5 – GUI: per-size source

```
Rozszerz GUI o obsługę per-size source (różne pliki na różne rozmiary):
- W SettingsPanel zamień listę checkboxów rozmiarów na QTableWidget z kolumnami:
  "✓" (checkbox), "Rozmiar", "Źródło" (ścieżka lub "– domyślne –"), "Wybierz..."
- Przycisk "Wybierz..." w każdym wierszu otwiera QFileDialog dla danego rozmiaru
- Kliknięcie komórki "Źródło" prawym przyciskiem → opcja "Usuń override" (wróć do domyślnego)
- Metoda get_config() uwzględnia source_override w SizeSpec
- Drag & drop pliku bezpośrednio na wiersz tabeli = ustaw jako source dla tego rozmiaru
- Wizualny wyróżnik wiersza gdy ma override (np. kolor tła)
- Testy manualne: ustaw różny PNG dla 16px i 256px, sprawdź że ICO zawiera oba
```

### Krok 2.6 – Sprawdzenie jakości i scalenie z main

```
Końcowa kontrola fazy 2:
1. pytest --cov=icoforge -v
2. ruff check . && mypy src/
3. Przetestuj ręcznie każdy format wejściowy (PNG, JPG, BMP, GIF, WEBP, TIFF, SVG)
4. Sprawdź per-size source: 16px z uproszczonego PNG, 256px z detailsowego
5. Sprawdź fallback gdy SVG/HEIC nie zainstalowane (odinstaluj tymczasowo)
6. Napraw wszystkie znalezione problemy
7. Końcowy commit na gałęzi roboczej:
   git add .
   git commit -m "feat: complete phase 2 - multi-format input and per-size source"
   git push origin feature/phase-2-formats

Poczekaj na moje potwierdzenie, a następnie scal z main:
8. git checkout main
   git pull origin main
   git merge --no-ff feature/phase-2-formats -m "feat: merge phase 2 - multi-format input complete"
   git push origin main
9. git branch -d feature/phase-2-formats
   git push origin --delete feature/phase-2-formats
10. git log --oneline -3 && pytest -v
```

---

## FAZA 3 – Optymalizacja PNG

### 🌿 Gałąź robocza – utwórz zanim zaczniesz

```
Utwórz gałąź roboczą dla fazy 3:
git checkout main
git pull origin main
git checkout -b feature/phase-3-optimizer
git push -u origin feature/phase-3-optimizer
Potwierdź: git branch --show-current
Po każdym kroku rób commit na tę gałąź.
```

### Krok 3.1 – Integracja pyoxipng

```
Zaimplementuj src/icoforge/core/optimizer.py:
- Funkcja optimize_png(source, target=None, config=None) -> OptimizationResult
- Integracja z pyoxipng (poziomy 0-6)
- OptimizationResult z bytes_before, bytes_after, saved_ratio
- verify_lossless(original, optimized) sprawdzający hash pikseli
- Testy MUSZĄ sprawdzać bezstratność (hash pikseli przed == po)
- CLI: icoforge-cli optimize input.png --level 4
```

### Krok 3.2 – Usuwanie metadanych

```
Dodaj do optimizer.py funkcję _strip_png_chunks(path, keep=frozenset()):
- Parser binarny chunków PNG (format: 4b length + 4b type + data + 4b CRC)
- Usuwa: tEXt, iTXt, zTXt, eXIf, tIME (opcjonalnie pHYs)
- Zachowuje: IHDR, IDAT, IEND, sRGB, gAMA, cHRM, iCCP (jeśli preserve_color_profile=True)
- Test: plik po strip nie ma metadanych, ale piksele identyczne
```

### Krok 3.3 – Batch i raport

```
Dodaj batch processing do optimizer.py i CLI:
- Funkcja optimize_batch(paths, config, progress=None) -> list[OptimizationResult]
- CLI: icoforge-cli optimize *.png --in-place --level 4
- Raport na końcu: X plików, łącznie Y MB → Z MB (W% mniej)
```

### Krok 3.4 – GUI: zakładka Optymalizacja

```
Dodaj zakładkę "Optymalizacja PNG" do głównego okna:
- QTabWidget jako centralny widget MainWindow (zakładki: "Konwersja", "Optymalizacja")
- W zakładce Optymalizacja:
  - Obszar drag & drop przyjmujący pliki PNG i całe foldery
  - QListWidget z kolejką plików (ścieżka + rozmiar przed + status)
  - Suwak poziomu kompresji 0–6 z etykietą "Szybszy" ↔ "Mniejszy"
  - Checkbox "Tryb Zopfli (wolny, maksymalna kompresja)"
  - Checkbox "Usuń metadane (GPS, data, aparat)"
  - Checkbox "Zachowaj profil kolorów ICC"
  - Radio buttons: "Zapisz w miejscu" / "Zapisz do folderu..." (z wyborem folderu)
  - Przycisk "Optymalizuj" uruchamiający workers.OptimizationWorker
  - QProgressBar per plik (pasek w wierszu listy) i globalny na dole
  - Raport po zakończeniu: tabela z kolumnami Plik / Przed / Po / Oszczędność %
  - Przycisk "Eksportuj raport CSV"
- Testy manualne: folder z 10 PNG, sprawdź raport
```

### Krok 3.5 – Sprawdzenie jakości i scalenie z main

```
Końcowa kontrola fazy 3:
1. pytest --cov=icoforge -v (coverage optimizera ≥ 80%)
2. ruff check . && mypy src/
3. Test bezstratności: optimize_png na 20 różnych PNG, verify_lossless musi
   przejść dla wszystkich
4. Test metadanych: sprawdź że po --strip nie ma tEXt/eXIf (użyj exiftool lub
   PIL.Image.open().info)
5. Benchmark: czas optymalizacji folderu 50 PNG (~5MB łącznie) < 30 sekund
6. Napraw wszystkie problemy
7. Końcowy commit na gałęzi roboczej:
   git add .
   git commit -m "feat: complete phase 3 - PNG optimization with GUI batch processing"
   git push origin feature/phase-3-optimizer

Poczekaj na moje potwierdzenie, a następnie scal z main:
8. git checkout main
   git pull origin main
   git merge --no-ff feature/phase-3-optimizer -m "feat: merge phase 3 - PNG optimizer complete"
   git push origin main
9. git branch -d feature/phase-3-optimizer
   git push origin --delete feature/phase-3-optimizer
10. git log --oneline -3 && pytest -v
```

---

## FAZA 4 – Edytor pikselowy

### 🌿 Gałąź robocza – utwórz zanim zaczniesz

```
Utwórz gałąź roboczą dla fazy 4:
git checkout main
git pull origin main
git checkout -b feature/phase-4-editor
git push -u origin feature/phase-4-editor
Potwierdź: git branch --show-current
Po każdym kroku rób commit na tę gałąź.
Faza 4 jest najdłuższa – commity po każdym podkroku są szczególnie ważne
żeby móc cofnąć się do stabilnego punktu w razie problemów.
```

### Krok 4.1 – ico_reader i ładowanie ICO

```
Zanim zaczniesz canvas, stwórz fundament odczytu plików ICO:
- Zaimplementuj src/icoforge/core/ico_reader.py:
  - Funkcja read_ico(path) -> list[tuple[Image, SizeSpec]]
  - Otwiera ICO przez PIL.Image, iteruje po rozmiarach przez ico.ico.sizes()
  - Dla każdego rozmiaru zwraca obraz RGBA i SizeSpec
  - Testy: otwórz ICO z fazy 1, sprawdź że liczba rozmiarów i ich wymiary zgadzają się
- Następnie zaimplementuj canvas w src/icoforge/gui/editor/canvas.py (QGraphicsView):
  - Wyświetlanie obrazu RGBA jako siatka pikseli
  - Zoom Ctrl+scroll: zakres 1x do 64x
  - Siatka między pikselami widoczna przy zoom >= 8x
  - Szachownica dla przezroczystych pikseli (dwa odcienie szarego, 8x8 px)
  - Pan (przesuwanie) środkowym przyciskiem myszy
- Stwórz src/icoforge/gui/editor/editor_window.py z:
  - QSplitter: po lewej QListWidget z listą rozmiarów z ICO, po prawej canvas
  - Kliknięcie rozmiaru na liście → canvas ładuje ten rozmiar
  - Tytuł okna: "Edytor – nazwa_pliku.ico [32x32]"
- Dodaj do menu File w MainWindow: "Otwórz ICO do edycji..." → otwiera EditorWindow
Pokaż mi działające okno edytora z załadowanym ICO i przełączaniem rozmiarów.
```

### Krok 4.2 – System narzędzi

```
Zaimplementuj system narzędzi w src/icoforge/gui/editor/tools.py:
- Abstrakcyjna klasa bazowa Tool z metodami on_press(x,y), on_move(x,y), on_release(x,y)
- PixelTool (ołówek): maluje kolor podstawowy na klikniętych pikselach, rozmiar 1-8px
- EraserTool (gumka): ustawia alpha=0, rozmiar 1-8px
- EyedropperTool (kroplomierz): klik pobiera kolor do koloru podstawowego,
  przytrzymanie Alt podczas innego narzędzia = tymczasowy switch na kroplomierz
- Toolbar z ikonami narzędzi (możesz użyć wbudowanych ikon Qt lub emoji jako placeholder)
- Skróty: B=ołówek, E=gumka, I=kroplomierz
Zintegruj z canvas. Testuj ręcznie: narysuj kilka pikseli, sprawdź że kolor się zgadza.
```

### Krok 4.3 – Undo/Redo

```
Dodaj historię zmian przez QUndoStack:
- Klasa DrawCommand(QUndoCommand) dla operacji rysowania
  - Przechowuje: współrzędne, kolor nowy, kolor poprzedni (delta, nie snapshot)
- Grupowanie: wszystkie piksele pomalowane podczas jednego kliknięcia/przeciągnięcia
  = jedna operacja w historii (QUndoStack.beginMacro / endMacro)
- Ctrl+Z / Ctrl+Shift+Z jako skróty klawiszowe
- Menu Edit z pozycjami Undo/Redo i aktualnym opisem akcji ("Undo: Pencil stroke")
- FillCommand dla flood fill (zapamiętuje listę zmienionych pikseli)
- Test: narysuj, cofnij, sprawdź że piksel wrócił do poprzedniego koloru
```

### Krok 4.4 – Paleta i kolory

```
Zaimplementuj widget palety kolorów w src/icoforge/gui/editor/palette.py:
- PaletteWidget(QWidget):
  - Dwa duże kwadraty: kolor podstawowy (foreground) i zapasowy (background)
  - Klik na kwadrat → QColorDialog z obsługą alpha
  - Klawisz X lub klik na strzałkę swap → zamień kolory miejscami
  - Klawisz D → reset do domyślnych (czarny/biały)
  - Siatka 32 kolorów do podglądu/szybkiego wyboru (edytowalna paleta)
- ColorExtractor w src/icoforge/core/color_utils.py:
  - Funkcja extract_dominant_colors(image, n=32) -> list[Color]
  - Implementacja k-means przez numpy (bez sklearn żeby nie dodawać zależności)
  - Lub użyj PIL.Image.quantize() jako szybszej alternatywy
- Przycisk "Pobierz paletę z obrazu" w PaletteWidget → wywołuje extract_dominant_colors
- Zapis palety do JSON: lista kolorów RGBA
- Wczytanie palety z pliku JSON
- Menu palety: Zapisz / Wczytaj / Resetuj do domyślnej
Dodaj PaletteWidget do EditorWindow po lewej stronie (pod listą rozmiarów).
```

### Krok 4.5 – Narzędzia rozszerzone

```
Dodaj brakujące narzędzia do tools.py:
- FillTool (wiadro farby):
  - Flood fill algorytm (iteracyjny BFS, nie rekurencja – ikony małe ale żeby nie stack overflow)
  - Parametr tolerancji kolorów 0–100 (suwak w panelu opcji narzędzia)
  - Skrót: G
- LineTool: linia prosta między punktem start a end
  - Algorytm Bresenhama
  - Podgląd linii w trakcie rysowania (render na osobnej warstwie overlay)
  - Skrót: L
- RectTool: prostokąt (toggle kontur/wypełniony w toolbarze), skrót: R
- SelectTool: zaznaczenie prostokątne
  - Wizualne "maszerujące mrówki" (animowane obramowanie zaznaczenia)
  - Kopiuj (Ctrl+C), wytnij (Ctrl+X), wklej (Ctrl+V)
  - Wklejanie zachowuje alpha (sprite-aware paste: nie nadpisuj przezroczystymi pikselami)
  - Skrót: S lub M
Każde narzędzie: ikona w toolbarze, tooltip z opisem i skrótem klawiszowym.
```

### Krok 4.6 – Zapis i sprawdzenie jakości fazy 4

```
Dokończ edytor i przeprowadź kontrolę jakości:
1. Implementuj zapis edytowanego ICO:
   - Przycisk "Zapisz" (Ctrl+S) → nadpisuje oryginalny plik
   - "Zapisz jako..." (Ctrl+Shift+S) → nowy plik
   - Jeśli niezapisane zmiany i użytkownik zamyka okno → dialog potwierdzenia
   - Użyj core.ico_writer.write_ico() – nie wynajduj koła na nowo
2. Testy integracyjne:
   - Otwórz ICO z fazy 1, edytuj piksel, zapisz, wczytaj ponownie → piksel zmieniony
   - Undo po zapisie nie cofa zapisu (historia zostaje, plik zapisany)
3. pytest -v (co da się testować automatycznie)
4. ruff check . && mypy src/
5. Test manualny pełnego flow: otwórz ICO → edytuj 32x32 → zmień kolor tła → undo →
   redo → zapisz → otwórz w Eksploratorze Windows → sprawdź wygląd ikony
6. Końcowy commit na gałęzi roboczej:
   git add .
   git commit -m "feat: complete phase 4 - pixel editor with all tools and undo history"
   git push origin feature/phase-4-editor

Poczekaj na moje potwierdzenie, a następnie scal z main:
7. git checkout main
   git pull origin main
   git merge --no-ff feature/phase-4-editor -m "feat: merge phase 4 - pixel editor complete"
   git push origin main
8. git branch -d feature/phase-4-editor
   git push origin --delete feature/phase-4-editor
9. git log --oneline -3 && pytest -v
```

---

## FAZA 5 – Tworzenie ICO od zera

### 🌿 Gałąź robocza – utwórz zanim zaczniesz

```
Utwórz gałąź roboczą dla fazy 5:
git checkout main
git pull origin main
git checkout -b feature/phase-5-new-ico
git push -u origin feature/phase-5-new-ico
Potwierdź: git branch --show-current
Po każdym kroku rób commit na tę gałąź.
```

### Krok 5.1 – Kreator nowego ICO

```
Dodaj kreator nowego pustego ICO:
- Dialog NewIcoDialog uruchamiany przez File → New ICO (Ctrl+N):
  - Checkboxy rozmiarów (domyślnie: 16, 32, 48, 256)
  - Radio: "Przezroczyste tło" / "Kolor tła" (z QPushButton → QColorDialog)
  - Sekcja "Szablon": "Pusty", "Wypełniony kolorem tła", "Skopiuj z schowka"
  - Podgląd na żywo: lista wybranych rozmiarów z informacją o łącznym rozmiarze
- Po kliknięciu OK: tworzy Document z pustymi obrazami RGBA i otwiera EditorWindow
- W EditorWindow: każdy rozmiar na liście pokazuje (pusty) canvas
- Plik "nienazwany.ico" – przy pierwszym zapisie otwiera SaveAs dialog
```

### Krok 5.2 – Synchronizacja rozmiarów i szablony

```
Rozszerz kreator i edytor o zaawansowane funkcje:
- Synchronizacja rozmiarów:
  - Checkbox "Synchronizuj rozmiary" w EditorWindow
  - Gdy włączona: po zapisaniu zmiany w większym rozmiarze, mniejsze rozmiary
    dostają automatyczny downscale (użyj ResampleAlgorithm z config)
  - Ikona synchronizacji przy każdym rozmiarze na liście (🔗 gdy zsynchronizowany)
  - Użytkownik może wyłączyć sync dla konkretnego rozmiaru ("odłącz" go)
- Szablony startowe jako osobna opcja w NewIcoDialog:
  - "Windows App Icon" – wszystkie rozmiary, czysty gradient niebieski
  - "Favicon" – 16/32/48, projekt przyjazny dla przeglądarek
  - "Kursor" – 16/32 + hotspot (przygotowuje pod .cur)
  - Szablony to PNG osadzone w zasobach aplikacji (assets/)
- Eksport wszystkich rozmiarów z tego samego projektu naraz:
  - Menu File → Export As → ICO / PNG spritesheet / Osobne PNG
  - ICNS (macOS) jeśli zainstalowane pillow-heif
```

### Krok 5.3 – Sprawdzenie jakości i scalenie z main

```
Końcowa kontrola fazy 5:
1. pytest -v && ruff check . && mypy src/
2. Test flow "od zera":
   - File → New ICO → wybierz 16, 32, 48
   - Narysuj prostą ikonę (np. literę) w każdym rozmiarze
   - Włącz synchronizację, edytuj 48px → sprawdź że 16 i 32 się zaktualizowały
   - Zapisz jako nowy.ico
   - Otwórz nowy.ico z powrotem i sprawdź że wszystko zostało zachowane
3. Test szablonów: każdy szablon otwiera się bez błędów
4. Końcowy commit na gałęzi roboczej:
   git add .
   git commit -m "feat: complete phase 5 - create ICO from scratch with sync and templates"
   git push origin feature/phase-5-new-ico

Poczekaj na moje potwierdzenie, a następnie scal z main:
5. git checkout main
   git pull origin main
   git merge --no-ff feature/phase-5-new-ico -m "feat: merge phase 5 - create from scratch complete"
   git push origin main
6. git branch -d feature/phase-5-new-ico
   git push origin --delete feature/phase-5-new-ico
7. git log --oneline -3 && pytest -v
```

---

## FUNKCJE DODATKOWE

*Każda z poniższych funkcji to osobny, niezależny krok. Implementuj w dowolnej
kolejności po ukończeniu fazy 5.*

### Eksport ICNS (ikony macOS)

```
Utwórz gałąź: git checkout main && git pull && git checkout -b feature/extra-icns && git push -u origin feature/extra-icns

Dodaj eksport do formatu ICNS (ikony aplikacji macOS):
- Stwórz src/icoforge/core/icns_writer.py
- Format ICNS: nagłówek "icns" + sekwencja bloków typ+rozmiar+dane
- Obsługiwane typy: icp4 (16px), icp5 (32px), icp6 (64px), ic07 (128px),
  ic08 (256px), ic09 (512px), ic10 (1024px) – dane jako PNG wewnątrz
- Testy: sprawdź nagłówek binarny wynikowego pliku
- CLI: icoforge-cli convert input.png output.icns --sizes 16,32,64,128,256,512
- GUI: w dialogu zapisu dodaj filtr "*.icns" i obsłuż rozszerzenie

Po zakończeniu i przetestowaniu – poczekaj na moje potwierdzenie, potem:
git add . && git commit -m "feat: add ICNS export for macOS"
git push origin feature/extra-icns
git checkout main && git merge --no-ff feature/extra-icns -m "feat: merge ICNS export" && git push origin main
git branch -d feature/extra-icns && git push origin --delete feature/extra-icns
```

### Eksport CUR (kursory Windows)

```
Utwórz gałąź: git checkout main && git pull && git checkout -b feature/extra-cur && git push -u origin feature/extra-cur

Dodaj obsługę kursorów Windows (.cur):
- Stwórz src/icoforge/core/cur_writer.py
- Format .cur jest identyczny z .ico oprócz: w nagłówku typ=2 (nie 1),
  i każdy obraz ma hotspot (x, y) zamiast zarezerwowanych bajtów
- Dodaj do IcoConfig: cursor_hotspot: tuple[int, int] | None = None
- CLI: icoforge-cli convert input.png output.cur --hotspot 0,0
- GUI: w dialogu zapisu filtr "*.cur" + pole na hotspot (dwa SpinBoxy X/Y)
  z podglądem hotspotu na miniaturze
- Test: zapisz .cur, sprawdź bajty nagłówka (offset 2-3 = 0x02 0x00)

Po zakończeniu i przetestowaniu – poczekaj na moje potwierdzenie, potem:
git add . && git commit -m "feat: add CUR cursor export with hotspot support"
git push origin feature/extra-cur
git checkout main && git merge --no-ff feature/extra-cur -m "feat: merge CUR cursor export" && git push origin main
git branch -d feature/extra-cur && git push origin --delete feature/extra-cur
```

### Favicon preset

```
Utwórz gałąź: git checkout main && git pull && git checkout -b feature/extra-favicon && git push -u origin feature/extra-favicon

Dodaj preset "Favicon Set" generujący kompletny zestaw dla strony WWW:
- Stwórz src/icoforge/core/favicon_generator.py z funkcją generate_favicon_set()
- Generuje w wybranym folderze:
  - favicon.ico (16, 32, 48px)
  - apple-touch-icon.png (180×180px, bez przezroczystości, białe tło)
  - icon-192.png i icon-512.png (dla PWA)
  - site.webmanifest z template'em {"icons": [...]}
- CLI: icoforge-cli favicon input.png output-folder/
- GUI: przycisk "Favicon Set..." w toolbarze → dialog wyboru folderu → generuje
- Test: sprawdź że wynikowy folder zawiera wszystkie 5 plików

Po zakończeniu i przetestowaniu – poczekaj na moje potwierdzenie, potem:
git add . && git commit -m "feat: add favicon set generator"
git push origin feature/extra-favicon
git checkout main && git merge --no-ff feature/extra-favicon -m "feat: merge favicon set generator" && git push origin main
git branch -d feature/extra-favicon && git push origin --delete feature/extra-favicon
```

### Auto-trim przezroczystych obrzeży

```
Utwórz gałąź: git checkout main && git pull && git checkout -b feature/extra-autotrim && git push -u origin feature/extra-autotrim

Dodaj funkcję przycinania pustych krawędzi:
- W src/icoforge/core/image_utils.py funkcja trim_transparency(image) -> Image:
  - Znajduje bounding box nieprzezroczystych pikseli (alpha > threshold)
  - Przycina obraz do tego bounding box
  - Opcja: dodaj padding N pikseli dookoła wynikowego bbox
- Integracja z konwerterem: IcoConfig.auto_trim: bool = False + auto_trim_padding: int = 0
- CLI: --auto-trim --trim-padding 4
- GUI: checkbox "Auto-trim" w SettingsPanel z polem na padding
- Testy: obraz z przezroczystymi krawędziami → po trim bbox == rozmiar treści

Po zakończeniu i przetestowaniu – poczekaj na moje potwierdzenie, potem:
git add . && git commit -m "feat: add auto-trim transparent borders"
git push origin feature/extra-autotrim
git checkout main && git merge --no-ff feature/extra-autotrim -m "feat: merge auto-trim feature" && git push origin main
git branch -d feature/extra-autotrim && git push origin --delete feature/extra-autotrim
```

### Ekstrakcja ikon z plików EXE i DLL

```
Utwórz gałąź: git checkout main && git pull && git checkout -b feature/extra-exe-extractor && git push -u origin feature/extra-exe-extractor

Dodaj możliwość wyciągania ikon z plików Windows:
- Stwórz src/icoforge/core/exe_extractor.py
- Użyj biblioteki pefile: pip install pefile (dodaj do pyproject.toml jako extra "exe")
- Funkcja extract_icons_from_exe(path) -> list[bytes] zwraca listę surowych ICO
- Obsługa błędów: plik nie jest PE, brak zasobu RT_GROUP_ICON, plik chroniony
- CLI: icoforge-cli extract-icons program.exe --output-dir ./extracted/
- GUI: File → "Wyciągnij ikony z EXE/DLL..." → dialog wyboru pliku →
  pokazuje siatkę znalezionych ikon do wyboru → zapisz zaznaczone
- Testy: fixture z minimalnym PE zawierającym ikonę (plik binarny w tests/fixtures/)

Po zakończeniu i przetestowaniu – poczekaj na moje potwierdzenie, potem:
git add . && git commit -m "feat: add icon extraction from EXE/DLL files"
git push origin feature/extra-exe-extractor
git checkout main && git merge --no-ff feature/extra-exe-extractor -m "feat: merge EXE/DLL icon extractor" && git push origin main
git branch -d feature/extra-exe-extractor && git push origin --delete feature/extra-exe-extractor
```

### Wsadowe usuwanie tła (rembg)

```
Utwórz gałąź: git checkout main && git pull && git checkout -b feature/extra-rembg && git push -u origin feature/extra-rembg

Dodaj opcjonalne usuwanie tła przez AI:
- Dodaj do pyproject.toml: [project.optional-dependencies] bgremove = ["rembg>=2.0.50"]
- Stwórz src/icoforge/core/bg_remover.py z funkcją remove_background(image) -> Image
- rembg używa modeli ONNX działających lokalnie (pierwsze uruchomienie pobiera model ~170MB)
- Informacja dla użytkownika o rozmiarze pobieranego modelu przed pierwszym użyciem
- Graceful fallback jeśli rembg nie zainstalowane
- CLI: icoforge-cli convert input.jpg output.ico --remove-bg
- GUI: checkbox "Usuń tło (AI)" w SettingsPanel (widoczny tylko jeśli rembg dostępne)
- Test manualny: zdjęcie produktu na tle → ICO z przezroczystym tłem

Po zakończeniu i przetestowaniu – poczekaj na moje potwierdzenie, potem:
git add . && git commit -m "feat: add AI background removal via rembg"
git push origin feature/extra-rembg
git checkout main && git merge --no-ff feature/extra-rembg -m "feat: merge AI background removal" && git push origin main
git branch -d feature/extra-rembg && git push origin --delete feature/extra-rembg
```

### Instalator Windows (PyInstaller + Inno Setup)

```
Utwórz gałąź: git checkout main && git pull && git checkout -b feature/extra-installer && git push -u origin feature/extra-installer

Stwórz automatyczny build instalatora dla Windows:
- Stwórz icoforge.spec dla PyInstaller:
  - Tryb onedir (nie onefile – szybszy start)
  - Dołącz zasoby: assets/, modele rembg jeśli dostępne
  - UPX compression dla mniejszego rozmiaru
  - Ikona aplikacji z assets/icoforge.ico
- Stwórz scripts/build_windows.py:
  - Uruchamia PyInstaller
  - Uruchamia Inno Setup (iscc) na skrypcie installer.iss
  - Wynikowy .exe w dist/
- Stwórz installer.iss (skrypt Inno Setup):
  - Instalacja do Program Files\IcoForge
  - Skrót na pulpicie i w Start Menu
  - Wpis w Dodaj/Usuń programy
  - Asocjacja pliku .ico z icoforge (opcjonalna)
- Stwórz .github/workflows/release.yml:
  - Trigger: push tagu "v*"
  - Buduje na windows-latest
  - Uploaduje .exe do GitHub Releases
- Test: zainstaluj na czystej maszynie Windows i sprawdź że działa

Po zakończeniu i przetestowaniu – poczekaj na moje potwierdzenie, potem:
git add . && git commit -m "feat: add Windows installer via PyInstaller and Inno Setup"
git push origin feature/extra-installer
git checkout main && git merge --no-ff feature/extra-installer -m "feat: merge Windows installer build" && git push origin main
git branch -d feature/extra-installer && git push origin --delete feature/extra-installer
```

---

## Prompty pomocnicze (do użycia w dowolnym momencie)

### Naprawienie błędów

```
Mam błąd: [WKLEJ TUTAJ TREŚĆ BŁĘDU]
Znajdź przyczynę i napraw. Wyjaśnij co było nie tak.
```

### Przegląd kodu

```
Przejrzyj ostatnio napisany kod w [NAZWA PLIKU].
Znajdź potencjalne problemy, nieoptymalny kod, brakujące edge cases.
Zaproponuj ulepszenia.
```

### Commit i push (w trakcie pracy na gałęzi)

```
Sprawdź na jakiej gałęzi jesteśmy (git branch --show-current).
Zrób commit wszystkich zmian z tej sesji na aktualną gałąź.
Użyj opisowego commit message po angielsku (conventional commits format).
Następnie git push origin <nazwa-aktualnej-gałęzi>.
NIE scalaj z main – to robimy dopiero po pełnym sprawdzeniu jakości.
```

### Status projektu

```
Uruchom pytest i pokaż wyniki.
Następnie sprawdź ruff i mypy.
Powiedz mi co jest gotowe, co w trakcie, co następne według ROADMAP.md.
```

### Dodawanie funkcji z listy

```
Zaimplementuj [NAZWA FUNKCJI] z docs/FEATURES.md.
Zanim zaczniesz, pokaż mi jak planujesz to zrobić.
Napisz testy przed implementacją (TDD).
```
