# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for IcoForge – onedir, windowed, UPX-compressed."""

from pathlib import Path

ROOT = Path(SPECPATH)  # noqa: F821  – SPECPATH injected by PyInstaller

# ---------------------------------------------------------------------------
# Data files to bundle
# ---------------------------------------------------------------------------
datas = [
    # Qt translation files for Polish/English UI
    (str(ROOT / "src" / "icoforge" / "translations"), "icoforge/translations"),
]

# Include non-empty assets directory if it ever gains content
_assets = ROOT / "assets"
if any(p for p in _assets.iterdir() if p.name != ".gitkeep"):
    datas.append((str(_assets), "assets"))

# ---------------------------------------------------------------------------
# Hidden imports (conditionally imported at runtime)
# ---------------------------------------------------------------------------
hidden_imports = [
    "icoforge.core.heic_loader",
    # optional feature modules – silently absent if package not installed;
    # rembg/onnxruntime are excluded here because their DLL-heavy imports
    # crash PyInstaller's analysis child process – PyInstaller picks them up
    # automatically from the installed site-packages when present
    "pillow_heif",
    "pefile",
]

block_cipher = None

a = Analysis(
    [str(ROOT / "src" / "icoforge" / "__main__.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "unittest", "test"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="IcoForge",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=["vcruntime140.dll", "ucrtbase.dll"],
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "icoForge.ico"),
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=["vcruntime140.dll", "ucrtbase.dll"],
    name="IcoForge",
)
