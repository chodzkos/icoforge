"""Icon extraction from Windows PE files (EXE, DLL, OCX, …).

Requires the optional ``exe`` extra::

    pip install icoforge[exe]

Algorithm
---------
1. Parse the PE resource directory to find all RT_GROUP_ICON entries.
2. For each group, decode the GRPICONDIR header to enumerate the individual
   RT_ICON frames referenced by ID.
3. Assemble a valid ICO byte-stream from the individual RT_ICON data blobs.
4. Return the assembled ICO bytes - callers can write them to disk or pass
   them to Pillow / icoforge directly.
"""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

from icoforge.core import limits

# RT_* resource type IDs (Windows SDK winuser.h)
_RT_ICON = 3
_RT_GROUP_ICON = 14


class ExeExtractError(Exception):
    """Raised when icon extraction cannot proceed."""


def extract_icons_from_exe(path: Path) -> list[bytes]:
    """Extract all icon groups from a Windows PE file.

    Args:
        path: Path to the EXE / DLL / OCX file.

    Returns:
        A list of raw ICO byte-strings, one per RT_GROUP_ICON resource.
        The list is empty when the file contains no icon resources.

    Raises:
        FileNotFoundError: *path* does not exist.
        ExeExtractError: The file is not a valid PE, is protected/packed,
            or its resource section cannot be parsed.
    """
    if not path.exists():
        raise FileNotFoundError(path)

    limits.check_file_size(path, limits.MAX_PE_BYTES)

    try:
        import pefile  # lazy import; pefile is an optional dependency
    except ImportError as exc:
        raise ExeExtractError("pefile is not installed. Run: pip install icoforge[exe]") from exc

    try:
        pe = pefile.PE(str(path), fast_load=False)
    except pefile.PEFormatError as exc:
        raise ExeExtractError(f"Not a valid PE file: {exc}") from exc
    except Exception as exc:
        raise ExeExtractError(f"Cannot open PE file: {exc}") from exc

    if not hasattr(pe, "DIRECTORY_ENTRY_RESOURCE"):
        return []

    # Index individual RT_ICON blobs by their resource ID so we can look
    # them up when assembling each group.
    icon_data: dict[int, bytes] = _collect_rt_icons(pe)

    result: list[bytes] = []
    for resource_type in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if _res_id(resource_type) != _RT_GROUP_ICON:
            continue
        for name_entry in resource_type.directory.entries:
            for lang_entry in name_entry.directory.entries:
                offset = lang_entry.data.struct.OffsetToData
                size = lang_entry.data.struct.Size
                raw = pe.get_data(offset, size)
                try:
                    ico = _build_ico(raw, icon_data)
                except (struct.error, KeyError, ValueError):
                    continue  # malformed group — skip
                result.append(ico)
    return result


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _res_id(entry: object) -> int:
    """Return the numeric ID of a resource directory entry."""
    # pefile represents the id as entry.id (int) or entry.name (bytes-like)
    entry_id = getattr(entry, "id", None)
    return int(entry_id) if entry_id is not None else -1


def _collect_rt_icons(pe: Any) -> dict[int, bytes]:
    """Build a mapping from RT_ICON resource ID → raw pixel data."""
    icons: dict[int, bytes] = {}
    for resource_type in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if _res_id(resource_type) != _RT_ICON:
            continue
        for name_entry in resource_type.directory.entries:
            icon_id = _res_id(name_entry)
            for lang_entry in name_entry.directory.entries:
                offset = lang_entry.data.struct.OffsetToData
                size = lang_entry.data.struct.Size
                icons[icon_id] = pe.get_data(offset, size)
                break  # first language is enough
    return icons


# GRPICONDIR / GRPICONDIRENTRY layout (as stored in RT_GROUP_ICON)
# GRPICONDIR:  reserved(2) type(2) count(2)
# GRPICONDIRENTRY per frame:
#   width(1) height(1) colorCount(1) reserved(1)
#   planes(2) bitCount(2) bytesInRes(4) id(2)
_GRPICONDIR_HDR = struct.Struct("<HHH")
_GRPICONDIRENTRY = struct.Struct("<BBBBHHI H")  # 14 bytes (note: id is WORD, not DWORD)

# Standard ICO on-disk layout
# ICONDIR:  reserved(2) type(2) count(2)
# ICONDIRENTRY per frame:
#   width(1) height(1) colorCount(1) reserved(1)
#   planes(2) bitCount(2) bytesInRes(4) imageOffset(4)
_ICONDIRENTRY = struct.Struct("<BBBBHHI I")  # 16 bytes


def _build_ico(group_raw: bytes, icon_data: dict[int, bytes]) -> bytes:
    """Assemble a valid ICO byte-stream from a RT_GROUP_ICON blob."""
    reserved, res_type, count = _GRPICONDIR_HDR.unpack_from(group_raw, 0)
    if reserved != 0 or res_type != 1:
        raise ValueError("Invalid GRPICONDIR header")

    # Parse all GRPICONDIRENTRY records
    entries: list[tuple[int, int, int, int, int, int, int, int]] = []
    offset = _GRPICONDIR_HDR.size
    for _ in range(count):
        w, h, cc, res, planes, bc, size, icon_id = _GRPICONDIRENTRY.unpack_from(group_raw, offset)
        entries.append((w, h, cc, res, planes, bc, size, icon_id))
        offset += _GRPICONDIRENTRY.size

    # Collect raw image data blobs (only frames we actually have data for)
    frames: list[tuple[tuple[int, int, int, int, int, int, int, int], bytes]] = []
    for entry in entries:
        icon_id = entry[7]
        if icon_id not in icon_data:
            continue
        frames.append((entry, icon_data[icon_id]))

    if not frames:
        raise ValueError("No matching RT_ICON data found")

    # Build ICO: fixed header + per-frame directory + raw image data
    header = struct.pack("<HHH", 0, 1, len(frames))
    dir_size = len(frames) * _ICONDIRENTRY.size
    data_offset = len(header) + dir_size

    directory = bytearray()
    image_blobs = bytearray()
    for (w, h, cc, res, planes, bc, _size, _icon_id), blob in frames:
        directory += _ICONDIRENTRY.pack(w, h, cc, res, planes, bc, len(blob), data_offset)
        data_offset += len(blob)
        image_blobs += blob

    return header + bytes(directory) + bytes(image_blobs)
