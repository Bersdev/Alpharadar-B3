"use client";

import { useSyncExternalStore } from "react";

/**
 * Armazenamento no navegador (localStorage) acessível como estado do React.
 * Os dados do usuário (favoritos, carteira) ficam só no aparelho dele: o servidor não os recebe.
 *
 * O localStorage é uma entrada NÃO CONFIÁVEL: outra extensão, uma versão antiga do app ou o próprio usuário
 * podem ter gravado qualquer coisa. Por isso todo valor lido passa por ``validar`` e, se estiver fora do formato
 * esperado, é descartado em vez de quebrar a tela.
 */
export function criarStore<T>(chave: string, vazio: T, validar: (valor: unknown) => T | null) {
  let cache: T | undefined;
  const ouvintes = new Set<() => void>();

  const ler = (): T => {
    if (cache !== undefined) return cache;
    try {
      const bruto = localStorage.getItem(chave);
      cache = bruto ? (validar(JSON.parse(bruto)) ?? vazio) : vazio;
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
    const limpo = validar(novo) ?? vazio;
    cache = limpo;
    try {
      localStorage.setItem(chave, JSON.stringify(limpo));
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

export const LIMITE_MAXIMO = 1e9; // quantidade e preço acima disso são tratados como erro de digitação
const FORMATO_TICKER = /^[A-Z0-9.\-]{1,12}$/;
const MAX_FAVORITOS = 200;
const MAX_POSICOES = 200;

/** Favoritos: lista de tickers no formato esperado, sem repetição. */
export function validarFavoritos(valor: unknown): string[] | null {
  if (!Array.isArray(valor)) return null;
  const limpos = valor.filter((t): t is string => typeof t === "string" && FORMATO_TICKER.test(t));
  return [...new Set(limpos)].slice(0, MAX_FAVORITOS);
}

/** Carteira: cada posição precisa ter ticker válido e números finitos, positivos e dentro do limite. */
export function validarCarteira(valor: unknown): Posicao[] | null {
  if (!Array.isArray(valor)) return null;
  const posicoes: Posicao[] = [];
  const vistos = new Set<string>();
  for (const p of valor) {
    if (typeof p !== "object" || p === null) continue;
    const { ticker, qtd, pm } = p as Record<string, unknown>;
    if (typeof ticker !== "string" || !FORMATO_TICKER.test(ticker) || vistos.has(ticker)) continue;
    if (typeof qtd !== "number" || typeof pm !== "number") continue;
    if (!Number.isFinite(qtd) || !Number.isFinite(pm) || qtd <= 0 || pm <= 0 || qtd > LIMITE_MAXIMO || pm > LIMITE_MAXIMO) continue;
    vistos.add(ticker);
    posicoes.push({ ticker, qtd, pm });
  }
  return posicoes.slice(0, MAX_POSICOES);
}

const FAVORITOS = criarStore<string[]>("alpharadar-favoritos", [], validarFavoritos);
const CARTEIRA = criarStore<Posicao[]>("alpharadar-carteira", [], validarCarteira);

export const useFavoritos = FAVORITOS.useStore;
export function alternarFavorito(ticker: string) {
  const atual = FAVORITOS.ler();
  FAVORITOS.gravar(atual.includes(ticker) ? atual.filter((t) => t !== ticker) : [...atual, ticker]);
}

export const useCarteira = CARTEIRA.useStore;
export const salvarCarteira = CARTEIRA.gravar;
