"""App de teste do screenkit — exercita captura, seleção e salvamento.

Uso::

    python examples/test_app.py
"""
from __future__ import annotations

import sys

from PySide6 import QtCore, QtGui, QtWidgets

import screenkit


def _to_qpixmap(image) -> QtGui.QPixmap:
    """Converte uma ``PIL.Image`` RGB em ``QPixmap`` (sem arquivos temporários)."""
    data = image.tobytes("raw", "RGB")
    qimage = QtGui.QImage(
        data,
        image.width,
        image.height,
        image.width * 3,
        QtGui.QImage.Format.Format_RGB888,
    )
    return QtGui.QPixmap.fromImage(qimage.copy())


def _list_monitors() -> list[tuple[int, str]]:
    """Lista os monitores no estilo ``mss`` (0 = todos, 1 = primário...)."""
    import mss

    with mss.MSS() as sct:
        all_monitors = sct.monitors
        virtual = all_monitors[0]
        monitors = list(all_monitors[1:])
    primary = next((m for m in monitors if m.get("is_primary")), None)
    if primary is None:
        primary = monitors[0]
    others = [m for m in monitors if m is not primary]
    others.sort(key=lambda m: (m["top"], m["left"]))
    ordered = [primary] + others

    labels: list[tuple[int, str]] = [
        (0, f"Todos os monitores — {virtual['width']} × {virtual['height']}")
    ]
    for i, monitor in enumerate(ordered, start=1):
        name = "primário" if i == 1 else ""
        suffix = f" ({name})" if name else ""
        labels.append(
            (i, f"Monitor {i}{suffix} — {monitor['width']} × {monitor['height']}")
        )
    return labels


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ScreenKit — App de teste")
        self.resize(720, 560)

        self._preview = QtWidgets.QLabel("Nenhuma captura ainda.")
        self._preview.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._preview.setMinimumHeight(320)
        self._preview.setFrameStyle(QtWidgets.QFrame.Shape.StyledPanel)

        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)

        monitor_row = QtWidgets.QHBoxLayout()
        monitor_row.addWidget(QtWidgets.QLabel("Monitor:"))
        self._monitor_combo = QtWidgets.QComboBox()
        for index, label in _list_monitors():
            self._monitor_combo.addItem(label, index)
        monitor_row.addWidget(self._monitor_combo, stretch=1)
        layout.addLayout(monitor_row)

        buttons = QtWidgets.QGridLayout()
        actions = [
            ("Selecionar região (Enter)", self._select_region),
            ("Selecionar região (auto)", self._select_region_auto),
            ("Capturar tela cheia", self._capture_full),
            ("Capturar e salvar", self._capture_and_save),
        ]
        for row, (text, handler) in enumerate(actions):
            button = QtWidgets.QPushButton(text)
            button.clicked.connect(handler)
            buttons.addWidget(button, row // 2, row % 2)
        layout.addLayout(buttons)
        layout.addWidget(self._preview, stretch=1)

        self.setCentralWidget(central)
        self.statusBar().showMessage("Pronto.")

    # ------------------------------------------------------------------
    # Ações
    # ------------------------------------------------------------------

    @property
    def _monitor(self) -> int:
        return self._monitor_combo.currentData()

    def _select_region(self) -> None:
        self._handle_region(screenkit.select_region(monitor=self._monitor))

    def _select_region_auto(self) -> None:
        self._handle_region(
            screenkit.select_region(monitor=self._monitor, auto_confirm=True)
        )

    def _capture_full(self) -> None:
        self.statusBar().showMessage("Capturando tela cheia...")
        image = screenkit.capture_full(monitor=self._monitor)
        self._show_image(image)
        self.statusBar().showMessage(f"Tela cheia: {image.width} × {image.height}")

    def _capture_and_save(self) -> None:
        path = screenkit.capture_and_save(
            monitor=self._monitor, auto_confirm=True
        )
        self.statusBar().showMessage(
            f"Salvo em {path}" if path else "Captura cancelada."
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _handle_region(self, region: screenkit.Region | None) -> None:
        if region is None:
            self.statusBar().showMessage("Seleção cancelada.")
            return
        image = screenkit.capture_region(region)
        self._show_image(image)
        self.statusBar().showMessage(
            f"Região: {region.width} × {region.height} "
            f"em ({region.left}, {region.top})"
        )

    def _show_image(self, image) -> None:
        pixmap = _to_qpixmap(image)
        self._preview.setPixmap(
            pixmap.scaled(
                self._preview.size(),
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation,
            )
        )


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
