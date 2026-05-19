# Funkcje

Status: `[ ]` planowane, `[~]` w trakcie, `[x]` gotowe.

## Konwersja

- [ ] PNG → ICO (multi-resolution)
- [ ] Wybór rozdzielczości: 16, 20, 24, 32, 40, 48, 64, 96, 128, 256
- [ ] Wybór głębi bitowej: 8 / 24 / 32-bit per rozmiar
- [ ] Kanał alpha (RGBA) i przezroczystość
- [ ] Wybór algorytmu resamplingu per rozmiar
- [ ] JPG → ICO (z opcją tła dla braku alpha)
- [ ] BMP, GIF, WEBP, TIFF → ICO
- [ ] SVG → ICO (rasteryzacja per rozmiar)
- [ ] HEIC, AVIF → ICO (opcjonalny extra)
- [ ] Per-size source – inny plik źródłowy na każdy rozmiar
- [ ] Eksport ICNS (macOS)
- [ ] Eksport CUR / ANI (kursory Windows)
- [ ] Favicon preset (`.ico` + `.png` + manifest)

## Edytor

- [ ] Otwieranie istniejącego ICO
- [ ] Canvas z zoomem do 64x
- [ ] Siatka pikseli w zoomie >= 8x
- [ ] Tło w szachownicę dla przezroczystości
- [ ] Tab/lista dla każdego rozmiaru w ICO
- [ ] Ołówek (rozmiar 1–8)
- [ ] Gumka
- [ ] Wypełnianie (flood fill, z tolerancją)
- [ ] Kroplomierz (Alt jako shortcut)
- [ ] Linia
- [ ] Prostokąt (kontur i wypełniony)
- [ ] Zaznaczenie prostokątne
- [ ] Kopiuj / wklej / wytnij
- [ ] Undo / Redo (Ctrl+Z, Ctrl+Shift+Z)
- [ ] Paleta kolorów (podstawowy + zapasowy)
- [ ] Ekstrakcja palety z obrazu
- [ ] Zapis/wczytanie palety
- [ ] Synchronizacja warstw między rozmiarami (opcjonalna)
- [ ] Tworzenie ICO od zera (kreator)

## Optymalizacja PNG

- [ ] Bezstratna kompresja (oxipng)
- [ ] Tryb Zopfli (wolniejszy, mniejszy)
- [ ] Usuwanie metadanych (`tEXt`, `iTXt`, `zTXt`, `eXIf`, `tIME`)
- [ ] Walidacja bezstratności (hash pikseli)
- [ ] Batch processing (folder, glob)
- [ ] Raport oszczędności (przed / po, MB i %)
- [ ] Opcja in-place lub do nowego pliku

## Funkcje wspierające

- [ ] Drag & drop plików i folderów
- [ ] Podgląd ICO w 1:1 i powiększeniu
- [ ] Preset systeem (zapis konfiguracji jako JSON)
- [ ] CLI równolegle do GUI dla każdej funkcji
- [ ] Auto-trim przezroczystych obrzeży
- [ ] Wymuszanie aspektu (centrowanie z paddingiem)
- [ ] Ekstrakcja ikon z `.exe` / `.dll`
- [ ] Wsadowe usuwanie tła (rembg, opcjonalny extra)

## Interfejs i UX

- [ ] Ikona aplikacji (własna, stworzona w icoforge – ostateczny dogfooding)
- [ ] Tryb ciemny / jasny (auto-detekcja z systemu + ręczny przełącznik)
- [ ] Lokalizacja PL/EN (system tłumaczeń Qt – `tr()`)
- [ ] Lista ostatnio otwartych plików (Recent Files, max 10)
- [ ] Zapamiętywanie pozycji i rozmiaru okna między uruchomieniami
- [ ] Konfigurowalne skróty klawiszowe
- [ ] Toolbar z głównymi akcjami
- [ ] Pasek statusu z informacją o aktualnym pliku
- [ ] Powiadomienia systemowe po zakończeniu długich operacji
- [ ] Ekran "O programie" (About) z wersją i linkami

## Dystrybucja

- [ ] PyInstaller bundle dla Windows
- [ ] Nuitka jako alternatywa (mniejszy rozmiar)
- [ ] Installer Inno Setup
- [ ] AppImage dla Linux
- [ ] DMG dla macOS (jeśli ktoś będzie potrzebował)
- [ ] GitHub Actions: build releases na tag
