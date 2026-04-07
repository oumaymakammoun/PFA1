"""
DocuFlow AI — Tests d'authentification
Tests JWT, hashing, rôles.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "streamlit_app"))


# ═════════════════════════════════════════════════════════════════════
#  Tests du hashing mot de passe
# ═════════════════════════════════════════════════════════════════════

class TestPasswordHashing:
    """Tests de hash_password et verify_password."""

    def test_hash_password_returns_string(self):
        from auth import hash_password
        result = hash_password("test123")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_hash_is_unique(self):
        """Deux hashes du même mot de passe doivent être différents (salt)."""
        from auth import hash_password
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2

    def test_verify_correct_password(self):
        from auth import hash_password, verify_password
        pw = "mon_mot_de_passe_2025"
        hashed = hash_password(pw)
        assert verify_password(pw, hashed) is True

    def test_verify_wrong_password(self):
        from auth import hash_password, verify_password
        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_hash_different_passwords(self):
        from auth import hash_password, verify_password
        h1 = hash_password("password1")
        h2 = hash_password("password2")
        assert verify_password("password1", h1) is True
        assert verify_password("password1", h2) is False


# ═════════════════════════════════════════════════════════════════════
#  Tests JWT
# ═════════════════════════════════════════════════════════════════════

class TestJWT:
    """Tests de création et décodage de tokens JWT."""

    def test_create_token_returns_string(self):
        from auth import create_token
        token = create_token(1, "testuser", "admin")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_valid_token(self):
        from auth import create_token, decode_token
        token = create_token(42, "oumaima", "comptable")
        payload = decode_token(token)
        assert payload is not None
        assert payload["user_id"] == 42
        assert payload["username"] == "oumaima"
        assert payload["role"] == "comptable"

    def test_decode_invalid_token(self):
        from auth import decode_token
        payload = decode_token("invalid.token.here")
        assert payload is None

    def test_decode_empty_token(self):
        from auth import decode_token
        payload = decode_token("")
        assert payload is None

    def test_token_contains_expiration(self):
        from auth import create_token, decode_token
        token = create_token(1, "test", "lecteur")
        payload = decode_token(token)
        assert "exp" in payload
        assert "iat" in payload

    def test_token_payload_fields(self):
        from auth import create_token, decode_token
        token = create_token(5, "admin", "admin")
        payload = decode_token(token)
        assert "user_id" in payload
        assert "username" in payload
        assert "role" in payload


# ═════════════════════════════════════════════════════════════════════
#  Tests des rôles
# ═════════════════════════════════════════════════════════════════════

class TestRoles:
    """Tests de la hiérarchie des rôles."""

    def test_role_levels_exist(self):
        from config import ROLES
        assert "admin" in ROLES
        assert "comptable" in ROLES
        assert "lecteur" in ROLES

    def test_admin_highest_level(self):
        from config import ROLES
        assert ROLES["admin"]["level"] > ROLES["comptable"]["level"]
        assert ROLES["comptable"]["level"] > ROLES["lecteur"]["level"]

    def test_admin_level_is_3(self):
        from config import ROLES
        assert ROLES["admin"]["level"] == 3

    def test_roles_have_labels(self):
        from config import ROLES
        for role, info in ROLES.items():
            assert "label" in info
            assert len(info["label"]) > 0
