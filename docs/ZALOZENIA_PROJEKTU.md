# Założenia projektu IcoForge

*Dokument dla właściciela projektu. Opisuje co program robi, dlaczego tak,
i jak wygląda plan działania krok po kroku.*

---

## Co to jest IcoForge

IcoForge to desktopowy program dla systemu Windows (i Linux/macOS), który
rozwiązuje jeden konkretny problem: **tworzenie i edycja plików ikon (.ico)**.

Plik `.ico` to specjalny format używany przez Windows do wyświetlania ikon
aplikacji, folderów i skrótów. Jeden plik `.ico` zawiera w sobie kilka
wersji tej samej ikony w różnych rozmiarach (np. 16×16, 32×32, 256×256)
– Windows automatycznie dobiera właściwy rozmiar zależnie od kontekstu.

**Problem który rozwiązuje program:** brakuje prostego narzędzia które
łączy konwersję PNG→ICO, edycję pikseli i optymalizację PNG w jednym miejscu.
Istniejące narzędzia online są niskiej jakości albo płatne, a Photoshop/GIMP
to przesada do tworzenia ikon.

---

## Pełna lista funkcji

### Blok 1 – Konwersja plików graficznych → ICO
*Co widzi użytkownik: wrzucam plik PNG, wybieram rozmiary i opcje, dostaję .ico*

**Podstawowe (niezbędne do MVP):**
- Konwersja PNG → ICO
- Wybór które rozmiary ma zawierać plik: 16, 20, 24, 32, 40, 48, 64, 96, 128, 256 px
- Przezroczystość (kanał alpha) – ikona z przezroczystym tłem
- Wybór głębi kolorów: 32-bit (pełny kolor + alpha), 24-bit, 8-bit (256 kolorów)
- Podgląd wszystkich rozmiarów przed zapisem
- Przeciągnij i upuść plik (drag & drop)

**Algorytmy skalowania (wpływają na jakość małych ikon):**
- Lanczos – domyślny, najlepsza jakość dla zdjęć i ikon z gradientem
- Bicubic – szybszy, podobna jakość
- Nearest Neighbor – dla pixel artu (zachowuje ostre krawędzie, bez rozmycia)
- Box – najlepszy przy bardzo dużym zmniejszeniu (np. 256→16 px)
- Opcja: inny algorytm dla każdego rozmiaru osobno (np. Lanczos dla 256px, Nearest dla 16px)

**Formaty wejściowe (faza 2):**
- JPG/JPEG (bez przezroczystości – można wybrać kolor tła)
- BMP, GIF, TIFF, WEBP
- SVG (plik wektorowy – rasteryzowany osobno dla każdego rozmiaru, idealne bo wektor)
- HEIC, AVIF (nowoczesne formaty z telefonów)

**Per-size source (faza 2) – zaawansowana funkcja:**
- Możliwość wskazania osobnego pliku źródłowego dla każdego rozmiaru
- Przykład: 256px z detailsowa_ikona.png, 16px z uproszczona_ikona.png
- Kluczowe bo ikona 16×16 px często wymaga uproszczonej wersji

---

### Blok 2 – Optymalizacja PNG (bezstratna)
*Co widzi użytkownik: wrzucam PNG, dostaję mniejszy plik bez żadnej utraty jakości*

- Zmniejszenie rozmiaru pliku PNG bez zmiany ani jednego piksela
- Silnik optymalizacji: oxipng (bardzo szybki, napisany w Rust)
- Poziomy kompresji 0–6 (wyższy = mniejszy plik ale wolniej)
- Opcja Zopfli: maksymalna kompresja, daje dodatkowe 5-10%, ale wolno
- Usuwanie metadanych: dane GPS, data zdjęcia, informacje o aparacie, oprogramowaniu
- Walidacja bezstratności: program sprawdza że każdy piksel jest identyczny przed i po
- Raport: ile MB/KB zaoszczędzono, procentowo
- Wsad: optymalizacja całego folderu naraz

---

### Blok 3 – Edytor pikselowy
*Co widzi użytkownik: siatka pikseli, mogę malować, edytować, tworzyć ikon od zera*

**Canvas (płótno):**
- Widok powiększony do 64x (każdy piksel widoczny jako duży kwadrat)
- Siatka między pikselami (przy powiększeniu ≥ 8x)
- Szachownica w tle dla pikseli przezroczystych (standardowy wzór)
- Płynny zoom kółkiem myszy (Ctrl + scroll)
- Przewijanie płótna środkowym przyciskiem myszy

**Narzędzia:**
- Ołówek (rozmiar 1–8 px, rysuje pojedyncze piksele lub grubszą linię)
- Gumka (usuwa kolor, ustawia przezroczystość)
- Wypełnianie (wiadro farby – wypełnia obszar jednym kolorem, z progiem tolerancji)
- Kroplomierz (pipeta – pobiera kolor z klikniętego piksela; Alt jako skrót)
- Linia prosta
- Prostokąt (sam kontur lub wypełniony)
- Zaznaczenie prostokątne (wytnij, kopiuj, wklej fragment)

**Historia zmian:**
- Cofnij (Ctrl+Z) i ponów (Ctrl+Shift+Z)
- Historia przechowuje zmiany wydajnie (zapamiętuje tylko co zmieniło się, nie cały obraz)

**Kolory i paleta:**
- Kolor podstawowy i zapasowy (swap klawiszem X)
- Ekstrakcja dominujących kolorów z otwartego obrazu
- Zapis i wczytanie własnej palety kolorów

**Praca z plikiem ICO:**
- Każdy rozmiar w pliku ICO edytowany osobno (zakładki lub lista)
- Zapis z powrotem do pliku ICO

---

### Blok 4 – Tworzenie ICO od zera
*Co widzi użytkownik: zaczynam z pustą siatką, rysuję piksel po pikselu*

- Kreator nowego pliku: wybór rozmiarów które chcę zawrzeć
- Wybór koloru tła lub przezroczyste
- Opcja synchronizacji: edycja 32×32 automatycznie skopiuje (z downscalingiem) do 16×16
- Szablony startowe: pusty, wypełniony jednym kolorem, skopiowany z clipboardu

---

### Moje dodatkowe propozycje (wysoki priorytet)

**Eksport ICNS (ikony macOS):**
- Ten sam pipeline co ICO, tylko inny format pliku wyjściowego
- Przydatne dla programistów tworzących aplikacje cross-platform

**Kursory (.cur i .ani):**
- Format .cur to prawie to samo co .ico, tylko z dodatkowym "hotspot" (punkt kliknięcia)
- .ani to animowany kursor – seria klatek
- Bardzo mała ilość dodatkowej pracy, duża wartość

**Favicon preset (dla webdeveloperów):**
- Jeden klik → generuje favicon.ico (16, 32, 48px) + apple-touch-icon.png (180×180) + site.webmanifest
- To standardowy zestaw który każda strona WWW powinna mieć

**Auto-trim (przycinanie pustych krawędzi):**
- Automatyczne usuwanie przezroczystych pikseli z krawędzi obrazu
- Przykład: masz ikonę 256×256 ale właściwy rysunek zajmuje tylko środkowe 200×200

**Ekstrakcja ikon z plików Windows:**
- Wczytanie pliku .exe lub .dll i wyciągnięcie z nich ikon
- Każdy program Windows ma w sobie wbudowane ikony

**Batch processing (przetwarzanie wsadowe):**
- Folder z plikami PNG → folder z plikami ICO, wszystkie za jednym razem
- Raport: ile skonwertowano, ile błędów

**Presety konfiguracji:**
- Zapisz aktualne ustawienia jako "Windows App Icon" albo "Favicon Set"
- Wczytaj preset jednym kliknięciem

**CLI (interfejs wiersza poleceń):**
- Wszystkie funkcje dostępne też z terminala (bez graficznego interfejsu)
- Do skryptowania, automatyzacji, integracji z innymi narzędziami
- Przykład: `icoforge-cli convert logo.png output.ico --sizes 16,32,48,256`

---

### Propozycje niskopriorytowe (warto mieć, ale nie na start)

- Usuwanie tła automatycznie (AI, biblioteka rembg)
- Sharpening (wyostrzanie) dla małych rozmiarów
- Generowanie wariantu ciemnego (dark mode) ikony
- Eksport spritesheet (wiele ikon w jednym PNG)
- Historia ostatnich plików
- Instalator Windows (.exe)

---

## Technologie – co i po co

Wszystko napisane w **Pythonie** – język programowania który jest czytelny,
ma ogromną ilość gotowych bibliotek i dobrze sprawdza się w aplikacjach desktopowych.

| Biblioteka | Do czego służy | Dlaczego ta a nie inna |
|---|---|---|
| **PySide6** | Tworzy okienka, przyciski, menu | Licencja LGPL (bezpłatna nawet w produktach komercyjnych), oficjalny Qt dla Pythona |
| **Pillow** | Operacje na obrazach: resize, konwersja formatów | Standard branżowy, obsługuje dziesiątki formatów |
| **numpy** | Szybkie operacje na tablicach pikseli | Pillow sam w sobie jest wolny przy edycji piksel po pikselu |
| **pyoxipng** | Optymalizacja PNG | Wrapper Pythona na oxipng (napisany w Rust – szybki), bez potrzeby instalowania zewnętrznych programów |
| **click** | Interfejs wiersza poleceń | Prostszy i czytelniejszy niż wbudowany argparse |
| **pytest** | Automatyczne testy | Standard w projektach Pythona |
| **ruff** | Sprawdzanie jakości kodu | Zastępuje 3 narzędzia jednym, 10x szybszy od poprzedników |

---

## Etapy tworzenia – ocena trudności

### Faza 1 – Działający konwerter PNG→ICO (3–5 dni roboczych Claude Code)
**Trudność: łatwa**

Pillow obsługuje ICO natywnie. Cała praca to:
1. Modele danych (konfiguracja konwersji)
2. Logika konwersji z opcjami
3. CLI z podstawowymi flagami
4. Testy automatyczne
5. Minimalny GUI: wrzuć plik, wybierz rozmiary, zapisz

Efekt końcowy: działający program który zastępuje konwertery online.

---

### Faza 2 – Więcej formatów wejściowych (2–3 dni)
**Trudność: łatwa/średnia**

JPG/BMP/GIF/WEBP/TIFF przez Pillow – minimalny wysiłek.
SVG wymaga dodatkowej biblioteki (cairosvg lub resvg) – chwila konfiguracji.
HEIC/AVIF – opcjonalny plugin.
Per-size source – rozszerzenie konfiguracji.

---

### Faza 3 – Optymalizacja PNG (2–3 dni)
**Trudność: średnia**

Integracja z pyoxipng, własny parser chunków PNG do usuwania metadanych,
walidacja bezstratności, batch processing.
Najtrudniejsze: parser PNG (format binarny), ale dobrze udokumentowany.

---

### Faza 4 – Edytor pikselowy (2–3 tygodnie)
**Trudność: trudna**

Największy etap. Wymaga:
- Canvas z QGraphicsView (Qt) – kilka dni samo w sobie
- System narzędzi z undo/redo – tydzień
- Paleta kolorów, interfejs
- Testy (edytor trudno testować automatycznie)

Warto podzielić na pod-fazy i testować każde narzędzie osobno.

---

### Faza 5 – Tworzenie ICO od zera (3–5 dni po fazie 4)
**Trudność: średnia** (edytor już istnieje, to rozszerzenie)

---

## Ocena komercyjna

Program ma potencjał komercyjny jako:
- Jednorazowy zakup (np. 15–30 USD) – najprostsze
- Freemium: podstawowa konwersja bezpłatna, edytor i batch płatne
- Licencja dla firm (site license)

Licencja MIT kodu własnego pozwala na pełną komercjalizację.
PySide6 (LGPL) nie stanowi przeszkody przy dystrybucji jako instalator Windows.

---

## Priorytety według wartości dla użytkownika

Malejąco – co daje największą wartość przy najmniejszym wysiłku:

1. **Konwersja PNG→ICO** (faza 1) – rozwiązuje główny problem od razu
2. **CLI** (równolegle z fazą 1) – darmowy test API, przydatny dla programistów
3. **Batch processing** (po fazie 1) – ogromna wartość, mały wysiłek
4. **Więcej formatów** (faza 2) – JPG i SVG to realne potrzeby
5. **Favicon preset** – jeden przycisk, ogromna wartość dla webdeveloperów
6. **Optymalizacja PNG** (faza 3) – przydatna, ale osobna funkcja
7. **Edytor pikselowy** (faza 4) – wyróżnik produktu, ale dużo pracy
