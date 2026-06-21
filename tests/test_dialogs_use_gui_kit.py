"""Strażnik migracji dialogów: gui/ NIE używa surowego QFileDialog.

Surowy ``QFileDialog`` (z wymuszonym ``DontUseNativeDialog``) omijał regułę
natywny/fallback kitu — i fallback bez resetu toolbara v2.6 gubił ikony. Dialogi
plików muszą iść przez ``chodzkos_gui_kit.qt.dialogs`` (``open_file``/``open_files``/
``save_file``/``pick_dir``).

Test skanuje źródła (jak audyt tooltipów) — pominięty dialog WYWALI CI, zamiast
czekać na ręczny smoke na Windows.
"""

from __future__ import annotations

from pathlib import Path

_GUI_DIR = Path(__file__).resolve().parents[1] / "src" / "icoforge" / "gui"
_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_no_raw_qfiledialog_in_gui() -> None:
    """Żaden moduł w gui/ nie odwołuje się do ``QFileDialog`` (tylko helpery kitu)."""
    offenders = [
        py.relative_to(_REPO_ROOT).as_posix()
        for py in sorted(_GUI_DIR.rglob("*.py"))
        if "QFileDialog" in py.read_text(encoding="utf-8")
    ]
    assert not offenders, (
        "Surowy QFileDialog w gui/ — użyj chodzkos_gui_kit.qt.dialogs "
        f"(open_file/open_files/save_file/pick_dir): {offenders}"
    )
