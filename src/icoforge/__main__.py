"""Entry point for ``python -m icoforge`` and the ``icoforge`` console script."""

from __future__ import annotations

from pathlib import Path


def _force_xcb_on_wsl() -> None:
    """Force X11 backend on WSL to avoid WSLg Wayland window-activation bugs."""
    import os

    if os.environ.get("QT_QPA_PLATFORM"):
        return  # user has set it explicitly, don't override
    try:
        if "microsoft" in Path("/proc/version").read_text().lower():
            os.environ["QT_QPA_PLATFORM"] = "xcb"
    except OSError:
        pass


def run_gui() -> int:
    """Launch the PySide6 GUI."""
    import logging

    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")

    _force_xcb_on_wsl()

    from icoforge.core import heic_loader

    heic_loader.register_heif_opener()

    import sys

    from PySide6.QtCore import QTranslator
    from PySide6.QtWidgets import QApplication

    from icoforge.utils.settings import get_language

    app = QApplication(sys.argv)

    # Apply the saved (or system-detected) theme before any window is created.
    # Qt requires the palette/stylesheet to be set before the first paint.
    from icoforge.utils.theme import init_theme_manager

    theme_manager = init_theme_manager(app)
    # Apply the persisted (or auto → system-detected) theme before any window paints.
    theme_manager.apply(theme_manager.setting)

    lang = get_language()

    # Load Qt base translations (buttons like Save/Discard/Cancel) for non-English
    if lang != "en":
        from PySide6.QtCore import QLibraryInfo

        qt_translator = QTranslator()
        qt_translations_dir = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
        if qt_translator.load(f"qtbase_{lang}", qt_translations_dir):
            app.installTranslator(qt_translator)

    translator = QTranslator()
    qm_path = Path(__file__).parent / "translations" / f"icoforge_{lang}.qm"
    if qm_path.exists() and translator.load(str(qm_path)):
        app.installTranslator(translator)

    # OS colour-scheme changes in "auto" mode are handled by the kit ThemeManager
    # itself (it subscribes to colorSchemeChanged only while the setting is "auto").

    from icoforge.gui.main_window import main as gui_main

    return gui_main(app, theme_manager=theme_manager)


if __name__ == "__main__":
    raise SystemExit(run_gui())
