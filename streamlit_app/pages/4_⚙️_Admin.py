"""
DocuFlow AI — Administration
Gestion des utilisateurs, logs d'audit, statistiques, configuration.
Réservé aux administrateurs.
"""

import streamlit as st
import pandas as pd
from styles import apply_theme, render_sidebar
from auth import is_authenticated, get_current_user, require_role, hash_password
from database import DatabaseManager

if not is_authenticated():
    st.switch_page("app.py")
    st.stop()

if not require_role("admin"):
    st.error("🚫 Accès réservé aux administrateurs.")
    st.stop()

apply_theme()
user = get_current_user()
render_sidebar(user)

st.markdown("""
<div class="main-header">
    <h1>⚙️ Administration</h1>
    <p>Gestion des utilisateurs, statistiques et logs d'audit</p>
</div>
""", unsafe_allow_html=True)

db = DatabaseManager()

tab_users, tab_stats, tab_logs, tab_config = st.tabs([
    "👥 Utilisateurs", "📊 Statistiques", "📜 Logs d'Audit", "🔧 Système"
])

# ── Onglet Utilisateurs ──────────────────────────────────────────────
with tab_users:
    st.markdown("### 👥 Gestion des Utilisateurs")

    # Créer un nouvel utilisateur
    with st.expander("➕ Créer un nouvel utilisateur"):
        with st.form("create_user_form"):
            new_username = st.text_input("Nom d'utilisateur")
            new_email = st.text_input("Email")
            new_password = st.text_input("Mot de passe", type="password")
            new_role = st.selectbox("Rôle", ["lecteur", "comptable", "admin"])
            submitted = st.form_submit_button("Créer", use_container_width=True)

            if submitted:
                if not all([new_username, new_email, new_password]):
                    st.error("Tous les champs sont requis")
                elif db.username_exists(new_username):
                    st.error("Ce nom d'utilisateur existe déjà")
                else:
                    try:
                        pw_hash = hash_password(new_password)
                        db.create_user(new_username, new_email, pw_hash, new_role)
                        db.log_action(user["user_id"], "create_user", {"new_user": new_username, "role": new_role})
                        st.success(f"Utilisateur **{new_username}** créé !")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {e}")

    # Liste des utilisateurs
    try:
        users = db.get_all_users()
    except Exception:
        users = []

    for u in users:
        role_class = f"role-{u['role']}"
        cols = st.columns([3, 2, 2, 2, 2])
        with cols[0]:
            st.markdown(f"**{u['username']}** ({u['email']})")
        with cols[1]:
            st.markdown(f'<span class="{role_class}">{u["role"].upper()}</span>', unsafe_allow_html=True)
        with cols[2]:
            status = "🟢 Actif" if u.get("is_active") else "🔴 Inactif"
            st.markdown(status)
        with cols[3]:
            last = u.get("last_login")
            st.caption(str(last)[:16] if last else "Jamais")
        with cols[4]:
            if u["username"] != "admin":
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button("⚡", key=f"toggle_{u['id']}", help="Activer/Désactiver"):
                        db.toggle_user_active(u["id"], not u.get("is_active", True))
                        db.log_action(user["user_id"], "toggle_user", {
                            "target_user": u["username"],
                            "new_status": not u.get("is_active", True)
                        })
                        st.rerun()
                with btn_col2:
                    # Changement de rôle
                    current_role = u.get("role", "lecteur")
                    new_role = st.selectbox(
                        "Rôle",
                        ["lecteur", "comptable", "admin"],
                        index=["lecteur", "comptable", "admin"].index(current_role),
                        key=f"role_{u['id']}",
                        label_visibility="collapsed"
                    )
                    if new_role != current_role:
                        db.update_user_role(u["id"], new_role)
                        db.log_action(user["user_id"], "change_role", {
                            "target_user": u["username"],
                            "old_role": current_role,
                            "new_role": new_role,
                        })
                        st.rerun()

# ── Onglet Statistiques ──────────────────────────────────────────────
with tab_stats:
    st.markdown("### 📊 Statistiques par Utilisateur")

    try:
        user_stats = db.get_user_stats()
    except Exception:
        user_stats = []

    if user_stats:
        # KPIs globaux
        total_users = len(user_stats)
        total_docs = sum(s.get("nb_documents", 0) or 0 for s in user_stats)
        total_actions = sum(s.get("nb_actions", 0) or 0 for s in user_stats)

        s1, s2, s3 = st.columns(3)
        with s1:
            st.markdown(f'<div class="stat-box"><div class="stat-number">{total_users}</div><div class="stat-label">Utilisateurs</div></div>', unsafe_allow_html=True)
        with s2:
            st.markdown(f'<div class="stat-box"><div class="stat-number">{total_docs}</div><div class="stat-label">Documents totaux</div></div>', unsafe_allow_html=True)
        with s3:
            st.markdown(f'<div class="stat-box"><div class="stat-number">{total_actions}</div><div class="stat-label">Actions totales</div></div>', unsafe_allow_html=True)

        st.markdown("#### 📋 Détail par utilisateur")

        # Tableau
        df_stats = pd.DataFrame(user_stats)
        col_rename = {
            "username": "Utilisateur", "role": "Rôle",
            "nb_documents": "Documents", "total_facture": "Total facturé (TND)",
            "nb_actions": "Actions", "dernier_document": "Dernier document"
        }
        display_cols = [c for c in col_rename.keys() if c in df_stats.columns]
        df_display = df_stats[display_cols].rename(columns=col_rename)

        st.dataframe(df_display, use_container_width=True, hide_index=True)

        # Graphique documents par utilisateur
        import plotly.express as px
        df_chart = df_stats[df_stats["nb_documents"] > 0]
        if not df_chart.empty:
            fig = px.bar(
                df_chart, x="username", y="nb_documents",
                title="📄 Documents par Utilisateur",
                labels={"username": "Utilisateur", "nb_documents": "Documents"},
                color="role",
                color_discrete_map={
                    "admin": "#ef4444", "comptable": "#3b82f6", "lecteur": "#9ca3af"
                }
            )
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="#e2e8f0"
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucune statistique disponible")

# ── Onglet Logs ──────────────────────────────────────────────────────
with tab_logs:
    st.markdown("### 📜 Logs d'Audit")

    try:
        logs = db.get_audit_logs(limit=100)
    except Exception:
        logs = []

    if logs:
        # Filtre par action
        all_actions = sorted(set(log.get("action", "?") for log in logs))
        filtre_action = st.multiselect("Filtrer par action", all_actions, default=[])

        filtered_logs = logs
        if filtre_action:
            filtered_logs = [l for l in logs if l.get("action") in filtre_action]

        st.caption(f"{len(filtered_logs)} log(s) affichés")

        for log in filtered_logs:
            icon_map = {
                "login": "🔑", "logout": "🚪", "extraction": "📄",
                "extraction_batch": "📦",
                "delete_document": "🗑️", "register": "📝", "create_user": "👤",
                "change_role": "🔄", "toggle_user": "⚡",
            }
            icon = icon_map.get(log.get("action", ""), "📌")
            username = log.get("username", "?")
            action = log.get("action", "?")
            timestamp = str(log.get("created_at", ""))[:19]
            details = log.get("details", {})

            st.markdown(f"{icon} **{username}** — `{action}` — {timestamp}")
            if details and isinstance(details, dict) and details:
                st.caption(f"  Détails : {details}")
    else:
        st.info("Aucun log d'audit")

# ── Onglet Système ───────────────────────────────────────────────────
with tab_config:
    st.markdown("### 🔧 Configuration Système")

    try:
        db_ok = db.test_connection()
    except Exception:
        db_ok = False

    from config import MISTRAL_API_KEY, APP_VERSION, MISTRAL_OCR_MODEL, MISTRAL_CHAT_MODEL

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="info-card">
            <h3>📊 Statut des Services</h3>
            <p>{'🟢' if db_ok else '🔴'} PostgreSQL : {'Connecté' if db_ok else 'Déconnecté'}</p>
            <p>{'🟢' if MISTRAL_API_KEY else '🔴'} Mistral API : {'Configurée' if MISTRAL_API_KEY else 'Non configurée'}</p>
            <p>🤖 Modèle OCR : {MISTRAL_OCR_MODEL}</p>
            <p>🧠 Modèle Chat : {MISTRAL_CHAT_MODEL}</p>
            <p>📦 Version : {APP_VERSION}</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        try:
            doc_count = db.get_document_count()
        except Exception:
            doc_count = 0
        try:
            all_users = db.get_all_users()
            user_count = len(all_users)
        except Exception:
            user_count = 0
        st.markdown(f"""
        <div class="info-card">
            <h3>💾 Base de Données</h3>
            <p>📄 Documents : {doc_count}</p>
            <p>👥 Utilisateurs : {user_count}</p>
            <p>📜 Logs : {len(logs)}</p>
        </div>
        """, unsafe_allow_html=True)
