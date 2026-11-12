"""
limites.py — Limitador de uso (rate limit) por IP e, opcionalmente, global, em memória
=======================================================================================

A API é pública e sem login, então a defesa contra abuso é o limite de pedidos:

    * por IP:   quantos pedidos UM visitante pode fazer na janela (padrão: 60 s)
    * global:   (opcional) quantos pedidos TODOS juntos podem fazer na janela

Quando usar o teto global: só para proteger um recurso externo limitado (a cota gratuita da IA). Num
endpoint barato, um teto global é uma ARMA contra os visitantes legítimos: bastam alguns endereços
distintos para esgotá-lo e bloquear todo mundo. Por isso ``global_`` é opcional (``None`` = sem teto).

Características de segurança:
    - Janela deslizante: guarda o horário de cada pedido recente e descarta os antigos.
    - Memória limitada: no máximo ``max_ips`` IPs rastreados (LRU). Um pedido BLOQUEADO nunca cria
      uma entrada nova: quem estoura o limite não consegue encher a memória.
    - IPv6 agrupado por /64: quem tem uma rede IPv6 controla milhões de endereços; tratá-los como um
      só impede que girar de endereço burle o limite.
    - Thread-safe: leitura, checagem e escrita acontecem sob a mesma trava.

Limitação assumida: o estado fica na memória de UM processo. Com várias réplicas, cada uma conta
separado; para isso seria preciso um armazenamento compartilhado (ex.: Redis).
"""

from __future__ import annotations

import ipaddress
import threading
import time
from collections import OrderedDict


def chave_do_ip(ip: str) -> str:
    """IPv4 como está; IPv6 vira o prefixo /64 (IPv4 embutido em IPv6 volta a ser IPv4); texto estranho é truncado."""
    try:
        endereco = ipaddress.ip_address(ip.strip())
    except ValueError:
        return ip.strip()[:64]
    if isinstance(endereco, ipaddress.IPv6Address):
        if endereco.ipv4_mapped is not None:
            return str(endereco.ipv4_mapped)
        return str(ipaddress.ip_network(f"{endereco}/64", strict=False))
    return str(endereco)


class Limitador:
    def __init__(self, por_ip: int, global_: int | None = None, janela: float = 60.0, max_ips: int = 5000) -> None:
        self.por_ip = por_ip
        self.global_ = global_
        self.janela = janela
        self.max_ips = max_ips
        self._ips: OrderedDict[str, list[float]] = OrderedDict()
        self._todos: list[float] = []
        self._trava = threading.Lock()

    def limpar(self) -> None:
        with self._trava:
            self._ips.clear()
            self._todos.clear()

    def permitir(self, ip: str) -> bool:
        """Registra o pedido e devolve True; devolve False (sem registrar nada novo) se o limite foi atingido."""
        chave = chave_do_ip(ip)
        agora = time.monotonic()
        with self._trava:
            if self.global_ is not None:
                self._todos[:] = [t for t in self._todos if agora - t < self.janela]
            recentes = [t for t in self._ips.get(chave, []) if agora - t < self.janela]
            estourou_global = self.global_ is not None and len(self._todos) >= self.global_
            if len(recentes) >= self.por_ip or estourou_global:
                if chave in self._ips:  # só atualiza quem já era conhecido; IP novo bloqueado não ocupa memória
                    self._ips[chave] = recentes
                return False
            recentes.append(agora)
            if self.global_ is not None:
                self._todos.append(agora)
            self._ips[chave] = recentes
            self._ips.move_to_end(chave)
            while len(self._ips) > self.max_ips:
                self._ips.popitem(last=False)
            return True
