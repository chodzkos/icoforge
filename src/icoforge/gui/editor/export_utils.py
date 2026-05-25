"""Export utilities: separate PNGs, PNG spritesheet, ICNS."""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

from icoforge.core.models import SizeSpec


def export_separate_pngs(frames: list[tuple[Image.Image, SizeSpec]], directory: Path) -> list[Path]:
    """Export each frame as icon_WxH.png in *directory*.

    Returns:
        List of saved paths, sorted by ascending size.
    """
    directory.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    for img, spec in sorted(frames, key=lambda f: f[1].width):
        path = directory / f"icon_{spec.width}x{spec.height}.png"
        img.save(path, format="PNG")
        saved.append(path)
    return saved


def export_spritesheet(
    frames: list[tuple[Image.Image, SizeSpec]],
    output_path: Path,
    *,
    columns: int = 4,
) -> Path:
    """Composite all frames into a single PNG spritesheet grid.

    Frames are sorted by ascending size. Each cell is the size of the
    largest frame; smaller frames are centered within their cell.

    Args:
        frames: Source frames to export.
        output_path: Where to write the PNG file.
        columns: Number of columns in the grid (default 4).

    Returns:
        The path of the saved spritesheet.

    Raises:
        ValueError: *frames* is empty.
    """
    if not frames:
        raise ValueError("No frames to export")
    sorted_frames = sorted(frames, key=lambda f: f[1].width)
    cols = min(columns, len(sorted_frames))
    rows = (len(sorted_frames) + cols - 1) // cols
    cell_w = max(spec.width for _, spec in sorted_frames)
    cell_h = max(spec.height for _, spec in sorted_frames)

    sheet = Image.new("RGBA", (cell_w * cols, cell_h * rows), (0, 0, 0, 0))
    for i, (img, _) in enumerate(sorted_frames):
        col = i % cols
        row = i // cols
        x = col * cell_w + (cell_w - img.width) // 2
        y = row * cell_h + (cell_h - img.height) // 2
        sheet.paste(img, (x, y), img)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, format="PNG")
    return output_path


def export_icns(frames: list[tuple[Image.Image, SizeSpec]], output_path: Path) -> Path:
    """Export frames as a macOS ICNS file.

    Uses Pillow's built-in ICNS support. Frames are sorted by size before
    writing. Call :func:`icns_available` first to check support.

    Args:
        frames: Source frames (at least one required).
        output_path: Where to write the ICNS file.

    Returns:
        The path of the saved ICNS file.

    Raises:
        ValueError: *frames* is empty.
        Exception: Pillow cannot write ICNS on this platform.
    """
    if not frames:
        raise ValueError("No frames to export")
    sorted_frames = sorted(frames, key=lambda f: f[1].width)
    images = [img for img, _ in sorted_frames]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(output_path, format="ICNS", append_images=images[1:])
    return output_path


def icns_available() -> bool:
    """Return True if Pillow can write ICNS on this platform."""
    try:
        img = Image.new("RGBA", (16, 16), (0, 0, 0, 255))
        buf = io.BytesIO()
        img.save(buf, format="ICNS")
        return True
    except Exception:
        return False
