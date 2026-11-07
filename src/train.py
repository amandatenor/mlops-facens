"""Estágio `train`: treina o modelo, registra o experimento no MLflow e
cria uma nova versão no Model Registry.

A promoção (alias @champion) NÃO é automática: é uma decisão de governança.
"""
import json
import subprocess
from pathlib import Path

import joblib
import mlflow
import pandas as pd
import yaml
from mlflow.models import infer_signature
from sklearn.ensemble import HistGradientBoostingRegressor

from bike import MODEL_NAME, tracking_uri, xy

params = yaml.safe_load(open("params.yaml"))
hp = params["train"]


def data_version() -> str:
    """Hash do dado bruto, lido do arquivo .dvc (liga o modelo à versão dos dados)."""
    dvc_file = Path("data/raw/bike.csv.dvc")
    if not dvc_file.exists():
        return "nao-versionado"
    return yaml.safe_load(dvc_file.read_text())["outs"][0]["md5"]


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return "desconhecido"


train = pd.read_csv("data/split/train.csv", parse_dates=["dteday"])
X, y = xy(train)

model = HistGradientBoostingRegressor(
    learning_rate=hp["learning_rate"],
    max_iter=hp["max_iter"],
    max_leaf_nodes=hp["max_leaf_nodes"],
    random_state=hp["random_state"],
)

mlflow.set_tracking_uri(tracking_uri())
mlflow.set_experiment(params["mlflow"]["experiment"])

with mlflow.start_run() as run:
    mlflow.log_params(hp)
    mlflow.set_tags({
        "data_version": data_version(),
        "git_commit": git_commit(),
        "train_rows": len(train),
        "train_until": f"{train['dteday'].max():%Y-%m-%d}",
    })

    model.fit(X, y)

    info = mlflow.sklearn.log_model(
        model,
        name="model",
        signature=infer_signature(X, model.predict(X)),
        input_example=X.head(3),
        registered_model_name=MODEL_NAME,
        # Formato tradicional (pickle). O padrão novo do MLflow (skops) é mais seguro,
        # mas exige listar "tipos confiáveis" para modelos de árvore (tema da Aula 4).
        serialization_format="cloudpickle",
    )
    mlflow.MlflowClient().update_model_version(
        MODEL_NAME, info.registered_model_version, description="Treino do pipeline (dvc repro)")

Path("models").mkdir(exist_ok=True)
joblib.dump(model, "models/model.joblib")
json.dump(
    {"run_id": run.info.run_id, "model_name": MODEL_NAME,
     "model_version": info.registered_model_version},
    open("models/run.json", "w"), indent=2,
)
print(f"run_id={run.info.run_id} | {MODEL_NAME} versão {info.registered_model_version}")
