# Audyt migracji IcoForge → chodzkos-gui-kit 0.5.3

> **Cel:** jedna kanoniczna implementacja komponentów GUI w kicie; IcoForge tylko
> importuje. Punkt odniesienia: przejścia pdf2md i EpubForge.
> **Zakres tego dokumentu:** PROMPT A (inwentaryzacja + tabela mapowania). Zero
> zmian w `src/`. Plan fal migracji = PROMPT B (po akceptacji tabeli).

Data: 2026-07-17 · gui-kit: **0.5.3** (potwierdzone z kodu:
`uv run python -c "import chodzkos_gui_kit; print(__version__)"` → `0.5.3`).

---

## 0a. Co oferuje gui-kit 0.5.3 (z kodu, nie z pamięci)

Publiczne API (z `qt/__init__.py`, `qt/widgets/__init__.py`, `config.py`):

### Motyw — `chodzkos_gui_kit.qt.theme`
| Symbol | Sygnatura | Uwaga |
|---|---|---|
| `apply_theme` | `apply_theme(app, palette, *, repaint_item_views=True)` | **Kanoniczna sekwencja §4**: `setStyle("Fusion")` → `setPalette` → `setStyleSheet(build_qss)` → **`QToolTip.setPalette`** → `_repolish` (unpolish/polish/update + item-views) → `set_current_palette`. |
| `build_palette` | `build_palette(palette) -> QPalette` | |
| `build_qss` | `build_qss(palette) -> str` | QSS = funkcja palety (bez cache). |
| `ThemeManager` | `ThemeManager(app, config: MutableMapping[str, Any])` | Sygnał `theme_changed(Palette)`. Metody: `apply(setting)`, `resolved_name(setting=None)`, `attach_titlebar(window)`; property `setting`/`palette`. Persist przez `config["theme"]`. DWM belek **bezwarunkowo** przy każdym `apply()` dla okien dołączonych `attach_titlebar`. |
| `ThemeSetting`/`ThemeName` | `"auto"/"light"/"dark"` / `"light"/"dark"` | |
| `current_palette` / `set_current_palette` | | Paleta modułowa (czytana przez ikony). |
| `mode_of` / `system_scheme` | `mode_of(palette)->ThemeName` / `system_scheme()->ThemeName` | `Unknown → dark`. |

### Pasek tytułu — `chodzkos_gui_kit.qt.titlebar` + `winutil.dwm`
| Symbol | Sygnatura | Uwaga |
|---|---|---|
| `set_titlebar_dark` | `set_titlebar_dark(window, dark)` | `int(winId())` → `winutil.dwm.set_titlebar`. |
| `sync_titlebar` | `sync_titlebar(window, mode)` | Bezwarunkowo wg motywu app (v2.5). |
| `TitlebarSync` | `TitlebarSync(window, mode_getter: Callable[[],ThemeName])` | Filtr zdarzeń: re-aplikuje DWM na `Show` **i `ActivationChange`**. |
| `winutil.dwm.set_titlebar` | `set_titlebar(hwnd: int, dark)` | Czysty ctypes, **zero Qt/tk**. HWND pointer-sized (`argtypes`, brak truncacji Win64). Redraw ramki: `SetWindowPos(FRAMECHANGED)` + `WM_NCACTIVATE 0→1` + `RedrawWindow(RDW_FRAME|RDW_ALLCHILDREN|RDW_ERASE…)`. No-op poza Windows. |

### Ikony — `chodzkos_gui_kit.qt.icons`
| Symbol | Sygnatura | Uwaga |
|---|---|---|
| `get_icon` | `get_icon(name, color=None, size=20) -> QIcon` | Przebarwialne SVG Lucide; token palety (`fg` domyślnie, `accent_text`…); cache `(name,hex,size)`. **Ekstrakcja z IcoForge** (v0.3). |
| `clear_cache` | `clear_cache()` | Wołać na zmianę motywu. |
| `ICON_MAP` | `dict[str,str]` | akcja → plik SVG; 21 ikon Lucide w `assets/icons/`. |

### Dialogi plików — `chodzkos_gui_kit.qt.dialogs`
`open_file` / `open_files` / `save_file(*, initial_name=None)` / `pick_dir` /
`use_native_dialog(app_mode, system)`. **Reguła rozjazdu symetryczna**: natywny
gdy `app_mode == system`, inaczej fallback Qt (`DontUseNativeDialog`) z ciemną
belką DWM, sidebarem (Pulpit/Dokumenty/Pobrane/dyski/ostatni katalog), widokiem
Detail, zapamiętanym rozmiarem okna i per-widget QSS na przyciski toolbara (v2.6).
`config: DialogConfig = MutableMapping` (opcjonalny).

### Widgety — `chodzkos_gui_kit.qt.widgets`
| Widget | Sygnatura konstruktora / kluczowe API |
|---|---|
| `HelpWindow` | `HelpWindow(parent=None, *, title="Help", tabs: list[tuple[str,str]] \| None=None)` + `add_html_section(title, html)` + **`add_markdown_section(title, source: str \| Path)`** (0.5.3). Re-render na `PaletteChange`. Bez persystencji geometrii. |
| `help_html` | `section`/`paragraph`/`unordered_list`/`table`/`code`/`preformatted` (kolory przez `palette(...)`; `code`/`preformatted`/`table` escapują wejście — v0.5.1). |
| `FileList` | `FileList(...)` + `FileListTexts`; toolbar +Files/+Folder/Remove/Clear, D&D, sygnały `files_changed`/`selection_changed`. |
| `PathEntry` | `PathEntry(...)` + `PathEntryTexts`/`PathMode`/`FileTypes`; `get()`/`set()`, `path_changed`, `remember_key`. |
| `LogView` | `LogView(...)`; `append_line(text, level)`, `log_info/warning/error`, `set_theme(palette)`, 5 poziomów→role palety. |
| `make_scrollable` | `make_scrollable(content: QWidget) -> QScrollArea` (0.5.2). Pionowy bezramkowy scroll; tło zostawione motywowi. |

### Konfiguracja — `chodzkos_gui_kit.config` (warstwa 0, czysty Python + platformdirs)
| Symbol | Sygnatura / zachowanie |
|---|---|
| `config_dir` | `config_dir(app_name) -> Path`. Portable = frozen + marker **`portable.flag`** obok exe → **katalog obok exe**. Inaczej `platformdirs.user_config_dir(app_name, appauthor=False, roaming=True)`. |
| `Config` | `Config(app_name, *, path=None, on_dirty=None)` — podtyp `dict`; **atomowy zapis** (tmp+`os.replace`); **kopia uszkodzonego** `config.json.broken-<ts>`; `mark_dirty`/`flush`/`save_now`, hak `on_dirty` pod debounce. Plik `config.json`. |
| `load_config`/`save_config` | funkcyjne odpowiedniki (JSON, atomowo, backup przy `JSONDecodeError`). |
| `PORTABLE_MARKER` | `"portable.flag"`. |

**Czego BRAK w 0.5.3** (istotne dla IcoForge): `AboutPanel` (kandydat ROADMAP),
`LogStreamer` (jest tylko `LogView`), `Section`/`Checkbox`/`Tooltip` jako widgety
(kandydaci), helper „resource path/_MEIPASS", helper stanu okna, „recent files",
sprawdzanie aktualizacji (`version_check`), event-filter tłumiący `WM_NCACTIVATE`.

### CHANGELOG 0.5.1 → 0.5.3 (co doszło od pinu IcoForge = 0.5.2)
- **0.5.1** — single-source wersji przez `importlib.metadata`; kopia uszkodzonego
  `config.json` → `.broken-<ts>`; escaping `help_html` (`code`/`preformatted`/`table`);
  pointer-sized ctypes `GetParent` (tk).
- **0.5.2** — `make_scrollable` *(IcoForge już migrowany — PR #19)*.
- **0.5.3** — `HelpWindow.add_markdown_section` / `add_html_section` („jeden plik
  prawdy" z `docs/*.md`); GUI_STANDARD → v2.15 (docs).

---

## 0b. Co ma lokalnie IcoForge (z kodu)

**Już migrowane do kitu** (lokalnie zostały tylko miejsca wywołań / treść):
palety hex → `palette.DARK/LIGHT`; `apply_theme`; dialogi plików
(`qt.dialogs` — 8 miejsc); belka DWM (`set_titlebar_dark` — main/editor/new_ico);
`IconProvider` (`qt.icons.get_icon`/`clear_cache`); `HelpWindow`; `make_scrollable`.
Brak lokalnych `QFileDialog`/`DontUseNativeDialog`, brak lokalnego `QToolTip`,
brak lokalnego `DwmSetWindowAttribute` (poza event-filterem — patrz niżej).

**Pozostało lokalnie:**
| Plik | Symbole publiczne |
|---|---|
| `utils/theme.py` | `ThemeManager(app)` (sygnał `theme_changed(str)`), `apply`/`restore`/`current_resolved`/`current_setting`; `init_theme_manager`/`get_theme_manager` (singleton). |
| `utils/window_theme.py` | `apply_theme_to_dialog(dialog, theme_manager)`. |
| `utils/native_event_filter.py` | `TitlebarEventFilter` (WM_NCACTIVATE). |
| `utils/paths.py` | `get_resource_path(relative)`, `get_settings_dir()`. |
| `utils/settings.py` | `get_setting`/`save_setting`/`get_language`/`set_language`. |
| `utils/recent_files.py` | `load_recent`/`save_recent`/`add_recent`/`remove_missing`. |
| `utils/window_state.py` | `save_window_state`/`restore_window_state`. |
| `utils/version_check.py` | `get_installed_version`/`get_latest_release_version`/`is_update_available`. |
| `utils/python_finder.py` | `find_python()`. |
| `gui/help_window.py` | `HELP_TITLE`, `help_tabs()` (treść zakładek). |

---

## 0c. Zależności i zasoby
- **Pin:** `pyproject.toml` →
  `chodzkos-gui-kit[qt] @ git+…@12c6b30cfa8f4c00f21b31c583cd70e70b0d1379  # v0.5.2`.
  Zgodny z konwencją „SHA + komentarz wersji" (CLAUDE.md kitu). **Do bumpu na
  0.5.3** — release commit `bb40fa6` (bump `version="0.5.3"` + `add_markdown_section`).
- **PyInstaller (`icoforge.spec`):** `copy_metadata("icoforge")` +
  `collect_data_files("chodzkos_gui_kit")` (assets/ikony kitu + `LICENSE-icons` +
  `py.typed`) + katalog `assets/` aplikacji. Ikony kitu **wchodzą** do bundla przez
  `importlib.resources`. Portable vs instalator: różni je tylko marker (patrz 0f).

---

## 0d. Tabela mapowania (bramka PROMPT B)

Werdykty: **ZASTĄP** (kit ma pełny odpowiednik) · **ZASTĄP+PR** (lokalne ma
poprawkę/feature, których kit nie ma → najpierw PR do kitu) · **ZOSTAW**
(specyficzne dla IcoForge) · **ROZSTRZYGNIJ** (częściowe pokrycie / decyzja).

| # | Obszar | IcoForge (plik, klasa/fn) | gui-kit 0.5.3 (moduł, API) | Werdykt |
|---|---|---|---|---|
| 1 | Silnik motywu (Fusion+paleta+QSS+`QToolTip`+kolejność apply+repaint item-views) | `utils/theme.py` → woła `apply_theme` | `qt.theme.apply_theme` | **ZASTĄP** — *już zrobione*; lokalnie tylko wywołanie. |
| 2 | Palety (hexy) | — (brak lokalnych hexów) | `palette.DARK/LIGHT` | **ZASTĄP** — *już zrobione*. |
| 3 | `ThemeManager` (orkiestracja trybu, sygnał, singleton, persist) | `utils/theme.py:ThemeManager` | `qt.theme.ThemeManager` | **ROZSTRZYGNIJ** — pokrycie częściowe, rozjazd API (patrz §Sygnatury). |
| 4 | Belka DWM (marshaling HWND, WM_NCACTIVATE+RedrawWindow, Win10/Win11) | `set_titlebar_dark` w main/editor/new_ico | `qt.titlebar.set_titlebar_dark` / `winutil.dwm` | **ZASTĄP** — *już zrobione* (nasza „walka o Win10" wcześniej weszła do kitu: 0.3.2/0.3.3/0.4.3). |
| 5 | Sync belki dialogów przy pokazaniu/aktywacji | `utils/window_theme.py:apply_theme_to_dialog` (+`QTimer.singleShot(0)`) | `qt.titlebar.TitlebarSync` / `ThemeManager.attach_titlebar` | **ROZSTRZYGNIJ** — kit ma czystszy odpowiednik (deferral przez `Show`), ale adopcja zależy od #3. |
| 6 | Tłumienie `WM_NCACTIVATE` (belka „aktywna" gdy otwarty dialog) | `utils/native_event_filter.py:TitlebarEventFilter` | `qt.titlebar.TitlebarSync` (re-aplikacja na `ActivationChange`) | **ZASTĄP** — **kod jest martwy** (nigdzie `installNativeEventFilter`); kit rozwiązuje ten sam scenariusz inną strategią. Migracja = usunięcie pliku, zero call-site. |
| 7 | Ikony (`get_icon`/`clear_cache`/`ICON_MAP`/cache/color-resolver) | `qt.icons` (import) | `qt.icons` | **ZASTĄP** — *już zrobione* (kit = ekstrakcja z IcoForge). |
| 8 | Dialogi plików (rozjazd, fallback sidebar/Detail/rozmiar/QSS) | `qt.dialogs` (8 miejsc) | `qt.dialogs` | **ZASTĄP** — *już zrobione*. |
| 9 | `HelpWindow` (zakładki, re-render, belka) | `qt.widgets.HelpWindow` (import) + `gui/help_window.py` (treść) | `qt.widgets.HelpWindow` | **ZASTĄP** okna — *zrobione*; treść → wiersz 10. |
| 10 | Treść pomocy | `gui/help_window.py:help_tabs()` (HTML kitowymi helperami) | `help_html` + `add_markdown_section` | **ZOSTAW** — treść jest wiedzą o IcoForge; markdown-„jeden plik prawdy" ma tu **niską wartość** (patrz 0e). |
| 11 | `make_scrollable` | `qt.widgets.make_scrollable` (import) | `qt.widgets.make_scrollable` | **ZASTĄP** — *już zrobione* (PR #19). |
| 12 | Katalog konfiguracji + portable | `utils/paths.py:get_settings_dir` | `config.config_dir` | **ROZSTRZYGNIJ** — rozjazd marker/ścieżek + ryzyko migracji danych (patrz §Sygnatury, 0f). |
| 13 | Persystencja ustawień (klucz-wartość) | `utils/settings.py` | `config.Config` | **ZASTĄP** — kit to nadzbiór (atomowy zapis, backup, debounce); migracja musi ujednolicić 3 pisarzy tego samego `settings.json` (patrz §Sygnatury). |
| 14 | `get_resource_path` (`_MEIPASS`, assets aplikacji) | `utils/paths.py:get_resource_path` | — (brak) | **ZOSTAW** — assets aplikacji (`.ico`, logo); kit pakuje własne zasoby wewnętrznie. |
| 15 | Ostatnio otwierane pliki | `utils/recent_files.py` | — (brak) | **ZOSTAW** — jedzie na wspólny `Config` po #13. |
| 16 | Stan/geometria okna | `utils/window_state.py` | — (`HelpWindow` świadomie NIE persystuje geometrii) | **ZOSTAW** — jedzie na wspólny `Config` po #13. |
| 17 | „O programie" + sprawdzanie aktualizacji | `utils/version_check.py` + `main_window._on_about` | — (`AboutPanel` = kandydat ROADMAP) | **ZOSTAW** (dziś) → **ZASTĄP+PR** gdy kit wyda `AboutPanel` (kontrybucja update-check; wzorzec single-source wersji już zgodny). |
| 18 | Szukanie interpretera Pythona (dla rembg) | `utils/python_finder.py` + `gui/ai_installer.py` + `core/bg_remover.py` | — (brak) | **ZOSTAW** — specyficzne dla IcoForge (subprocess-izolacja rembg). |
| 19 | Edytor pikseli, canvas, konwerter, ICO/CUR/ICNS, optymalizator, presety | `core/*`, `gui/editor/*`, `gui/widgets/*` | — | **ZOSTAW** — domena IcoForge. |

### Różnice sygnatur (wejście do planu fal PROMPT B)

**#3 `ThemeManager`** — realny rozjazd kontraktu:
| | IcoForge | gui-kit 0.5.3 |
|---|---|---|
| konstruktor | `ThemeManager(app)` | `ThemeManager(app, config: MutableMapping)` |
| sygnał | `theme_changed(str)` `"dark"/"light"` | `theme_changed(Palette)` |
| zmiana motywu | `apply(theme: str)` + `restore()` | `apply(setting: ThemeSetting)` (bez `restore` — stan początkowy czytany w `__init__`) |
| odczyt | `current_resolved()`→str, `current_setting()`→str | `resolved_name()`→ThemeName, property `setting`/`palette` |
| persist | `utils/settings` (`"theme"`) | `config["theme"]` |
| ikony | `apply` sam woła `clear_cache()` | konsument: `theme_changed.connect(clear_cache)` |
| belki | ręcznie w każdym oknie | `attach_titlebar(window)` (DWM bezwarunkowo przy `apply`) |
| dostęp | singleton `init/get_theme_manager` | zwykły obiekt (wstrzykiwany) |

**Miejsca wywołań do zmiany:** sloty `theme_changed` (str→Palette lub adapter):
`main_window` (×2 connect), `editor_window` (×2), `canvas`, `settings_panel`;
oraz wszystkie `mgr.current_resolved()` (main×3, editor×3, new_ico). Migracja #3
pociąga #5 (belki przez `attach_titlebar`) i #13 (potrzebny `config` MutableMapping).

**#12/#13 `paths`/`settings` → `config`** — rozjazd i ryzyko danych:
| | IcoForge | gui-kit 0.5.3 |
|---|---|---|
| marker portable | `portable.txt` | `portable.flag` |
| lokalizacja portable | `exe/settings/` | katalog **obok exe** |
| ścieżka Win | `%APPDATA%/IcoForge` | `platformdirs(...roaming)` → `%APPDATA%/IcoForge` ✅ zbieżne |
| ścieżka Linux | `~/.config/icoforge` | `~/.config/<app_name>` — **uwaga na wielkość liter** |
| plik | `settings.json` (+ `presets/`) | `config.json` |
| zapis | `write_text` (**nieatomowy**) | tmp+`os.replace` (atomowy) |
| uszkodzony JSON | ciche `{}` | kopia `.broken-<ts>` |
| API | `get_setting(k,d)` / `save_setting(k,v)` | `config.get(k,d)` / `config[k]=v` + `flush()` |

**Znaleziona pułapka (motywacja #13):** `settings.py`, `recent_files.py` i
`window_state.py` **niezależnie** robią `_load`/`_save` na **tym samym**
`settings.json` (klucze `theme`/`language`, `recent_files`, `window_state`) →
read-modify-write bez synchronizacji = latentny clobber przy zapisach blisko
w czasie. Migracja na jeden `Config` (jeden obiekt-słownik + `flush`) to naprawia
przy okazji — ale wymaga przepięcia `core/presets.py` (używa `get_settings_dir`
dla `presets/`) na `config_dir`.

---

## 0e. Audyt pomocy (wzorzec pdf2md)

Zakładki `HelpWindow` IcoForge (`help_tabs()`): **Konwersja, Optymalizacja PNG,
Edytor, CLI, Model AI** — treść budowana kitowymi helperami `help_html`
(`section`/`paragraph`/`unordered_list`/`table`/`code`/`preformatted`),
tłumaczona `QCoreApplication.translate("HelpWindow", …)`.

`docs/*.md` repo (`ARCHITECTURE`, `FEATURES`, `GETTING_STARTED`, `ROADMAP`,
`PROMPTY`, `ZALOZENIA_PROJEKTU`, `CO_ROBI_CLAUDE_CODE`) to **dokumentacja
deweloperska po polsku**, nie treść pomocy użytkownika. **Brak duplikacji**
help ↔ docs (inaczej niż w pdf2md). **Wniosek:** `add_markdown_section` („jeden
plik prawdy", pliki pakietu przez `importlib.resources`, nie `Path(__file__)`)
ma tu **niską wartość** — brak wspólnego źródła do scalenia. Kandydatów: brak.
(Gdyby powstał user-facing `docs/POMOC.md`, wtedy warto — poza zakresem migracji.)

---

## 0f. Ryzyka specyficzne IcoForge

1. **PyInstaller — wheel kitu w bundlu:** kit instaluje się jak zwykły pakiet
   (`git+…`), więc trafia do bundla; ikony/assets kitu **już** objęte
   `collect_data_files("chodzkos_gui_kit")`. **Do dopilnowania:** spec ma
   `copy_metadata("icoforge")`, **ale nie** `copy_metadata("chodzkos-gui-kit")` —
   jeśli kod frozen sięgnie po `chodzkos_gui_kit.__version__` (metadane) dostanie
   fallback `0.0.0+unknown`. Dziś nieczytane → nieszkodliwe; dodać przy adopcji
   `AboutPanel`/diagnostyki wersji kitu.
2. **`ai_installer._find_python` + subprocess rembg:** oba zależą od
   `utils/python_finder` (**nie** od `paths`/`get_settings_dir`). Migracja
   `paths`/`settings` (#12/#13) ich nie dotyka bezpośrednio — ale `core/presets.py`
   używa `get_settings_dir` dla `presets/`, więc zmiana `get_settings_dir` musi
   przepiąć presety, recent i window_state **razem** (inaczej rozjadą się katalogi).
3. **`_version.py` generowany przy buildzie (`__version__="1.3.0"`):**
   `get_installed_version` czyta `importlib.metadata("icoforge")` z fallbackiem
   na `_version`. Wzorzec zgodny z single-source kitu (`importlib.metadata`) —
   ewentualny `AboutPanel` kitu powinien czytać wersję **konsumenta** (parametr
   albo `importlib.metadata(app_name)`), nie własną; do potwierdzenia w PR #17.
4. **Migracja danych użytkownika (#12/#13):** zmiana `settings.json`→`config.json`,
   `portable.txt`→`portable.flag`, `exe/settings/`→obok-exe i wielkość liter na
   Linux wymaga **shima migracyjnego** (jednorazowe przeniesienie), inaczej
   użytkownicy „tracą" ustawienia/recent/geometrię po update.

---

## Wnioski — stan i rekomendacja

**IcoForge jest już w ~70% zmigrowany:** silnik motywu, palety, dialogi,
belka DWM, ikony, `HelpWindow`, `make_scrollable` — wszystko z kitu (część kitu
to wręcz ekstrakcje z IcoForge: `IconProvider`, wzorce DWM/Win10). Pozostałe
lokalne moduły dzielą się na trzy grupy:

- **Domknięcie „za darmo"** (małe, niskie ryzyko): bump pinu 0.5.2→**0.5.3**
  (`bb40fa6`); usunięcie martwego `native_event_filter.py` (#6).
- **Jedna decyzyjna fala** (#3 `ThemeManager` → pociąga #5 belki i #13 config):
  adopcja kitowego `ThemeManager` + `attach_titlebar` + `Config`, z refaktorem
  ~8 slotów `theme_changed` (str→Palette) i **shimem migracji danych**. To
  największy element PROMPT B.
- **Zostaje w aplikacji:** edytor/canvas/konwerter/ICO-CUR-ICNS/optymalizator/
  presety, `get_resource_path`, `recent_files`, `window_state`, `version_check`
  (do czasu `AboutPanel` w kicie), `python_finder`/`ai_installer`, treść pomocy.

**Kandydaci na PR do kitu (przed migracją odpowiednich wierszy):** `AboutPanel`
(#17, z update-check IcoForge) — pozostałe obszary kit już pokrywa, więc
**ZASTĄP+PR poza #17 nie występuje**.
