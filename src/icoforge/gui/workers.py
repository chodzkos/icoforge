"""Background workers for long-running conversion operations."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal

from icoforge.core.converter import convert
from icoforge.core.models import IcoConfig, OptimizationConfig
from icoforge.core.optimizer import optimize_batch


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


class _BatchOptimizationSignals(QObject):
    """Qt signals for BatchOptimizationWorker (must live on the main thread)."""

    progress = Signal(float)
    finished = Signal(list)  # list[OptimizationResult]
    error = Signal(str)


class BatchOptimizationWorker(QRunnable):
    """Run :func:`~icoforge.core.optimizer.optimize_batch` in a pool thread.

    Keeps the GUI responsive during long optimizations (e.g. Zopfli mode).
    Cancellation is cooperative: call :meth:`cancel` and the worker stops after
    the current file finishes, at the next progress tick.

    Args:
        paths: PNG files to optimize.
        config: Optimization parameters.
        target_dir: When ``None``, files are optimized in place; otherwise each
            result is written to ``target_dir/<stem>.min.png`` (originals kept).
    """

    def __init__(
        self,
        paths: list[Path],
        config: OptimizationConfig,
        target_dir: Path | None = None,
    ) -> None:
        super().__init__()
        self.signals = _BatchOptimizationSignals()
        self._paths = list(paths)
        self._config = config
        self._target_dir = target_dir
        self._cancelled = False
        self.setAutoDelete(True)

    def cancel(self) -> None:
        """Request cancellation; the worker stops at the next progress tick."""
        self._cancelled = True

    def run(self) -> None:
        try:
            results = optimize_batch(
                self._paths,
                config=self._config,
                progress=self._on_progress,
                target_dir=self._target_dir,
            )
            if not self._cancelled:
                self.signals.finished.emit(results)
        except _Cancelled:
            pass
        except Exception as exc:
            if not self._cancelled:
                self.signals.error.emit(str(exc))

    def _on_progress(self, value: float) -> None:
        if self._cancelled:
            raise _Cancelled()
        self.signals.progress.emit(value)
