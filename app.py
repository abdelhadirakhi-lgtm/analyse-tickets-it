from pathlib import Path
import io
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

st.set_page_config(page_title="Analyse des tickets IT", page_icon="📊", layout="wide")

FICHIER_EXCEL = "01_Technologie_IT.xlsx"

@st.cache_data
def charger_donnees(source, nom_feuille="Données"):
    df = pd.read_excel(source, sheet_name=nom_feuille, header=2)
    df.columns = [str(c).strip() for c in df.columns]
    obligatoires = ["ID ticket", "Date ouverture", "Service", "Canal", "Type de demande", "Priorité", "Réponse (h)", "Résolution (h)", "Statut", "Objectif SLA (h)"]
    manquantes = [c for c in obligatoires if c not in df.columns]
    if manquantes:
        raise ValueError("Colonnes manquantes dans le fichier Excel : " + ", ".join(manquantes))
    df["Date ouverture"] = pd.to_datetime(df["Date ouverture"], errors="coerce")
    for col in ["Réponse (h)", "Résolution (h)", "Objectif SLA (h)", "Satisfaction /5"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["Mois"] = df["Date ouverture"].dt.to_period("M").astype(str)
    df["SLA dépassé"] = pd.NA
    resolus = df["Statut"].eq("Résolu") & df["Résolution (h)"].notna() & df["Objectif SLA (h)"].notna()
    df.loc[resolus, "SLA dépassé"] = df.loc[resolus, "Résolution (h)"] > df.loc[resolus, "Objectif SLA (h)"]
    return df

st.title("📊 Analyse des tickets de support informatique")
st.caption("Tableau de bord interactif — données analysées avec pandas et graphiques matplotlib.")

fichier_local = Path(__file__).resolve().parent / FICHIER_EXCEL
if fichier_local.exists():
    try:
        df = charger_donnees(str(fichier_local))
    except Exception as exc:
        st.error(f"Impossible de lire le fichier Excel : {exc}")
        st.stop()
else:
    fichier_charge = st.file_uploader("Téléversez le fichier Excel 01_Technologie_IT.xlsx", type=["xlsx"])
    if fichier_charge is None:
        st.info("Ajoutez le fichier Excel au dépôt GitHub avec app.py, ou téléversez-le ici.")
        st.stop()
    try:
        df = charger_donnees(fichier_charge)
    except Exception as exc:
        st.error(f"Impossible de lire le fichier Excel : {exc}")
        st.stop()

with st.sidebar:
    st.header("Filtres")
    dates = df["Date ouverture"].dropna()
    if not dates.empty:
        date_min, date_max = dates.min().date(), dates.max().date()
        periode = st.date_input("Période d'ouverture", value=(date_min, date_max), min_value=date_min, max_value=date_max)
        if isinstance(periode, tuple) and len(periode) == 2:
            debut, fin = pd.Timestamp(periode[0]), pd.Timestamp(periode[1])
            df = df[df["Date ouverture"].between(debut, fin + pd.Timedelta(days=1) - pd.Timedelta(seconds=1))]
    for col, titre in [("Service", "Service"), ("Priorité", "Priorité"), ("Canal", "Canal"), ("Statut", "Statut"), ("Type de demande", "Type de demande")]:
        valeurs = sorted(df[col].dropna().astype(str).unique().tolist())
        selection = st.multiselect(titre, valeurs, default=valeurs)
        df = df[df[col].astype(str).isin(selection)]

if df.empty:
    st.warning("Aucun ticket ne correspond aux filtres sélectionnés.")
    st.stop()

resolus = df[df["Statut"].eq("Résolu") & df["Résolution (h)"].notna() & df["Objectif SLA (h)"].notna()].copy()
resolus["SLA dépassé"] = resolus["Résolution (h)"] > resolus["Objectif SLA (h)"]
nb_tickets = len(df)
nb_resolus = len(resolus)
nb_depassements = int(resolus["SLA dépassé"].sum()) if nb_resolus else 0
taux_sla = nb_depassements / nb_resolus * 100 if nb_resolus else 0
mediane_resolution = resolus["Résolution (h)"].median() if nb_resolus else float("nan")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Tickets dans la sélection", f"{nb_tickets:,}".replace(",", " "))
c2.metric("Tickets résolus analysables", f"{nb_resolus:,}".replace(",", " "))
c3.metric("Dépassements SLA", f"{nb_depassements:,}".replace(",", " "))
c4.metric("Taux de dépassement SLA", f"{taux_sla:.1f}%" if nb_resolus else "N/D")
if not df["Date ouverture"].dropna().empty:
    st.caption(f"Période affichée : {df['Date ouverture'].min():%d/%m/%Y} – {df['Date ouverture'].max():%d/%m/%Y}. Les tickets non résolus ne sont pas comptés comme des dépassements SLA.")

onglets = st.tabs(["Vue d'ensemble", "Services", "SLA & priorités", "Canaux", "Évolution mensuelle", "Données"])

with onglets[0]:
    st.subheader("1. Types de demandes les plus fréquents")
    volumes_types = df["Type de demande"].value_counts().sort_values(ascending=False)
    if not volumes_types.empty:
        top_type, top_n = volumes_types.index[0], int(volumes_types.iloc[0])
        st.write(f"Type le plus fréquent : **{top_type}** — {top_n} tickets ({top_n / len(df) * 100:.1f} % de la sélection).")
        fig, ax = plt.subplots(figsize=(9, 4.5))
        volumes_types.sort_values().plot(kind="barh", ax=ax)
        ax.set(title="Nombre de tickets par type de demande", xlabel="Nombre de tickets", ylabel="Type de demande")
        ax.grid(axis="x", alpha=.25); fig.tight_layout(); st.pyplot(fig); plt.close(fig)

with onglets[1]:
    st.subheader("2. Services les plus sollicités et délais de résolution")
    volumes = df["Service"].value_counts().rename("Nombre de tickets")
    medians = resolus.groupby("Service")["Résolution (h)"].median().rename("Délai médian de résolution (h)")
    resume_services = pd.concat([volumes, medians], axis=1).sort_values("Nombre de tickets", ascending=False)
    if not resume_services.empty:
        service_top = resume_services.index[0]
        med = resume_services.iloc[0]["Délai médian de résolution (h)"]
        med_text = f"{med:.2f} h" if pd.notna(med) else "non disponible"
        st.write(f"Service recevant le plus de tickets : **{service_top}** ({int(resume_services.iloc[0]['Nombre de tickets'])} tickets). Délai médian de résolution : **{med_text}**.")
    st.dataframe(resume_services.round(2), use_container_width=True)

with onglets[2]:
    st.subheader("3. Dépassements SLA par priorité")
    if nb_resolus:
        sla = resolus.groupby("Priorité").agg(Tickets_résolus=("ID ticket", "count"), Dépassements=("SLA dépassé", "sum"))
        sla["Taux de dépassement (%)"] = sla["Dépassements"] / sla["Tickets_résolus"] * 100
        ordre = [p for p in ["Critique", "Haute", "Normale"] if p in sla.index]
        sla = sla.reindex(ordre + [p for p in sla.index if p not in ordre])
        st.write(f"Au total, **{nb_depassements}/{nb_resolus}** tickets résolus analysables dépassent l'objectif SLA ({taux_sla:.1f} %).")
        st.dataframe(sla.round(2), use_container_width=True)
        fig, ax = plt.subplots(figsize=(8, 4))
        sla["Taux de dépassement (%)"].plot(kind="bar", ax=ax)
        ax.set(title="Taux de dépassement SLA par priorité", xlabel="Priorité", ylabel="Tickets dépassant le SLA (%)", ylim=(0, 100))
        ax.tick_params(axis="x", rotation=0); ax.grid(axis="y", alpha=.25); fig.tight_layout(); st.pyplot(fig); plt.close(fig)
    else:
        st.info("Aucun ticket résolu avec délai et objectif SLA disponibles dans cette sélection.")

with onglets[3]:
    st.subheader("4. Temps de première réponse selon le canal")
    resume_canaux = df.groupby("Canal")["Réponse (h)"].agg(Nombre="count", Médiane="median", Moyenne="mean").sort_values("Médiane")
    st.dataframe(resume_canaux.round(2), use_container_width=True)
    canaux = [c for c in df["Canal"].dropna().unique() if df.loc[df["Canal"].eq(c), "Réponse (h)"].notna().any()]
    donnees = [df.loc[df["Canal"].eq(c), "Réponse (h)"].dropna().to_numpy() for c in canaux]
    if donnees:
        fig, ax = plt.subplots(figsize=(9, 4.5))
        ax.boxplot(donnees, tick_labels=canaux, showmeans=True)
        ax.set(title="Temps de première réponse selon le canal", xlabel="Canal d'entrée", ylabel="Temps de première réponse (heures)")
        ax.grid(axis="y", alpha=.25); fig.tight_layout(); st.pyplot(fig); plt.close(fig)
        if not resume_canaux["Médiane"].dropna().empty:
            st.write(f"Médiane la plus faible : **{resume_canaux['Médiane'].idxmin()}** ({resume_canaux['Médiane'].min():.2f} h). Médiane la plus élevée : **{resume_canaux['Médiane'].idxmax()}** ({resume_canaux['Médiane'].max():.2f} h).")

with onglets[4]:
    st.subheader("5. Évolution mensuelle du volume et des dépassements SLA")
    mensuel = df.groupby("Mois").size().rename("Tickets ouverts").to_frame()
    dep = resolus[resolus["SLA dépassé"]].groupby("Mois").size().rename("Dépassements SLA")
    taux = resolus.groupby("Mois")["SLA dépassé"].mean().mul(100).rename("Taux de dépassement parmi les tickets résolus (%)")
    resume_mensuel = mensuel.join(dep, how="left").join(taux, how="left").fillna({"Dépassements SLA": 0})
    resume_mensuel["Dépassements SLA"] = resume_mensuel["Dépassements SLA"].astype(int)
    st.dataframe(resume_mensuel.round(1), use_container_width=True)
    if not resume_mensuel.empty:
        fig, ax1 = plt.subplots(figsize=(10, 4.8))
        x = list(range(len(resume_mensuel)))
        ax1.plot(x, resume_mensuel["Tickets ouverts"], marker="o", label="Tickets ouverts")
        ax1.set_ylabel("Nombre de tickets ouverts"); ax1.set_xlabel("Mois")
        ax1.set_xticks(x, resume_mensuel.index, rotation=45); ax1.grid(alpha=.25)
        ax2 = ax1.twinx(); ax2.plot(x, resume_mensuel["Dépassements SLA"], marker="s", linestyle="--", label="Dépassements SLA")
        ax2.set_ylabel("Nombre de dépassements SLA")
        h1, l1 = ax1.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
        ax1.legend(h1+h2, l1+l2, loc="upper left")
        ax1.set_title("Évolution mensuelle du volume et des dépassements SLA")
        fig.tight_layout(); st.pyplot(fig); plt.close(fig)
        mois_top = resume_mensuel["Tickets ouverts"].idxmax()
        mois_sla = resume_mensuel["Dépassements SLA"].idxmax()
        st.write(f"Volume maximal : **{mois_top}** ({int(resume_mensuel.loc[mois_top, 'Tickets ouverts'])} tickets). Maximum de dépassements SLA : **{mois_sla}** ({int(resume_mensuel.loc[mois_sla, 'Dépassements SLA'])}).")

with onglets[5]:
    st.subheader("Données filtrées")
    st.dataframe(df.drop(columns=["Mois", "SLA dépassé"], errors="ignore"), use_container_width=True, hide_index=True)
    sortie = io.BytesIO()
    with pd.ExcelWriter(sortie, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Tickets filtres", index=False)
    st.download_button("Télécharger les données filtrées (Excel)", data=sortie.getvalue(), file_name="tickets_filtres.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

st.divider()
st.subheader("6. Recommandation opérationnelle")
if nb_resolus and not resolus.empty:
    taux_priorite = resolus.groupby("Priorité")["SLA dépassé"].mean().mul(100).dropna()
    if not taux_priorite.empty:
        pire_priorite = taux_priorite.idxmax()
        pire_taux = taux_priorite.max()
        types = df["Type de demande"].value_counts()
        if not types.empty:
            top_type, top_n = types.index[0], int(types.iloc[0])
            st.write(f"Mettre en place un plan de réduction des dépassements SLA en analysant en priorité les tickets de priorité **{pire_priorite}** (taux de dépassement : **{pire_taux:.1f} %**). Examiner aussi le type **{top_type}**, le plus fréquent dans la sélection ({top_n} tickets), afin d'identifier les causes récurrentes et de standardiser les solutions.")
        else:
            st.write(f"Analyser les causes des dépassements SLA pour la priorité **{pire_priorite}** (taux : {pire_taux:.1f} %) et suivre cet indicateur chaque mois.")
    else:
        st.info("Les données sélectionnées ne permettent pas de calculer un taux SLA par priorité.")
else:
    st.info("Il faut des tickets résolus avec un délai et un objectif SLA renseignés pour générer une recommandation sur le SLA.")
st.caption("Note : une différence entre canaux ou priorités est descriptive et ne prouve pas, à elle seule, une relation de cause à effet.")
