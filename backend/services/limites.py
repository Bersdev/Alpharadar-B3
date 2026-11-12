"""
limites.py — Limitador de uso (rate limit) por IP e global, em memória
========================================================================

A API é pública e sem login, então a defesa contra abuso é o limite de pedidos:

    * por IP:   quantos pedidos UM visitante pode fazer na janela (padrão: 60 s)
    * global:   quantos pedidos TODOS juntos podem fazer na janela (cobre quem troca de IP)

Características de segurança:
    - Janela deslizante: guarda o horário de cada pedido recente e descarta os antigos.
    - Memória limitada: no máximo ``max_ips`` IPs rastreados; os menos recentes são descartados (LRU).
    - Thread-safe: leitura, checagem e escrita acontecem sob a mesma trava (sem corrida entre threads).

Limitação assumida: o estado fica na memória de UM processo. Com várias réplicas, cada uma conta
separado; para isso seria preciso um armazenamento compartilhado (ex.: Redis).
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict


class Limitador:
    def __init__(self, por_ip: int, global_: int, janela: float = 60.0, max_ips: int = 5000) -> None:
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
        """Registra o pedido e devolve True; devolve False (sem registrar) se o limite foi atingido."""
        agora = time.monotonic()
        with self._trava:
            self._todos[:] = [t for t in self._todos if agora - t < self.janela]
            recentes = [t for t in self._ips.get(ip, []) if agora - t < self.janela]
            if len(recentes) >= self.por_ip or len(self._todos) >= self.global_:
                self._ips[ip] = recentes  # mantém só os recentes (não deixa a lista crescer)
                return False
            recentes.append(agora)
            self._todos.append(agora)
            self._ips[ip] = recentes
            self._ips.move_to_end(ip)
            while len(self._ips) > self.max_ips:
                self._ips.popitem(last=False)
            return True
