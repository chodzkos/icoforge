"""Color extraction utilities for the pixel editor."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image


def extract_dominant_colors(image: Image.Image, n: int = 32) -> list[tuple[int, int, int, int]]:
    """Extract the n most dominant colors from *image* using PIL quantize.

    Returns a list of RGBA tuples sorted by pixel frequency, padded to
    exactly *n* entries with opaque black if fewer unique colors exist.
    """
    from PIL import Image as PilImage

    n = max(1, min(n, 256))
    rgb = image.convert("RGB")
    quantized = rgb.quantize(colors=n, method=PilImage.Quantize.FASTOCTREE)
    palette_data = quantized.getpalette() or []  # flat [r, g, b, ...] x 256 entries

    # Count how often each palette index appears in the quantized image.
    counts: dict[int, int] = {}
    for idx in quantized.getdata():
        counts[idx] = counts.get(idx, 0) + 1

    result: list[tuple[int, int, int, int]] = []
    seen: set[tuple[int, int, int]] = set()
    for idx in sorted(counts, key=lambda i: -counts[i]):
        base = idx * 3
        if base + 2 >= len(palette_data):
            continue
        r, g, b = palette_data[base], palette_data[base + 1], palette_data[base + 2]
        if (r, g, b) not in seen:
            seen.add((r, g, b))
            result.append((r, g, b, 255))
        if len(result) >= n:
            break

    while len(result) < n:
        result.append((0, 0, 0, 255))

    return result
