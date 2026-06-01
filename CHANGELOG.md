# Changelog

Wszystkie istotne zmiany w tym projekcie są dokumentowane tutaj.
Format oparty na [Keep a Changelog](https://keepachangelog.com/pl/1.0.0/).
Projekt stosuje [Semantic Versioning](https://semver.org/lang/pl/).

---

## [1.2.2] - 2026-06-01

### Naprawione

- **Pozostalosci starego motywu po przełaczeniu** — Qt nie zawsze propaguje
  zmiane palety/stylesheet do wszystkich widgetow potomnych (widoczne jako
  ciemne fragmenty w widgecie "Rozmiary" po przejsciu jasny → ciemny → jasny).
  `ThemeManager._force_refresh()` wykonuje teraz `style.unpolish / style.polish
  / widget.update()` na kazdym widgecie aplikacji po kazdej zmianie motywu.
  Dodatkowo hardcoded kolory `QColor(150,150,150)` i `QColor(0,0,0)` w
  `SizeTable` zastapiono rolami palety (`PlaceholderText`, `Text`), zeby
  kolor tekstu elementow tablicy aktualizowal sie niezaleznie od odswiezenia.

### Dodane

- **Ciemny pasek tytulu okna na Windows** — przy trybie ciemnym aplikacji
  pasek tytulu (systemowy, z przyciskami okna) teraz rowniez jest ciemny,
  nawet gdy Windows jest ustawiony w tryb jasny. Realizowane przez
  `DwmSetWindowAttribute(DWMWA_USE_IMMERSIVE_DARK_MODE=20)` via ctypes
  (nowy plik `utils/window_theme.py`). Obsluguje Windows 10 build 2004+
  i Windows 11; fallback na atrybut 19 dla starszych pre-release buildow;
  na innych systemach i przy braku DWM — cisza (no-op). Dotyczy okna
  glownego i okna edytora; zmiana obowiazuje natychmiast po przelaczeniu
  motywu bez restartu.

---

## [1.2.1] - 2026-06-01

### Dodane

- **Tryb ciemny / jasny** — menu Widok → Motyw z trzema opcjami (QActionGroup,
  wzajemnie wykluczające sie): Automatyczny (sledzi OS), Ciemny (qdarktheme),
  Jasny (natywny Qt). Wybor zapisywany w `settings.json`; przywracany przy
  starcie aplikacji.
- `utils/theme.py`: nowa klasa `ThemeManager` (QObject, singleton); zapamiętuje
  natywny styl / paletę / stylesheet przed pierwszym wywołaniem qdarktheme, by
  tryb jasny mozna bylo przywrocic do dokladnie oryginalnego wygladu.
- `utils/settings.py`: generyczne helpery `get_setting()` / `save_setting()`.
- `pyproject.toml`: nowa zaleznosc `pyqtdarktheme>=0.1.7`.

### Naprawione

- **Tryb jasny = wygląd natywny Qt** — qdarktheme 0.1.7 nakładał własny płaski
  jasny motyw. `ThemeManager._apply_native_light()` przywraca oryginalny styl,
  paletę i stylesheet zamiast wołac qdarktheme dla "light". Wygląd trybu
  jasnego jest pixel-identyczny z wersją sprzed wprowadzenia motywów.
- Szachownica canvasu dostosowuje kolory do aktywnej palety aplikacji (jasna:
  biały/szary; ciemna: ciemnoszary/grafitowy) — bez potrzeby osobnych
  wywołań konfiguracyjnych.

### Zmienione

- `__main__.py`: `ThemeManager` tworzony przed `MainWindow`; podłączony do
  `styleHints().colorSchemeChanged` dla live-update bez restartu.
- `gui/editor/canvas.py`: `CheckerboardBackground.paint()` czyta jasność biezacej
  palety w kazdym odswiezeniu; `EditorCanvas._on_theme_changed()` aktualizuje
  kolor tla widoku.
- `gui/main_window.py`: nowe menu Widok → Motyw; `_on_about` wybiera
  `logo-dark.png` / `logo-light.png` (fallback do `logo.png`).

---

## [1.2.0] - 2026-05-31

### Naprawione

- **ico_reader: dekodowanie klatek DIB/BMP** — `read_ico()` przekazywalo surowe
  bajty klatki do generycznego `Image.open()`, ktory traktowal dane DIB jako
  zwykly BMP z podwojoną wysokoscia (`biHeight * 2` w `BITMAPINFOHEADER`).
  Skutek: blad "image file is truncated" dla ikon klasycznych Windows i ikon
  wyciagnietych z plikow EXE/DLL. Naprawka: delegacja do
  `IcoImagePlugin.IcoFile.frame()`, ktory poprawnie obsluguje format ICO DIB
  (XOR bitmap + AND mask, polowa wysokosci). ([tests/test_ico_reader.py])

- **ico_writer: glebokos bitowa realnie wplywa na zawartosc PNG** — pole
  `bit_depth` w `SizeSpec` trafialo tylko do naglowka `ICONDIRENTRY.bitCount`,
  ale kodowany PNG zawsze byl 32-bitowym RGBA. Naprawka: `_encode_png` koduje
  odpowiednio do `bit_depth`: 8 → tryb P (paleta, `quantize`), 24 → RGB (alpha
  splaszczona w konwerterze na kolor tla lub biel), 32 → RGBA bez zmian.
  Pole `bitCount` jest teraz spojne z danymi. ([tests/test_ico_writer.py])

- **converter: SVG ignorowalo opcje remove_bg / auto_trim / preserve_aspect** —
  `_render_svg_frame` stosowal tylko kompozycje koloru tla, pomijajac usuwanie
  tla, przycinanie przezroczystych obrzezy i letterboxing. Naprawka: SVG jest
  teraz rasteryzowane do naturalnego rozmiaru (`rasterize_svg_natural`), nastepnie
  przechodzi przez wspolny krok `_apply_post_load` (remove_bg + auto_trim) i
  `_render_frame` (resize + letterbox). Ta sama sciezka co rastry i HEIC.
  ([tests/test_svg.py])

- **optimizer: `preserve_color_profile=True` nie zachowywalo profilu koloru** —
  `optimize_png` budowalo `StripChunks` wylacznie z `keep_chunks`, ignorujac
  flage `preserve_color_profile`. Chunki `iCCP`, `sRGB`, `gAMA`, `cHRM` byly
  usuwane mimo ustawienia `True`. Naprawka: `chunks_to_keep = keep_chunks |
  _COLOR_PROFILE_CHUNKS` gdy flaga jest aktywna. Usuniety rowniez martwy kod
  (`_strip_png_chunks` i pomocniki) nie uzywany w zywej sciezce.
  ([tests/test_optimizer.py])

- **CLI `optimize`: domyslnie nadpisywalo plik zrodlowy** — wywolanie
  `icoforge-cli optimize plik.png` bez zadnych flag zapisywalo wynik w miejscu
  (target=None → optimize_png nadpisuje zrodlo). Nowe zachowanie: domyslnie
  tworzy `<stem>.min.png` obok zrodla — zrodlo pozostaje nienaruszone. Dla wielu
  plikow wymagany jest jawny `--in-place`. Dodano flagi `--force` (nadpisz
  istniejacy .min.png) oraz blokade polaczenia `--in-place + --output`.
  ([tests/test_cli.py])

### Zmienione

- `IcoConfig.sizes` z `bit_depth=24` kompozytuje przezroczyste piksele na
  skonfigurowany kolor tla (lub biel gdy `background="transparent"`) przed
  zapisem jako RGB PNG.
- `svg_loader`: nowa funkcja `rasterize_svg_natural()` zwraca SVG w naturalnych
  wymiarach; uzywana przez `_render_svg_frame` zamiast bezposredniej rasteryzacji
  do rozmiaru docelowego.
- `converter`: wspolna funkcja `_apply_post_load(img, config)` eliminuje
  powielanie logiki remove_bg + auto_trim miedzy rastrem, HEIC i SVG.

---

## [1.1.2] - 2026-05-28

### Naprawione

- Testy CI: usuniety test `test_is_position_visible_returns_false_without_running_app`,
  ktory zakladal brak `QApplication` w procesie testowym — pytest-qt tworzy ja
  przed pierwszym testem.

---

## [1.1.1] - 2026-05-26

### Naprawione

- Ikona skrotu na pulpicie (Windows): dodano jawne `IconFilename` w instalatorze
  Inno Setup oraz bundlowanie `icoforge.ico` w korzeniu paczki PyInstaller.
- Logo w oknie "O programie": scentralizowano ladowanie zasobow przez
  `get_resource_path()` dzialajace zarowno w srodowisku deweloperskim, jak i
  w paczce PyInstaller (`sys._MEIPASS`).

---

## [1.1.0] - 2026-05-26

### Dodane

- Wsparcie SVG: dwa backendy (resvg-py bez zewnetrznych DLL; cairosvg z
  bundlowanymi bibliotekami Cairo dla instalatora Windows).
- Ikona i logo aplikacji (`assets/icoforge.ico`, `assets/logo.png`).
- Usuwanie tla AI: opcja `rembg` z widoczna sekcja w `SettingsPanel` (naprawa
  przez `QScrollArea`).
- Dokumentacja: README z opisem instalacji AI pod Windows, FEATURES.md, aktualizacja
  ROADMAP.md.

---

## [1.0.0] - 2026-03-23

### Dodane

- Konwersja PNG/JPG/BMP/GIF/WEBP/TIFF → ICO (multi-resolution).
- Optymalizacja PNG (oxipng, poziomy 0–6, Zopfli, usuwanie metadanych).
- Edytor pikselowy: canvas, narzedzia (olowek, gumka, flood-fill, linia,
  prostokat, zaznaczenie), undo/redo, paleta.
- CLI: `icoforge-cli convert`, `icoforge-cli optimize`.
- Eksport ICNS, CUR, Favicon Set.
- Ekstrakcja ikon z EXE/DLL (`pefile`).
- Instalator Windows (Inno Setup) i paczka portable ZIP.
- GitHub Actions: CI + release na tag.
