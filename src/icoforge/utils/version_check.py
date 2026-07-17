"""IcoForge version + update-check identity — logic lives in chodzkos-gui-kit.

The reusable machinery (read installed version from package metadata, query the
GitHub Releases API, compare versions) is the kit's ``release`` module. This
module only carries what is genuinely IcoForge-specific — the distribution name,
the GitHub owner/repo, and the frozen-build fallback version — and delegates.
"""

from __future__ import annotations

from chodzkos_gui_kit import release

_DIST = "icoforge"
_OWNER = "chodzkos"
_REPO = "icoforge"


def _fallback() -> str:
    """Static version baked into the source tree (frozen builds without dist-info)."""
    try:
        from icoforge._version import __version__

        return __version__
    except Exception:
        return "0.0.0"


def app_version() -> str:
    """Installed IcoForge version (package metadata, with source-tree fallback)."""
    return release.installed_version(_DIST, fallback=_fallback())


def check_update() -> tuple[bool, str]:
    """Whether a newer IcoForge release exists on GitHub. Hits the network — run off-thread."""
    return release.check_github_update(_DIST, _OWNER, _REPO, fallback=_fallback())


def releases_url() -> str:
    """URL of the IcoForge GitHub releases page (link target for the update notice)."""
    return release.github_releases_url(_OWNER, _REPO)
