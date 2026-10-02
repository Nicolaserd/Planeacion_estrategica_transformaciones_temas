"""Hook PreToolUse (Bash y PowerShell) · Commits y push con una sola autoría: la de la persona que hace el push.

Regla del proyecto (Nicolás, 2026-10-02). El hook bloquea ("deny"):
  - `git commit` si el mensaje trae coautores (Co-Authored-By) o atribución a herramientas ("Generated with Claude Code",
    noreply@anthropic.com, 🤖), o si usa --author para firmar con otro nombre;
  - `git push` si algún commit por subir tiene un autor distinto de `git config user.email`, coautores o atribución.
Complementa a `.claude/settings.json` ("attribution" vacío) y a los hooks de git en `.githooks/`.
"""
import json
import os
import re
import subprocess
import sys

ATRIBUCION = re.compile(r"co-authored-by\s*:|noreply@anthropic\.com|generated with \[?claude|\U0001F916", re.I)
# git como comando (al inicio o tras ; & | ( { o salto de línea), no dentro de un texto entre comillas
GIT = r"(?:^|[;&|({\n])\s*git(?:\.exe)?(?:\s+-[cC]\s+\S+)*\s+"


def git(args, cwd):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout.strip()


def denegar(motivo: str):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": f"Regla del proyecto (única autoría de quien hace el push): {motivo}",
    }}))  # JSON en ASCII: la consola de Windows no garantiza UTF-8
    sys.exit(0)


def revisar_commit(cmd: str, cwd: str):
    if ATRIBUCION.search(cmd):
        denegar("el mensaje del commit no puede llevar Co-Authored-By ni atribución a Claude u otra herramienta. "
                "Quita esas líneas y vuelve a intentarlo.")
    if re.search(r"--author\b", cmd):
        denegar("no uses --author: el commit debe quedar a nombre de la persona configurada en git (user.name/user.email).")
    m = re.search(r"(?:\s-F|\s--file)[\s=]+(\"[^\"]+\"|'[^']+'|\S+)", cmd)
    if m:
        ruta = m.group(1).strip("\"'")
        ruta = ruta if os.path.isabs(ruta) else os.path.join(cwd, ruta)
        if os.path.exists(ruta) and ATRIBUCION.search(open(ruta, encoding="utf-8", errors="replace").read()):
            denegar(f"el archivo de mensaje {m.group(1)} trae Co-Authored-By o atribución a una herramienta.")


def revisar_push(cwd: str):
    if git(["rev-parse", "--is-inside-work-tree"], cwd)[0]:
        return
    email = git(["config", "user.email"], cwd)[1].lower()
    rc, lista = git(["rev-list", "@{u}..HEAD"], cwd)
    if rc:
        rc, lista = git(["rev-list", "HEAD", "--not", "--remotes"], cwd)
    problemas = []
    for sha in lista.split():
        _, info = git(["log", "-1", "--format=%ae%x00%B", sha], cwd)
        autor, _, cuerpo = info.partition("\x00")
        if email and autor.lower() != email:
            problemas.append(f"{sha[:7]} es de {autor}, no de {email}")
        if ATRIBUCION.search(cuerpo):
            problemas.append(f"{sha[:7]} tiene coautoría o atribución en el mensaje")
    if problemas:
        denegar("hay commits por subir que no cumplen: " + "; ".join(problemas[:10]) +
                ". Corrígelos (por ejemplo con git commit --amend o git rebase) antes de hacer push.")


def main():
    d = json.loads(sys.stdin.buffer.read().decode("utf-8-sig") or "{}")
    cmd = (d.get("tool_input") or {}).get("command", "")
    cwd = d.get("cwd") or os.getcwd()
    if re.search(GIT + r"commit\b", cmd, re.I):
        revisar_commit(cmd, cwd)
    if re.search(GIT + r"push\b", cmd, re.I):
        revisar_push(cwd)
    sys.exit(0)


if __name__ == "__main__":
    main()
