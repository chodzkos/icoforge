"""Drawing tools for pixel editor."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum

from PIL import Image


class ToolType(Enum):
    """Available tool types."""

    PENCIL = "pencil"
    ERASER = "eraser"
    EYEDROPPER = "eyedropper"


class Tool(ABC):
    """Abstract base class for drawing tools."""

    def __init__(self, image: Image.Image) -> None:
        """Initialize tool with image reference.

        Args:
            image: PIL Image in RGBA mode to draw on.
        """
        self.image = image
        self.pixels = image.load()
        self.width, self.height = image.size

    @abstractmethod
    def on_press(self, x: int, y: int) -> None:
        """Handle mouse press at pixel coordinates.

        Args:
            x: Pixel x coordinate (0-width).
            y: Pixel y coordinate (0-height).
        """
        pass

    @abstractmethod
    def on_move(self, x: int, y: int) -> None:
        """Handle mouse move at pixel coordinates.

        Args:
            x: Pixel x coordinate.
            y: Pixel y coordinate.
        """
        pass

    @abstractmethod
    def on_release(self, x: int, y: int) -> None:
        """Handle mouse release at pixel coordinates.

        Args:
            x: Pixel x coordinate.
            y: Pixel y coordinate.
        """
        pass

    def _clamp(self, x: int, y: int) -> tuple[int, int]:
        """Clamp coordinates to image bounds."""
        x = max(0, min(x, self.width - 1))
        y = max(0, min(y, self.height - 1))
        return x, y

    def _draw_circle(self, cx: int, cy: int, radius: int, color: tuple) -> None:
        """Draw filled circle at position with given color.

        Args:
            cx: Center x.
            cy: Center y.
            radius: Circle radius in pixels.
            color: RGBA tuple (r, g, b, a).
        """
        r_sq = radius * radius
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx * dx + dy * dy <= r_sq:
                    x = cx + dx
                    y = cy + dy
                    if 0 <= x < self.width and 0 <= y < self.height:
                        self.pixels[x, y] = color


class PixelTool(Tool):
    """Pencil tool for drawing with current color."""

    def __init__(self, image: Image.Image, color: tuple = (0, 0, 0, 255), size: int = 1) -> None:
        """Initialize pencil tool.

        Args:
            image: PIL Image to draw on.
            color: RGBA color tuple.
            size: Brush size (1-8 pixels).
        """
        super().__init__(image)
        self.color = color
        self.size = max(1, min(size, 8))

    def on_press(self, x: int, y: int) -> None:
        """Draw at mouse press position."""
        x, y = self._clamp(x, y)
        if self.size == 1:
            self.pixels[x, y] = self.color
        else:
            self._draw_circle(x, y, self.size - 1, self.color)

    def on_move(self, x: int, y: int) -> None:
        """Draw while dragging."""
        self.on_press(x, y)

    def on_release(self, x: int, y: int) -> None:
        """No action on release."""
        pass

    def set_color(self, color: tuple) -> None:
        """Set the drawing color."""
        self.color = color

    def set_size(self, size: int) -> None:
        """Set brush size."""
        self.size = max(1, min(size, 8))


class EraserTool(Tool):
    """Eraser tool that sets alpha to 0."""

    def __init__(self, image: Image.Image, size: int = 1) -> None:
        """Initialize eraser tool.

        Args:
            image: PIL Image to erase from.
            size: Eraser size (1-8 pixels).
        """
        super().__init__(image)
        self.size = max(1, min(size, 8))

    def on_press(self, x: int, y: int) -> None:
        """Erase at mouse press position."""
        x, y = self._clamp(x, y)
        # Set alpha to 0 (fully transparent)
        if self.size == 1:
            r, g, b, _ = self.pixels[x, y]
            self.pixels[x, y] = (r, g, b, 0)
        else:
            # Erase circle
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
        """Erase while dragging."""
        self.on_press(x, y)

    def on_release(self, x: int, y: int) -> None:
        """No action on release."""
        pass

    def set_size(self, size: int) -> None:
        """Set eraser size."""
        self.size = max(1, min(size, 8))


class EyedropperTool(Tool):
    """Color picker tool - samples color from clicked pixel."""

    def __init__(self, image: Image.Image) -> None:
        """Initialize eyedropper tool.

        Args:
            image: PIL Image to sample from.
        """
        super().__init__(image)
        self.picked_color: tuple | None = None

    def on_press(self, x: int, y: int) -> None:
        """Pick color from clicked position."""
        x, y = self._clamp(x, y)
        self.picked_color = self.pixels[x, y]

    def on_move(self, x: int, y: int) -> None:
        """Pick color while dragging."""
        self.on_press(x, y)

    def on_release(self, x: int, y: int) -> None:
        """No action on release."""
        pass

    def get_color(self) -> tuple | None:
        """Get the picked color."""
        return self.picked_color
