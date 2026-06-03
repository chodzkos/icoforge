"""Version introspection and GitHub Releases update check."""

from __future__ import annotations

import json
import urllib.request
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version

GITHUB_API_URL = "https://api.github.com/repos/chodzkos/icoforge/releases/latest"
_RELEASES_URL = "https://github.com/chodzkos/icoforge/releases"


def get_installed_version() -> str:
    """Return the installed package version string.

    Resolution order:
    1. ``importlib.metadata`` — works in dev and in PyInstaller bundles when
       ``copy_metadata("icoforge")`` is added to the spec's *datas*.
    2. ``icoforge._version.__version__`` — static fallback baked into the
       source tree; used when the .dist-info directory is absent (e.g. older
       bundles or running directly from source without ``pip install -e .``).

    Returns:
        Version string (e.g. ``"1.2.8"``), or ``"0.0.0"`` as a last resort.
    """
    try:
        return pkg_version("icoforge")
    except PackageNotFoundError:
        pass
    except Exception:
        pass
    try:
        from icoforge._version import __version__

        return __version__
    except Exception:
        return "0.0.0"


def get_latest_release_version(timeout: int = 5) -> str | None:
    """Fetch the latest release tag from GitHub Releases API.

    Args:
        timeout: Network timeout in seconds.

    Returns:
        Version string (e.g. ``"1.3.0"``), or ``None`` when the network is
        unavailable or the API response is malformed.
    """
    try:
        req = urllib.request.Request(
            GITHUB_API_URL,
            headers={"User-Agent": "IcoForge-VersionCheck"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data: dict[str, object] = json.loads(resp.read())
            tag = str(data.get("tag_name", ""))
            return tag.lstrip("v") or None
    except Exception:
        return None


def is_update_available() -> tuple[bool, str]:
    """Compare the installed version against the latest GitHub release.

    Returns:
        ``(True, "1.3.0")`` when a newer release is available,
        ``(False, "")`` otherwise (including when offline).
    """
    installed = get_installed_version()
    latest = get_latest_release_version()
    if not latest or installed == "nieznana":
        return False, ""
    try:
        from packaging.version import Version

        if Version(latest) > Version(installed):
            return True, latest
    except Exception:
        # packaging not available — plain string comparison as fallback
        if latest != installed:
            return True, latest
    return False, ""
