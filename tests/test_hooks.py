"""Pruebas de los hooks: carpeta .claude protegida y única autoría en commit y push."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
HOOKS = RAIZ / ".claude" / "hooks"
GITHOOKS = RAIZ / ".githooks"
TRAILER = "Co-Authored-By: Claude <noreply@anthropic.com>"


def hook(nombre, entrada, cwd=RAIZ):
    r = subprocess.run([sys.executable, str(HOOKS / nombre)], input=json.dumps(entrada).encode("utf-8"),
                       capture_output=True, cwd=cwd, env={**os.environ, "CLAUDE_PROJECT_DIR": str(RAIZ)})
    assert r.returncode == 0, r.stderr
    salida = r.stdout.decode("utf-8").strip()
    return json.loads(salida)["hookSpecificOutput"]["permissionDecision"] if salida else None


def proteger(tool, **tool_input):
    return hook("proteger_carpeta_claude.py", {"tool_name": tool, "tool_input": tool_input, "cwd": str(RAIZ)})


def test_carpeta_claude_pide_confirmacion():
    assert proteger("Edit", file_path=str(RAIZ / ".claude" / "rules" / "02_temas.md")) == "ask"
    assert proteger("Write", file_path=".claude/settings.json") == "ask"
    assert proteger("PowerShell", command="Set-Content .claude\\settings.json '{}'") == "ask"
    assert proteger("Bash", command="rm -rf .claude/hooks") == "ask"
    assert proteger("Edit", file_path=str(RAIZ / ".claude" / "CLAUDE.md")) == "ask"


def test_fuera_de_carpeta_claude_no_interviene():
    assert proteger("Edit", file_path=str(RAIZ / "src" / "ejercicio.py")) is None
    assert proteger("Write", file_path=str(RAIZ / "docs" / "README.md")) is None
    assert proteger("Write", file_path=r"C:\Users\x\.claude\projects\p\memory\a.md") is None   # memoria del usuario
    assert proteger("PowerShell", command="Get-Content .claude\\rules\\01_procedimiento.md") is None


def autoria(command, cwd=RAIZ):
    return hook("autoria_git.py", {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(cwd)}, cwd)


def test_commit_sin_coautoria():
    assert autoria(f'git commit -m "Ajusta temas" -m "{TRAILER}"') == "deny"
    assert autoria('git commit -m "Ajusta temas" -m "Generated with [Claude Code](https://claude.com/claude-code)"') == "deny"
    assert autoria('git commit --author="Otra Persona <otra@x.co>" -m "Ajusta temas"') == "deny"
    assert autoria('cd repo; git commit --author="Otra <otra@x.co>" -m "x"') == "deny"
    assert autoria('git commit -m "Ajusta temas de Ubaté"') is None
    assert autoria("git status") is None
    assert autoria('echo "ejemplo: git commit --author=x"') is None      # solo lo menciona en un texto


def git(cwd, *args, ok=True):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if ok:
        assert r.returncode == 0, r.stderr
    return r


@pytest.fixture
def repo(tmp_path):
    if shutil.which("git") is None:
        pytest.skip("git no disponible")
    remoto, local = tmp_path / "remoto.git", tmp_path / "local"
    git(tmp_path, "init", "--bare", str(remoto))
    git(tmp_path, "init", str(local))
    for k, v in (("user.name", "Persona Que Sube"), ("user.email", "persona@ucundinamarca.edu.co"),
                 ("core.hooksPath", str(GITHOOKS).replace("\\", "/"))):
        git(local, "config", k, v)
    git(local, "remote", "add", "origin", str(remoto))
    return local


def commit(repo, archivo, mensaje, *extra):
    (repo / archivo).write_text(archivo, encoding="utf-8")
    git(repo, "add", archivo)
    git(repo, *extra, "commit", "-m", mensaje)


def test_hook_git_commit_msg_quita_coautoria(repo):
    commit(repo, "a.txt", f"Primer cambio\n\n{TRAILER}\n🤖 Generated with [Claude Code](https://claude.com/claude-code)")
    cuerpo = git(repo, "log", "-1", "--format=%B").stdout
    assert "Primer cambio" in cuerpo and "Co-Authored-By" not in cuerpo and "Generated with" not in cuerpo


def test_hook_git_pre_push_exige_autoria_unica(repo):
    commit(repo, "a.txt", "Cambio propio")
    assert git(repo, "push", "origin", "HEAD:main", ok=False).returncode == 0
    commit(repo, "b.txt", "Cambio de otra persona", "-c", "user.email=otra@x.co")
    assert git(repo, "push", "origin", "HEAD:main", ok=False).returncode != 0
    assert autoria("git push origin HEAD:main", cwd=repo) == "deny"      # el hook de Claude también lo detecta
