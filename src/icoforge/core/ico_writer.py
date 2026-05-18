"""ICO file writing.

Pillow has native ICO support: ``Image.save(path, format="ICO", sizes=[...])``.
For 256x256 entries Pillow embeds PNG (the modern convention); smaller sizes
go as DIB. We delegate to Pillow but expose a typed interface and validate.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from icoforge.core.models import SizeSpec


def write_ico(target: Path, images: list[tuple[Image.Image, SizeSpec]]) -> None:
    """Write a multi-size ICO file.

    Args:
        target: Path of the output ``.ico`` file.
        images: List of (image, spec) pairs. Each image must already be sized
            according to its spec (use ``converter`` for the high-level pipeline).

    Raises:
        ValueError: If images list is empty or sizes don't match specs.
    """
    if not images:
        raise ValueError("Cannot write an empty ICO file")

    # Validate that images match their specs - guards against accidental misuse.
    for img, spec in images:
        if img.size != (spec.width, spec.height):
            raise ValueError(
                f"Image size {img.size} does not match spec {(spec.width, spec.height)}"
            )

    # Pillow takes the largest image as the base and uses ``sizes=`` to derive
    # the rest. To respect per-size processing (different resample algos, future
    # per-size sources), we hand it the largest already-processed image and
    # supply the explicit list of sizes. Pillow will still re-encode each entry
    # but at this point all entries are at their target dimensions.
    images_sorted = sorted(images, key=lambda x: x[1].width * x[1].height, reverse=True)
    base_img, _base_spec = images_sorted[0]
    sizes = [(spec.width, spec.height) for _, spec in images_sorted]

    target.parent.mkdir(parents=True, exist_ok=True)
    base_img.save(target, format="ICO", sizes=sizes)

    # TODO(phase-1+): for true per-size control (different resamples, per-size
    # sources from phase 2), we'll need to build the ICO container manually
    # rather than going through ``Image.save``. The ICO format is documented:
    # https://en.wikipedia.org/wiki/ICO_(file_format)
