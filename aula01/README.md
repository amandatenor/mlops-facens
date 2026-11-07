# Aula 1: fundamentos de MLOps, CI/CD e versionamento

Os notebooks das tarefas são liberados ao longo da aula. Arraste cada um para esta pasta e faça as tarefas
**na ordem**: cada uma usa o resultado da anterior.

| Tarefa | Tema |
|---|---|
| **T0** | Preparação do ambiente e dados v1 |
| **T1** | DVC: pipeline com `dvc.yaml` e `dvc repro` |
| **T2** | MLflow: experimentos, parâmetros, métricas e artefatos |
| **T3** | MLflow Model Registry: registro, promoção e rollback |
| **T4** | DVC: versionamento de dados e linhagem com o MLflow |

> **Antes de tudo:** servidor MLflow no ar em um terminal separado (`bash scripts/start_mlflow.sh`).

## Como cada tarefa funciona

Os notebooks de `t1_...` a `t4_...` têm duas partes:

1. **Parte 1 · Juntos:** alguém compartilha a tela e rodamos uma vez, conversando sobre cada passo.
2. **Parte 2 · Sozinhos:** você aplica o mesmo fluxo a um caso novo, no seu Codespace. As células com `# TODO` são suas.

A T0 é toda feita junto. Escolha o kernel **Python 3.12** e rode célula a célula.

Nas células `%%bash`, os comandos que mudam o Git e o DVC vêm comentados (com `#`).
Quando chegar a hora, tire o `#` (selecione as linhas e use **Ctrl + /**) e rode a célula.
