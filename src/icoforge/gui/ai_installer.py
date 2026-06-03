"""Dialog for installing the rembg AI library into the local ai_packages/ dir."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QProgressBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from icoforge.utils.python_finder import find_python as _find_python


def _ai_packages_dir() -> Path:
    """Return the target directory for AI packages next to the exe / repo root."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "ai_packages"
    return Path(__file__).resolve().parents[3] / "ai_packages"


class _InstallWorker(QThread):
    """Background thread that runs ``pip install rembg onnxruntime``."""

    log_line = Signal(str)
    finished = Signal(bool)

    def __init__(self, target: Path) -> None:
        super().__init__()
        self._target = target

    def run(self) -> None:
        python_parts = _find_python()

        if not python_parts:
            self.log_line.emit(
                "✗ Nie znaleziono Pythona 3.x w systemie.\n"
                "Zainstaluj Python 3.11+ ze strony python.org\n"
                "i upewnij sie ze jest dodany do PATH."
            )
            self.finished.emit(False)
            return

        self.log_line.emit(f"Uzywam Pythona: {python_parts[0]}")
        self.log_line.emit(f"Cel instalacji: {self._target}\n")

        cmd = [
            *python_parts,
            "-m",
            "pip",
            "install",
            "rembg",
            "onnxruntime",
            "--target",
            str(self._target),
            "--no-cache-dir",
            "--no-warn-script-location",
        ]
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            assert proc.stdout is not None
            for line in proc.stdout:
                self.log_line.emit(line.rstrip())
            proc.wait()
            self.finished.emit(proc.returncode == 0)
        except Exception as exc:
            self.log_line.emit(f"Blad: {exc}")
            self.finished.emit(False)


class AiInstallerDialog(QDialog):
    """Dialog that installs rembg into the *ai_packages/* directory.

    Works both in development and in the frozen .exe — the target directory
    is resolved by :func:`_ai_packages_dir`.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Instalacja modelu AI"))
        self.setMinimumWidth(520)
        self.setMinimumHeight(340)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        info = QLabel(
            self.tr(
                "Pobierze i zainstaluje biblioteke rembg (~200 MB).\n"
                "Model AI (~170 MB) zostanie pobrany przy pierwszym uzyciu.\n"
                "Wymagane polaczenie z internetem.\n\n"
                "Folder instalacji: %1"
            ).replace("%1", str(_ai_packages_dir()))
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMinimumHeight(140)
        layout.addWidget(self._log)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        btns = QDialogButtonBox()
        self._install_btn = btns.addButton(
            self.tr("Zainstaluj"), QDialogButtonBox.ButtonRole.AcceptRole
        )
        btns.addButton(QDialogButtonBox.StandardButton.Close)
        self._install_btn.clicked.connect(self._run_install)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self._worker: _InstallWorker | None = None

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        from icoforge.utils.theme import get_theme_manager
        from icoforge.utils.window_theme import apply_theme_to_dialog

        mgr = get_theme_manager()
        if mgr is not None:
            apply_theme_to_dialog(self, mgr)

    def _run_install(self) -> None:
        self._install_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._log.clear()

        target = _ai_packages_dir()
        target.mkdir(parents=True, exist_ok=True)

        self._worker = _InstallWorker(target)
        self._worker.log_line.connect(self._log.append)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_finished(self, success: bool) -> None:
        self._progress.setVisible(False)
        if success:
            self._log.append(
                self.tr(
                    "\n Instalacja zakonczona pomyslnie.\n"
                    "Uruchom ponownie IcoForge aby uzyc funkcji Usun tlo (AI)."
                )
            )
        else:
            self._log.append(
                self.tr("\n Blad instalacji. Sprawdz polaczenie z internetem\ni sprobuj ponownie.")
            )
