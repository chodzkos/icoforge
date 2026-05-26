"""Build script: PyInstaller onedir bundle + portable ZIP.

Usage (from repo root, with PyInstaller installed):
    python scripts/build_windows.py

Outputs in dist/:
    IcoForge/                    - onedir build (used by the installer)
    IcoForge-portable/           - copy with portable.txt
    IcoForge-portable-X.Y.Z.zip - ready-to-ship portable archive
"""

from __future__ import annotations

import importlib.metadata
import shutil
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = REPO_ROOT / "dist"
APP_NAME = "IcoForge"


def _version() -> str:
    try:
        return importlib.metadata.version("icoforge")
    except importlib.metadata.PackageNotFoundError:
        return "0.0.0"


def _run_pyinstaller() -> None:
    import subprocess
    import sys

    translations_src = REPO_ROOT / "src" / "icoforge" / "translations"
    add_data = f"{translations_src}{':' if sys.platform != 'win32' else ';'}icoforge/translations"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name",
        APP_NAME,
        "--distpath",
        str(DIST_DIR),
        "--add-data",
        add_data,
        "--hidden-import",
        "icoforge.core.heic_loader",
        str(REPO_ROOT / "src" / "icoforge" / "__main__.py"),
    ]
    subprocess.run(cmd, check=True, cwd=REPO_ROOT)


def _build_portable(version: str) -> Path:
    src = DIST_DIR / APP_NAME
    portable_dir = DIST_DIR / f"{APP_NAME}-portable"
    zip_path = DIST_DIR / f"{APP_NAME}-portable-{version}.zip"

    if portable_dir.exists():
        shutil.rmtree(portable_dir)
    shutil.copytree(src, portable_dir)
    (portable_dir / "portable.txt").write_text(
        "This file enables portable mode: settings are stored in the 'settings' "
        "subfolder next to the executable.\n",
        encoding="utf-8",
    )

    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in sorted(portable_dir.rglob("*")):
            zf.write(file, file.relative_to(DIST_DIR))

    return zip_path


def main() -> None:
    version = _version()
    print(f"Building IcoForge {version}")

    print("Running PyInstaller…")
    _run_pyinstaller()

    print("Building portable bundle…")
    zip_path = _build_portable(version)
    print(f"Portable archive: {zip_path}")

    print("Done.")


if __name__ == "__main__":
    main()
