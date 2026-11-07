"""Estágio `evaluate`: mede o modelo no teste, grava metrics.json (DVC)
e anexa as métricas ao mesmo run do MLflow criado no treino."""
import json

import joblib
import mlflow
import pandas as pd
from mlflow import MlflowClient

from bike import regression_metrics, tracking_uri, xy

test = pd.read_csv("data/split/test.csv")
X_test, y_test = xy(test)
model = joblib.load("models/model.joblib")
metrics = regression_metrics(y_test, model.predict(X_test))

json.dump(metrics, open("metrics.json", "w"), indent=2)

run_id = json.load(open("models/run.json"))["run_id"]
mlflow.set_tracking_uri(tracking_uri())
client = MlflowClient()
for name, value in metrics.items():
    client.log_metric(run_id, f"test_{name}", value)

print(json.dumps(metrics, indent=2))
