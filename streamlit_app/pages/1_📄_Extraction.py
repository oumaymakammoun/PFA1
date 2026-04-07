"""
DocuFlow AI — Page d'extraction de documents
Upload, OCR, extraction structurée, classification, validation.
Mode batch avec retry automatique pour plusieurs documents.
"""

import streamlit as st
import json
import pandas as pd
from PIL import Image
from io import BytesIO
from styles import apply_theme, render_sidebar
from auth import is_authenticated, get_current_user, require_role
from ocr_engine import extract_with_mistral
from ai_engine import enrich_extraction, get_confidence_label
from batch_processor import BatchProcessor
from database import DatabaseManager

# ── Vérification authentification ────────────────────────────────────
if not is_authenticated():
    st.switch_page("app.py")
    st.stop()

apply_theme()
user = get_current_user()
render_sidebar(user)

# ── Header ───────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>📄 Extraction de Documents</h1>
    <p>Uploadez une facture, un bon de livraison ou un reçu pour extraction automatique</p>
</div>
""", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════
#  Fonction utilitaire pour afficher les résultats d'extraction
# ═════════════════════════════════════════════════════════════════════

def _render_extraction_result(extraction: dict, metadata: dict, file_name: str):
    """Affiche les résultats d'une extraction (utilisé en mode single et batch)."""

    # ── Bannière succès ──
    doc_type = metadata.get("document_type", "facture").replace("_", " ").title()
    conf_score = metadata.get("confidence_score", 0)
    conf_label, conf_class = get_confidence_label(conf_score)

    st.markdown(f"""
    <div class="success-card">
        <h3>✅ Extraction réussie</h3>
        <p>Type : <strong>{doc_type}</strong> · Confiance : <span class="{conf_class}">{conf_score:.0%} ({conf_label})</span></p>
    </div>
    """, unsafe_allow_html=True)

    # ── Anomalies ──
    anomalies = metadata.get("anomalies", [])
    if anomalies:
        with st.expander(f"⚠️ {len(anomalies)} anomalie(s) détectée(s)", expanded=True):
            for a in anomalies:
                icon = "🔴" if a["severity"] == "error" else "🟡" if a["severity"] == "warning" else "🔵"
                st.markdown(f"{icon} **{a['field']}** — {a['issue']}")

    # ── Scores de confiance ──
    scores = metadata.get("confidence_scores", {})
    if scores:
        with st.expander("📊 Scores de confiance par section"):
            score_cols = st.columns(5)
            for i, (section, score) in enumerate(scores.items()):
                if section != "global":
                    label, css = get_confidence_label(score)
                    with score_cols[i % 5]:
                        st.metric(section.capitalize(), f"{score:.0%}")

    # ── Fournisseur & Client ──
    col1, col2 = st.columns(2)
    fournisseur = extraction.get("fournisseur", {})
    client_data = extraction.get("client", {})
    facture = extraction.get("facture", {})

    with col1:
        st.markdown(f"""
        <div class="info-card">
            <h3>🏢 Fournisseur</h3>
            <p><strong>{fournisseur.get('nom', 'N/A')}</strong></p>
            <p>{fournisseur.get('adresse', 'N/A')}</p>
            <p>📞 {fournisseur.get('telephone', 'N/A') or 'N/A'}</p>
            <p>📧 {fournisseur.get('email', 'N/A') or 'N/A'}</p>
            <p>🔢 MF: {fournisseur.get('matricule_fiscal', 'N/A') or 'N/A'}</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="info-card">
            <h3>👤 Client & Facture</h3>
            <p><strong>Client :</strong> {client_data.get('nom', 'N/A') or 'N/A'}</p>
            <p><strong>Adresse :</strong> {client_data.get('adresse', 'N/A') or 'N/A'}</p>
            <p>📄 <strong>N° :</strong> {facture.get('numero', 'N/A')}</p>
            <p>📅 <strong>Date :</strong> {facture.get('date', 'N/A')}</p>
            <p>💱 <strong>Devise :</strong> {facture.get('devise', 'N/A')}</p>
        </div>
        """, unsafe_allow_html=True)

    # ── Articles ──
    articles = extraction.get("articles", [])
    if articles:
        st.markdown("### 📦 Articles")
        df = pd.DataFrame(articles)
        col_rename = {"reference": "Référence", "designation": "Désignation",
                      "quantite": "Quantité", "prix_unitaire": "Prix Unitaire",
                      "total_ligne": "Total Ligne"}
        df = df.rename(columns={k: v for k, v in col_rename.items() if k in df.columns})
        st.dataframe(df, use_container_width=True, hide_index=True)

    # ── Totaux ──
    totaux = extraction.get("totaux", {})
    if totaux:
        devise = facture.get("devise", "TND")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f'<div class="stat-box"><div class="stat-number">{totaux.get("total_ht", 0):.3f}</div><div class="stat-label">Total HT ({devise})</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="stat-box"><div class="stat-number">{totaux.get("total_tva", 0):.3f}</div><div class="stat-label">Total TVA ({devise})</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="stat-box"><div class="stat-number">{totaux.get("total_ttc", 0):.3f}</div><div class="stat-label">Total TTC ({devise})</div></div>', unsafe_allow_html=True)
        with c4:
            timbre = totaux.get("timbre_fiscal")
            timbre_display = f"{timbre:.3f}" if timbre else "—"
            st.markdown(f'<div class="stat-box"><div class="stat-number">{timbre_display}</div><div class="stat-label">Timbre</div></div>', unsafe_allow_html=True)

    # ── Export JSON ──
    json_str = json.dumps(extraction, indent=2, ensure_ascii=False)
    st.download_button(
        "⬇️ Télécharger JSON",
        data=json_str,
        file_name=f"extraction_{file_name.rsplit('.', 1)[0]}.json",
        mime="application/json",
        use_container_width=True,
        key=f"dl_json_{file_name}"
    )

    with st.expander("🔍 JSON brut"):
        st.json(extraction)


# ── Upload ───────────────────────────────────────────────────────────
st.markdown("### 📤 Uploader un document")

uploaded_files = st.file_uploader(
    "Glissez-déposez un ou plusieurs documents",
    type=["png", "jpg", "jpeg", "pdf", "tiff", "bmp", "webp"],
    accept_multiple_files=True,
    help="Formats supportés : PNG, JPG, PDF, TIFF, BMP, WebP"
)

if uploaded_files:

    # ═════════════════════════════════════════════════════════════════
    #  MODE BATCH — Plusieurs fichiers
    # ═════════════════════════════════════════════════════════════════
    if len(uploaded_files) > 1:
        st.markdown(f"""
        <div class="info-card">
            <h3>📦 Mode Batch</h3>
            <p><strong>{len(uploaded_files)}</strong> documents détectés —
               Traitement séquentiel avec retry automatique (3 tentatives max)</p>
        </div>
        """, unsafe_allow_html=True)

        # Aperçu des fichiers
        with st.expander(f"📄 Aperçu des {len(uploaded_files)} fichiers"):
            for uf in uploaded_files:
                st.caption(f"• {uf.name} ({uf.size / 1024:.1f} Ko)")

        col_batch1, col_batch2 = st.columns([1, 1])
        with col_batch1:
            batch_btn = st.button(
                "🚀 Traiter tout en batch",
                type="primary", use_container_width=True
            )
        with col_batch2:
            single_mode = st.button(
                "📄 Traiter un par un",
                use_container_width=True
            )

        if batch_btn:
            st.markdown("---")
            st.markdown("### ⚙️ Traitement Batch en cours...")

            progress_bar = st.progress(0, text="Préparation...")
            status_container = st.container()

            # Préparer les fichiers
            files = []
            for uf in uploaded_files:
                uf.seek(0)
                files.append({
                    "file_name": uf.name,
                    "file_bytes": uf.read(),
                    "mime_type": uf.type,
                })

            # Callbacks pour la progression
            status_messages = {}

            def update_progress(p):
                progress_bar.progress(min(p, 1.0), text=f"Progression : {p:.0%}")

            def update_status(index, status, message):
                status_messages[index] = (status, message)
                with status_container:
                    for idx in sorted(status_messages.keys()):
                        s, m = status_messages[idx]
                        if s == "success":
                            st.success(m)
                        elif s == "failed":
                            st.error(m)
                        elif s == "retrying":
                            st.warning(m)
                        else:
                            st.info(m)

            # Lancer le batch
            processor = BatchProcessor(max_retries=3)
            batch_result = processor.process_batch(
                files=files,
                extract_fn=extract_with_mistral,
                enrich_fn=enrich_extraction,
                progress_callback=update_progress,
                status_callback=update_status,
            )

            progress_bar.progress(1.0, text="✅ Batch terminé !")

            # Résumé du batch
            st.markdown(f"""
            <div class="{'success-card' if batch_result.failed == 0 else 'warning-card'}">
                <h3>{'✅' if batch_result.failed == 0 else '⚠️'} Résultat du Batch</h3>
                <p>
                    ✅ <strong>{batch_result.success}</strong> réussi(s) ·
                    ❌ <strong>{batch_result.failed}</strong> échoué(s) ·
                    🔄 <strong>{batch_result.retried}</strong> réessayé(s) ·
                    ⏱️ <strong>{batch_result.total_time:.1f}s</strong> au total
                </p>
                <p>Taux de succès : <strong>{batch_result.success_rate:.0f}%</strong></p>
            </div>
            """, unsafe_allow_html=True)

            # Sauvegarder les résultats en BDD
            db = DatabaseManager()
            saved_count = 0
            for item in batch_result.items:
                if item.status == "success" and item.result.get("success"):
                    try:
                        extraction = item.result["extraction"]
                        metadata = item.result["metadata"]
                        doc_id = db.save_document(user["user_id"], extraction, metadata)
                        db.log_action(user["user_id"], "extraction_batch", {
                            "file": item.file_name,
                            "document_id": doc_id,
                            "type": metadata.get("document_type", "facture"),
                            "attempts": item.attempts,
                        })
                        saved_count += 1
                    except Exception as e:
                        st.warning(f"⚠️ Sauvegarde échouée pour {item.file_name}: {e}")

            if saved_count > 0:
                st.info(f"💾 {saved_count} document(s) sauvegardé(s) en base de données")

            # Détails par document
            for item in batch_result.items:
                if item.status == "success" and item.result.get("success"):
                    extraction = item.result["extraction"]
                    metadata = item.result["metadata"]
                    with st.expander(
                        f"✅ {item.file_name} — "
                        f"{metadata.get('document_type', 'facture').title()} — "
                        f"{extraction.get('totaux', {}).get('total_ttc', 0):.3f} TND"
                    ):
                        _render_extraction_result(extraction, metadata, item.file_name)

        # Si "traiter un par un" est cliqué, on tombe dans le mode single ci-dessous
        if not single_mode and not batch_btn:
            st.stop()

    # ═════════════════════════════════════════════════════════════════
    #  MODE SINGLE — Un fichier à la fois
    # ═════════════════════════════════════════════════════════════════
    for uploaded_file in uploaded_files:
        st.divider()
        col_preview, col_result = st.columns([1, 1.5])

        with col_preview:
            st.markdown(f"#### 🖼️ {uploaded_file.name}")
            if uploaded_file.type and uploaded_file.type.startswith("image/"):
                image = Image.open(uploaded_file)
                st.image(image, use_container_width=True)
            else:
                st.info(f"📄 **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} Ko)")

            extract_btn = st.button(
                "🚀 Extraire les données",
                type="primary",
                use_container_width=True,
                key=f"extract_{uploaded_file.name}"
            )

        with col_result:
            if extract_btn:
                st.markdown("#### 📊 Résultats")

                with st.spinner("🔄 Analyse en cours avec Mistral OCR... (5-15 sec)"):
                    uploaded_file.seek(0)
                    file_bytes = uploaded_file.read()

                    # Extraction OCR
                    result = extract_with_mistral(
                        file_bytes=file_bytes,
                        file_name=uploaded_file.name,
                        mime_type=uploaded_file.type
                    )

                    # Enrichissement IA (classification + validation + confiance)
                    if result.get("success"):
                        result = enrich_extraction(result)

                if result.get("success"):
                    extraction = result["extraction"]
                    metadata = result["metadata"]

                    # ── Sauvegarde en BDD ──
                    try:
                        db = DatabaseManager()
                        doc_id = db.save_document(user["user_id"], extraction, metadata)
                        db.log_action(user["user_id"], "extraction", {
                            "file": uploaded_file.name,
                            "document_id": doc_id,
                            "type": metadata.get("document_type", "facture"),
                        })
                        metadata["document_id"] = doc_id
                    except Exception as e:
                        st.warning(f"⚠️ Sauvegarde BDD échouée : {e}")

                    _render_extraction_result(extraction, metadata, uploaded_file.name)

                else:
                    st.error(f"❌ {result.get('error', 'Erreur inconnue')}")



