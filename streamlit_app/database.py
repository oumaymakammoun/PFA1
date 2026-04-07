"""
DocuFlow AI — Gestionnaire de base de données PostgreSQL
Opérations CRUD pour documents, utilisateurs, logs d'audit.
"""

import psycopg2
import psycopg2.extras
import json
import logging
from datetime import datetime
from contextlib import contextmanager
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Singleton pour la connexion PostgreSQL."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._conn_params = {
            "host": DB_HOST,
            "port": DB_PORT,
            "dbname": DB_NAME,
            "user": DB_USER,
            "password": DB_PASSWORD,
        }

    @contextmanager
    def get_cursor(self, dict_cursor=True):
        """Context manager pour obtenir un curseur avec auto-commit."""
        conn = psycopg2.connect(**self._conn_params)
        cursor_factory = psycopg2.extras.RealDictCursor if dict_cursor else None
        cursor = conn.cursor(cursor_factory=cursor_factory)
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def test_connection(self) -> bool:
        """Teste la connexion à PostgreSQL."""
        try:
            with self.get_cursor() as cur:
                cur.execute("SELECT 1")
                return True
        except Exception:
            return False

    def ensure_admin_exists(self):
        """
        Crée le compte administrateur par défaut si aucun admin n'existe.
        Appelé au démarrage de l'application.
        """
        try:
            with self.get_cursor() as cur:
                cur.execute("SELECT COUNT(*) as count FROM users WHERE role = 'admin'")
                admin_count = cur.fetchone()["count"]
                if admin_count == 0:
                    import bcrypt
                    password_hash = bcrypt.hashpw(
                        "admin123".encode("utf-8"), bcrypt.gensalt()
                    ).decode("utf-8")
                    cur.execute(
                        """INSERT INTO users (username, email, password_hash, role)
                           VALUES (%s, %s, %s, %s)
                           ON CONFLICT (username) DO NOTHING""",
                        ("admin", "admin@docuflow.local", password_hash, "admin"),
                    )
                    logger.info("Compte admin par défaut créé (admin / admin123)")
        except Exception as e:
            logger.warning(f"Impossible de créer l'admin par défaut : {e}")

    # ── Utilisateurs ─────────────────────────────────────────────────

    def create_user(self, username: str, email: str, password_hash: str, role: str = "lecteur") -> dict:
        """Crée un nouvel utilisateur."""
        with self.get_cursor() as cur:
            cur.execute(
                """INSERT INTO users (username, email, password_hash, role)
                   VALUES (%s, %s, %s, %s)
                   RETURNING id, username, email, role, is_active, created_at""",
                (username, email, password_hash, role),
            )
            return dict(cur.fetchone())

    def get_user_by_username(self, username: str) -> dict | None:
        """Récupère un utilisateur par son username."""
        with self.get_cursor() as cur:
            cur.execute("SELECT * FROM users WHERE username = %s AND is_active = true", (username,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> dict | None:
        """Récupère un utilisateur par son ID."""
        with self.get_cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_all_users(self) -> list[dict]:
        """Récupère tous les utilisateurs."""
        with self.get_cursor() as cur:
            cur.execute("SELECT id, username, email, role, is_active, created_at, last_login FROM users ORDER BY created_at DESC")
            return [dict(row) for row in cur.fetchall()]

    def update_user_role(self, user_id: int, role: str):
        """Met à jour le rôle d'un utilisateur."""
        with self.get_cursor() as cur:
            cur.execute("UPDATE users SET role = %s WHERE id = %s", (role, user_id))

    def toggle_user_active(self, user_id: int, is_active: bool):
        """Active/désactive un utilisateur."""
        with self.get_cursor() as cur:
            cur.execute("UPDATE users SET is_active = %s WHERE id = %s", (is_active, user_id))

    def update_last_login(self, user_id: int):
        """Met à jour la date de dernière connexion."""
        with self.get_cursor() as cur:
            cur.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s", (user_id,))

    def username_exists(self, username: str) -> bool:
        """Vérifie si un username existe déjà."""
        with self.get_cursor() as cur:
            cur.execute("SELECT 1 FROM users WHERE username = %s", (username,))
            return cur.fetchone() is not None

    def email_exists(self, email: str) -> bool:
        """Vérifie si un email existe déjà."""
        with self.get_cursor() as cur:
            cur.execute("SELECT 1 FROM users WHERE email = %s", (email,))
            return cur.fetchone() is not None

    def get_user_stats(self) -> list[dict]:
        """Récupère les statistiques par utilisateur (nb documents, dernière activité)."""
        with self.get_cursor() as cur:
            cur.execute("""
                SELECT
                    u.id, u.username, u.role,
                    COUNT(d.id) as nb_documents,
                    SUM(COALESCE(d.total_ttc, 0)) as total_facture,
                    MAX(d.created_at) as dernier_document,
                    (
                        SELECT COUNT(*) FROM audit_logs al WHERE al.user_id = u.id
                    ) as nb_actions
                FROM users u
                LEFT JOIN documents d ON d.user_id = u.id
                GROUP BY u.id, u.username, u.role
                ORDER BY nb_documents DESC
            """)
            return [dict(row) for row in cur.fetchall()]

    # ── Documents ────────────────────────────────────────────────────

    def save_document(self, user_id: int, extraction: dict, metadata: dict) -> int:
        """Sauvegarde un document extrait en BDD. Retourne l'ID du document."""
        fournisseur = extraction.get("fournisseur", {})
        client = extraction.get("client", {})
        facture = extraction.get("facture", {})
        totaux = extraction.get("totaux", {})

        with self.get_cursor() as cur:
            # Insérer le document principal
            cur.execute(
                """INSERT INTO documents (
                    user_id, file_name, file_type, document_type,
                    fournisseur_nom, fournisseur_adresse, fournisseur_telephone,
                    fournisseur_email, fournisseur_matricule_fiscal,
                    client_nom, client_adresse,
                    facture_numero, facture_date, facture_devise,
                    total_ht, total_tva, total_ttc, timbre_fiscal,
                    raw_json, model_used, is_valid, validation_warnings,
                    confidence_score, document_class
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s
                ) RETURNING id""",
                (
                    user_id,
                    metadata.get("source_file", ""),
                    metadata.get("file_type", ""),
                    metadata.get("document_type", "facture"),
                    fournisseur.get("nom"),
                    fournisseur.get("adresse"),
                    fournisseur.get("telephone"),
                    fournisseur.get("email"),
                    fournisseur.get("matricule_fiscal"),
                    client.get("nom"),
                    client.get("adresse"),
                    facture.get("numero"),
                    facture.get("date"),
                    facture.get("devise", "TND"),
                    totaux.get("total_ht"),
                    totaux.get("total_tva"),
                    totaux.get("total_ttc"),
                    totaux.get("timbre_fiscal"),
                    json.dumps(extraction, ensure_ascii=False),
                    metadata.get("model_used", "mistral-ocr"),
                    metadata.get("is_valid", False),
                    metadata.get("validation_warnings", []),
                    metadata.get("confidence_score"),
                    metadata.get("document_type", "facture"),
                ),
            )
            doc_id = cur.fetchone()["id"]

            # Insérer les articles
            articles = extraction.get("articles", [])
            for i, article in enumerate(articles):
                cur.execute(
                    """INSERT INTO document_articles (document_id, reference, designation, quantite, prix_unitaire, total_ligne, ligne_numero)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (
                        doc_id,
                        article.get("reference"),
                        article.get("designation", ""),
                        article.get("quantite"),
                        article.get("prix_unitaire"),
                        article.get("total_ligne"),
                        i + 1,
                    ),
                )

            # Insérer les détails TVA
            tva_details = totaux.get("tva_details", [])
            for tva in tva_details:
                cur.execute(
                    """INSERT INTO document_tva_details (document_id, taux_pourcent, montant)
                       VALUES (%s, %s, %s)""",
                    (doc_id, tva.get("taux_pourcent"), tva.get("montant")),
                )

            return doc_id

    def get_documents(self, user_id: int = None, limit: int = 50, offset: int = 0,
                      fournisseur: str = None, date_from: str = None, date_to: str = None,
                      doc_type: str = None) -> list[dict]:
        """Récupère les documents avec filtres optionnels."""
        query = "SELECT * FROM documents WHERE 1=1"
        params = []

        if user_id:
            query += " AND user_id = %s"
            params.append(user_id)
        if fournisseur:
            query += " AND fournisseur_nom ILIKE %s"
            params.append(f"%{fournisseur}%")
        if date_from:
            query += " AND facture_date >= %s"
            params.append(date_from)
        if date_to:
            query += " AND facture_date <= %s"
            params.append(date_to)
        if doc_type:
            query += " AND document_class = %s"
            params.append(doc_type)

        query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        with self.get_cursor() as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]

    def get_document_by_id(self, doc_id: int) -> dict | None:
        """Récupère un document par son ID avec ses articles."""
        with self.get_cursor() as cur:
            cur.execute("SELECT * FROM documents WHERE id = %s", (doc_id,))
            doc = cur.fetchone()
            if not doc:
                return None
            doc = dict(doc)

            cur.execute("SELECT * FROM document_articles WHERE document_id = %s ORDER BY ligne_numero", (doc_id,))
            doc["articles"] = [dict(row) for row in cur.fetchall()]

            cur.execute("SELECT * FROM document_tva_details WHERE document_id = %s", (doc_id,))
            doc["tva_details"] = [dict(row) for row in cur.fetchall()]

            return doc

    def delete_document(self, doc_id: int):
        """Supprime un document (cascade sur articles et tva_details)."""
        with self.get_cursor() as cur:
            cur.execute("DELETE FROM documents WHERE id = %s", (doc_id,))

    def get_articles_for_export(self, user_id: int = None) -> list[dict]:
        """Récupère tous les articles avec le nom du fournisseur pour l'export Excel."""
        where = "WHERE d.user_id = %s" if user_id else ""
        params = [user_id] if user_id else []
        with self.get_cursor() as cur:
            cur.execute(f"""
                SELECT
                    d.fournisseur_nom      AS "Fournisseur",
                    d.facture_numero       AS "N° Facture",
                    d.facture_date         AS "Date Facture",
                    a.reference            AS "Référence / Code",
                    a.designation          AS "Désignation",
                    a.quantite             AS "Quantité",
                    a.prix_unitaire        AS "Prix Unitaire",
                    d.facture_devise       AS "Devise"
                FROM document_articles a
                JOIN documents d ON a.document_id = d.id
                {where}
                ORDER BY d.created_at DESC, a.ligne_numero
            """, params)
            return [dict(row) for row in cur.fetchall()]

    def get_documents_for_export(self, user_id: int = None, limit: int = 500) -> list[dict]:
        """Récupère les documents avec colonnes nettoyées pour l'export."""
        where = "WHERE user_id = %s" if user_id else ""
        params = [user_id] if user_id else []
        params.append(limit)
        with self.get_cursor() as cur:
            cur.execute(f"""
                SELECT
                    id, file_name, document_class as type_document,
                    fournisseur_nom, client_nom,
                    facture_numero, facture_date, facture_devise,
                    total_ht, total_tva, total_ttc, timbre_fiscal,
                    is_valid, confidence_score,
                    model_used, created_at
                FROM documents {where}
                ORDER BY created_at DESC
                LIMIT %s
            """, params)
            return [dict(row) for row in cur.fetchall()]

    def get_document_count(self, user_id: int = None) -> int:
        """Nombre total de documents."""
        with self.get_cursor() as cur:
            if user_id:
                cur.execute("SELECT COUNT(*) as count FROM documents WHERE user_id = %s", (user_id,))
            else:
                cur.execute("SELECT COUNT(*) as count FROM documents")
            return cur.fetchone()["count"]

    # ── Statistiques / Dashboard ─────────────────────────────────────

    def get_dashboard_stats(self, user_id: int = None) -> dict:
        """Récupère les statistiques pour le dashboard."""
        with self.get_cursor() as cur:
            where = "WHERE user_id = %s" if user_id else ""
            params = [user_id] if user_id else []

            # Stats globales
            cur.execute(f"""
                SELECT
                    COUNT(*) as total_documents,
                    COUNT(*) FILTER (WHERE is_valid = true) as valid_documents,
                    SUM(COALESCE(total_ttc, 0)) as total_facture,
                    COUNT(DISTINCT fournisseur_nom) as unique_fournisseurs,
                    AVG(confidence_score) as avg_confidence
                FROM documents {where}
            """, params)
            stats = dict(cur.fetchone())

            # Par mois (12 derniers mois)
            cur.execute(f"""
                SELECT
                    TO_CHAR(created_at, 'YYYY-MM') as mois,
                    COUNT(*) as count,
                    SUM(COALESCE(total_ttc, 0)) as montant_ttc
                FROM documents {where}
                GROUP BY TO_CHAR(created_at, 'YYYY-MM')
                ORDER BY mois DESC
                LIMIT 12
            """, params)
            stats["par_mois"] = [dict(row) for row in cur.fetchall()]

            # Top fournisseurs
            cur.execute(f"""
                SELECT
                    fournisseur_nom,
                    COUNT(*) as nb_factures,
                    SUM(COALESCE(total_ttc, 0)) as total
                FROM documents {where}
                WHERE fournisseur_nom IS NOT NULL
                GROUP BY fournisseur_nom
                ORDER BY total DESC
                LIMIT 10
            """, params)
            stats["top_fournisseurs"] = [dict(row) for row in cur.fetchall()]

            # Par type de document
            cur.execute(f"""
                SELECT
                    COALESCE(document_class, 'facture') as type,
                    COUNT(*) as count
                FROM documents {where}
                GROUP BY document_class
            """, params)
            stats["par_type"] = [dict(row) for row in cur.fetchall()]

            return stats

    # ── Logs d'audit ─────────────────────────────────────────────────

    def log_action(self, user_id: int, action: str, details: dict = None):
        """Enregistre une action dans les logs d'audit."""
        with self.get_cursor() as cur:
            cur.execute(
                """INSERT INTO audit_logs (user_id, action, details)
                   VALUES (%s, %s, %s)""",
                (user_id, action, json.dumps(details or {}, ensure_ascii=False)),
            )

    def get_audit_logs(self, limit: int = 100, user_id: int = None) -> list[dict]:
        """Récupère les logs d'audit."""
        with self.get_cursor() as cur:
            if user_id:
                cur.execute("""
                    SELECT al.*, u.username
                    FROM audit_logs al
                    LEFT JOIN users u ON al.user_id = u.id
                    WHERE al.user_id = %s
                    ORDER BY al.created_at DESC LIMIT %s
                """, (user_id, limit))
            else:
                cur.execute("""
                    SELECT al.*, u.username
                    FROM audit_logs al
                    LEFT JOIN users u ON al.user_id = u.id
                    ORDER BY al.created_at DESC LIMIT %s
                """, (limit,))
            return [dict(row) for row in cur.fetchall()]
