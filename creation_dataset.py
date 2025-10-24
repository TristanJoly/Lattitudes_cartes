
import streamlit as st
import json
from pathlib import Path
import folium
from streamlit_folium import st_folium
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

# --- lecture du fichier ---
fichier_excel = "Panorama_statistique_2024.xlsx"
df_excel = pd.read_excel(fichier_excel, sheet_name="2. Revenus et inégalités", header=None)

# --- extraction des données ---
departements = [str(dep).strip() for dep in df_excel.iloc[3, 1:] if pd.notna(dep)]
taux_pauvrete_75_plus = df_excel.iloc[7, 1:1+len(departements)].tolist()
niveau_vie_median = df_excel.iloc[4, 1:1+len(departements)].tolist()



norm_dep_taux = {normalize_name(dep): val for dep, val in zip(departements, taux_pauvrete_75_plus)}

norm_dep_niveau_vie = {normalize_name(dep): val for dep, val in zip(departements, niveau_vie_median)}

# --- construction du DataFrame final ---
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

# --- Nettoyage final ---
df = df.drop(columns=["dep_norm"])

#---------------

df_pop = pd.read_excel("population_departements_60_75_plus.xlsx")



# Identifier automatiquement la colonne du code département
code_col = None
for c in df_pop.columns:
    if "geo" in c.lower():
        code_col = c
        break

if code_col is None:
    raise ValueError("Impossible de trouver la colonne du code département dans df_pop")

# Renommer cette colonne proprement
df_pop = df_pop.rename(columns={
    "GEO_": "code_departement",
    "F_Y60T74": "Femmes_60_74_ans",
    "M_Y60T74": "Hommes_60_74_ans",
    "F_Y75Tplus": "Femmes_75_ans_et_plus",
    "M_Y75Tplus": "Hommes_75_ans_et_plus"
})

# S'assurer que les codes sont bien formatés sur 2 chiffres
df_pop["code_departement"] = df_pop["code_departement"].astype(str).str.zfill(2)

# --- Fusion avec le DataFrame principal ---
df_merged = df.merge(df_pop, on="code_departement", how="left")

#-------------------------------------------------------------------------
df_dept = pd.read_csv("departement_aggreg.csv", sep=",")  # ou sep="," selon ton CSV
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


departements = [str(dep).strip() for dep in df_taux_equip.iloc[3, 1:] if pd.notna(dep)]

ehpad_75_plus = df_taux_equip.iloc[4, 1:1+len(departements)].tolist()
non_ehpad_75_plus = df_taux_equip.iloc[5, 1:1+len(departements)].tolist()
centre_jour_75_plus = df_taux_equip.iloc[6, 1:1+len(departements)].tolist()
ssiads_75_plus = df_taux_equip.iloc[7, 1:1+len(departements)].tolist()


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


departements = [str(dep).strip() for dep in df_esms.iloc[3, 1:] if pd.notna(dep)]


ehpad_nb_etab = df_esms.iloc[5, 1:1+len(departements)].tolist()
ehpad_nb_lits = df_esms.iloc[6, 1:1+len(departements)].tolist()

res_aut_nb_etab = df_esms.iloc[10, 1:1+len(departements)].tolist()
res_aut_nb_lits = df_esms.iloc[11, 1:1+len(departements)].tolist()

usld_nb = df_esms.iloc[15, 1:1+len(departements)].tolist()
usld_nb_lits = df_esms.iloc[16, 1:1+len(departements)].tolist()

centre_jour_nb_etab = df_esms.iloc[18, 1:1+len(departements)].tolist()
centre_jour_nb_lits = df_esms.iloc[19, 1:1+len(departements)].tolist()

autres_nb_etab = df_esms.iloc[22, 1:1+len(departements)].tolist()
autres_nb_lits = df_esms.iloc[23, 1:1+len(departements)].tolist()

ssiads_nb_service = df_esms.iloc[26, 1:1+len(departements)].tolist()
ssiads_nb_lits = df_esms.iloc[27, 1:1+len(departements)].tolist()


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

#-------------------------------------------------------------------------
output_file = "resultat_final.csv"
df_final_2.to_csv(output_file, index=False, encoding="utf-8-sig")
print("c'est fait")
