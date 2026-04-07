"""
DocuFlow AI — Historique des Documents
Liste paginée, filtres avancés, détails, texte OCR, export PDF, suppression.
"""

import streamlit as st
import json
import pandas as pd
from styles import apply_theme, render_sidebar
from auth import is_authenticated, get_current_user, require_role
from database import DatabaseManager
from config import DOCUMENT_TYPES

if not is_authenticated():
    st.switch_page("app.py")
    st.stop()

apply_theme()
user = get_current_user()
render_sidebar(user)

st.markdown("""
<div class="main-header">
    <h1>📋 Historique des Documents</h1>
    <p>Consultez et gérez tous les documents traités</p>
</div>
""", unsafe_allow_html=True)

db = DatabaseManager()

# ── Filtres ──────────────────────────────────────────────────────────
st.markdown("### 🔍 Filtres")
fcol1, fcol2, fcol3, fcol4 = st.columns(4)

with fcol1:
    filtre_fournisseur = st.text_input("Fournisseur", placeholder="Rechercher...")
with fcol2:
    filtre_date_from = st.date_input("Date début", value=None)
with fcol3:
    filtre_date_to = st.date_input("Date fin", value=None)
with fcol4:
    type_options = ["Tous"] + list(DOCUMENT_TYPES.values())
    type_keys = [None] + list(DOCUMENT_TYPES.keys())
    filtre_type_label = st.selectbox("Type de document", type_options)
    filtre_type = type_keys[type_options.index(filtre_type_label)]

# ── Récupérer les documents ──────────────────────────────────────────
try:
    documents = db.get_documents(
        fournisseur=filtre_fournisseur if filtre_fournisseur else None,
        date_from=str(filtre_date_from) if filtre_date_from else None,
        date_to=str(filtre_date_to) if filtre_date_to else None,
        doc_type=filtre_type,
        limit=100
    )
except Exception as e:
    st.error(f"❌ Erreur BDD : {e}")
    documents = []

st.markdown(f"### 📄 {len(documents)} document(s) trouvé(s)")

if not documents:
    st.info("📭 Aucun document dans l'historique. Allez dans **Extraction** pour commencer.")
    st.stop()

# ── Tableau récapitulatif ────────────────────────────────────────────
for doc in documents:
    doc_class = doc.get("document_class", "facture") or "facture"
    doc_type_label = DOCUMENT_TYPES.get(doc_class, doc_class.title())
    conf = doc.get("confidence_score")
    conf_str = f" · 🎯 {float(conf)*100:.0f}%" if conf else ""

    with st.expander(
        f"{'✅' if doc.get('is_valid') else '⚠️'} "
        f"**{doc.get('file_name', 'Document')}** — "
        f"{doc.get('fournisseur_nom', 'N/A')} — "
        f"{doc.get('facture_numero', 'N/A')} — "
        f"{doc.get('total_ttc', 0):.3f} TND — "
        f"📋 {doc_type_label}{conf_str}"
    ):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"""
            <div class="info-card">
                <h3>🏢 Fournisseur</h3>
                <p><strong>{doc.get('fournisseur_nom', 'N/A')}</strong></p>
                <p>{doc.get('fournisseur_adresse', 'N/A') or 'N/A'}</p>
                <p>📞 {doc.get('fournisseur_telephone', 'N/A') or 'N/A'}</p>
                <p>🔢 MF: {doc.get('fournisseur_matricule_fiscal', 'N/A') or 'N/A'}</p>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div class="info-card">
                <h3>👤 Client & Facture</h3>
                <p><strong>Client :</strong> {doc.get('client_nom', 'N/A') or 'N/A'}</p>
                <p>📄 <strong>N° :</strong> {doc.get('facture_numero', 'N/A')}</p>
                <p>📅 <strong>Date :</strong> {doc.get('facture_date', 'N/A')}</p>
                <p>💱 <strong>Devise :</strong> {doc.get('facture_devise', 'TND')}</p>
            </div>
            """, unsafe_allow_html=True)

        # Totaux
        tc1, tc2, tc3 = st.columns(3)
        with tc1:
            st.metric("Total HT", f"{doc.get('total_ht', 0) or 0:.3f} TND")
        with tc2:
            st.metric("Total TVA", f"{doc.get('total_tva', 0) or 0:.3f} TND")
        with tc3:
            st.metric("Total TTC", f"{doc.get('total_ttc', 0) or 0:.3f} TND")

        # Articles (depuis raw_json)
        raw_json = doc.get("raw_json")
        parsed_json = None
        if raw_json:
            if isinstance(raw_json, str):
                parsed_json = json.loads(raw_json)
            else:
                parsed_json = raw_json

            articles = parsed_json.get("articles", [])
            if articles:
                st.markdown(f"**📦 {len(articles)} article(s)**")
                df = pd.DataFrame(articles)
                col_rename = {
                    "reference": "Référence",
                    "designation": "Désignation", "quantite": "Quantité",
                    "prix_unitaire": "Prix Unitaire", "total_ligne": "Total Ligne"
                }
                df = df.rename(columns={k: v for k, v in col_rename.items() if k in df.columns})
                st.dataframe(df, use_container_width=True, hide_index=True)

        # JSON brut (pas d'expander imbriqué)
        if parsed_json:
            show_json = st.checkbox("🔍 Afficher JSON brut", key=f"show_json_{doc['id']}")
            if show_json:
                st.json(parsed_json)

        # Boutons d'action
        action_cols = st.columns(3)

        # Export PDF unitaire
        with action_cols[0]:
            try:
                from pdf_export import generate_document_pdf
                pdf_bytes = generate_document_pdf(doc)
                st.download_button(
                    "📕 Télécharger PDF",
                    data=pdf_bytes,
                    file_name=f"docuflow_{doc.get('facture_numero', doc['id'])}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key=f"pdf_{doc['id']}"
                )
            except Exception as e:
                st.caption(f"PDF indisponible : {e}")

        # Export JSON
        with action_cols[1]:
            if parsed_json:
                json_str = json.dumps(parsed_json, indent=2, ensure_ascii=False)
                st.download_button(
                    "⬇️ Télécharger JSON",
                    data=json_str,
                    file_name=f"extraction_{doc['id']}.json",
                    mime="application/json",
                    use_container_width=True,
                    key=f"json_{doc['id']}"
                )

        # Suppression (comptable + admin)
        with action_cols[2]:
            if require_role("comptable"):
                if st.button(f"🗑️ Supprimer", key=f"del_{doc['id']}", use_container_width=True):
                    try:
                        db.delete_document(doc["id"])
                        db.log_action(user["user_id"], "delete_document", {"document_id": doc["id"]})
                        st.success("Document supprimé")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {e}")
