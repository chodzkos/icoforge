"""Command-line interface for IcoForge."""

from __future__ import annotations

from pathlib import Path

import click

from icoforge.core import (
    FAVICON_SIZES,
    TRANSPARENT,
    WINDOWS_APP_SIZES,
    Background,
    Color,
    IcoConfig,
    ResampleAlgorithm,
    SizeSpec,
)
from icoforge.core.converter import convert as run_convert

_PRESETS: dict[str, tuple[SizeSpec, ...]] = {
    "windows": WINDOWS_APP_SIZES,
    "favicon": FAVICON_SIZES,
}

_BAR_WIDTH = 30


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_sizes(spec: str) -> tuple[SizeSpec, ...]:
    """Parse a sizes spec into a tuple of SizeSpec.

    Accepts a preset name (``windows``, ``favicon``) or a comma-separated
    list of integers, e.g. ``16,32,48,256``.
    """
    if spec in _PRESETS:
        return _PRESETS[spec]

    sizes: list[SizeSpec] = []
    for raw in spec.split(","):
        chunk = raw.strip()
        if not chunk:
            raise click.BadParameter(
                f"Empty segment in sizes spec: {spec!r}",
                param_hint="'--sizes'",
            )
        try:
            n = int(chunk)
        except ValueError:
            raise click.BadParameter(
                f"Expected an integer, got {chunk!r}. "
                "Use a comma-separated list like '16,32,48,256', "
                "or a preset: 'windows', 'favicon'.",
                param_hint="'--sizes'",
            ) from None
        try:
            sizes.append(SizeSpec(n, n))
        except ValueError as exc:
            raise click.BadParameter(str(exc), param_hint="'--sizes'") from exc

    if not sizes:
        raise click.BadParameter("At least one size is required.", param_hint="'--sizes'")

    return tuple(sizes)


def _parse_background(value: str) -> Background:
    """Parse a background string into a :data:`~icoforge.core.models.Background`."""
    if value == "transparent":
        return TRANSPARENT

    hex_str = value.lstrip("#")
    try:
        if len(hex_str) == 6:
            r, g, b = int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
            return Color(r, g, b, 255)
        if len(hex_str) == 8:
            r = int(hex_str[0:2], 16)
            g = int(hex_str[2:4], 16)
            b = int(hex_str[4:6], 16)
            a = int(hex_str[6:8], 16)
            return Color(r, g, b, a)
    except ValueError:
        pass

    raise click.BadParameter(
        f"Expected 'transparent' or a hex colour like '#ff0000' / '#ff0000ff', got {value!r}.",
        param_hint="'--background'",
    )


def _progress_callback(value: float) -> None:
    """Print an in-place ASCII progress bar to stdout."""
    filled = round(value * _BAR_WIDTH)
    bar = "#" * filled + "-" * (_BAR_WIDTH - filled)
    click.echo(f"\r[{bar}] {value * 100:5.1f}%  ", nl=False)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@click.group()
@click.version_option()
def main() -> None:
    """IcoForge - convert, optimize and edit ICO files."""


@main.command()
@click.argument("source", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("target", type=click.Path(dir_okay=False, path_type=Path))
@click.option(
    "--sizes",
    default="16,32,48,256",
    show_default=True,
    help=(
        "Comma-separated target sizes in pixels, e.g. '16,32,48,256'.  "
        "Presets: 'windows' (16,20,24,32,40,48,64,96,128,256), "
        "'favicon' (16,32,48)."
    ),
)
@click.option(
    "--resample",
    type=click.Choice([a.value for a in ResampleAlgorithm]),
    default=ResampleAlgorithm.LANCZOS.value,
    show_default=True,
    help="Resampling algorithm used when scaling the source image.",
)
@click.option(
    "--background",
    default="transparent",
    show_default=True,
    help=(
        "Background fill for source images without an alpha channel "
        "(e.g. JPEG).  Use 'transparent' or a hex colour like '#ffffff'."
    ),
)
def convert(
    source: Path,
    target: Path,
    sizes: str,
    resample: str,
    background: str,
) -> None:
    """Convert SOURCE image to a multi-size ICO file at TARGET."""
    size_specs = _parse_sizes(sizes)
    bg = _parse_background(background)
    config = IcoConfig(
        sizes=size_specs,
        resample=ResampleAlgorithm(resample),
        background=bg,
    )

    try:
        run_convert(source, target, config, progress=_progress_callback)
    except FileNotFoundError as exc:
        click.echo()
        click.secho(f"Error: source file not found: {exc}", fg="red", err=True)
        raise SystemExit(1) from exc
    except ValueError as exc:
        click.echo()
        click.secho(f"Error: {exc}", fg="red", err=True)
        raise SystemExit(1) from exc

    click.echo()
    click.secho(f"Wrote {target}", fg="green")


@main.command()
@click.argument("source", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--output", "-o", type=click.Path(dir_okay=False, path_type=Path), default=None)
@click.option("--level", type=click.IntRange(0, 6), default=4, show_default=True)
@click.option("--strip/--no-strip", default=True, help="Strip metadata chunks.")
@click.option("--slow", is_flag=True, help="Use Zopfli (slow, smaller output).")
def optimize(
    source: Path,
    output: Path | None,
    level: int,
    strip: bool,
    slow: bool,
) -> None:
    """Losslessly optimize a PNG file. (Phase 3)"""
    # TODO(phase-3): wire to icoforge.core.optimizer.optimize_png
    click.secho("optimize: not yet implemented (phase 3)", fg="yellow")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
