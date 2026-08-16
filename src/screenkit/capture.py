"""Capturas de tela: tela inteira, região específica e janela por título."""
from __future__ import annotations

import ctypes
import platform
import re
import shutil
import subprocess

import mss
from PIL import Image

from screenkit.utils import (
    PlatformNotSupportedError,
    Region,
    WindowNotFoundError,
    get_logger,
    image_from_mss,
)

logger = get_logger(__name__)

_SYSTEM = platform.system().lower()


def capture_full(monitor: int = 0) -> Image.Image:
    """Captura a tela inteira (um monitor ou todos combinados).

    Args:
        monitor: Índice no estilo ``mss`` — ``0`` (padrão) captura todos os
            monitores combinados; ``1`` é o monitor primário, ``2`` o segundo,
            e assim por diante.

    Returns:
        Imagem RGB da captura.

    Raises:
        ValueError: Se o índice do monitor for inválido.

    Examples:
        >>> import screenkit
        >>> img = screenkit.capture_full()      # todos os monitores
        >>> img = screenkit.capture_full(1)     # apenas o primário
    """
    with mss.MSS() as sct:
        if monitor < 0 or monitor >= len(sct.monitors):
            raise ValueError(
                f"Monitor inválido: {monitor} "
                f"(disponíveis: 0..{len(sct.monitors) - 1})"
            )
        logger.debug("Capturando monitor %d (%s)", monitor, sct.monitors[monitor])
        shot = sct.grab(sct.monitors[monitor])
        return image_from_mss(shot)


def capture_region(region: Region | tuple[int, int, int, int]) -> Image.Image:
    """Captura uma região específica da tela.

    Args:
        region: Região como ``Region`` ou tupla ``(left, top, width, height)``
            em pixels físicos.

    Returns:
        Imagem RGB com as dimensões exatas da região.

    Raises:
        ValueError: Se a região for vazia (largura ou altura <= 0).
        mss.exception.ScreenShotError: Se a região estiver fora da tela
            visível.

    Examples:
        >>> from screenkit import capture_region, Region
        >>> img = capture_region(Region(0, 0, 800, 600))
        >>> img = capture_region((10, 20, 300, 200))
    """
    reg = Region._make(region) if isinstance(region, tuple) else region
    if reg.is_empty:
        raise ValueError(f"Região inválida (sem área): {reg}")
    with mss.MSS() as sct:
        logger.debug("Capturando região %s", reg)
        shot = sct.grab(reg.to_mss())
        return image_from_mss(shot)


def capture_window(title: str, *, exact: bool = True) -> Image.Image:
    """Captura a área de uma janela localizada pelo título.

    A janela precisa estar visível (não minimizada) para que a geometria
    esteja correta.

    Args:
        title: Título da janela (ou parte dele, se ``exact=False``).
        exact: Se ``True`` (padrão), exige correspondência exata do título;
            caso contrário, usa a primeira janela que contém o texto.

    Returns:
        Imagem RGB da área da janela.

    Raises:
        WindowNotFoundError: Se nenhuma janela com o título for encontrada.
        PlatformNotSupportedError: No macOS, ou no Linux sem ``xdotool``.

    Notes:
        - Windows: usa a API Win32 (via ``ctypes``, sem dependência extra).
        - Linux (X11): requer o utilitário ``xdotool``
          (``sudo apt install xdotool``).
        - Wayland: não suportado (ver limitações no README).
    """
    if _SYSTEM == "windows":
        rect = _window_rect_windows(title, exact)
    elif _SYSTEM == "linux":
        rect = _window_rect_x11(title, exact)
    else:
        raise PlatformNotSupportedError(
            "capture_window",
            reason="No macOS, use a captura por região ou tela inteira.",
        )
    logger.info("Janela %r encontrada em %s", title, rect)
    return capture_region(rect)


# --------------------------------------------------------------------------
# Backends por plataforma
# --------------------------------------------------------------------------


def _window_rect_windows(title: str, exact: bool) -> Region:
    """Localiza a janela via Win32 (``FindWindowW``/``EnumWindows``) com ctypes."""
    user32 = ctypes.windll.user32  # type: ignore[attr-defined]

    if exact:
        hwnd = int(user32.FindWindowW(None, title))
    else:
        hwnd = _find_hwnd_containing(title)
    if not hwnd:
        raise WindowNotFoundError(title)

    class Rect(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long),
            ("top", ctypes.c_long),
            ("right", ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]

    rect = Rect()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return Region(
        rect.left,
        rect.top,
        rect.right - rect.left,
        rect.bottom - rect.top,
    )


def _find_hwnd_containing(title: str) -> int:
    """Varre as janelas de topo e retorna a primeira cujo título contém ``title``."""
    user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    needle = title.lower()
    found: list[int] = []
    EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)

    def _callback(hwnd: int, _lparam: int) -> bool:
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        if needle in buffer.value.lower():
            found.append(hwnd)
            return False
        return True

    callback = EnumProc(_callback)  # manter referência viva durante a chamada
    user32.EnumWindows(callback, 0)
    return found[0] if found else 0


def _window_rect_x11(title: str, exact: bool) -> Region:
    """Localiza a janela no X11 via ``xdotool``."""
    if shutil.which("xdotool") is None:
        raise PlatformNotSupportedError(
            "capture_window",
            reason="No Linux, instale o utilitário xdotool "
            "(sudo apt install xdotool).",
        )
    pattern = f"^{re.escape(title)}$" if exact else re.escape(title)
    result = subprocess.run(
        ["xdotool", "search", "--name", pattern],
        capture_output=True,
        text=True,
        check=False,
    )
    window_ids = result.stdout.split()
    if not window_ids:
        raise WindowNotFoundError(title)
    geometry = subprocess.run(
        ["xdotool", "getwindowgeometry", "--shell", window_ids[0]],
        capture_output=True,
        text=True,
        check=True,
    )
    values = dict(
        line.split("=", 1) for line in geometry.stdout.splitlines() if "=" in line
    )
    return Region(
        int(values["X"]),
        int(values["Y"]),
        int(values["WIDTH"]),
        int(values["HEIGHT"]),
    )
