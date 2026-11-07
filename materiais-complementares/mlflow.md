# MLflow: material complementar

O MLflow é uma plataforma open source para o ciclo de vida de modelos de Machine Learning. Com ele você registra experimentos, empacota modelos num formato padrão e controla quais versões estão aprovadas para uso. Funciona com a maioria das bibliotecas de ML (scikit-learn, XGBoost, CatBoost, PyTorch...) e em qualquer ambiente: no seu computador, no Codespaces ou num servidor da empresa.

Este material segue a versão usada na disciplina, o **MLflow 3.17.0**. Os exemplos usam um caso diferente do das aulas: a **previsão de vendas diárias de uma rede de lojas** (experimento `previsao-vendas`, modelo registrado `vendas-diarias`).

> [!TIP]
> Documentação oficial: <https://mlflow.org/docs/latest/>
>
> - Tracking: <https://mlflow.org/docs/latest/ml/tracking/>
> - Model Registry: <https://mlflow.org/docs/latest/ml/model-registry/>

---

## 1. Componentes principais

Na parte de ML clássico, que é a que usamos na disciplina, o MLflow tem três componentes centrais:

- **MLflow Tracking**: registra o que aconteceu em cada treino.
- **MLflow Models**: define um formato padrão para salvar e carregar modelos.
- **Model Registry**: guarda as versões dos modelos e indica qual delas está em uso.

Existe ainda o **MLflow Projects**, mais antigo, e um conjunto de recursos para IA generativa (traces, avaliação de LLMs), que ficam fora do escopo da disciplina.

### 1.1 MLflow Tracking

O Tracking é uma API e uma interface para registrar parâmetros, métricas, tags e arquivos de cada execução do seu código e consultar tudo isso depois.

O que se registra em cada execução:

- **Parâmetros**: hiperparâmetros do modelo (por exemplo, o número de árvores de um Random Forest) ou outras escolhas do desenvolvimento.
- **Métricas**: valores numéricos de desempenho (RMSE, MAE, acurácia...).
- **Tags**: rótulos em texto para organizar e filtrar (autor, versão dos dados, versão do experimento...).
- **Artefatos**: arquivos gerados na execução (gráficos, relatórios, o próprio modelo).

Tudo isso fica organizado em dois níveis:

- Um **run** é uma execução de um trecho de código, por exemplo uma rodada do `train.py`. Cada run guarda seus parâmetros, métricas, tags, artefatos e os horários de início e fim.
- Um **experimento** agrupa os runs de um mesmo objetivo. Em geral, todos os treinos de um projeto ficam num experimento com o nome desse objetivo.

```python
import mlflow

mlflow.set_tracking_uri("http://127.0.0.1:5000")  # servidor do MLflow
mlflow.set_experiment("previsao-vendas")          # cria o experimento se ele não existir

with mlflow.start_run(run_name="rf-100"):
    mlflow.set_tags({"autor": "maria", "version": "1.0.0"})

    params = {"n_estimators": 100, "max_depth": 8}
    mlflow.log_params(params)

    model = RandomForestRegressor(**params, random_state=42).fit(X_train, y_train)
    rmse = root_mean_squared_error(y_test, model.predict(X_test))

    mlflow.log_metric("test_rmse", rmse)
    mlflow.log_artifact("reports/residuos.png")   # qualquer arquivo
```

#### Autolog

Em vez de registrar cada item à mão, você pode chamar `mlflow.autolog()` antes do treino. O MLflow passa a registrar sozinho parâmetros, métricas e o modelo das bibliotecas suportadas (scikit-learn, XGBoost, LightGBM, PyTorch, Keras, Spark...).

```python
import mlflow

mlflow.autolog()

# seu código de treino aqui...
```

O autolog é prático para explorar. Em projetos, muitas equipes preferem o registro explícito: fica claro no código o que é registrado e com qual nome. O importante é decidir isso no começo do projeto e manter a escolha.

#### Registrando qualquer informação útil

`log_param` e `set_tag` servem para qualquer informação, não só para hiperparâmetros. Alguns exemplos:

- um parâmetro `features` com a lista de colunas usadas no modelo;
- um parâmetro `n_amostras_treino` com o tamanho do conjunto de treino;
- uma tag `modo` indicando uma configuração específica daquela execução.

#### Ligando o run à versão dos dados

Um run só é reproduzível se você souber **com quais dados** ele foi treinado. Quando os dados são versionados com o DVC, o arquivo `.dvc` guarda o md5 do dado. Registrar esse md5 como tag liga cada run a uma versão exata dos dados:

```python
import yaml

def versao_dos_dados(arquivo_dvc="data/raw/vendas.csv.dvc"):
    """md5 do dado versionado pelo DVC (ou 'nao-versionado')."""
    try:
        with open(arquivo_dvc) as f:
            return yaml.safe_load(f)["outs"][0]["md5"]
    except FileNotFoundError:
        return "nao-versionado"

with mlflow.start_run():
    mlflow.set_tag("data_version", versao_dos_dados())
```

Com isso, a pergunta "esse modelo foi treinado com quais dados?" passa a ter resposta direta: basta comparar a tag `data_version` com o md5 de cada versão do dado no Git.

> [!NOTE]
> O md5 identifica o **dado**. O hash do commit do Git identifica o **código**. Se quiser registrar os dois, o commit atual sai de `git rev-parse HEAD` (o hash completo tem 40 caracteres; os 7 primeiros costumam bastar para identificação).

#### MLflow Data

O MLflow também tem um módulo para registrar datasets (`mlflow.data` + `mlflow.log_input`). Na disciplina não usamos esse módulo, porque o DVC já cuida do versionamento dos dados e o vínculo com o run é feito pela tag `data_version`.

### 1.2 MLflow Models

O MLflow Models define um formato padrão para salvar modelos. Cada modelo salvo é uma pasta com os arquivos do modelo e um arquivo `MLmodel`, que descreve em quais **flavors** (formatos) ele pode ser carregado. Alguns flavors disponíveis:

- scikit-learn
- XGBoost, LightGBM, CatBoost
- PyTorch, TensorFlow, Keras
- `pyfunc`: o flavor genérico, que todo modelo tem e que só expõe o `predict`

Para salvar, use o `log_model` do flavor. No MLflow 3, o nome do modelo dentro do run vai no argumento `name` (o antigo `artifact_path` está descontinuado):

```python
from mlflow.models import infer_signature

with mlflow.start_run() as run:
    signature = infer_signature(X_train, model.predict(X_train))
    mlflow.sklearn.log_model(
        model,
        name="model",
        signature=signature,
        input_example=X_train.head(3),
        serialization_format="cloudpickle",
    )
```

Três detalhes desse trecho:

- **Signature**: registra as colunas e os tipos de entrada e saída. Uma previsão com coluna faltando ou tipo incompatível passa a dar erro, em vez de gerar um resultado errado em silêncio.
- **Input example**: guarda algumas linhas de exemplo junto do modelo. Ajuda quem vai consumir o modelo a saber o formato esperado.
- **`serialization_format="cloudpickle"`**: no MLflow 3.17, o formato padrão do scikit-learn é o skops, que recusa modelos de árvore (o erro fala em *untrusted types*). Por isso usamos o cloudpickle. Essa escolha tem implicações de segurança, que voltam na Aula 4.

Para carregar, use o `load_model` do flavor ou o `pyfunc`:

```python
model = mlflow.sklearn.load_model(f"runs:/{run_id}/model")   # objeto do scikit-learn
model = mlflow.pyfunc.load_model(f"runs:/{run_id}/model")    # só com predict
```

### 1.3 Model Registry

O Model Registry é o catálogo dos modelos que podem ir para uso. Um **modelo registrado** tem um nome único e reúne:

- **versões**: cada registro com o mesmo nome cria a próxima versão (1, 2, 3...);
- **aliases**: apelidos que apontam para uma versão, como `@champion` (a versão em uso) e `@challenger` (a candidata);
- **tags**: informações de governança, como o resultado da validação ou o motivo de uma decisão;
- **descrição**.

#### Registrando uma versão

Depois de comparar os runs e escolher o melhor, registre o modelo daquele run:

```python
mv = mlflow.register_model(f"runs:/{run_id}/model", "vendas-diarias")
print(mv.version)
```

Se o nome ainda não existe, o MLflow cria o modelo registrado e a versão 1. Se já existe, cria a próxima versão. Também dá para registrar direto no treino, passando `registered_model_name="vendas-diarias"` para o `log_model`.

> [!NOTE]
> No MLflow 3, o `register_model("runs:/...")` mostra um aviso sobre *LoggedModel*. É esperado e não impede o registro.

**Registrar não coloca nada em produção.** Uma versão nova é só uma versão nova. Quem diz qual versão está em uso é o alias.

#### Aliases e tags

```python
from mlflow import MlflowClient

client = MlflowClient()

# a versão 3 passa a ser a candidata
client.set_registered_model_alias("vendas-diarias", "challenger", 3)

# depois da validação, registramos o resultado e a decisão
client.set_model_version_tag("vendas-diarias", 3, "validation_status", "aprovado")
client.set_model_version_tag("vendas-diarias", 3, "motivo", "RMSE menor que o da versão em uso")

# e a versão 3 vira a campeã
client.set_registered_model_alias("vendas-diarias", "champion", 3)
```

Quem consome o modelo nunca usa o número da versão, e sim o alias:

```python
model = mlflow.pyfunc.load_model("models:/vendas-diarias@champion")
```

Assim, trocar o modelo em uso é só mover o alias. O código de quem consome não muda.

> [!IMPORTANT]
> Versões antigas do MLflow usavam **stages** (`Staging`, `Production`, `Archived`). Os stages estão descontinuados desde o MLflow 2.9 e foram substituídos por aliases e tags. Se encontrar `transition_model_version_stage` num tutorial, ele é anterior a essa mudança.

### 1.4 Backend store e artifact store

O servidor do MLflow guarda as informações em dois lugares:

- **Backend store**: os metadados, ou seja, experimentos, runs, parâmetros, métricas, tags e o Model Registry. Pode ser um arquivo SQLite (como nas aulas) ou um banco como PostgreSQL ou MySQL. O Model Registry precisa de um backend em banco de dados.
- **Artifact store**: os arquivos, ou seja, modelos, gráficos e relatórios. Pode ser uma pasta local (como nas aulas) ou um armazenamento de objetos como S3, Azure Blob ou Google Cloud Storage.

Quando você usa o MLflow sem configurar nada, ele grava tudo numa pasta `./mlruns`. Na disciplina, o servidor usa `mlflow.db` (SQLite) como backend store e a pasta `mlartifacts/` como artifact store.

### 1.5 MLflow Projects

O MLflow Projects é uma convenção para empacotar código com suas dependências e executá-lo de forma reproduzível. Na disciplina não usamos esse componente: quem organiza a execução das etapas e a reprodutibilidade é o pipeline do DVC (`dvc.yaml` + `dvc repro`).

---

## 2. Configurando o MLflow

### 2.1 Na disciplina (Codespaces)

O MLflow já vem instalado no Codespace. Num ambiente seu, instale dentro do ambiente virtual do projeto:

```bash
pip install mlflow==3.17.0
```

O servidor sobe pelo script `scripts/start_mlflow.sh`, que fica num terminal aberto durante a aula:

```bash
mlflow server \
  --host 127.0.0.1 --port 5000 \
  --backend-store-uri sqlite:///mlflow.db \
  --artifacts-destination ./mlartifacts \
  --allowed-hosts "localhost,localhost:*,127.0.0.1,127.0.0.1:*,*.app.github.dev" \
  --cors-allowed-origins "https://*.app.github.dev"
```

O que cada opção faz:

- `--backend-store-uri`: onde ficam os metadados (o arquivo `mlflow.db`).
- `--artifacts-destination`: onde ficam os artefatos (a pasta `mlartifacts/`). Os clientes enviam os arquivos ao servidor, e ele grava nessa pasta.
- `--allowed-hosts` e `--cors-allowed-origins`: o servidor do MLflow 3 recusa endereços que ele não conhece. Essas opções liberam o endereço `*.app.github.dev`, que o Codespaces usa para abrir a interface no navegador.

O código aponta para o servidor com `mlflow.set_tracking_uri("http://127.0.0.1:5000")` ou com a variável de ambiente `MLFLOW_TRACKING_URI`.

> [!TIP]
> Use sempre `mlflow server` (pelo script), e não `mlflow ui`. O `mlflow ui` serve para olhar uma pasta local, e sem as opções de host a interface no Codespaces responde com erro (*Invalid Host header* ou 403).

**Sem servidor:** dá para usar o MLflow apontando direto para o arquivo SQLite, com `MLFLOW_TRACKING_URI=sqlite:///mlflow.db`. Tracking e Registry funcionam normalmente, mas não há interface gráfica; os resultados aparecem pelo `mlflow.search_runs()`.

### 2.2 Como isso fica numa empresa

Num time, o MLflow precisa ser compartilhado: todos registram no mesmo servidor e enxergam os mesmos experimentos e modelos. Uma configuração comum é:

- **backend store** num PostgreSQL gerenciado (por exemplo, Amazon RDS), com um banco por projeto e um usuário por pessoa;
- **artifact store** num bucket de armazenamento de objetos (por exemplo, Amazon S3), com uma pasta do projeto para o MLflow, outra para o remote do DVC e outra para os dados brutos.

As credenciais ficam num arquivo `.env` na raiz do repositório. Tome como exemplo um projeto fictício, o **Projeto Aurora** (previsão de demanda de energia):

```bash
POSTGRES_USER=seu_usuario
POSTGRES_PASSWORD=sua_senha
POSTGRES_HOST=meu-banco.xxxxxxxx.us-east-1.rds.amazonaws.com
POSTGRES_PORT=5432
POSTGRES_DB_MLFLOW=aurora_mlflow
ARTIFACTS_BUCKET=s3://empresa-aurora/mlflow/
```

> [!WARNING]
> O `.env` **nunca** vai para o Git: ele tem senhas. Coloque-o no `.gitignore` e combine com o time como as credenciais são distribuídas.

O script de inicialização lê o `.env` e sobe o servidor apontando para o banco e para o bucket:

```bash
#!/bin/bash
source .env
BACKEND_URI="postgresql+psycopg2://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DB_MLFLOW"

mlflow server \
  --backend-store-uri "$BACKEND_URI" \
  --artifacts-destination "$ARTIFACTS_BUCKET" \
  --host 127.0.0.1 --port 5000
```

A estrutura é a mesma das aulas: só mudam o lugar do backend store (o banco no lugar do `mlflow.db`) e o do artifact store (o bucket no lugar de `mlartifacts/`). Para o PostgreSQL e o S3 são necessários os pacotes `psycopg2-binary` e `boto3`, além das credenciais da nuvem configuradas na máquina. Em muitas empresas, esse servidor fica permanentemente no ar numa máquina do time, e cada pessoa só aponta o `MLFLOW_TRACKING_URI` para ele.

Também é comum o projeto ter um pequeno módulo de apoio (por exemplo, `src/utils/mlflow.py`) com funções para configurar a conexão a partir do `.env`, criar o experimento se ele não existir e carregar o modelo pelo alias. O nome do experimento costuma ficar no `params.yaml`, junto dos outros parâmetros do pipeline.

---

## 3. MLflow e DVC: quem faz o quê

As duas ferramentas se complementam. O MLflow responde "o que foi testado, qual resultado deu e qual modelo está em uso". O DVC responde "com quais dados e por qual sequência de etapas esse resultado foi produzido".

| Necessidade | MLflow | DVC |
|---|---|---|
| Registrar parâmetros e métricas de cada treino | ✅ Ponto forte, com interface para comparar runs | Parcial (`dvc metrics`, `dvc params`), sem interface própria |
| Versionar dados grandes junto com o Git | ❌ | ✅ Ponto forte (`dvc add`, remote, `dvc pull`) |
| Pipeline reproduzível com dependências | Limitado | ✅ Ponto forte (`dvc.yaml`, `dvc repro`) |
| Catálogo de modelos com versões e aliases | ✅ Model Registry | ❌ |
| Servir o modelo para quem consome | ✅ Carregamento por alias (`models:/nome@champion`) | ❌ |

Na prática, o DVC cuida dos dados e do pipeline, e o MLflow cuida dos experimentos e dos modelos. A tag `data_version` é a ponte entre os dois.

---

## 4. Versionamento dos experimentos

Além das versões do Model Registry, vale versionar os próprios experimentos. Duas ferramentas ajudam: o nome do experimento e uma tag de versão nos runs.

**Nome do experimento: o objetivo do projeto.** Se o objetivo da modelagem muda no meio do caminho, crie um experimento novo. Assim os runs de objetivos diferentes não se misturam.

> Exemplo: o projeto começou prevendo só as vendas do dia seguinte. Depois surgiu a necessidade de prever as vendas da semana inteira. Isso pede um experimento novo (`previsao-vendas-semanal`), e não mais runs no antigo.

**Tag `version`: o que mudou entre os runs.** Use o versionamento semântico `MAJOR.MINOR.PATCH`, começando em `0.0.0`:

- **MAJOR**: mudanças grandes.
  - Troca do tipo de modelo que muda o pré-processamento (por exemplo, de CatBoost para LSTM).
  - Mudança de target, dentro do mesmo objetivo.
  - Mudanças substanciais no pré-processamento ou na engenharia de features.
- **MINOR**: mudanças menores.
  - Troca do tipo de modelo sem mudar o pré-processamento (por exemplo, de CatBoost para XGBoost).
  - Inclusão ou remoção de features.
  - Ajustes leves no pré-processamento.
- **PATCH**: correções e ajustes.
  - Correção de bug, ajuste pequeno no código, atualização de bibliotecas.
  - Dados novos do mesmo tipo, sem mudar o processamento.

Exemplos:

- De `1.2.3` para `2.0.0`: troca de CatBoost por LSTM, com pré-processamento novo para capturar a ordem temporal.
- De `1.3.1` para `1.4.0`: inclusão de features novas que o cliente passou a coletar.
- De `1.3.2` para `1.3.3`: correção de um bug no pré-processamento.

---

## 5. Boas práticas

- Instale o MLflow dentro do ambiente virtual do projeto e fixe a versão (`mlflow==3.17.0`).
- Use nomes de experimento que descrevam o objetivo. Se o objetivo mudar, crie um experimento novo.
- Defina no início do projeto quais tags todo run deve ter. Um bom ponto de partida: `autor`, `version` e `data_version`.
- Sempre ligue o run à versão dos dados (tag `data_version`). Sem isso, o run não é reproduzível.
- Registre os parâmetros relevantes, inclusive os que não são hiperparâmetros (features usadas, tamanho do treino).
- Mantenha os mesmos nomes de métricas durante todo o projeto e deixe claro de qual conjunto cada uma vem: `train_rmse`, `val_rmse`, `test_rmse`.
- Decida no começo se vai usar o autolog ou o registro explícito, e mantenha a escolha.
- Salve os artefatos que ajudam a entender o resultado (gráficos de resíduos, importância das features).
- Logue os modelos com signature e input example.
- No Model Registry, use aliases para indicar o que está em uso e tags para registrar as decisões (`validation_status`, `motivo`). Quem consome o modelo carrega pelo alias, nunca pelo número da versão.

---

## 6. Guia da interface

A interface do MLflow abre pela aba **PORTAS** (PORTS) do Codespace, no 🌐 da porta **5000**. As etapas abaixo seguem a interface do MLflow 3.17.

### Etapa 1: escolher o modo de trabalho

No canto superior esquerdo há um seletor de modo. Deixe em **Model training**. O outro modo (GenAI) é para aplicações com LLMs, e nele o menu **Model registry** não aparece.

### Etapa 2: a tabela de runs

No menu **Experiments**, clique no experimento (por exemplo, `previsao-vendas`). A lista de runs aparece em forma de tabela, o que facilita comparar modelos.

- Em **Columns**, escolha quais parâmetros, métricas e tags aparecem na tabela.
- Clique no nome de uma coluna para ordenar (por exemplo, pela `test_rmse`, do menor para o maior).
- Na caixa de busca, filtre os runs com expressões como `metrics.test_rmse < 6` ou `tags.autor = 'maria'`.
- Em **Chart view**, as mesmas métricas aparecem em gráficos. **Table view** volta para a tabela.

### Etapa 3: comparar runs

Marque a caixa de dois ou mais runs na tabela e clique em **Compare**. A página de comparação mostra os parâmetros e as métricas lado a lado e gráficos que relacionam parâmetros e métricas. É o jeito mais rápido de ver o que mudou entre dois treinos.

### Etapa 4: a página de um run

Clique no nome de um run para abrir a página dele:

- **Overview**: o **Run ID** (com botão para copiar), os horários, os parâmetros, as métricas, as tags e os modelos logados naquele run. O Run ID é o que você usa no código para carregar ou registrar o modelo (`runs:/<run_id>/model`).
- **Model metrics**: gráficos das métricas registradas.
- **System metrics**: uso de CPU e memória, quando esse registro está ativado.
- **Artifacts**: os arquivos logados com `log_artifact`, como gráficos e relatórios. Imagens e textos podem ser visualizados ali mesmo.

### Etapa 5: registrar um modelo pela interface

Na página do run, use o botão **Register model**. Escolha um modelo registrado que já existe (o MLflow cria a próxima versão) ou crie um novo nome. O resultado é o mesmo do `mlflow.register_model(...)` no código.

### Etapa 6: o Model Registry

No menu **Model registry**, a lista mostra os modelos registrados. Clique em `vendas-diarias` para ver a tabela de versões, com os aliases de cada uma.

- Ao clicar numa versão, a página mostra o **Source run** (link para o run que gerou aquela versão), a descrição, os aliases e as tags.
- Para mover um alias, clique em **Add aliases** (ou **Edit aliases**, se a versão já tem algum), digite o nome (`champion`, `challenger`) e clique em **Save aliases**. Um alias só aponta para uma versão por vez: se ele estava em outra, sai de lá.
- Para registrar uma decisão, use **Add tags** (por exemplo, `validation_status = aprovado`).

> [!NOTE]
> O botão **Promote model** **não** move alias: ele copia a versão para **outro** modelo registrado (por exemplo, de `vendas-diarias-dev` para `vendas-diarias-prod`). Para trocar o modelo em uso, mova o alias.

O vínculo entre as telas fecha o ciclo: a versão do modelo aponta para o run, e o run guarda os parâmetros, as métricas e a tag `data_version`, que aponta para a versão exata dos dados.
