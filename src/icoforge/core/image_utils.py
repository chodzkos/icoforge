"""Image utility functions."""

from __future__ import annotations

import numpy as np
from PIL import Image


def trim_transparency(
    image: Image.Image,
    padding: int = 0,
    threshold: int = 0,
) -> Image.Image:
    """Crop transparent borders from *image*.

    Finds the bounding box of pixels with alpha > *threshold* and crops to that
    region, then adds *padding* transparent pixels on each side.

    Args:
        image: Source image (any mode; converted to RGBA internally).
        padding: Pixels of transparent padding to add on each side after trim.
        threshold: Pixels with alpha <= threshold are treated as transparent
            (0 = only fully transparent pixels are trimmed).

    Returns:
        Cropped and padded RGBA image.  Result size is (content + 2*padding).
        Returns a 1x1 transparent image if all pixels are transparent.
    """
    rgba = image.convert("RGBA")
    alpha = np.array(rgba)[:, :, 3]

    rows = np.any(alpha > threshold, axis=1)
    cols = np.any(alpha > threshold, axis=0)

    if not rows.any():
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))

    top = int(np.argmax(rows))
    bottom = int(len(rows) - np.argmax(rows[::-1]))
    left = int(np.argmax(cols))
    right = int(len(cols) - np.argmax(cols[::-1]))

    cropped = rgba.crop((left, top, right, bottom))

    if padding == 0:
        return cropped

    new_w = cropped.width + 2 * padding
    new_h = cropped.height + 2 * padding
    result = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))
    result.paste(cropped, (padding, padding))
    return result
