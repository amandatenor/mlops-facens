"""Estágio `plot`: gráfico real × previsto no período de teste.

Grava reports/previsto_vs_real.png (o DVC acompanha como `plots`) e anexa a mesma
figura ao run do MLflow criado no treino.
"""
import json
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")  # gera a imagem sem abrir janela
import matplotlib.pyplot as plt  # noqa: E402
import mlflow  # noqa: E402
import pandas as pd  # noqa: E402
from mlflow import MlflowClient  # noqa: E402

from bike import tracking_uri, xy  # noqa: E402

test = pd.read_csv("data/split/test.csv", parse_dates=["dteday"])
X_test, y_test = xy(test)
model = joblib.load("models/model.joblib")
quando = test["dteday"] + pd.to_timedelta(test["hr"], unit="h")

fig, ax = plt.subplots(figsize=(11, 3.5))
ax.plot(quando, y_test, label="real", lw=1)
ax.plot(quando, model.predict(X_test), label="previsto", lw=1)
ax.set_title(f"Real × previsto no teste ({quando.min():%d/%m/%Y} a {quando.max():%d/%m/%Y})")
ax.set_ylabel("aluguéis por hora")
ax.legend()
fig.tight_layout()

out = Path("reports/previsto_vs_real.png")
out.parent.mkdir(exist_ok=True)
fig.savefig(out, dpi=110)

run_id = json.load(open("models/run.json"))["run_id"]
mlflow.set_tracking_uri(tracking_uri())
MlflowClient().log_artifact(run_id, str(out))
print(f"plot: {out} salvo e anexado ao run {run_id}")
