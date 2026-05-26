"""Build script: PyInstaller onedir bundle + portable ZIP + Inno Setup installer.

Usage (from repo root, with PyInstaller installed):
    python scripts/build_windows.py            # all steps
    python scripts/build_windows.py --no-installer  # skip Inno Setup

Outputs in dist/:
    IcoForge/                    - onedir build (used by the installer)
    IcoForge-portable/           - copy with portable.txt
    IcoForge-portable-X.Y.Z.zip - ready-to-ship portable archive
    IcoForge-X.Y.Z-setup.exe    - Inno Setup installer (Windows only)
"""

from __future__ import annotations

import argparse
import importlib.metadata
import shutil
import subprocess
import sys
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
    """Build the onedir bundle using icoforge.spec."""
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--distpath",
        str(DIST_DIR),
        str(REPO_ROOT / "icoforge.spec"),
    ]
    subprocess.run(cmd, check=True, cwd=REPO_ROOT)


def _build_portable(version: str) -> Path:
    """Copy the onedir build, add portable.txt, pack to ZIP."""
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


def _run_inno_setup(version: str) -> Path:
    """Run Inno Setup compiler (iscc) to produce the installer EXE."""
    iss = REPO_ROOT / "installer" / "icoforge.iss"
    iscc = shutil.which("iscc") or r"C:\Program Files (x86)\Inno Setup 6\iscc.exe"

    if not Path(iscc).exists():
        raise FileNotFoundError(
            f"iscc not found at {iscc!r}. "
            "Install Inno Setup 6 from https://jrsoftware.org/isinfo.php"
        )

    cmd = [iscc, f"/DAppVersion={version}", str(iss)]
    subprocess.run(cmd, check=True, cwd=REPO_ROOT)

    return DIST_DIR / f"{APP_NAME}-{version}-setup.exe"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build IcoForge Windows packages")
    parser.add_argument(
        "--no-installer",
        action="store_true",
        help="Skip Inno Setup step (portable ZIP only)",
    )
    args = parser.parse_args()

    version = _version()
    print(f"Building IcoForge {version}")

    print("Running PyInstaller...")
    _run_pyinstaller()

    print("Building portable bundle...")
    zip_path = _build_portable(version)
    print(f"  -> {zip_path}")

    if not args.no_installer:
        print("Running Inno Setup...")
        try:
            exe_path = _run_inno_setup(version)
            print(f"  -> {exe_path}")
        except FileNotFoundError as e:
            print(f"  SKIPPED: {e}")

    print("Done.")


if __name__ == "__main__":
    main()
