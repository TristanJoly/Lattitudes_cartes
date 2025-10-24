import pandas as pd

# === 1. Chargement du fichier CSV ===
file_path = "DS_ESTIMATION_POPULATION_data.csv"
df = pd.read_csv(file_path, sep=';', quotechar='"')

# === 2. Filtrage des départements métropolitains ===
df = df[df["GEO_OBJECT"] == "DEP"]
df = df[df["GEO"].astype(str).str.match(r"^0?[1-9][0-9]?$")]

# === 3. On garde uniquement F et M ===
df = df[df["SEX"].isin(["F", "M"])]

# === 4. On crée une catégorie d'âge simplifiée ===
def regroupe_age(age):
    if age in ["Y60T64", "Y65T69", "Y70T74", "Y70T75"]:
        return "Y60T74"
    elif age in ["Y75T79", "Y80T84", "Y85T89", "Y90T94", "Y75T94", "Y_GE95"]:
        return "Y75Tplus"
    else:
        return None

df["AGE_GROUP"] = df["AGE"].apply(regroupe_age)

# On retire les lignes sans catégorie pertinente
df = df[df["AGE_GROUP"].notna()]

# === 5. On garde uniquement la date la plus récente ===
latest_year = df["TIME_PERIOD"].max()
df = df[df["TIME_PERIOD"] == latest_year]

# === 6. Agrégation (somme des populations par département, sexe, groupe d'âge) ===
df_grouped = (
    df.groupby(["GEO", "SEX", "AGE_GROUP"])["OBS_VALUE"]
    .sum()
    .reset_index()
)

# === 7. Pivot pour avoir colonnes séparées par sexe et âge ===
df_result = df_grouped.pivot_table(
    index="GEO",
    columns=["SEX", "AGE_GROUP"],
    values="OBS_VALUE"
).reset_index()

# === 8. Aplatir les noms de colonnes ===
df_result.columns = [
    f"{sex}_{age}" if isinstance(sex, str) else sex
    for sex, age in df_result.columns
]

# === 9. Sauvegarde ===
output_file = "population_departements_60_75_plus.xlsx"
df_result.to_excel(output_file, index=False)

print(f"✅ Fichier généré : {output_file}")
