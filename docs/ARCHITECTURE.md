# Architektura

## Główna zasada: rdzeń niezależny od UI

```
┌─────────────────┐    ┌─────────────────┐
│   GUI (Qt)      │    │   CLI (Click)   │
└────────┬────────┘    └────────┬────────┘
         │                      │
         └──────────┬───────────┘
                    │
            ┌───────▼────────┐
            │   core/        │  ← cała logika tutaj
            └────────────────┘
                    │
       ┌────────────┼────────────┐
       │            │            │
   ┌───▼───┐  ┌─────▼─────┐ ┌────▼────┐
   │Pillow │  │  pyoxipng │ │ numpy   │
   └───────┘  └───────────┘ └─────────┘
```

`core/` nie importuje niczego z `gui/` ani z `cli.py`. Jeśli musi sygnalizować postęp, robi to przez callback (`progress: Callable[[float], None] | None = None`).

## Modele danych

Wszystkie konfiguracje są dataclassami w `core/models.py`. Brak `dict`-ów po API – zawsze typowane obiekty.

```python
@dataclass(frozen=True)
class SizeSpec:
    width: int
    height: int
    bit_depth: Literal[8, 24, 32] = 32
    source_override: Path | None = None  # per-size source (faza 2)

@dataclass(frozen=True)
class IcoConfig:
    sizes: tuple[SizeSpec, ...]
    resample: ResampleAlgorithm = ResampleAlgorithm.LANCZOS
    background: Color | Literal["transparent"] = "transparent"
    preserve_aspect: bool = True
```

`frozen=True` żeby konfiguracja była hashowalna i bezpieczna dla cache.

## Pipeline konwersji

```
source files → load → (per size) resize → (optional) optimize → encode ICO
```

Każdy krok to czysta funkcja w `core/`. Pipeline jest sekwencyjny – nie ma asynchroniczności w rdzeniu. Współbieżność wprowadzana dopiero w GUI (QThreadPool) i CLI (multiprocessing dla batch).

## Format ICO – co warto wiedzieć

- ICO to kontener: nagłówek + indeks + N obrazów
- Każdy obraz może być DIB (BMP-like, dla małych) lub embedded PNG (zwykle od 256×256)
- Pillow przy `save(format="ICO", sizes=[...])` automatycznie używa PNG dla 256×256
- Bit-depth ICO: 1, 4, 8 (paleta), 24 (RGB), 32 (RGBA) – Pillow uprości to do RGBA lub palety
- Dla < 32-bit z alpha: AND mask (1-bitowa maska przezroczystości) – Pillow obsługuje, ale na poziomie naszego API powinniśmy ostrzegać że to legacy

## Resampling – wybór algorytmu

| Algorytm  | Kiedy używać                              |
| --------- | ----------------------------------------- |
| `LANCZOS` | Default. Zdjęcia, ikony fotorealistyczne. |
| `BICUBIC` | Szybciej niż Lanczos, podobna jakość.     |
| `BILINEAR`| Rzadko – kompromis.                       |
| `NEAREST` | Pixel art. Zachowuje ostre krawędzie.     |
| `BOX`     | Tylko downscale, dobre dla 256→16.        |

Per-size override – użytkownik może wybrać NEAREST dla 16×16 i LANCZOS dla 256×256 w jednym ICO.

## Optymalizacja PNG – decyzje

- **oxipng level 4** jako default (dobry kompromis czas/wynik)
- **Zopfli** opcjonalnie (flag `--slow`) – wolne ale daje +5-10%
- **Bezstratność walidowana w testach** – hash pikseli przed i po musi być identyczny
- **Strip metadata** jako osobna opcja – ludzie czasem chcą zachować ICC profile
- Brak pngquant w MVP – to lossy, narusza wymóg „bez utraty jakości"

## Edytor – architektura komend

Każda edycja to obiekt komendy implementujący `QUndoCommand`:

```python
class DrawPixelCommand(QUndoCommand):
    def __init__(self, canvas, x, y, color, prev_color):
        ...
    def redo(self): self.canvas.set_pixel(self.x, self.y, self.color)
    def undo(self): self.canvas.set_pixel(self.x, self.y, self.prev_color)
```

Powody:
- Tania pamięć (zapamiętujemy delty, nie pełne snapshoty)
- Łatwo łączyć komendy w grupy (np. cały gest ołówkiem = jedna grupa)
- Qt ma to zrobione za nas (`QUndoStack`, `QUndoGroup`)

## Threading w GUI

- UI thread tylko renderuje
- Konwersja, optymalizacja i ładowanie idą przez `QThreadPool` + `QRunnable`
- Sygnały Qt do propagacji postępu (`Signal(float)`)
- `core/` dostaje callback `progress`, który wywołuje sygnał

## Co stoi za wyborem PySide6 zamiast PyQt6

- Licencja LGPL – łatwiejsza dystrybucja w przyszłości
- API identyczne (mała różnica: `Signal`/`Slot` zamiast `pyqtSignal`/`pyqtSlot`)
- Oficjalny port od Qt Company, nie społeczność

## Co stoi za pyoxipng zamiast wywoływania binary

- Brak zależności od PATH użytkownika
- Lepsza obsługa błędów (Pythonowe wyjątki, nie parsowanie stderr)
- Działa identycznie na Windows/Linux/macOS

## Czego unikamy

- **Globalny stan.** Żadnych `current_image` w module – wszystko przekazywane jako argument lub trzymane w klasie okna
- **dict zamiast dataclass.** Słowniki tylko na granicy I/O (JSON, YAML)
- **`from foo import *`.** Eksporty jawne w `__init__.py` przez `__all__`
- **Sztuczna abstrakcja.** Nie ma "BaseConverter" dopóki nie mamy trzech konwerterów
