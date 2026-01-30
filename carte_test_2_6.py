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
from style_manager import apply_external_css
import plotly.express as px
import plotly.graph_objects as go
from branca.element import MacroElement
from jinja2 import Template
#-----------------------------------------------------------------------------------------------
def is_low(value, series):
    return pd.notna(value) and value <= series.quantile(0.25)

def is_high(value, series):
    return pd.notna(value) and value >= series.quantile(0.75)

def extract_dept_from_output(output, geo_key):
    if not output:
        return None
    lad = output.get("last_active_drawing")
    if isinstance(lad, dict):
        props = lad.get("properties") or {}
        for key in (geo_key, "code", "id", "nom", "name"):
            if props.get(key):
                return str(props.get(key))
    loc = output.get("last_object_clicked")
    if isinstance(loc, dict):
        props2 = loc.get("properties") or {}
        for key in (geo_key, "code", "id", "nom", "name"):
            if props2.get(key):
                return str(props2.get(key))
    tooltip = output.get("last_object_clicked_tooltip") or ""
    if tooltip:
        txt = re.sub(r"\s+", " ", tooltip).strip()
        m = re.search(r"\b(\d{1,2}A?|2A|2B)\b", txt)
        if m:
            return m.group(1)
    return None

def is_warning(feature):
    props = feature.get("properties") or {}
    code_raw = props.get(geo_key) or props.get("code") or props.get("id")
    if code_raw is None:
        return False
    code_s = str(code_raw).strip().lstrip("0")
    
    row = df[df["departement"].astype(str).str.lstrip("0") == code_s]
    if row.empty:
        return False
    
    row = row.iloc[0]
    for col, seuil in seuils_warning.items():
        if seuil is None:
            continue
        val = pd.to_numeric(row.get(col), errors="coerce")
        if pd.notna(val) and val <= seuil:
            return True
    return False


def detect_geo_key(geojson, df_codes):
    features = geojson.get("features", [])
    all_keys = set()
    for f in features:
        props = f.get("properties") or {}
        all_keys.update(props.keys())
    df_set = {str(x) for x in df_codes}
    for k in all_keys:
        vals = {str((f.get("properties") or {}).get(k)) for f in features if (f.get("properties") or {}).get(k) is not None}
        if vals & df_set:
            return k
        vals_nz = {v.lstrip("0") for v in vals if isinstance(v, str)}
        if vals_nz & {v.lstrip("0") for v in df_set}:
            return k
    return None

def extract_coords(geom):
    coords = []
    if not geom:
        return coords
    gtype = geom.get("type")
    c = geom.get("coordinates")
    if gtype == "Point":
        coords.append(tuple(c))
    elif gtype in ("MultiPoint", "LineString"):
        coords.extend([tuple(pt) for pt in c])
    elif gtype == "Polygon":
        for ring in c:
            for pt in ring:
                coords.append(tuple(pt))
    elif gtype == "MultiPolygon":
        for poly in c:
            for ring in poly:
                for pt in ring:
                    coords.append(tuple(pt))
    else:
        try:
            for item in c:
                coords.extend(extract_coords({"type":"unknown","coordinates":item}))
        except Exception:
            pass
    return coords

def feature_code_str(feature, geo_key):
    props = feature.get("properties") or {}
    val = props.get(geo_key) or props.get("code") or props.get("id")
    if val is None:
        return None
    s = str(val).strip()
    return s

def evaluate_alerts(dep_row, metric):
    if metric not in ALERT_CONFIG:
        return []

    alerts = []
    config = ALERT_CONFIG[metric]

    for key, alert in config.items():
        ok = True
        for col, level in alert["conditions"]:
            series = pd.to_numeric(df[col], errors="coerce")
            value = pd.to_numeric(dep_row[col], errors="coerce")

            if level == "low" and not is_low(value, series):
                ok = False
            if level == "high" and not is_high(value, series):
                ok = False

        if ok:
            alerts.append(alert)

    return alerts
def warning_color(n):
    if n == 1:
        return "beige"
    elif n == 2:
        return "orange"
    elif n >= 3:
        return "red"
    return None

def get_department_alerts(dep_code, metric):
    dep_code = str(dep_code).lstrip("0")
    df["dep_norm"] = df["departement"].astype(str).str.lstrip("0")
    row = df[df["dep_norm"] == dep_code]

    if row.empty:
        return []

    row = row.iloc[0]
    alerts = []

    for alert_id, alert in ALERT_CONFIG.get(metric, {}).items():
        valid = True
        for col, direction in alert["conditions"]:
            if col not in df.columns:
                valid = False
                break

            series = pd.to_numeric(df[col], errors="coerce")
            value = pd.to_numeric(row[col], errors="coerce")

            if pd.isna(value):
                valid = False
                break

            if direction == "low" and value > series.quantile(0.25):
                valid = False
            if direction == "high" and value < series.quantile(0.75):
                valid = False

        if valid:
            alerts.append(alert)

    return alerts

def diagnostic_color(nb_tw):
    if nb_tw == 0:
        return "#2ecc71"  # vert
    elif nb_tw <= 2:
        return "#f1c40f"  # jaune
    elif nb_tw <= 4:
        return "#e67e22"  # orange
    else:
        return "#e74c3c"  # rouge

def compute_axis_score(dep_row, cols):
    z_scores = []

    for col in cols:
        mean = df[col].mean()
        std = df[col].std()

        if std == 0 or pd.isna(std):
            continue

        z = (dep_row[col] - mean) / std
        z_scores.append(z)

    if len(z_scores) == 0:
        return 0

    return np.mean(z_scores)

def spider_chart(dep_row):
    axes = {
        "Sanitaire": ["access_med_generalistes", "MAL_CHRO_Oui"],
        "Économique": ["taux de pauvreté au seuil de 60%", "aspa_effectif_2024"],
        "Social": ["60_75_plus_isoles", "60_75_plus_sans_voiture"]
    }

    dep_scores = []
    nat_scores = []

    for cols in axes.values():
        dep_vals = []
        nat_vals = []

        for col in cols:
            series = df[col].dropna()
            if series.empty:
                continue

            min_val = series.min()
            max_val = series.max()
            nat_mean = series.mean()

            if max_val == min_val:
                continue

            dep_norm = (dep_row[col] - min_val) / (max_val - min_val)
            nat_norm = (nat_mean - min_val) / (max_val - min_val)

            dep_vals.append(dep_norm)
            nat_vals.append(nat_norm)

        dep_scores.append(np.mean(dep_vals))
        nat_scores.append(np.mean(nat_vals))

    labels = list(axes.keys())

    fig = go.Figure()

    # Département
    fig.add_trace(go.Scatterpolar(
        r=dep_scores,
        theta=labels,
        fill="toself",
        name="Département",
        line=dict(color="#778873", width=2),
        fillcolor="rgba(161, 188, 152, 0.6)"
    ))

    # Moyenne nationale
    fig.add_trace(go.Scatterpolar(
        r=nat_scores,
        theta=labels,
        fill="toself",
        name="Moyenne nationale",
        line=dict(color="lightgrey", width=1),
        fillcolor="rgba(241, 243, 224, 0.8)"
    ))

    fig.update_layout(
        polar=dict(
            bgcolor="#F1F3E0",
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                tickvals=[0, 0.5, 1],
                ticktext=["Faible", "Moyen", "Élevé"],
                gridcolor="#D2DCB6"
            ),
            angularaxis=dict(
                gridcolor="#D2DCB6"
            )
        ),
        paper_bgcolor="#F1F3E0",
        plot_bgcolor="#F1F3E0",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            xanchor="center",
            x=0.5
        ),
        height=300,
        margin=dict(l=20, r=20, t=20, b=20)
    )

    return fig



# -------------------------------------------------------------------------------
# CHARGEMENTS & CONFIG
GEO_PATH = Path("departements.geojson")
if not GEO_PATH.exists():
    st.error(f"departements.geojson introuvable : {GEO_PATH.resolve()}")
    st.stop()

geojson_raw = json.loads(GEO_PATH.read_text(encoding="utf-8"))

# listes & mappages (tu avais déjà tout ça)
metropole_codes = [
    "01","02","03","04","05","06","07","08","09","10","11","12","13","14","15","16","17","18","19","21",
    "22","23","24","25","26","27","28","29","2A","2B","30","31","32","33","34","35","36","37","38","39",
    "40","41","42","43","44","45","46","47","48","49","50","51","52","53","54","55","56","57","58","59",
    "60","61","62","63","64","65","66","67","68","69","70","71","72","73","74","75","76","77","78","79",
    "80","81","82","83","84","85","86","87","88","89","90","91","92","93","94","95"
]

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

nom_to_code = {v: k for k, v in code_to_nom.items()}

@st.cache_data(show_spinner="Chargement des données…")
def load_df():
    return pd.read_csv(
        "resultat_final.csv",
        encoding="utf-8-sig",
        low_memory=False
    )

df = load_df()


ALERT_CONFIG = {

    # ============================
    # MÉTRIQUE : NOMBRE MALADIES
    # ============================
    "nombre maladies par personnes": {

        "A": {
            "label": "Désertification Médicale Critique",
            "conditions": [
                ("access_med_generalistes", "low"),
                ("MAL_CHRO_Oui", "high")
            ],
            "explanation": "Forte charge de maladies chroniques avec faible accès aux médecins",
            "action": "Déploiement de cabines de téléconsultation assistée"
        },

        "B": {
            "label": "Risque de Rupture du Maintien à Domicile",
            "conditions": [
                ("aide_menagere_personnes_agees", "low"),
                ("dont part des 75 ans ou plus (en %)", "high")
            ],
            "explanation": "Population très âgée avec peu d’aides à domicile",
            "action": "Renforcer les services d’aide à domicile"
        },

        "C": {
            "label": "Fragilité Préventive",
            "conditions": [
                ("Grippe 65 ans et plus", "low"),
                ("Part des 60 ans ou plus (en %)", "high")
            ],
            "explanation": "Population âgée insuffisamment protégée",
            "action": "Renforcer les campagnes de prévention"
        }
    },

    # ============================
    # MÉTRIQUE : PAUVRETÉ
    # ============================
    "taux_pauvrete_calcul": {

        "A": {
            "label": "Précarité Locative",
            "conditions": [
                ("aspa_effectif_2024", "high"),
                ("60_75_plus_proprietaires", "low")
            ],
            "explanation": "Faible patrimoine et reste à vivre réduit",
            "action": "Renforcement du Fonds de Solidarité Logement Seniors"
        },

        "B": {
            "label": "Renoncement aux Soins",
            "conditions": [
                ("access_med_generalistes", "low"),
                ("taux de pauvreté au seuil de 60%", "high")
            ],
            "explanation": "Barrières financières et géographiques cumulées",
            "action": "Aides au transport et remboursement de trajets médicaux"
        },

        "C": {
            "label": "Paupérisation Structurelle",
            "conditions": [
                ("aspa_effectif_2024", "high"),
                ("dont part des 75 ans ou plus (en %)", "high")
            ],
            "explanation": "Vieillissement et appauvrissement simultanés",
            "action": "Révision des dotations de l’État"
        }
    },

    # ============================
    # MÉTRIQUE : ISOLEMENT
    # ============================
    "60_75_plus_isoles": {

        "A": {
            "label": "Enfermement Rural",
            "conditions": [
                ("60_75_plus_isoles", "high"),
                ("60_75_plus_sans_voiture", "high")
            ],
            "explanation": "Isolement social et impossibilité de mobilité",
            "action": "Dispositifs de lien social et visites à domicile"
        },

        "B": {
            "label": "Exclusion Numérique",
            "conditions": [
                ("60_75_plus_isoles", "high"),
                (" Score de fragilité numérique senior", "high")
            ],
            "explanation": "Personnes isolées et invisibles administrativement",
            "action": "Conseillers numériques itinérants"
        },

        "C": {
            "label": "Enclavement Sanitaire",
            "conditions": [
                ("access_med_generalistes", "low"),
                ("60_75_plus_sans_voiture", "high")
            ],
            "explanation": "Accès aux soins physiquement impossible",
            "action": "Navettes communales et transport solidaire"
        }
    }
}


GRAPH_OPTIONS = [
    "Top 5 maladies chez ≥ 65 ans",
    "Profil social 60–74 ans",
    "Part des 60 ans ou plus",
    "Radar santé (6 variables)",
    "Espérance de vie",
    "Part sans voiture",
    "Fragilité numérique",
    "Offre de services médico-sociaux",
    "Taux de vaccination",
    "Face à face médecins / vieillissement",
    "Isolement social",
    "Propriétaires vs Locataires",
    #"Revenus",
    "ASPA",
    "LIVIA"
    #"Nombre projeté de seniors",
    #"Nombre projeté de seniors en dépendance sévère"
]

if "selected_graphs" not in st.session_state:
    st.session_state["selected_graphs"] = GRAPH_OPTIONS[:3]

st.set_page_config(page_title="France - départements colorés ", layout="wide")
if "selected_graphs" not in st.session_state:
    st.session_state.selected_graphs = GRAPH_OPTIONS[:3]

if "selected_dep" not in st.session_state:
    st.session_state.selected_dep = "91"   # Essonne par défaut


#--------------------------------------------------------------------------------

st.sidebar.title("Nos liens et contacts")

# Sources
st.sidebar.markdown("#### Sources")
st.sidebar.markdown("[Source 1](https://opendata.caissedesdepots.fr/explore/dataset/75-ans-et-plus-indicateurs-de-vieillissement-par-departement/information/?sort=reg_code#localisation-des-75-ans-et-plus)")
st.sidebar.markdown("[Source 2](https://data.drees.solidarites-sante.gouv.fr/explore/dataset/enquete-vie-quotidienne-et-sante-2021-donnees-detaillees/information/)")
st.sidebar.markdown("[Source 3](https://opendata.caissedesdepots.fr/explore/dataset/60-et-plus_indicateurs-au-niveau-de-la-commune/table/#hbergement-des-60-ans-et-plus)")

# Contact
st.sidebar.markdown("#### Contact")
st.sidebar.markdown("[Email](mailto:datavislattitudescpes@gmail.co)")

# LinkedIn des membres
st.sidebar.markdown("#### LinkedIn des membres")
st.sidebar.markdown("[BENRABH Hanae](https://www.linkedin.com/in/hanae-c%C3%A9line-benrabh-3a4b04326/)")
st.sidebar.markdown("[Nammous Othmane](https://www.linkedin.com/in/othmane-nammous-400330297/)")
st.sidebar.markdown("[Gaspalou Charlotte](https://www.linkedin.com/in/charlotte-gaspalou-367b84347/)")
st.sidebar.markdown("[RAVELOMANANA GONZALO Charlotte](https://www.linkedin.com/in/charlotte-ravelomanana-gonzalo-1b974830b/)")
st.sidebar.markdown("[Joly Tristan](https://www.linkedin.com/in/tristan-joly-10179034a/)")

# GitHub
st.sidebar.markdown("#### GitHub")
st.sidebar.markdown("[Notre GitHub](https://github.com/TristanJoly/Lattitudes_cartes/)")

#-------------------------------------------------------------------------------
apply_external_css("style_2.css")
st.title("Mapsentor")

# -------------------------------------------------------------------------------
# detect geo_key early (nécessaire pour filtrage des features)
geo_key = detect_geo_key(geojson_raw, df["departement"].tolist())
if not geo_key:
    st.error("Impossible de détecter la propriété GeoJSON contenant les codes de département. Affiche un feature pour debug.")
    st.json(geojson_raw.get("features", [])[0].get("properties", {}))
    st.stop()


metropole_set = {c.upper() for c in metropole_codes}
feats = []
for f in geojson_raw.get("features", []):
    code = feature_code_str(f, geo_key)
    if code is None:
        continue
    s = code.upper()
    keep = False
    if s in metropole_set:
        keep = True
    else:
        try:
            if str(int(s)).zfill(2) in metropole_set:
                keep = True
        except Exception:
            pass
        if s.lstrip("0") in {c.lstrip("0") for c in metropole_set}:
            keep = True
    if keep:
        feats.append(f)
if not feats:
    geojson = geojson_raw
else:
    geojson = {"type": "FeatureCollection", "features": feats}

# -------------------------------------------------------------------------------
# Calculs géométriques (centre/bounds)
all_lons, all_lats = [], []
for f in geojson.get("features", []):
    geom = f.get("geometry", {})
    pts = extract_coords(geom)
    for lon, lat in pts:
        try:
            all_lons.append(float(lon))
            all_lats.append(float(lat))
        except Exception:
            pass

if all_lats and all_lons:
    min_lat, max_lat = min(all_lats), max(all_lats)
    min_lon, max_lon = min(all_lons), max(all_lons)
    center = [(min_lat + max_lat) / 2, (min_lon + max_lon) / 2]
    bounds = [[min_lat, min_lon], [max_lat, max_lon]]
else:
    center = [46.6, 2.4]
    bounds = [[41.0, -5.0], [51.5, 10.5]]

warning_columns = {
    "Grippe 65-74 ans": "Grippe 65–74 ans",
    "Grippe 75 ans et plus": "Grippe 75+",
    "Covid-19 65 ans et plus": "Covid-19 65+",
    "nombre maladies par personnes": "Maladies / urgences"
}

# Calcul des seuils des 25 %
warning_thresholds = {}
for col in warning_columns.keys():
    if col in df.columns:
        vals = pd.to_numeric(df[col], errors="coerce").dropna()
        warning_thresholds[col] = vals.quantile(0.25)
    else:
        warning_thresholds[col] = None
def department_has_warning(feature):
    props = feature.get("properties") or {}
    code_raw = props.get(geo_key) or props.get("code") or props.get("id")
    if code_raw is None:
        return False, []

    dep_code = str(code_raw).strip().lstrip("0")
    df["dep_norm"] = df["departement"].astype(str).str.lstrip("0")

    row = df[df["dep_norm"] == dep_code]
    if row.empty:
        return False, []

    row = row.iloc[0]
    triggered = []

    for col, label in warning_columns.items():
        threshold = warning_thresholds.get(col)
        if threshold is None:
            continue

        val = pd.to_numeric(row.get(col), errors="coerce")
        if pd.notna(val) and val <= threshold:
            triggered.append(label)

    return len(triggered) > 0, triggered

# ---------- U ----------
col_metric, col_dep = st.columns([1, 1])

with col_metric:
    metric = st.selectbox(
        "Choisir la métrique :",
        [
            "60_75_plus_isoles",
            "taux_pauvrete_calcul",
            "nombre maladies par personnes",
        ],
        key="metric_select"
    )

with col_dep:
    dep_list = df["departement"].astype(str).tolist()

    selected_box_value = st.selectbox(
        "Choisir un département :",
        options=dep_list,
        index=dep_list.index(st.session_state.selected_dep)
        if st.session_state.selected_dep in dep_list
        else 0,
        key="dep_selectbox_main"
    )

    # synchronisation directe
    st.session_state.selected_dep = selected_box_value


# ---------- 
value_by_code = (
    df.set_index("departement")[metric]
    .apply(pd.to_numeric, errors="coerce")
    .to_dict()
)

value_by_code_nozero = {
    k.lstrip("0"): v for k, v in value_by_code.items()
}



values = (
    pd.to_numeric(pd.Series(value_by_code.values()), errors="coerce")
    .dropna()
)

if values.empty:
    st.error("Aucune valeur valide pour la colormap")
    st.stop()

vmin = float(values.min())
vmax = float(values.max())

if vmin == vmax:
    vmax = vmin + 1e-6  # évite colormap dégénérée

colormap = cm.LinearColormap(
    ["#F1F3E0", "#D2DCB6", "#A1BC98", "#778873"],
    vmin=vmin,
    vmax=vmax
)
colormap.caption = metric

if "selected_dep" not in st.session_state:
    st.session_state["selected_dep"] = None
if "expanded_chart" not in st.session_state:
    st.session_state["expanded_chart"] = None  # identifiant du graphique agrandi

st.markdown("""
    <style>
        .folium-map { background-color: transparent !important; }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------------------------
# fonctions style / tooltip pour GeoJson
def style_function(feature):
    props = feature.get("properties") or {}
    code_raw = props.get(geo_key) or props.get("code") or props.get("id")
    if code_raw is None:
        fill = "#eeeeee"
        code_s = ""
    else:
        code_s = str(code_raw).strip()
        val = value_by_code.get(code_s)
        if val is None:
            val = value_by_code_nozero.get(code_s.lstrip("0"))
        try:
            if val is None or pd.isna(val):
                fill = "#f0f0f0"
            else:
                val = float(val)
                val = max(vmin, min(vmax, val))  # clamp
                fill = colormap(val)
        except Exception:
            fill = "#f0f0f0"
    if st.session_state.get("selected_dep") and str(code_s).strip() == str(st.session_state.get("selected_dep")).strip():
        return {"fillColor": fill, "color": "#A1BC98", "weight": 3, "fillOpacity": 0.9}
    else:
        return {"fillColor": fill, "color": "#778873", "weight": 1.0, "fillOpacity": 0.7}



# -------------------------------------------------------------------------------
# Créer la carte Folium (m)
m = folium.Map(
    location=center,
    zoom_start=8,
    min_zoom=6,
    max_zoom=14,
    tiles=None,
    control_scale=True,
    prefer_canvas=True,
    attr=""
)
m.fit_bounds(bounds, padding=(50, 50))  # padding en pixels


# GeoJson layer + tooltip
gj = folium.GeoJson(
    geojson,
    name="departements",
    style_function=style_function,
    highlight_function=lambda feat: {"weight": 3,"color": "#A1BC98","fillOpacity": 0.9},
    tooltip=folium.GeoJsonTooltip(
        fields=[geo_key, 'nom'] if any('nom' in (f.get("properties") or {}) for f in geojson.get("features", [])) else [geo_key],
        aliases=["code", "nom"] if any('nom' in (f.get("properties") or {}) for f in geojson.get("features", [])) else ["code"],
        localize=True
    )
)
gj.add_to(m)
colormap.add_to(m)
current_metric = metric  # metric vient de ton selectbox

for feature in geojson.get("features", []):
    props = feature.get("properties") or {}
    code_raw = props.get(geo_key)
    if not code_raw:
        continue

    dep_code = str(code_raw).lstrip("0")
    df["dep_norm"] = df["departement"].astype(str).str.lstrip("0")
    row = df[df["dep_norm"] == dep_code]

    if row.empty:
        continue

    dep_row = row.iloc[0]
    alerts = evaluate_alerts(dep_row, current_metric)

    if not alerts:
        continue

    coords = extract_coords(feature.get("geometry"))
    if not coords:
        continue

    lons, lats = zip(*coords)
    center_lat = sum(lats) / len(lats)
    center_lon = sum(lons) / len(lons)

    tooltip = "<b>⚠️ Alertes déclenchées</b><br>"
    for a in alerts:
        tooltip += f"""
        <b>{a['label']}</b><br>
        {a['explanation']}<br>
        <i>Levier :</i> {a['action']}<br><br>
        """

    folium.Marker(
            location=[center_lat, center_lon],
            icon=folium.Icon(
                icon="exclamation-triangle",
                prefix="fa",
                color=warning_color(len(alerts))
            ),
            tooltip=tooltip
        ).add_to(m)


m.fit_bounds(bounds)
m.options["maxBounds"] = bounds

# JS injection to keep transparency/minZoom (tu avais déjà ça)
from branca.element import Element
map_var_name = m.get_name()
script = Element(f"""
<script>
(function() {{
  try {{
    var map = {map_var_name};
    if (!map) return;
    var currentZoom = map.getZoom();
    map.options.minZoom = currentZoom;
    if (typeof map.setMinZoom === 'function') {{ map.setMinZoom(currentZoom); }}
    map.on('zoomend', function() {{ if (map.getZoom() < map.options.minZoom) {{ map.setZoom(map.options.minZoom); }} }});
    var container = map.getContainer();
    if (container && container.style) {{ container.style.background = 'transparent'; }}
    var panes = container.getElementsByClassName('leaflet-pane');
    for (var i = 0; i < panes.length; i++) {{ panes[i].style.background = 'transparent'; }}
    var foliumMapDivs = document.getElementsByClassName('folium-map');
    for (var j = 0; j < foliumMapDivs.length; j++) {{ foliumMapDivs[j].style.background = 'transparent'; }}
  }} catch (e) {{ console.warn('JS injection pour map transparent/minZoom failed', e); }}
}})();
</script>
""")
m.get_root().html.add_child(script)

st.markdown("""
    <style>
      iframe[title^="folium"] { background: transparent !important; }
      .folium-map, .leaflet-container { background: transparent !important; }
      .stFrame iframe { background: transparent !important; }
    </style>
""", unsafe_allow_html=True)

st.write("Clique sur un département pour voir ses infos (ou utilise le selectbox fallback).")

# ---------------- Layout : map left, charts right ----------------

col_map, col_right  = st.columns([1, 1])

with col_map:



    
    # --- Carte interactive ---
    
    output = st_folium(
    m,
    width="100%",  # pleine largeur de la colonne
    height=700
)

    clicked = extract_dept_from_output(output, geo_key)

    # --- Gestion du clic sur la carte ---
    if clicked:
        clicked_norm = clicked.strip()
        try:
            if clicked_norm.isdigit():
                clicked_norm = str(int(clicked_norm)).zfill(2)
        except Exception:
            pass

        st.session_state.selected_dep = clicked_norm

        ## --- Encadré alertes pour le département sélectionné ---
    
    # ------------------- Encadré infos département -------------------
    

            
with col_right :
    
    selected_dep_code = st.session_state.get("selected_dep")
    if selected_dep_code == None :
        selected_dep = "Essonne"
    dep_row = df[df["departement"].astype(str).str.lstrip("0") == str(selected_dep_code).lstrip("0")]

    


    # --- Nom du département ---
    if not dep_row.empty:
        dep_code = str(selected_dep_code).zfill(2)
        dep_name = code_to_nom.get(dep_code, dep_row["departement"].values[0])

        st.markdown(
            f"""
            <div style="
                background-color:#F1F3E0;
                padding:12px 20px;
                border-radius:10px;
                font-size:24px;
                font-weight:600;
                color:#778873;
                margin-bottom:15px;
                text-align:center;
            ">
                {dep_name} <span style="font-size:16px; color:#A1BC98;">({dep_code})</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.subheader("Informations clés du département")
    if not dep_row.empty:
        # ===================== Encadré “Infos clés” avec unités =====================
        metrics_to_show = {
            "total_seniors": "Total seniors",
            "EHPAD_nb_lits": "Nb lits EHPAD",
            "Niveau de vie médian des ménages (en euros)": "Revenu médian"
        }

        # Unités correspondantes
        metrics_units = {
            "total_seniors": "personnes agées",
            "EHPAD_nb_lits": "lits dans les ephad",
            "Niveau de vie médian des ménages (en euros)": "€"
        }


        # Créer 4 colonnes
        cols = st.columns(4)

        for i, (col_name, label) in enumerate(metrics_to_show.items()):
            col = cols[i % 4]  # on boucle sur les colonnes si moins de 4 metrics
            if col_name in df.columns:
                val = dep_row[col_name] if not isinstance(dep_row[col_name], pd.Series) else dep_row[col_name].values[0]
                unit = metrics_units.get(col_name, "")

                # Définir ordre pour le classement
                ascending = False if col_name == "Niveau de vie médian des ménages (en euros)" else True

                # Colonne de valeurs à classer
                values = pd.to_numeric(df[col_name], errors="coerce")  # Seulement la colonne des valeurs
                values.index = df["code_departement"]  # Peut contenir "2A", "2B", etc.

                # Supprimer les NaN
                values_clean = values.dropna()

                # Département cible (y compris Corse)
                dep = "2A"

                # Calcul du rang
                if dep in values_clean.index:
                    rank = int(values_clean.rank(ascending=ascending, method="min")[dep])
                else:
                    rank = None

                total_depts = 96  # France métropolitaine + Corse

                # HTML pour affichage propre
                html = f"""
                <div style="
                    background-color: #F1F3E0;
                    padding: 15px;
                    border-radius: 10px;
                    text-align: center;
                    height: 140px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                ">
                    <div style="font-size: 28px; font-weight: bold; color: #778873;">{val} {unit}</div>
                    <div style="font-size: 14px; color: #555; margin-top: 5px;">{label}</div>
                    <div style="font-size: 12px; color: #A1BC98; text-align: right; margin-top: 10px;">
                        Rang: {rank} / {total_depts}
                    </div>
                </div>
                """
                col.markdown(html, unsafe_allow_html=True)


    col_spider, col_alerts = st.columns([1, 1])
    with col_spider:
        if not dep_row.empty:
            st.markdown("###  Profil global")
            fig_spider = spider_chart(dep_row)
            st.plotly_chart(
                fig_spider,
                use_container_width=True,
                config={"displayModeBar": False}
            )


    with col_alerts:
        if not dep_row.empty:
            dep_row = dep_row.iloc[0]
            # Récupération de toutes les alertes déclenchées toutes métriques confondues
            all_alerts = []
            for metric, config in ALERT_CONFIG.items():
                alerts = get_department_alerts(dep_row["departement"], metric)
                all_alerts.extend(alerts)

            # Nombre d'alertes détectées
            nb_alertes = len(all_alerts)

            # Choix dynamique de la couleur selon le nombre d'alertes
            if nb_alertes <= 2:
                border_color = "#f1c40f"  # jaune
                bg_color = "#fef9e7"
            elif nb_alertes <= 4:
                border_color = "#e67e22"  # orange
                bg_color = "#fdf2e9"
            else:
                border_color = "#e74c3c"  # rouge
                bg_color = "#fdecea"

            # Construction du HTML
            alert_html = f"<b>{nb_alertes} alerte(s) détectée(s)</b><br><br>"
            for alert in all_alerts:
                alert_html += f"""
                <div style="margin-bottom:5px;">
                    ⚠️ <b>{alert['label']}</b><br>
                    🔧 Levier d'action : {alert['action']}
                </div>
                """

            # Affichage avec encadré dynamique
            st.markdown(
                f"""
                <div style="
                    border:2px solid {border_color}; 
                    padding:10px; 
                    border-radius:8px; 
                    background-color:{bg_color};
                ">
                    {alert_html}
                </div>
                """,
                unsafe_allow_html=True
            )



st.markdown("---")

with st.expander("📈 Graphiques détaillés du département", expanded=False):
             
    selected = st.session_state.get("selected_dep")
    sel_row = None

    # Normalisation : enlever espaces et mettre en majuscule
    df["dep_norm"] = df["departement"].astype(str).str.strip().str.upper()

    if selected:
        s = str(selected).strip().upper()
        if s in df["dep_norm"].values:
            sel_row = df[df["dep_norm"] == s].iloc[0]
        else:
            # fallback vers l'Essonne
            if "Essonne" in df["dep_norm"].values:
                sel_row = df[df["dep_norm"] == "Essonne"].iloc[0]
    else:
        # fallback si aucun selected_dep
        if "E" in df["dep_norm"].values:
            sel_row = df[df["dep_norm"] == "Essonne"].iloc[0]

    national_means = {}
    for col in [
        "Taux de pauvrete pour plus de 75 ans",
        "Population",
        "Niveau de vie médian des ménages (en euros)",
        "Part des femmes (en %)",
        "Part des 60 ans ou plus (en %)",
        "dont part des 75 ans ou plus (en %)"
    ]:
        if col in df.columns:
            national_means[col] = float(df[col].dropna().astype(float).mean())
        else:
            national_means[col] = None

    # --- Initialisation safe




    # --- Multiselect avec default tiré de session_state
    st.multiselect(
    "Choisissez jusqu'à 3 graphiques à afficher :",
    options=GRAPH_OPTIONS,
    max_selections=3,
    key="selected_graphs"
)





    plot_config = {"displayModeBar": True, "scrollZoom": True, "displaylogo": False}

    
    metric_map_right = [
        "Taux de pauvrete pour plus de 75 ans",  
        "Part des 60 ans ou plus (en %)",       
        "Niveau de vie médian des ménages (en euros)"  
    ]

    
    selected_charts = []

    
    

    
    # --- Graphique 1 
    fig1 = go.Figure()

    PREFIXE_65 = "≥ 65 ans" 
    maladies_65 = [col for col in df.columns if col.startswith(PREFIXE_65) and "Total" not in col]


    if sel_row is not None:
        values_before_conversion = sel_row[maladies_65]

        values = pd.to_numeric(values_before_conversion, errors="coerce")
        values = values.dropna()

        if len(values) > 0:
            top5 = values.sort_values(ascending=False).head(5)

            fig1.add_trace(go.Bar(
                x=top5.values,
                y=[m.replace("≥ 65 ans - ", "") for m in top5.index],
                orientation="h",
                marker=dict(color="#778873")
            ))

            fig1.update_layout(
                title=f"Top 5 maladies chez les ≥ 65 ans – {sel_row['departement']}",
                margin=dict(l=10, r=10, t=40, b=10),
                height=300,paper_bgcolor="#F1F3E0",plot_bgcolor="#F1F3E0"
            )
        else:
            fig1 = px.bar(x=["Pas de données"], y=[0], height=300)

    else:
        fig1 = px.bar(x=["Aucune sélection"], y=[0], height=300)

    if "Top 5 maladies chez ≥ 65 ans" in st.session_state.selected_graphs:
        selected_charts.append(fig1)




    # =============== GRAPHIQUE 2 : RADAR 60–74 ANS ==================

    radar_vars = [
        "60_74_menage_peu_diplome",
        "60_74_menage_immigre",
        "60_74_proprietaires",
        "femmes_60_74_isolees",
        "60_74_sans_voiture"
    ]
    
    theta_labels = [
        "Peu diplômés",
        "Ménages immigrés",
        "Propriétaires",
        "Femmes isolées",
        "Sans voiture"
    ]
    theta_labels = [str(x) for x in theta_labels]


    fig2 = go.Figure()

    if sel_row is not None:

        vals = (
            pd.to_numeric(sel_row[radar_vars], errors="coerce")
            .fillna(0)
            .astype(float)     
            .tolist()
        )


        fig2.add_trace(go.Scatterpolar(
            r=vals,
            theta=theta_labels,
            fill='toself',
            name=str(sel_row["departement"]),  # éviter pd.NA
            line=dict(color="#778873"),
            fillcolor="#A1BC98"
        ))



        fig2.update_layout(
            title="Profil social 60–74 ans",
            polar=dict(radialaxis=dict(visible=True)),
            margin=dict(l=10, r=10, t=40, b=10),
            height=300,paper_bgcolor="#F1F3E0",plot_bgcolor="#F1F3E0"
        )
    else:
        fig2.add_trace(go.Scatterpolar(r=[1], theta=["Aucune sélection"], fill="toself"))
        fig2.update_layout(height=300)

    if "Profil social 60–74 ans" in st.session_state.selected_graphs:
        selected_charts.append(fig2)



    # =============== GRAPHIQUE 3 : CAMEMBERT PART DES 60+ ==================

    fig3 = go.Figure()

    if sel_row is not None:
        part60 = float(sel_row["Part des 60 ans ou plus (en %)"])
        reste = max(0, 100 - part60)

        fig3.add_trace(go.Pie(
            labels=[f"60+ ({part60}%)", "Autres"],  
            values=[part60, reste],                   
            hole=0.4,
            marker=dict(colors=["#778873", "#D2DCB6"])
        ))

        fig3.update_layout(
            title="Part des 60 ans ou plus",
            margin=dict(l=10, r=10, t=40, b=10),
            height=220,
            paper_bgcolor="#F1F3E0",
            plot_bgcolor="#F1F3E0"
        )
    else:
        fig3.add_trace(go.Pie(labels=["Aucune sélection"], values=[1], hole=0.4))
        fig3.update_layout(
            title="Part des 60 ans ou plus",
            margin=dict(l=10, r=10, t=40, b=10),
            height=220,
            paper_bgcolor="#F1F3E0",
            plot_bgcolor="#F1F3E0"
        )

    if "Part des 60 ans ou plus" in st.session_state.selected_graphs:
        selected_charts.append(fig3)

# =============== GRAPHIQUE 4 : RADAR SANTÉ (6 VARIABLES) ==================
    radar6_vars_raw = {
        "VUE_1 - Beaucoup de difficultés ou ne peut pas du tout": "Vue",
        "MAL_CHRO_Oui": "Maladies chroniques",
        "LFPHYSIQUES_Oui": "Limitations physiques",
        "AUDITIF_1 - Beaucoup de difficultés ou ne peut pas du tout": "Auditif",
        "HANDICAP_Oui": "Handicap déclaré",
        "ETAT_SANT_4 - Mauvais ou très mauvais": "Mauvais état de santé"
    }

    fig4 = go.Figure()

    if sel_row is not None:
        vals_dep = pd.to_numeric(sel_row[list(radar6_vars_raw.keys())], errors="coerce").fillna(0).tolist()

        vals_nat = df[list(radar6_vars_raw.keys())].apply(pd.to_numeric, errors="coerce").mean().fillna(0).tolist()

        labels = list(radar6_vars_raw.values())

        fig4.add_trace(go.Scatterpolar(
            r=vals_dep,
            theta=labels,
            fill='toself',
            name=f"{sel_row['departement']}",
            line=dict(color="#778873"),
            fillcolor="#A1BC98"
        ))

        fig4.add_trace(go.Scatterpolar(
            r=vals_nat,
            theta=labels,
            fill='toself',
            name="France",
            line=dict(color="lightgrey", width=1),
            fillcolor="rgba(241, 243, 224, 0.7)", 
            opacity=0.8 
        ))


        fig4.update_layout(
            title="Radar santé – difficultés et limitations",
            polar=dict(radialaxis=dict(visible=True)),
            margin=dict(l=10, r=10, t=40, b=10),
            height=320,paper_bgcolor="#F1F3E0",plot_bgcolor="#F1F3E0"
        )
    else:
        fig4.add_trace(go.Scatterpolar(r=[1], theta=["Aucune sélection"], fill="toself"))
        fig4.update_layout(height=300)

    if "Radar santé (6 variables)" in st.session_state.selected_graphs:
        selected_charts.append(fig4)


# =============== GRAPHIQUE 5 : ESPÉRANCE DE VIE ==================

    fig5 = go.Figure()

    if sel_row is not None:
        esp = sel_row["esp"]

        fig5.add_annotation(
            x=0.5,
            y=0.5,
            text=f"<b>{esp:.1f} ans</b>",
            showarrow=False,
            font=dict(size=40, color="#778873")
        )


        fig5.update_layout(
            title="Espérance de vie",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            margin=dict(l=10, r=10, t=40, b=10),
            height=220,paper_bgcolor="#F1F3E0",plot_bgcolor="#F1F3E0"
        )
    else:
        fig5.add_annotation(x=0.5, y=0.5, text="Aucune sélection", showarrow=False)
        fig5.update_layout(height=200)

    if "Espérance de vie" in st.session_state.selected_graphs:
        selected_charts.append(fig5)

#--------------------------------------------------------------------------------------------

    fig_voiture = go.Figure()

    if sel_row is not None:
        total_60_74 = (
            sel_row["Femmes_60_74_ans"] +
            sel_row["Hommes_60_74_ans"]
        )

        total_75_plus = (
            sel_row["Femmes_75_ans_et_plus"] +
            sel_row["Hommes_75_ans_et_plus"]
        )

        part_60_74 = (
            sel_row["60_74_sans_voiture"] / total_60_74 * 100
            if total_60_74 > 0 else 0
        )

        part_75_plus = (
            sel_row["75_plus_sans_voiture"] / total_75_plus * 100
            if total_75_plus > 0 else 0
        )

        fig_voiture.add_trace(go.Bar(
            x=["60–74 ans", "75 ans et plus"],
            y=[part_60_74, part_75_plus],
            text=[f"{part_60_74:.1f} %", f"{part_75_plus:.1f} %"],
            textposition="auto",
            marker_color=["#9BB07C", "#778873"]
        ))

        fig_voiture.update_layout(
            title="Part des personnes sans voiture par âge",
            yaxis_title="Pourcentage (%)",
            yaxis_range=[0, 100],
            margin=dict(l=20, r=20, t=50, b=20),
            height=300,
            paper_bgcolor="#F1F3E0",
            plot_bgcolor="#F1F3E0"
        )

    else:
        fig_voiture.add_annotation(
            x=0.5, y=0.5,
            text="Aucune sélection",
            showarrow=False
        )
        fig_voiture.update_layout(height=300)

    if "Part sans voiture" in st.session_state.selected_graphs:
         selected_charts.append(fig_voiture)
#--------------------------------------------------------------------------------------

    fig_fragilite = go.Figure()

    if sel_row is not None:
        score = sel_row[" Score de fragilité numérique senior"]

        fig_fragilite.add_trace(go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "", "font": {"size": 28}},
            title={"text": "Fragilité numérique des seniors", "font": {"size": 18}},
            gauge={
                "axis": {
                    "range": [0, 10],
                    "tickwidth": 1,
                    "tickcolor": "#666"
                },
                "bar": {"color": "rgba(0,0,0,0)"},  # on cache la barre centrale
                "bgcolor": "#F1F3E0",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 3.3], "color": "#7FB069"},   # vert
                    {"range": [3.3, 6.6], "color": "#F4D35E"}, # jaune
                    {"range": [6.6, 10], "color": "#EE6352"} # rouge
                ],
                "threshold": {
                    "line": {"color": "#2E2E2E", "width": 4},
                    "thickness": 0.75,
                    "value": score
                }
            },
            domain={"x": [0, 1], "y": [0, 1]}
        ))

        fig_fragilite.update_layout(
            height=350,
            margin=dict(l=20, r=20, t=60, b=20),
            paper_bgcolor="#F1F3E0",
            plot_bgcolor="#F1F3E0"
        )

    else:
        fig_fragilite.add_annotation(
            x=0.5, y=0.5,
            text="Aucune sélection",
            showarrow=False
        )
        fig_fragilite.update_layout(height=300)

    if "Fragilité numérique" in st.session_state.selected_graphs:
        selected_charts.append(fig_fragilite)

# -------------------------------------------------------------------------------


    fig_vol_seniors = go.Figure()

    if sel_row is not None:
        # Construire les colonnes pour vol_GLOB
        vol_type = "vol_GLOB"
        sexes = ["F", "H"]  # Retirer "E"
        annees = [2025, 2030, 2035, 2040, 2045, 2050]
        scenarios = ["s1", "s2", "s3"]

        for scenario in scenarios:
            scenario_tracked = False  # Pour s'assurer qu'au moins une ligne existe par scénario
            for sexe in sexes:
                cols = [f"{vol_type}_{scenario}_{sexe}_{annee}" for annee in annees]
                cols_exist = [c for c in cols if c in df.columns]
                if cols_exist:
                    scenario_tracked = True
                    y_vals = pd.to_numeric(sel_row[cols_exist], errors="coerce").fillna(0).tolist()
                    fig_vol_seniors.add_trace(go.Scatter(
                        x=[int(c.split("_")[-1]) for c in cols_exist],
                        y=y_vals,
                        mode="lines+markers",
                        name=f"{scenario.upper()} – { {'F':'Femmes','H':'Hommes'}[sexe] }"
                    ))
            # Si aucune colonne n'existe pour ce scénario
            if not scenario_tracked:
                fig_vol_seniors.add_annotation(
                    x=0.5, y=0.5, 
                    text=f"Aucune donnée pour le scénario {scenario.upper()}", 
                    showarrow=False,
                    font=dict(size=16, color="#778873")
                )

    else:
        fig_vol_seniors.add_annotation(
            x=0.5, y=0.5, text="Aucune sélection", showarrow=False,
            font=dict(size=20, color="#778873")
        )

    fig_vol_seniors.update_layout(
        title=f"Nombre projeté de seniors – Département {sel_row['departement'] if sel_row is not None else ''}",
        xaxis_title="Année",
        yaxis_title="Valeur",
        height=300,
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="#F1F3E0",
        plot_bgcolor="#F1F3E0"
    )

    # Affichage conditionnel via selected_graphs
    if "Nombre projeté de seniors" in st.session_state.selected_graphs:
        selected_charts.append(fig_vol_seniors)


# -------------------------------------------------------------------------------

#-------------------------------------------------------
    fig_diff_scenarios = go.Figure()

    if sel_row is not None:
        # Si sel_row est un DataFrame avec 1 ligne, on le transforme en Série
        if isinstance(sel_row, pd.DataFrame):
            sel_row = sel_row.iloc[0]

        vol_type = "vol_s_GLOB"
        sexes = ["F", "H"]  # Retirer "E"
        annees = [2025, 2030, 2035, 2040, 2045, 2050]
        scenarios = ["s1", "s2", "s3"]
        sex_labels = {'F': 'Femmes', 'H': 'Hommes'}

        for sexe in sexes:
            # Colonnes pour le scénario de référence S1
            base_cols = [f"{vol_type}_s1_{sexe}_{annee}" for annee in annees]
            base_cols_exist = [c for c in base_cols if c in df.columns]
            base_cols_exist = sorted(base_cols_exist, key=lambda x: int(x.split("_")[-1]))
            if not base_cols_exist:
                continue

            base_vals = pd.to_numeric(sel_row[base_cols_exist], errors="coerce").fillna(0).tolist()

            # Boucle sur S2 et S3 pour calculer la différence par rapport à S1
            for scenario in ['s2', 's3']:
                cols = [f"{vol_type}_{scenario}_{sexe}_{annee}" for annee in annees]
                cols_exist = [c for c in cols if c in df.columns]
                cols_exist = sorted(cols_exist, key=lambda x: int(x.split("_")[-1]))
                if cols_exist:
                    y_vals = pd.to_numeric(sel_row[cols_exist], errors="coerce").fillna(0).tolist()
                    diff_vals = [y - b for y, b in zip(y_vals, base_vals)]
                    fig_diff_scenarios.add_trace(go.Scatter(
                        x=[int(c.split("_")[-1]) for c in cols_exist],
                        y=diff_vals,
                        mode="lines+markers",
                        name=f"{scenario.upper()} – {sex_labels[sexe]} (diff S1)"
                    ))

        if not fig_diff_scenarios.data:
            fig_diff_scenarios.add_annotation(
                x=0.5, y=0.5,
                text="Aucune donnée pour ce département",
                showarrow=False,
                font=dict(size=16, color="#778873")
            )
    else:
        fig_diff_scenarios.add_annotation(
            x=0.5, y=0.5,
            text="Aucune sélection",
            showarrow=False,
            font=dict(size=20, color="#778873")
        )

    # Mise en page
    fig_diff_scenarios.update_layout(
        title=f"Differences entre scénarios par rapport à S1 – Département {sel_row['departement'] if sel_row is not None else ''}",
        xaxis_title="Année",
        yaxis_title="Différence",
        height=400,
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="#F1F3E0",
        plot_bgcolor="#F1F3E0"
    )

    # Affichage dans Streamlit
    if "Nombre projeté de seniors en dépendance sévère" in st.session_state.selected_graphs:
        selected_charts.append(fig_diff_scenarios)


#--------------------------------------------------------------------------------------------------------------------------------
    fig_services = go.Figure()

    if sel_row is not None:

        dept = sel_row["departement"]
        region = sel_row["region"]

        services_cols = {
            "Aides à domicile": "APL_SAPA",
            "EHPAD": "APL_EHPA",
            "Médecins généralistes": "access_med_generalistes"
        }

        df_dept = df[df["departement"] == dept]
        df_region = df[df["region"] == region]
        df_nat = df.copy()

        pop_dept = pd.to_numeric(df_dept["Population"], errors="coerce").sum()
        pop_region = pd.to_numeric(df_region["Population"], errors="coerce").sum()
        pop_nat = pd.to_numeric(df_nat["Population"], errors="coerce").sum()

        dept_vals, region_vals = [], []

        for col in services_cols.values():

            dept_rate = (
                pd.to_numeric(df_dept[col], errors="coerce").sum() / pop_dept
                if pop_dept > 0 else 0
            )
            region_rate = (
                pd.to_numeric(df_region[col], errors="coerce").sum() / pop_region
                if pop_region > 0 else 0
            )
            nat_rate = (
                pd.to_numeric(df_nat[col], errors="coerce").sum() / pop_nat
                if pop_nat > 0 else 0
            )

            dept_vals.append(dept_rate / nat_rate if nat_rate > 0 else 0)
            region_vals.append(region_rate / nat_rate if nat_rate > 0 else 0)

        fig_services.add_bar(
            x=list(services_cols.keys()),
            y=dept_vals,
            name="Département"
        )

        fig_services.add_bar(
            x=list(services_cols.keys()),
            y=region_vals,
            name="Région"
        )

    else:
        fig_services.add_annotation(
            x=0.5, y=0.5,
            text="Aucune sélection",
            showarrow=False
        )

    fig_services.update_layout(
        title=f"Indice normalisé de l’offre médico-sociale – {dept} ({region})"
              if sel_row is not None else "",
        yaxis_title="Indice (1 = moyenne nationale)",
        barmode="group",
        height=320,
        paper_bgcolor="#F1F3E0",
        plot_bgcolor="#F1F3E0",
        shapes=[dict(
            type="line",
            x0=-0.5, x1=3.5,
            y0=1, y1=1,
            line=dict(dash="dash", color="gray")
        )]
    )

    if "Offre de services médico-sociaux" in st.session_state.selected_graphs:
        selected_charts.append(fig_services)

#--------------------------------------------------------------------------------------------------------------------------------

    fig_vaccination = go.Figure()

    if sel_row is not None:

        dept = sel_row["departement"]
        region = sel_row["region"]

        # Colonnes à utiliser pour le taux de vaccination / prévention
        vaccination_cols = {
            "Covid 65+": "Covid-19 65 ans et plus",
            "Grippe 65+": "Grippe 65 ans et plus"
        }

        df_dept = df[df["departement"] == dept]
        df_region = df[df["region"] == region]
        df_nat = df.copy()

        dept_vals, region_vals, nat_vals = [], [], []

        for col in vaccination_cols.values():
            # Conversion en numérique si nécessaire
            dept_rate = pd.to_numeric(df_dept[col], errors="coerce").mean()
            region_rate = pd.to_numeric(df_region[col], errors="coerce").mean()
            nat_rate = pd.to_numeric(df_nat[col], errors="coerce").mean()

            dept_vals.append(dept_rate if not pd.isna(dept_rate) else 0)
            region_vals.append(region_rate if not pd.isna(region_rate) else 0)
            nat_vals.append(nat_rate if not pd.isna(nat_rate) else 0)

        fig_vaccination.add_bar(
            x=list(vaccination_cols.keys()),
            y=dept_vals,
            name="Département"
        )

        fig_vaccination.add_bar(
            x=list(vaccination_cols.keys()),
            y=region_vals,
            name="Région"
        )

        fig_vaccination.add_bar(
            x=list(vaccination_cols.keys()),
            y=nat_vals,
            name="France"
        )

    else:
        fig_vaccination.add_annotation(
            x=0.5,
            y=0.5,
            text="Aucune sélection",
            showarrow=False,
            font=dict(size=16, color="#778873")
        )

    fig_vaccination.update_layout(
        title=f"Taux de vaccination / prévention – {dept} ({region})"
              if sel_row is not None else "",
        yaxis_title="Taux (%)",
        barmode="group",
        height=320,
        paper_bgcolor="#F1F3E0",
        plot_bgcolor="#F1F3E0"
    )

    # Ajout du graphique dans la session si sélectionné
    if "Taux de vaccination" in st.session_state.selected_graphs:
        selected_charts.append(fig_vaccination)
#--------------------------------------------------------------------------------------------------------------------------------
    fig_face_a_face = go.Figure()

    if sel_row is not None:

        dept = sel_row["departement"]
        region = sel_row["region"]

        df_dept = df[df["departement"] == dept]
        df_region = df[df["region"] == region]
        df_nat = df.copy()

        offre_col = "access_med_generalistes"
        besoin_col = "dont part des 75 ans ou plus (en %)"

        # Moyennes
        offre_nat = pd.to_numeric(df_nat[offre_col], errors="coerce").mean()
        besoin_nat = pd.to_numeric(df_nat[besoin_col], errors="coerce").mean()

        offre_vals = [
            (pd.to_numeric(df_dept[offre_col], errors="coerce").mean() - offre_nat) / offre_nat * 100,
            (pd.to_numeric(df_region[offre_col], errors="coerce").mean() - offre_nat) / offre_nat * 100
        ]

        besoin_vals = [
            (pd.to_numeric(df_dept[besoin_col], errors="coerce").mean() - besoin_nat) / besoin_nat * 100,
            (pd.to_numeric(df_region[besoin_col], errors="coerce").mean() - besoin_nat) / besoin_nat * 100
        ]

        x_labels = ["Département", "Région"]

        fig_face_a_face.add_bar(
            x=x_labels,
            y=offre_vals,
            name="Offre : Médecins généralistes",
            marker_color="#4C78A8"
        )

        fig_face_a_face.add_bar(
            x=x_labels,
            y=besoin_vals,
            name="Besoins : Part des 75 ans ou +",
            marker_color="#F58518"
        )

        fig_face_a_face.add_hline(
            y=0,
            line_dash="dash",
            line_color="black",
            annotation_text="Moyenne nationale",
            annotation_position="bottom right"
        )

    else:
        fig_face_a_face.add_annotation(
            x=0.5,
            y=0.5,
            text="Aucune sélection",
            showarrow=False,
            font=dict(size=16, color="#778873")
        )

    fig_face_a_face.update_layout(
        title=f"Face-à-face Offre vs Besoins – {dept} ({region})"
              if sel_row is not None else "",
        yaxis_title="Écart à la moyenne nationale (%)",
        barmode="group",
        height=340,
        paper_bgcolor="#F1F3E0",
        plot_bgcolor="#F1F3E0",
        legend_title=""
    )

    if "Face à face médecins / vieillissement" in st.session_state.selected_graphs:
        selected_charts.append(fig_face_a_face)

#--------------------------------------------------------------------------------------------------------------------------------
    
    fig_nested_donut = go.Figure()

    if sel_row is not None:
        # Total seniors et isolés
        total = pd.to_numeric(sel_row["total_seniors"], errors="coerce")
        isoles = pd.to_numeric(sel_row["60_75_plus_isoles"], errors="coerce")
        non_isoles = total - isoles

        # Parmi les isolés, femmes vs hommes
        femmes_isolees = pd.to_numeric(sel_row["femmes_60_75_plus_isolees"], errors="coerce")
        hommes_isoles = isoles - femmes_isolees

        # Données pour le donut imbriqué
        outer_labels = ["Non isolés", "Isolés"]
        outer_values = [non_isoles, isoles]

        inner_labels = ["Hommes isolés", "Femmes isolées"]
        inner_values = [hommes_isoles, femmes_isolees]

        # Anneau extérieur
        fig_nested_donut.add_trace(go.Pie(
            labels=outer_labels,
            values=outer_values,
            hole=0.4,
            textinfo="label+percent",
            textposition="outside",
            marker_colors=["#4C78A8", "#F58518"],
            domain={'x': [0, 1], 'y': [0, 1]},
            name="Isolation",
            pull=[0.05, 0.05]  # léger "décalage" pour meilleure lisibilité
        ))

        # Anneau intérieur (hommes/femmes parmi isolés)
        fig_nested_donut.add_trace(go.Pie(
            labels=inner_labels,
            values=inner_values,
            hole=0.65,  # légèrement plus grand que 0.7 pour laisser place aux labels
            textinfo="label+percent",
            textposition="outside",
            marker_colors=["#1F77B4", "#FF7F0E"],
            domain={'x': [0, 1], 'y': [0, 1]},
            name="Genre",
            pull=[0.05, 0.05]
        ))

    else:
        fig_nested_donut.add_annotation(
            x=0.5,
            y=0.5,
            text="Aucune sélection",
            showarrow=False,
            font=dict(size=16, color="#778873")
        )

    # Layout
    fig_nested_donut.update_layout(
        title=f"Isolement social des +65 ans – {sel_row['departement']} ({sel_row['region']})" if sel_row is not None else "Isolement social des +65 ans",
        height=450,
        paper_bgcolor="#F1F3E0",
        plot_bgcolor="#F1F3E0",
        showlegend=True
    )

    # Ajouter à la liste si sélectionné
    if "Isolement social" in st.session_state.selected_graphs:
        selected_charts.append(fig_nested_donut)
#--------------------------------------------------------------------------------------------------------------------------------

    fig_ratio_logement = go.Figure()

    if sel_row is not None:
        # Total seniors
        proprietaires = pd.to_numeric(sel_row["60_75_plus_proprietaires"], errors="coerce")
        locataires_prive = pd.to_numeric(sel_row["60_75_plus_autre_logement"], errors="coerce")
        locataires_social = pd.to_numeric(sel_row["60_75_plus_en_maison"], errors="coerce")

        # Camembert 1 : Propriétaires vs Locataires
        labels_outer = ["Propriétaires", "Locataires"]
        values_outer = [proprietaires, locataires_prive + locataires_social]
        colors_outer = ["#2E86AB", "#F6C85F"]

        fig_ratio_logement.add_trace(go.Pie(
            labels=labels_outer,
            values=values_outer,
            name="Propriétaires vs Locataires",
            hole=0.4,
            textinfo="label+percent",
            textposition="inside",
            marker_colors=colors_outer,
            domain={'x': [0, 0.48], 'y': [0, 1]},  # à gauche
            hoverinfo="label+value+percent"
        ))

        # Camembert 2 : Locataires parc privé vs social
        labels_inner = ["Locataires parc privé", "Locataires parc social"]
        values_inner = [locataires_prive, locataires_social]
        colors_inner = ["#6FB1FC", "#F6D78C"]

        fig_ratio_logement.add_trace(go.Pie(
            labels=labels_inner,
            values=values_inner,
            name="Type de locataires",
            hole=0.4,
            textinfo="label+percent",
            textposition="inside",
            marker_colors=colors_inner,
            domain={'x': [0.52, 1], 'y': [0, 1]},  # à droite
            hoverinfo="label+value+percent"
        ))

    else:
        fig_ratio_logement.add_annotation(
            x=0.5,
            y=0.5,
            text="Aucune sélection",
            showarrow=False,
            font=dict(size=16, color="#778873")
        )

    # Layout amélioré
    fig_ratio_logement.update_layout(
        title=dict(
            text=f"Répartition propriétaires et locataires des +65 ans – {sel_row['departement']} ({sel_row['region']})" if sel_row is not None else "Répartition propriétaires et locataires des +65 ans",
            x=0.5,
            xanchor='center',
            font=dict(size=18, family="Arial", color="#333333")
        ),
        height=450,
        paper_bgcolor='rgba(0,0,0,0)',  # fond transparent
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.1,
            xanchor="center",
            x=0.5,
            font=dict(size=12)
        )
    )

    # Ajouter à la liste si sélectionné
    if "Propriétaires vs Locataires" in st.session_state.selected_graphs:
        selected_charts.append(fig_ratio_logement)
#-------------------------------------------------------------------------


    fig_revenu = go.Figure()
    fig_revenu.add_trace(go.Scatter(
        x=df['departement'],
        y=df['revenu_median_60_74'],
        mode='lines+markers',
        name="60-74 ans - médiane",
        line=dict(color="#1f77b4", width=3)
    ))

    # Tracé médiane 75+ ans
    fig_revenu.add_trace(go.Scatter(
        x=df['departement'],
        y=df['revenu_median_75_plus'],
        mode='lines+markers',
        name="75+ ans - médiane",
        line=dict(color="#ff7f0e", width=3)
    ))

    # Moyennes régionales
    fig_revenu.add_trace(go.Scatter(
        x=df['departement'],
        y=[df['revenu_median_60_74'].mean()]*len(df),
        mode='lines',
        name="Moyenne régionale 60-74 ans",
        line=dict(color="#1f77b4", dash='dash')
    ))

    fig_revenu.add_trace(go.Scatter(
        x=df['departement'],
        y=[df['revenu_median_75_plus'].mean()]*len(df),
        mode='lines',
        name="Moyenne régionale 75+ ans",
        line=dict(color="#ff7f0e", dash='dash')
    ))

    # Layout
    fig_revenu.update_layout(
        title="Revenu médian des seniors par département (60-74 ans et 75+)",
        xaxis_title="Département",
        yaxis_title="Revenu (€)",
        xaxis=dict(tickangle=45),
        height=500,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    if "Revenus" in st.session_state.selected_graphs:
        selected_charts.append(fig_revenu)

#--------------------------------------------------------------------------------------------------------------------------------


    colonnes_aspa = [
    'aspa_effectif_2013', 'aspa_effectif_2014', 'aspa_effectif_2015', 'aspa_effectif_2016',
    'aspa_effectif_2017', 'aspa_effectif_2018', 'aspa_effectif_2019', 'aspa_effectif_2020',
    'aspa_effectif_2021', 'aspa_effectif_2022', 'aspa_effectif_2023', 'aspa_effectif_2024'
    ]

    annees_aspa = [int(col.split("_")[-1]) for col in colonnes_aspa]

    fig_aspa = go.Figure()

    if sel_row is not None:
        # Récupérer les valeurs ASPA pour le département sélectionné
        aspa_values = [pd.to_numeric(sel_row[col], errors="coerce") for col in colonnes_aspa]

        # Tracé de la courbe
        fig_aspa.add_trace(go.Scatter(
            x=annees_aspa,
            y=aspa_values,
            mode='lines+markers',
            name=f"Bénéficiaires ASPA - {sel_row['departement']}",
            line=dict(color="#2E86AB", width=3),
            marker=dict(size=6)
        ))

    else:
        fig_aspa.add_annotation(
            x=0.5,
            y=0.5,
            text="Aucune sélection",
            showarrow=False,
            font=dict(size=16, color="#778873")
        )

    # Layout amélioré
    fig_aspa.update_layout(
        title=dict(
            text=f"Évolution du nombre de bénéficiaires de l'ASPA – {sel_row['departement']}" if sel_row is not None else "Évolution du nombre de bénéficiaires de l'ASPA",
            x=0.5,
            xanchor='center',
            font=dict(size=18, family="Arial", color="#333333")
        ),
        xaxis_title="Année",
        yaxis_title="Nombre de bénéficiaires",
        height=450,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.1,
            xanchor="center",
            x=0.5,
            font=dict(size=12)
        )
    )

    # Ajouter à la liste si sélectionné
    if "ASPA" in st.session_state.selected_graphs:
        selected_charts.append(fig_aspa)


#--------------------------------------------------------------------------------------------------------------------------------

#--------------------------------------------------------------------------------------------------------------------------------

    annees = [2025, 2030, 2035, 2040, 2045, 2050]

    # scénario unique
    scenario = "s1"

    sexes = {
        "F": "Femmes",
        "H": "Hommes"
    }

    couleur_scenario = "#1f77b4"

    fig_livia = go.Figure()

    if sel_row is not None:
        for sexe_code, sexe_label in sexes.items():

            colonnes = [
                f"vol_GLOB_{scenario}_{sexe_code}_{annee}"
                for annee in annees
            ]

            valeurs = [
                pd.to_numeric(sel_row.get(col), errors="coerce")
                for col in colonnes
            ]

            fig_livia.add_trace(go.Scatter(
                x=annees,
                y=valeurs,
                mode="lines+markers",
                name=sexe_label,
                line=dict(
                    color=couleur_scenario,
                    width=3,
                    dash="solid" if sexe_code != "H" else "dash"
                ),
                marker=dict(size=7)
            ))
    else:
        fig_livia.add_annotation(
            text="Aucune sélection",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="gray")
        )

    fig_livia.update_layout(
        title=dict(
            text=f"Prévisions LIVIA – vol_GLOB ({sel_row['departement']})"
            if sel_row is not None else
            f"Prévisions LIVIA – vol_GLOB",
            x=0.5
        ),
        xaxis_title="Année",
        yaxis_title="Volume",
        height=450,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h",
            y=-0.2,
            x=0.5,
            xanchor="center"
        )
    )

    if "LIVIA" in st.session_state.selected_graphs:
        selected_charts.append(fig_livia)

#--------------------------------------------------------------------------------------------------------------------------------

    cols_per_row = 3
    for i in range(0, len(selected_charts), cols_per_row):
        row_charts = selected_charts[i:i+cols_per_row]
        cols = st.columns(len(row_charts))
        for col, fig in zip(cols, row_charts):
            col.plotly_chart(fig, use_container_width=True, config=plot_config)


# =========================================================
#        MODULE COMPARAISON DE DÉPARTEMENTS
# =========================================================

with st.expander("🔎 Comparer des départements", expanded=False):

    st.subheader("Sélection des départements")

    dep_options = sorted(df["Département"].unique().tolist())

    col1, col2, col3, col4 = st.columns(4)

    dep1 = col1.selectbox("Département 1", dep_options, key="dep_comp1")
    dep2 = col2.selectbox("Département 2", dep_options, key="dep_comp2")
    dep3 = col3.selectbox("Département 3", ["Aucun"] + dep_options, key="dep_comp3")
    dep4 = col4.selectbox("Département 4", ["Aucun"] + dep_options, key="dep_comp4")

    selected_deps = [d for d in [dep1, dep2, dep3, dep4] if d != "Aucun"]
    selected_deps = list(dict.fromkeys(selected_deps))  # enlève doublons

    # ============================
    # TABLEAU DE COMPARAISON
    # ============================
    st.markdown("### Tableau comparatif")

    df_compare = df[df["Département"].isin(selected_deps)]

    columns_to_show = [
        "Département",
        "Population",
        "Part des femmes (en %)",
        "Part des 60 ans ou plus (en %)",
        "total_seniors",
        "taux_pauvrete_calcul",
        " Score de fragilité numérique senior"
    ]

    columns_to_show = [c for c in columns_to_show if c in df_compare.columns]

    st.dataframe(
        df_compare[columns_to_show].set_index("Département"),
        use_container_width=True
    )

    # ============================
    # GRAPHIQUES
    # ============================
    if len(selected_deps) >= 2:

        st.markdown("### Graphiques comparatifs")

        df_plot = df_compare.set_index("Département")

        graph_choices = st.multiselect(
            "Graphiques à afficher",
            ["Population seniors", "Taux pauvreté", "Fragilité numérique"],
            default=["Population seniors"]
        )

        if "Population seniors" in graph_choices:
            st.bar_chart(df_plot["total_seniors"])

        if "Taux pauvreté" in graph_choices:
            st.bar_chart(df_plot["taux_pauvrete_calcul"])

        if "Fragilité numérique" in graph_choices:
            st.bar_chart(df_plot[" Score de fragilité numérique senior"])

