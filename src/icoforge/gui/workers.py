"""Background workers for long-running conversion operations."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal

from icoforge.core.converter import convert
from icoforge.core.models import IcoConfig


class _WorkerSignals(QObject):
    """Qt signals for ConversionWorker (must live on the main thread)."""

    progress = Signal(float)
    finished = Signal(Path)
    error = Signal(str)


class _Cancelled(BaseException):
    """Raised inside the progress callback to interrupt a cancelled conversion."""


class ConversionWorker(QRunnable):
    """Run :func:`~icoforge.core.converter.convert` in a QThreadPool thread.

    Cancellation is cooperative: call :meth:`cancel` and the worker will stop
    at the next progress tick without killing the thread.
    """

    def __init__(self, source: Path, target: Path, config: IcoConfig) -> None:
        super().__init__()
        self.signals = _WorkerSignals()
        self._source = source
        self._target = target
        self._config = config
        self._cancelled = False
        self.setAutoDelete(True)

    def cancel(self) -> None:
        """Request cancellation; the worker stops at the next progress tick."""
        self._cancelled = True

    def run(self) -> None:
        try:
            convert(self._source, self._target, self._config, self._on_progress)
            if not self._cancelled:
                self.signals.finished.emit(self._target)
        except _Cancelled:
            pass
        except Exception as exc:
            if not self._cancelled:
                self.signals.error.emit(str(exc))

    def _on_progress(self, value: float) -> None:
        if self._cancelled:
            raise _Cancelled()
        self.signals.progress.emit(value)
