"use client";

import { useSyncExternalStore } from "react";

/**
 * Armazenamento no navegador (localStorage) acessível como estado do React.
 * Os dados do usuário (favoritos, carteira) ficam só no aparelho dele: o servidor não os recebe.
 */
export function criarStore<T>(chave: string, vazio: T) {
  let cache: T | undefined;
  const ouvintes = new Set<() => void>();

  const ler = (): T => {
    if (cache !== undefined) return cache;
    try {
      const bruto = localStorage.getItem(chave);
      cache = bruto ? (JSON.parse(bruto) as T) : vazio;
    } catch {
      cache = vazio; // armazenamento bloqueado ou conteúdo corrompido
    }
    return cache;
  };

  const assinar = (aviso: () => void) => {
    ouvintes.add(aviso);
    const aoMudarEmOutraAba = (e: StorageEvent) => {
      if (e.key === chave) {
        cache = undefined;
        aviso();
      }
    };
    window.addEventListener("storage", aoMudarEmOutraAba);
    return () => {
      ouvintes.delete(aviso);
      window.removeEventListener("storage", aoMudarEmOutraAba);
    };
  };

  const gravar = (novo: T) => {
    cache = novo;
    try {
      localStorage.setItem(chave, JSON.stringify(novo));
    } catch {
      /* sem espaço ou bloqueado: a mudança vale só nesta visita */
    }
    ouvintes.forEach((f) => f());
  };

  const useStore = () => useSyncExternalStore(assinar, ler, () => vazio);
  return { useStore, gravar, ler };
}

export interface Posicao {
  ticker: string;
  qtd: number;
  pm: number; // preço médio pago, na moeda do ativo
}

const FAVORITOS = criarStore<string[]>("alpharadar-favoritos", []);
const CARTEIRA = criarStore<Posicao[]>("alpharadar-carteira", []);

export const useFavoritos = FAVORITOS.useStore;
export function alternarFavorito(ticker: string) {
  const atual = FAVORITOS.ler();
  FAVORITOS.gravar(atual.includes(ticker) ? atual.filter((t) => t !== ticker) : [...atual, ticker]);
}

export const useCarteira = CARTEIRA.useStore;
export const salvarCarteira = CARTEIRA.gravar;
