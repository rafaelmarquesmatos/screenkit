"""Testes das funções de captura (região, tela inteira, janela)."""
from __future__ import annotations

import platform

import pytest
from PIL import Image

import screenkit
from screenkit.utils import Region


def _require_display() -> None:
    """Pula o teste se não houver captura de tela disponível (ex.: CI headless)."""
    import mss

    try:
        with mss.MSS() as sct:
            if not sct.monitors:
                pytest.skip("Nenhum monitor disponível para captura.")
    except Exception as exc:  # pragma: no cover - depende do ambiente
        pytest.skip(f"Captura de tela indisponível: {exc}")


def test_region_helpers() -> None:
    region = Region(10, 20, 30, 40)
    assert region.to_mss() == {
        "left": 10,
        "top": 20,
        "width": 30,
        "height": 40,
    }
    assert (region.right, region.bottom) == (40, 60)
    assert not region.is_empty
    assert Region(0, 0, 0, 5).is_empty
    assert Region.from_mss(region.to_mss()) == region


def test_capture_region_returns_image_of_expected_size() -> None:
    _require_display()
    image = screenkit.capture_region(Region(0, 0, 100, 100))
    assert isinstance(image, Image.Image)
    assert image.size == (100, 100)
    assert image.mode == "RGB"


def test_capture_region_accepts_tuple() -> None:
    _require_display()
    image = screenkit.capture_region((0, 0, 64, 64))
    assert image.size == (64, 64)


def test_capture_region_rejects_empty_region() -> None:
    _require_display()
    with pytest.raises(ValueError):
        screenkit.capture_region(Region(0, 0, 0, 100))


def test_capture_full_returns_image() -> None:
    _require_display()
    image = screenkit.capture_full()
    assert isinstance(image, Image.Image)
    assert image.width > 0 and image.height > 0


def test_capture_full_invalid_monitor() -> None:
    _require_display()
    with pytest.raises(ValueError):
        screenkit.capture_full(monitor=999)


def test_capture_window_unknown_title_raises() -> None:
    _require_display()
    if platform.system() == "Darwin":
        pytest.skip("capture_window não é suportado no macOS")
    with pytest.raises(screenkit.WindowNotFoundError):
        screenkit.capture_window("__screenkit_titulo_inexistente_xyz__")


def test_capture_and_save_silent_mode(tmp_path) -> None:
    _require_display()
    path = screenkit.capture_and_save(silent=True, directory=tmp_path)
    assert path is not None
    assert path.exists()
    assert path.suffix == ".png"
    assert path.parent == tmp_path


def test_capture_and_save_with_predefined_region(tmp_path) -> None:
    _require_display()
    path = screenkit.capture_and_save(
        region=(0, 0, 50, 50), directory=tmp_path, fmt="png"
    )
    assert path is not None
    assert path.exists()
    with Image.open(path) as saved:
        assert saved.size == (50, 50)
