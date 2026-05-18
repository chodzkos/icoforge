# IcoForge

Konwerter i edytor plików ICO. Konwersja z PNG/JPG/WEBP/SVG/HEIC do `.ico` z pełną kontrolą nad rozdzielczościami i głębią bitową, bezstratna optymalizacja PNG oraz edytor pikselowy do tworzenia ikon od podstaw.

## Status

Projekt na wczesnym etapie. Patrz [docs/ROADMAP.md](docs/ROADMAP.md) dla aktualnego planu.

## Funkcje (planowane)

**Faza 1 – fundament (MVP)**
- Konwersja PNG → ICO z wyborem zestawu rozdzielczości (16, 20, 24, 32, 40, 48, 64, 96, 128, 256 px)
- Konfiguracja głębi bitowej (8 / 24 / 32-bit) per rozmiar
- Zachowanie kanału alpha i przezroczystości
- Wybór algorytmu resamplingu (Lanczos, Bicubic, Nearest – pixel art)
- CLI równolegle do GUI

**Faza 2 – więcej formatów wejściowych**
- JPG, BMP, GIF, WEBP, TIFF (przez Pillow)
- SVG (rasteryzacja resvg / cairosvg)
- HEIC, AVIF (pillow-heif)
- Per-size source – inny plik źródłowy na każdy rozmiar

**Faza 3 – optymalizacja PNG (bezstratna)**
- oxipng jako główny silnik
- Usuwanie metadanych (`tEXt`, `iTXt`, `zTXt`, `eXIf`, `tIME`)
- Zopfli compression (wolniej, mniejszy rozmiar)
- Tryb wsadowy

**Faza 4 – edytor pikselowy**
- Canvas z zoomem do 32x i widokiem siatki
- Narzędzia: ołówek, gumka, wypełnianie, kroplomierz, prostokąt, linia, zaznaczenie
- Undo/redo (command stack)
- Edycja każdej rozdzielczości osobno w obrębie tego samego ICO
- Paleta kolorów z importem z obrazu

**Faza 5 – tworzenie ICO od podstaw**
- Kreator nowego ICO (wybór rozmiarów, kolor tła / transparent)
- Synchronizacja warstw między rozmiarami (opcjonalna)

**Funkcje dodatkowe**
- Eksport ICNS (macOS) i CUR (kursory Windows)
- Preset Favicon (`.ico` + `apple-touch-icon` + manifest PWA)
- Auto-trim przezroczystych obrzeży
- Ekstrakcja ikon z `.exe` / `.dll`
- Drag & drop, batch processing

## Instalacja (dev)

```bash
git clone https://github.com/<your-user>/icoforge.git
cd icoforge
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Uruchomienie

```bash
# GUI
icoforge

# CLI
icoforge-cli convert input.png output.ico --sizes 16,32,48,256
icoforge-cli optimize input.png --output input.min.png
```

## Architektura

Patrz [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Licencja

MIT
