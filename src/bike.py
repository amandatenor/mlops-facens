"""Funções compartilhadas do projeto Bike Sharing.

Usado pelos scripts do pipeline (src/*.py) e pelos notebooks das aulas.
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Variáveis de entrada do modelo (todas disponíveis no momento da previsão).
# "casual" e "registered" ficam de fora: somadas, elas SÃO o alvo (vazamento de dados).
FEATURES = [
    "season", "yr", "mnth", "hr", "holiday", "weekday", "workingday",
    "weathersit", "temp", "atemp", "hum", "windspeed",
]
TARGET = "cnt"  # total de bicicletas alugadas na hora

RAW_PATH = Path("data/raw/bike.csv")
MODEL_NAME = "bike-demand"  # nome do modelo no MLflow Model Registry


def tracking_uri() -> str:
    """Endereço do servidor MLflow (variável de ambiente ou padrão local)."""
    return os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")


def load_raw(path=RAW_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["dteday"])
    return df.sort_values(["dteday", "hr"]).reset_index(drop=True)


def xy(df: pd.DataFrame):
    """Separa entradas (X, como float) e alvo (y)."""
    return df[FEATURES].astype("float64"), df[TARGET]


def time_split(df: pd.DataFrame, test_days: int = 28):
    """Separação temporal: os últimos `test_days` dias viram teste.

    Em séries temporais não se embaralha: o modelo treina no passado
    e é avaliado no futuro, como acontece em produção.
    """
    cutoff = df["dteday"].max() - pd.Timedelta(days=test_days - 1)
    train = df[df["dteday"] < cutoff]
    test = df[df["dteday"] >= cutoff]
    return train, test


def regression_metrics(y_true, y_pred) -> dict:
    return {
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)),
    }
