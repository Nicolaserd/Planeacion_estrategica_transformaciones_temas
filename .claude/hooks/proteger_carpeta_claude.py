"""Hook PreToolUse · La carpeta .claude/ del proyecto no se modifica sin preguntar primero.

Si Claude intenta crear, editar o borrar algo dentro de .claude/ (con Edit, Write, MultiEdit o NotebookEdit, o con un
comando de Bash o PowerShell que escriba ahí), el hook responde "ask" y Claude Code pide confirmación a la persona.
Todo lo demás pasa sin intervenir. Regla del proyecto (Nicolás, 2026-10-02).
"""
import json
import os
import re
import sys

ESCRITURA = re.compile(
    r">|\b(Set-Content|Add-Content|Out-File|Clear-Content|New-Item|Remove-Item|Move-Item|Copy-Item|Rename-Item|"
    r"rm|rmdir|del|mv|cp|mkdir|touch|tee|ni|ri|mi|ci)\b|sed\s+-i|WriteAll|\.write\(|open\([^)]*['\"][wa]",
    re.I)


def normal(ruta: str) -> str:
    return os.path.normcase(os.path.abspath(ruta)).rstrip("\\/")


def main():
    d = json.loads(sys.stdin.buffer.read().decode("utf-8-sig") or "{}")
    herramienta = d.get("tool_name", "")
    entrada = d.get("tool_input") or {}
    cwd = d.get("cwd") or os.getcwd()
    proyecto = os.environ.get("CLAUDE_PROJECT_DIR") or cwd
    carpeta = normal(os.path.join(proyecto, ".claude"))

    def dentro(ruta):
        if not ruta:
            return False
        p = normal(ruta if os.path.isabs(ruta) else os.path.join(cwd, ruta))
        return p == carpeta or p.startswith(carpeta + os.sep)

    motivo = None
    if herramienta in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        ruta = entrada.get("file_path") or entrada.get("notebook_path")
        if dentro(ruta):
            motivo = f"{herramienta} sobre {ruta}"
    elif herramienta in ("Bash", "PowerShell"):
        cmd = entrada.get("command", "")
        absoluta = carpeta.replace("\\", "/")
        menciona = (re.search(r"(^|[\s\"'=(])\.?[\\/]?\.claude([\\/]|\s|$|[\"'])", cmd)
                    or absoluta in os.path.normcase(cmd).replace("\\", "/"))
        if menciona and ESCRITURA.search(cmd):
            motivo = f"comando que escribe en .claude: {cmd[:120]}"
    if motivo:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": ("Regla del proyecto: cualquier cambio en la carpeta .claude/ (reglas, hooks, "
                                         f"configuración) requiere tu aprobación. Acción: {motivo}"),
        }}))  # JSON en ASCII: la consola de Windows no garantiza UTF-8
    sys.exit(0)


if __name__ == "__main__":
    main()
