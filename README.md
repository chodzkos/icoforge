<p align="center">
  <img src="assets/logo.png" alt="IcoForge" width="300"/>
</p>

# IcoForge

Konwerter i edytor plików ICO dla Windows. Konwersja z PNG/JPG/WEBP/SVG/HEIC do `.ico`
z pełną kontrolą nad rozdzielczościami, bezstratna optymalizacja PNG oraz edytor pikselowy
do tworzenia ikon od podstaw.

## Funkcje

### Konwersja
- Formaty wejściowe: PNG, JPG, BMP, GIF, WEBP, TIFF, SVG, HEIC/AVIF
- Wybór zestawu rozdzielczości (16–256 px), presety Windows / Favicon / Game
- 5 algorytmów resamplingu (Lanczos, Bicubic, Bilinear, Nearest, Box)
- Zachowanie kanału alpha i przezroczystości; letterboxing z wypełnieniem kolorem
- Per-size source — inny plik źródłowy dla każdego rozmiaru
- Usuwanie tła AI (U2-Net / rembg, opcjonalny extra)
- Auto-trim przezroczystych obrzeży
- Eksport: `.ico`, `.icns` (macOS), `.cur` (kursor Windows), Favicon Set (`.ico` + PWA icons + `webmanifest`)
- Ekstrakcja ikon z `.exe` / `.dll`

### Optymalizacja PNG
- Bezstratna kompresja z oxipng (poziomy 0–6) i opcją Zopfli
- Usuwanie metadanych (tEXt, iTXt, zTXt, eXIf, tIME)
- Tryb wsadowy z raportem oszczędności (%)

### Edytor pikselowy
- Canvas z zoomem 1×–64×, siatką i miniaturą nawigacyjną
- Narzędzia: ołówek, gumka, kroplomierz, wypełnianie (BFS + tolerancja), linia, prostokąt, zaznaczenie
- Undo/redo (Ctrl+Z / Ctrl+Shift+Z), kopiuj/wytnij/wklej
- Paleta 32 kolorów z ekstrakcją z obrazu i zapisem/wczytaniem JSON
- Edycja każdej rozdzielczości osobno w obrębie tego samego ICO
- Kreator nowego ICO (wybór rozmiarów, kolor tła, synchronizacja warstw)

### Interfejs
- GUI (PySide6): drag & drop, podgląd każdego rozmiaru, pasek postępu
- CLI: `icoforge-cli convert`, `icoforge-cli optimize`
- Lokalizacja PL/EN z przełącznikiem języka (Pomoc → Język)
- Instalator Windows + wersja portable

---

## Instalacja

### Instalator Windows (zalecane)

Pobierz `IcoForge-X.Y.Z-setup.exe` ze strony [Releases](https://github.com/chodzkos/icoforge/releases)
i uruchom instalator. Nie wymaga dodatkowych zależności.

### Wersja portable

Pobierz `IcoForge-portable-X.Y.Z.zip`, rozpakuj w dowolne miejsce i uruchom `IcoForge.exe`.

### Instalacja deweloperska

```bash
git clone https://github.com/chodzkos/icoforge.git
cd icoforge
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

---

## Opcjonalne zależności

### SVG

```bash
pip install resvg-py            # zalecane — czyste koła Rust, bez DLL
# lub
pip install "icoforge[svg]"     # cairosvg (wymaga libcairo-2.dll)
```

### HEIC / AVIF

```bash
pip install "icoforge[heic]"
```

### Ekstrakcja ikon z EXE/DLL

```bash
pip install "icoforge[exe]"
```

---

## Usuwanie tła AI na Windows

Funkcja "Usuń tło (AI)" używa modelu U2-Net przez bibliotekę `rembg`.
Pojawia się w panelu ustawień konwersji po poprawnej instalacji.

### Wymagania

- Python 3.10–3.12 (64-bit)
- Windows 10 / 11 (64-bit)
- Microsoft Visual C++ Redistributable 2019 lub nowszy
  ([pobierz tutaj](https://aka.ms/vs/17/release/vc_redist.x64.exe))

### Instalacja

**Krok 1** — zainstaluj `onnxruntime` i `rembg`:

```bat
pip install "icoforge[bgremove]"
```

lub bez wirtualnego środowiska:

```bat
pip install onnxruntime rembg
```

> Jeśli pojawi się błąd `Microsoft Visual C++ Redistributable is not installed`,
> pobierz i zainstaluj plik z linku powyżej, a następnie powtórz polecenie pip.

**Krok 2** — uruchom IcoForge. W panelu ustawień konwersji pojawi się sekcja
**"Usuwanie tła (AI)"** z checkboxem "Usuń tło (U2-Net)".

**Krok 3** — przy pierwszym użyciu checkboxa aplikacja automatycznie pobiera model
AI U2-Net (~170 MB) do katalogu `%USERPROFILE%\.u2net\`. Pobieranie odbywa się
jednorazowo — kolejne uruchomienia używają zapisanego modelu.

### Rozwiązywanie problemów

| Problem | Rozwiązanie |
|---------|-------------|
| Sekcja "Usuwanie tła (AI)" nie pojawia się | Sprawdź czy `pip install` przebiegło bez błędów: `python -c "import rembg"` |
| `DLL load failed` przy imporcie onnxruntime | Zainstaluj [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) |
| Błąd przy pierwszym użyciu (brak modelu) | Sprawdź połączenie internetowe; model pobierany jest z GitHub przy pierwszym uruchomieniu |
| `pip install` kończy się błędem kompilacji | Zainstaluj [Python 3.11 64-bit](https://www.python.org/downloads/) — onnxruntime wymaga 64-bit |

---

## Uruchomienie (dev)

```bash
# GUI
icoforge

# CLI — konwersja
icoforge-cli convert input.png output.ico --sizes 16,32,48,256

# CLI — optymalizacja
icoforge-cli optimize input.png --output input.min.png

# CLI — usuwanie tła
icoforge-cli convert input.png output.ico --sizes 256 --remove-bg
```

---

## Status projektu

| Faza | Opis | Stan |
|------|------|------|
| Faza 1 | MVP konwersji PNG → ICO | ✅ Ukończona |
| Faza 2 | Więcej formatów wejściowych | ✅ Ukończona |
| Faza 3 | Optymalizacja PNG | ✅ Ukończona |
| Faza 4 | Edytor pikselowy | ✅ Ukończona |
| Faza 5 | Tworzenie ICO od podstaw | ✅ Ukończona |
| Funkcje dodatkowe | AI bg removal, eksport ICNS/CUR/Favicon, lokalizacja, installer | ✅ Wdrożone |

Patrz [docs/ROADMAP.md](docs/ROADMAP.md) i [docs/FEATURES.md](docs/FEATURES.md).

---

## Licencja

MIT
