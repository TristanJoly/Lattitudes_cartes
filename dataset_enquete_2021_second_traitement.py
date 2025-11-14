import pandas as pd

df = pd.read_csv("extracted_60plus_long.csv")

# --- Renommage propre ---
df = df.rename(columns={
    "sheet": "source",
    "dep_code": "code_departement",
    "dep_name_raw": "departement",
    "metric": "variable",
    "value": "valeur"
})

# --- Création d'un identifiant unique pour chaque variable ---
df["var_id"] = df["source"] + "_" + df["variable"]

# --- Pivot long -> wide ---
df_wide = df.pivot_table(
    index=["code_departement", "departement", "dep_norm"],
    columns="var_id",
    values="valeur",
    aggfunc="first"
).reset_index()

# Les colonnes pivotées deviennent des colonnes classiques
df_wide.columns = [str(c) for c in df_wide.columns]
print(df_wide.columns)
