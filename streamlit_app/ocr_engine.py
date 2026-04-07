"""
DocuFlow AI — Moteur OCR Mistral
Pipeline d'extraction : Mistral OCR → Mistral Small → JSON structuré.
"""

import base64
import json
import re
from datetime import datetime
from mistralai.client import Mistral
from config import MISTRAL_API_KEY, MISTRAL_OCR_MODEL, MISTRAL_CHAT_MODEL


# ── Prompt d'extraction structurée ───────────────────────────────────
EXTRACTION_PROMPT = """Tu es un expert en extraction de données de factures et documents commerciaux.
Voici le contenu OCR d'un document commercial.
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
      "reference": "...",
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

Utilise null pour les champs manquants. Utilise des nombres (point décimal) pour les montants.
Pour chaque article, extrais la référence produit (code, réf, SKU, numéro d'article) si elle existe. Si aucune référence n'est trouvée, utilise null.
Réponds UNIQUEMENT avec le JSON, sans texte ni explication.

Contenu OCR du document :
"""


def get_mime_type(file_name: str, file_type: str = "") -> str:
    """Détermine le MIME type pour l'API Mistral."""
    ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    mime_map = {
        "pdf": "application/pdf", "png": "image/png",
        "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "tiff": "image/tiff", "tif": "image/tiff",
        "bmp": "image/bmp", "webp": "image/webp",
    }
    return mime_map.get(ext, file_type or "image/jpeg")


def perform_ocr(client: Mistral, file_bytes: bytes, file_name: str, mime_type: str) -> str:
    """
    Étape 1 : OCR avec Mistral OCR.
    Retourne le texte extrait au format Markdown.
    """
    resolved_mime = get_mime_type(file_name, mime_type)
    base64_data = base64.b64encode(file_bytes).decode("utf-8")
    document_url = f"data:{resolved_mime};base64,{base64_data}"

    ocr_response = client.ocr.process(
        model=MISTRAL_OCR_MODEL,
        document={"type": "document_url", "document_url": document_url},
    )

    ocr_text = ""
    for page in ocr_response.pages:
        ocr_text += page.markdown + "\n\n"

    return ocr_text.strip()


def extract_structured_data(client: Mistral, ocr_text: str) -> dict:
    """
    Étape 2 : Extraction structurée avec Mistral Small.
    Retourne le JSON parsé des données de la facture.
    """
    chat_response = client.chat.complete(
        model=MISTRAL_CHAT_MODEL,
        messages=[{"role": "user", "content": EXTRACTION_PROMPT + ocr_text}],
        temperature=0.1,
        response_format={"type": "json_object"},
    )

    raw_content = chat_response.choices[0].message.content

    # Nettoyer les balises markdown
    raw_content = re.sub(r'^```json\s*', '', raw_content.strip())
    raw_content = re.sub(r'^```\s*', '', raw_content)
    raw_content = re.sub(r'\s*```$', '', raw_content)

    # Extraire le JSON
    first_brace = raw_content.find('{')
    last_brace = raw_content.rfind('}')

    if first_brace == -1 or last_brace == -1:
        raise ValueError(f"Pas de JSON dans la réponse : {raw_content[:300]}")

    json_str = raw_content[first_brace:last_brace + 1]

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
        return json.loads(json_str)


def extract_with_mistral(file_bytes: bytes, file_name: str, mime_type: str) -> dict:
    """
    Pipeline complet d'extraction.
    Retourne {"success": True/False, "extraction": {...}, "metadata": {...}}.
    """
    try:
        if not MISTRAL_API_KEY:
            return {"success": False, "error": "Clé API Mistral non configurée. Ajoutez MISTRAL_API_KEY dans .env"}

        client = Mistral(api_key=MISTRAL_API_KEY)

        # Étape 1 : OCR
        ocr_text = perform_ocr(client, file_bytes, file_name, mime_type)
        if not ocr_text:
            return {"success": False, "error": "Mistral OCR n'a extrait aucun texte. Vérifiez la qualité de l'image."}

        # Étape 2 : Extraction structurée
        parsed = extract_structured_data(client, ocr_text)

        # Validation basique
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
            "ocr_text": ocr_text,
            "metadata": {
                "source_file": file_name,
                "file_type": mime_type,
                "extraction_date": datetime.now().isoformat(),
                "model_used": f"{MISTRAL_OCR_MODEL} + {MISTRAL_CHAT_MODEL}",
                "validation_warnings": warnings,
                "is_valid": len(warnings) == 0,
                "nombre_articles": len(parsed.get("articles", [])),
                "ocr_text_length": len(ocr_text),
                "mode": "mistral_ocr",
            }
        }

    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg:
            return {"success": False, "error": "Clé API Mistral invalide."}
        if "429" in error_msg:
            return {"success": False, "error": "Limite de requêtes Mistral atteinte. Réessayez."}
        return {"success": False, "error": f"Erreur Mistral OCR : {error_msg}"}
