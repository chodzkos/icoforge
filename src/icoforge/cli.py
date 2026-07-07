"""Command-line interface for IcoForge."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
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
from icoforge.core.converter import render_frames as run_render
from icoforge.core.optimizer import optimize_batch, optimize_png
from icoforge.core.presets import BUILTIN_PRESETS, list_user_presets
from icoforge.core.presets import load_preset as load_user_preset

_PRESETS: dict[str, tuple[SizeSpec, ...]] = {
    "windows": WINDOWS_APP_SIZES,
    "favicon": FAVICON_SIZES,
}

_BAR_WIDTH = 30


def _load_named_preset(name: str) -> IcoConfig:
    """Load a preset by name: tries builtin first, then user presets.

    Args:
        name: Preset name as shown in ``presets list``.

    Returns:
        Corresponding IcoConfig.

    Raises:
        click.BadParameter: If no preset with that name exists.
    """
    if name in BUILTIN_PRESETS:
        return BUILTIN_PRESETS[name]
    try:
        return load_user_preset(name)
    except FileNotFoundError:
        pass
    available = list(BUILTIN_PRESETS) + list_user_presets()
    raise click.BadParameter(
        f"Unknown preset {name!r}. Available: {', '.join(available)}",
        param_hint="'--preset'",
    )


# Sizes for which `--source-N` flags are registered. Covers every size used
# by the built-in presets (windows + favicon).
_PER_SIZE_FLAG_SIZES: tuple[int, ...] = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)

# Default output sizes when the user omits --sizes.  The set depends on the
# target format: ICNS supports 16/32/64/128/256/512/1024 (no 48), while ICO/CUR
# conventionally include 48.
_DEFAULT_SIZES_RASTER = "16,32,48,256"  # .ico / .cur
_DEFAULT_SIZES_ICNS = "16,32,64,128,256,512"  # .icns


def _icns_sizes_from_preset(preset_name: str, widths: list[int]) -> list[int]:
    """Map a preset's sizes onto the ICNS-supported set.

    Presets such as "Windows App Icon" include sizes (20, 24, 40, 48, 96) that
    ICNS cannot store.  Drop the unsupported sizes with a warning; if none of
    the preset's sizes are valid for ICNS, fall back to the ICNS defaults.

    Args:
        preset_name: Name of the preset, used in the warning message.
        widths: Pixel sizes requested by the preset.

    Returns:
        The subset of *widths* valid for ICNS, or the ICNS defaults if empty.
    """
    from icoforge.core.icns_writer import _VALID_SIZES

    valid = [w for w in widths if w in _VALID_SIZES]
    dropped = [w for w in widths if w not in _VALID_SIZES]
    if dropped:
        click.secho(
            f"Warning: preset {preset_name!r} includes size(s) {dropped} unsupported by "
            f"ICNS; using {valid or 'ICNS defaults'} instead.",
            fg="yellow",
            err=True,
        )
    if not valid:
        return [int(s) for s in _DEFAULT_SIZES_ICNS.split(",")]
    return valid


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


def _explicitly_set(ctx: click.Context, name: str) -> bool:
    """Return ``True`` when option *name* was supplied on the command line or env.

    Used so ``--preset`` can start from the preset's full configuration and only
    override the fields the user explicitly provided, rather than clobbering them
    with option defaults.

    Args:
        ctx: The active Click context.
        name: The option's Python parameter name (e.g. ``"background"``).
    """
    from click.core import ParameterSource

    return ctx.get_parameter_source(name) in (
        ParameterSource.COMMANDLINE,
        ParameterSource.ENVIRONMENT,
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
    "--preset",
    default=None,
    metavar="NAME",
    help=(
        "Load a named preset (builtin or user) as the base configuration.  "
        "Use 'presets list' to see available names.  "
        "--sizes and --resample override the preset when also provided."
    ),
)
@click.option(
    "--sizes",
    default=None,
    show_default=False,
    help=(
        "Comma-separated target sizes in pixels, e.g. '16,32,48,256' (default when no "
        "--preset).  Presets: 'windows' (16,20,24,32,40,48,64,96,128,256), 'favicon' (16,32,48)."
    ),
)
@click.option(
    "--resample",
    type=click.Choice([a.value for a in ResampleAlgorithm]),
    default=None,
    show_default=False,
    help="Resampling algorithm (default: lanczos, or inherited from --preset).",
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
@click.option(
    "--hotspot",
    default=None,
    help=(
        "Cursor hotspot as 'X,Y' (e.g. '0,0').  "
        "Required when TARGET is a .cur file; ignored otherwise."
    ),
)
@click.option(
    "--auto-trim/--no-auto-trim",
    default=False,
    show_default=True,
    help="Crop transparent borders from the source before resizing.",
)
@click.option(
    "--trim-padding",
    type=click.IntRange(0),
    default=0,
    show_default=True,
    help="Pixels of transparent padding to add around the trimmed content.",
)
@click.option(
    "--remove-bg/--no-remove-bg",
    default=False,
    show_default=True,
    help=(
        "Remove image background using the U2-Net AI model (requires icoforge[bgremove]). "
        "First run downloads the model (~170 MB)."
    ),
)
@_per_size_source_options
@click.pass_context
def convert(
    ctx: click.Context,
    source: Path,
    target: Path,
    preset: str | None,
    sizes: str | None,
    resample: str | None,
    background: str,
    bit_depth: str,
    keep_aspect: bool,
    hotspot: str | None,
    auto_trim: bool,
    trim_padding: int,
    remove_bg: bool,
    **per_size_sources: Path | None,
) -> None:
    """Convert SOURCE image to a multi-size ICO, ICNS, or CUR file at TARGET.

    When TARGET ends with .icns the output is a macOS ICNS file.
    When TARGET ends with .cur the output is a Windows cursor file.
    Supported ICNS sizes: 16, 32, 64, 128, 256, 512, 1024.
    """
    suffix = target.suffix.lower()

    # Resolve sizes and resample: preset provides defaults, explicit --sizes
    # overrides.  When --sizes is omitted, the default size set depends on the
    # target format because ICNS supports a different set than ICO/CUR.
    base: IcoConfig | None = None
    resolved_sizes: str
    resolved_resample: str
    if preset:
        base = _load_named_preset(preset)
        resolved_resample = resample or base.resample.value
        if sizes:
            resolved_sizes = sizes
        else:
            preset_widths = [s.width for s in base.sizes]
            if suffix == ".icns":
                preset_widths = _icns_sizes_from_preset(preset, preset_widths)
            resolved_sizes = ",".join(str(w) for w in preset_widths)
    else:
        resolved_resample = resample or ResampleAlgorithm.LANCZOS.value
        if sizes:
            resolved_sizes = sizes
        elif suffix == ".icns":
            resolved_sizes = _DEFAULT_SIZES_ICNS
        else:
            resolved_sizes = _DEFAULT_SIZES_RASTER
    if suffix == ".icns":
        _convert_icns(source, target, resolved_sizes, resolved_resample, background, keep_aspect)
        return
    if suffix == ".cur":
        _convert_cur(
            source,
            target,
            resolved_sizes,
            resolved_resample,
            background,
            bit_depth,
            keep_aspect,
            hotspot,
        )
        return

    if remove_bg:
        from icoforge.core.bg_remover import is_available

        if not is_available():
            click.secho(
                "Error: --remove-bg requires rembg. Run: pip install icoforge[bgremove]",
                fg="red",
                err=True,
            )
            raise SystemExit(1)
        click.echo(
            "Uwaga: pierwsze uruchomienie pobierze model AI U2-Net (~170 MB).",
            err=True,
        )

    parsed_sizes = _parse_sizes(resolved_sizes)
    source_overrides = _collect_source_overrides(per_size_sources, parsed_sizes)

    # Choose the base SizeSpecs.  With a preset and no explicit --sizes, keep the
    # preset's full specs (non-square heights, per-size bit_depth and resample);
    # otherwise derive square specs from the resolved --sizes.
    base_specs = base.sizes if (base is not None and not sizes) else parsed_sizes

    # bit_depth: an explicit --bit-depth overrides every entry; otherwise each
    # spec keeps its own depth (from the preset or the SizeSpec default).
    bit_depth_override: Literal[8, 24, 32] | None = (
        cast(Literal[8, 24, 32], int(bit_depth)) if _explicitly_set(ctx, "bit_depth") else None
    )
    size_specs = tuple(
        replace(
            s,
            bit_depth=bit_depth_override if bit_depth_override is not None else s.bit_depth,
            source_override=source_overrides.get(s.width, s.source_override),
        )
        for s in base_specs
    )

    if base is not None:
        # Start from the preset's complete configuration and override only the
        # fields the user explicitly passed on the command line.
        config = replace(
            base,
            sizes=size_specs,
            resample=ResampleAlgorithm(resolved_resample),
            background=(
                _parse_background(background)
                if _explicitly_set(ctx, "background")
                else base.background
            ),
            preserve_aspect=(
                keep_aspect if _explicitly_set(ctx, "keep_aspect") else base.preserve_aspect
            ),
            auto_trim=auto_trim if _explicitly_set(ctx, "auto_trim") else base.auto_trim,
            auto_trim_padding=(
                trim_padding if _explicitly_set(ctx, "trim_padding") else base.auto_trim_padding
            ),
            remove_bg=remove_bg if _explicitly_set(ctx, "remove_bg") else base.remove_bg,
        )
    else:
        config = IcoConfig(
            sizes=size_specs,
            resample=ResampleAlgorithm(resolved_resample),
            background=_parse_background(background),
            preserve_aspect=keep_aspect,
            auto_trim=auto_trim,
            auto_trim_padding=trim_padding,
            remove_bg=remove_bg,
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
    except Exception as exc:
        # Catches BgRemoveError (and any other runtime failure)
        click.echo()
        click.secho(f"Error: {exc}", fg="red", err=True)
        raise SystemExit(1) from exc

    click.echo()
    click.secho(f"Wrote {target}", fg="green")


def _convert_icns(
    source: Path,
    target: Path,
    sizes: str,
    resample: str,
    background: str,
    keep_aspect: bool,
) -> None:
    """Render frames from *source* and write an ICNS file to *target*."""

    from icoforge.core.icns_writer import _VALID_SIZES, render_and_write_icns
    from icoforge.core.resampling import to_pillow

    # Parse sizes as plain ints (bypassing SizeSpec's 1-256 ICO restriction).
    raw_sizes: list[int] = []
    for chunk in sizes.split(","):
        chunk = chunk.strip()
        try:
            raw_sizes.append(int(chunk))
        except ValueError:
            click.secho(
                f"Error: expected an integer size, got {chunk!r}.",
                fg="red",
                err=True,
            )
            raise SystemExit(1) from None

    invalid = [s for s in raw_sizes if s not in _VALID_SIZES]
    if invalid:
        click.secho(
            f"Error: ICNS does not support size(s) {invalid}. Supported: {sorted(_VALID_SIZES)}.",
            fg="red",
            err=True,
        )
        raise SystemExit(1)

    pil_resample = to_pillow(ResampleAlgorithm(resample))
    bg = _parse_background(background)
    bg_tuple: tuple[int, int, int, int] = (
        (0, 0, 0, 0) if isinstance(bg, str) else (bg.r, bg.g, bg.b, bg.a)
    )

    try:
        render_and_write_icns(
            source,
            target,
            raw_sizes,
            resample=pil_resample,
            background=bg_tuple,
            preserve_aspect=keep_aspect,
            progress=_progress_callback,
        )
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
@click.argument(
    "paths",
    nargs=-1,
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option("--output", "-o", type=click.Path(dir_okay=False, path_type=Path), default=None)
@click.option("--level", type=click.IntRange(0, 6), default=4, show_default=True)
@click.option("--strip/--no-strip", default=True, help="Strip metadata chunks.")
@click.option("--slow", is_flag=True, help="Use Zopfli (slow, smaller output).")
@click.option("--in-place", is_flag=True, help="Overwrite source file(s) in-place.")
@click.option("--force", is_flag=True, help="Overwrite existing output file in default mode.")
def optimize(
    paths: tuple[Path, ...],
    output: Path | None,
    level: int,
    strip: bool,
    slow: bool,
    in_place: bool,
    force: bool,
) -> None:
    """Losslessly optimize PNG file(s).

    Reduces file size without changing pixel data using oxipng compression.
    Optionally strips metadata chunks (tEXt, iTXt, zTXt, eXIf, tIME, pHYs).

    \b
    Single file — three modes:
      (default)   Write <stem>.min.png next to the source. Source is NOT modified.
                  Use --force to overwrite if <stem>.min.png already exists.
      --in-place  Overwrite the source file.
      --output F  Write to path F.

    Multiple files:
      --in-place is required. Each file is optimized in-place.
      --output is not supported for multiple files.
    """
    if not paths:
        click.secho("Error: at least one PNG file required", fg="red", err=True)
        raise SystemExit(1)

    if output and len(paths) > 1:
        click.secho("Error: --output can only be used with a single file", fg="red", err=True)
        raise SystemExit(1)

    if in_place and output:
        click.secho("Error: --in-place and --output are mutually exclusive", fg="red", err=True)
        raise SystemExit(1)

    if len(paths) > 1 and not in_place:
        click.secho(
            "Error: optimizing multiple files requires --in-place.\n"
            "       Pass files one at a time to use the safe default (<stem>.min.png).",
            fg="red",
            err=True,
        )
        raise SystemExit(1)

    config = OptimizationConfig(
        level=level,
        strip_metadata=strip,
        use_zopfli=slow,
    )

    click.echo(f"Optimizing {len(paths)} file(s)...")
    click.echo()

    try:
        if len(paths) == 1:
            source = paths[0]
            if in_place:
                target: Path | None = source
            elif output:
                target = output
            else:
                target = source.parent / (source.stem + ".min.png")
                if target.exists() and not force:
                    click.secho(
                        f"Error: '{target}' already exists. "
                        "Use --force to overwrite or --in-place to optimize in-place.",
                        fg="red",
                        err=True,
                    )
                    raise SystemExit(1)
            click.echo(f"  {source.name}...", nl=False)
            result = optimize_png(source, target=target, config=config)
            click.echo(" ✓")
            click.secho(
                f"    {result.bytes_before:,} -> {result.bytes_after:,} bytes "
                f"({result.saved_ratio * 100:.1f}% smaller)",
                fg="cyan",
            )
            results = [result]
        else:
            results = optimize_batch(list(paths), config=config)
            for result in results:
                click.echo(f"  {result.source.name}...", nl=False)
                click.echo(" ✓")
                click.secho(
                    f"    {result.bytes_before:,} -> {result.bytes_after:,} bytes "
                    f"({result.saved_ratio * 100:.1f}% smaller)",
                    fg="cyan",
                )

    except FileNotFoundError as exc:
        click.echo()
        click.secho(f"Error: source file not found: {exc}", fg="red", err=True)
        raise SystemExit(1) from exc
    except ValueError as exc:
        click.echo()
        click.secho(f"Error: {exc}", fg="red", err=True)
        raise SystemExit(1) from exc

    # Print summary report
    click.echo()
    total_before = sum(r.bytes_before for r in results)
    total_after = sum(r.bytes_after for r in results)
    total_saved = total_before - total_after
    total_ratio = (total_saved / total_before * 100) if total_before > 0 else 0.0

    click.secho("Summary:", fg="green", bold=True)
    click.echo(
        f"  {len(results)} file(s): {total_before / 1e6:.1f} MB → "
        f"{total_after / 1e6:.1f} MB ({total_ratio:.1f}% smaller)"
    )


def _parse_hotspot(value: str | None) -> tuple[int, int]:
    """Parse '--hotspot X,Y' into a (x, y) tuple.

    Returns ``(0, 0)`` when *value* is ``None``.
    """
    if value is None:
        return (0, 0)
    parts = value.split(",")
    if len(parts) != 2:
        raise click.BadParameter(
            f"Expected 'X,Y', got {value!r}.",
            param_hint="'--hotspot'",
        )
    try:
        x, y = int(parts[0].strip()), int(parts[1].strip())
    except ValueError:
        raise click.BadParameter(
            f"Both X and Y must be integers, got {value!r}.",
            param_hint="'--hotspot'",
        ) from None
    if x < 0 or y < 0:
        raise click.BadParameter(
            f"Hotspot coordinates must be non-negative, got ({x}, {y}).",
            param_hint="'--hotspot'",
        )
    return (x, y)


def _convert_cur(
    source: Path,
    target: Path,
    sizes: str,
    resample: str,
    background: str,
    bit_depth: str,
    keep_aspect: bool,
    hotspot: str | None,
) -> None:
    """Render frames from *source* and write a Windows .cur file to *target*."""
    from icoforge.core.cur_writer import write_cur

    parsed_sizes = _parse_sizes(sizes)
    bd = cast(Literal[8, 24, 32], int(bit_depth))
    size_specs = tuple(
        SizeSpec(s.width, s.height, bit_depth=bd, resample=s.resample) for s in parsed_sizes
    )
    bg = _parse_background(background)
    config = IcoConfig(
        sizes=size_specs,
        resample=ResampleAlgorithm(resample),
        background=bg,
        preserve_aspect=keep_aspect,
    )
    hs = _parse_hotspot(hotspot)

    for spec in size_specs:
        if hs[0] >= spec.width or hs[1] >= spec.height:
            raise click.BadParameter(
                f"Hotspot {hs} is outside {spec.width}x{spec.height}.",
                param_hint="'--hotspot'",
            )

    try:
        frames = run_render(source, config, progress=_progress_callback)
    except FileNotFoundError as exc:
        click.echo()
        click.secho(f"Error: source file not found: {exc}", fg="red", err=True)
        raise SystemExit(1) from exc
    except ValueError as exc:
        click.echo()
        click.secho(f"Error: {exc}", fg="red", err=True)
        raise SystemExit(1) from exc

    pairs = list(zip(frames, size_specs, strict=False))
    write_cur(target, pairs, hotspot=hs)
    click.echo()
    click.secho(f"Wrote {target}", fg="green")


@main.command()
@click.argument("source", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("output_dir", type=click.Path(file_okay=False, path_type=Path))
@click.option(
    "--resample",
    type=click.Choice([a.value for a in ResampleAlgorithm]),
    default=ResampleAlgorithm.LANCZOS.value,
    show_default=True,
    help="Resampling algorithm used when scaling the source image.",
)
def favicon(
    source: Path,
    output_dir: Path,
    resample: str,
) -> None:
    """Generate a complete web favicon set from SOURCE into OUTPUT_DIR.

    Creates five files: favicon.ico (16/32/48 px), apple-touch-icon.png
    (180x180, white background), icon-192.png, icon-512.png (PWA icons),
    and site.webmanifest.
    """
    from icoforge.core.favicon_generator import generate_favicon_set
    from icoforge.core.resampling import to_pillow

    pil_resample = to_pillow(ResampleAlgorithm(resample))

    try:
        generated = generate_favicon_set(
            source,
            output_dir,
            resample=pil_resample,
            progress=_progress_callback,
        )
    except FileNotFoundError as exc:
        click.echo()
        click.secho(f"Error: source file not found: {exc}", fg="red", err=True)
        raise SystemExit(1) from exc
    except ValueError as exc:
        click.echo()
        click.secho(f"Error: {exc}", fg="red", err=True)
        raise SystemExit(1) from exc

    click.echo()
    click.secho(f"Favicon set written to {output_dir}/", fg="green")
    for path in generated:
        click.echo(f"  {path.name}")


@main.command("extract-icons")
@click.argument("source", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("output_dir", type=click.Path(file_okay=False, path_type=Path))
def extract_icons(source: Path, output_dir: Path) -> None:
    """Extract icon groups from a Windows PE file (EXE, DLL, OCX, …).

    SOURCE must be a valid Windows PE binary that contains RT_GROUP_ICON
    resources.  Each icon group is saved as a separate .ico file inside
    OUTPUT_DIR.

    Requires the optional ``exe`` extra::

        pip install icoforge[exe]
    """
    from icoforge.core.exe_extractor import ExeExtractError, extract_icons_from_exe

    try:
        icons = extract_icons_from_exe(source)
    except FileNotFoundError as exc:
        click.secho(f"Error: file not found: {exc}", fg="red", err=True)
        raise SystemExit(1) from exc
    except ExeExtractError as exc:
        click.secho(f"Error: {exc}", fg="red", err=True)
        raise SystemExit(1) from exc

    if not icons:
        click.secho("No icon resources found in the file.", fg="yellow")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = source.stem
    for i, ico_bytes in enumerate(icons):
        out = output_dir / f"{stem}_icon{i + 1}.ico"
        out.write_bytes(ico_bytes)
        click.echo(f"  {out.name}  ({len(ico_bytes):,} bytes)")

    click.echo()
    click.secho(f"{len(icons)} icon(s) saved to {output_dir}/", fg="green")


@main.group("presets")
def presets_group() -> None:
    """Manage named conversion presets (builtin and user-defined)."""


@presets_group.command("list")
def presets_list() -> None:
    """List all available presets (builtin and user-defined)."""
    click.secho("Built-in presets:", bold=True)
    for name in BUILTIN_PRESETS:
        click.echo(f"  {name}")

    user = list_user_presets()
    if user:
        click.echo()
        click.secho("User presets:", bold=True)
        for name in user:
            click.echo(f"  {name}")
    else:
        click.echo()
        click.echo("No user presets saved yet.")


@presets_group.command("show")
@click.argument("name")
def presets_show(name: str) -> None:
    """Show configuration details for a named preset."""
    try:
        config = _load_named_preset(name)
    except click.BadParameter as exc:
        click.secho(str(exc), fg="red", err=True)
        raise SystemExit(1) from exc

    click.secho(f"Preset: {name}", bold=True)
    click.echo(f"  Resample : {config.resample.value}")
    bg = "transparent" if config.background is TRANSPARENT else str(config.background)
    click.echo(f"  Background: {bg}")
    click.echo(f"  Preserve aspect: {config.preserve_aspect}")
    click.echo(f"  Auto-trim: {config.auto_trim}")
    if config.auto_trim:
        click.echo(f"  Trim padding: {config.auto_trim_padding} px")
    click.echo(f"  Sizes ({len(config.sizes)}):")
    for spec in config.sizes:
        per = f"  [resample: {spec.resample.value}]" if spec.resample else ""
        click.echo(f"    {spec.width}x{spec.height}  {spec.bit_depth}-bit{per}")


if __name__ == "__main__":
    main()
