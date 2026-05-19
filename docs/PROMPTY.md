# Gotowe prompty dla Claude Code

Wklej poniższe polecenia bezpośrednio do sesji Claude Code.
Kolejność odzwierciedla kolejność faz w ROADMAP.md.

---

## 🚀 Prompt startowy (uruchom jako pierwszy w każdej sesji)

```
Przeczytaj CLAUDE.md i docs/ROADMAP.md. Powiedz mi:
1. Na którym etapie jest projekt (jakie rzeczy są już zaimplementowane)
2. Co powinienem zrobić jako następne
3. Czy wszystkie testy przechodzą (uruchom pytest)
```

---

## FAZA 1 – Konwersja PNG → ICO

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

### Krok 1.11 – Sprawdzenie jakości fazy 1

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
8. Commit z message "feat: complete phase 1 - PNG to ICO conversion with GUI and CLI"
```

---

## FAZA 2 – Więcej formatów wejściowych

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

### Krok 2.3 – Per-size source

```
Dodaj obsługę per-size source w SizeSpec i converter.py:
- SizeSpec.source_override: Path | None
- Jeśli ustawione, użyj tego pliku zamiast głównego source dla tego rozmiaru
- CLI: --source-16 path.png --source-32 path2.png (opcjonalne flagi)
- Testy: konwersja z różnym plikiem dla 16px i 256px
```

---

## FAZA 3 – Optymalizacja PNG

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

---

## FAZA 4 – Edytor pikselowy

### Krok 4.1 – Canvas (najtrudniejszy krok)

```
Zaimplementuj canvas w src/icoforge/gui/editor/canvas.py używając QGraphicsView:
- Wyświetlanie obrazu RGBA w siatce pikseli
- Zoom kółkiem myszy (Ctrl+scroll): zakres 1x do 64x
- Siatka między pikselami widoczna przy zoom >= 8x  
- Szachownica dla przezroczystych pikseli (dwa odcienie szarego, 8x8 px)
- Pan (przesuwanie) środkowym przyciskiem myszy
Nie implementuj jeszcze narzędzi rysowania – tylko wyświetlanie i nawigację.
Pokaż mi canvas z załadowanym przykładowym obrazem 32x32.
```

### Krok 4.2 – System narzędzi

```
Zaimplementuj system narzędzi w src/icoforge/gui/editor/tools.py:
- Abstrakcyjna klasa bazowa Tool z metodami on_press, on_move, on_release
- PixelTool (ołówek): maluje kolor podstawowy na klikniętych pikselach
- EraserTool (gumka): ustawia alpha=0
- EyedropperTool (kroplomierz): pobiera kolor, Alt jako tymczasowy switch
Zintegruj z canvas. Testuj ręcznie uruchamiając GUI.
```

### Krok 4.3 – Undo/Redo

```
Dodaj historię zmian przez QUndoStack:
- Klasa DrawCommand(QUndoCommand) dla operacji rysowania
- Grupowanie pociągnięć ołówkiem w jedną operację (między mouse_press a mouse_release)
- Ctrl+Z / Ctrl+Shift+Z jako skróty klawiszowe
- Menu Edit → Undo/Redo z aktualnym opisem akcji
```

### Krok 4.4 – Pozostałe narzędzia

```
Dodaj brakujące narzędzia do tools.py:
- FillTool (wiadro): flood fill z tolerancją kolorów (parametr 0-100)
- LineTool: linia prosta między punktem start a end (podgląd w trakcie rysowania)
- RectTool: prostokąt kontur lub wypełniony
- SelectTool: zaznaczenie prostokątne + kopiuj/wklej przez QClipboard
Każde narzędzie ma ikonę w toolbarze i skrót klawiszowy.
```

---

## FAZA 5 – Tworzenie ICO od zera

```
Dodaj kreator nowego ICO:
- Dialog: wybór rozmiarów (checkboxy), kolor tła lub transparent
- Otwiera edytor z pustymi kanwasami dla każdego rozmiaru
- Opcja "synchronizuj rozmiary": edycja większego → automatyczny downscale do mniejszych
- Wbudowane szablony: pusty, gradient, solid color
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

### Commit i push

```
Zrób commit wszystkich zmian z tej sesji.
Użyj opisowego commit message po angielsku (conventional commits format).
Następnie git push.
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
