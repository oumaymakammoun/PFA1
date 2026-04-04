"""
PFA — Interface Streamlit
Traitement Intelligent de Documents Commerciaux
Propulsé par Mistral OCR
"""

import streamlit as st
import requests
import json
import os
import base64
import re
import pandas as pd
from datetime import datetime
from io import BytesIO
from PIL import Image
from mistralai.client import Mistral

# ── Configuration ────────────────────────────────────────────────────
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/facture")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")

# ── Page Config ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="DocuFlow AI — Extraction de Factures",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CSS Personnalisé ─────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Global */
    .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* Header */
    .main-header {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        color: white;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }
    .main-header h1 {
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
        background: linear-gradient(90deg, #f97316, #fb923c, #fbbf24);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .main-header p {
        color: #a5b4fc;
        font-size: 1rem;
        margin: 0.5rem 0 0 0;
    }

    /* Cards */
    .info-card {
        background: linear-gradient(135deg, #1e1b4b, #312e81);
        border: 1px solid rgba(139, 92, 246, 0.3);
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        color: white;
    }
    .info-card h3 {
        color: #a78bfa;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
        font-weight: 600;
    }
    .info-card p {
        color: #e2e8f0;
        font-size: 1rem;
        margin: 0.25rem 0;
    }

    /* Success card */
    .success-card {
        background: linear-gradient(135deg, #064e3b, #065f46);
        border: 1px solid rgba(52, 211, 153, 0.3);
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        color: white;
    }
    .success-card h3 {
        color: #34d399;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
    }

    /* Warning card */
    .warning-card {
        background: linear-gradient(135deg, #78350f, #92400e);
        border: 1px solid rgba(251, 191, 36, 0.3);
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        color: white;
    }
    .warning-card h3 {
        color: #fbbf24;
    }

    /* Stats */
    .stat-box {
        background: linear-gradient(135deg, #1e1b4b, #312e81);
        border: 1px solid rgba(139, 92, 246, 0.2);
        border-radius: 12px;
        padding: 1.25rem;
        text-align: center;
        transition: transform 0.2s ease;
    }
    .stat-box:hover {
        transform: translateY(-2px);
    }
    .stat-number {
        font-size: 1.8rem;
        font-weight: 700;
        background: linear-gradient(90deg, #a78bfa, #60a5fa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .stat-label {
        color: #94a3b8;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Upload area */
    .upload-area {
        background: linear-gradient(135deg, #1e1b4b, #312e81);
        border: 2px dashed rgba(139, 92, 246, 0.4);
        border-radius: 16px;
        padding: 2rem;
        text-align: center;
        transition: border-color 0.3s ease;
    }
    .upload-area:hover {
        border-color: rgba(139, 92, 246, 0.8);
    }

    /* Table styling */
    .article-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 1rem;
    }
    .article-table th {
        background: rgba(139, 92, 246, 0.2);
        color: #a78bfa;
        padding: 0.75rem 1rem;
        text-align: left;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        border-bottom: 2px solid rgba(139, 92, 246, 0.3);
    }
    .article-table td {
        padding: 0.75rem 1rem;
        color: #e2e8f0;
        border-bottom: 1px solid rgba(139, 92, 246, 0.1);
    }
    .article-table tr:hover td {
        background: rgba(139, 92, 246, 0.05);
    }

    /* Hide Streamlit defaults */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
</style>
""", unsafe_allow_html=True)


# ── Session State ────────────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []
if "current_result" not in st.session_state:
    st.session_state.current_result = None


# ── Helper Functions ─────────────────────────────────────────────────

EXTRACTION_PROMPT = """Tu es un expert en extraction de données de factures. Voici le contenu OCR d'une facture.
Extrais les données et retourne UNIQUEMENT un JSON valide avec cette structure exacte :

{
  "fournisseur": {
    "nom": "...",
    "adresse": "...",
    "telephone": "...",
    "email": "...",
    "matricule_fiscal": "..."
  },
  "client": {
    "nom": "...",
    "adresse": "..."
  },
  "facture": {
    "numero": "...",
    "date": "...",
    "devise": "TND"
  },
  "articles": [
    {
      "designation": "...",
      "quantite": 0,
      "prix_unitaire": 0.0,
      "total_ligne": 0.0
    }
  ],
  "totaux": {
    "total_ht": 0.0,
    "total_tva": 0.0,
    "total_ttc": 0.0,
    "timbre_fiscal": null,
    "tva_details": [
      {"taux_pourcent": 19, "montant": 0.0}
    ]
  }
}

Utilise null pour les champs manquants. Utilise des nombres (avec point décimal) pour les montants.
Réponds UNIQUEMENT avec le JSON, sans texte ni explication.

Contenu OCR du document :
"""


def get_mime_type(file_name: str, file_type: str) -> str:
    """Détermine le MIME type pour l'API Mistral."""
    ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    mime_map = {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "tiff": "image/tiff",
        "tif": "image/tiff",
        "bmp": "image/bmp",
        "webp": "image/webp",
    }
    return mime_map.get(ext, file_type or "image/jpeg")


def extract_with_mistral(file_bytes: bytes, file_name: str, mime_type: str) -> dict:
    """Appelle l'API Mistral OCR pour extraire les données de la facture."""
    try:
        if not MISTRAL_API_KEY:
            return {"success": False, "error": "Clé API Mistral non configurée. Ajoutez MISTRAL_API_KEY dans le fichier .env"}

        print(f"[MISTRAL] Starting extraction for {file_name} ({mime_type})")

        client = Mistral(api_key=MISTRAL_API_KEY)

        # ── Étape 1 : OCR avec Mistral ──────────────────────────────
        resolved_mime = get_mime_type(file_name, mime_type)
        base64_data = base64.b64encode(file_bytes).decode("utf-8")
        document_url = f"data:{resolved_mime};base64,{base64_data}"

        print(f"[MISTRAL] Calling OCR API (model: mistral-ocr-latest)...")
        ocr_response = client.ocr.process(
            model="mistral-ocr-latest",
            document={
                "type": "document_url",
                "document_url": document_url,
            },
        )

        # Récupérer le texte OCR de toutes les pages
        ocr_text = ""
        for page in ocr_response.pages:
            ocr_text += page.markdown + "\n\n"

        print(f"[MISTRAL] OCR text length: {len(ocr_text)} chars")
        print(f"[MISTRAL] OCR text (first 500 chars): {ocr_text[:500]}")

        if not ocr_text.strip():
            return {"success": False, "error": "Mistral OCR n'a extrait aucun texte du document. Vérifiez la qualité de l'image."}

        # ── Étape 2 : Extraction structurée avec Pixtral ─────────────
        print(f"[MISTRAL] Calling chat API for structured extraction...")
        chat_response = client.chat.complete(
            model="mistral-small-latest",
            messages=[
                {
                    "role": "user",
                    "content": EXTRACTION_PROMPT + ocr_text,
                }
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        raw_content = chat_response.choices[0].message.content
        print(f"[MISTRAL] Chat response (first 500 chars): {raw_content[:500]}")

        # Nettoyer les balises markdown
        raw_content = re.sub(r'^```json\s*', '', raw_content.strip())
        raw_content = re.sub(r'^```\s*', '', raw_content)
        raw_content = re.sub(r'\s*```$', '', raw_content)

        # Extraire le JSON
        first_brace = raw_content.find('{')
        last_brace = raw_content.rfind('}')

        if first_brace == -1 or last_brace == -1:
            return {"success": False, "error": f"Pas de JSON dans la réponse Mistral : {raw_content[:300]}"}

        json_str = raw_content[first_brace:last_brace + 1]

        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError:
            # Tentative de correction
            json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
            try:
                parsed = json.loads(json_str)
            except json.JSONDecodeError as e:
                return {"success": False, "error": f"JSON invalide : {str(e)} | Contenu : {json_str[:300]}"}

        # Validation
        warnings = []
        if not parsed.get("fournisseur", {}).get("nom"):
            warnings.append("Nom fournisseur manquant")
        if not parsed.get("facture", {}).get("numero"):
            warnings.append("Numéro facture manquant")
        if not parsed.get("articles") or len(parsed["articles"]) == 0:
            warnings.append("Aucun article extrait")
        if parsed.get("totaux", {}).get("total_ttc") is None:
            warnings.append("Total TTC manquant")

        return {
            "success": True,
            "extraction": parsed,
            "metadata": {
                "source_file": file_name,
                "extraction_date": datetime.now().isoformat(),
                "model_used": "mistral-ocr-latest + mistral-small-latest",
                "validation_warnings": warnings,
                "is_valid": len(warnings) == 0,
                "nombre_articles": len(parsed.get("articles", [])),
                "ocr_text_length": len(ocr_text),
                "mode": "mistral_ocr"
            }
        }

    except Exception as e:
        print(f"[MISTRAL] ERROR: {e}")
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg:
            return {"success": False, "error": "Clé API Mistral invalide. Vérifiez MISTRAL_API_KEY dans .env"}
        if "429" in error_msg:
            return {"success": False, "error": "Limite de requêtes Mistral atteinte. Réessayez dans quelques secondes."}
        return {"success": False, "error": f"Erreur Mistral OCR : {error_msg}"}


def send_to_n8n(file_bytes: bytes, file_name: str, mime_type: str) -> dict:
    """Envoie le fichier au webhook n8n. Si n8n échoue, retourne None pour fallback."""
    try:
        files = {"file": (file_name, file_bytes, mime_type)}
        response = requests.post(N8N_WEBHOOK_URL, files=files, timeout=300)
        response.raise_for_status()

        if not response.text or not response.text.strip():
            return None  # Signal pour utiliser le fallback

        try:
            result = response.json()
            if result.get("success"):
                return result
            return None  # Erreur n8n → fallback
        except json.JSONDecodeError:
            return None  # Réponse invalide → fallback

    except Exception:
        return None  # Toute erreur n8n → fallback


def render_extraction(data: dict):
    """Affiche les données extraites de manière structurée."""
    extraction = data.get("extraction", {})
    metadata = data.get("metadata", {})

    # ── Validation Warnings ──
    warnings = metadata.get("validation_warnings", [])
    if warnings:
        warnings_html = "".join([f"<p>⚠️ {w}</p>" for w in warnings])
        st.markdown(f'<div class="warning-card"><h3>⚠️ Avertissements</h3>{warnings_html}</div>', unsafe_allow_html=True)

    # ── Fournisseur & Client ──
    col1, col2 = st.columns(2)

    with col1:
        fournisseur = extraction.get("fournisseur", {})
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
        client = extraction.get("client", {})
        facture = extraction.get("facture", {})
        st.markdown(f"""
        <div class="info-card">
            <h3>👤 Client & Facture</h3>
            <p><strong>Client :</strong> {client.get('nom', 'N/A') or 'N/A'}</p>
            <p><strong>Adresse :</strong> {client.get('adresse', 'N/A') or 'N/A'}</p>
            <p>📄 <strong>N° Facture :</strong> {facture.get('numero', 'N/A')}</p>
            <p>📅 <strong>Date :</strong> {facture.get('date', 'N/A')}</p>
            <p>💱 <strong>Devise :</strong> {facture.get('devise', 'N/A')}</p>
        </div>
        """, unsafe_allow_html=True)

    # ── Tableau des articles ──
    articles = extraction.get("articles", [])
    if articles:
        st.markdown("### 📦 Articles")
        df = pd.DataFrame(articles)
        col_rename = {
            "designation": "Désignation",
            "quantite": "Quantité",
            "prix_unitaire": "Prix Unitaire",
            "total_ligne": "Total Ligne"
        }
        df = df.rename(columns=col_rename)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Désignation": st.column_config.TextColumn("Désignation", width="large"),
                "Quantité": st.column_config.NumberColumn("Quantité", format="%.3f"),
                "Prix Unitaire": st.column_config.NumberColumn("Prix Unitaire", format="%.3f"),
                "Total Ligne": st.column_config.NumberColumn("Total Ligne", format="%.3f"),
            }
        )

    # ── Totaux ──
    totaux = extraction.get("totaux", {})
    if totaux:
        devise = facture.get("devise", "TND") if facture else "TND"
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-number">{totaux.get('total_ht', 0):.3f}</div>
                <div class="stat-label">Total HT ({devise})</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-number">{totaux.get('total_tva', 0):.3f}</div>
                <div class="stat-label">Total TVA ({devise})</div>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-number">{totaux.get('total_ttc', 0):.3f}</div>
                <div class="stat-label">Total TTC ({devise})</div>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            timbre = totaux.get("timbre_fiscal")
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-number">{timbre:.3f if timbre else '—'}</div>
                <div class="stat-label">Timbre Fiscal</div>
            </div>
            """, unsafe_allow_html=True)

        # TVA Details
        tva_details = totaux.get("tva_details", [])
        if tva_details:
            st.markdown("#### 📊 Détails TVA")
            for tva in tva_details:
                st.markdown(f"- Taux **{tva.get('taux_pourcent', 0)}%** → Montant : **{tva.get('montant', 0):.3f} {devise}**")

    # ── JSON brut (expandable) ──
    with st.expander("🔍 Voir le JSON brut"):
        st.json(extraction)


# ═══════════════════════════════════════════════════════════════════
#  MAIN UI
# ═══════════════════════════════════════════════════════════════════

# ── Header ──
st.markdown("""
<div class="main-header">
    <h1>📄 DocuFlow AI</h1>
    <p>Extraction intelligente de documents commerciaux — Propulsé par Mistral OCR</p>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ──
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    st.markdown(f"**Webhook n8n :** `{N8N_WEBHOOK_URL}`")
    st.markdown(f"**Moteur IA :** `Mistral OCR`")
    api_status = "✅ Configurée" if MISTRAL_API_KEY else "❌ Manquante"
    st.markdown(f"**Clé API :** {api_status}")
    st.divider()

    st.markdown("## 📊 Statistiques")
    total_docs = len(st.session_state.history)
    valid_docs = sum(1 for h in st.session_state.history if h.get("metadata", {}).get("is_valid", False))

    col1, col2 = st.columns(2)
    col1.metric("Documents", total_docs)
    col2.metric("Valides", valid_docs)

    st.divider()
    st.markdown("## 📋 Historique")
    if st.session_state.history:
        for i, entry in enumerate(reversed(st.session_state.history)):
            meta = entry.get("metadata", {})
            fname = meta.get("source_file", "Document")
            is_valid = meta.get("is_valid", False)
            icon = "✅" if is_valid else "⚠️"
            if st.button(f"{icon} {fname}", key=f"hist_{i}", use_container_width=True):
                st.session_state.current_result = entry
    else:
        st.caption("Aucun document traité")

# ── Upload Area ──
st.markdown("### 📤 Uploader un document")

uploaded_file = st.file_uploader(
    "Glissez-déposez une facture ou un bon de livraison",
    type=["png", "jpg", "jpeg", "pdf", "tiff", "bmp", "webp"],
    help="Formats supportés : PNG, JPG, PDF, TIFF, BMP, WebP"
)

if uploaded_file:
    col_preview, col_result = st.columns([1, 1.5])

    with col_preview:
        st.markdown("#### 🖼️ Aperçu")
        if uploaded_file.type.startswith("image/"):
            image = Image.open(uploaded_file)
            st.image(image, use_container_width=True)
        else:
            st.info(f"📄 Fichier : **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} Ko)")

        # Bouton d'extraction
        extract_btn = st.button(
            "🚀 Extraire les données",
            type="primary",
            use_container_width=True
        )

    with col_result:
        if extract_btn:
            st.markdown("#### 📊 Résultats d'extraction")

            if not MISTRAL_API_KEY:
                st.error("❌ Clé API Mistral non configurée. Ajoutez `MISTRAL_API_KEY` dans le fichier `.env`")
            else:
                with st.spinner("🔄 Analyse en cours avec Mistral OCR... (5-15 secondes)"):
                    uploaded_file.seek(0)
                    file_bytes = uploaded_file.read()

                    # Tentative via n8n
                    result = send_to_n8n(
                        file_bytes=file_bytes,
                        file_name=uploaded_file.name,
                        mime_type=uploaded_file.type
                    )

                    # Fallback : appel direct à Mistral OCR si n8n échoue
                    if result is None:
                        st.info("⚡ Appel direct à Mistral OCR (n8n indisponible)...")
                        result = extract_with_mistral(
                            file_bytes=file_bytes,
                            file_name=uploaded_file.name,
                            mime_type=uploaded_file.type
                        )

                if result.get("success"):
                    st.session_state.current_result = result
                    st.session_state.history.append(result)

                    st.markdown("""
                    <div class="success-card">
                        <h3>✅ Extraction réussie</h3>
                        <p>Les données ont été extraites avec succès via Mistral OCR.</p>
                    </div>
                    """, unsafe_allow_html=True)

                    render_extraction(result)

                    # Bouton téléchargement JSON
                    json_str = json.dumps(result.get("extraction", {}), indent=2, ensure_ascii=False)
                    st.download_button(
                        label="⬇️ Télécharger JSON",
                        data=json_str,
                        file_name=f"extraction_{uploaded_file.name.rsplit('.', 1)[0]}.json",
                        mime="application/json",
                        use_container_width=True
                    )
                else:
                    error_msg = result.get("error", "Erreur inconnue")
                    st.error(f"❌ Erreur d'extraction : {error_msg}")

        elif st.session_state.current_result:
            st.markdown("#### 📊 Dernier résultat")
            render_extraction(st.session_state.current_result)

# ── Footer ──
st.divider()
st.markdown(
    "<p style='text-align:center; color:#64748b; font-size:0.8rem;'>"
    "DocuFlow AI — PFA 2025 · Propulsé par Mistral OCR & n8n"
    "</p>",
    unsafe_allow_html=True
)
