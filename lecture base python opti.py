import pandas as pd

df = pd.read_csv('resultat_final.csv')

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)

print(df[" Score de fragilité numérique senior"])
