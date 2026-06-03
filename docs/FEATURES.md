# Funkcje

Status: `[ ]` planowane, `[~]` w trakcie, `[x]` gotowe.

## Konwersja

- [x] PNG → ICO (multi-resolution)
- [x] Wybór rozdzielczości: 16, 20, 24, 32, 40, 48, 64, 96, 128, 256
- [x] Wybor glebosci bitowej: 8 / 24 / 32-bit per rozmiar (rzeczywisty tryb PNG: P / RGB / RGBA)
- [x] Kanał alpha (RGBA) i przezroczystość
- [x] Wybór algorytmu resamplingu per rozmiar
- [x] JPG → ICO (z opcją tła dla braku alpha)
- [x] BMP, GIF, WEBP, TIFF → ICO
- [x] SVG → ICO (rasteryzacja per rozmiar, resvg-py lub cairosvg; honoruje remove_bg, auto_trim, preserve_aspect)
- [x] HEIC, AVIF → ICO (opcjonalny extra `pillow-heif`)
- [x] Per-size source – inny plik źródłowy na każdy rozmiar
- [x] Eksport ICNS (macOS)
- [x] Eksport CUR (kursory Windows)
- [x] Favicon preset (`.ico` + `apple-touch-icon` + manifest PWA)
- [x] Auto-trim przezroczystych obrzeży
- [x] Ekstrakcja ikon z `.exe` / `.dll` (`pefile`)
- [x] Usuwanie tła AI (rembg / U2-Net, opcjonalny extra)

## Edytor

- [x] Otwieranie istniejącego ICO
- [x] Canvas z zoomem do 64×
- [x] Siatka pikseli w zoomie ≥ 8×
- [x] Tło w szachownicę dla przezroczystości
- [x] Tab / lista dla każdego rozmiaru w ICO
- [x] Ołówek (rozmiar 1–8)
- [x] Gumka
- [x] Wypełnianie (flood fill, z tolerancją)
- [x] Kroplomierz (Alt jako skrót)
- [x] Linia (algorytm Bresenhama)
- [x] Prostokąt (kontur i wypełniony)
- [x] Zaznaczenie prostokątne (marching ants)
- [x] Kopiuj / wklej / wytnij
- [x] Undo / Redo (Ctrl+Z, Ctrl+Shift+Z)
- [x] Paleta kolorów (pierwszoplanowy + tła, swap X, reset D)
- [x] Ekstrakcja palety z obrazu
- [x] Zapis / wczytanie palety (JSON)
- [x] Synchronizacja warstw między rozmiarami (opcjonalna)
- [x] Tworzenie ICO od zera (kreator z wyborem rozmiarów i tła)

## Optymalizacja PNG

- [x] Bezstratna kompresja (oxipng, poziomy 0–6)
- [x] Tryb Zopfli (wolniejszy, mniejszy)
- [x] Usuwanie metadanych (`tEXt`, `iTXt`, `zTXt`, `eXIf`, `tIME`)
- [x] Walidacja bezstratności (hash pikseli)
- [x] Batch processing (folder, glob)
- [x] Raport oszczędności (przed / po, MB i %)
- [x] Domyslny bezpieczny zapis jako <stem>.min.png (zrodlo nienaruszone); --in-place nadpisuje, --output wskazuje sciezke

## Funkcje wspierające

- [x] Drag & drop plików i folderów
- [x] Podgląd ICO w 1:1 i powiększeniu
- [x] Preset system (zapis konfiguracji jako JSON; wbudowane + użytkownika, import/eksport, domyslny preset)
- [x] CLI równolegle do GUI dla każdej funkcji
- [x] Wymuszanie aspektu (centrowanie z paddingiem)

## Interfejs i UX

- [x] Ikona aplikacji
- [x] Tryb ciemny / jasny (Widok -> Motyw: Automatyczny / Ciemny / Jasny; auto-detekcja z systemu, zapis w settings.json)
- [x] Lokalizacja PL/EN (system tłumaczeń Qt — `tr()`)
- [x] Lista ostatnio otwartych plikow (Recent Files, max 10)
- [x] Zapamietywanie pozycji i rozmiaru okna miedzy uruchomieniami
- [ ] Konfigurowalne skróty klawiszowe
- [x] Toolbar z głównymi akcjami
- [x] Pasek statusu z informacją o aktualnym pliku
- [ ] Powiadomienia systemowe po zakończeniu długich operacji
- [x] Ekran "O programie" z logo

## Dystrybucja

- [x] PyInstaller bundle dla Windows (onedir + portable ZIP)
- [x] Bundlowanie Cairo DLL dla wsparcia SVG (cairosvg) w paczce Windows
- [ ] Nuitka jako alternatywa (mniejszy rozmiar)
- [x] Installer Inno Setup
- [ ] AppImage dla Linux
- [ ] DMG dla macOS
- [x] GitHub Actions: build i release na tag (`v*.*.*`)
