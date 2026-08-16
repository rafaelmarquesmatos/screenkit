"""Seleção interativa de área com o mouse (overlay PySide6)."""
from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from typing import Any

from PySide6 import QtCore, QtGui, QtWidgets

from screenkit.utils import Region, get_logger

logger = get_logger(__name__)


def _ordered_screens() -> list[QtGui.QScreen]:
    """Telas Qt ordenadas: primária primeiro, depois as demais por (topo, esquerda)."""
    screens = QtGui.QGuiApplication.screens()
    if not screens:
        return []
    primary = QtGui.QGuiApplication.primaryScreen() or screens[0]
    others = [s for s in screens if s is not primary]
    others.sort(key=lambda s: (s.geometry().top(), s.geometry().left()))
    return [primary] + others


def _ordered_mss_monitors() -> list[dict[str, int]]:
    """Monitores ``mss`` (físicos) na mesma ordem espacial das telas Qt.

    O primário é identificado pela flag ``is_primary``; os demais são
    ordenados por (topo, esquerda). A ordem espacial é invariante ao DPI,
    então casa com :func:`_ordered_screens`.
    """
    import mss

    with mss.MSS() as sct:
        monitors = list(sct.monitors[1:])
    primary = next((m for m in monitors if m.get("is_primary")), None)
    if primary is None:
        primary = monitors[0]
    others = [m for m in monitors if m is not primary]
    others.sort(key=lambda m: (m["top"], m["left"]))
    return [primary] + others


def _target_pairs(
    monitor: int,
) -> list[tuple[QtGui.QScreen, dict[str, int]]]:
    """Pares (tela Qt, monitor físico mss) cobertos pelo ``monitor`` escolhido.

    ``monitor=0`` = todas as telas; ``1`` = primária; ``2+`` = demais.
    """
    screens = _ordered_screens()
    monitors = _ordered_mss_monitors()
    pairs = list(zip(screens, monitors))
    if not pairs:
        return []
    if monitor == 0:
        return pairs
    index = max(0, monitor - 1)
    return [pairs[index]] if index < len(pairs) else [pairs[0]]


class RegionOverlay(QtWidgets.QDialog):
    """Diálogo de tela cheia para selecionar uma região arrastando o mouse.

    Mostra a captura da tela como fundo (esmaecida fora da seleção), desenha
    o retângulo da seleção com borda e dimensões em tempo real. ``Enter``
    confirma e ``Esc`` cancela — a menos que ``auto_confirm`` seja ``True``,
    caso em que soltar o botão do mouse já confirma.

    Com ``monitor=0`` (padrão), o overlay cobre **todos os monitores**
    (área de trabalho virtual) e permite selecionar atravessando telas.
    Com ``monitor>=1``, cobre apenas o monitor correspondente (1 = primário).

    A conversão de coordenadas é feita por tela (levando em conta o
    ``devicePixelRatio`` de cada uma), então funciona com monitores de DPI
    diferentes.

    Também pode ser usada de forma não bloqueante (``show()``) em aplicações
    Qt existentes — veja :func:`start_region_selection`.
    """

    region_selected = QtCore.Signal(object)
    """Emitido com a ``Region`` escolhida quando o usuário confirma."""

    region_cancelled = QtCore.Signal()
    """Emitido quando o usuário cancela com ``Esc``."""

    BORDER_COLOR = QtGui.QColor("#4FC3F7")
    DIM_COLOR = QtGui.QColor(0, 0, 0, 110)

    def __init__(self, monitor: int = 0, auto_confirm: bool = False) -> None:
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

        self._monitor = monitor
        self._auto_confirm = auto_confirm

        self._pairs = _target_pairs(monitor)
        self._logical = self._union_logical()
        self.setGeometry(self._logical)

        self._backgrounds: list[tuple[QtCore.QRect, QtGui.QPixmap]] = []
        self._offsets: dict[int, tuple[int, int]] = {}
        self._grab_backgrounds()

        self._start: QtCore.QPoint | None = None
        self._end: QtCore.QPoint | None = None
        self._pressed = False

    # ------------------------------------------------------------------
    # Geometria e fundo
    # ------------------------------------------------------------------

    def _union_logical(self) -> QtCore.QRect:
        rects = [screen.geometry() for screen, _ in self._pairs]
        union = rects[0]
        for rect in rects[1:]:
            union = union.united(rect)
        return union

    def _grab_backgrounds(self) -> None:
        """Captura cada monitor (via ``mss``) e calcula o offset físico."""
        import mss

        origin = self._logical.topLeft()
        try:
            with mss.MSS() as sct:
                for screen, monitor in self._pairs:
                    shot = sct.grab(monitor)
                    image = QtGui.QImage(
                        shot.rgb,
                        shot.width,
                        shot.height,
                        shot.width * 3,
                        QtGui.QImage.Format.Format_RGB888,
                    )
                    pixmap = QtGui.QPixmap.fromImage(image.copy())
                    widget_rect = screen.geometry().translated(-origin)
                    self._backgrounds.append((widget_rect, pixmap))
                    self._offsets[id(screen)] = (
                        monitor["left"],
                        monitor["top"],
                    )
        except Exception:
            logger.exception("Falha ao capturar o fundo do overlay")
            self._backgrounds = []

    def _to_physical(self, point: QtCore.QPoint) -> tuple[int, int]:
        """Converte um ponto do widget (lógico) para pixels físicos da tela virtual."""
        global_point = self._logical.topLeft() + point
        screen = QtGui.QGuiApplication.screenAt(global_point)
        if screen is None:
            screen = QtGui.QGuiApplication.primaryScreen()
        dpr = screen.devicePixelRatio()
        offset = self._offsets.get(id(screen), (0, 0))
        local = global_point - screen.geometry().topLeft()
        return (
            offset[0] + round(local.x() * dpr),
            offset[1] + round(local.y() * dpr),
        )

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
        left, top = self._to_physical(rect.topLeft())
        right, bottom = self._to_physical(rect.bottomRight())
        return Region(left, top, max(1, right - left), max(1, bottom - top))

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
            if self._auto_confirm and self.selected_region is not None:
                logger.debug("Seleção confirmada automaticamente: %s", self.selected_region)
                self.accept()
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

        if not self._backgrounds:
            painter.fillRect(self.rect(), self.DIM_COLOR)
        for rect, pixmap in self._backgrounds:
            if pixmap.isNull():
                painter.fillRect(rect, self.DIM_COLOR)
            else:
                painter.drawPixmap(rect, pixmap)

        rect = self._current_rect()
        if rect is not None and not rect.isEmpty():
            path = QtGui.QPainterPath()
            path.setFillRule(QtCore.Qt.FillRule.OddEvenFill)
            path.addRect(self.rect())
            path.addRect(rect)
            painter.fillPath(path, self.DIM_COLOR)

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
        else:
            painter.fillRect(self.rect(), self.DIM_COLOR)

        hint = (
            "Arraste para selecionar — Esc cancela"
            if self._auto_confirm
            else "Arraste para selecionar — Enter confirma, Esc cancela"
        )
        painter.setPen(QtGui.QColor(255, 255, 255, 200))
        painter.drawText(
            self.rect().adjusted(0, 0, 0, -24),
            QtCore.Qt.AlignmentFlag.AlignBottom
            | QtCore.Qt.AlignmentFlag.AlignHCenter,
            hint,
        )
        painter.end()


def _ensure_application() -> tuple[QtWidgets.QApplication, bool]:
    """Retorna a ``QApplication`` atual ou cria uma; informa se a criou."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)
        return app, True
    return app, False


def select_region(
    silent: bool = False, monitor: int = 0, auto_confirm: bool = False
) -> Region | None:
    """Abre o overlay de seleção de área e retorna a região escolhida.

    Args:
        silent: Se ``True``, não abre o overlay e retorna ``None``
            imediatamente (útil em automação/ambientes sem interação).
        monitor: Monitor no estilo ``mss``: ``0`` = todos os monitores
            (área de trabalho virtual), ``1`` = primário, ``2`` = segundo,
            etc.
        auto_confirm: Se ``True``, a seleção é confirmada automaticamente
            ao soltar o botão do mouse (sem precisar de ``Enter``).

    Returns:
        ``Region`` em pixels físicos (coordenadas da tela virtual), ou
        ``None`` se cancelada (``Esc``) ou em modo silencioso.

    Notes:
        - Deve ser chamada a partir da thread principal.
        - Se uma ``QApplication`` já existir (ex.: app host), ela é
          reutilizada; o diálogo roda com ``exec()`` aninhado.

    Examples:
        >>> import screenkit
        >>> region = screenkit.select_region()          # todos os monitores
        >>> region = screenkit.select_region(monitor=1) # só o primário
        >>> if region:
        ...     img = screenkit.capture_region(region)
    """
    if silent:
        logger.debug("Modo silencioso: overlay ignorado.")
        return None

    app, owns_app = _ensure_application()
    overlay = RegionOverlay(monitor=monitor, auto_confirm=auto_confirm)
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
    callback: Callable[[Region | None], Any],
    monitor: int = 0,
    auto_confirm: bool = False,
) -> RegionOverlay:
    """Versão não bloqueante de :func:`select_region` para apps Qt existentes.

    Mostra o overlay sem travar a aplicação; o ``callback`` recebe a
    ``Region`` escolhida (ou ``None`` se cancelada). Guarde a referência
    retornada enquanto o overlay estiver em uso.

    Args:
        callback: Função chamada com ``Region | None`` ao finalizar.
        monitor: Monitor no estilo ``mss`` (``0`` = todos, ``1`` = primário).
        auto_confirm: Se ``True``, confirma a seleção ao soltar o mouse.

    Returns:
        O overlay exibido (mantenha a referência viva).

    Examples:
        >>> from screenkit.overlay import start_region_selection
        >>> def on_done(region):
        ...     print(region)
        >>> overlay = start_region_selection(on_done)  # não bloqueia
    """
    _, owns_app = _ensure_application()
    overlay = RegionOverlay(monitor=monitor, auto_confirm=auto_confirm)

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
