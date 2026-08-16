"""Salvamento de capturas em arquivo (PNG, JPG, WebP)."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from screenkit.utils import ScreenKitError, get_logger

logger = get_logger(__name__)

SUPPORTED_FORMATS: tuple[str, ...] = ("png", "jpg", "webp")


class UnsupportedFormatError(ScreenKitError):
    """Lançada ao tentar salvar em um formato não suportado."""

    def __init__(self, fmt: str) -> None:
        super().__init__(
            f"Formato não suportado: {fmt!r}. "
            f"Use um de: {', '.join(SUPPORTED_FORMATS)}."
        )


def _normalize_format(fmt: str) -> str:
    """Normaliza e valida o formato (``jpeg`` vira ``jpg``)."""
    normalized = fmt.lower().lstrip(".")
    if normalized == "jpeg":
        normalized = "jpg"
    if normalized not in SUPPORTED_FORMATS:
        raise UnsupportedFormatError(fmt)
    return normalized


def build_filename(
    fmt: str, prefix: str = "screen", now: datetime | None = None
) -> str:
    """Gera um nome de arquivo com timestamp.

    Args:
        fmt: Formato do arquivo (``png``, ``jpg`` ou ``webp``).
        prefix: Prefixo do nome (padrão ``screen``).
        now: Data/hora de referência (útil em testes); padrão ``datetime.now()``.

    Returns:
        Nome no formato ``screen_2026-08-15_14-30-05.png``.

    Raises:
        UnsupportedFormatError: Se o formato não for suportado.
    """
    fmt = _normalize_format(fmt)
    stamp = (now or datetime.now()).strftime("%Y-%m-%d_%H-%M-%S")
    return f"{prefix}_{stamp}.{fmt}"


def default_directory() -> Path:
    """Retorna a pasta padrão de salvamento (``~/Pictures``), criando-a se preciso."""
    folder = Path.home() / "Pictures"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _unique_path(path: Path) -> Path:
    """Garante um caminho que não sobrescreva arquivo existente (sufixo ``_1``)."""
    if not path.exists():
        return path
    for index in range(1, 1000):
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise ScreenKitError(f"Não foi possível gerar um nome único para {path}")


def save(
    image: Any,
    *,
    path: str | Path | None = None,
    directory: str | Path | None = None,
    fmt: str | None = None,
    quality: int = 95,
    prefix: str = "screen",
) -> Path:
    """Salva a imagem em disco e retorna o caminho do arquivo.

    Args:
        image: Imagem ``PIL.Image`` a ser salva.
        path: Caminho completo do arquivo. Se informado, ``directory``,
            ``prefix`` e o nome automático são ignorados.
        directory: Pasta de destino (padrão: ``~/Pictures``).
        fmt: Formato de saída (``png``, ``jpg`` ou ``webp``). Padrão: ``png``,
            ou o formato inferido da extensão de ``path``.
        quality: Qualidade de 1 a 100 para formatos com perda (``jpg``/``webp``).
        prefix: Prefixo do nome automático do arquivo.

    Returns:
        Caminho do arquivo salvo.

    Raises:
        UnsupportedFormatError: Se o formato não for suportado.
        OSError: Se não for possível gravar no destino.

    Examples:
        >>> from screenkit import capture_full, save
        >>> img = capture_full()
        >>> save(img)                        # ~/Pictures/screen_2026-08-15_....png
        >>> save(img, directory="docs")      # pasta personalizada
        >>> save(img, fmt="jpg", quality=80) # formato e qualidade
        >>> save(img, path="captura.png")    # caminho exato
    """
    if path is not None:
        target = Path(path)
        fmt = fmt or target.suffix.lstrip(".").lower() or "png"
    else:
        fmt = fmt or "png"
        folder = Path(directory) if directory is not None else default_directory()
        folder.mkdir(parents=True, exist_ok=True)
        target = _unique_path(folder / build_filename(fmt, prefix=prefix))

    fmt = _normalize_format(fmt)
    logger.debug("Salvando %dx%d em %s (%s, q=%d)", image.width, image.height, target, fmt, quality)

    if fmt == "jpg":
        converted = image if image.mode in ("RGB", "L") else image.convert("RGB")
        converted.save(target, format="JPEG", quality=quality)
    elif fmt == "webp":
        image.save(target, format="WEBP", quality=quality)
    else:
        image.save(target, format="PNG")

    logger.info("Imagem salva em %s", target)
    return target
