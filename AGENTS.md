# AGENTS.md

Instruções para agentes e desenvolvedores trabalhando no repositório.

## Comandos

```powershell
# ambiente (Windows)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

# testes
pytest
```

## Versionamento e releases

Este projeto usa **SemVer** (`MAJOR.MINOR.PATCH`). Toda mudança visível para
quem usa a lib deve gerar um release com tag — quem consome via
`screenkit @ git+...@vX.Y.Z` ou PyPI só percebe atualizações assim.

**Checklist de release (rode a cada mudança):**

1. Atualize a `version` no `pyproject.toml` (e `__version__` em
   `src/screenkit/__init__.py`).
2. Registre as mudanças no `CHANGELOG.md`.
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
