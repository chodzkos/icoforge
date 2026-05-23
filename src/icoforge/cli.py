"""Command-line interface for IcoForge."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal, cast

import click

from icoforge.core import (
    FAVICON_SIZES,
    TRANSPARENT,
    WINDOWS_APP_SIZES,
    Background,
    Color,
    IcoConfig,
    OptimizationConfig,
    ResampleAlgorithm,
    SizeSpec,
)
from icoforge.core.converter import convert as run_convert
from icoforge.core.optimizer import optimize_png

_PRESETS: dict[str, tuple[SizeSpec, ...]] = {
    "windows": WINDOWS_APP_SIZES,
    "favicon": FAVICON_SIZES,
}

_BAR_WIDTH = 30

# Sizes for which `--source-N` flags are registered. Covers every size used
# by the built-in presets (windows + favicon).
_PER_SIZE_FLAG_SIZES: tuple[int, ...] = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)


def _per_size_source_options(func: Callable[..., Any]) -> Callable[..., Any]:
    """Attach ``--source-N`` options (one per :data:`_PER_SIZE_FLAG_SIZES`).

    Each flag, e.g. ``--source-16 hand.png``, overrides the source file used
    for that specific ICO entry. Sizes without an override fall back to the
    positional ``SOURCE`` argument.
    """
    for size in reversed(_PER_SIZE_FLAG_SIZES):
        func = click.option(
            f"--source-{size}",
            f"source_{size}",
            type=click.Path(exists=True, dir_okay=False, path_type=Path),
            default=None,
            help=(
                f"Source file for the {size}x{size} ICO entry only. "
                f"Overrides the global SOURCE for this one size."
            ),
        )(func)
    return func


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


def _collect_source_overrides(
    per_size_sources: dict[str, Path | None],
    parsed_sizes: tuple[SizeSpec, ...],
) -> dict[int, Path]:
    """Extract ``--source-N`` flags into a ``{size: path}`` map.

    Flags for sizes that are not part of ``parsed_sizes`` are rejected so the
    user gets immediate feedback instead of a silently-ignored override.
    """
    overrides: dict[int, Path] = {}
    requested_widths = {spec.width for spec in parsed_sizes}
    for key, path in per_size_sources.items():
        if path is None:
            continue
        size = int(key.removeprefix("source_"))
        if size not in requested_widths:
            raise click.BadParameter(
                f"--source-{size} was provided but {size}x{size} is not in --sizes "
                f"({sorted(requested_widths)}).",
                param_hint=f"'--source-{size}'",
            )
        overrides[size] = path
    return overrides


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
@click.option(
    "--bit-depth",
    type=click.Choice(["8", "24", "32"]),
    default="32",
    show_default=True,
    help="Colour depth for each ICO frame (8, 24, or 32 bits).",
)
@click.option(
    "--keep-aspect/--no-keep-aspect",
    default=True,
    show_default=True,
    help="Preserve source aspect ratio by letterboxing (default: on).",
)
@_per_size_source_options
def convert(
    source: Path,
    target: Path,
    sizes: str,
    resample: str,
    background: str,
    bit_depth: str,
    keep_aspect: bool,
    **per_size_sources: Path | None,
) -> None:
    """Convert SOURCE image to a multi-size ICO file at TARGET."""
    parsed_sizes = _parse_sizes(sizes)
    source_overrides = _collect_source_overrides(per_size_sources, parsed_sizes)
    bd = cast(Literal[8, 24, 32], int(bit_depth))
    size_specs = tuple(
        SizeSpec(
            s.width,
            s.height,
            bit_depth=bd,
            resample=s.resample,
            source_override=source_overrides.get(s.width, s.source_override),
        )
        for s in parsed_sizes
    )
    bg = _parse_background(background)
    config = IcoConfig(
        sizes=size_specs,
        resample=ResampleAlgorithm(resample),
        background=bg,
        preserve_aspect=keep_aspect,
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
    """Losslessly optimize a PNG file.

    Reduces file size without changing pixel data using pyoxipng compression.
    Optionally strips metadata chunks (tEXt, iTXt, zTXt, eXIf, tIME, pHYs).
    """
    click.echo(f"Optimizing {source.name}...")

    config = OptimizationConfig(
        level=level,
        strip_metadata=strip,
        use_zopfli=slow,
    )

    try:
        result = optimize_png(source, target=output, config=config)
    except FileNotFoundError as exc:
        click.echo()
        click.secho(f"Error: source file not found: {exc}", fg="red", err=True)
        raise SystemExit(1) from exc
    except ValueError as exc:
        click.echo()
        click.secho(f"Error: {exc}", fg="red", err=True)
        raise SystemExit(1) from exc

    click.echo()
    click.secho(f"✓ Wrote {result.target}", fg="green")
    click.secho(
        f"  {result.bytes_before:,} → {result.bytes_after:,} bytes "
        f"({result.saved_ratio * 100:.1f}% smaller)",
        fg="cyan",
    )


if __name__ == "__main__":
    main()
