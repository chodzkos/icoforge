"""Programmatic startup templates for NewIcoDialog."""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from icoforge.core.models import SizeSpec

TEMPLATE_WINDOWS_APP = "windows_app"
TEMPLATE_FAVICON = "favicon"
TEMPLATE_CURSOR = "cursor"

_TEMPLATE_LABELS: dict[str, str] = {
    TEMPLATE_WINDOWS_APP: "Windows App Icon",
    TEMPLATE_FAVICON: "Favicon",
    TEMPLATE_CURSOR: "Cursor",
}

_TEMPLATE_SIZES: dict[str, list[int]] = {
    TEMPLATE_WINDOWS_APP: [16, 20, 24, 32, 40, 48, 64, 96, 128, 256],
    TEMPLATE_FAVICON: [16, 32, 48],
    TEMPLATE_CURSOR: [16, 32],
}


def _blue_gradient(size: int) -> Image.Image:
    """Blue gradient: top-left (0,102,204) to bottom-right (0,188,242)."""
    arr = np.zeros((size, size, 4), dtype=np.uint8)
    if size > 1:
        t = np.linspace(0.0, 1.0, size)
        tx, ty = np.meshgrid(t, t)
        blend: np.ndarray = (tx + ty) / 2.0
    else:
        blend = np.zeros((1, 1), dtype=np.float64)
    arr[..., 0] = 0
    arr[..., 1] = (102 + (188 - 102) * blend).astype(np.uint8)
    arr[..., 2] = (204 + (242 - 204) * blend).astype(np.uint8)
    arr[..., 3] = 255
    return Image.fromarray(arr, "RGBA")


def _warm_gradient(size: int) -> Image.Image:
    """Warm orange gradient: top-left (255,100,0) to bottom-right (255,200,50)."""
    arr = np.zeros((size, size, 4), dtype=np.uint8)
    if size > 1:
        t = np.linspace(0.0, 1.0, size)
        tx, ty = np.meshgrid(t, t)
        blend: np.ndarray = (tx + ty) / 2.0
    else:
        blend = np.zeros((1, 1), dtype=np.float64)
    arr[..., 0] = 255
    arr[..., 1] = (100 + 100 * blend).astype(np.uint8)
    arr[..., 2] = (50 * blend).astype(np.uint8)
    arr[..., 3] = 255
    return Image.fromarray(arr, "RGBA")


def _cursor_arrow(size: int) -> Image.Image:
    """Draw a simple arrow cursor: white fill with dark outline."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    scale = (size - 1) / 15.0
    points = [
        (0, 0),
        (0, int(10 * scale)),
        (int(3 * scale), int(7 * scale)),
        (int(6 * scale), int(13 * scale)),
        (int(8 * scale), int(12 * scale)),
        (int(5 * scale), int(6 * scale)),
        (int(9 * scale), int(6 * scale)),
    ]
    draw.polygon(points, fill=(255, 255, 255, 255), outline=(50, 50, 50, 255))
    return img


_BUILDERS = {
    TEMPLATE_WINDOWS_APP: _blue_gradient,
    TEMPLATE_FAVICON: _warm_gradient,
    TEMPLATE_CURSOR: _cursor_arrow,
}


def template_label(template_id: str) -> str:
    """Return the human-readable label for a template ID."""
    return _TEMPLATE_LABELS[template_id]


def template_sizes(template_id: str) -> list[int]:
    """Return the list of icon sizes for a template ID."""
    return _TEMPLATE_SIZES[template_id]


def build_template_frames(template_id: str) -> list[tuple[Image.Image, SizeSpec]]:
    """Build all frames for the given startup template.

    Args:
        template_id: One of TEMPLATE_WINDOWS_APP, TEMPLATE_FAVICON, TEMPLATE_CURSOR.

    Returns:
        List of (image, SizeSpec) pairs sorted by ascending size.

    Raises:
        ValueError: Unknown template_id.
    """
    if template_id not in _BUILDERS:
        raise ValueError(f"Unknown template: {template_id!r}")
    builder = _BUILDERS[template_id]
    sizes = sorted(_TEMPLATE_SIZES[template_id])
    return [(builder(s), SizeSpec(s, s)) for s in sizes]
