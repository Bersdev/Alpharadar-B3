"""
http_seguro.py — Downloads de fontes externas com teto de tamanho
===================================================================

Feeds RSS e APIs de terceiros são dados NÃO CONFIÁVEIS: uma fonte comprometida (ou um redirecionamento
malicioso) poderia devolver gigabytes e esgotar a memória do servidor. ``baixar`` lê a resposta em
pedaços e desiste ao passar de ``max_bytes``. Só aceita http(s).
"""

from __future__ import annotations

from urllib.parse import urlparse

import requests

LIMITE_PADRAO = 2_000_000  # 2 MB: sobra para qualquer feed legítimo


class RespostaGrande(Exception):
    """A resposta passou do tamanho máximo permitido."""


def url_http_valida(url: str) -> bool:
    try:
        p = urlparse(url.strip())
    except ValueError:
        return False
    return p.scheme in ("http", "https") and bool(p.netloc)


def baixar(url: str, *, timeout: float = 8, max_bytes: int = LIMITE_PADRAO, **kwargs) -> bytes:
    """GET que devolve o corpo (bytes) ou levanta ``RespostaGrande`` / erro HTTP."""
    if not url_http_valida(url):
        raise ValueError("URL inválida: só http(s)")
    with requests.get(url, timeout=timeout, stream=True, **kwargs) as resp:
        try:
            resp.raise_for_status()
        except requests.HTTPError as erro:
            # Guarda um pedaço do corpo do erro (até 4 KB): APIs como a brapi explicam a causa ali ("code").
            try:
                erro.corpo_erro = resp.raw.read(4096, decode_content=True)  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                erro.corpo_erro = b""  # type: ignore[attr-defined]
            raise
        anunciado = resp.headers.get("content-length")
        if anunciado and anunciado.isdigit() and int(anunciado) > max_bytes:
            raise RespostaGrande(f"resposta anuncia {anunciado} bytes")
        partes: list[bytes] = []
        total = 0
        for pedaco in resp.iter_content(chunk_size=65_536):
            total += len(pedaco)
            if total > max_bytes:
                raise RespostaGrande(f"resposta passou de {max_bytes} bytes")
            partes.append(pedaco)
    return b"".join(partes)
