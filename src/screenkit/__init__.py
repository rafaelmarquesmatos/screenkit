"""screenkit — captura de tela, seleção de área com o mouse e salvamento.

Uso rápido::

    import screenkit

    img = screenkit.capture_full()          # PIL.Image da tela inteira
    screenkit.save(img)                     # ~/Pictures/screen_....png
    region = screenkit.select_region()      # overlay com o mouse
    path = screenkit.capture_and_save()     # seleciona e salva num passo
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from screenkit.capture import capture_full, capture_region, capture_window
from screenkit.overlay import RegionOverlay, select_region, start_region_selection
from screenkit.save import (
    UnsupportedFormatError,
    build_filename,
    default_directory,
    save,
)
from screenkit.utils import (
    PlatformNotSupportedError,
    Region,
    ScreenKitError,
    WindowNotFoundError,
)

__version__ = "0.1.0"

__all__ = [
    "Region",
    "RegionOverlay",
    "PlatformNotSupportedError",
    "ScreenKitError",
    "UnsupportedFormatError",
    "WindowNotFoundError",
    "build_filename",
    "capture_and_save",
    "capture_full",
    "capture_region",
    "capture_window",
    "default_directory",
    "save",
    "select_region",
    "start_region_selection",
]


def capture_and_save(
    *,
    silent: bool = False,
    monitor: int = 0,
    auto_confirm: bool = False,
    directory: str | Path | None = None,
    fmt: str | None = None,
    quality: int = 95,
    prefix: str = "screen",
    region: Region | tuple[int, int, int, int] | None = None,
) -> Path | None:
    """Seleciona a área com o mouse, captura e salva em um único passo.

    Args:
        silent: Se ``True``, captura a tela inteira sem abrir o overlay
            (modo silencioso, para automação).
        monitor: Monitor no estilo ``mss`` (``0`` = todos, ``1`` = primário).
        auto_confirm: Se ``True``, a seleção é confirmada automaticamente
            ao soltar o mouse (sem ``Enter``).
        directory: Pasta de destino (padrão: ``~/Pictures``).
        fmt: Formato de saída (``png``, ``jpg`` ou ``webp``; padrão ``png``).
        quality: Qualidade de 1 a 100 para ``jpg``/``webp``.
        prefix: Prefixo do nome automático do arquivo.
        region: Região pré-definida; se informada, dispensa o overlay
            (``(left, top, width, height)`` ou ``Region``).

    Returns:
        Caminho do arquivo salvo, ou ``None`` se a seleção for cancelada.

    Examples:
        >>> import screenkit
        >>> screenkit.capture_and_save()                    # interativo
        >>> screenkit.capture_and_save(silent=True)         # automação
        >>> screenkit.capture_and_save(region=(0, 0, 500, 400), fmt="jpg")
    """
    if region is not None:
        image = capture_region(region)
    elif silent:
        image = capture_full(monitor)
    else:
        selected = select_region(monitor=monitor, auto_confirm=auto_confirm)
        if selected is None:
            return None
        image = capture_region(selected)
    return save(
        image,
        directory=directory,
        fmt=fmt,
        quality=quality,
        prefix=prefix,
    )
