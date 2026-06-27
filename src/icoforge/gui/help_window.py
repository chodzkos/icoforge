"""Treść okna pomocy IcoForge — zakładki dla kitowego ``HelpWindow``.

Okno (belka DWM + re-render motywu) liczy wspólny kit
(:class:`chodzkos_gui_kit.qt.widgets.HelpWindow`). Tu zostaje WYŁĄCZNIE wiedza o
IcoForge: lista zakładek ``(tytuł, html)`` składana kitowymi helperami HTML
(kolory przez ``palette(...)`` — re-render przy zmianie motywu robi kit dla
WSZYSTKICH zakładek). Wołający:

    from chodzkos_gui_kit.qt.widgets import HelpWindow
    from icoforge.gui.help_window import HELP_TITLE, help_tabs
    HelpWindow(parent, title=HELP_TITLE, tabs=help_tabs()).exec()

i18n: ``QCoreApplication.translate`` z kontekstem ``"HelpWindow"`` (stabilny dla
``lupdate``). Przycisk „Close" tłumaczy Qt (``QDialogButtonBox`` w kicie).
"""

from __future__ import annotations

from chodzkos_gui_kit.qt.widgets import (
    code,
    paragraph,
    preformatted,
    section,
    table,
    unordered_list,
)
from PySide6.QtCore import QCoreApplication

HELP_TITLE = "Pomoc — IcoForge"


def _tr(text: str) -> str:
    """Tłumaczenie w kontekście ``HelpWindow`` (zgodne z dawnym ``self.tr``)."""
    return QCoreApplication.translate("HelpWindow", text)


def help_tabs() -> list[tuple[str, str]]:
    """Zakładki pomocy IcoForge jako ``(tytuł, html)`` — wstrzykiwane do kitu."""
    return [
        (_tr("Konwersja"), _conversion_html()),
        (_tr("Optymalizacja PNG"), _optimization_html()),
        (_tr("Edytor"), _editor_html()),
        (_tr("CLI"), _cli_html()),
        (_tr("Model AI"), _ai_model_html()),
    ]


# ── Treść zakładek (po polsku; wiedza o IcoForge) ──────────────────────────────


def _conversion_html() -> str:
    return (
        section(
            _tr("Rozmiary"),
            paragraph(_tr("Wybierz rozmiary ramek, które znajdą się w pliku ICO."))
            + unordered_list(
                _tr("16x16 — pasek zadań, małe ikony systemu"),
                _tr("20, 24, 40, 48, 96 — skalowanie DPI 125-200%"),
                _tr("32x32 — standardowa ikona pulpitu, menu Start"),
                _tr("64x64 — widok ikon średnich"),
                _tr("128, 256 — widok ikon dużych i szczegółowych"),
            ),
        )
        + section(
            _tr("Presety"),
            unordered_list(
                _tr("<b>Niestandardowy</b> — ręczny dobór rozmiarów"),
                _tr("<b>Favicon (16/32/48)</b> — minimalny zestaw dla strony WWW"),
                _tr("<b>Windows App Icon</b> — pełny zestaw Windows (16-256 px, 10 rozmiarów)"),
                _tr("<b>Web (16/32/64/128)</b> — popularny zestaw dla aplikacji webowych"),
            ),
        )
        + section(
            _tr("Algorytm skalowania"),
            unordered_list(
                _tr("<b>Lanczos</b> — najlepsza jakość, idealny dla zdjęć i grafiki wektorowej"),
                _tr("<b>Bicubic</b> — dobra jakość, szybszy od Lanczos; dobry wybór ogólny"),
                _tr("<b>Bilinear</b> — szybki; wystarczający przy małych zmianach rozmiaru"),
                _tr("<b>Nearest</b> — brak interpolacji; zachowuje ostre piksele (pixel art)"),
                _tr("<b>Box</b> — najlepszy przy dużym zmniejszeniu (np. 256→16 px)"),
            ),
        )
        + section(
            _tr("Tło dla braku alpha"),
            paragraph(
                _tr(
                    "Pliki JPG i niektóre BMP nie mają kanału przezroczystości. "
                    "Wybierz kolor tła, który zostanie użyty przy konwersji, "
                    "lub zostaw &ldquo;Przezroczyste&rdquo; jeśli chcesz żeby piksele "
                    "stały się przeźroczyste."
                )
            ),
        )
        + section(
            _tr("Auto-trim"),
            paragraph(
                _tr(
                    "Przed skalowaniem wycina przezroczyste piksele z krawędzi obrazu, "
                    "tak aby treść wypełniała całą ramkę. Użyj Padding, "
                    "jeśli chcesz zachować margines wokół ikony."
                )
            ),
        )
        + section(
            _tr("Per-size source"),
            paragraph(
                _tr(
                    "Każdy rozmiar może mieć osobny plik źródłowy. "
                    "Np. ręcznie narysowany 16x16 i wygenerowany 256x256. "
                    "Kliknij &ldquo;Wybierz…&rdquo; przy wybranym wierszu lub "
                    "przeciągnij plik na wiersz."
                )
            ),
        )
    )


def _optimization_html() -> str:
    return (
        section(
            _tr("Poziom kompresji (0-6)"),
            paragraph(
                _tr(
                    "Kontroluje kompromis między czasem a rozmiarem pliku. "
                    "Domyślna wartość 4 daje dobre wyniki w rozsądnym czasie. "
                    "Poziom 0 jest najszybszy (ale największy plik), "
                    "poziom 6 daje najmniejszy plik (ale wolniej)."
                )
            ),
        )
        + section(
            _tr("Tryb Zopfli"),
            paragraph(
                _tr(
                    "Dodatkowy algorytm kompresji dający 5-10% mniejszy plik niż poziom 6, "
                    "ale znacznie wolniejszy. Zalecany tylko przy dużych plikach lub "
                    "gdy czas przetwarzania nie jest ważny."
                )
            ),
        )
        + section(
            _tr("Usuń metadane"),
            paragraph(
                _tr(
                    "Usuwa z pliku PNG dane takie jak: "
                    "komentarze (tEXt/iTXt/zTXt), datę (tIME), dane aparatu (eXIf). "
                    "Zawartość pikseli pozostaje identyczna — optymalizacja jest bezstratna."
                )
            ),
        )
        + section(
            _tr("Zachowaj profil kolorów ICC"),
            paragraph(
                _tr(
                    "Przy włączonym &ldquo;Usuń metadane&rdquo; profil kolorów (chunk iCCP/sRGB) "
                    "jest normalnie usuwany. Zaznacz tę opcję, jeśli plik zawiera "
                    "profil Adobe RGB lub CMYK i chcesz go zachować dla poprawnego wyświetlania."
                )
            ),
        )
    )


def _editor_html() -> str:
    tools_table = table(
        [_tr("Narzędzie"), _tr("Skrót"), _tr("Opis")],
        [
            [_tr("Ołówek"), "B", _tr("Rysowanie odręczne, rozmiar 1-8 px")],
            [_tr("Gumka"), "E", _tr("Ustawia piksele jako przezroczyste (alpha=0)")],
            [_tr("Wypełnienie"), "G", _tr("Flood fill z tolerancją 0-100")],
            [_tr("Kroplomierz"), "I / Alt", _tr("Pobiera kolor z płótna")],
            [_tr("Linia"), "L", _tr("Prosta linia, algorytm Bresenhama")],
            [_tr("Prostokąt"), "R", _tr("Kontur lub wypełniony")],
            [_tr("Zaznaczenie"), "S", _tr("Prostokątne; Ctrl+C/X/V")],
        ],
    )
    zoom_table = table(
        [_tr("Akcja"), _tr("Skrót")],
        [
            [_tr("Zoom in/out"), "Ctrl + scroll"],
            [_tr("Zoom in/out"), "+ / -"],
            [_tr("Dopasuj do ekranu"), "Ctrl+0"],
            [_tr("Zoom 1:1 (100%)"), "Ctrl+1"],
        ],
    )
    return (
        section(_tr("Narzędzia"), tools_table)
        + section(
            _tr("Zoom"),
            zoom_table + paragraph(_tr("Siatka pikseli wyświetla się przy zoom ≥ 8x.")),
        )
        + section(
            _tr("Undo / Redo"),
            unordered_list(
                _tr("Cofnij: Ctrl+Z"),
                _tr("Ponów: Ctrl+Shift+Z lub Ctrl+Y"),
                _tr("Historia jest niezależna dla każdego rozmiaru ramki."),
            ),
        )
        + section(
            _tr("Synchronizacja rozmiarów"),
            paragraph(
                _tr(
                    "Gdy zaznaczony jest checkbox &ldquo;Synchronizuj rozmiary&rdquo;, "
                    "przełączenie na mniejszy rozmiar automatycznie tworzy "
                    "downscale z aktualnie edytowanej ramki."
                )
            ),
        )
    )


def _cli_html() -> str:
    def cmd(command: str, desc: str) -> str:
        return preformatted(command) + paragraph(desc)

    return (
        section(
            _tr("Konwersja ICO / ICNS / CUR"),
            paragraph(_tr("Format wyjścia wybierany jest automatycznie po rozszerzeniu TARGET."))
            + cmd(
                "icoforge-cli convert input.png output.ico --sizes 16,32,48,256",
                _tr("Podstawowa konwersja PNG → ICO. ")
                + code("--sizes")
                + _tr(" przyjmuje też presety: ")
                + code("windows")
                + ", "
                + code("favicon")
                + ".",
            )
            + cmd(
                "icoforge-cli convert input.svg output.ico --sizes windows --resample nearest",
                _tr("SVG z presetem Windows App i algorytmem Nearest (pixel art)."),
            )
            + cmd(
                "icoforge-cli convert input.jpg output.ico --background #ffffff",
                _tr("JPG bez kanału alpha — białe tło dla przezroczystych pikseli."),
            )
            + cmd(
                "icoforge-cli convert input.png output.icns --sizes 16,32,64,128,256,512,1024",
                _tr("Zapis w formacie ICNS (macOS)."),
            )
            + cmd(
                "icoforge-cli convert input.png cursor.cur --sizes 32,48 --hotspot 0,0",
                _tr("Kursor Windows CUR. ")
                + code("--hotspot X,Y")
                + _tr(" to aktywny piksel kursora (musi leżeć wewnątrz każdej ramki)."),
            ),
        )
        + section(
            _tr("Optymalizacja PNG"),
            cmd(
                "icoforge-cli optimize input.png",
                _tr("Tworzy ") + code("input.min.png") + _tr(" — źródło nienaruszone."),
            )
            + cmd(
                "icoforge-cli optimize input.png --level 4 --strip",
                _tr("Poziom kompresji 4, usuń metadane."),
            )
            + cmd(
                "icoforge-cli optimize *.png --in-place --slow",
                _tr("Nadpisz wszystkie PNG w miejscu, tryb Zopfli (maksymalna kompresja)."),
            ),
        )
        + section(
            _tr("Favicon i ekstrakcja"),
            cmd(
                "icoforge-cli favicon logo.png ./output-folder/",
                _tr("Generuje pełny zestaw favicon: ")
                + code("favicon.ico")
                + ", "
                + code("apple-touch-icon.png")
                + _tr(", PWA icons, ")
                + code("site.webmanifest")
                + ".",
            )
            + cmd(
                "icoforge-cli extract-icons app.exe --output-dir ./icons/",
                _tr("Wyciąga grupy ikon RT_GROUP_ICON z pliku PE (EXE/DLL). ")
                + _tr("Wymaga: ")
                + code("pip install icoforge[exe]")
                + ".",
            ),
        )
        + section(
            _tr("Presety"),
            cmd(
                "icoforge-cli presets list",
                _tr("Wypisuje dostępne presety (wbudowane + użytkownika)."),
            )
            + cmd(
                'icoforge-cli presets show "Windows App Icon"',
                _tr("Pokazuje konfigurację wybranego presetu."),
            )
            + cmd(
                'icoforge-cli convert input.png out.ico --preset "Windows App Icon"',
                _tr("Użyj presetu jako bazy konfiguracji. ")
                + code("--sizes")
                + _tr(" i ")
                + code("--resample")
                + _tr(" mogą nadpisać wartości presetu."),
            ),
        )
    )


def _ai_model_html() -> str:
    vc_redist = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
    return (
        section(
            _tr("Usuwanie tła przez AI (rembg)"),
            paragraph(
                _tr(
                    'Funkcja „Usuń tło (AI)" wymaga jednorazowej instalacji '
                    "biblioteki rembg i pobrania modelu (~170 MB)."
                )
            ),
        )
        + "<h4>"
        + _tr("Krok 1 — instalacja przez instalator GUI")
        + "</h4>"
        + paragraph(
            _tr(
                "W aplikacji wybierz menu <b>Narzędzia &rarr; Zainstaluj model AI...</b><br>"
                "Kliknij przycisk <b>Zainstaluj</b> i poczekaj na zakończenie.<br>"
                "Wymagane połączenie z internetem (~200 MB do pobrania)."
            )
        )
        + paragraph(
            _tr(
                "Alternatywnie, jeżeli checkbox &bdquo;Usuń tło (AI)&rdquo; jest widoczny "
                "w panelu konwersji, kliknij przycisk <b>Zainstaluj model AI...</b> "
                "bezpośrednio tam."
            )
        )
        + "<h4>"
        + _tr("Krok 2 — pobranie modelu")
        + "</h4>"
        + paragraph(
            _tr(
                "Model pobiera się automatycznie przy pierwszym użyciu "
                'funkcji „Usuń tło (AI)" w aplikacji.<br>'
                "Rozmiar: ~170 MB. Wymagane połączenie z internetem.<br>"
                "Model zapisywany jest w:"
            )
        )
        + preformatted("C:\\Users\\&lt;TWOJA_NAZWA&gt;\\.u2net\\u2net.onnx")
        + paragraph(_tr("Kolejne uruchomienia nie wymagają pobierania."))
        + "<h4>"
        + _tr("Krok 3 — restart i użycie")
        + "</h4>"
        + paragraph(
            _tr(
                "Zamknij i uruchom ponownie IcoForge.<br>"
                'Opcja „Usuń tło (AI)" pojawi się automatycznie w ustawieniach konwersji.'
            )
        )
        + "<h4>"
        + _tr("Dostępne modele (opcjonalnie)")
        + "</h4>"
        + table(
            [_tr("Model"), _tr("Rozmiar"), _tr("Zastosowanie")],
            [
                ["u2net", "176 MB", _tr("Domyślny, ogólny — dobry do większości obrazów")],
                ["u2net_human_seg", "176 MB", _tr("Sylwetki ludzi")],
                ["u2netp", "4 MB", _tr("Szybki, mniejsza dokładność")],
                ["silueta", "44 MB", _tr("Dobry do obiektów i produktów")],
            ],
        )
        + paragraph(_tr("Zmianę modelu znajdziesz w Ustawieniach — Model AI."))
        + "<h4>"
        + _tr("Wymagania systemowe")
        + "</h4>"
        + unordered_list(
            _tr("Python 3.11 lub nowszy"),
            _tr("Visual C++ Redistributable 2019+ (pobierz: ") + code(vc_redist) + ")",
            _tr("~500 MB wolnego miejsca na dysku"),
            _tr("Działa bez karty GPU (CPU wystarczy)"),
        )
    )
