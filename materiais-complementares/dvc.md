# DVC: material complementar

O DVC (Data Version Control) é uma ferramenta open source que faz duas coisas que o Git sozinho não faz bem:

1. **Versiona dados e modelos**, que costumam ser grandes demais para o Git, mantendo a ligação com cada commit do código.
2. **Organiza o pipeline de ML** em etapas com dependências declaradas, de forma que `dvc repro` refaz só o que mudou.

Este material segue a versão usada na disciplina, o **DVC 3.67.1**. Os exemplos usam um caso diferente do das aulas: a **previsão de vendas diárias de uma rede de lojas**, com os dados em `data/raw/vendas.csv`.

> [!TIP]
> Documentação oficial: <https://dvc.org/doc>
>
> - Versionamento de dados: <https://dvc.org/doc/start/data-management/data-versioning>
> - Pipelines: <https://dvc.org/doc/start/data-management/data-pipelines>
> - Referência do `dvc.yaml`: <https://dvc.org/doc/user-guide/project-structure/dvcyaml-files>

---

## 1. A ideia central

O Git guarda o histórico do código, mas não foi feito para arquivos grandes: cada versão de um CSV de centenas de MB ficaria para sempre no repositório. O DVC resolve isso separando o dado em duas partes:

- **No Git** vai só um arquivo pequeno, o `.dvc`, que funciona como um ponteiro: ele guarda o **md5** (uma "impressão digital") do dado.
- **O dado em si** vai para o **cache** do DVC (a pasta `.dvc/cache`) e, quando você manda, para um **remote** (uma pasta, um bucket S3, um Google Drive...).

```
Git                          Cache local (.dvc/cache)        Remote (../dvc-storage, S3...)
───                          ────────────────────────        ──────────────────────────────
vendas.csv.dvc  ──md5──▶     a7/8ab8c7b6...  (o dado)  ◀──▶  a7/8ab8c7b6...  (cópia)
                              dvc add / dvc checkout          dvc push / dvc pull
```

Como o md5 muda sempre que o conteúdo do arquivo muda, cada commit do Git aponta para uma versão exata do dado. Voltar o código para um commit antigo e rodar `dvc checkout` traz de volta o dado daquela época.

---

## 2. Versionamento de dados

### 2.1 Começando: `dvc init` e o remote

Dentro de um repositório Git:

```bash
dvc init                                   # cria a pasta .dvc/ e os arquivos de configuração
dvc remote add -d local ../dvc-storage     # remote padrão (-d) numa pasta local
git add .dvc .dvcignore
git commit -m "inicia o DVC"
```

O remote é o lugar onde os dados ficam guardados fora da sua máquina. Nas aulas usamos uma pasta local; numa empresa, o remote costuma ser um bucket na nuvem:

```bash
dvc remote add -d storage s3://empresa-projeto/dvc
```

A configuração do remote fica em `.dvc/config`, que vai para o Git. As credenciais da nuvem **não** vão: elas ficam na máquina de cada pessoa (ou em `.dvc/config.local`, que o DVC já deixa fora do Git).

### 2.2 Versionando um arquivo: `dvc add`

```bash
dvc add data/raw/vendas.csv
```

O comando faz três coisas:

1. calcula o md5 do arquivo e copia o dado para o cache;
2. cria o arquivo `data/raw/vendas.csv.dvc`;
3. coloca `vendas.csv` no `data/raw/.gitignore`, para o dado em si não ir para o Git.

O `.dvc` é um YAML curto:

```yaml
outs:
- md5: a78ab8c7b67a354eda7f29f2f9fa3034
  size: 7727
  hash: md5
  path: vendas.csv
```

Quem vai para o Git são o `.dvc` e o `.gitignore`:

```bash
git add data/raw/vendas.csv.dvc data/raw/.gitignore
git commit -m "dados v1"
git tag dados-v1
```

> [!WARNING]
> Não rode `git add -A` (ou `git add .`) antes do `dvc add`: o Git passa a rastrear o dado e o `dvc add` falha com *output is already tracked by SCM*. Se isso acontecer, tire o arquivo do Git com `git rm --cached data/raw/vendas.csv` e rode o `dvc add` de novo.

A tag no Git é opcional, mas ajuda muito: `dados-v1` fica sendo um nome legível para "o commit em que os dados eram a versão 1".

### 2.3 Enviando e baixando: `dvc push` e `dvc pull`

```bash
dvc push      # envia do cache para o remote tudo que os arquivos .dvc e o dvc.lock referenciam
dvc pull      # baixa do remote para o cache e coloca os arquivos no lugar
```

O fluxo de quem chega no projeto é sempre o mesmo:

```bash
git clone <url-do-repositorio>
cd <repositorio>
dvc pull
```

O Git traz o código e os ponteiros; o `dvc pull` traz os dados que esses ponteiros indicam. Sem o `dvc push` de quem versionou, o `dvc pull` dos outros não encontra nada.

### 2.4 Uma nova versão dos dados

Chegaram dados novos: o `vendas.csv` foi substituído por uma versão com mais dias.

```bash
dvc status                     # mostra que data/raw/vendas.csv mudou
dvc add data/raw/vendas.csv    # novo md5, nova cópia no cache
git add data/raw/vendas.csv.dvc
git commit -m "dados v2"
git tag dados-v2
dvc push
```

O cache passa a ter as duas versões, e o Git tem dois commits, cada um apontando para uma delas.

### 2.5 Viagem no tempo: `git checkout` + `dvc checkout`

Para voltar o projeto inteiro (código e dados) para uma versão anterior:

```bash
git checkout dados-v1     # volta o código e os ponteiros (.dvc, dvc.lock)
dvc checkout              # troca os dados no disco pelos que os ponteiros indicam
```

E para voltar ao presente:

```bash
git checkout main
dvc checkout
```

Se você só quer o dado antigo, sem mexer no resto do código:

```bash
git checkout dados-v1 -- data/raw/vendas.csv.dvc
dvc checkout data/raw/vendas.csv.dvc
```

> [!NOTE]
> Os dois comandos andam juntos. O `git checkout` sozinho troca só o ponteiro: o arquivo no disco continua o da versão anterior até o `dvc checkout`. Se o `dvc checkout` avisar que algum arquivo não está no cache, ele ainda não foi baixado (`dvc pull`) ou nunca foi gerado naquele commit (`dvc repro`).

### 2.6 Gravando mudanças feitas fora do DVC: `dvc commit`

O DVC acompanha os arquivos de cada estágio do pipeline (seção 3). Quando um arquivo versionado muda **por fora** do `dvc repro` e do `dvc add`, o DVC percebe a diferença, mas não a grava sozinho. O `dvc commit` grava o estado atual no cache e atualiza o `dvc.lock` (ou o `.dvc`), sem rodar o código de novo.

Casos em que ele é útil:

- você adicionou arquivos numa pasta que é só dependência de um estágio (por exemplo, `data/raw/`) e quer registrar o novo estado;
- você alterou manualmente uma saída de um estágio e quer que essa versão passe a valer.

```bash
dvc status     # mostra o que está diferente do registrado
dvc commit     # grava o estado atual sem reexecutar
```

Use com consciência: o `dvc commit` diz ao DVC "pode confiar neste arquivo como está", mesmo que ele não tenha sido produzido pelo pipeline.

### 2.7 Limpando o cache: `dvc gc`

O DVC nunca substitui uma versão antiga no cache: cada `dvc add` e cada `dvc repro` que muda um arquivo cria uma cópia nova. Com o tempo, o cache cresce. O `dvc gc` (*garbage collector*) apaga do cache o que não é mais referenciado. Ele exige que você diga **o que deve ser mantido**, e a escolha importa:

| Opção | Mantém os dados de... | Cuidado |
|---|---|---|
| `-w`, `--workspace` | só o estado atual do projeto | Apaga as versões antigas. Um `git checkout dados-v1` depois disso não acha os dados. |
| `-a`, `--all-branches` | o último commit de cada branch | **Também apaga** os dados de tags e commits antigos (como `dados-v1`). |
| `-T`, `--all-tags` | todas as tags | Combine com `-a` para manter branches e tags. |
| `-A`, `--all-commits` | todos os commits do histórico | A opção mais segura: só apaga o que nenhum commit referencia. |
| `-c`, `--cloud` | (combinada com as anteriores) | Apaga também do **remote**. Aí não tem volta. |

```bash
dvc gc -A        # mais seguro: mantém tudo que algum commit usa
```

> [!CAUTION]
> Antes de usar `-c`, confirme que ninguém do time precisa das versões que serão apagadas. Sem `-c`, o pior caso é ter que rodar `dvc pull` de novo; com `-c`, o dado some de vez.

---

## 3. Pipelines

### 3.1 Por que um pipeline

Um projeto de ML costuma ter várias etapas: limpar os dados, criar features, treinar, avaliar. Rodar cada script à mão tem dois problemas: é fácil esquecer uma etapa depois de mudar algo, e é desperdício rodar de novo uma etapa cujas entradas não mudaram.

No pipeline do DVC, cada etapa (**estágio**) declara o comando que roda, do que depende e o que produz. A partir disso o DVC monta o grafo de dependências e, no `dvc repro`, executa **só os estágios afetados por alguma mudança**.

O pipeline usa três arquivos:

| Arquivo | Quem escreve | O que guarda | Vai para o Git? |
|---|---|---|---|
| `params.yaml` | você | os valores que você experimenta (hiperparâmetros, limites, janelas) | sim |
| `dvc.yaml` | você | os estágios: comando, dependências, parâmetros e saídas | sim |
| `dvc.lock` | o DVC, a cada `dvc repro` | o md5 de cada dependência e saída e os valores dos parâmetros usados | sim |

### 3.2 O `params.yaml`

```yaml
clean:
  max_vendas: 500        # descarta dias com vendas acima disso (erro de digitação)

features:
  janela_media: 7        # dias da média móvel

train:
  n_estimators: 100
  max_depth: 6
  test_size: 0.2
```

Os scripts leem os valores daqui, em vez de tê-los fixos no código:

```python
import yaml

p = yaml.safe_load(open("params.yaml"))["train"]
model = RandomForestRegressor(n_estimators=p["n_estimators"], max_depth=p["max_depth"], random_state=42)
```

Assim, mudar um hiperparâmetro é mudar o `params.yaml`, e o DVC sabe exatamente qual estágio precisa rodar de novo.

### 3.3 O `dvc.yaml`

O pipeline de vendas tem três estágios: `clean` → `features` → `train`.

```yaml
stages:
  clean:
    cmd: python src/clean.py
    deps:
      - src/clean.py
      - data/raw/vendas.csv
    params:
      - clean.max_vendas
    outs:
      - data/interim/vendas_limpas.csv

  features:
    cmd: python src/features.py
    deps:
      - src/features.py
      - data/interim/vendas_limpas.csv
    params:
      - features
    outs:
      - data/processed/features.csv

  train:
    cmd: python src/train.py
    deps:
      - src/train.py
      - data/processed/features.csv
    params:
      - train
    outs:
      - models/model.joblib
    metrics:
      - metrics.json:
          cache: false
```

As chaves de cada estágio:

- **`cmd`**: o comando que o estágio executa.
- **`deps`**: os arquivos de que o estágio depende. Inclua sempre o **próprio script**: se o código muda, o estágio precisa rodar de novo.
- **`params`**: os parâmetros do `params.yaml` que o estágio usa. Pode ser uma chave específica (`clean.max_vendas`) ou uma seção inteira (`train`).
- **`outs`**: os arquivos que o estágio produz. O DVC os coloca no cache e no `.gitignore` automaticamente, então eles não vão para o Git.
- **`metrics`**: arquivos de métricas (JSON ou YAML). O `cache: false` mantém o arquivo fora do cache do DVC, e aí ele vai para o Git: assim o histórico de métricas fica visível em cada commit.

O DVC também tem **`plots`**, para arquivos de dados que viram gráficos (`dvc plots show`). A referência do `dvc.yaml` (link no topo) mostra as opções.

**O encadeamento sai das próprias dependências.** A saída de `clean` (`vendas_limpas.csv`) é dependência de `features`, então `features` roda depois de `clean`. Você não declara a ordem; o DVC a deduz.

> [!TIP]
> Os scripts devem gravar exatamente nos caminhos declarados em `outs`, e o DVC apaga essas saídas antes de rodar o estágio. Se a pasta de saída pode não existir, crie-a no script (`os.makedirs("data/interim", exist_ok=True)`).

#### Usando valores do `params.yaml` dentro do `dvc.yaml`

O `dvc.yaml` aceita referências `${...}` para valores do `params.yaml`. Isso evita repetir caminhos:

```yaml
# params.yaml
clean:
  input_path: data/raw/vendas.csv
  output_path: data/interim/vendas_limpas.csv
```

```yaml
# dvc.yaml
stages:
  clean:
    cmd: python src/clean.py
    deps:
      - src/clean.py
      - ${clean.input_path}
    outs:
      - ${clean.output_path}
```

### 3.4 Rodando: `dvc repro`

```bash
dvc repro
```

Na primeira vez, o DVC roda os três estágios em ordem e grava o `dvc.lock`, com o md5 de cada dependência e de cada saída e os valores dos parâmetros usados. Um trecho:

```yaml
stages:
  clean:
    cmd: python src/clean.py
    deps:
    - path: data/raw/vendas.csv
      hash: md5
      md5: a78ab8c7b67a354eda7f29f2f9fa3034
      size: 7727
    params:
      params.yaml:
        clean.max_vendas: 500
    outs:
    - path: data/interim/vendas_limpas.csv
      ...
```

Nas vezes seguintes, o DVC compara o estado atual com o `dvc.lock`:

- **Nada mudou**: nenhum estágio roda (*Data and pipelines are up to date*).
- **Mudou o `max_depth` no `params.yaml`**: só o `train` roda. `clean` e `features` são pulados (*didn't change, skipping*).
- **Chegou uma nova versão de `vendas.csv`**: os três estágios rodam, porque a mudança no começo se propaga pela cadeia.

Comandos que ajudam a entender o pipeline:

```bash
dvc dag        # desenha o grafo de estágios no terminal
dvc status     # mostra o que mudou desde o último repro (e por quê)
```

### 3.5 Depois do `dvc repro`: o que vai para o Git

O `dvc repro` não faz commit. Para registrar o resultado:

```bash
git add dvc.lock params.yaml metrics.json      # e os .gitignore que o DVC criou
git commit -m "treino com max_depth 10"
dvc push                                       # envia as saídas (modelo, dados processados) ao remote
```

Com isso, o commit guarda tudo o que é preciso para reproduzir aquele resultado: o código, os parâmetros e, pelo `dvc.lock`, a versão exata de cada dado e de cada saída.

### 3.6 Comparando versões: `dvc params` e `dvc metrics`

```bash
dvc params diff     # parâmetros do workspace × último commit
dvc metrics show    # métricas atuais
dvc metrics diff    # métricas do workspace × último commit
```

Exemplo de saída depois de mudar o `max_depth` e rodar `dvc repro`:

```
Path         Param            HEAD    workspace
params.yaml  train.max_depth  6       10

Path          Metric    HEAD    workspace    Change
metrics.json  rmse      5.63    5.68         0.05
```

Os dois comandos também aceitam commits ou tags, para comparar duas versões quaisquer: `dvc metrics diff <commit-a> <commit-b>`.

---

## 4. Comandos mais usados

| Comando | O que faz |
|---|---|
| `dvc init` | Inicia o DVC no repositório |
| `dvc remote add -d <nome> <caminho>` | Define o remote padrão |
| `dvc add <arquivo>` | Versiona um arquivo ou pasta (cria o `.dvc`) |
| `dvc status` | Mostra o que mudou em relação ao registrado |
| `dvc push` / `dvc pull` | Envia ao remote / baixa do remote |
| `dvc checkout` | Coloca no disco os dados indicados pelos ponteiros atuais |
| `dvc repro` | Executa os estágios afetados por mudanças |
| `dvc dag` | Mostra o grafo do pipeline |
| `dvc params diff` | Compara parâmetros entre versões |
| `dvc metrics show` / `dvc metrics diff` | Mostra / compara métricas |
| `dvc commit` | Grava no cache mudanças feitas fora do DVC |
| `dvc gc -A` | Limpa do cache o que nenhum commit usa |

---

## 5. Boas práticas

- Fixe a versão do DVC no projeto (`dvc==3.67.1`), assim como a do MLflow.
- Dado nunca vai para o Git. No Git vão os `.dvc`, o `dvc.yaml`, o `dvc.lock` e o `params.yaml`.
- Depois de cada `dvc add` ou `dvc repro` que valha a pena guardar: `git commit` e `dvc push`. Commit sem push deixa o time sem os dados.
- Use tags no Git para marcar versões importantes dos dados (`dados-v1`, `dados-v2`).
- Coloque nos `deps` de cada estágio o próprio script e tudo o que ele lê. Uma dependência esquecida é um estágio que deixa de rodar quando deveria.
- Tudo o que você experimenta vai para o `params.yaml`, e não fixo no código.
- Registre a versão dos dados (o md5 do `.dvc`) nos runs do MLflow. É isso que liga um modelo aos dados com que foi treinado.
- No `dvc gc`, prefira `-A`. Nunca use `-c` sem combinar com o time.

---

## 6. Para ir além

Os recursos abaixo aparecem em projetos maiores. Não são necessários nas tarefas, mas resolvem problemas comuns quando o pipeline cresce.

### 6.1 `foreach`: o mesmo estágio para vários arquivos

Suponha que as vendas chegam em um arquivo por loja: `data/raw/sp.csv`, `data/raw/rj.csv`, `data/raw/mg.csv`. Um estágio que lê a pasta inteira funciona, mas tem dois problemas:

- se só o arquivo de uma loja mudar, o estágio roda de novo para todas;
- para o DVC, a pasta inteira é uma dependência só, e ele não sabe qual arquivo gerou qual saída.

O `foreach` cria um **subestágio por item** de uma lista:

```yaml
# params.yaml
lojas:
  - sp
  - rj
  - mg
```

```yaml
# dvc.yaml
stages:
  limpar:
    foreach: ${lojas}
    do:
      cmd: python src/limpar.py --loja ${item}
      deps:
        - src/limpar.py
        - data/raw/${item}.csv
      outs:
        - data/interim/${item}.csv
```

O DVC transforma isso em três estágios independentes, `limpar@sp`, `limpar@rj` e `limpar@mg` (`dvc stage list` mostra todos). Se só `rj.csv` mudar, só `limpar@rj` roda.

O `foreach` também itera sobre um dicionário. Nesse caso, `${key}` é o nome de cada entrada e `${item.<campo>}` acessa os campos:

```yaml
stages:
  treinar:
    foreach:
      rapido:
        n_estimators: 50
        max_depth: 4
      completo:
        n_estimators: 300
        max_depth: 10
    do:
      cmd: python src/train.py --nome ${key} --n_estimators ${item.n_estimators} --max_depth ${item.max_depth}
      deps:
        - src/train.py
        - data/processed/features.csv
      outs:
        - models/${key}.joblib
```

Os subestágios ficam `treinar@rapido` e `treinar@completo`.

### 6.2 `argparse`: scripts que recebem argumentos

Com o `foreach`, o mesmo script roda várias vezes com valores diferentes, então ele precisa receber esses valores pela linha de comando. O jeito mais comum em Python é o módulo `argparse`:

```python
import argparse

parser = argparse.ArgumentParser(description="Limpa os dados de vendas de uma loja.")
parser.add_argument(
    "--loja",
    required=True,      # argumento obrigatório
    type=str,
    help="Sigla da loja, igual ao nome do arquivo em data/raw (ex.: 'sp').",
)
args = parser.parse_args()

loja = args.loja
```

Rodando `python src/limpar.py --help`, o `argparse` mostra a descrição e os argumentos. Documentação: <https://docs.python.org/3/library/argparse.html>

### 6.3 Arquivos novos entrando sozinhos no `foreach`

Com a lista no `params.yaml`, cada loja nova precisa ser adicionada à mão. Com 3 lojas tudo bem; com 100, não. Dá para automatizar com um estágio que lista os arquivos da pasta e grava a lista num YAML que o próprio `dvc.yaml` lê:

```python
# src/listar_lojas.py
from pathlib import Path
import yaml

p = yaml.safe_load(open("params.yaml"))["listar_lojas"]
lojas = sorted(f.stem for f in Path(p["input_path"]).glob("*.csv"))

with open(p["output_path"], "w") as f:
    yaml.safe_dump({"lojas": lojas}, f)
```

```yaml
# params.yaml
listar_lojas:
  input_path: data/raw
  output_path: lojas.yaml
```

```yaml
# dvc.yaml
vars:
  - lojas.yaml           # o dvc.yaml lê a lista gerada pelo estágio abaixo

stages:
  listar_lojas:
    cmd: python src/listar_lojas.py
    deps:
      - src/listar_lojas.py
      - ${listar_lojas.input_path}
    outs:
      - ${listar_lojas.output_path}:
          cache: false   # fica fora do cache e vai para o Git
    always_changed: true # roda sempre, para varrer a pasta

  limpar:
    foreach: ${lojas}
    do:
      cmd: python src/limpar.py --loja ${item}
      deps:
        - src/limpar.py
        - data/raw/${item}.csv
      outs:
        - data/interim/${item}.csv
```

Dois cuidados com essa estrutura:

- **O `lojas.yaml` precisa existir antes do primeiro `dvc repro`.** O DVC lê o `dvc.yaml` (e o `vars`) antes de rodar qualquer estágio. Sem o arquivo, ele não consegue montar o pipeline. Faça o commit de uma versão inicial do `lojas.yaml` no Git.
- **Uma loja nova só é processada no `dvc repro` seguinte.** O DVC monta a lista do `foreach` no começo da execução, com o `lojas.yaml` que existia naquele momento. Na primeira execução depois de chegar `mg.csv`, o `listar_lojas` atualiza o YAML; o `limpar@mg` só aparece na próxima.

### 6.4 Opções de estágio

Ficam no mesmo nível de `cmd`, `deps` e `outs`:

- **`frozen: true`** (padrão `false`): congela o estágio. O `dvc repro` não o executa, mesmo que as dependências mudem. Útil para testar o pipeline por partes ou para fixar uma etapa cara que não vai mudar. Os comandos `dvc freeze <estágio>` e `dvc unfreeze <estágio>` gravam essa opção por você, mas só em estágios sem `${...}` e sem `foreach`; nesses, escreva `frozen: true` direto no `dvc.yaml`.
- **`always_changed: true`** (padrão `false`): o oposto. O estágio é sempre considerado modificado e roda em todo `dvc repro`, como o `listar_lojas` acima.

### 6.5 Opções de saída

Ficam em cada saída, escrita como um dicionário (`- caminho:` seguido das opções):

- **`cache: false`** (padrão `true`): a saída não vai para o cache do DVC. Útil para arquivos pequenos que devem ir para o Git (métricas, listas geradas) ou para arquivos temporários que são sempre regerados.
- **`persist: true`** (padrão `false`): o DVC não apaga a saída antes de rodar o estágio. Útil quando o script atualiza um arquivo de forma incremental, em vez de recriá-lo do zero.

```yaml
outs:
  - data/interim/historico.parquet:
      persist: true
```
