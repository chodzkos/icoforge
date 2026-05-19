# CLAUDE.md

Kontekst projektu dla Claude Code. Czytaj ten plik na początku każdej sesji.

## Czym jest projekt

IcoForge to desktopowa aplikacja Python do tworzenia i edycji plików ikon (.ico).
Łączy trzy obszary:

1. **Konwersja** – pliki PNG/JPG/SVG/WEBP → wielorozdzielczościowy plik .ico
2. **Optymalizacja PNG** – bezstratne zmniejszanie rozmiaru pliku (bez utraty pikseli)
3. **Edytor pikselowy** – tworzenie i edycja ikon piksel po pikselu

Każda z tych funkcji jest dostępna zarówno przez GUI (okienkowy program)
jak i przez CLI (wiersz poleceń) – ten sam kod rdzenia (`core/`).

## Stos technologiczny

- **Python 3.11+**
- **PySide6** – GUI (licencja LGPL)
- **Pillow** + **numpy** – obróbka obrazów
- **pyoxipng** – optymalizacja PNG
- **click** – CLI
- **pytest** + **pytest-qt** – testy
- **ruff** + **mypy strict** – lint i typowanie

## Architektura – najważniejsza zasada

`core/` NIE importuje niczego z `gui/` ani `cli.py`.
Cała logika biznesowa jest w `core/` i działa niezależnie od interfejsu.
Postęp operacji przez callback: `progress: Callable[[float], None] | None = None`

## Struktura katalogów

```
src/icoforge/
├── core/                  # Logika – bez GUI/CLI
│   ├── models.py          # Dataclassy: SizeSpec, IcoConfig, OptimizationConfig
│   ├── resampling.py      # Algorytmy skalowania obrazu
│   ├── converter.py       # Pipeline: source → resized → ICO
│   ├── ico_writer.py      # Zapis ICO (multi-resolution)
│   ├── ico_reader.py      # Odczyt ICO (do edytora, faza 4)
│   └── optimizer.py       # Optymalizacja PNG (faza 3)
├── gui/                   # PySide6 GUI
│   ├── main_window.py
│   ├── editor/            # Edytor pikselowy (faza 4)
│   └── widgets/           # Reużywalne widgety
├── utils/
├── cli.py
└── __main__.py
```

## Konwencje kodu

- Type hints na wszystkich publicznych funkcjach
- Docstringi Google-style po angielsku w kodzie
- Dataclassy z `frozen=True` zamiast słowników po API
- `ruff check .` i `mypy src/` muszą przechodzić przed każdym commitem
- Test-first dla rdzenia: najpierw test, potem implementacja
- Komentarze w kodzie po angielsku, dokumenty w docs/ po polsku

## Komendy robocze

```bash
pip install -e ".[dev]"          # instalacja
pytest                           # wszystkie testy
pytest tests/test_converter.py   # jeden plik
pytest --cov=icoforge            # z pokryciem kodu
ruff check . --fix               # lint z auto-naprawą
ruff format .                    # formatowanie
mypy src/                        # type checking
icoforge-cli convert in.png out.ico --sizes 16,32,48,256
```

## Roadmapa i zasoby

- `docs/ROADMAP.md` – plan faz z kryteriami zakończenia
- `docs/PROMPTY.md` – gotowe polecenia do implementacji kolejnych kroków
- `docs/ZALOZENIA_PROJEKTU.md` – pełne założenia w języku polskim
- `docs/CO_ROBI_CLAUDE_CODE.md` – podział pracy user vs Claude Code

## Co NIE należy do projektu

- OCR, AI generowanie obrazów
- Konwersja EPUB/PDF (osobny projekt – epubtools)
- Web frontend
- Generator ikon z tekstu
