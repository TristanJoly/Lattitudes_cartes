import pandas as pd
import re
import unicodedata

# -------------------------------
# Fonction pour normaliser les noms de département
# -------------------------------
def normalize_name(name):
    if not isinstance(name, str):
        return ""
    name = ''.join(c for c in unicodedata.normalize('NFD', name)
                   if unicodedata.category(c) != 'Mn')
    name = name.lower()
    name = re.sub(r"[^a-z0-9]", "", name)
    return name

# -------------------------------
# Fichier à lire
# -------------------------------
path = "Enquête Vie quotidienne et santé 2021 - Données départementales - effectifs.xlsx"

xls = pd.ExcelFile(path)
sheet_names = xls.sheet_names[1:]   # toutes sauf la première

rows = []  # stockage des lignes extraites

# -------------------------------
# Lecture de chaque feuille
# -------------------------------
for sheet in sheet_names:

    df = pd.read_excel(path, sheet_name=sheet, header=None, dtype=object)

    # On prend à partir de la ligne 4 (index 3)
    if df.shape[0] <= 3:
        continue

    df_sub = df.iloc[3:, :].copy().reset_index(drop=True)

    # On parcourt chaque ligne
    for _, r in df_sub.iterrows():

        dep_cell = r[1] if 1 in r.index else None  # colonne B
        metric_cell = r[2] if 2 in r.index else None  # colonne C
        value_cell = r[5] if 5 in r.index else None  # colonne F

        # Département vide → ignorer
        if pd.isna(dep_cell) or str(dep_cell).strip() == "":
            continue

        # -------------------------------
        # Extraction du code + nom département
        # -------------------------------
        s = str(dep_cell).strip()
        s = s.replace('\u202f', ' ').replace('\xa0', ' ').strip()

        # Exemple attendu : "01 Ain", "13 - Bouches-du-Rhône", "2A Corse-du-Sud"
        match = re.match(r"^\s*([0-9]{1,3}[A-Za-z]{0,2})\s*[-\u2013\s]*\s*(.*)$", s)

        if match:
            code = match.group(1)
            code = code if not code.isdigit() else code.zfill(2)
            name_raw = match.group(2).strip() if match.group(2).strip() != "" else None
        else:
            # fallback simple : split par espace
            parts = s.split(" ", 1)
            if len(parts) == 2 and re.match(r"^[0-9]", parts[0]):
                code = parts[0].zfill(2)
                name_raw = parts[1].strip()
            else:
                code = None
                name_raw = s

        dep_norm = normalize_name(name_raw) if name_raw else ""

        # -------------------------------
        # Nettoyage valeur colonne F (float)
        # -------------------------------
        value = None
        if not pd.isna(value_cell):
            v = str(value_cell)
            v = v.replace("\u202f", "").replace("\xa0", "")
            v = v.replace(" ", "").replace(",", ".")
            v = v.replace("%", "").replace("(", "").replace(")", "")

            try:
                value = float(v)
            except:
                # extraire un nombre dans un texte
                m2 = re.search(r"[-+]?\d+[\.,]?\d*", v)
                if m2:
                    value = float(m2.group(0).replace(",", "."))
                else:
                    value = None

        metric = str(metric_cell).strip() if not pd.isna(metric_cell) else ""

        # -------------------------------
        # Ajout ligne au dataset final
        # -------------------------------
        rows.append({
            "sheet": sheet,
            "dep_code": code,
            "dep_name_raw": name_raw,
            "dep_norm": dep_norm,
            "metric": metric,
            "value": value
        })

# -------------------------------
# Construction DataFrame final
# -------------------------------
df_extracted = pd.DataFrame(rows)

df_extracted["value"] = pd.to_numeric(df_extracted["value"], errors="coerce")
df_extracted["dep_code"] = df_extracted["dep_code"].astype(str).str.zfill(2)

# -------------------------------
# Export CSV
# -------------------------------
output_file = "extracted_60plus_long.csv"
df_extracted.to_csv(output_file, index=False, encoding="utf-8-sig")

print("Extraction terminée !")
print(f"Lignes extraites : {len(df_extracted)}")
print(f"CSV sauvegardé : {output_file}")
