"""
DocuFlow AI — Module d'authentification
JWT + bcrypt pour la gestion des sessions utilisateur.
"""

import bcrypt
import jwt
import streamlit as st
from datetime import datetime, timedelta, timezone
from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_HOURS, ROLES
from database import DatabaseManager


def hash_password(password: str) -> str:
    """Hache un mot de passe avec bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Vérifie un mot de passe contre son hash bcrypt."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_token(user_id: int, username: str, role: str) -> str:
    """Crée un token JWT."""
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    """Décode et valide un token JWT. Retourne None si invalide/expiré."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def login_user(username: str, password: str) -> dict | None:
    """
    Tente d'authentifier un utilisateur.
    Retourne les infos user + token si succès, None sinon.
    """
    db = DatabaseManager()
    user = db.get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None

    token = create_token(user["id"], user["username"], user["role"])
    db.update_last_login(user["id"])
    db.log_action(user["id"], "login", {"method": "password"})

    return {
        "user_id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "role": user["role"],
        "token": token,
    }


def register_user(username: str, email: str, password: str, role: str = "lecteur") -> dict:
    """
    Enregistre un nouvel utilisateur.
    Retourne {"success": True, "user": ...} ou {"success": False, "error": "..."}.
    """
    db = DatabaseManager()

    if len(username) < 3:
        return {"success": False, "error": "Le nom d'utilisateur doit contenir au moins 3 caractères"}
    if len(password) < 6:
        return {"success": False, "error": "Le mot de passe doit contenir au moins 6 caractères"}
    if "@" not in email:
        return {"success": False, "error": "Email invalide"}
    if db.username_exists(username):
        return {"success": False, "error": "Ce nom d'utilisateur existe déjà"}
    if db.email_exists(email):
        return {"success": False, "error": "Cet email est déjà utilisé"}

    password_hash = hash_password(password)
    user = db.create_user(username, email, password_hash, role)
    db.log_action(user["id"], "register", {"role": role})

    return {"success": True, "user": user}


def get_current_user() -> dict | None:
    """Récupère l'utilisateur actuellement connecté depuis le session state."""
    return st.session_state.get("user", None)


def is_authenticated() -> bool:
    """Vérifie si l'utilisateur est authentifié avec un token valide."""
    user = get_current_user()
    if not user or "token" not in user:
        return False
    payload = decode_token(user["token"])
    return payload is not None


def require_role(required_role: str) -> bool:
    """Vérifie si l'utilisateur a le niveau de rôle requis."""
    user = get_current_user()
    if not user:
        return False
    user_level = ROLES.get(user.get("role", ""), {}).get("level", 0)
    required_level = ROLES.get(required_role, {}).get("level", 99)
    return user_level >= required_level


def logout():
    """Déconnecte l'utilisateur."""
    user = get_current_user()
    if user:
        try:
            db = DatabaseManager()
            db.log_action(user["user_id"], "logout")
        except Exception:
            pass
    for key in ["user", "current_result", "history"]:
        if key in st.session_state:
            del st.session_state[key]


def render_login_page():
    """Affiche la page de connexion / inscription."""
    from styles import apply_theme
    apply_theme()

    st.markdown("""
    <div class="main-header">
        <h1>📄 DocuFlow AI</h1>
        <p>Traitement Intelligent de Documents Commerciaux</p>
    </div>
    """, unsafe_allow_html=True)

    tab_login, tab_register = st.tabs(["🔐 Connexion", "📝 Inscription"])

    with tab_login:
        with st.form("login_form"):
            st.markdown("### Se connecter")
            username = st.text_input("Nom d'utilisateur", key="login_user")
            password = st.text_input("Mot de passe", type="password", key="login_pass")
            submitted = st.form_submit_button("Se connecter", type="primary", use_container_width=True)

            if submitted:
                if not username or not password:
                    st.error("Veuillez remplir tous les champs")
                else:
                    result = login_user(username, password)
                    if result:
                        st.session_state.user = result
                        st.success(f"Bienvenue, {result['username']} !")
                        st.rerun()
                    else:
                        st.error("Nom d'utilisateur ou mot de passe incorrect")

    with tab_register:
        with st.form("register_form"):
            st.markdown("### Créer un compte")
            new_username = st.text_input("Nom d'utilisateur", key="reg_user")
            new_email = st.text_input("Email", key="reg_email")
            new_password = st.text_input("Mot de passe", type="password", key="reg_pass")
            new_password2 = st.text_input("Confirmer le mot de passe", type="password", key="reg_pass2")
            submitted = st.form_submit_button("Créer le compte", use_container_width=True)

            if submitted:
                if new_password != new_password2:
                    st.error("Les mots de passe ne correspondent pas")
                else:
                    result = register_user(new_username, new_email, new_password)
                    if result["success"]:
                        st.success("Compte créé ! Vous pouvez maintenant vous connecter.")
                    else:
                        st.error(result["error"])

    st.markdown("""
    <div style="text-align:center; margin-top:2rem; color:#64748b; font-size:0.8rem;">
        Compte par défaut : <b>admin</b> / <b>admin123</b>
    </div>
    """, unsafe_allow_html=True)
