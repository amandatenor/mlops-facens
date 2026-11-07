"""Estágio `split`: separa treino e teste no tempo (os últimos N dias viram teste)."""
from pathlib import Path

import pandas as pd
import yaml

from bike import time_split

params = yaml.safe_load(open("params.yaml"))["split"]

df = pd.read_csv("data/prepared/bike.csv", parse_dates=["dteday"])
train, test = time_split(df, test_days=params["test_days"])

out = Path("data/split")
out.mkdir(parents=True, exist_ok=True)
train.to_csv(out / "train.csv", index=False, date_format="%Y-%m-%d")
test.to_csv(out / "test.csv", index=False, date_format="%Y-%m-%d")

print(f"split: treino {len(train):,} linhas | teste {len(test):,} linhas "
      f"({test['dteday'].min():%Y-%m-%d} a {test['dteday'].max():%Y-%m-%d})")
