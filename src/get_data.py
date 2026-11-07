"""Baixa o dataset Bike Sharing (UCI) e grava os dados "disponíveis até" uma data.

Simula a chegada de dados novos ao longo do tempo:

    python src/get_data.py --until 2011-12-31   # dados v1 (2011)
    python src/get_data.py --until 2012-06-30   # dados v2 (+ 1º semestre de 2012)
    python src/get_data.py --until 2012-12-31   # dados v3 (base completa)

Fonte: Fanaee-T, H. & Gama, J. (2013). Bike Sharing Dataset. UCI Machine
Learning Repository. Licença CC BY 4.0.
"""
import argparse
import io
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

UCI_ZIP = "https://archive.ics.uci.edu/static/public/275/bike+sharing+dataset.zip"
MIRROR_CSV = (
    "https://raw.githubusercontent.com/udacity/deep-learning-v2-pytorch/"
    "master/project-bikesharing/Bike-Sharing-Dataset/hour.csv"
)
CACHE = Path.home() / ".cache" / "bike-sharing" / "hour.csv"
OUT = Path("data/raw/bike.csv")


def download() -> Path:
    """Baixa o hour.csv uma única vez e guarda em cache (fora do repositório)."""
    if CACHE.exists():
        return CACHE
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    try:
        print(f"Baixando de {UCI_ZIP} ...")
        with urllib.request.urlopen(UCI_ZIP, timeout=60) as resp:
            with zipfile.ZipFile(io.BytesIO(resp.read())) as zf:
                CACHE.write_bytes(zf.read("hour.csv"))
    except Exception as err:  # UCI fora do ar? usa o espelho no GitHub
        print(f"UCI indisponível ({err}). Usando espelho: {MIRROR_CSV}")
        with urllib.request.urlopen(MIRROR_CSV, timeout=60) as resp:
            CACHE.write_bytes(resp.read())
    return CACHE


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--until", required=True, help="última data incluída (AAAA-MM-DD)")
    args = parser.parse_args()

    df = pd.read_csv(download(), parse_dates=["dteday"])
    df = df[df["dteday"] <= args.until]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False, date_format="%Y-%m-%d")
    print(f"{OUT}: {len(df):,} linhas | {df['dteday'].min():%Y-%m-%d} a {df['dteday'].max():%Y-%m-%d}")


if __name__ == "__main__":
    main()
