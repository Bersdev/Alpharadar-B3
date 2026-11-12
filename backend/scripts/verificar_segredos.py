"""
verificar_segredos.py — Procura chaves de API e arquivos sensíveis nos arquivos versionados
============================================================================================

Uso (na raiz do repositório ou em qualquer subpasta):

    python backend/scripts/verificar_segredos.py

Sai com código 1 se achar algo (por isso serve de trava no CI e de gancho antes do commit).
Varre só o que está no Git (``git ls-files``), então ``.env`` local e ``node_modules`` ficam de fora.
Nunca imprime o valor encontrado, só onde está.

Para rodar antes de CADA commit, crie ``.git/hooks/pre-commit`` com:
    #!/bin/sh
    python backend/scripts/verificar_segredos.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PADROES = {
    "chave estilo OpenAI/DeepSeek (sk-...)": r"\bsk-[A-Za-z0-9]{20,}",
    "chave Groq (gsk_...)": r"\bgsk_[A-Za-z0-9]{20,}",
    "chave Google (AIza...)": r"\bAIza[0-9A-Za-z_\-]{30,}",
    "chave Anthropic (sk-ant-...)": r"\bsk-ant-[A-Za-z0-9_\-]{20,}",
    "token do GitHub": r"\b(?:ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{20,}",
    "chave de acesso AWS": r"\bAKIA[0-9A-Z]{16}\b",
    "chave privada": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "URL com usuário e senha": r"https?://[^/\s:@]+:[^/\s:@]+@",
    "NOME_DA_CHAVE=valor preenchido": r"(?m)^[ \t]*[A-Z][A-Z0-9_]*(?:API_KEY|TOKEN|SECRET|PASSWORD)[ \t]*=[ \t]*[^\s#\"'<>$][^\s#]{7,}[ \t]*$",
}
NOMES_PROIBIDOS = re.compile(r"(^|/)(\.env(\..+)?|.*\.pem|.*\.key|.*\.p12|.*\.pfx|id_rsa.*|.*credentials.*\.json)$", re.I)
PERMITIDOS = {".env.example"}


def main() -> int:
    raiz = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True).stdout.strip())
    arquivos = subprocess.run(["git", "-C", str(raiz), "ls-files"], capture_output=True, text=True, check=True).stdout.splitlines()
    achados: list[str] = []
    for rel in arquivos:
        if NOMES_PROIBIDOS.search(rel) and Path(rel).name not in PERMITIDOS:
            achados.append(f"{rel}: nome de arquivo que não deve ser versionado")
            continue
        if Path(rel).name in {"package-lock.json"} or rel.endswith((".png", ".ico", ".webp", ".svg", ".woff2", ".bundle")):
            continue
        try:
            texto = (raiz / rel).read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        for nome, rx in PADROES.items():
            if Path(rel).name == "verificar_segredos.py":
                continue  # este arquivo descreve os padrões
            for m in re.finditer(rx, texto):
                linha = texto.count("\n", 0, m.start()) + 1
                achados.append(f"{rel}:{linha}: {nome}")
    if achados:
        print("POSSÍVEL SEGREDO VERSIONADO (valores omitidos):")
        print("\n".join(f"  - {a}" for a in achados))
        return 1
    print(f"ok: {len(arquivos)} arquivos versionados verificados, nenhum segredo encontrado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
