"""Drawing tools for pixel editor."""

from __future__ import annotations

import collections
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from PIL import Image


class ToolType(Enum):
    """Available tool types."""

    PENCIL = "pencil"
    ERASER = "eraser"
    EYEDROPPER = "eyedropper"
    FILL = "fill"
    LINE = "line"
    RECT = "rect"
    SELECT = "select"


class Tool(ABC):
    """Abstract base class for drawing tools."""

    # Subclasses that render a live-preview overlay set this to True and
    # expose an ``overlay_image: Image.Image | None`` attribute.
    has_overlay: bool = False

    def __init__(self, image: Image.Image) -> None:
        """Initialize tool with image reference.

        Args:
            image: PIL Image in RGBA mode to draw on.
        """
        self.image = image
        self.pixels: Any = image.load()
        self.width, self.height = image.size

    @abstractmethod
    def on_press(self, x: int, y: int) -> None:
        """Handle mouse press at pixel coordinates."""

    @abstractmethod
    def on_move(self, x: int, y: int) -> None:
        """Handle mouse move at pixel coordinates."""

    @abstractmethod
    def on_release(self, x: int, y: int) -> None:
        """Handle mouse release at pixel coordinates."""

    def _clamp(self, x: int, y: int) -> tuple[int, int]:
        """Clamp coordinates to image bounds."""
        return max(0, min(x, self.width - 1)), max(0, min(y, self.height - 1))

    def _draw_circle(self, cx: int, cy: int, radius: int, color: tuple[int, int, int, int]) -> None:
        """Draw filled circle at position with given color."""
        r_sq = radius * radius
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx * dx + dy * dy <= r_sq:
                    x = cx + dx
                    y = cy + dy
                    if 0 <= x < self.width and 0 <= y < self.height:
                        self.pixels[x, y] = color


# ---------------------------------------------------------------------------
# Existing tools
# ---------------------------------------------------------------------------


class PixelTool(Tool):
    """Pencil tool for drawing with current color."""

    name = "Pencil"

    def __init__(
        self,
        image: Image.Image,
        color: tuple[int, int, int, int] = (0, 0, 0, 255),
        size: int = 1,
    ) -> None:
        super().__init__(image)
        self.color = color
        self.size = max(1, min(size, 8))

    def on_press(self, x: int, y: int) -> None:
        x, y = self._clamp(x, y)
        if self.size == 1:
            self.pixels[x, y] = self.color
        else:
            self._draw_circle(x, y, self.size - 1, self.color)

    def on_move(self, x: int, y: int) -> None:
        self.on_press(x, y)

    def on_release(self, x: int, y: int) -> None:
        pass

    def set_color(self, color: tuple[int, int, int, int]) -> None:
        """Set the drawing color."""
        self.color = color

    def set_size(self, size: int) -> None:
        """Set brush size."""
        self.size = max(1, min(size, 8))


class EraserTool(Tool):
    """Eraser tool that sets alpha to 0."""

    name = "Eraser"

    def __init__(self, image: Image.Image, size: int = 1) -> None:
        super().__init__(image)
        self.size = max(1, min(size, 8))

    def on_press(self, x: int, y: int) -> None:
        x, y = self._clamp(x, y)
        if self.size == 1:
            r, g, b, _ = self.pixels[x, y]
            self.pixels[x, y] = (r, g, b, 0)
        else:
            radius = self.size - 1
            r_sq = radius * radius
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    if dx * dx + dy * dy <= r_sq:
                        px = x + dx
                        py = y + dy
                        if 0 <= px < self.width and 0 <= py < self.height:
                            cr, cg, cb, _ = self.pixels[px, py]
                            self.pixels[px, py] = (cr, cg, cb, 0)

    def on_move(self, x: int, y: int) -> None:
        self.on_press(x, y)

    def on_release(self, x: int, y: int) -> None:
        pass

    def set_size(self, size: int) -> None:
        """Set eraser size."""
        self.size = max(1, min(size, 8))


class EyedropperTool(Tool):
    """Color picker tool - samples color from clicked pixel."""

    name = "Eyedropper"

    def __init__(self, image: Image.Image) -> None:
        super().__init__(image)
        self.picked_color: tuple[int, int, int, int] | None = None

    def on_press(self, x: int, y: int) -> None:
        x, y = self._clamp(x, y)
        self.picked_color = self.pixels[x, y]

    def on_move(self, x: int, y: int) -> None:
        self.on_press(x, y)

    def on_release(self, x: int, y: int) -> None:
        pass

    def get_color(self) -> tuple[int, int, int, int] | None:
        """Get the picked color."""
        return self.picked_color


# ---------------------------------------------------------------------------
# FillTool
# ---------------------------------------------------------------------------


class FillTool(Tool):
    """Flood fill (paint bucket) with adjustable colour tolerance.

    Tolerance 0 = exact colour match only; 100 = fill everything.
    BFS algorithm — no recursion, safe for all icon sizes.
    """

    name = "Fill"

    def __init__(
        self,
        image: Image.Image,
        color: tuple[int, int, int, int] = (0, 0, 0, 255),
        tolerance: int = 32,
    ) -> None:
        super().__init__(image)
        self.color = color
        self.tolerance = max(0, min(100, tolerance))

    def on_press(self, x: int, y: int) -> None:
        x, y = self._clamp(x, y)
        target: tuple[int, int, int, int] = self.pixels[x, y]
        if target == self.color:
            return
        self._bfs_fill(x, y, target)

    def on_move(self, x: int, y: int) -> None:
        pass

    def on_release(self, x: int, y: int) -> None:
        pass

    def set_color(self, color: tuple[int, int, int, int]) -> None:
        """Set fill colour."""
        self.color = color

    def set_tolerance(self, tolerance: int) -> None:
        """Set tolerance (0-100)."""
        self.tolerance = max(0, min(100, tolerance))

    def _bfs_fill(self, x: int, y: int, target: tuple[int, int, int, int]) -> None:
        queue: collections.deque[tuple[int, int]] = collections.deque([(x, y)])
        visited: set[tuple[int, int]] = {(x, y)}
        self.pixels[x, y] = self.color

        while queue:
            cx, cy = queue.popleft()
            for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                if (
                    (nx, ny) not in visited
                    and 0 <= nx < self.width
                    and 0 <= ny < self.height
                    and self._matches(self.pixels[nx, ny], target)
                ):
                    visited.add((nx, ny))
                    self.pixels[nx, ny] = self.color
                    queue.append((nx, ny))

    def _matches(self, c1: tuple[int, int, int, int], c2: tuple[int, int, int, int]) -> bool:
        if self.tolerance == 0:
            return c1 == c2
        # tolerance 100 => threshold 1000 (max RGBA delta is 4*255 = 1020)
        return sum(abs(a - b) for a, b in zip(c1, c2, strict=False)) <= self.tolerance * 10


# ---------------------------------------------------------------------------
# LineTool
# ---------------------------------------------------------------------------


class LineTool(Tool):
    """Straight line using Bresenham's algorithm with live overlay preview.

    The line is only committed to the canvas image on mouse-release; during
    the drag an ``overlay_image`` shows the preview without touching pixels.
    """

    name = "Line"
    has_overlay = True

    def __init__(
        self,
        image: Image.Image,
        color: tuple[int, int, int, int] = (0, 0, 0, 255),
        size: int = 1,
    ) -> None:
        super().__init__(image)
        self.color = color
        self.size = max(1, min(size, 8))
        self._start: tuple[int, int] | None = None
        self.overlay_image: Image.Image | None = None

    def on_press(self, x: int, y: int) -> None:
        self._start = self._clamp(x, y)
        self._update_overlay(self._start, self._start)

    def on_move(self, x: int, y: int) -> None:
        if self._start is not None:
            self._update_overlay(self._start, self._clamp(x, y))

    def on_release(self, x: int, y: int) -> None:
        if self._start is not None:
            end = self._clamp(x, y)
            self._bresenham(self._start[0], self._start[1], end[0], end[1], self.pixels)
        self._start = None
        self.overlay_image = None

    def set_color(self, color: tuple[int, int, int, int]) -> None:
        """Set line colour."""
        self.color = color

    def set_size(self, size: int) -> None:
        """Set line width."""
        self.size = max(1, min(size, 8))

    def _update_overlay(self, start: tuple[int, int], end: tuple[int, int]) -> None:
        self.overlay_image = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        self._bresenham(start[0], start[1], end[0], end[1], self.overlay_image.load())

    def _bresenham(self, x0: int, y0: int, x1: int, y1: int, target: Any) -> None:
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self._plot(x0, y0, target)
            if x0 == x1 and y0 == y1:
                break
            e2 = err * 2
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def _plot(self, x: int, y: int, target: Any) -> None:
        if self.size == 1:
            if 0 <= x < self.width and 0 <= y < self.height:
                target[x, y] = self.color
        else:
            r = self.size - 1
            r_sq = r * r
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if dx * dx + dy * dy <= r_sq:
                        px, py = x + dx, y + dy
                        if 0 <= px < self.width and 0 <= py < self.height:
                            target[px, py] = self.color


# ---------------------------------------------------------------------------
# RectTool
# ---------------------------------------------------------------------------


class RectTool(Tool):
    """Rectangle tool — toggle between outline-only and solid fill.

    Like LineTool, the shape is previewed in an overlay during drag and
    committed to the canvas only on release.
    """

    name = "Rect"
    has_overlay = True

    def __init__(
        self,
        image: Image.Image,
        color: tuple[int, int, int, int] = (0, 0, 0, 255),
        filled: bool = False,
    ) -> None:
        super().__init__(image)
        self.color = color
        self.filled = filled
        self._start: tuple[int, int] | None = None
        self.overlay_image: Image.Image | None = None

    def on_press(self, x: int, y: int) -> None:
        self._start = self._clamp(x, y)
        self._update_overlay(self._start, self._start)

    def on_move(self, x: int, y: int) -> None:
        if self._start is not None:
            self._update_overlay(self._start, self._clamp(x, y))

    def on_release(self, x: int, y: int) -> None:
        if self._start is not None:
            self._draw_rect(self._start, self._clamp(x, y), self.pixels)
        self._start = None
        self.overlay_image = None

    def set_color(self, color: tuple[int, int, int, int]) -> None:
        """Set rectangle colour."""
        self.color = color

    def _update_overlay(self, start: tuple[int, int], end: tuple[int, int]) -> None:
        self.overlay_image = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        self._draw_rect(start, end, self.overlay_image.load())

    def _draw_rect(self, start: tuple[int, int], end: tuple[int, int], target: Any) -> None:
        x1, x2 = sorted((start[0], end[0]))
        y1, y2 = sorted((start[1], end[1]))
        if self.filled:
            for y in range(y1, y2 + 1):
                for x in range(x1, x2 + 1):
                    if 0 <= x < self.width and 0 <= y < self.height:
                        target[x, y] = self.color
        else:
            for x in range(x1, x2 + 1):
                if 0 <= x < self.width:
                    if 0 <= y1 < self.height:
                        target[x, y1] = self.color
                    if 0 <= y2 < self.height:
                        target[x, y2] = self.color
            for y in range(y1 + 1, y2):
                if 0 <= y < self.height:
                    if 0 <= x1 < self.width:
                        target[x1, y] = self.color
                    if 0 <= x2 < self.width:
                        target[x2, y] = self.color


# ---------------------------------------------------------------------------
# SelectTool
# ---------------------------------------------------------------------------


class SelectTool(Tool):
    """Rectangular selection with marching-ants animation and clipboard.

    Image data is never modified by press/move/release — only by the explicit
    ``clear_selection_area`` and ``paste`` helpers called from the editor.
    """

    name = "Select"
    has_overlay = True

    def __init__(self, image: Image.Image) -> None:
        super().__init__(image)
        self._start: tuple[int, int] | None = None
        self.selection: tuple[int, int, int, int] | None = None  # x1,y1,x2,y2
        self._clipboard: Image.Image | None = None
        self._dash_offset: int = 0
        self.overlay_image: Image.Image = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))

    def on_press(self, x: int, y: int) -> None:
        self._start = self._clamp(x, y)
        self.selection = None
        self._redraw_overlay()

    def on_move(self, x: int, y: int) -> None:
        if self._start is not None:
            x, y = self._clamp(x, y)
            x1, x2 = sorted((self._start[0], x))
            y1, y2 = sorted((self._start[1], y))
            self.selection = (x1, y1, x2, y2)
            self._redraw_overlay()

    def on_release(self, x: int, y: int) -> None:
        if self._start is not None:
            x, y = self._clamp(x, y)
            x1, x2 = sorted((self._start[0], x))
            y1, y2 = sorted((self._start[1], y))
            self.selection = (x1, y1, x2, y2) if (x2 > x1 or y2 > y1) else None
        self._start = None
        self._redraw_overlay()

    def tick_animation(self) -> None:
        """Advance marching-ants dash offset by one step."""
        self._dash_offset = (self._dash_offset + 1) % 8
        self._redraw_overlay()

    def clear_selection(self) -> None:
        """Drop the current selection rectangle."""
        self.selection = None
        self._redraw_overlay()

    def get_selected_image(self) -> Image.Image | None:
        """Return a copy of the pixels inside the selection."""
        if self.selection is None:
            return None
        x1, y1, x2, y2 = self.selection
        return self.image.crop((x1, y1, x2 + 1, y2 + 1))

    def clear_selection_area(self) -> None:
        """Fill selected pixels with fully transparent colour (used by cut)."""
        if self.selection is None:
            return
        x1, y1, x2, y2 = self.selection
        for y in range(y1, y2 + 1):
            for x in range(x1, x2 + 1):
                if 0 <= x < self.width and 0 <= y < self.height:
                    self.pixels[x, y] = (0, 0, 0, 0)

    def paste(self, clip: Image.Image, x: int, y: int) -> None:
        """Sprite-aware paste: skip fully transparent source pixels."""
        clip_rgba = clip.convert("RGBA")
        for py in range(clip_rgba.height):
            for px in range(clip_rgba.width):
                src = clip_rgba.getpixel((px, py))
                if src[3] > 0:
                    dx, dy = x + px, y + py
                    if 0 <= dx < self.width and 0 <= dy < self.height:
                        self.pixels[dx, dy] = src

    @property
    def clipboard(self) -> Image.Image | None:
        return self._clipboard

    @clipboard.setter
    def clipboard(self, value: Image.Image | None) -> None:
        self._clipboard = value

    def _redraw_overlay(self) -> None:
        self.overlay_image = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        if self.selection is not None:
            self._draw_marching_ants()

    def _draw_marching_ants(self) -> None:
        if self.selection is None:
            return
        x1, y1, x2, y2 = self.selection
        pix: Any = self.overlay_image.load()

        perimeter: list[tuple[int, int]] = []
        for x in range(x1, x2 + 1):
            perimeter.append((x, y1))
        for y in range(y1 + 1, y2 + 1):
            perimeter.append((x2, y))
        for x in range(x2 - 1, x1 - 1, -1):
            perimeter.append((x, y2))
        for y in range(y2 - 1, y1, -1):
            perimeter.append((x1, y))

        for i, (x, y) in enumerate(perimeter):
            if 0 <= x < self.width and 0 <= y < self.height:
                white = ((i + self._dash_offset) // 4) % 2 == 0
                pix[x, y] = (255, 255, 255, 255) if white else (0, 0, 0, 255)
