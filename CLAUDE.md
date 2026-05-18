# CLAUDE.md

Kontekst projektu dla Claude Code. Czytaj ten plik na początku każdej sesji.

## Czym jest projekt

IcoForge to desktopowy konwerter i edytor plików ICO napisany w Pythonie. Łączy trzy obszary:
1. Konwersja obrazów (PNG, JPG, SVG, …) do wielorozdzielczościowego ICO
2. Bezstratna optymalizacja PNG (oxipng + ręczne czyszczenie metadanych)
3. Edytor pikselowy do tworzenia / edycji ICO od zera

Architektura jest celowo podzielona na rdzeń (`core/`) niezależny od GUI – ten sam kod obsługuje GUI (PySide6) i CLI. Każda funkcja powinna najpierw działać w `core/` z testami, dopiero potem dostawać interfejs.

## Stos technologiczny

- **Python 3.11+** – nowoczesne typing, match statements
- **PySide6** – GUI (licencja LGPL, lepsze niż PyQt6 dla dystrybucji)
- **Pillow** + **numpy** – obróbka obrazów
- **pyoxipng** – optymalizacja PNG
- **pytest** + **pytest-qt** – testy
- **ruff** – lint i formatowanie (zamiast black + flake8 + isort)
- **mypy** w trybie strict – type checking

## Konwencje kodu

- Wszystkie publiczne funkcje mają type hints i docstringi w stylu Google
- Nie ma `Any` poza warstwą I/O – jeśli musisz użyć, dodaj komentarz dlaczego
- Plik tematyczny, nie typy – jeden moduł = jedna domena (np. `ico_writer.py`, nie `models.py`)
- Funkcje pure w `core/`, side-effects izolowane w `gui/` i `cli.py`
- Brak globalnego stanu. Konfiguracja przekazywana jawnie przez dataclassy
- Komentarze i docstringi po angielsku (kod), README/docs po polsku

## Struktura katalogów

```
src/icoforge/
├── core/           # Rdzeń, bez zależności od GUI/CLI
│   ├── ico_writer.py     # Zapis ICO z multi-resolution
│   ├── ico_reader.py     # Parser ICO (do edytora)
│   ├── converter.py      # Pipeline: source → resized → ICO
│   ├── optimizer.py      # Optymalizacja PNG
│   ├── resampling.py     # Algorytmy resamplingu i wybór
│   └── models.py         # Dataclassy: IcoConfig, SizeSpec, …
├── gui/            # PySide6
│   ├── main_window.py
│   ├── editor/           # Canvas, narzędzia, undo stack
│   └── widgets/          # Reużywalne widgety
├── utils/          # Logging, ścieżki, helpers
├── cli.py
└── __main__.py     # `python -m icoforge`
```

## Komendy

```bash
# Setup
pip install -e ".[dev]"

# Testy
pytest                          # wszystkie
pytest tests/test_converter.py  # jeden plik
pytest -k "alpha"               # po nazwie
pytest --cov=icoforge           # z coverage

# Lint i typing
ruff check .
ruff format .
mypy src/

# Uruchomienie
icoforge          # GUI
icoforge-cli ...  # CLI
```

## Filozofia rozwoju

- **Małe iteracje.** Najpierw działający MVP fazy 1, potem rozszerzanie.
- **Test-first dla rdzenia.** GUI i tak będzie się zmieniał, ale `core/` musi być solidny.
- **Nie zaczynaj GUI bez działającego CLI.** CLI jest darmowym testem API rdzenia.
- **Optymalizacja po profilowaniu.** Pillow i numpy są szybkie; nie cache'uj na zapas.

## Roadmapa

Patrz [docs/ROADMAP.md](docs/ROADMAP.md). Każda faza ma jasno zdefiniowane kryteria zakończenia. Nie skacz między fazami – kończ kompletnie.

## Gdy coś nie pasuje

Jeśli zaproponowana zmiana łamie którąś z konwencji powyżej, **najpierw zapytaj**, nie zakładaj że konwencja jest do wyrzucenia. Konwencje są tu po to, żeby kod był spójny przez całą długość projektu.

## Co NIE należy do tego projektu

- Konwersja w drugą stronę (ICO → PNG poza prostym eksportem z edytora)
- Wektorowa edycja (to nie Inkscape)
- Generowanie ikon z tekstu / AI (osobny projekt)
- Web frontend (to ma być natywna aplikacja desktop)
