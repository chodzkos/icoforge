# Pierwsze kroki

## Setup repozytorium

```bash
# 1. Utwórz repo na GitHubie (możesz też przez gh CLI)
gh repo create icoforge --private --source=. --remote=origin

# 2. Zainicjuj git lokalnie
git init
git branch -M main
git add .
git commit -m "Initial scaffold"
git push -u origin main
```

## Środowisko deweloperskie

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# Skopiuj przykładowe ustawienia VS Code
cp .vscode/settings.example.json .vscode/settings.json
```

## Uruchomienie testów (powinny przechodzić "z pudełka")

```bash
pytest                    # konwertera (działa po fazie 1) + modeli (działa już teraz)
pytest tests/test_models.py
ruff check .
mypy src/
```

W skrypcie `cli.py` polecenie `convert` działa od razu po zainstalowaniu zależności – core PNG→ICO już jest, tylko trzeba uruchomić:

```bash
icoforge-cli convert input.png output.ico --sizes 16,32,48,256
```

## Praca z Claude Code

Claude Code automatycznie czyta `CLAUDE.md` przy starcie sesji. Sugerowany flow:

1. Otwórz folder w VS Code: `code icoforge/`
2. Uruchom Claude Code: `claude` (z folderu repo)
3. Podawaj zadania w jednostkach kroków z `docs/ROADMAP.md`. Przykład:

```
Zaimplementuj fazę 1 z ROADMAP, sekcja "Rdzeń". Pomijaj GUI, skup się tylko 
na core/. Przed implementacją pokaż mi plan w 5 punktach.
```

```
Dodaj test sprawdzający, że konwersja PNG bez kanału alpha z opcją 
background=#ffffff produkuje ICO z białym tłem zamiast czarnego. Najpierw test, 
potem ewentualna poprawka kodu.
```

```
Faza 3, oxipng. Zaimplementuj optimize_png z testem walidującym bezstratność 
(hash pikseli przed/po). Nie ruszaj CLI dopóki testy nie przejdą.
```

## Workflow git z Claude Code

- Twórz osobne branche na fazy: `feature/phase-1-core`, `feature/phase-3-optimizer`
- Claude Code może robić commity – ustaw mu mały zakres na sesję
- PRs przez `gh pr create` z czytelnym opisem (Claude Code zrobi to dobrze jeśli poprosisz)

## Częste pytania

**Czy potrzebuję Qt do uruchomienia testów core?**
Nie. Testy `core/` używają tylko Pillow. Qt jest tylko w `gui/` (faza 1+).

**Pillow narzeka na ICO sizes()?**
Pillow zmieniał API ICO między wersjami. Jeśli atrybut `ico.ico.sizes()` znika, użyj 
`ico.info["sizes"]` lub ręcznego parsowania nagłówka.

**Jak ograniczyć żeby Claude Code nie dodawał niepotrzebnych funkcji?**
W `CLAUDE.md` jest sekcja "Co NIE należy do tego projektu". Odsyłaj do niej.
