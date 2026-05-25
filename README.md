# IcoForge

Konwerter i edytor plików ICO. Konwersja z PNG/JPG/WEBP/SVG/HEIC do `.ico` z pełną kontrolą nad rozdzielczościami i głębią bitową, bezstratna optymalizacja PNG oraz edytor pikselowy do tworzenia ikon od podstaw.

## Status

| Faza | Opis | Stan |
|------|------|------|
| Faza 1 | MVP konwersji PNG → ICO | ✅ Ukończona |
| Faza 2 | Więcej formatów wejściowych | ✅ Ukończona |
| Faza 3 | Optymalizacja PNG | ✅ Ukończona |
| Faza 4 | Edytor pikselowy | ✅ Ukończona |
| Faza 5 | Tworzenie ICO od podstaw | ✅ Ukończona |

Patrz [docs/ROADMAP.md](docs/ROADMAP.md) dla szczegółowego planu.

## Funkcje

**Faza 1 – fundament (MVP)** ✅
- Konwersja PNG/JPG/BMP/GIF/WEBP/TIFF → ICO z wyborem zestawu rozdzielczości
- Zachowanie kanału alpha i przezroczystości
- Wybór algorytmu resamplingu (Lanczos, Bicubic, Bilinear, Nearest, Box)
- Zachowanie proporcji (letterboxing)
- GUI (PySide6): drag & drop, podgląd każdego rozmiaru, zapis z paskiem postępu
- CLI: `icoforge-cli convert`

**Faza 2 – więcej formatów wejściowych** ✅
- JPG, BMP, GIF, WEBP, TIFF (przez Pillow)
- SVG (rasteryzacja resvg / cairosvg)
- HEIC, AVIF (pillow-heif)
- Per-size source – inny plik źródłowy na każdy rozmiar

**Faza 3 – optymalizacja PNG (bezstratna)** ✅
- oxipng jako główny silnik (level 0–6)
- Usuwanie metadanych (`tEXt`, `iTXt`, `zTXt`, `eXIf`, `tIME`)
- Zopfli compression (wolniej, mniejszy rozmiar)
- Tryb wsadowy z raportem CSV
- GUI: zakładka "Optymalizacja" z drag & drop, progress bar i wynikami

**Faza 4 – edytor pikselowy** ✅
- Canvas z zoomem 1×–64×, siatką pikselową i miniaturą nawigacyjną
- 7 narzędzi: ołówek, gumka, kroplomierz, wypełnianie (BFS + tolerancja), linia (Bresenham), prostokąt, zaznaczenie (marching ants)
- Undo/redo (QUndoStack) — Ctrl+Z / Ctrl+Shift+Z
- Kopiuj/wytnij/wklej z obsługą przezroczystości (sprite-aware paste)
- Paleta kolorów: siatka 32 kolorów, ekstrakcja z obrazu, zapis/wczytanie JSON
- Edycja każdej rozdzielczości osobno w obrębie tego samego ICO
- Zapis (Ctrl+S) i Zapisz jako (Ctrl+Shift+S); dialog potwierdzenia przy zamykaniu

**Faza 5 – tworzenie ICO 
od podstaw** ✅
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
