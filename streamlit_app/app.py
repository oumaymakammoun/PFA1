"""
DocuFlow AI — Point d'entrée principal
Gère l'authentification et la navigation entre les pages.
"""

import streamlit as st
from auth import is_authenticated, render_login_page
from styles import apply_theme

# ── Page Config ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="DocuFlow AI — Traitement Intelligent de Documents",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Initialisation : création admin par défaut ───────────────────────
if "db_initialized" not in st.session_state:
    try:
        from database import DatabaseManager
        db_init = DatabaseManager()
        db_init.ensure_admin_exists()
        st.session_state.db_initialized = True
    except Exception:
        pass  # La BDD n'est peut-être pas encore prête

# ── Vérification d'authentification ──────────────────────────────────
if not is_authenticated():
    render_login_page()
    st.stop()

# ── Page d'accueil (utilisateur connecté) ────────────────────────────
apply_theme()

from styles import render_sidebar
from auth import get_current_user
from database import DatabaseManager

user = get_current_user()
render_sidebar(user)

st.markdown("""
<div class="main-header">
    <h1>📄 DocuFlow AI</h1>
    <p>Traitement Intelligent de Documents Commerciaux — Propulsé par Mistral OCR</p>
</div>
""", unsafe_allow_html=True)

st.markdown(f"### 👋 Bienvenue, **{user['username']}** !")

# ── Cartes de navigation ─────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="info-card">
        <h3>📄 Extraction</h3>
        <p>Uploadez une facture, un bon de livraison ou un reçu.</p>
        <p>L'IA extrait automatiquement toutes les données structurées.</p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("📄 Aller à l'Extraction", use_container_width=True, type="primary"):
        st.switch_page("pages/1_📄_Extraction.py")

    st.markdown("""
    <div class="info-card">
        <h3>📋 Historique</h3>
        <p>Consultez tous les documents déjà traités.</p>
        <p>Recherchez par fournisseur, date ou numéro de facture.</p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("📋 Voir l'Historique", use_container_width=True):
        st.switch_page("pages/3_📋_Historique.py")

with col2:
    st.markdown("""
    <div class="info-card">
        <h3>📊 Dashboard</h3>
        <p>Visualisez vos KPIs : facturation mensuelle, top fournisseurs.</p>
        <p>Exportez en Excel ou CSV.</p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("📊 Voir le Dashboard", use_container_width=True):
        st.switch_page("pages/2_📊_Dashboard.py")

    if user.get("role") == "admin":
        st.markdown("""
        <div class="info-card">
            <h3>⚙️ Administration</h3>
            <p>Gérez les utilisateurs et consultez les logs d'audit.</p>
            <p>Surveillez l'état des services.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("⚙️ Administration", use_container_width=True):
            st.switch_page("pages/4_⚙️_Admin.py")

# ── Stats rapides ────────────────────────────────────────────────────
st.divider()
try:
    db = DatabaseManager()
    stats = db.get_dashboard_stats()
    total = stats.get("total_documents", 0) or 0
    valid = stats.get("valid_documents", 0) or 0
    total_ttc = float(stats.get("total_facture", 0) or 0)

    s1, s2, s3 = st.columns(3)
    with s1:
        st.metric("📄 Documents traités", total)
    with s2:
        st.metric("✅ Extractions valides", valid)
    with s3:
        st.metric("💰 Total facturé", f"{total_ttc:,.0f} TND")
except Exception:
    st.caption("📊 Statistiques indisponibles (BDD non connectée)")

# ── Footer ───────────────────────────────────────────────────────────
st.divider()
st.markdown(
    "<p style='text-align:center; color:#64748b; font-size:0.8rem;'>"
    "DocuFlow AI v2.0 — PFE 2025 · Mistral OCR · n8n · PostgreSQL"
    "</p>",
    unsafe_allow_html=True
)
