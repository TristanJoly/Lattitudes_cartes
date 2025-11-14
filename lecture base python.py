import pandas as pd

# Remplace 'fichier.csv' par le chemin de ton fichier
df = pd.read_csv('resultat_final.csv')
"""
pd.set_option('display.max_columns', None)  # Affiche toutes les colonnes
pd.set_option('display.max_rows', None)     # Affiche toutes les lignes si nécessaire

print(df.describe(include='all'))# Inclut toutes les colonnes
"""
a = df.columns.tolist()
for i in a :
    print (i)

