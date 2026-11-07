#!/usr/bin/env bash
# Sobe o servidor de tracking do MLflow (deixe este terminal aberto).
#  - metadados (experimentos, runs, registry) -> mlflow.db (SQLite)
#  - artefatos (modelos, gráficos)             -> mlartifacts/
# As opções --allowed-hosts / --cors-allowed-origins liberam o endereço
# *.app.github.dev que o Codespaces usa para abrir a interface no navegador.
cd "$(dirname "$0")/.."
mlflow server \
  --host 127.0.0.1 --port 5000 \
  --backend-store-uri sqlite:///mlflow.db \
  --artifacts-destination ./mlartifacts \
  --allowed-hosts "localhost,localhost:*,127.0.0.1,127.0.0.1:*,*.app.github.dev" \
  --cors-allowed-origins "https://*.app.github.dev"
