# Changelog

Todas as mudanças notáveis do screenkit são documentadas neste arquivo.
O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/)
e o projeto usa [SemVer](https://semver.org/lang/pt-BR/).

## [0.1.0] - 2026-08-16

### Adicionado

- `capture_full`: captura da tela inteira (todos os monitores ou um específico).
- `capture_region`: captura de região `(left, top, width, height)` ou `Region`.
- `capture_window`: captura de janela por título (Win32 no Windows,
  `xdotool` no Linux/X11).
- `select_region`: overlay PySide6 de seleção com o mouse (dim, dimensões em
  tempo real, `Esc` cancela, `Enter` confirma, modo silencioso).
- `start_region_selection`: versão não bloqueante do overlay para apps Qt.
- `capture_and_save`: seleção + captura + salvamento em um passo.
- `save`: salvamento em PNG/JPG/WebP com nome automático
  (`screen_2026-08-15_14-30-05.png`) e pasta padrão `~/Pictures`.
- `build_filename` e `default_directory`.
- Pacote instalável via `pyproject.toml` (build `pip install -e .`).
- Suíte de testes com pytest (23 testes).
- Workflow de release no GitHub Actions (testes + publish no PyPI por tag).

[0.1.0]: https://github.com/rafaelmarquesmatos/screenkit/releases/tag/v0.1.0
