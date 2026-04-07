"""
DocuFlow AI — Moteur d'Intelligence Artificielle
Classification, validation, scores de confiance.
"""

import json
import re
from mistralai.client import Mistral
from config import MISTRAL_API_KEY, MISTRAL_CHAT_MODEL, TVA_RATES_TUNISIA


def _get_client() -> Mistral:
    """Retourne un client Mistral initialisé."""
    return Mistral(api_key=MISTRAL_API_KEY)


# ═══════════════════════════════════════════════════════════════════════
#  1. CLASSIFICATION AUTOMATIQUE DES DOCUMENTS
# ═══════════════════════════════════════════════════════════════════════

CLASSIFICATION_PROMPT = """Analyse le texte OCR suivant et classifie le type de document.
Réponds UNIQUEMENT avec un JSON valide :
{
  "type": "facture" | "bon_livraison" | "recu" | "autre",
  "confidence": 0.0 à 1.0,
  "raison": "explication courte"
}

Indices pour la classification :
- "facture" : contient TVA, montant TTC, numéro de facture, articles avec prix
- "bon_livraison" : contient quantités livrées, référence BL, pas de prix
- "recu" : contient "reçu", montant payé, mode de paiement
- "autre" : ne correspond à aucune catégorie

Texte OCR :
"""


def classify_document(ocr_text: str) -> dict:
    """
    Classifie automatiquement un document à partir de son texte OCR.
    Retourne : {"type": "facture", "confidence": 0.95, "raison": "..."}
    """
    try:
        if not MISTRAL_API_KEY or not ocr_text:
            return {"type": "facture", "confidence": 0.5, "raison": "Classification par défaut"}

        client = _get_client()
        response = client.chat.complete(
            model=MISTRAL_CHAT_MODEL,
            messages=[{"role": "user", "content": CLASSIFICATION_PROMPT + ocr_text[:2000]}],
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        result = json.loads(raw)
        return {
            "type": result.get("type", "facture"),
            "confidence": min(1.0, max(0.0, float(result.get("confidence", 0.5)))),
            "raison": result.get("raison", ""),
        }
    except Exception:
        return {"type": "facture", "confidence": 0.5, "raison": "Erreur de classification, type par défaut"}


# ═══════════════════════════════════════════════════════════════════════
#  2. VALIDATION INTELLIGENTE
# ═══════════════════════════════════════════════════════════════════════

def validate_extraction(extraction: dict) -> list[dict]:
    """
    Valide les données extraites avec des règles métier.
    Retourne une liste d'anomalies détectées.
    """
    anomalies = []
    totaux = extraction.get("totaux", {})
    articles = extraction.get("articles", [])

    # ── Vérification Total TTC = Total HT + Total TVA ────────────────
    total_ht = _to_float(totaux.get("total_ht"))
    total_tva = _to_float(totaux.get("total_tva"))
    total_ttc = _to_float(totaux.get("total_ttc"))
    timbre = _to_float(totaux.get("timbre_fiscal"))

    if total_ht and total_tva and total_ttc:
        expected_ttc = total_ht + total_tva
        ecart = abs(total_ttc - expected_ttc)
        # Tolérance de 1 TND pour les arrondis
        if ecart > 1.0:
            anomalies.append({
                "field": "total_ttc",
                "issue": f"TTC ({total_ttc:.3f}) ≠ HT ({total_ht:.3f}) + TVA ({total_tva:.3f}) = {expected_ttc:.3f}. Écart: {ecart:.3f} TND",
                "severity": "error" if ecart > 10 else "warning",
            })

    # ── Vérification Total Facture = TTC + Timbre ────────────────────
    if total_ttc and timbre:
        total_facture_expected = total_ttc + timbre
        # On ne signale que si c'est mentionné dans la facture

    # ── Vérification cohérence article × prix ────────────────────────
    for i, article in enumerate(articles):
        qte = _to_float(article.get("quantite"))
        pu = _to_float(article.get("prix_unitaire"))
        total_ligne = _to_float(article.get("total_ligne"))

        if qte and pu and total_ligne:
            expected = qte * pu
            ecart = abs(total_ligne - expected)
            if ecart > 0.5:
                anomalies.append({
                    "field": f"articles[{i}].total_ligne",
                    "issue": f"Article '{article.get('designation', '?')}': {qte} × {pu} = {expected:.3f} ≠ {total_ligne:.3f}",
                    "severity": "warning",
                })

    # ── Vérification taux TVA tunisiens ──────────────────────────────
    tva_details = totaux.get("tva_details", [])
    for tva in tva_details:
        taux = _to_float(tva.get("taux_pourcent"))
        if taux is not None and taux not in TVA_RATES_TUNISIA:
            anomalies.append({
                "field": "totaux.tva_details",
                "issue": f"Taux TVA {taux}% non standard en Tunisie (attendu: {TVA_RATES_TUNISIA})",
                "severity": "warning",
            })

    # ── Montants négatifs ────────────────────────────────────────────
    for field_name, value in [("total_ht", total_ht), ("total_tva", total_tva), ("total_ttc", total_ttc)]:
        if value is not None and value < 0:
            anomalies.append({
                "field": f"totaux.{field_name}",
                "issue": f"Montant négatif détecté : {value:.3f}",
                "severity": "error",
            })

    # ── Montants suspicieusement élevés ──────────────────────────────
    if total_ttc and total_ttc > 1_000_000:
        anomalies.append({
            "field": "totaux.total_ttc",
            "issue": f"Montant TTC très élevé : {total_ttc:,.3f} TND",
            "severity": "info",
        })

    return anomalies


# ═══════════════════════════════════════════════════════════════════════
#  3. SCORES DE CONFIANCE PAR CHAMP
# ═══════════════════════════════════════════════════════════════════════

def compute_confidence_scores(ocr_text: str, extraction: dict) -> dict:
    """
    Calcule un score de confiance [0-1] pour chaque section extraite.
    Basé sur la présence des données dans le texte OCR + format attendu.
    """
    scores = {}
    ocr_lower = ocr_text.lower() if ocr_text else ""

    # ── Fournisseur ──
    fournisseur = extraction.get("fournisseur", {})
    f_score = 0.0
    f_count = 0
    for key in ["nom", "adresse", "telephone", "matricule_fiscal"]:
        val = fournisseur.get(key)
        if val and str(val).lower() != "null":
            f_count += 1
            # Vérifier si la valeur apparaît dans l'OCR
            if str(val).lower()[:10] in ocr_lower:
                f_score += 1.0
            else:
                f_score += 0.5
    scores["fournisseur"] = round(f_score / max(f_count, 1), 2)

    # ── Client ──
    client = extraction.get("client", {})
    c_score = 0.0
    c_count = 0
    for key in ["nom", "adresse"]:
        val = client.get(key)
        if val and str(val).lower() != "null":
            c_count += 1
            if str(val).lower()[:10] in ocr_lower:
                c_score += 1.0
            else:
                c_score += 0.5
    scores["client"] = round(c_score / max(c_count, 1), 2)

    # ── Facture ──
    facture = extraction.get("facture", {})
    fac_score = 0.0
    fac_count = 0
    for key in ["numero", "date", "devise"]:
        val = facture.get(key)
        if val and str(val).lower() != "null":
            fac_count += 1
            if str(val).lower()[:6] in ocr_lower:
                fac_score += 1.0
            else:
                fac_score += 0.5
    scores["facture"] = round(fac_score / max(fac_count, 1), 2)

    # ── Articles ──
    articles = extraction.get("articles", [])
    if articles:
        art_scores = []
        for art in articles:
            des = art.get("designation", "")
            if des and des.lower()[:8] in ocr_lower:
                art_scores.append(1.0)
            elif des:
                art_scores.append(0.6)
            else:
                art_scores.append(0.2)
        scores["articles"] = round(sum(art_scores) / len(art_scores), 2)
    else:
        scores["articles"] = 0.0

    # ── Totaux ──
    totaux = extraction.get("totaux", {})
    t_score = 0.0
    t_count = 0
    for key in ["total_ht", "total_tva", "total_ttc"]:
        val = totaux.get(key)
        if val is not None:
            t_count += 1
            val_str = f"{float(val):.3f}"
            if val_str in ocr_text or val_str.replace(".", ",") in ocr_text:
                t_score += 1.0
            else:
                t_score += 0.5
    scores["totaux"] = round(t_score / max(t_count, 1), 2)

    # ── Score global ──
    all_scores = [v for v in scores.values() if v > 0]
    scores["global"] = round(sum(all_scores) / max(len(all_scores), 1), 2)

    return scores


def get_confidence_label(score: float) -> tuple[str, str]:
    """Retourne (label, css_class) pour un score de confiance."""
    if score >= 0.8:
        return "Élevée", "confidence-high"
    elif score >= 0.5:
        return "Moyenne", "confidence-medium"
    else:
        return "Faible", "confidence-low"


# ═══════════════════════════════════════════════════════════════════════
#  4. PIPELINE IA COMPLET
# ═══════════════════════════════════════════════════════════════════════

def enrich_extraction(result: dict) -> dict:
    """
    Enrichit un résultat d'extraction avec classification, validation et confiance.
    Prend le résultat de extract_with_mistral() et l'augmente.
    """
    if not result.get("success"):
        return result

    extraction = result["extraction"]
    ocr_text = result.get("ocr_text", "")
    metadata = result["metadata"]

    # 1. Classification
    classification = classify_document(ocr_text)
    metadata["document_type"] = classification["type"]
    metadata["classification_confidence"] = classification["confidence"]
    metadata["classification_raison"] = classification["raison"]

    # 2. Validation intelligente
    anomalies = validate_extraction(extraction)
    metadata["anomalies"] = anomalies
    metadata["nb_anomalies"] = len(anomalies)
    metadata["has_errors"] = any(a["severity"] == "error" for a in anomalies)

    # 3. Scores de confiance
    confidence = compute_confidence_scores(ocr_text, extraction)
    metadata["confidence_scores"] = confidence
    metadata["confidence_score"] = confidence.get("global", 0.5)

    return result


# ── Utilitaires ──────────────────────────────────────────────────────

def _to_float(value) -> float | None:
    """Convertit une valeur en float, retourne None si impossible."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
