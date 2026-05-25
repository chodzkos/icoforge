"""Undo/redo commands for the pixel editor."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from PySide6.QtGui import QUndoCommand

if TYPE_CHECKING:
    from PIL import Image

PixelChange = tuple[int, int, tuple[int, int, int, int], tuple[int, int, int, int]]


def compute_pixel_diff(old_image: Image.Image, new_image: Image.Image) -> list[PixelChange]:
    """Return list of (x, y, old_rgba, new_rgba) for every changed pixel."""
    old_arr = np.array(old_image)
    new_arr = np.array(new_image)
    changed = np.any(old_arr != new_arr, axis=2)
    ys, xs = np.where(changed)
    result: list[PixelChange] = []
    for i in range(len(xs)):
        y_i, x_i = int(ys[i]), int(xs[i])
        old_c = (
            int(old_arr[y_i, x_i, 0]),
            int(old_arr[y_i, x_i, 1]),
            int(old_arr[y_i, x_i, 2]),
            int(old_arr[y_i, x_i, 3]),
        )
        new_c = (
            int(new_arr[y_i, x_i, 0]),
            int(new_arr[y_i, x_i, 1]),
            int(new_arr[y_i, x_i, 2]),
            int(new_arr[y_i, x_i, 3]),
        )
        result.append((x_i, y_i, old_c, new_c))
    return result


class DrawCommand(QUndoCommand):
    """Records per-pixel delta changes from a single drawing stroke."""

    def __init__(
        self,
        image: Image.Image,
        changes: list[PixelChange],
        description: str = "Draw",
    ) -> None:
        super().__init__(description)
        self._image = image
        self._changes = changes
        self._first_redo = True

    def undo(self) -> None:
        px = self._image.load()
        for x, y, old, _ in self._changes:
            px[x, y] = old

    def redo(self) -> None:
        if self._first_redo:
            # Changes are already applied to the image at push time.
            self._first_redo = False
            return
        px = self._image.load()
        for x, y, _, new in self._changes:
            px[x, y] = new


class FillCommand(DrawCommand):
    """Records pixel changes from a flood-fill operation."""

    def __init__(self, image: Image.Image, changes: list[PixelChange]) -> None:
        super().__init__(image, changes, "Fill")
