"""Estágio `prepare`: limpa o dado bruto e deixa só as colunas que o modelo pode usar."""
from pathlib import Path

from bike import FEATURES, TARGET, load_raw

df = load_raw()  # já ordenado por data e hora
antes = len(df)

df = df.drop_duplicates(subset=["dteday", "hr"])   # uma linha por hora
df = df.dropna(subset=[*FEATURES, TARGET])          # sem valores faltando

# Saem `instant` (só um contador) e `casual`/`registered` (somadas, são o alvo: vazamento)
cols = ["dteday", *FEATURES, TARGET]

out = Path("data/prepared")
out.mkdir(parents=True, exist_ok=True)
df[cols].to_csv(out / "bike.csv", index=False, date_format="%Y-%m-%d")

print(f"prepare: {len(df):,} linhas ({antes - len(df)} removidas) e {len(cols)} colunas "
      f"-> {out / 'bike.csv'}")
