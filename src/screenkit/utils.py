"""Helpers internos do screenkit (região, erros, logging, conversões)."""
from __future__ import annotations

import logging
from typing import Any, NamedTuple


class ScreenKitError(Exception):
    """Erro base da biblioteca."""


class WindowNotFoundError(ScreenKitError):
    """Lançada quando uma janela com o título informado não é encontrada."""

    def __init__(self, title: str) -> None:
        super().__init__(f"Janela não encontrada: {title!r}")


class PlatformNotSupportedError(ScreenKitError):
    """Lançada quando um recurso não é suportado na plataforma atual."""

    def __init__(self, feature: str, reason: str = "") -> None:
        import platform

        message = (
            f"Recurso `{feature}` não é suportado em "
            f"{platform.system()} ({platform.machine()})."
        )
        if reason:
            message += f" {reason}"
        super().__init__(message)


class Region(NamedTuple):
    """Região retangular em pixels físicos (coordenadas da tela virtual).

    Attributes:
        left: Coordenada x do canto superior esquerdo.
        top: Coordenada y do canto superior esquerdo.
        width: Largura em pixels.
        height: Altura em pixels.
    """

    left: int
    top: int
    width: int
    height: int

    @property
    def right(self) -> int:
        """Coordenada x do canto inferior direito."""
        return self.left + self.width

    @property
    def bottom(self) -> int:
        """Coordenada y do canto inferior direito."""
        return self.top + self.height

    @property
    def is_empty(self) -> bool:
        """True se a região não possui área utilizável."""
        return self.width <= 0 or self.height <= 0

    def to_mss(self) -> dict[str, int]:
        """Converte para o dicionário esperado por ``mss``."""
        return {
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
        }

    @classmethod
    def from_mss(cls, monitor: dict[str, int]) -> Region:
        """Cria uma ``Region`` a partir do dicionário de monitor do ``mss``."""
        return cls(
            monitor["left"],
            monitor["top"],
            monitor["width"],
            monitor["height"],
        )


def image_from_mss(shot: Any) -> Any:
    """Converte um ``ScreenShot`` do ``mss`` (BGRA) em ``PIL.Image`` RGB."""
    from PIL import Image

    return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")


def get_logger(name: str) -> logging.Logger:
    """Retorna um logger com ``NullHandler`` (evita propagar mensagens por acidente)."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    return logger
