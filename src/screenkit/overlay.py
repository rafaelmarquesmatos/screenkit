"""Seleção interativa de área com o mouse (overlay PySide6)."""
from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from typing import Any

from PySide6 import QtCore, QtGui, QtWidgets

from screenkit.utils import Region, get_logger

logger = get_logger(__name__)


class RegionOverlay(QtWidgets.QDialog):
    """Diálogo de tela cheia para selecionar uma região arrastando o mouse.

    Mostra a tela esmaecida (dim), desenha o retângulo da seleção com borda
    e dimensões em tempo real. ``Enter`` confirma e ``Esc`` cancela.

    Também pode ser usada de forma não bloqueante (``show()``) em aplicações
    Qt existentes — veja :func:`start_region_selection`.
    """

    region_selected = QtCore.Signal(object)
    """Emitido com a ``Region`` escolhida quando o usuário confirma."""

    region_cancelled = QtCore.Signal()
    """Emitido quando o usuário cancela com ``Esc``."""

    BORDER_COLOR = QtGui.QColor("#4FC3F7")
    DIM_COLOR = QtGui.QColor(0, 0, 0, 110)

    def __init__(self, screen: QtGui.QScreen | None = None) -> None:
        super().__init__(None)
        flags = (
            QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.WindowStaysOnTopHint
            | QtCore.Qt.WindowType.Tool
        )
        self.setWindowFlags(flags)
        self.setCursor(QtCore.Qt.CursorShape.CrossCursor)
        self.setMouseTracking(True)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        self._screen = screen or QtGui.QGuiApplication.primaryScreen()
        self.setGeometry(self._screen.geometry())
        self._start: QtCore.QPoint | None = None
        self._end: QtCore.QPoint | None = None
        self._pressed = False

    # ------------------------------------------------------------------
    # Seleção
    # ------------------------------------------------------------------

    def _current_rect(self) -> QtCore.QRect | None:
        """Retorna o retângulo normalizado (suporta arrastar em qualquer direção)."""
        if self._start is None or self._end is None:
            return None
        return QtCore.QRect(self._start, self._end).normalized()

    def _reset_selection(self) -> None:
        self._start = None
        self._end = None
        self._pressed = False
        self.update()

    @property
    def selected_region(self) -> Region | None:
        """Região escolhida em pixels físicos, ou ``None`` se nada foi selecionado."""
        rect = self._current_rect()
        if rect is None or rect.isEmpty():
            return None
        factor = self._screen.devicePixelRatio()
        return Region(
            round(rect.x() * factor),
            round(rect.y() * factor),
            max(1, round(rect.width() * factor)),
            max(1, round(rect.height() * factor)),
        )

    # ------------------------------------------------------------------
    # Eventos de mouse e teclado
    # ------------------------------------------------------------------

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._start = self._end = event.position().toPoint()
            self._pressed = True
            self.update()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._pressed:
            self._end = event.position().toPoint()
            self.update()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton and self._pressed:
            self._end = event.position().toPoint()
            self._pressed = False
            self.update()
        else:
            super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        key = event.key()
        if key in (QtCore.Qt.Key.Key_Escape, QtCore.Qt.Key.Key_Q):
            logger.debug("Seleção cancelada (Esc)")
            self._reset_selection()
            self.reject()
        elif key in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
            if self.selected_region is None:
                logger.debug("Enter sem seleção — ignorado")
                return
            logger.debug("Seleção confirmada: %s", self.selected_region)
            self.accept()
        else:
            super().keyPressEvent(event)

    # ------------------------------------------------------------------
    # Desenho
    # ------------------------------------------------------------------

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        del event
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        painter.fillRect(self.rect(), self.DIM_COLOR)
        rect = self._current_rect()
        if rect is not None and not rect.isEmpty():
            painter.setCompositionMode(
                QtGui.QPainter.CompositionMode.CompositionMode_Clear
            )
            painter.fillRect(rect, QtCore.Qt.GlobalColor.transparent)
            painter.setCompositionMode(
                QtGui.QPainter.CompositionMode.CompositionMode_SourceOver
            )

            painter.setPen(QtGui.QPen(self.BORDER_COLOR, 2))
            painter.drawRect(rect)

            label = f"{rect.width()} × {rect.height()}"
            text_rect = rect.adjusted(4, 4, -4, -4)
            painter.setPen(QtGui.QColor("#FFFFFF"))
            painter.drawText(
                text_rect,
                QtCore.Qt.AlignmentFlag.AlignTop
                | QtCore.Qt.AlignmentFlag.AlignLeft,
                label,
            )

        hint = "Arraste para selecionar — Enter confirma, Esc cancela"
        painter.setPen(QtGui.QColor(255, 255, 255, 200))
        painter.drawText(
            self.rect().adjusted(0, 0, 0, -24),
            QtCore.Qt.AlignmentFlag.AlignBottom
            | QtCore.Qt.AlignmentFlag.AlignHCenter,
            hint,
        )
        painter.end()


def _pick_screen(monitor: int) -> QtGui.QScreen:
    """Escolhe a tela Qt para o monitor no estilo ``mss`` (1 = primário)."""
    screens = QtGui.QGuiApplication.screens()
    if not screens:
        return QtGui.QGuiApplication.primaryScreen()
    index = max(0, monitor - 1)
    return screens[index] if index < len(screens) else screens[0]


def _ensure_application() -> tuple[QtWidgets.QApplication, bool]:
    """Retorna a ``QApplication`` atual ou cria uma; informa se a criou."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)
        return app, True
    return app, False


def select_region(silent: bool = False, monitor: int = 0) -> Region | None:
    """Abre o overlay de seleção de área e retorna a região escolhida.

    Args:
        silent: Se ``True``, não abre o overlay e retorna ``None``
            imediatamente (útil em automação/ambientes sem interação).
        monitor: Monitor no estilo ``mss``: ``0`` ou ``1`` = primário,
            ``2`` = segundo monitor, etc.

    Returns:
        ``Region`` em pixels físicos, ou ``None`` se cancelada
        (``Esc``) ou em modo silencioso.

    Notes:
        - Deve ser chamada a partir da thread principal.
        - Se uma ``QApplication`` já existir (ex.: app host), ela é
          reutilizada; o diálogo roda com ``exec()`` aninhado.

    Examples:
        >>> import screenkit
        >>> region = screenkit.select_region()
        >>> if region:
        ...     img = screenkit.capture_region(region)
    """
    if silent:
        logger.debug("Modo silencioso: overlay ignorado.")
        return None

    app, owns_app = _ensure_application()
    overlay = RegionOverlay(_pick_screen(monitor))
    result = overlay.exec()
    region = (
        overlay.selected_region
        if result == QtWidgets.QDialog.DialogCode.Accepted
        else None
    )
    if owns_app:
        app.quit()
    if region is None:
        logger.info("Seleção de região cancelada.")
    else:
        logger.info("Região selecionada: %s", region)
    return region


def start_region_selection(
    callback: Callable[[Region | None], Any], monitor: int = 0
) -> RegionOverlay:
    """Versão não bloqueante de :func:`select_region` para apps Qt existentes.

    Mostra o overlay sem travar a aplicação; o ``callback`` recebe a
    ``Region`` escolhida (ou ``None`` se cancelada). Guarde a referência
    retornada enquanto o overlay estiver em uso.

    Args:
        callback: Função chamada com ``Region | None`` ao finalizar.
        monitor: Monitor no estilo ``mss`` (1 = primário).

    Returns:
        O overlay exibido (mantenha a referência viva).

    Examples:
        >>> from screenkit.overlay import start_region_selection
        >>> def on_done(region):
        ...     print(region)
        >>> overlay = start_region_selection(on_done)  # não bloqueia
    """
    _, owns_app = _ensure_application()
    overlay = RegionOverlay(_pick_screen(monitor))

    def _on_finished(result: int) -> None:
        region = (
            overlay.selected_region
            if result == QtWidgets.QDialog.DialogCode.Accepted
            else None
        )
        callback(region)

    overlay.finished.connect(_on_finished)
    overlay.show()
    overlay.raise_()
    overlay.activateWindow()
    return overlay
