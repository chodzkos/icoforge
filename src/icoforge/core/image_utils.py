"""Image utility functions."""

from __future__ import annotations

import numpy as np
from PIL import Image


def trim_transparency(
    image: Image.Image,
    *,
    threshold: int = 0,
    padding: int = 0,
) -> Image.Image:
    """Crop transparent borders from *image*.

    Finds the bounding box of pixels with alpha > *threshold* and crops to that
    region, then adds *padding* transparent pixels on each side.

    Args:
        image: RGBA source image.
        threshold: Pixels with alpha <= threshold are treated as transparent
            (0 = only fully transparent pixels are trimmed).
        padding: Pixels of transparent padding to add on each side after trim.

    Returns:
        Cropped and padded RGBA image.  Returns *image* unchanged if all
        pixels are fully transparent or no opaque content exists.
    """
    if image.mode != "RGBA":
        image = image.convert("RGBA")

    arr = np.asarray(image)
    alpha = arr[:, :, 3]
    mask = alpha > threshold

    if not mask.any():
        return image

    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    row_min = int(np.argmax(rows))
    row_max = int(len(rows) - 1 - int(np.argmax(rows[::-1])))
    col_min = int(np.argmax(cols))
    col_max = int(len(cols) - 1 - int(np.argmax(cols[::-1])))

    cropped = image.crop((col_min, row_min, col_max + 1, row_max + 1))

    if padding <= 0:
        return cropped

    pw = cropped.width + 2 * padding
    ph = cropped.height + 2 * padding
    canvas = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    canvas.paste(cropped, (padding, padding))
    return canvas
