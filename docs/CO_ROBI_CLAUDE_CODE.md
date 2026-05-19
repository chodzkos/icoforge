# Co robi Claude Code, a co robię ja

---

## Ty robisz to (jednorazowo, na początku)

Czynności które musisz wykonać osobiście, bo wymagają Twojego konta,
Twoich decyzji lub kliknięcia w graficzny interfejs.

### ✅ Krok 1 – Pobierz i rozpakuj projekt

1. Pobierz plik `icoforge.zip` z czatu Claude
2. Otwórz terminal WSL (w VS Code: Ctrl+` lub z menu Terminal → New Terminal)
3. Wpisz komendy:

```bash
mkdir -p ~/projekty
cp /mnt/c/Users/<TWOJA_NAZWA>/Downloads/icoforge.zip ~/projekty/
cd ~/projekty
unzip icoforge.zip
cd icoforge
```

*Zamień `<TWOJA_NAZWA>` na swoją nazwę użytkownika Windows.*
*Jeśli pobierasz do innego folderu, zmień ścieżkę odpowiednio.*

---

### ✅ Krok 2 – Zainstaluj zależności Pythona

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

To instaluje wszystkie biblioteki potrzebne do uruchomienia projektu.
Trwa 1–3 minuty przy pierwszym uruchomieniu.

Sprawdź że działa:
```bash
pytest tests/test_models.py -v
```
Powinno pokazać zielone „passed".

---

### ✅ Krok 3 – Utwórz repozytorium na GitHub

Masz dwie opcje:

**Opcja A – przez stronę (prościej):**
1. Wejdź na github.com i zaloguj się
2. Kliknij zielony przycisk „New" (nowe repozytorium)
3. Nazwa: `icoforge`
4. Wybierz Private (prywatne) lub Public
5. **NIE zaznaczaj** „Initialize with README" (mamy już swój)
6. Kliknij „Create repository"
7. GitHub pokaże Ci komendy – skopiuj sekcję „push an existing repository"

**Opcja B – przez terminal (szybciej, jeśli masz gh CLI):**
```bash
gh repo create icoforge --private --source=. --remote=origin --push
```

---

### ✅ Krok 4 – Wypchnij kod na GitHub

Jeśli wybrałeś Opcję A w kroku 3:

```bash
cd ~/projekty/icoforge
git init
git add .
git commit -m "Initial project scaffold"
git branch -M main
git remote add origin https://github.com/<TWOJA_NAZWA>/icoforge.git
git push -u origin main
```

*Zamień `<TWOJA_NAZWA>` na swoją nazwę użytkownika GitHub.*

---

### ✅ Krok 5 – Otwórz projekt w VS Code

```bash
cd ~/projekty/icoforge
code .
```

VS Code otworzy się z zieloną ikonką „WSL: Ubuntu" na dole po lewej.
To potwierdza że wszystko jest połączone prawidłowo.

Skopiuj ustawienia VS Code:
```bash
cp .vscode/settings.example.json .vscode/settings.json
```

---

### ✅ Krok 6 – Uruchom Claude Code i zacznij pracę

W terminalu VS Code (który jest terminalem WSL):

```bash
claude
```

Przy pierwszym uruchomieniu otworzy się przeglądarka – zaloguj się na konto Anthropic.
Po zalogowaniu wróć do terminala.

**I to wszystko co musisz zrobić osobiście.**

---

## Claude Code robi to (wszystko pozostałe)

Kiedy napiszesz polecenie w sesji Claude Code, on sam:

### Implementacja funkcji
- Pisze cały kod Pythona
- Tworzy nowe pliki i moduły
- Rozbudowuje istniejące funkcje
- Implementuje algorytmy (skalowanie, detekcja struktury, itp.)

### Testy
- Pisze testy automatyczne dla każdej nowej funkcji
- Naprawia testy które przestały działać
- Sprawdza czy wszystkie testy przechodzą

### Naprawianie błędów
- Analizuje komunikaty błędów
- Znajdzie i naprawi bug
- Wyjaśni co poszło nie tak

### Jakość kodu
- Uruchamia `ruff` (sprawdzanie stylu kodu)
- Uruchamia `mypy` (sprawdzanie typów)
- Poprawia wszystkie ostrzeżenia

### Git
- Robi commity z sensownymi opisami
- Tworzy nowe gałęzie (branches) dla nowych funkcji
- Może otworzyć Pull Request

### Dokumentacja
- Aktualizuje ROADMAP.md gdy coś ukończy
- Pisze docstringi (opisy funkcji w kodzie)
- Aktualizuje README

---

## Jak rozmawiać z Claude Code

Claude Code rozumie naturalny język (po polsku też). Nie musisz znać komend.

**Dobre polecenia:**

```
Zaimplementuj fazę 1 z ROADMAP.md. Zacznij od modeli danych 
w core/models.py. Przed napisaniem kodu pokaż mi plan.
```

```
Coś nie działa - dostaję błąd: [wklej treść błędu]. Napraw to.
```

```
Dodaj obsługę drag & drop do głównego okna GUI. 
Użytkownik powinien móc przeciągnąć plik PNG na okno aplikacji.
```

```
Napisz testy dla funkcji convert() w core/converter.py. 
Sprawdź szczególnie przypadek gdy plik wejściowy nie istnieje.
```

```
Zrób commit ze zmianami które zrobiłeś w tej sesji. 
Użyj opisowego komunikatu po angielsku.
```

**Wskazówki:**
- Im bardziej konkretne polecenie, tym lepszy wynik
- Możesz poprosić o wyjaśnienie zanim coś zrobi: „wyjaśnij co zamierzasz zrobić"
- Możesz powiedzieć „zatrzymaj się i pokaż mi kod zanim go zapiszesz"
- Jeśli wynik Ci się nie podoba: „to nie to – chciałem żeby..."

---

## Codzienny rytm pracy

```
1. Otwórz terminal WSL w VS Code
2. cd ~/projekty/icoforge
3. source .venv/bin/activate    (aktywuj środowisko Pythona)
4. claude                        (uruchom Claude Code)
5. Wpisz co chcesz zrobić dziś
6. Po zakończeniu: git push      (wypchnij zmiany na GitHub)
```

---

## Kiedy coś pójdzie nie tak

**„Testy nie przechodzą":**
```
Uruchom pytest i pokaż mi błędy. Napraw je.
```

**„Nie wiem jak to opisać słowami":**
Zrób zrzut ekranu (Print Screen) i wklej do czatu Claude Code
(od wersji 1.0.93+ obsługuje obrazy przez Alt+V).

**„Claude Code zrobił coś czego nie chciałem":**
```
Cofnij ostatnie zmiany. Użyj git checkout -- . żeby przywrócić poprzedni stan.
```

**„Nie wiem od czego zacząć":**
```
Przeczytaj CLAUDE.md i docs/ROADMAP.md. 
Co powinienem zaimplementować w pierwszej kolejności?
```
