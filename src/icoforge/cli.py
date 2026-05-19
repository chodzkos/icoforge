"""Command-line interface for IcoForge."""

from __future__ import annotations

from pathlib import Path

import click

from icoforge.core import (
    TRANSPARENT,
    WINDOWS_APP_SIZES,
    Background,
    Color,
    IcoConfig,
    ResampleAlgorithm,
    SizeSpec,
)
from icoforge.core.converter import convert as run_convert


def _parse_sizes(spec: str) -> tuple[SizeSpec, ...]:
    """Parse ``16,32,48,256`` into a tuple of SizeSpec."""
    sizes = []
    for chunk in spec.split(","):
        n = int(chunk.strip())
        sizes.append(SizeSpec(n, n))
    return tuple(sizes)


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
    help="Comma-separated list of sizes (e.g. 16,32,48,256). Use 'windows' for the full Windows set.",
)
@click.option(
    "--resample",
    type=click.Choice([a.value for a in ResampleAlgorithm]),
    default=ResampleAlgorithm.LANCZOS.value,
    help="Resampling algorithm.",
)
@click.option(
    "--background",
    default="transparent",
    help="Background color for sources without alpha. 'transparent' or hex like '#ffffff'.",
)
def convert(
    source: Path,
    target: Path,
    sizes: str,
    resample: str,
    background: str,
) -> None:
    """Convert SOURCE image to multi-size ICO at TARGET."""
    size_specs = WINDOWS_APP_SIZES if sizes == "windows" else _parse_sizes(sizes)

    bg = _parse_background(background)

    config = IcoConfig(
        sizes=size_specs,
        resample=ResampleAlgorithm(resample),
        background=bg,
    )

    def progress(value: float) -> None:
        click.echo(f"\r  progress: {value * 100:5.1f}%", nl=False)

    run_convert(source, target, config, progress=progress)
    click.echo()
    click.secho(f"Wrote {target}", fg="green")


@main.command()
@click.argument("source", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--output", "-o", type=click.Path(dir_okay=False, path_type=Path), default=None)
@click.option("--level", type=click.IntRange(0, 6), default=4)
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


def _parse_background(value: str) -> Background:
    """Parse a background string into a Background value."""
    if value == "transparent":
        return TRANSPARENT
    v = value.lstrip("#")
    if len(v) == 6:
        r, g, b = int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)
        return Color(r, g, b, 255)
    if len(v) == 8:
        r, g, b, a = int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16), int(v[6:8], 16)
        return Color(r, g, b, a)
    raise click.BadParameter(f"Cannot parse background color: {value}")


if __name__ == "__main__":
    main()
