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

#-----------------------------------------------------------------------------------------------
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

df = pd.read_csv("resultat_final.csv", encoding="utf-8-sig")

st.set_page_config(page_title="France - départements colorés ", layout="wide")
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
apply_external_css("style.css")
st.title("France")

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

# ---------- U ----------
metric = st.selectbox("Choisir la métrique :", [
    "Taux de pauvrete pour plus de 75 ans",
    "Population",
    "Niveau de vie médian des ménages (en euros)",
    "Part des femmes (en %)",
    "Part des 60 ans ou plus (en %)",
    "dont part des 75 ans ou plus (en %)"
])

# ---------- 
value_by_code = {}
for _, row in df.iterrows():
    code = str(row["departement"]).strip()
    value_by_code[code] = row[metric]
value_by_code_nozero = {code.lstrip("0"): v for code, v in value_by_code.items()}

values = [v for v in value_by_code.values() if pd.notnull(v)]
vmin, vmax = min(values), max(values)
colormap = cm.LinearColormap(["#FEF3E2","#FAB12F","#FA812F","#DD0303"], vmin=vmin, vmax=vmax)
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
        fill = colormap(val) if val is not None else "#f0f0f0"
    if st.session_state.get("selected_dep") and str(code_s).strip() == str(st.session_state.get("selected_dep")).strip():
        return {"fillColor": fill, "color": "#000000", "weight": 3, "fillOpacity": 0.8}
    else:
        return {"fillColor": fill, "color": "#444444", "weight": 1.0, "fillOpacity": 0.6}

# -------------------------------------------------------------------------------
# Créer la carte Folium (m)
m = folium.Map(
    location=center,
    zoom_start=6,
    min_zoom=6,
    max_zoom=14,
    tiles=None,
    control_scale=True,
    prefer_canvas=True
)
m.fit_bounds(bounds)

# GeoJson layer + tooltip
gj = folium.GeoJson(
    geojson,
    name="departements",
    style_function=style_function,
    highlight_function=lambda feat: {"weight": 3, "color": "#ff3333", "fillOpacity": 0.9},
    tooltip=folium.GeoJsonTooltip(
        fields=[geo_key, 'nom'] if any('nom' in (f.get("properties") or {}) for f in geojson.get("features", [])) else [geo_key],
        aliases=["code", "nom"] if any('nom' in (f.get("properties") or {}) for f in geojson.get("features", [])) else ["code"],
        localize=True
    )
)
gj.add_to(m)
colormap.add_to(m)
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
col_map, col_graph = st.columns([2, 1])

with col_map:
    # --- Initialisation ---
    if "selected_dep" not in st.session_state:
        st.session_state["selected_dep"] = df["departement"].iloc[0]

    # --- Carte interactive ---
    output = st_folium(m, width=950, height=700)
    clicked = extract_dept_from_output(output, geo_key)

    # --- Gestion du clic sur la carte ---
    if clicked:
        clicked_norm = clicked.strip()
        try:
            if clicked_norm.isdigit():
                clicked_norm = str(int(clicked_norm)).zfill(2)
        except Exception:
            pass

        if st.session_state["selected_dep"] != clicked_norm:
            st.session_state["selected_dep"] = clicked_norm
            st.rerun()

    # --- Sélecteur manuel avec bouton de validation ---
    current_dep = st.session_state["selected_dep"]
    selected_box_value = st.selectbox(
        "Choisir un département :",
        df["departement"],
        index=df["departement"].tolist().index(current_dep)
        if current_dep in df["departement"].tolist() else 0,
        key="dep_selectbox"
    )

    if st.button("Valider le choix manuel"):
        if st.session_state["selected_dep"] != selected_box_value:
            st.session_state["selected_dep"] = selected_box_value
            st.rerun()


with col_graph:
    graph_options = [
        "Top 5 maladies chez ≥ 65 ans",
        "Profil social 60–74 ans",
        "Part des 60 ans ou plus",
        "Radar santé (6 variables)",
        "Espérance de vie"
    ]

    # --- Nettoyage session_state avant affichage ---
    if "selected_graphs" in st.session_state:
        if len(st.session_state.selected_graphs) > 3:
            st.session_state.selected_graphs = st.session_state.selected_graphs[:3]
    else:
        st.session_state.selected_graphs = graph_options[:3]  # default propre

    # --- Multiselect unique et sécurisé ---
    selected_graphs = st.multiselect(
        "Choisissez jusqu'à 3 graphiques à afficher :",
        options=graph_options,
        default=st.session_state.selected_graphs,
        max_selections=3,
        key="selected_graphs"
    )
    plot_config = {"displayModeBar": True, "scrollZoom": True, "displaylogo": False}

    
    metric_map_right = [
        "Taux de pauvrete pour plus de 75 ans",  
        "Part des 60 ans ou plus (en %)",       
        "Niveau de vie médian des ménages (en euros)"  
    ]

    

    selected = st.session_state.get("selected_dep")

    # calculer moyennes nationales pour tous les indicateurs utiles
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

    sel_row = None
    if selected:
        s = str(selected).strip()
        s_norm = s.upper().lstrip("0")

        df["dep_norm"] = df["departement"].astype(str).str.upper().str.lstrip("0")

        if s_norm in df["dep_norm"].values:
            sel_row = df[df["dep_norm"] == s_norm].iloc[0]
        else:
            sel_row = None

    
    # --- Graphique 1 
    fig1 = go.Figure()

    # On récupère toutes les colonnes maladies ≥ 65 ans réellement présentes et numériques
    maladies_65 = [col for col in df.columns if "65" in col and "Total" not in col]


    if sel_row is not None:
        
        # On convertit les valeurs en nombre (des fois string → numeric)
        values = pd.to_numeric(sel_row[maladies_65], errors="coerce")

        # On retire les NaN sinon Plotly ne trace rien
        values = values.dropna()

        if len(values) > 0:
            top5 = values.sort_values(ascending=False).head(5)

            fig1.add_trace(go.Bar(
                x=top5.values,
                y=[m.replace("≥ 65 ans - ", "") for m in top5.index],
                orientation="h",
                marker=dict(color="#0074D9")
            ))

            fig1.update_layout(
                title=f"Top 5 maladies chez les ≥ 65 ans – {sel_row['departement']}",
                margin=dict(l=10, r=10, t=40, b=10),
                height=300
            )
        else:
            fig1 = px.bar(x=["Pas de données"], y=[0], height=300)

    else:
        fig1 = px.bar(x=["Aucune sélection"], y=[0], height=300)

    if "Top 5 maladies chez ≥ 65 ans" in selected_graphs:
        st.plotly_chart(fig1, use_container_width=True, config=plot_config, key="chart_1")




    # =============== GRAPHIQUE 2 : RADAR 60–74 ANS ==================

    radar_vars = [
        "60_74_menage_peu_diplome",
        "60_74_menage_immigre",
        "60_74_proprietaires",
        "femmes_60_74_isolees",
        "60_74_sans_voiture"
    ]

    fig2 = go.Figure()

    if sel_row is not None:

        vals = pd.to_numeric(sel_row[radar_vars], errors="coerce").fillna(0).tolist()

        fig2.add_trace(go.Scatterpolar(
            r=vals,
            theta=[
                "Peu diplômés",
                "Ménages immigrés",
                "Propriétaires",
                "Femmes isolées",
                "Sans voiture"
            ],
            fill='toself',
            name=sel_row["departement"]
        ))

        fig2.update_layout(
            title="Profil social 60–74 ans",
            polar=dict(radialaxis=dict(visible=True)),
            margin=dict(l=10, r=10, t=40, b=10),
            height=300
        )
    else:
        fig2.add_trace(go.Scatterpolar(r=[1], theta=["Aucune sélection"], fill="toself"))
        fig2.update_layout(height=300)

    if "Profil social 60–74 ans" in selected_graphs:
        st.plotly_chart(fig2, use_container_width=True, config=plot_config, key="chart_2")



    # =============== GRAPHIQUE 3 : CAMEMBERT PART DES 60+ ==================

    fig3 = go.Figure()

    if sel_row is not None:
        part60 = float(sel_row["Part des 60 ans ou plus (en %)"])
        reste = max(0, 100 - part60)

        fig3.add_trace(go.Pie(
            labels=[f"60+ ({part60}%)", "Autres"],
            values=[part60, reste],
            hole=0.4
        ))

        fig3.update_layout(
            title="Part des 60 ans ou plus",
            margin=dict(l=10, r=10, t=40, b=10),
            height=220
        )
    else:
        fig3.add_trace(go.Pie(labels=["Aucune sélection"], values=[1], hole=0.4))
        fig3.update_layout(height=220)

    if "Part des 60 ans ou plus" in selected_graphs:
        st.plotly_chart(fig3, use_container_width=True, config=plot_config, key="chart_3")

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
        # Valeurs du département
        vals_dep = pd.to_numeric(sel_row[list(radar6_vars_raw.keys())], errors="coerce").fillna(0).tolist()

        # Moyenne nationale UNIQUEMENT sur ces 6 variables
        vals_nat = df[list(radar6_vars_raw.keys())].apply(pd.to_numeric, errors="coerce").mean().fillna(0).tolist()

        labels = list(radar6_vars_raw.values())

        fig4.add_trace(go.Scatterpolar(
            r=vals_dep,
            theta=labels,
            fill='toself',
            name=f"{sel_row['departement']}"
        ))

        fig4.add_trace(go.Scatterpolar(
            r=vals_nat,
            theta=labels,
            fill='toself',
            name="France"
        ))

        fig4.update_layout(
            title="Radar santé – difficultés et limitations",
            polar=dict(radialaxis=dict(visible=True)),
            margin=dict(l=10, r=10, t=40, b=10),
            height=320
        )
    else:
        fig4.add_trace(go.Scatterpolar(r=[1], theta=["Aucune sélection"], fill="toself"))
        fig4.update_layout(height=300)

    if "Radar santé (6 variables)" in selected_graphs:
        st.plotly_chart(fig4, use_container_width=True, config=plot_config, key="chart_4")


# =============== GRAPHIQUE 5 : ESPÉRANCE DE VIE ==================

    fig5 = go.Figure()

    if sel_row is not None:
        esp = sel_row["esp"]

        fig5.add_annotation(
            x=0.5, y=0.5,
            text=f"<b>{esp:.1f} ans</b>",
            showarrow=False,
            font=dict(size=40)
        )

        fig5.update_layout(
            title="Espérance de vie",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            margin=dict(l=10, r=10, t=40, b=10),
            height=220
        )
    else:
        fig5.add_annotation(x=0.5, y=0.5, text="Aucune sélection", showarrow=False)
        fig5.update_layout(height=200)

    if "Espérance de vie" in selected_graphs:
        st.plotly_chart(fig5, use_container_width=True, config=plot_config, key="chart_5")


# -------------------------------------------------------------------------------




# -------------------------------------------------------------------------------
