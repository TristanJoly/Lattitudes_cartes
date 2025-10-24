import pandas as pd

# Chargement des données
df = pd.read_csv("60-et-plus_indicateurs-au-niveau-de-la-commune.csv", sep=';')
 

# Liste des variables à agréger
variables = [
    'FILOSOFI_AGE5Q217_60_74', 'BPE_NB_D101', 'BPE_NB_D106', 'BPE_NB_D108',
    'BPE_NB_D402', 'BPE_NB_D403', 'BPE_NB_D404', 'BPE_NB_D405',
    'FILOSOFI_AGE6Q217_75', 'APL_medecins_generalistes_est',
    'X6074_ANS_APPART_AV_ASC', 'X6074_ANS_APPART_SS_ASC', 'X6074_ANS_EMMENAGT_2',
    'X6074_ANS_AUT_LOGT', 'X6074_ANS_EMMENAGT_30', 'X6074_ANS_EN_MAISON',
    'X6074_ANS_ISOLES', 'X6074_ANS_MEN_NON_DIPL', 'X6074_ANS_MEN_PR_IMMIG',
    'X6074_ANS_PROPRIETAIRES', 'FEMMES_6074_ANS_ISOLEES',
    'X6074_ANS_SANS_VOITURE', 'FEMMES_75_ANS_ET_PLUS_ISOLEES',
    'X75_ANS_ET_PLUS_APPART_AV_ASC', 'X75_ANS_ET_PLUS_AUT_LOGT',
    'X75_ANS_ET_PLUS_EMMENAGT_30', 'X75_ANS_ET_PLUS_EN_MAISON',
    'X75_ANS_ET_PLUS_MEN_NON_DIPLOME', 'X75_ANS_ET_PLUS_MEN_PR_IMMIGREE',
    'X75_ANS_ET_PLUS_PROPRIETAIRES', 'X75_ANS_ET_PLUS_SANS_VOITURE'
]

# Sélection des colonnes utiles
df_selected = df[['Nom Officiel Département'] + variables]

# Agrégation par département (somme sur chaque variable)
df_dept = df_selected.groupby('Nom Officiel Département', as_index=False).sum(numeric_only=True)

# Dictionnaire de renommage
renommage = {
    'FILOSOFI_AGE5Q217_60_74': 'revenu_median_60_74',
    'BPE_NB_D101': 'hopital_court_sejour',
    'BPE_NB_D106': 'services_urgence',
    'BPE_NB_D108': 'dispensaire',
    'BPE_NB_D402': 'soins_domicile_personnes_agees',
    'BPE_NB_D403': 'aide_menagere_personnes_agees',
    'BPE_NB_D404': 'foyer_restaurant_personnes_agees',
    'BPE_NB_D405': 'repas_domicile_personnes_agees',
    'FILOSOFI_AGE6Q217_75': 'revenu_median_75_plus',
    'APL_medecins_generalistes_est': 'access_med_generalistes',
    'X6074_ANS_APPART_AV_ASC': '60_74_appart_ascenseur',
    'X6074_ANS_APPART_SS_ASC': '60_74_appart_sans_ascenseur',
    'X6074_ANS_EMMENAGT_2': '60_74_menage_2ans',
    'X6074_ANS_AUT_LOGT': '60_74_autre_logement',
    'X6074_ANS_EMMENAGT_30': '60_74_menage_30ans_plus',
    'X6074_ANS_EN_MAISON': '60_74_en_maison',
    'X6074_ANS_ISOLES': '60_74_isoles',
    'X6074_ANS_MEN_NON_DIPL': '60_74_menage_peu_diplome',
    'X6074_ANS_MEN_PR_IMMIG': '60_74_menage_immigre',
    'X6074_ANS_PROPRIETAIRES': '60_74_proprietaires',
    'FEMMES_6074_ANS_ISOLEES': 'femmes_60_74_isolees',
    'X6074_ANS_SANS_VOITURE': '60_74_sans_voiture',
    'FEMMES_75_ANS_ET_PLUS_ISOLEES': 'femmes_75_plus_isolees',
    'X75_ANS_ET_PLUS_APPART_AV_ASC': '75_plus_appart_ascenseur',
    'X75_ANS_ET_PLUS_AUT_LOGT': '75_plus_autre_logement',
    'X75_ANS_ET_PLUS_EMMENAGT_30': '75_plus_menage_30ans_plus',
    'X75_ANS_ET_PLUS_EN_MAISON': '75_plus_en_maison',
    'X75_ANS_ET_PLUS_MEN_NON_DIPLOME': '75_plus_menage_peu_diplome',
    'X75_ANS_ET_PLUS_MEN_PR_IMMIGREE': '75_plus_menage_immigre',
    'X75_ANS_ET_PLUS_PROPRIETAIRES': '75_plus_proprietaires',
    'X75_ANS_ET_PLUS_SANS_VOITURE': '75_plus_sans_voiture'
}

# Renommage des colonnes
df_dept.rename(columns=renommage, inplace=True)

# Sauvegarde en CSV
df_dept.to_csv("departement_aggreg.csv", index=False)

# Vérification
print(df_dept.head())
