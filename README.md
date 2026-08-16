# screenkit

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
![Plataformas](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20(X11)-lightgrey)

Biblioteca Python para **captura de tela**, **seleção de área com o mouse**
(overlay interativo) e **salvamento de imagens** — simples, rápida e
cross-platform.

> [!CAUTION]
> Este projeto utilizou IA como apoio no desenvolvimento.

## Instalação

```powershell
# direto do repositório (desenvolvimento)
git clone https://github.com/rafaelmarquesmatos/screenkit.git
cd screenkit
pip install -e ".[dev]"

# ou via requirements.txt de outro projeto
# screenkit @ git+https://github.com/rafaelmarquesmatos/screenkit.git
```

## Uso rápido

```python
import screenkit

img = screenkit.capture_full()            # PIL.Image (todos os monitores)
img = screenkit.capture_full(monitor=1)   # apenas o monitor primário
img = screenkit.capture_region((10, 20, 400, 300))
img = screenkit.capture_window("Notepad", exact=False)

screenkit.save(img)                       # ~/Pictures/screen_2026-08-15_14-30-05.png
screenkit.save(img, directory="docs", fmt="jpg", quality=85)

region = screenkit.select_region()        # overlay: arraste, Enter confirma, Esc cancela
path = screenkit.capture_and_save()       # seleciona, captura e salva num passo
```

## API pública

| Função | Descrição | Retorno |
| ------ | --------- | ------- |
| `capture_full(monitor=0)` | Tela inteira; `0` = todos os monitores, `1` = primário, `2+` = demais | `PIL.Image` |
| `capture_region(region)` | Região como `Region` ou `(left, top, width, height)` | `PIL.Image` |
| `capture_window(title, exact=True)` | Janela por título (Windows: Win32; Linux: X11 via `xdotool`) | `PIL.Image` |
| `select_region(silent=False, monitor=0)` | Overlay de seleção com o mouse | `Region \| None` |
| `capture_and_save(...)` | Seleção + captura + salvamento em um passo | `Path \| None` |
| `save(image, *, path, directory, fmt, quality, prefix)` | Salva em PNG/JPG/WebP com nome automático | `Path` |
| `build_filename(fmt, prefix)` | Gera `screen_2026-08-15_14-30-05.png` | `str` |
| `default_directory()` | Pasta padrão (`~/Pictures`, criada se necessário) | `Path` |

### Modo silencioso (automação)

Para scripts e automação, use `silent=True` — a captura acontece sem abrir
o overlay:

```python
path = screenkit.capture_and_save(silent=True)            # tela inteira
path = screenkit.capture_and_save(region=(0, 0, 800, 600))  # região pré-definida
```

### Integração com aplicações Qt

Se uma `QApplication` já existir (ex.: seu app PySide6), `select_region()`
a reutiliza automaticamente e roda o diálogo com `exec()` aninhado.
Para integração **não bloqueante**, use:

```python
from screenkit import start_region_selection, capture_region

def on_done(region):
    if region:
        capture_region(region).show()

overlay = start_region_selection(on_done)   # mostra o overlay sem travar o app
```

## Threads

- As funções de captura (`capture_*`) criam a instância do `mss` por chamada
  e são seguras para rodar em `QThread`/`ThreadPoolExecutor`.
- O overlay (`select_region`, `start_region_selection`) deve ser chamado da
  **thread principal** (limitação do Qt).

## Limitações por plataforma

| Recurso | Windows | Linux (X11) | macOS | Wayland |
| ------- | ------- | ----------- | ----- | ------- |
| `capture_full` / `capture_region` | ✅ | ✅ | ✅ | ❌ `mss` não suporta Wayland; use XWayland ou portal do GNOME |
| `capture_window` | ✅ Win32 | ✅ requer `xdotool` | ❌ | ❌ |
| `select_region` (overlay) | ✅ | ✅ | ✅¹ | ✅¹ (o overlay usa Qt, mas a captura depende de `mss`) |

¹ O macOS exige permissão de **Screen Recording** para o terminal/IDE nas
Preferências do Sistema.

### Notas de DPI (escala de exibição)

`select_region()` retorna coordenadas em **pixels físicos** (a escala de
exibição é compensada). Em displays com escalas diferentes por monitor,
informe o `monitor` correto.

## Logging

A biblioteca usa o módulo `logging` (nenhum `print`). Para ver as mensagens:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Desenvolvimento

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest
```

## Versionamento e releases

Este projeto usa **SemVer** (`MAJOR.MINOR.PATCH`). Toda mudança visível para
quem usa a lib deve gerar um release com tag — quem consome via
`screenkit @ git+...@vX.Y.Z` ou PyPI só percebe atualizações assim.

**Checklist de release (rode a cada mudança):**

1. Atualize a `version` no `pyproject.toml` (e `__version__` em
   `src/screenkit/__init__.py`).
2. Registre as mudanças no [CHANGELOG.md](CHANGELOG.md).
3. Rode os testes: `pytest`.
4. Commit e push: `git add -A && git commit -m "..." && git push origin main`.
5. Crie e envie a tag:
   ```powershell
   git tag -a v0.2.0 -m "screenkit v0.2.0"
   git push origin v0.2.0
   ```
   A tag dispara a Action `.github/workflows/release.yml` (testes + publish
   no PyPI via Trusted Publishing).
6. Crie o GitHub Release com as notas do changelog:
   ```powershell
   gh release create v0.2.0 --title "v0.2.0" --notes-from-tag
   ```

> **Dica:** sem release, projetos que usam a lib nunca saberão que houve
> atualização — o pin `@vX.Y.Z` continua apontando para a versão antiga.

## Licença

[MIT](LICENSE)
