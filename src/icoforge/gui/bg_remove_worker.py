"""QThread worker for non-blocking AI background removal."""

from __future__ import annotations

from PIL import Image
from PySide6.QtCore import QThread, Signal


class BgRemoveWorker(QThread):
    """Run remove_background() in a background thread."""

    finished = Signal(object)  # Image.Image on success
    error = Signal(str)
    progress_text = Signal(str)

    def __init__(self, image: Image.Image) -> None:
        super().__init__()
        self._image = image

    def run(self) -> None:
        from icoforge.core.bg_remover import BgRemoveError, remove_background

        try:
            self.progress_text.emit("Usuwanie tła (może potrwać przy pierwszym użyciu)…")
            result = remove_background(self._image)
            self.finished.emit(result)
        except BgRemoveError as exc:
            self.error.emit(str(exc))
        except Exception as exc:
            self.error.emit(f"Nieoczekiwany błąd: {exc}")
