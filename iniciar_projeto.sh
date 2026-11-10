#!/usr/bin/env bash
# ============================================================
#  AlphaRadar B3 — inicia backend (FastAPI) e frontend (Next.js)
#  Uso (Linux/macOS):  chmod +x iniciar_projeto.sh && ./iniciar_projeto.sh
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"

PY=$(command -v python3 || command -v python || true)
[ -z "$PY" ] && { echo "[ERRO] Python 3.11+ não encontrado."; exit 1; }
command -v npm >/dev/null || { echo "[ERRO] Node.js/npm não encontrado."; exit 1; }

echo "[1/4] Preparando ambiente Python (backend/.venv)..."
[ -x backend/.venv/bin/python ] || "$PY" -m venv backend/.venv
backend/.venv/bin/python -m pip install --quiet --prefer-binary -r backend/requirements.txt

echo "[2/4] Instalando dependências do frontend (somente na primeira vez)..."
[ -d frontend/node_modules ] || npm --prefix frontend install

echo "[3/4] Iniciando backend em http://localhost:8000 ..."
(cd backend && .venv/bin/python -m uvicorn main:app --reload --port 8000) &
BACKEND_PID=$!

echo "[4/4] Iniciando frontend em http://localhost:3000 ..."
npm --prefix frontend run dev &
FRONTEND_PID=$!

# Ao apertar Ctrl+C, encerra os dois servidores juntos.
trap 'echo; echo "Encerrando..."; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null' INT TERM

sleep 8
URL="http://localhost:3000"
(command -v xdg-open >/dev/null && xdg-open "$URL") || (command -v open >/dev/null && open "$URL") || true
echo
echo "Pronto! Dashboard: $URL   |   Documentação da API: http://localhost:8000/docs"
echo "Pressione Ctrl+C para encerrar."
wait
