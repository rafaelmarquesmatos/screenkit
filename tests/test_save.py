"""Testes de salvamento de imagem e geração de nome de arquivo."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pytest
from PIL import Image

from screenkit.save import (
    UnsupportedFormatError,
    build_filename,
    default_directory,
    save,
)


@pytest.fixture
def image() -> Image.Image:
    return Image.new("RGBA", (64, 32), (255, 0, 0, 128))


def test_build_filename_exact_pattern() -> None:
    name = build_filename("png", now=datetime(2026, 8, 15, 14, 30, 5))
    assert name == "screen_2026-08-15_14-30-05.png"


def test_build_filename_general_pattern() -> None:
    name = build_filename("png")
    assert re.fullmatch(r"screen_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.png", name)


def test_build_filename_custom_prefix() -> None:
    name = build_filename("webp", prefix="shot")
    assert name.startswith("shot_")
    assert name.endswith(".webp")


def test_build_filename_normalizes_jpeg() -> None:
    assert build_filename("jpeg").endswith(".jpg")


def test_build_filename_rejects_unknown_format() -> None:
    with pytest.raises(UnsupportedFormatError):
        build_filename("bmp")


def test_default_directory_is_pictures() -> None:
    folder = default_directory()
    assert folder == Path.home() / "Pictures"
    assert folder.exists()


def test_save_png_auto_name(image: Image.Image, tmp_path: Path) -> None:
    path = save(image, directory=tmp_path)
    assert path.exists()
    assert path.suffix == ".png"
    assert path.parent == tmp_path
    assert re.fullmatch(
        r"screen_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.png", path.name
    )
    with Image.open(path) as saved:
        assert saved.format == "PNG"


def test_save_jpg_converts_rgba_and_applies_quality(
    image: Image.Image, tmp_path: Path
) -> None:
    path = save(image, directory=tmp_path, fmt="jpg", quality=50)
    assert path.suffix == ".jpg"
    with Image.open(path) as saved:
        assert saved.format == "JPEG"
        assert saved.mode == "RGB"


def test_save_webp(image: Image.Image, tmp_path: Path) -> None:
    path = save(image, directory=tmp_path, fmt="webp", quality=80)
    assert path.suffix == ".webp"
    with Image.open(path) as saved:
        assert saved.format == "WEBP"


def test_save_with_explicit_path(image: Image.Image, tmp_path: Path) -> None:
    target = tmp_path / "captura.png"
    assert save(image, path=target) == target
    assert target.exists()


def test_save_infers_format_from_extension(
    image: Image.Image, tmp_path: Path
) -> None:
    target = tmp_path / "foto.jpg"
    path = save(image, path=target)
    with Image.open(path) as saved:
        assert saved.format == "JPEG"


def test_save_creates_missing_directory(image: Image.Image, tmp_path: Path) -> None:
    folder = tmp_path / "sub" / "pasta"
    path = save(image, directory=folder)
    assert path.parent == folder
    assert path.exists()


def test_save_generates_unique_names(image: Image.Image, tmp_path: Path) -> None:
    first = save(image, directory=tmp_path)
    second = save(image, directory=tmp_path)
    assert first != second
    assert first.exists() and second.exists()


def test_save_rejects_unknown_format(image: Image.Image, tmp_path: Path) -> None:
    with pytest.raises(UnsupportedFormatError):
        save(image, directory=tmp_path, fmt="gif")
