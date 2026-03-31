"""
PFA Ollama — Interface Streamlit
Traitement Intelligent de Documents Commerciaux
"""

import streamlit as st
import requests
import json
import os
import base64
import pandas as pd
from datetime import datetime
from io import BytesIO
from PIL import Image

# ── Configuration ────────────────────────────────────────────────────
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/facture")

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
        background: linear-gradient(90deg, #a78bfa, #60a5fa, #34d399);
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
# ── Configuration Ollama directe ─────────────────────────────────────
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "moondream")

EXTRACTION_PROMPT = """Extract invoice data as JSON: fournisseur_nom, fournisseur_adresse, fournisseur_telephone, fournisseur_email, fournisseur_matricule_fiscal, client_nom, client_adresse, facture_numero, facture_date, facture_devise, total_ht, total_tva, total_ttc, timbre_fiscal, articles array with designation/quantite/prix_unitaire/total_ligne. Use null for missing fields, numbers for amounts (dot decimal separator). Respond ONLY with valid JSON, no extra text."""


def optimize_image(file_bytes: bytes, max_size: int = 800) -> bytes:
    """Réduit la taille de l'image pour accélérer l'inférence sur CPU."""
    try:
        img = Image.open(BytesIO(file_bytes))
        # Convertir en RGB si nécessaire
        if img.mode in ('RGBA', 'P', 'LA'):
            img = img.convert('RGB')
        # Redimensionner si trop grand
        w, h = img.size
        if max(w, h) > max_size:
            ratio = max_size / max(w, h)
            new_w, new_h = int(w * ratio), int(h * ratio)
            img = img.resize((new_w, new_h), Image.LANCZOS)
        # Sauvegarder en JPEG compressé
        buf = BytesIO()
        img.save(buf, format='JPEG', quality=85)
        return buf.getvalue()
    except Exception:
        return file_bytes  # En cas d'erreur, renvoyer l'original


def extract_with_ollama(file_bytes: bytes, file_name: str, mime_type: str) -> dict:
    """Appelle Ollama directement pour extraire les données de la facture."""
    try:
        # Optimiser l'image pour CPU
        if mime_type.startswith("image/"):
            optimized = optimize_image(file_bytes)
        else:
            optimized = file_bytes

        base64_image = base64.b64encode(optimized).decode("utf-8")

        payload = {
            "model": OLLAMA_MODEL,
            "prompt": EXTRACTION_PROMPT,
            "images": [base64_image],
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 4096
            }
        }

        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=600
        )

        if response.status_code != 200:
            error_detail = response.text[:300] if response.text else "Pas de détail"
            return {"success": False, "error": f"Erreur Ollama ({response.status_code}): {error_detail}"}

        result = response.json()

        raw_content = result.get("response", "") or result.get("message", {}).get("content", "")

        # Nettoyer les balises markdown et <think>
        import re
        raw_content = re.sub(r'<think>[\s\S]*?</think>', '', raw_content).strip()
        raw_content = re.sub(r'^```json\s*', '', raw_content)
        raw_content = re.sub(r'^```\s*', '', raw_content)
        raw_content = re.sub(r'\s*```$', '', raw_content)

        # Extraire le JSON
        first_brace = raw_content.find('{')
        last_brace = raw_content.rfind('}')

        if first_brace == -1 or last_brace == -1:
            return {"success": False, "error": f"Pas de JSON dans la réponse Ollama : {raw_content[:300]}"}

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
                "model_used": OLLAMA_MODEL,
                "validation_warnings": warnings,
                "is_valid": len(warnings) == 0,
                "nombre_articles": len(parsed.get("articles", [])),
                "mode": "direct_ollama"
            }
        }

    except requests.exceptions.Timeout:
        return {"success": False, "error": f"Timeout Ollama (>10min). Le modèle {OLLAMA_MODEL} tourne sur CPU. Essayez avec une image plus petite."}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": f"Impossible de se connecter à Ollama ({OLLAMA_URL}). Vérifiez que le service est démarré."}
    except Exception as e:
        return {"success": False, "error": f"Erreur Ollama : {str(e)}"}


def send_to_n8n(file_bytes: bytes, file_name: str, mime_type: str) -> dict:
    """Envoie le fichier au webhook n8n. Si n8n échoue, appelle Ollama directement."""
    try:
        files = {"file": (file_name, file_bytes, mime_type)}
        response = requests.post(N8N_WEBHOOK_URL, files=files, timeout=300)
        response.raise_for_status()

        if not response.text or not response.text.strip():
            # n8n a retourné une réponse vide → fallback Ollama direct
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
        devise = facture.get("devise", "TND")
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
    <p>Extraction intelligente de documents commerciaux — Propulsé par Ollama & Qwen3-VL</p>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ──
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    st.markdown(f"**Webhook n8n :** `{N8N_WEBHOOK_URL}`")
    st.markdown(f"**Modèle IA :** `{OLLAMA_MODEL}`")
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

            with st.spinner(f"🔄 Analyse en cours avec {OLLAMA_MODEL}... (peut prendre 1-3 min sur CPU)"):
                uploaded_file.seek(0)
                file_bytes = uploaded_file.read()

                # Tentative via n8n
                result = send_to_n8n(
                    file_bytes=file_bytes,
                    file_name=uploaded_file.name,
                    mime_type=uploaded_file.type
                )

                # Fallback : appel direct à Ollama si n8n échoue
                if result is None:
                    st.info("⚡ Appel direct à Ollama (n8n indisponible)...")
                    result = extract_with_ollama(
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
                    <p>Les données ont été extraites avec succès.</p>
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
    "DocuFlow AI — PFA 2025 · Propulsé par Ollama, Qwen3-VL & n8n"
    "</p>",
    unsafe_allow_html=True
)
