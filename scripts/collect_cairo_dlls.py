"""Collect libcairo-2.dll and all transitive MSYS2/MinGW deps into scripts/cairo_dlls/.

Usage (from repo root, in a MSYS2 MINGW64 shell or after msys2/setup-msys2 in CI):
    python scripts/collect_cairo_dlls.py [--msys2-bin C:/msys64/mingw64/bin]

The script uses ``ldd`` (available in MSYS2) to walk the DLL dependency tree
recursively.  Only DLLs that live inside *msys2_bin* are copied - Windows system
DLLs (kernel32, ntdll, msvcrt, …) are not present there and are therefore skipped.

Output: scripts/cairo_dlls/  (gitignored)
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MSYS2_BIN = Path("C:/msys64/mingw64/bin")
CAIRO_DLLS_DIR = REPO_ROOT / "scripts" / "cairo_dlls"

# Windows system DLLs that are present on every machine - never copy these
_SYSTEM_DLL_PREFIXES = {
    "kernel32",
    "ntdll",
    "user32",
    "gdi32",
    "shell32",
    "ole32",
    "oleaut32",
    "advapi32",
    "ws2_32",
    "msvcrt",
    "ucrtbase",
    "vcruntime",
    "api-ms-win",
    "ext-ms-win",
    "msvcp",
}


def _is_system_dll(name: str) -> bool:
    low = name.lower()
    return any(low.startswith(p) for p in _SYSTEM_DLL_PREFIXES)


def _ldd_deps(dll_path: Path) -> list[str]:
    """Return immediate DLL deps of *dll_path* via ``ldd``."""
    try:
        result = subprocess.run(
            ["ldd", str(dll_path)],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []

    deps: list[str] = []
    # ldd output lines look like:
    #   libfoo-1.dll => /mingw64/bin/libfoo-1.dll (0x...)
    #   KERNEL32.dll => /c/Windows/System32/KERNEL32.dll (0x...)
    for line in result.stdout.splitlines():
        m = re.search(r"=>\s+(\S+)", line)
        if not m:
            continue
        target = m.group(1)
        name = Path(target).name
        if not _is_system_dll(name):
            deps.append(name)
    return deps


def collect(entry: str, src: Path, dst: Path, seen: set[str]) -> None:
    """Recursively copy *entry* and its MinGW deps from *src* into *dst*."""
    key = entry.lower()
    if key in seen:
        return
    seen.add(key)

    src_file = src / entry
    if not src_file.exists():
        return  # not a MinGW DLL - skip

    dst_file = dst / entry
    if not dst_file.exists():
        shutil.copy2(src_file, dst_file)
        size_kb = src_file.stat().st_size // 1024
        print(f"  + {entry:45s}  {size_kb:>6} KB")

    for dep in _ldd_deps(src_file):
        collect(dep, src, dst, seen)


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect Cairo DLLs from MSYS2")
    parser.add_argument(
        "--msys2-bin",
        type=Path,
        default=DEFAULT_MSYS2_BIN,
        help=f"Path to MSYS2 MinGW64 bin dir (default: {DEFAULT_MSYS2_BIN})",
    )
    args = parser.parse_args()
    msys2_bin: Path = args.msys2_bin

    entry = "libcairo-2.dll"
    if not (msys2_bin / entry).exists():
        print(
            f"ERROR: {entry} not found in {msys2_bin}\n"
            "Install it with:\n"
            "  pacman -S mingw-w64-x86_64-cairo\n"
            "or check --msys2-bin path.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not shutil.which("ldd"):
        print(
            "ERROR: ldd not found. Run this script inside a MSYS2 MinGW64 shell\n"
            "or after the msys2/setup-msys2 GitHub Action.",
            file=sys.stderr,
        )
        sys.exit(1)

    CAIRO_DLLS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Collecting Cairo DLLs from {msys2_bin} → {CAIRO_DLLS_DIR}")
    collect(entry, msys2_bin, CAIRO_DLLS_DIR, set())

    dlls = list(CAIRO_DLLS_DIR.glob("*.dll"))
    print(f"\nDone: {len(dlls)} DLL(s) collected.")


if __name__ == "__main__":
    main()
