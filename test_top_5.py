import pandas as pd

# Charger ton fichier
df = pd.read_csv('resultat_final.csv')

# --------------------------------------------------------
# Liste des colonnes à analyser
# --------------------------------------------------------
colonnes = [
"≥ 65 ans - Accident vasculaire cérébral aigu",
"≥ 65 ans - Artériopathie oblitérante du membre inférieur",
"≥ 65 ans - Autres affections cardiovasculaires",
"≥ 65 ans - Autres affections de longue durée (dont 31 et 32)",
"≥ 65 ans - Autres affections neurologiques",
"≥ 65 ans - Autres cancers actifs",
"≥ 65 ans - Autres cancers sous surveillance",
"≥ 65 ans - Autres maladies inflammatoires chroniques",
"≥ 65 ans - Autres troubles psychiatriques",
"≥ 65 ans - Cancer colorectal actif",
"≥ 65 ans - Cancer colorectal sous surveillance",
"≥ 65 ans - Cancer de la prostate actif",
"≥ 65 ans - Cancer de la prostate sous surveillance",
"≥ 65 ans - Cancer du poumon actif",
"≥ 65 ans - Cancer du poumon sous surveillance",
"≥ 65 ans - Cancer du sein de la femme actif",
"≥ 65 ans - Cancer du sein de la femme sous surveillance",
"≥ 65 ans - Diabète",
"≥ 65 ans - Dialyse chronique",
"≥ 65 ans - Déficience mentale",
"≥ 65 ans - Démences (dont maladie d'Alzheimer)",
"≥ 65 ans - Embolie pulmonaire aiguë",
"≥ 65 ans - Hémophilie ou troubles de l'hémostase graves",
"≥ 65 ans - Insuffisance cardiaque aiguë",
"≥ 65 ans - Insuffisance cardiaque chronique",
"≥ 65 ans - Maladie coronaire chronique",
"≥ 65 ans - Maladie de Parkinson",
"≥ 65 ans - Maladie valvulaire",
"≥ 65 ans - Maladies du foie ou du pancréas (hors mucoviscidose)",
"≥ 65 ans - Maladies inflammatoires chroniques intestinales",
"≥ 65 ans - Maladies métaboliques héréditaires ou amylose",
"≥ 65 ans - Maladies respiratoires chroniques (hors mucoviscidose)",
"≥ 65 ans - Mucoviscidose",
"≥ 65 ans - Myopathie ou myasthénie",
"≥ 65 ans - Paraplégie",
"≥ 65 ans - Polyarthrite rhumatoïde et maladies apparentées",
"≥ 65 ans - Sclérose en plaques",
"≥ 65 ans - Spondylarthrite ankylosante et maladies apparentées",
"≥ 65 ans - Suivi de transplantation rénale",
"≥ 65 ans - Syndrome coronaire aigu",
"≥ 65 ans - Séjours hospitaliers pour Covid-19",
"≥ 65 ans - Séquelle d'accident vasculaire cérébral",
"≥ 65 ans - Total",
"≥ 65 ans - Traitements antidépresseurs ou régulateurs de l'humeur (avec ou sans pathologies)",
"≥ 65 ans - Traitements antidépresseurs ou régulateurs de l'humeur (hors pathologies)",
"≥ 65 ans - Traitements antihypertenseurs (avec ou sans pathologies)",
"≥ 65 ans - Traitements antihypertenseurs (hors pathologies)",
"≥ 65 ans - Traitements anxiolytiques (avec ou sans pathologies)",
"≥ 65 ans - Traitements anxiolytiques (hors pathologies)",
"≥ 65 ans - Traitements hypnotiques (avec ou sans pathologies)",
"≥ 65 ans - Traitements hypnotiques (hors pathologies)",
"≥ 65 ans - Traitements hypolipémiants (avec ou sans pathologies)",
"≥ 65 ans - Traitements hypolipémiants (hors pathologies)",
"≥ 65 ans - Traitements neuroleptiques (avec ou sans pathologies)",
"≥ 65 ans - Traitements neuroleptiques (hors pathologies)",
"≥ 65 ans - Transplantation rénale",
"≥ 65 ans - Troubles addictifs",
"≥ 65 ans - Troubles du rythme ou de la conduction cardiaque",
"≥ 65 ans - Troubles névrotiques et de l’humeur",
"≥ 65 ans - Troubles psychiatriques ayant débuté dans l'enfance",
"≥ 65 ans - Troubles psychotiques",
"≥ 65 ans - VIH ou SIDA",
"≥ 65 ans - Épilepsie"
]

# --------------------------------------------------------
# Boucle pour afficher le Top 5 de chaque variable
# --------------------------------------------------------
for col in colonnes:
    if col in df.columns:
        print(f"\n🔹 Top 5 de la colonne : {col}")
        print(df[col].nlargest(5))
    else:
        print(f"\n⚠️ Colonne absente dans le fichier : {col}")
