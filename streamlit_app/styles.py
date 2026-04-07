"""
DocuFlow AI — Styles CSS et thème de l'application
Thème sombre professionnel avec dégradés violet/indigo.
"""

import streamlit as st


def apply_theme():
    """Applique le thème CSS personnalisé à l'application Streamlit."""
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        .stApp { font-family: 'Inter', sans-serif; }

        /* Header */
        .main-header {
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            padding: 2rem 2.5rem; border-radius: 16px; margin-bottom: 2rem;
            color: white; box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }
        .main-header h1 {
            font-size: 2rem; font-weight: 700; margin: 0;
            background: linear-gradient(90deg, #f97316, #fb923c, #fbbf24);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        .main-header p { color: #a5b4fc; font-size: 1rem; margin: 0.5rem 0 0 0; }

        /* Cards */
        .info-card {
            background: linear-gradient(135deg, #1e1b4b, #312e81);
            border: 1px solid rgba(139,92,246,0.3); border-radius: 12px;
            padding: 1.25rem; margin-bottom: 1rem; color: white;
        }
        .info-card h3 {
            color: #a78bfa; font-size: 0.85rem; text-transform: uppercase;
            letter-spacing: 0.05em; margin-bottom: 0.5rem; font-weight: 600;
        }
        .info-card p { color: #e2e8f0; font-size: 1rem; margin: 0.25rem 0; }

        .success-card {
            background: linear-gradient(135deg, #064e3b, #065f46);
            border: 1px solid rgba(52,211,153,0.3); border-radius: 12px;
            padding: 1.25rem; margin-bottom: 1rem; color: white;
        }
        .success-card h3 {
            color: #34d399; font-size: 0.85rem; text-transform: uppercase;
            letter-spacing: 0.05em; margin-bottom: 0.5rem;
        }

        .warning-card {
            background: linear-gradient(135deg, #78350f, #92400e);
            border: 1px solid rgba(251,191,36,0.3); border-radius: 12px;
            padding: 1.25rem; margin-bottom: 1rem; color: white;
        }
        .warning-card h3 { color: #fbbf24; }

        /* Stats */
        .stat-box {
            background: linear-gradient(135deg, #1e1b4b, #312e81);
            border: 1px solid rgba(139,92,246,0.2); border-radius: 12px;
            padding: 1.25rem; text-align: center; transition: transform 0.2s ease;
        }
        .stat-box:hover { transform: translateY(-2px); }
        .stat-number {
            font-size: 1.8rem; font-weight: 700;
            background: linear-gradient(90deg, #a78bfa, #60a5fa);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        .stat-label {
            color: #94a3b8; font-size: 0.8rem; text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        /* Confidence badge */
        .confidence-high { color: #34d399; font-weight: 600; }
        .confidence-medium { color: #fbbf24; font-weight: 600; }
        .confidence-low { color: #f87171; font-weight: 600; }

        /* Role badges */
        .role-admin {
            background: linear-gradient(135deg, #dc2626, #ef4444);
            color: white; padding: 2px 10px; border-radius: 12px; font-size: 0.75rem;
        }
        .role-comptable {
            background: linear-gradient(135deg, #2563eb, #3b82f6);
            color: white; padding: 2px 10px; border-radius: 12px; font-size: 0.75rem;
        }
        .role-lecteur {
            background: linear-gradient(135deg, #6b7280, #9ca3af);
            color: white; padding: 2px 10px; border-radius: 12px; font-size: 0.75rem;
        }

        /* Hide Streamlit defaults */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .stDeployButton {display:none;}
    </style>
    """, unsafe_allow_html=True)


def render_sidebar(user: dict):
    """Affiche la sidebar avec les infos utilisateur et navigation."""
    from auth import logout

    with st.sidebar:
        st.markdown(f"### 👤 {user['username']}")
        role_class = f"role-{user['role']}"
        st.markdown(f'<span class="{role_class}">{user["role"].upper()}</span>', unsafe_allow_html=True)
        st.divider()

        if st.button("🚪 Se déconnecter", use_container_width=True):
            logout()
            st.rerun()
