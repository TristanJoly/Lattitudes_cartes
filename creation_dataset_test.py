
import streamlit as st
import json
from pathlib import Path
import folium

import branca.colormap as cm
import re
import numpy as np
import time
import unicodedata
import pandas as pd
fichier_excel = "TCRD_021.xlsx"
# --- Lecture du fichier DEP ---
cols = "A,B,C,D,H,I"
df_dep = pd.read_excel(fichier_excel, sheet_name="DEP", usecols=cols)

df_dep.columns = [
    "Code département",
    "Département",
    "Population",
    "Part des femmes (en %)",
    "Part des 60 ans ou plus (en %)",
    "dont part des 75 ans ou plus (en %)"
]






metropole_codes = [
    "01","02","03","04","05","06","07","08","09","10","11","12","13","14","15","16","17","18","19","21",
    "22","23","24","25","26","27","28","29","2A","2B","30","31","32","33","34","35","36","37","38","39",
    "40","41","42","43","44","45","46","47","48","49","50","51","52","53","54","55","56","57","58","59",
    "60","61","62","63","64","65","66","67","68","69","70","71","72","73","74","75","76","77","78","79",
    "80","81","82","83","84","85","86","87","88","89","90","91","92","93","94","95"
]


# --- fonction pour nettoyer les noms de département ---
def normalize_name(name):
    if not isinstance(name, str):
        return ""
    
    name = ''.join(
        c for c in unicodedata.normalize('NFD', name)
        if unicodedata.category(c) != 'Mn'
    )
    
    name = name.lower()
    name = re.sub(r"[^a-z0-9]", "", name)
    return name


code_to_nom = {
    "01": "Ain", "02": "Aisne", "03": "Allier", "04": "Alpes-de-Haute-Provence",
    "05": "Hautes-Alpes", "06": "Alpes-Maritimes", "07": "Ardèche", "08": "Ardennes",
    "09": "Ariège", "10": "Aube", "11": "Aude", "12": "Aveyron", "13": "Bouches-du-Rhône",
    "14": "Calvados", "15": "Cantal", "16": "Charente", "17": "Charente-Maritime",
    "18": "Cher", "19": "Corrèze", "21": "Côte-d'Or", "22": "Côtes-d'Armor",
    "23": "Creuse", "24": "Dordogne", "25": "Doubs", "26": "Drôme", "27": "Eure",
    "28": "Eure-et-Loir", "29": "Finistère", "2A": "Corse-du-Sud", "2B": "Haute-Corse",
    "30": "Gard", "31": "Haute-Garonne", "32": "Gers", "33": "Gironde", "34": "Hérault",
    "35": "Ille-et-Vilaine", "36": "Indre", "37": "Indre-et-Loire", "38": "Isère",
    "39": "Jura", "40": "Landes", "41": "Loir-et-Cher", "42": "Loire", "43": "Haute-Loire",
    "44": "Loire-Atlantique", "45": "Loiret", "46": "Lot", "47": "Lot-et-Garonne",
    "48": "Lozère", "49": "Maine-et-Loire", "50": "Manche", "51": "Marne",
    "52": "Haute-Marne", "53": "Mayenne", "54": "Meurthe-et-Moselle", "55": "Meuse",
    "56": "Morbihan", "57": "Moselle", "58": "Nièvre", "59": "Nord", "60": "Oise",
    "61": "Orne", "62": "Pas-de-Calais", "63": "Puy-de-Dôme", "64": "Pyrénées-Atlantiques",
    "65": "Hautes-Pyrénées", "66": "Pyrénées-Orientales", "67": "Bas-Rhin",
    "68": "Haut-Rhin", "69": "Rhône", "70": "Haute-Saône", "71": "Saône-et-Loire",
    "72": "Sarthe", "73": "Savoie", "74": "Haute-Savoie", "75": "Paris",
    "76": "Seine-Maritime", "77": "Seine-et-Marne", "78": "Yvelines",
    "79": "Deux-Sèvres", "80": "Somme", "81": "Tarn", "82": "Tarn-et-Garonne",
    "83": "Var", "84": "Vaucluse", "85": "Vendée", "86": "Vienne", "87": "Haute-Vienne",
    "88": "Vosges", "89": "Yonne", "90": "Territoire de Belfort", "91": "Essonne",
    "92": "Hauts-de-Seine", "93": "Seine-Saint-Denis", "94": "Val-de-Marne",
    "95": "Val-d'Oise"
}

nom_to_code = {
    "Ain": "01", "Aisne": "02", "Allier": "03", "Alpes-de-Haute-Provence": "04",
    "Hautes-Alpes": "05", "Alpes-Maritimes": "06", "Ardèche": "07", "Ardennes": "08",
    "Ariège": "09", "Aube": "10", "Aude": "11", "Aveyron": "12", "Bouches-du-Rhône": "13",
    "Calvados": "14", "Cantal": "15", "Charente": "16", "Charente-Maritime": "17",
    "Cher": "18", "Corrèze": "19", "Côte-d'Or": "21", "Côtes-d'Armor": "22",
    "Creuse": "23", "Dordogne": "24", "Doubs": "25", "Drôme": "26", "Eure": "27",
    "Eure-et-Loir": "28", "Finistère": "29", "Corse-du-Sud": "2A", "Haute-Corse": "2B",
    "Gard": "30", "Haute-Garonne": "31", "Gers": "32", "Gironde": "33", "Hérault": "34",
    "Ille-et-Vilaine": "35", "Indre": "36", "Indre-et-Loire": "37", "Isère": "38",
    "Jura": "39", "Landes": "40", "Loir-et-Cher": "41", "Loire": "42", "Haute-Loire": "43",
    "Loire-Atlantique": "44", "Loiret": "45", "Lot": "46", "Lot-et-Garonne": "47",
    "Lozère": "48", "Maine-et-Loire": "49", "Manche": "50", "Marne": "51",
    "Haute-Marne": "52", "Mayenne": "53", "Meurthe-et-Moselle": "54", "Meuse": "55",
    "Morbihan": "56", "Moselle": "57", "Nièvre": "58", "Nord": "59", "Oise": "60",
    "Orne": "61", "Pas-de-Calais": "62", "Puy-de-Dôme": "63", "Pyrénées-Atlantiques": "64",
    "Hautes-Pyrénées": "65", "Pyrénées-Orientales": "66", "Bas-Rhin": "67",
    "Haut-Rhin": "68", "Rhône": "69", "Haute-Saône": "70", "Saône-et-Loire": "71",
    "Sarthe": "72", "Savoie": "73", "Haute-Savoie": "74", "Paris": "75",
    "Seine-Maritime": "76", "Seine-et-Marne": "77", "Yvelines": "78",
    "Deux-Sèvres": "79", "Somme": "80", "Tarn": "81", "Tarn-et-Garonne": "82",
    "Var": "83", "Vaucluse": "84", "Vendée": "85", "Vienne": "86", "Haute-Vienne": "87",
    "Vosges": "88", "Yonne": "89", "Territoire de Belfort": "90", "Essonne": "91",
    "Hauts-de-Seine": "92", "Seine-Saint-Denis": "93", "Val-de-Marne": "94",
    "Val-d'Oise": "95"
}
df_dep["dep_norm"] = df_dep["Département"].apply(normalize_name)


fichier_excel = "Panorama_statistique_2024.xlsx"
df_excel = pd.read_excel(fichier_excel, sheet_name="2. Revenus et inégalités", header=None)


departements = [str(dep).strip() for dep in df_excel.iloc[3, 1:] if pd.notna(dep)]
taux_pauvrete_75_plus = df_excel.iloc[7, 1:1+len(departements)].tolist()
niveau_vie_median = df_excel.iloc[4, 1:1+len(departements)].tolist()



norm_dep_taux = {normalize_name(dep): val for dep, val in zip(departements, taux_pauvrete_75_plus)}

norm_dep_niveau_vie = {normalize_name(dep): val for dep, val in zip(departements, niveau_vie_median)}


records = []
for code, nom in code_to_nom.items():
    key = normalize_name(nom)
    taux = norm_dep_taux.get(key, np.nan)
    niveau_vie = norm_dep_niveau_vie.get(key, np.nan)
    records.append({
        "code_departement": code,
        "departement": nom,
        "Taux de pauvrete pour plus de 75 ans": taux,
        "Niveau de vie médian des ménages (en euros)": niveau_vie
    })

df_b = pd.DataFrame(records)

df_b["dep_norm"] = df_b["departement"].apply(normalize_name)


df = df_b.merge(df_dep, on="dep_norm", how="left")


df = df.drop(columns=["dep_norm"])



df_pop = pd.read_excel("population_departements_60_75_plus.xlsx")




code_col = None
for c in df_pop.columns:
    if "geo" in c.lower():
        code_col = c
        break

if code_col is None:
    raise ValueError("Impossible de trouver la colonne du code département dans df_pop")


df_pop = df_pop.rename(columns={
    "GEO_": "code_departement",
    "F_Y60T74": "Femmes_60_74_ans",
    "M_Y60T74": "Hommes_60_74_ans",
    "F_Y75Tplus": "Femmes_75_ans_et_plus",
    "M_Y75Tplus": "Hommes_75_ans_et_plus"
})

df_pop["code_departement"] = df_pop["code_departement"].astype(str).str.zfill(2)


df_merged = df.merge(df_pop, on="code_departement", how="left")

#-------------------------------------------------------------------------
df_dept = pd.read_csv("departement_aggreg.csv", sep=",")

df_dept["dep_norm"] = df_dept["Nom Officiel Département"].apply(normalize_name)

df_merged["dep_norm"] = df_merged["Département"].apply(normalize_name) 

df_final_2 =df_merged.merge(df_dept, on="dep_norm", how="left")

df_final_2 = df_final_2.drop(columns=["dep_norm", "Nom Officiel Département"])



#-------------------------------------------------------------------------

fichier_excel = "Panorama_statistique_2024.xlsx"
df_handicap = pd.read_excel(fichier_excel, sheet_name="5. Handicap-Dépendance", header=None)

departements = [str(dep).strip() for dep in df_handicap.iloc[3, 1:] if pd.notna(dep)]

apa_60_plus = df_handicap.iloc[7, 1:1+len(departements)].tolist()
apa_75_plus = df_handicap.iloc[8, 1:1+len(departements)].tolist()

norm_dep_apa_60 = {normalize_name(dep): val for dep, val in zip(departements, apa_60_plus)}
norm_dep_apa_75 = {normalize_name(dep): val for dep, val in zip(departements, apa_75_plus)}


df_final_2["dep_norm"] = df_final_2["Département"].apply(normalize_name)

df_final_2["APA_60_plus"] = df_final_2["dep_norm"].map(norm_dep_apa_60)
df_final_2["APA_75_plus"] = df_final_2["dep_norm"].map(norm_dep_apa_75)


df_final_2 = df_final_2.drop(columns=["dep_norm"])

output_file = "resultat_final.csv"
df_final_2.to_csv(output_file, index=False, encoding="utf-8-sig")

#-------------------------------------------------------------------------


df_taux_equip = pd.read_excel(fichier_excel, sheet_name="8. Taux équipement PA", header=None)


departements = [str(dep).strip() for dep in df_taux_equip.iloc[4, 1:] if pd.notna(dep)]

ehpad_75_plus = df_taux_equip.iloc[5, 1:1+len(departements)].tolist()
non_ehpad_75_plus = df_taux_equip.iloc[6, 1:1+len(departements)].tolist()
centre_jour_75_plus = df_taux_equip.iloc[7, 1:1+len(departements)].tolist()
ssiads_75_plus = df_taux_equip.iloc[8, 1:1+len(departements)].tolist()


norm_dep_ehpad = {normalize_name(dep): val for dep, val in zip(departements, ehpad_75_plus)}
norm_dep_non_ehpad = {normalize_name(dep): val for dep, val in zip(departements, non_ehpad_75_plus)}
norm_dep_centre_jour = {normalize_name(dep): val for dep, val in zip(departements, centre_jour_75_plus)}
norm_dep_ssiads = {normalize_name(dep): val for dep, val in zip(departements, ssiads_75_plus)}


df_final_2["dep_norm"] = df_final_2["Département"].apply(normalize_name)

df_final_2["Taux_EHPAD_75_plus"] = df_final_2["dep_norm"].map(norm_dep_ehpad)
df_final_2["Taux_non_EHPAD_75_plus"] = df_final_2["dep_norm"].map(norm_dep_non_ehpad)
df_final_2["Taux_Centre_jour_75_plus"] = df_final_2["dep_norm"].map(norm_dep_centre_jour)
df_final_2["Taux_SSIAD_75_plus"] = df_final_2["dep_norm"].map(norm_dep_ssiads)

df_final_2 = df_final_2.drop(columns=["dep_norm"])

#-------------------------------------------------------------------------

df_esms = pd.read_excel(fichier_excel, sheet_name="7. ESMS PA", header=None)


departements = [str(dep).strip() for dep in df_esms.iloc[4, 1:] if pd.notna(dep)]


ehpad_nb_etab = df_esms.iloc[6, 1:1+len(departements)].tolist()
ehpad_nb_lits = df_esms.iloc[7, 1:1+len(departements)].tolist()

res_aut_nb_etab = df_esms.iloc[11, 1:1+len(departements)].tolist()
res_aut_nb_lits = df_esms.iloc[12, 1:1+len(departements)].tolist()

usld_nb = df_esms.iloc[15, 1:1+len(departements)].tolist()
usld_nb_lits = df_esms.iloc[17, 1:1+len(departements)].tolist()

centre_jour_nb_etab = df_esms.iloc[19, 1:1+len(departements)].tolist()
centre_jour_nb_lits = df_esms.iloc[20, 1:1+len(departements)].tolist()

autres_nb_etab = df_esms.iloc[23, 1:1+len(departements)].tolist()
autres_nb_lits = df_esms.iloc[24, 1:1+len(departements)].tolist()

ssiads_nb_service = df_esms.iloc[27, 1:1+len(departements)].tolist()
ssiads_nb_lits = df_esms.iloc[28, 1:1+len(departements)].tolist()



norm_dep_esms = {normalize_name(dep): dep for dep in departements}


df_final_2["dep_norm"] = df_final_2["Département"].apply(normalize_name)





df_final_2["EHPAD_nb_etab"] = df_final_2["dep_norm"].map(lambda x: ehpad_nb_etab[departements.index(norm_dep_esms[x])] if x in norm_dep_esms else None)
df_final_2["EHPAD_nb_lits"] = df_final_2["dep_norm"].map(lambda x: ehpad_nb_lits[departements.index(norm_dep_esms[x])] if x in norm_dep_esms else None)

df_final_2["ResAut_nb_etab"] = df_final_2["dep_norm"].map(lambda x: res_aut_nb_etab[departements.index(norm_dep_esms[x])] if x in norm_dep_esms else None)
df_final_2["ResAut_nb_lits"] = df_final_2["dep_norm"].map(lambda x: res_aut_nb_lits[departements.index(norm_dep_esms[x])] if x in norm_dep_esms else None)

df_final_2["USLD_nb"] = df_final_2["dep_norm"].map(lambda x: usld_nb[departements.index(norm_dep_esms[x])] if x in norm_dep_esms else None)
df_final_2["USLD_nb_lits"] = df_final_2["dep_norm"].map(lambda x: usld_nb_lits[departements.index(norm_dep_esms[x])] if x in norm_dep_esms else None)

df_final_2["CentreJour_nb_etab"] = df_final_2["dep_norm"].map(lambda x: centre_jour_nb_etab[departements.index(norm_dep_esms[x])] if x in norm_dep_esms else None)
df_final_2["CentreJour_nb_lits"] = df_final_2["dep_norm"].map(lambda x: centre_jour_nb_lits[departements.index(norm_dep_esms[x])] if x in norm_dep_esms else None)

df_final_2["Autres_nb_etab"] = df_final_2["dep_norm"].map(lambda x: autres_nb_etab[departements.index(norm_dep_esms[x])] if x in norm_dep_esms else None)
df_final_2["Autres_nb_lits"] = df_final_2["dep_norm"].map(lambda x: autres_nb_lits[departements.index(norm_dep_esms[x])] if x in norm_dep_esms else None)

df_final_2["SSIAD_nb_service"] = df_final_2["dep_norm"].map(lambda x: ssiads_nb_service[departements.index(norm_dep_esms[x])] if x in norm_dep_esms else None)
df_final_2["SSIAD_nb_lits"] = df_final_2["dep_norm"].map(lambda x: ssiads_nb_lits[departements.index(norm_dep_esms[x])] if x in norm_dep_esms else None)


df_final_2 = df_final_2.drop(columns=["dep_norm"])


#---------------------------------------------------------------------------------------------------------------------------------------------------------



df_esp = pd.read_csv("esperance-de-vie-par-departements.csv")
df_esp = df_esp.rename(columns={"L’espérance de vie": "esp"})


df_esp["Departement_clean"] = df_esp["Région-Département"].str.split(" - ").str[-1].str.strip()

df_esp["dep_norm"] = df_esp["Departement_clean"].apply(normalize_name)
df_final_2["dep_norm"] = df_final_2["Département"].apply(normalize_name)

df_esp["esp"] = pd.to_numeric(df_esp["esp"], errors='coerce')

df_final_2 = df_final_2.merge(df_esp[["dep_norm", "esp"]], on="dep_norm", how="left")


#-------------------------------------------------------------------------


df_extra = pd.read_csv("extracted_60plus_long.csv")

df_extra = df_extra.rename(columns={
    "sheet": "source",
    "dep_code": "code_departement",
    "dep_name_raw": "departement",
    "metric": "variable",
    "value": "valeur"
})


df_extra["code_departement"] = (
    df_extra["code_departement"]
    .astype(str)
    .str.strip() 
    .apply(lambda x: x.zfill(2) if x.isdigit() and len(x) < 3 else x)
)



df_extra["var_id"] = df_extra["source"] + "_" + df_extra["variable"]

df_extra_wide = df_extra.pivot_table(
    index="code_departement", 
    columns="var_id",
    values="valeur",
    aggfunc="first"
).reset_index()


df_extra_wide.columns = [str(c) for c in df_extra_wide.columns]

df_final_2["code_departement"] = df_final_2["code_departement"].astype(str) 


df_final_2 = df_final_2.merge(df_extra_wide, on="code_departement", how="left")
df_final_2 = df_final_2.drop(columns=["dep_norm"])


#--------------------------------------------------------------------------


path_tcrd = "2023_effectif-departemental-par-pathologie-sexe-age_serie-annuelle.xlsx"
xls = pd.ExcelFile(path_tcrd)



def clean_tcrd_sheet(sheet):
    df = pd.read_excel(path_tcrd, sheet_name=sheet, header=None)
    current_dept = None
    
    data = df.iloc[3:].copy()
    patho = data.iloc[:, 0]

    rows = []
    SEXE_AGE = ["Hommes", "Femmes", "≥ 65 ans"]
    for col in range(2, df.shape[1]):
        bloc_index = (col - 2) % 3
        sexe_age = SEXE_AGE[bloc_index]
        if bloc_index == 0:
            dept_code_raw = df.iloc[1, col]
            if pd.isna(dept_code_raw):
                current_dept = None
                continue 
            current_dept = str(dept_code_raw).strip()
        if current_dept is None:
            continue
            
        dept = current_dept 

        for i in range(len(data)):
            raw_value = data.iloc[i, col]
            if pd.isna(raw_value):
                continue

            try:
                num = float(raw_value)
                value = int(num) if num.is_integer() else num
            except:
                continue

            col_name = f"{sexe_age} - {patho.iloc[i]}"

            rows.append({
                "code_departement": dept,
                "colonne": col_name,
                "valeur": value
            })

    return pd.DataFrame(rows)


df_t1 = clean_tcrd_sheet(xls.sheet_names[0])
df_t2 = clean_tcrd_sheet(xls.sheet_names[1])

df_long = pd.concat([df_t1, df_t2], ignore_index=True)

df_long["code_departement"] = df_long["code_departement"].astype(str).str.zfill(2)




df_wide = df_long.pivot_table(
    index="code_departement",
    columns="colonne",
    values="valeur",
    aggfunc="first"
).reset_index()


df_wide.columns.name = None




df_final_3 = df_final_2.merge(df_wide, on="code_departement", how="left")


#-------------------------------------------------------------------------



# Lecture du fichier
df_lv = pd.read_csv("livia_lieux_vie_sc1.csv", sep=";", encoding="latin-1")

# Renommer les colonnes
df_lv = df_lv.rename(columns={
    "Département (ENS = France entière)": "DEPARTEMENT",
    "Année": "ANNEE",
    "Sexe": "SEXE",
    "Nombre projeté de seniors": "vol_GLOB",
    "Nombre projeté de seniors en ménage ordinaire qui sont en situation de dépendance modérée (GIR 3 et 4)": "vol_m_GLOB",
    "Nombre projeté de seniors en ménage ordinaire qui sont en situation de dépendance sévère (GIR 1 et 2)": "vol_s_GLOB",
    "Nombre projeté de seniors en résidence autonomie": "vol_RA",
    "Nombre projeté de seniors en EHPAD et assimilés": "vol_INS",
    "Nombre projeté de seniors en ménage ordinaire": "vol_MENO",
    "Taux de seniors en résidence autonomie": "taux_ra",
    "Taux de seniors en EHPAD et assimilés": "taux_insti",
    "Taux de seniors en ménage ordinaire": "taux_meno",
    "Taux de seniors en ménage ordinaire qui sont en situation de dépendance modérée (GIR 3 et 4)": "taux_dep_moderee",
    "Taux de seniors en ménage ordinaire qui sont en situation de dépendance sévère (GIR 1 et 2)": "taux_dep_severe",
})

# Filtrer les années
annees = [2025, 2030, 2035, 2040, 2045, 2050]
df_lv = df_lv[df_lv["ANNEE"].isin(annees)]

# Ajouter taux_dep
df_lv["taux_dep"] = df_lv["taux_dep_moderee"] + df_lv["taux_dep_severe"]

# Colonnes à conserver
colonnes_conservees = [
    "DEPARTEMENT", "ANNEE", "SEXE",
    "vol_GLOB", "vol_m_GLOB", "vol_s_GLOB",
    "vol_MENO", "vol_RA", "vol_INS",
    "taux_meno", "taux_ra", "taux_insti",
    "taux_dep_moderee", "taux_dep_severe", "taux_dep"
]

df_lv = df_lv[colonnes_conservees]

# Colonnes numériques
colonnes_num = df_lv.select_dtypes(include="number").columns

# Fonction d’agrégation
def agg(df, sexe=None):
    if sexe is not None:
        data = df[df["SEXE"] == sexe].copy()
    else:
        data = df.copy()
    
    # Exclure ANNEE de la somme pour garder les années correctes
    colonnes_num_sans_annee = [c for c in colonnes_num if c != "ANNEE"]
    
    grouped = data.groupby(["DEPARTEMENT", "ANNEE"], as_index=False)[colonnes_num_sans_annee].sum()
    
    
    grouped["SEXE"] = (
        "Hommes" if sexe == "HOMMES" else
        "Femmes" if sexe == "FEMMES" else
        "Ensemble"
    )
    
    return grouped


agg_h = agg(df_lv, "HOMMES")
agg_f = agg(df_lv, "FEMMES")
agg_tot = agg(df_lv, None)


df_lv_final = pd.concat([agg_h, agg_f, agg_tot], ignore_index=True)


suffix = "_s1"
colonnes_sauf = ["DEPARTEMENT", "ANNEE", "SEXE"]
colonnes_a_renommer = [c for c in df_lv_final.columns if c not in colonnes_sauf]
df_lv_final = df_lv_final.rename(columns={c: c + suffix for c in colonnes_a_renommer})


keys = []
for idx, row in df_lv_final.iterrows():
    sexe_initial = str(row["SEXE"]).strip()[0].upper()
    annee_str = str(row["ANNEE"])  
    keys.append(f"{sexe_initial}_{annee_str}")

df_lv_final["KEY"] = keys


df_lv_final["code_departement"] = (
    df_lv_final["DEPARTEMENT"]
    .astype(str)
    .str.replace(" ", "")
    .str.zfill(2)
)


value_cols = [c for c in df_lv_final.columns if c.endswith('_s1')]
df_lv_wide_list = []
for col in value_cols:
    tmp = df_lv_final.pivot(index='code_departement', columns='KEY', values=col)
    tmp.columns = [f"{col}_{key}" for key in tmp.columns]
    df_lv_wide_list.append(tmp)


df_lv_wide = pd.concat(df_lv_wide_list, axis=1).reset_index()

df_final_4 = df_final_3.merge(df_lv_wide, on="code_departement", how="left")



#-------------------------------------------------------------------------------

df_lv2 = pd.read_csv("livia_lieux_vie_sc2.csv", sep=";", encoding="latin-1")


df_lv2 = df_lv2.rename(columns={
    "Département (ENS = France entière)": "DEPARTEMENT",
    "Année": "ANNEE",
    "Sexe": "SEXE",

    "Nombre projeté de seniors": "vol_GLOB",

    "Nombre projeté de seniors en ménage ordinaire qui sont en situation de dépendance modérée (GIR 3 et 4)": "vol_m_GLOB",
    "Nombre projeté de seniors en ménage ordinaire qui sont en situation de dépendance sévère (GIR 1 et 2)": "vol_s_GLOB",

    "Nombre projeté de seniors en résidence autonomie": "vol_RA",
    "Nombre projeté de seniors en EHPAD et assimilés": "vol_INS",
    "Nombre projeté de seniors en ménage ordinaire": "vol_MENO",

    "Taux de seniors en résidence autonomie": "taux_ra",
    "Taux de seniors en EHPAD et assimilés": "taux_insti",
    "Taux de seniors en ménage ordinaire": "taux_meno",

    "Taux de seniors en ménage ordinaire qui sont en situation de dépendance modérée (GIR 3 et 4)": "taux_dep_moderee",
    "Taux de seniors en ménage ordinaire qui sont en situation de dépendance sévère (GIR 1 et 2)": "taux_dep_severe",
})


annees = [2025, 2030, 2035, 2040, 2045, 2050]
df_lv2 = df_lv2[df_lv2["ANNEE"].isin(annees)]

colonnes_conservees = [
    "DEPARTEMENT", "ANNEE", "SEXE",
    "vol_GLOB",
    "vol_m_GLOB",
    "vol_s_GLOB",
    "vol_MENO",
    "vol_RA",
    "vol_INS",
    "taux_meno",
    "taux_ra",
    "taux_insti",
    "taux_dep_moderee",
    "taux_dep_severe"
]

df_lv2["taux_dep"] = df_lv2["taux_dep_moderee"] + df_lv2["taux_dep_severe"]

df_lv2 = df_lv2[colonnes_conservees]

colonnes_num = df_lv2.select_dtypes(include="number").columns




agg_h2 = agg(df_lv2, "HOMMES")
agg_f2 = agg(df_lv2, "FEMMES")
agg_tot2 = agg(df_lv2, None)

df_lv_final_s2 = pd.concat([agg_h2, agg_f2, agg_tot2], ignore_index=True)


suffix = "_s2"
colonnes_sauf = ["DEPARTEMENT", "ANNEE", "SEXE"]

colonnes_a_renommer = [c for c in df_lv_final_s2.columns if c not in colonnes_sauf]

df_lv_final_s2 = df_lv_final_s2.rename(columns={c: c + suffix for c in colonnes_a_renommer})


df_lv_final_s2["code_departement"] = (
    df_lv_final_s2["DEPARTEMENT"]
    .astype(str)
    .str.replace(" ", "")
    .str.zfill(2)
)

value_cols2 = df_lv_final_s2.select_dtypes(include="number").columns.tolist()
value_cols2 = [c for c in value_cols2 if c not in ["ANNEE"]]


df_lv_final_s2["KEY"] = (
    df_lv_final_s2["SEXE"].str[0].str.upper()
    + "_" +
    df_lv_final_s2["ANNEE"].astype(str)
)

df_lv_wide2 = df_lv_final_s2.pivot_table(
    index="code_departement",
    columns="KEY",
    values=value_cols2
)

df_lv_wide2.columns = [f"{var}_{key}" for var, key in df_lv_wide2.columns]

df_lv_wide2 = df_lv_wide2.reset_index()




df_final_5 = df_final_4.merge(df_lv_wide2, on="code_departement", how="left")

#-------------------------------------------------------------------------------
df_lv3 = pd.read_csv("livia_lieux_vie_sc3.csv", sep=";", encoding="latin-1")


df_lv3 = df_lv3.rename(columns={
    "Département (ENS = France entière)": "DEPARTEMENT",
    "Année": "ANNEE",
    "Sexe": "SEXE",

    "Nombre projeté de seniors": "vol_GLOB",

    "Nombre projeté de seniors en ménage ordinaire qui sont en situation de dépendance modérée (GIR 3 et 4)": "vol_m_GLOB",
    "Nombre projeté de seniors en ménage ordinaire qui sont en situation de dépendance sévère (GIR 1 et 2)": "vol_s_GLOB",

    "Nombre projeté de seniors en résidence autonomie": "vol_RA",
    "Nombre projeté de seniors en EHPAD et assimilés": "vol_INS",
    "Nombre projeté de seniors en ménage ordinaire": "vol_MENO",

    "Taux de seniors en résidence autonomie": "taux_ra",
    "Taux de seniors en EHPAD et assimilés": "taux_insti",
    "Taux de seniors en ménage ordinaire": "taux_meno",

    "Taux de seniors en ménage ordinaire qui sont en situation de dépendance modérée (GIR 3 et 4)": "taux_dep_moderee",
    "Taux de seniors en ménage ordinaire qui sont en situation de dépendance sévère (GIR 1 et 2)": "taux_dep_severe",
})


annees = [2025, 2030, 2035, 2040, 2045, 2050]
df_lv3 = df_lv3[df_lv3["ANNEE"].isin(annees)]

colonnes_conservees = [
    "DEPARTEMENT", "ANNEE", "SEXE",
    "vol_GLOB",
    "vol_m_GLOB",
    "vol_s_GLOB",
    "vol_MENO",
    "vol_RA",
    "vol_INS",
    "taux_meno",
    "taux_ra",
    "taux_insti",
    "taux_dep_moderee",
    "taux_dep_severe"
]

df_lv3["taux_dep"] = df_lv3["taux_dep_moderee"] + df_lv3["taux_dep_severe"]

df_lv3 = df_lv3[colonnes_conservees]

colonnes_num = df_lv3.select_dtypes(include="number").columns




agg_h3 = agg(df_lv3, "HOMMES")
agg_f3 = agg(df_lv3, "FEMMES")
agg_tot3 = agg(df_lv3, None)

df_lv_final_s3 = pd.concat([agg_h3, agg_f3, agg_tot3], ignore_index=True)


suffix = "_s3"
colonnes_sauf = ["DEPARTEMENT", "ANNEE", "SEXE"]

colonnes_a_renommer = [c for c in df_lv_final_s3.columns if c not in colonnes_sauf]

df_lv_final_s3 = df_lv_final_s3.rename(columns={c: c + suffix for c in colonnes_a_renommer})


df_lv_final_s3["code_departement"] = (
    df_lv_final_s3["DEPARTEMENT"]
    .astype(str)
    .str.replace(" ", "")
    .str.zfill(2)
)

value_cols3 = df_lv_final_s3.select_dtypes(include="number").columns.tolist()
value_cols3 = [c for c in value_cols3 if c not in ["ANNEE"]]


df_lv_final_s3["KEY"] = (
    df_lv_final_s3["SEXE"].str[0].str.upper()
    + "_" +
    df_lv_final_s3["ANNEE"].astype(str)
)




df_lv_wide3 = df_lv_final_s3.pivot_table(
    index="code_departement",
    columns="KEY",
    values=value_cols3
)

df_lv_wide3.columns = [f"{var}_{key}" for var, key in df_lv_wide3.columns]

df_lv_wide3 = df_lv_wide3.reset_index()




df_final_6 = df_final_5.merge(df_lv_wide3, on="code_departement", how="left")

#-------------------------------------------------------------------------
"""

df_apa = pd.read_csv("livia_beneficiaires_apa.csv", sep=";", encoding="latin-1")

df_apa = df_apa.rename(columns={
    "Département (ENS = France entière)": "DEPARTEMENT",
    "Année": "ANNEE",
    "Sexe": "SEXE",
})

annees = [2025, 2030, 2035, 2040, 2045, 2050]
df_apa = df_apa[df_apa["ANNEE"].isin(annees)]


colonnes_s1 = {
    "Nombre de beneficiaires de l'APA (scénario 1)": "total_APA",
    "Nombre de beneficiaires de l'APA domicile (scénario 1)": "total_APA_DOM",
    "Nombre de beneficiaires de l'APA etablissement (scénario 1)": "total_APA_ETAB",
    "Nombre de beneficiaires de l'APA domicile en GIR 3 et 4 (scénario 1)": "vol_APA_m_DOM",
}

colonnes_s2 = {
    "Nombre de beneficiaires de l'APA (scénario 2)": "total_APA",
    "Nombre de beneficiaires de l'APA domicile (scénario 2)": "total_APA_DOM",
    "Nombre de beneficiaires de l'APA etablissement (scénario 2)": "total_APA_ETAB",
    "Nombre de beneficiaires de l'APA domicile en GIR 3 et 4 (scénario 2)": "vol_APA_m_DOM",
}

colonnes_s3 = {
    "Nombre de beneficiaires de l'APA (scénario 3)": "total_APA",
    "Nombre de beneficiaires de l'APA domicile (scénario 3)": "total_APA_DOM",
    "Nombre de beneficiaires de l'APA etablissement (scénario 3)": "total_APA_ETAB",
    "Nombre de beneficiaires de l'APA domicile en GIR 3 et 4 (scénario 3)": "vol_APA_m_DOM",
}


def prepare_apa(df, mapping, suffix):
    df_tmp = df.copy()

    # Renommage des colonnes de valeurs
    df_tmp = df_tmp.rename(columns=mapping)

    # Création d'une clé UNIQUE par ligne
    df_tmp["SCENARIO_DEMOGRAPHIE"] = (
        df_tmp["Tranche d'âge"].astype(str) + "_" +
        df_tmp["Hypothèse d'évolution de la dépendance"].astype(str) + "_" +
        df_tmp["Hypothèse d'évolution démographique"].astype(str)
    )

    # Colonnes de base + métriques
    base_cols = ["DEPARTEMENT", "ANNEE", "SEXE", "SCENARIO_DEMOGRAPHIE"]
    df_tmp = df_tmp[base_cols + list(mapping.values())]

    # Ajout suffixe
    df_tmp = df_tmp.rename(columns={c: c + suffix for c in mapping.values()})

    return df_tmp



df_apa_s1 = prepare_apa(df_apa, colonnes_s1, "_s1")
df_apa_s2 = prepare_apa(df_apa, colonnes_s2, "_s2")
df_apa_s3 = prepare_apa(df_apa, colonnes_s3, "_s3")


keys = ["DEPARTEMENT", "ANNEE", "SEXE", "SCENARIO_DEMOGRAPHIE"]

df_apa_all = df_apa_s1.merge(df_apa_s2, on=keys, how="outer")
df_apa_all = df_apa_all.merge(df_apa_s3, on=keys, how="outer")


df_apa_all["code_departement"] = (
    df_apa_all["DEPARTEMENT"]
    .astype(str)
    .str.replace(" ", "")
    .str.zfill(2)
)


df_apa_all = df_apa_all.drop(columns=["DEPARTEMENT", "ANNEE", "SEXE", "SCENARIO_DEMOGRAPHIE"])


print(df_final_6["code_departement"].value_counts().head(20))
print(df_apa_all["code_departement"].value_counts().head(20))

df_final_7 = df_final_6.merge(df_apa_all, on="code_departement", how="left")

"""
#-------------------------------------------------------------------------

df_sante = pd.read_csv("couvertures-vaccinales-des-adolescent-et-adultes-departement.csv")


cols = [
    "Département Code",
    "Grippe 65 ans et plus",
    "Grippe 65-74 ans",
    "Grippe 75 ans et plus",
    "Covid-19 65 ans et plus",
    "Année"
]

df_sante_2023 = (
    df_sante[cols]
    .loc[df_sante["Année"] == 2023]
    .copy()
)

df_final_6["dep_code_norm"] = (
    df_final_2["code_departement"]
    .astype(str)
    .str.upper()
    .str.strip()
)

df_sante_2023["dep_code_norm"] = (
    df_sante_2023["Département Code"]
    .astype(str)
    .str.upper()
    .str.strip()
)

vars_num = [
    "Grippe 65 ans et plus",
    "Grippe 65-74 ans",
    "Grippe 75 ans et plus",
    "Covid-19 65 ans et plus"
]

df_sante_2023[vars_num] = df_sante_2023[vars_num].apply(
    pd.to_numeric, errors="coerce"
)


df_final_6 = df_final_6.merge(
    df_sante_2023[
        ["dep_code_norm"] + vars_num
    ],
    on="dep_code_norm",
    how="left"
)
#-------------------------------------------------------------------------

def add_60_75_plus(df, col_60_74, col_75_plus, new_col):
    df[new_col] = df[[col_60_74, col_75_plus]].sum(axis=1, min_count=1)


add_60_75_plus(df_final_6, "Femmes_60_74_ans", "Femmes_75_ans_et_plus", "Femmes_60_75_plus")
add_60_75_plus(df_final_6, "Hommes_60_74_ans", "Hommes_75_ans_et_plus", "Hommes_60_75_plus")


pairs = [
    ("60_74_appart_ascenseur", "75_plus_appart_ascenseur", "60_75_plus_appart_ascenseur"),
    ("60_74_autre_logement", "75_plus_autre_logement", "60_75_plus_autre_logement"),
    ("60_74_menage_30ans_plus", "75_plus_menage_30ans_plus", "60_75_plus_menage_30ans_plus"),
    ("60_74_en_maison", "75_plus_en_maison", "60_75_plus_en_maison"),
    ("60_74_menage_peu_diplome", "75_plus_menage_peu_diplome", "60_75_plus_menage_peu_diplome"),
    ("60_74_menage_immigre", "75_plus_menage_immigre", "60_75_plus_menage_immigre"),
    ("60_74_proprietaires", "75_plus_proprietaires", "60_75_plus_proprietaires"),
    ("60_74_sans_voiture", "75_plus_sans_voiture", "60_75_plus_sans_voiture"),
    ("60_74_isoles", "75_plus_isoles", "60_75_plus_isoles"),
    ("femmes_60_74_isolees", "femmes_75_plus_isolees", "femmes_60_75_plus_isolees")
]

for c60, c75, new in pairs:
    add_60_75_plus(df_final_6, c60, c75, new)
#-------------------------------------------------------------------------

df_fragilite = pd.read_csv("Dataset_fragilité_numérique.csv")


cols_frag = [
    "Nom Officiel Département Majuscule",
    "code_dep",
    " Score de fragilité numérique senior"
]
df_fragilite = df_fragilite[cols_frag].copy()

def normalize_dep_code(x):
    x = str(x).strip().upper()
    if x.isdigit():
        return x.zfill(2)
    return x

df_fragilite["dep_code_norm"] = (
    df_fragilite["code_dep"]
    .apply(normalize_dep_code)
)


df_fragilite[" Score de fragilité numérique senior"] = (
    df_fragilite[" Score de fragilité numérique senior"]
    .astype(str)
    .str.strip()       
    .str.replace(",", ".", regex=False)  
)


df_fragilite[" Score de fragilité numérique senior"] = pd.to_numeric(
    df_fragilite[" Score de fragilité numérique senior"],
    errors="coerce"
)
df_final_6["dep_code_norm"] = (
    df_final_6["code_departement"]
    .apply(normalize_dep_code)
)


df_final_6 = df_final_6.merge(
    df_fragilite[["dep_code_norm", " Score de fragilité numérique senior"]],
    on="dep_code_norm",
    how="left"
)
print(
    df_final_6.loc[
        df_final_6[" Score de fragilité numérique senior"].isna(),
        ["code_departement", "Département"]
    ]
)

#-------------------------------------------------------------------------

df_aspa = pd.read_csv("effectifs_ASPA_par_annee_departement.csv",sep=";")

df_aspa["dept_name_norm"] = (
    df_aspa["Nomdept"]
    .astype(str)
    .str.upper()
    .str.strip()
)
df_final_6["dept_name_norm"] = (
    df_final_6["Département"]
    .astype(str)
    .str.upper()
    .str.strip()
)
df_aspa["Annee"] = pd.to_numeric(df_aspa["Annee"], errors="coerce")
df_aspa["effectif"] = pd.to_numeric(df_aspa["effectif"], errors="coerce")
df_aspa_wide = (
    df_aspa
    .pivot_table(
        index="dept_name_norm",
        columns="Annee",
        values="effectif",
        aggfunc="sum"
    )
    .reset_index()
)
df_aspa_wide.columns = [
    "dept_name_norm"
    if col == "dept_name_norm"
    else f"aspa_effectif_{int(col)}"
    for col in df_aspa_wide.columns
]
df_final_6 = df_final_6.merge(
    df_aspa_wide,
    on="dept_name_norm",
    how="left"
)
#-------------------------------------------------------------------------

df_apl = pd.read_csv("accessibilite-potentielle-localisee-apl-aux-structures-medico-sociales-destinees.csv",sep =";")


# Normalisation département
df_apl["dep_code_norm"] = (
    df_apl["CODE_COM"]
    .astype(str)
    .str.strip()
    .str[:2]
)

# Colonnes numériques
cols_numeric = ["APL_EHPA", "APL_RA", "APL_SAPA"]
df_apl[cols_numeric] = df_apl[cols_numeric].apply(
    pd.to_numeric, errors="coerce"
)
df_apl_dep = (
    df_apl
    .groupby("dep_code_norm", as_index=False)[cols_numeric]
    .sum()   # ou mean(), selon le sens métier
)

# ✅ MERGE PROPRE (1 → 1)
df_final_6 = df_final_6.merge(
    df_apl_dep,
    on="dep_code_norm",
    how="left"
)


#------------------------------------------------------------------------

df_pauvrete = pd.read_excel(
    "taux_de_pauvreté_senior_2021 (1).xlsx",
    usecols="A,H,I",
    skiprows=4  
)

df_pauvrete.columns = ["code_dep", "taux_60_74", "taux_75_plus"]

df_pauvrete["code_dep_norm"] = df_pauvrete["code_dep"].astype(str).str.upper().str.strip().str[:2]

df_pauvrete["taux_60_74"] = df_pauvrete["taux_60_74"] /100
df_pauvrete["taux_75_plus"] = df_pauvrete["taux_75_plus"] /100


df_final_6 = df_final_6.merge(
    df_pauvrete[["code_dep_norm", "taux_60_74", "taux_75_plus"]],
    left_on="dep_code_norm",
    right_on="code_dep_norm",
    how="left"
)


df_final_6["pauvre60_74"] = (df_final_6["Femmes_60_74_ans"]+ df_final_6["Hommes_60_74_ans"])* df_final_6["taux_60_74"]

df_final_6["pauvre75_plus"] = (df_final_6["Hommes_75_ans_et_plus"] +df_final_6["Femmes_75_ans_et_plus"]) * df_final_6["taux_75_plus"]



df_final_6["total_pauvres"] = (df_final_6["pauvre75_plus"] +df_final_6["pauvre60_74"] )


df_final_6["total_seniors"] = (
    df_final_6["Femmes_60_74_ans"] + df_final_6["Hommes_60_74_ans"] +
    df_final_6["Femmes_75_ans_et_plus"] + df_final_6["Hommes_75_ans_et_plus"]
)


df_final_6["taux_pauvrete_calcul"] = (df_final_6["total_pauvres"] / df_final_6["total_seniors"]) * 100


cols_to_drop = [
    "taux_60_74", "taux_75_plus",
    "pauvre60_74", 
    "pauvre75_plus", 
    "total_pauvres"
]
df_final_6 = df_final_6.drop(columns=cols_to_drop)
#-------------------------------------------------------------------------



colonnes_maladies = [col for col in df_final_6.columns 
                     if col.startswith("≥ 65 ans -") and "Traitements" not in col]


df_final_6["total_malades_65_plus"] = df_final_6[colonnes_maladies].sum(axis=1)


df_final_6["nombre maladies par personnes"] = df_final_6["total_malades_65_plus"] / df_final_6["total_seniors"] 


colonnes_traitements = [col for col in df_final_6.columns 
                        if col.startswith("≥ 65 ans - Traitements")]


df_final_6["total_traitements_65_plus"] = df_final_6[colonnes_traitements].sum(axis=1)


df_final_6["taux_traitements_65_plus"] = df_final_6["total_traitements_65_plus"] / df_final_6["total_seniors"] * 100


groupes_traitements = {
    "antidepresseurs": [col for col in colonnes_traitements if "antidépresseurs" in col.lower()],
    "anxiolytiques": [col for col in colonnes_traitements if "anxiolytiques" in col.lower()],
    "hypnotiques": [col for col in colonnes_traitements if "hypnotiques" in col.lower()],
    "antihypertenseurs": [col for col in colonnes_traitements if "antihypertenseurs" in col.lower()],
    "hypolipemiants": [col for col in colonnes_traitements if "hypolipémiants" in col.lower()],
    "neuroleptiques": [col for col in colonnes_traitements if "neuroleptiques" in col.lower()]
}

groupes = {
    "cardiovasculaires": [
        "≥ 65 ans - Accident vasculaire cérébral aigu",
        "≥ 65 ans - Artériopathie oblitérante du membre inférieur",
        "≥ 65 ans - Autres affections cardiovasculaires",
        "≥ 65 ans - Insuffisance cardiaque aiguë",
        "≥ 65 ans - Insuffisance cardiaque chronique",
        "≥ 65 ans - Maladie coronaire chronique",
        "≥ 65 ans - Maladie valvulaire",
        "≥ 65 ans - Syndrome coronaire aigu",
        "≥ 65 ans - Troubles du rythme ou de la conduction cardiaque"
    ],
    "cancers": [
        "≥ 65 ans - Autres cancers actifs",
        "≥ 65 ans - Autres cancers sous surveillance",
        "≥ 65 ans - Cancer colorectal actif",
        "≥ 65 ans - Cancer colorectal sous surveillance",
        "≥ 65 ans - Cancer de la prostate actif",
        "≥ 65 ans - Cancer de la prostate sous surveillance",
        "≥ 65 ans - Cancer du poumon actif",
        "≥ 65 ans - Cancer du poumon sous surveillance",
        "≥ 65 ans - Cancer du sein de la femme actif",
        "≥ 65 ans - Cancer du sein de la femme sous surveillance"
    ],
    "neurologiques": [
        "≥ 65 ans - Autres affections neurologiques",
        "≥ 65 ans - Déficience mentale",
        "≥ 65 ans - Démences (dont maladie d'Alzheimer)",
        "≥ 65 ans - Maladie de Parkinson",
        "≥ 65 ans - Sclérose en plaques",
        #"≥ 65 ans - Epilepsie"
    ]

}


for groupe, cols in groupes.items():
    df_final_6[f"taux_{groupe}_65_plus"] = df_final_6[cols].sum(axis=1) / df_final_6["total_seniors"] * 100
for groupe, cols in groupes_traitements.items():
    df_final_6[f"taux_{groupe}_65_plus"] = df_final_6[cols].sum(axis=1) / df_final_6["total_seniors"] * 100


#-------------------------------------------------------------------------
output_file = "resultat_final.csv"
df_final_6.to_csv(output_file, index=False, encoding="utf-8-sig")
print("c'est fait")

