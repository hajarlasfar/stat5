import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime

st.set_page_config(
    page_title="Plateforme de Veille et d'Archivage Documentaire",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>

/* Fond général */
.stApp {
    background-color: #F8FAFC;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #1E293B;
}

[data-testid="stSidebar"] * {
    color: white;
}

/* Boutons */
.stButton > button {
    background-color: #1F3A5F;
    color: white;
    border-radius: 10px;
    border: none;
    height: 45px;
    font-weight: bold;
}

.stButton > button:hover {
    background-color: #274C77;
}

/* Inputs */
.stTextInput input,
.stDateInput input,
.stSelectbox div {
    border-radius: 8px;
}

/* Containers */
div[data-testid="stVerticalBlock"] > div:has(div[data-testid="stHorizontalBlock"]) {
    border-radius: 12px;
}

/* Titres */
h1 {
    color: #1F3A5F;
    font-size: 44px !important;
}

/* Titre "Bibliotheque" dans la sidebar, plus grand */
[data-testid="stSidebar"] h1 {
    font-size: 32px !important;
}

/* Texte des themes dans le menu de la sidebar (les boutons radio) */
[data-testid="stSidebar"] [data-testid="stRadio"] label p {
    font-size: 18px !important;
}

/* Cercle du bouton radio lui-meme, agrandi pour rester proportionnel */
[data-testid="stSidebar"] [data-testid="stRadio"] label span:first-child {
    transform: scale(1.3);
}

</style>
""", unsafe_allow_html=True)

DOSSIER_FICHIERS = "fichiers_stockes"
CHEMIN_DB = "bibliotheque.db"
COLONNE_DATE = "Date"
os.makedirs(DOSSIER_FICHIERS, exist_ok=True)

def get_connexion():
    conn = sqlite3.connect(CHEMIN_DB)
    conn.row_factory = sqlite3.Row
    return conn

def initialiser_db():
    conn = get_connexion()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS themes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT UNIQUE NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fichiers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            theme TEXT NOT NULL,
            chemin TEXT NOT NULL,
            date_min TEXT,
            date_max TEXT,
            nb_lignes INTEGER,
            importe_le TEXT
        )
    """)
    for theme_defaut in ["Elections", "Demographie", "Ministere de l'Interieur"]:
        conn.execute("INSERT OR IGNORE INTO themes (nom) VALUES (?)", (theme_defaut,))
    conn.commit()
    conn.close()

initialiser_db()

def lister_themes():
    conn = get_connexion()
    themes = [r["nom"] for r in conn.execute("SELECT nom FROM themes ORDER BY nom")]
    conn.close()
    return themes

def ajouter_theme(nom):
    conn = get_connexion()
    conn.execute("INSERT OR IGNORE INTO themes (nom) VALUES (?)", (nom,))
    conn.commit()
    conn.close()

def lister_fichiers():
    conn = get_connexion()
    lignes = conn.execute("SELECT * FROM fichiers ORDER BY importe_le DESC").fetchall()
    conn.close()
    return [dict(l) for l in lignes]

def ajouter_fichier(nom, theme, chemin, date_min, date_max, nb_lignes):
    conn = get_connexion()
    conn.execute("""
        INSERT INTO fichiers (nom, theme, chemin, date_min, date_max, nb_lignes, importe_le)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (nom, theme, chemin,
          str(date_min) if date_min is not None else None,
          str(date_max) if date_max is not None else None,
          nb_lignes, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def supprimer_fichier(id_fichier, chemin):
    conn = get_connexion()
    conn.execute("DELETE FROM fichiers WHERE id = ?", (id_fichier,))
    conn.commit()
    conn.close()
    if os.path.exists(chemin):
        os.remove(chemin)

fichiers = lister_fichiers()
themes = lister_themes()

total_fichiers = len(fichiers)
total_themes = len(themes)
total_lignes = sum(f["nb_lignes"] for f in fichiers)

m1, m2, m3 = st.columns(3)
m1.metric("📂 Fichiers", total_fichiers)
m2.metric("🏷️ Thèmes", total_themes)
m3.metric("📰 Articles", total_lignes)

with st.sidebar:
    st.markdown("""
# 📚 Bibliothèque
""")
    st.success(f"{len(fichiers)} fichier(s) enregistré(s)")

    compteurs = {}
    for f in fichiers:
        compteurs[f["theme"]] = compteurs.get(f["theme"], 0) + 1

    options = ["Tous les themes"] + themes
    libelles = {"Tous les themes": f"Tous les themes ({len(fichiers)})"}
    for t in themes:
        libelles[t] = f"{t} ({compteurs.get(t, 0)})"

    theme_actif = st.radio(
        "Themes", options, format_func=lambda x: libelles.get(x, x),
        label_visibility="collapsed",
    )

    with st.expander("Gerer les themes"):
        nouveau = st.text_input("Nouveau theme", key="nouveau_theme")
        if st.button("Ajouter le theme") and nouveau:
            ajouter_theme(nouveau)
            st.success(f"Theme '{nouveau}' ajoute.")
            st.rerun()

st.markdown("""
<h1>
📊 Plateforme de Veille et d’Archivage Documentaire
</h1>
""", unsafe_allow_html=True)

st.markdown("""
<div style='font-size:16px;color:gray;margin-bottom:25px'>
Centralisation, classement et consultation des données thématiques et des fichiers de veille.
</div>
""", unsafe_allow_html=True)

with st.expander("📤 Importer un nouveau fichier", expanded=len(fichiers) == 0):
    fichier_upload = st.file_uploader("Fichier Excel (.xlsx)", type=["xlsx"])

    if fichier_upload is not None:
        try:
            apercu_df = pd.read_excel(fichier_upload)
        except Exception as e:
            st.error(f"Impossible de lire ce fichier : {e}")
            apercu_df = None

        if apercu_df is not None:
            if COLONNE_DATE not in apercu_df.columns:
                st.error(f"Ce fichier n'a pas de colonne '{COLONNE_DATE}'. Colonnes trouvees : {list(apercu_df.columns)}")
            else:
                theme_choisi = st.selectbox("Theme", themes)
                st.dataframe(apercu_df, use_container_width=True, height=250)

                if st.button("Importer ce fichier", type="primary"):
                    nom_unique = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{fichier_upload.name}"
                    chemin = os.path.join(DOSSIER_FICHIERS, nom_unique)
                    with open(chemin, "wb") as out:
                        out.write(fichier_upload.getbuffer())

                    dates_converties = pd.to_datetime(apercu_df[COLONNE_DATE], errors="coerce")
                    dates_valides = dates_converties.dropna()

                    ajouter_fichier(
                        nom=fichier_upload.name,
                        theme=theme_choisi,
                        chemin=chemin,
                        date_min=dates_valides.min() if not dates_valides.empty else None,
                        date_max=dates_valides.max() if not dates_valides.empty else None,
                        nb_lignes=len(apercu_df),
                    )
                    st.success(f"'{fichier_upload.name}' importe dans le theme '{theme_choisi}'.")
                    st.rerun()

st.markdown("""
## 🔍 Recherche documentaire
""")

with st.container(border=True):
    fc1, fc2, fc3 = st.columns([2, 1, 1])

    recherche_nom = fc1.text_input("Recherche par nom de fichier")
    date_debut = fc2.date_input("Du", value=None, format="YYYY-MM-DD")
    date_fin = fc3.date_input("Au", value=None, format="YYYY-MM-DD")

fichiers_affiches = fichiers

# Filtre theme
if theme_actif != "Tous les themes":
    fichiers_affiches = [f for f in fichiers_affiches if f["theme"] == theme_actif]

# Filtre nom fichier
if recherche_nom:
    fichiers_affiches = [f for f in fichiers_affiches if recherche_nom.lower() in f["nom"].lower()]

# Pre-filtrage rapide au niveau fichier avant lecture ligne par ligne
if date_debut:
    fichiers_affiches = [
        f for f in fichiers_affiches
        if f["date_max"] and datetime.fromisoformat(f["date_max"]).date() >= date_debut
    ]
if date_fin:
    fichiers_affiches = [
        f for f in fichiers_affiches
        if f["date_min"] and datetime.fromisoformat(f["date_min"]).date() <= date_fin
    ]

# Si une date est renseignee => recherche au niveau des lignes, combinee
# avec le filtre par nom de fichier deja applique ci-dessus
recherche_date = date_debut is not None or date_fin is not None

if recherche_date:

    lignes_trouvees = []

    for f in fichiers_affiches:

        try:
            df = pd.read_excel(f["chemin"])
        except Exception:
            continue

        if COLONNE_DATE not in df.columns:
            continue

        dates = pd.to_datetime(df[COLONNE_DATE], errors="coerce")

        masque = pd.Series(True, index=df.index)

        if date_debut:
            masque &= (dates.dt.date >= date_debut)

        if date_fin:
            masque &= (dates.dt.date <= date_fin)

        resultat_df = df[masque].copy()

        if not resultat_df.empty:
            resultat_df.insert(0, "Fichier", f["nom"])
            resultat_df.insert(1, "Theme", f["theme"])
            lignes_trouvees.append(resultat_df)

    if lignes_trouvees:

        resultat = pd.concat(lignes_trouvees, ignore_index=True)

        st.info(f"📄 {len(resultat):,} ligne(s) trouvée(s)")

        st.dataframe(resultat, use_container_width=True, height=600)

        csv = resultat.to_csv(index=False).encode("utf-8")

        st.download_button("Télécharger les résultats", csv, "resultats_recherche.csv", "text/csv")

    else:
        st.warning("Aucune ligne trouvée pour cette période.")

# Sinon affichage normal des fichiers
else:

    st.markdown("""
### 📁 Fichiers disponibles
""")

    if not fichiers_affiches:
        st.info("Aucun fichier ne correspond à ces critères.")

    for f in fichiers_affiches:

        periode = "date inconnue"

        if f["date_min"] and f["date_max"]:
            dmin = datetime.fromisoformat(f["date_min"]).strftime("%Y-%m-%d")
            dmax = datetime.fromisoformat(f["date_max"]).strftime("%Y-%m-%d")
            periode = dmin if dmin == dmax else f"{dmin} au {dmax}"

        with st.container(border=True):

            c1, c2, c3, c4, c5 = st.columns([3, 1.5, 1.5, 1, 1])

            c1.markdown(f"**{f['nom']}**")
            c2.markdown(f"`{f['theme']}`")
            c3.caption(f"{periode} • {f['nb_lignes']} lignes")

            voir = c4.button("👁 Consulter", key=f"apercu_{f['id']}")
            supprimer = c5.button("🗑 Supprimer", key=f"suppr_{f['id']}")

            if supprimer:
                supprimer_fichier(f["id"], f["chemin"])
                st.rerun()

            if voir:
                st.session_state[f"ouvrir_{f['id']}"] = not st.session_state.get(f"ouvrir_{f['id']}", False)

            if st.session_state.get(f"ouvrir_{f['id']}"):

                df_contenu = pd.read_excel(f["chemin"])

                st.dataframe(df_contenu, use_container_width=True)

                csv = df_contenu.to_csv(index=False).encode("utf-8")

                st.download_button(
                    "Télécharger en CSV",
                    csv,
                    f"{f['nom']}.csv",
                    "text/csv",
                    key=f"dl_{f['id']}"
                )

                with open(f["chemin"], "rb") as fh:
                    st.download_button(
                        "Télécharger l'Excel original",
                        fh.read(),
                        f["nom"],
                        key=f"dlxlsx_{f['id']}"
                    )
