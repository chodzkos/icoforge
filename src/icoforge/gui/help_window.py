"""In-app help window with tabs for each major feature area."""

from __future__ import annotations

from PySide6.QtCore import QByteArray, QSettings, Qt
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


def _scroll(widget: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setWidget(widget)
    return area


def _section(title: str, body: str) -> str:
    return f"<h3>{title}</h3>{body}"


def _p(text: str) -> str:
    return f"<p>{text}</p>"


def _ul(*items: str) -> str:
    rows = "".join(f"<li>{i}</li>" for i in items)
    return f"<ul>{rows}</ul>"


def _table(headers: list[str], rows: list[list[str]]) -> str:
    th = "".join(f"<th style='padding:4px 8px;text-align:left'>{h}</th>" for h in headers)
    trs = ""
    for row in rows:
        tds = "".join(f"<td style='padding:4px 8px'>{c}</td>" for c in row)
        trs += f"<tr>{tds}</tr>"
    return (
        "<table border='1' cellspacing='0' cellpadding='0' "
        "style='border-collapse:collapse;margin:4px 0'>"
        f"<tr style='background:palette(mid)'>{th}</tr>{trs}</table>"
    )


def _code(text: str) -> str:
    return f"<code style='background:palette(mid);padding:1px 4px;border-radius:2px'>{text}</code>"


def _pre(text: str) -> str:
    return (
        f"<pre style='background:palette(mid);padding:8px;border-radius:4px;"
        f"white-space:pre-wrap'>{text}</pre>"
    )


class HelpWindow(QDialog):
    """Tabbed help / user manual dialog."""

    _GEOMETRY_KEY = "HelpWindow/geometry"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Instrukcja obsługi — IcoForge"))
        self.resize(700, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        tabs = QTabWidget()
        tabs.addTab(_scroll(self._make_conversion_tab()), self.tr("Konwersja"))
        tabs.addTab(_scroll(self._make_optimization_tab()), self.tr("Optymalizacja PNG"))
        tabs.addTab(_scroll(self._make_editor_tab()), self.tr("Edytor"))
        tabs.addTab(_scroll(self._make_cli_tab()), self.tr("CLI"))
        layout.addWidget(tabs)

        close_btn = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_btn.rejected.connect(self.accept)
        layout.addWidget(close_btn)

        self._restore_geometry()

    # ------------------------------------------------------------------
    # Geometry persistence
    # ------------------------------------------------------------------

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        from icoforge.utils.theme import get_theme_manager
        from icoforge.utils.window_theme import apply_theme_to_dialog

        mgr = get_theme_manager()
        if mgr is not None:
            apply_theme_to_dialog(self, mgr)

    def closeEvent(self, event: object) -> None:
        settings = QSettings("IcoForge", "IcoForge")
        settings.setValue(self._GEOMETRY_KEY, self.saveGeometry())
        super().closeEvent(event)  # type: ignore[arg-type]

    def _restore_geometry(self) -> None:
        settings = QSettings("IcoForge", "IcoForge")
        raw = settings.value(self._GEOMETRY_KEY)
        if isinstance(raw, (bytes, QByteArray)):
            self.restoreGeometry(raw)

    # ------------------------------------------------------------------
    # Tab builders
    # ------------------------------------------------------------------

    def _make_conversion_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        html = (
            _section(
                self.tr("Rozmiary"),
                _p(self.tr("Wybierz rozmiary ramek, które znajdą się w pliku ICO."))
                + _ul(
                    self.tr("16x16 — pasek zadań, małe ikony systemu"),
                    self.tr("20, 24, 40, 48, 96 — skalowanie DPI 125-200%"),
                    self.tr("32x32 — standardowa ikona pulpitu, menu Start"),
                    self.tr("64x64 — widok ikon średnich"),
                    self.tr("128, 256 — widok ikon dużych i szczegółowych"),
                ),
            )
            + _section(
                self.tr("Presety"),
                _ul(
                    self.tr("<b>Niestandardowy</b> — ręczny dobór rozmiarów"),
                    self.tr("<b>Favicon (16/32/48)</b> — minimalny zestaw dla strony WWW"),
                    self.tr(
                        "<b>Windows App Icon</b> — pełny zestaw Windows (16-256 px, 10 rozmiarów)"
                    ),
                    self.tr("<b>Web (16/32/64/128)</b> — popularny zestaw dla aplikacji webowych"),
                ),
            )
            + _section(
                self.tr("Algorytm skalowania"),
                _ul(
                    self.tr(
                        "<b>Lanczos</b> — najlepsza jakość, idealny dla zdjęć i grafiki wektorowej"
                    ),
                    self.tr(
                        "<b>Bicubic</b> — dobra jakość, szybszy od Lanczos; dobry wybór ogólny"
                    ),
                    self.tr(
                        "<b>Bilinear</b> — szybki; wystarczający przy małych zmianach rozmiaru"
                    ),
                    self.tr(
                        "<b>Nearest</b> — brak interpolacji; zachowuje ostre piksele (pixel art)"
                    ),
                    self.tr("<b>Box</b> — najlepszy przy dużym zmniejszeniu (np. 256→16 px)"),
                ),
            )
            + _section(
                self.tr("Tło dla braku alpha"),
                _p(
                    self.tr(
                        "Pliki JPG i niektóre BMP nie mają kanału przezroczystości. "
                        "Wybierz kolor tła, który zostanie użyty przy konwersji, "
                        "lub zostaw &ldquo;Przezroczyste&rdquo; jeśli chcesz żeby piksele stały się przeźroczyste."
                    )
                ),
            )
            + _section(
                self.tr("Auto-trim"),
                _p(
                    self.tr(
                        "Przed skalowaniem wycina przezroczyste piksele z krawędzi obrazu, "
                        "tak aby treść wypełniała całą ramkę. Użyj Padding, "
                        "jeśli chcesz zachować margines wokół ikony."
                    )
                ),
            )
            + _section(
                self.tr("Per-size source"),
                _p(
                    self.tr(
                        "Każdy rozmiar może mieć osobny plik źródłowy. "
                        "Np. ręcznie narysowany 16x16 i wygenerowany 256x256. "
                        "Kliknij &ldquo;Wybierz…&rdquo; przy wybranym wierszu lub przeciągnij plik na wiersz."
                    )
                ),
            )
        )
        label = QLabel(html)
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setOpenExternalLinks(False)
        layout.addWidget(label)
        return w

    def _make_optimization_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        html = (
            _section(
                self.tr("Poziom kompresji (0-6)"),
                _p(
                    self.tr(
                        "Kontroluje kompromis między czasem a rozmiarem pliku. "
                        "Domyślna wartość 4 daje dobre wyniki w rozsądnym czasie. "
                        "Poziom 0 jest najszybszy (ale największy plik), "
                        "poziom 6 daje najmniejszy plik (ale wolniej)."
                    )
                ),
            )
            + _section(
                self.tr("Tryb Zopfli"),
                _p(
                    self.tr(
                        "Dodatkowy algorytm kompresji dający 5-10% mniejszy plik niż poziom 6, "
                        "ale znacznie wolniejszy. Zalecany tylko przy dużych plikach lub "
                        "gdy czas przetwarzania nie jest ważny."
                    )
                ),
            )
            + _section(
                self.tr("Usuń metadane"),
                _p(
                    self.tr(
                        "Usuwa z pliku PNG dane takie jak: "
                        "komentarze (tEXt/iTXt/zTXt), datę (tIME), dane aparatu (eXIf). "
                        "Zawartość pikseli pozostaje identyczna — optymalizacja jest bezstratna."
                    )
                ),
            )
            + _section(
                self.tr("Zachowaj profil kolorów ICC"),
                _p(
                    self.tr(
                        "Przy włączonym &ldquo;Usuń metadane&rdquo; profil kolorów (chunk iCCP/sRGB) "
                        "jest normalnie usuwany. Zaznacz tę opcję, jeśli plik zawiera "
                        "profil Adobe RGB lub CMYK i chcesz go zachować dla poprawnego wyświetlania."
                    )
                ),
            )
        )
        label = QLabel(html)
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(label)
        return w

    def _make_editor_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        tools_table = _table(
            [self.tr("Narzędzie"), self.tr("Skrót"), self.tr("Opis")],
            [
                [self.tr("Ołówek"), "B", self.tr("Rysowanie odręczne, rozmiar 1-8 px")],
                [self.tr("Gumka"), "E", self.tr("Ustawia piksele jako przezroczyste (alpha=0)")],
                [self.tr("Wypełnienie"), "G", self.tr("Flood fill z tolerancją 0-100")],
                [self.tr("Kroplomierz"), "I / Alt", self.tr("Pobiera kolor z płótna")],
                [self.tr("Linia"), "L", self.tr("Prosta linia, algorytm Bresenhama")],
                [self.tr("Prostokąt"), "R", self.tr("Kontur lub wypełniony")],
                [self.tr("Zaznaczenie"), "S", self.tr("Prostokątne; Ctrl+C/X/V")],
            ],
        )

        zoom_table = _table(
            [self.tr("Akcja"), self.tr("Skrót")],
            [
                [self.tr("Zoom in/out"), "Ctrl + scroll"],
                [self.tr("Zoom in/out"), "+ / -"],
                [self.tr("Dopasuj do ekranu"), "Ctrl+0"],
                [self.tr("Zoom 1:1 (100%)"), "Ctrl+1"],
            ],
        )

        html = (
            _section(self.tr("Narzędzia"), tools_table)
            + _section(
                self.tr("Zoom"),
                zoom_table + _p(self.tr("Siatka pikseli wyświetla się przy zoom ≥ 8x.")),
            )
            + _section(
                self.tr("Undo / Redo"),
                _ul(
                    self.tr("Cofnij: Ctrl+Z"),
                    self.tr("Ponów: Ctrl+Shift+Z lub Ctrl+Y"),
                    self.tr("Historia jest niezależna dla każdego rozmiaru ramki."),
                ),
            )
            + _section(
                self.tr("Synchronizacja rozmiarów"),
                _p(
                    self.tr(
                        "Gdy zaznaczony jest checkbox &ldquo;Synchronizuj rozmiary&rdquo;, "
                        "przełączenie na mniejszy rozmiar automatycznie tworzy "
                        "downscale z aktualnie edytowanej ramki."
                    )
                ),
            )
        )
        label = QLabel(html)
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(label)
        return w

    def _make_cli_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        def cmd(code: str, desc: str) -> str:
            return _pre(code) + _p(desc)

        html = (
            _section(
                self.tr("Konwersja ICO / ICNS / CUR"),
                _p(self.tr("Format wyjścia wybierany jest automatycznie po rozszerzeniu TARGET."))
                + cmd(
                    "icoforge-cli convert input.png output.ico --sizes 16,32,48,256",
                    self.tr(
                        "Podstawowa konwersja PNG → ICO. "
                        + _code("--sizes").replace("<", "&lt;")
                        + " przyjmuje też presety: "
                        + _code("windows").replace("<", "&lt;")
                        + ", "
                        + _code("favicon").replace("<", "&lt;")
                        + "."
                    ),
                )
                + cmd(
                    "icoforge-cli convert input.svg output.ico --sizes windows --resample nearest",
                    self.tr("SVG z presetem Windows App i algorytmem Nearest (pixel art)."),
                )
                + cmd(
                    "icoforge-cli convert input.jpg output.ico --background #ffffff",
                    self.tr("JPG bez kanału alpha — białe tło dla przezroczystych pikseli."),
                )
                + cmd(
                    "icoforge-cli convert input.png output.icns --sizes 16,32,64,128,256,512,1024",
                    self.tr("Zapis w formacie ICNS (macOS)."),
                )
                + cmd(
                    "icoforge-cli convert input.png cursor.cur --sizes 32,48 --hotspot 0,0",
                    self.tr(
                        "Kursor Windows CUR. "
                        + _code("--hotspot X,Y").replace("<", "&lt;")
                        + " to aktywny piksel kursora (musi leżeć wewnątrz każdej ramki)."
                    ),
                ),
            )
            + _section(
                self.tr("Optymalizacja PNG"),
                cmd(
                    "icoforge-cli optimize input.png",
                    self.tr(
                        "Tworzy "
                        + _code("input.min.png").replace("<", "&lt;")
                        + " — źródło nienaruszone."
                    ),
                )
                + cmd(
                    "icoforge-cli optimize input.png --level 4 --strip",
                    self.tr("Poziom kompresji 4, usuń metadane."),
                )
                + cmd(
                    "icoforge-cli optimize *.png --in-place --slow",
                    self.tr("Nadpisz wszystkie PNG w miejscu, tryb Zopfli (maksymalna kompresja)."),
                ),
            )
            + _section(
                self.tr("Favicon i ekstrakcja"),
                cmd(
                    "icoforge-cli favicon logo.png ./output-folder/",
                    self.tr(
                        "Generuje pełny zestaw favicon: "
                        + _code("favicon.ico").replace("<", "&lt;")
                        + ", "
                        + _code("apple-touch-icon.png").replace("<", "&lt;")
                        + ", PWA icons, "
                        + _code("site.webmanifest").replace("<", "&lt;")
                        + "."
                    ),
                )
                + cmd(
                    "icoforge-cli extract-icons app.exe --output-dir ./icons/",
                    self.tr(
                        "Wyciąga grupy ikon RT_GROUP_ICON z pliku PE (EXE/DLL). "
                        "Wymaga: " + _code("pip install icoforge[exe]").replace("<", "&lt;") + "."
                    ),
                ),
            )
            + _section(
                self.tr("Presety"),
                cmd(
                    "icoforge-cli presets list",
                    self.tr("Wypisuje dostępne presety (wbudowane + użytkownika)."),
                )
                + cmd(
                    'icoforge-cli presets show "Windows App Icon"',
                    self.tr("Pokazuje konfigurację wybranego presetu."),
                )
                + cmd(
                    'icoforge-cli convert input.png out.ico --preset "Windows App Icon"',
                    self.tr(
                        "Użyj presetu jako bazy konfiguracji. "
                        + _code("--sizes").replace("<", "&lt;")
                        + " i "
                        + _code("--resample").replace("<", "&lt;")
                        + " mogą nadpisać wartości presetu."
                    ),
                ),
            )
        )
        label = QLabel(html)
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(label)
        return w
