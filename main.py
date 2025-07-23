from complet import (
    read_pdf,
    extract_company_info,
    collect_company_data,
    generate_enhanced_porter_analysis,
    create_enhanced_pdf_report,
    INPUT_PDF_PATH,
    OUTPUT_PDF_PATH
)
import streamlit as st

import os
from datetime import datetime
import time

# === Configuration de la page ===
st.set_page_config(page_title="Analyse Porter Enrichie", layout="wide")
st.title("📊 Analyse Porter Enrichie par IA")
st.caption("Utilise un PDF statique situé dans `pdfs/document.pdf`")

# === Vérification du fichier ===
if not os.path.exists(INPUT_PDF_PATH):
    st.error("❌ Fichier `document.pdf` introuvable dans le dossier `pdfs/`.")
    st.info("💡 Placez un fichier PDF ici : `pdfs/document.pdf`.")
    st.stop()

st.success("📁 Fichier détecté : prêt pour l'analyse !")

# === Initialisation de la session ===
if "progress" not in st.session_state:
    st.session_state.progress = 0

def update_progress(step, total_steps):
    st.session_state.progress = int((step / total_steps) * 100)
    progress_bar.progress(st.session_state.progress)

# === Barre de progression ===
progress_bar = st.progress(0, text="En attente de démarrage...")

# === Lancement de l'analyse ===
if st.button("🚀 Démarrer l'analyse enrichie"):

    total_steps = 5
    step = 1

    with st.spinner("📥 Lecture du document PDF..."):
        time.sleep(0.8)
        original_text = read_pdf(INPUT_PDF_PATH)
        st.success(f"✅ Document lu ({len(original_text)} caractères)")
        update_progress(step, total_steps)
        step += 1

    with st.spinner("🔍 Extraction des informations sur l’entreprise..."):
        time.sleep(0.8)
        company_info = extract_company_info(original_text)
        if company_info:
            st.success(f"🏢 Entreprise détectée : {company_info.get('nom_entreprise', 'N/A')}")
            st.markdown("**Domaines d'activité** : " + ", ".join(company_info.get("domaines_activite", [])))
            with st.expander("📄 Détails JSON"):
                st.json(company_info)
        else:
            st.warning("⚠️ Aucune donnée extraite, on continue malgré tout.")
        update_progress(step, total_steps)
        step += 1

    with st.spinner("🌐 Recherche web et collecte d'informations..."):
        time.sleep(0.8)
        web_data = collect_company_data(company_info) if company_info else {}
        total_sources = sum(len(v) for v in web_data.values() if isinstance(v, list))
        st.info(f"🔎 {total_sources} sources web collectées.")
        if total_sources > 0:
            with st.expander("📚 Aperçu des données collectées"):
                st.json(web_data)
        update_progress(step, total_steps)
        step += 1

    with st.spinner("🧠 Génération de l’analyse Porter enrichie... (cela peut prendre quelques minutes)"):
        analysis = generate_enhanced_porter_analysis(original_text, company_info, web_data)
        st.success("✅ Analyse stratégique générée avec succès.")
        with st.expander("📝 Aperçu du rapport généré"):
            st.text_area("Contenu partiel du rapport", analysis[:5000], height=400)
        update_progress(step, total_steps)
        step += 1

    with st.spinner("💾 Création du rapport PDF..."):
        create_enhanced_pdf_report(analysis, company_info, OUTPUT_PDF_PATH)
        st.success("📄 Rapport PDF généré avec succès !")
        update_progress(step, total_steps)

        with open(OUTPUT_PDF_PATH, "rb") as f:
            st.download_button(
                label="📥 Télécharger le rapport PDF",
                data=f,
                file_name="rapport_porter_enrichi.pdf",
                mime="application/pdf"
            )

    st.balloons()
    st.success("🎉 Analyse terminée avec succès !")