# MLOps e Deploy de Modelos em Produção — Facens

Repositório único da disciplina. Ele cresce a cada encontro: versionamento e governança (Aula 1),
API e deploy (Aula 2), monitoramento e retreino (Aula 3), segurança e incidentes (Aula 4).

**Problema do curso:** prever a demanda horária de bicicletas compartilhadas
(*Bike Sharing Dataset*, UCI — Fanaee-T & Gama, 2013, licença CC BY 4.0).

## Começando

1. Clique em **Use this template → Create a new repository** (deixe **público**).
2. No seu repositório: **Code → Codespaces → Create codespace on main**.
   A primeira abertura instala tudo sozinha. Espere terminar antes de seguir.
3. Abra um terminal (**Ctrl + `**) e suba o MLflow. **Deixe esse terminal aberto:**
   ```bash
   bash scripts/start_mlflow.sh
   ```
4. Na aba **PORTAS** (PORTS), clique no 🌐 da porta **5000** para abrir a interface do MLflow.
5. Os notebooks das tarefas são liberados durante a aula. Arraste cada um para a pasta `aula01/` do seu Codespace.

## Estrutura

```
├── .devcontainer/        # ambiente do Codespaces (Python 3.12 + dependências)
├── scripts/
│   └── start_mlflow.sh   # servidor MLflow local (SQLite + artefatos em ./mlartifacts)
├── src/                  # código "de produção" do projeto
│   ├── bike.py           #   features, split temporal, métricas
│   ├── get_data.py       #   baixa os dados "disponíveis até" uma data
│   ├── prepare.py        #   estágio prepare  (limpeza)
│   ├── split.py          #   estágio split    (treino/teste no tempo)
│   ├── train.py          #   estágio train    (MLflow + Model Registry)
│   ├── evaluate.py       #   estágio evaluate (metrics.json)
│   └── plot.py           #   estágio plot     (gráfico real × previsto)
├── params.yaml           # hiperparâmetros do pipeline
└── aula01/               # aqui entram os notebooks das tarefas, liberados durante a aula
```

---
