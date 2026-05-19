# Przewodnik startowy krok po kroku

*Zakładam że masz już zainstalowane: WSL2, VS Code z rozszerzeniem WSL,
Node.js w WSL, GitHub CLI i Claude Code. Jeśli nie – wróć do przewodnika
instalacji który był wcześniej przygotowany w tym czacie.*

---

## Część 1 – Jednorazowe przygotowanie projektu

### Krok 1 – Pobierz projekt

Pobierz plik `icoforge.zip` z czatu Claude na swój komputer Windows.

### Krok 2 – Otwórz terminal WSL

W VS Code: `Ctrl + `` ` (backtick, klawisz pod Escape).
Sprawdź że w terminalu widzisz prompt zaczynający się od `marcin@` lub podobny
(NIE od `C:\`). To oznacza że jesteś w WSL, nie w Windows.

### Krok 3 – Przenieś i rozpakuj

```bash
mkdir -p ~/projekty
cp /mnt/c/Users/<TWOJA_NAZWA_WINDOWS>/Downloads/icoforge.zip ~/projekty/
cd ~/projekty
unzip icoforge.zip
cd icoforge
```

*Zamień `<TWOJA_NAZWA_WINDOWS>` na swoją nazwę użytkownika Windows.*
*Możesz ją sprawdzić wpisując: `ls /mnt/c/Users/`*

### Krok 4 – Zainstaluj Python i zależności

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Pierwsze uruchomienie pobiera biblioteki z internetu – trwa 1–3 minuty.

Sprawdź że wszystko działa:
```bash
pytest tests/test_models.py -v
```
Powinno pokazać kilka linii z `PASSED` na zielono.

### Krok 5 – Otwórz projekt w VS Code

```bash
code .
```

VS Code otworzy się. W dolnym lewym rogu zobaczysz zielony napis
`WSL: Ubuntu` – to potwierdza połączenie z WSL.

Skopiuj przykładowe ustawienia VS Code:
```bash
cp .vscode/settings.example.json .vscode/settings.json
```

### Krok 6 – Utwórz repozytorium na GitHub

```bash
gh repo create icoforge --private --source=. --remote=origin --push
```

Jeśli pojawi się prośba o logowanie:
```bash
gh auth login
# wybierz: GitHub.com → HTTPS → Login with a web browser
```

Sprawdź: wejdź na `https://github.com/<TWÓJ_LOGIN>/icoforge` – powinny być pliki.

---

## Część 2 – Codzienne uruchamianie

Za każdym razem gdy siadasz do pracy:

```bash
cd ~/projekty/icoforge
source .venv/bin/activate
claude
```

---

## Część 3 – Pierwsze polecenie dla Claude Code

Wklej to jako pierwszą wiadomość:

```
Przeczytaj CLAUDE.md i docs/ROADMAP.md. Uruchom pytest i powiedz mi:
1. Co jest już zaimplementowane
2. Czy wszystkie testy przechodzą
3. Co zrobić jako następne według roadmapy
```

Następnie korzystaj z gotowych promptów z pliku `docs/PROMPTY.md`.

---

## Część 4 – Koniec pracy – zapis na GitHub

```bash
git add .
git commit -m "Opis tego co zrobiłeś"
git push
```

Albo poproś Claude Code: *„Zrób commit i push wszystkich zmian"*

---

## Najczęstsze problemy

**Brak `(.venv)` przed promptem:** uruchom `source .venv/bin/activate`

**VS Code nie widzi plików:** otwieraj przez `code .` z terminala WSL,
nie przez ikonę na pulpicie Windows

**Claude Code nie znajduje pliku:** sprawdź `pwd` – musisz być w `~/projekty/icoforge`

**Jak cofnąć zmiany Claude Code:**
```bash
git checkout -- .    # cofa wszystkie niezapisane zmiany
git log --oneline    # historia commitów
git revert HEAD      # cofa ostatni commit
```
