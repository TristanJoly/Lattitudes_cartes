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
st.set_page_config(page_title="France - départements colorés ", layout="wide")
apply_external_css("style.css")

st.title("France ")





GEO_PATH = Path("departements.geojson")
if not GEO_PATH.exists():
    st.error(f"departements.geojson introuvable : {GEO_PATH.resolve()}")
    st.stop()

geojson_raw = json.loads(GEO_PATH.read_text(encoding="utf-8"))



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



df = pd.read_csv("resultat_final.csv", encoding="utf-8-sig")


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

geo_key = detect_geo_key(geojson_raw, df["departement"].tolist())
if not geo_key:
    st.error("Impossible de détecter la propriété GeoJSON contenant les codes de département. Affiche un feature pour debug.")
    st.json(geojson_raw.get("features", [])[0].get("properties", {}))
    st.stop()




# ---------- Filtrer GeoJSON ---------- 
def feature_code_str(feature, geo_key):
    props = feature.get("properties") or {}
    val = props.get(geo_key) or props.get("code") or props.get("id")
    if val is None:
        return None
    s = str(val).strip()
    return s

metropole_set = {c.upper() for c in metropole_codes}
if 1 == 0:
    geojson = geojson_raw
else:
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
            # try numeric variant
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

# ---------- UI : métrique ----------
metric = st.selectbox("Choisir la métrique :", ["Taux de pauvrete pour plus de 75 ans","Population","Niveau de vie médian des ménages (en euros)","Part des femmes (en %)","Part des 60 ans ou plus (en %)","dont part des 75 ans ou plus (en %)"])

# ---------- Préparer mapping code ---------- 
value_by_code = {}
for _, row in df.iterrows():
    code = str(row["departement"]).strip()
    value_by_code[code] = row[metric]


value_by_code_nozero = {code.lstrip("0"): v for code, v in value_by_code.items()}


values = list(value_by_code.values())
vmin, vmax = min(values), max(values)
colormap = cm.LinearColormap(["#FEF3E2","#FAB12F","#FA812F","#DD0303"], vmin=vmin, vmax=vmax)
colormap.caption = metric




if "selected_dep" not in st.session_state:
    st.session_state["selected_dep"] = None

    
m = folium.Map(
    location=center,
    zoom_start=6,
    min_zoom=6,             # empêche de dézoomer en dessous du niveau initial
    max_zoom=14,            # tu peux zoomer plus fort
    tiles=None,
    control_scale=True,
    prefer_canvas=True
)

# Empêche tout dézoom au-delà des limites de la France
m.fit_bounds(bounds)
# --- après m.fit_bounds(bounds) ---

# get folium map JS var name (ex: "map_12345")
map_var_name = m.get_name()

# inject JS to lock minZoom to current zoom, prevent dezoom, and make container transparent
from branca.element import Element

script = Element(f"""
<script>
(function() {{
  try {{
    // récupère la variable JS du map créée par folium
    var map = {map_var_name};

    // si map non trouvée on sort
    if (!map) return;

    // 1) définir minZoom au zoom courant pour empêcher le dézoom
    var currentZoom = map.getZoom();
    map.options.minZoom = currentZoom;
    // aussi forcer la valeur "minZoom" sur l'objet map (quelques versions de Leaflet lisent les deux)
    if (typeof map.setMinZoom === 'function') {{
      map.setMinZoom(currentZoom);
    }}

    // 2) sécurité : si l'utilisateur arrive à dézoomer, on le remet
    map.on('zoomend', function() {{
      if (map.getZoom() < map.options.minZoom) {{
        map.setZoom(map.options.minZoom);
      }}
    }});

    // 3) rendre le fond du conteneur transparent (feuilles Leaflet)
    var container = map.getContainer();
    if (container && container.style) {{
      container.style.background = 'transparent';
    }}

    // rendre transparent les différentes "panes" de leaflet (pour éviter le gris)
    var panes = container.getElementsByClassName('leaflet-pane');
    for (var i = 0; i < panes.length; i++) {{
      panes[i].style.background = 'transparent';
    }}

    // essayer aussi de rendre transparent le 'map' div enfant généré par folium
    var foliumMapDivs = document.getElementsByClassName('folium-map');
    for (var j = 0; j < foliumMapDivs.length; j++) {{
      foliumMapDivs[j].style.background = 'transparent';
    }}

  }} catch (e) {{
    console.warn('JS injection pour map transparent/minZoom failed', e);
  }}
}})();
</script>
""")

m.get_root().html.add_child(script)

# CSS côté Streamlit pour forcer l'iframe + conteneurs à être transparents
st.markdown(
    """
    <style>
      /* cible l'iframe généré par st_folium / folium et force transparence */
      iframe[title^="folium"] {
        background: transparent !important;
      }
      /* cible conteneurs Leaflet dans la page Streamlit au cas où */
      .folium-map, .leaflet-container {
        background: transparent !important;
      }
      /* si le wrapper Streamlit pose un fond gris on l'enlève pour l'iframe */
      .stFrame iframe {
        background: transparent !important;
      }
    </style>
    """,
    unsafe_allow_html=True
)


# style function qui colorie selon la valeur et met en évidence la sélection
def style_function(feature):
    code_raw = feature.get("properties", {}).get(geo_key) or feature.get("properties", {}).get("code") or feature.get("id")
    if code_raw is None:
        fill = "#eeeeee"
    else:
        code_s = str(code_raw).strip()
        # lookup value
        val = value_by_code.get(code_s)
        if val is None:
            val = value_by_code_nozero.get(code_s.lstrip("0"))
        if val is None:
            fill = "#f0f0f0"
        else:
            fill = colormap(val)
    # highlight selection stronger
    if st.session_state.get("selected_dep") and str(code_raw).strip() == str(st.session_state.get("selected_dep")).strip():
        return {
            "fillColor": fill,
            "color": "#000000",
            "weight": 3,
            "fillOpacity": 0.8
        }
    else:
        return {
            "fillColor": fill,
            "color": "#444444",
            "weight": 1.0,
            "fillOpacity": 0.6
        }


def tooltip_fields(feature):
    props = feature.get("properties") or {}
    code = props.get(geo_key) or props.get("code") or props.get("id") or ""
    name = props.get("nom") or props.get("name") or ""
    # find metric value
    v = value_by_code.get(str(code)) or value_by_code_nozero.get(str(code).lstrip("0"))
    return {"code": code, "name": name, "value": v}

# ajouter la couche GeoJson 
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


st.write("Clique sur un département pour voir ses infos (ou utilise le selectbox fallback).")
output = st_folium(m, width=950, height=700)
st.markdown(
    """
    <style>
        .folium-map {
            background-color: transparent !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)


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

clicked = extract_dept_from_output(output, geo_key)

if clicked:
    clicked_norm = clicked.strip()
    
    try:
        if clicked_norm.isdigit():
            clicked_norm = str(int(clicked_norm)).zfill(2)
    except Exception:
        pass
    if st.session_state.get("selected_dep") != clicked_norm:
        st.session_state["selected_dep"] = clicked_norm
        try:
            st.rerun()  
        except Exception:
            st.query_params["_rerun"] = str(int(time.time() * 100))

if not st.session_state.get("selected_dep"):
    chosen = st.selectbox("Choisir un département (fallback) :", df["departement"])
    if chosen:
        st.session_state["selected_dep"] = chosen

selected = st.session_state.get("selected_dep")
st.sidebar.markdown("### Département sélectionné")
if selected:
    # normalize key lookups
    s = str(selected).strip()
    
    row = None
    if s in df["departement"].values:
        row = df[df["departement"] == s].iloc[0]
    else:
        s_alt = s.zfill(2)
        if s_alt in df["departement"].values:
            row = df[df["departement"] == s_alt].iloc[0]
    if row is not None:
        st.sidebar.write(f"**Code :** {row['code_departement']}")
        st.sidebar.write(f"**Département :** {row['departement']}")
        st.sidebar.write(f"**Taux de pauvreté (75 ans et +) :** {row['Taux de pauvrete pour plus de 75 ans']} %")
        st.sidebar.write(f"**Population:** {row['Population']} personne")
        st.sidebar.write(f"**Part des femmes (en %) :** {row['Part des femmes (en %)']} %")
        st.sidebar.write(f"**Part des 60 et plus :** {row['Part des 60 ans ou plus (en %)']} %")
        st.sidebar.write(f"**Dont part des 75 ans :** {row['dont part des 75 ans ou plus (en %)']} %")
        st.sidebar.write(f"**Niveau de vie médian des ménages (en euros):** {row['Niveau de vie médian des ménages (en euros)']} ")
    else:
        st.sidebar.warning(f"Aucune donnée retrouvée pour {selected}")
else:
    st.sidebar.info("Aucun département sélectionné.")

# bouton pour effacer la selection
if st.sidebar.button("Effacer la sélection"):
    st.session_state["selected_dep"] = None
    st.rerun()
