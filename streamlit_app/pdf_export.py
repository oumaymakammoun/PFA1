"""
DocuFlow AI — Export PDF
Génération de rapports PDF professionnels avec ReportLab.
"""

from io import BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT


# ── Couleurs du thème DocuFlow AI ────────────────────────────────────
VIOLET_DARK = colors.HexColor("#1e1b4b")
VIOLET_MID = colors.HexColor("#312e81")
VIOLET_LIGHT = colors.HexColor("#8b5cf6")
ORANGE = colors.HexColor("#f97316")
GREEN = colors.HexColor("#34d399")
RED = colors.HexColor("#ef4444")
GRAY_LIGHT = colors.HexColor("#f1f5f9")
GRAY_TEXT = colors.HexColor("#64748b")


def _get_styles():
    """Crée les styles personnalisés pour le PDF."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="DocuTitle",
        parent=styles["Title"],
        fontSize=22, textColor=VIOLET_DARK,
        spaceAfter=6, fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        name="DocuSubtitle",
        parent=styles["Normal"],
        fontSize=10, textColor=GRAY_TEXT,
        spaceAfter=12, alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeader",
        parent=styles["Heading2"],
        fontSize=13, textColor=VIOLET_DARK,
        spaceBefore=14, spaceAfter=6,
        fontName="Helvetica-Bold",
        borderWidth=0, borderPadding=0,
    ))
    styles.add(ParagraphStyle(
        name="FieldLabel",
        parent=styles["Normal"],
        fontSize=9, textColor=GRAY_TEXT,
        fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        name="FieldValue",
        parent=styles["Normal"],
        fontSize=10, textColor=colors.black,
    ))
    styles.add(ParagraphStyle(
        name="Footer",
        parent=styles["Normal"],
        fontSize=7, textColor=GRAY_TEXT,
        alignment=TA_CENTER,
    ))

    return styles


def generate_document_pdf(doc: dict) -> bytes:
    """
    Génère un rapport PDF pour un document extrait.

    Args:
        doc: dict contenant les données du document (depuis la BDD ou extraction)

    Returns:
        bytes du fichier PDF
    """
    buffer = BytesIO()
    pdf = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )

    styles = _get_styles()
    elements = []

    # ── En-tête ──────────────────────────────────────────────────────
    elements.append(Paragraph("📄 DocuFlow AI", styles["DocuTitle"]))
    elements.append(Paragraph(
        "Rapport d'Extraction — Traitement Intelligent de Documents",
        styles["DocuSubtitle"]
    ))
    elements.append(HRFlowable(
        width="100%", thickness=2, color=VIOLET_LIGHT,
        spaceBefore=4, spaceAfter=12
    ))

    # ── Informations du document ─────────────────────────────────────
    meta_data = [
        ["Fichier :", str(doc.get("file_name", "N/A"))],
        ["Type :", str(doc.get("document_class", doc.get("document_type", "facture"))).replace("_", " ").title()],
        ["Date d'extraction :", str(doc.get("created_at", datetime.now()))[:19]],
        ["Modèle IA :", str(doc.get("model_used", "Mistral OCR"))],
    ]

    conf = doc.get("confidence_score")
    if conf is not None:
        conf_pct = f"{float(conf) * 100:.0f}%"
        meta_data.append(["Score de confiance :", conf_pct])

    validity = "✅ Valide" if doc.get("is_valid") else "⚠️ Anomalies détectées"
    meta_data.append(["Validation :", validity])

    meta_table = Table(meta_data, colWidths=[4 * cm, 12 * cm])
    meta_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), GRAY_TEXT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 12))

    # ── Fournisseur & Client ─────────────────────────────────────────
    elements.append(Paragraph("🏢 Fournisseur & Client", styles["SectionHeader"]))

    # Si les données sont directement dans le doc (depuis la BDD)
    fournisseur_nom = doc.get("fournisseur_nom") or doc.get("fournisseur", {}).get("nom", "N/A")
    fournisseur_adresse = doc.get("fournisseur_adresse") or doc.get("fournisseur", {}).get("adresse", "N/A")
    fournisseur_tel = doc.get("fournisseur_telephone") or doc.get("fournisseur", {}).get("telephone", "N/A")
    fournisseur_email = doc.get("fournisseur_email") or doc.get("fournisseur", {}).get("email", "N/A")
    fournisseur_mf = doc.get("fournisseur_matricule_fiscal") or doc.get("fournisseur", {}).get("matricule_fiscal", "N/A")
    client_nom = doc.get("client_nom") or doc.get("client", {}).get("nom", "N/A")
    client_adresse = doc.get("client_adresse") or doc.get("client", {}).get("adresse", "N/A")

    info_data = [
        ["", "Fournisseur", "Client"],
        ["Nom", str(fournisseur_nom or "N/A"), str(client_nom or "N/A")],
        ["Adresse", str(fournisseur_adresse or "N/A"), str(client_adresse or "N/A")],
        ["Téléphone", str(fournisseur_tel or "N/A"), "—"],
        ["Email", str(fournisseur_email or "N/A"), "—"],
        ["MF", str(fournisseur_mf or "N/A"), "—"],
    ]

    info_table = Table(info_data, colWidths=[3 * cm, 6.5 * cm, 6.5 * cm])
    info_table.setStyle(TableStyle([
        # En-tête
        ("BACKGROUND", (1, 0), (1, 0), VIOLET_DARK),
        ("BACKGROUND", (2, 0), (2, 0), VIOLET_MID),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        # Corps
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 1), (0, -1), GRAY_TEXT),
        ("BACKGROUND", (0, 1), (-1, -1), GRAY_LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 10))

    # ── Informations facture ─────────────────────────────────────────
    elements.append(Paragraph("📄 Détails du Document", styles["SectionHeader"]))

    facture_numero = doc.get("facture_numero") or doc.get("facture", {}).get("numero", "N/A")
    facture_date = doc.get("facture_date") or doc.get("facture", {}).get("date", "N/A")
    facture_devise = doc.get("facture_devise") or doc.get("facture", {}).get("devise", "TND")

    fac_data = [
        ["N° Facture", str(facture_numero or "N/A")],
        ["Date", str(facture_date or "N/A")],
        ["Devise", str(facture_devise or "TND")],
    ]
    fac_table = Table(fac_data, colWidths=[4 * cm, 12 * cm])
    fac_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), GRAY_TEXT),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(fac_table)
    elements.append(Spacer(1, 10))

    # ── Articles ─────────────────────────────────────────────────────
    import json
    articles = doc.get("articles", [])

    # Si articles vient du raw_json
    if not articles and doc.get("raw_json"):
        raw = doc["raw_json"]
        if isinstance(raw, str):
            raw = json.loads(raw)
        articles = raw.get("articles", [])

    if articles:
        elements.append(Paragraph("📦 Articles", styles["SectionHeader"]))

        art_data = [["#", "Désignation", "Qté", "P.U.", "Total"]]
        for i, art in enumerate(articles):
            if isinstance(art, dict):
                art_data.append([
                    str(i + 1),
                    str(art.get("designation", "—"))[:50],
                    str(art.get("quantite", "—")),
                    f"{float(art.get('prix_unitaire', 0)):.3f}" if art.get("prix_unitaire") else "—",
                    f"{float(art.get('total_ligne', 0)):.3f}" if art.get("total_ligne") else "—",
                ])

        art_table = Table(art_data, colWidths=[1 * cm, 8 * cm, 2 * cm, 2.5 * cm, 2.5 * cm])
        art_table.setStyle(TableStyle([
            # En-tête
            ("BACKGROUND", (0, 0), (-1, 0), VIOLET_DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            # Corps
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("BACKGROUND", (0, 1), (-1, -1), GRAY_LIGHT),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.white),
            ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            # Alterner les couleurs
            *[("BACKGROUND", (0, i), (-1, i), colors.white)
              for i in range(2, len(art_data), 2)],
        ]))
        elements.append(art_table)
        elements.append(Spacer(1, 10))

    # ── Totaux ───────────────────────────────────────────────────────
    elements.append(Paragraph("💰 Totaux", styles["SectionHeader"]))

    devise = str(facture_devise or "TND")
    total_ht = doc.get("total_ht") or doc.get("totaux", {}).get("total_ht", 0)
    total_tva = doc.get("total_tva") or doc.get("totaux", {}).get("total_tva", 0)
    total_ttc = doc.get("total_ttc") or doc.get("totaux", {}).get("total_ttc", 0)
    timbre = doc.get("timbre_fiscal") or doc.get("totaux", {}).get("timbre_fiscal")

    totaux_data = [
        ["Total HT", f"{float(total_ht or 0):.3f} {devise}"],
        ["Total TVA", f"{float(total_tva or 0):.3f} {devise}"],
        ["Total TTC", f"{float(total_ttc or 0):.3f} {devise}"],
    ]
    if timbre:
        totaux_data.append(["Timbre fiscal", f"{float(timbre):.3f} {devise}"])

    totaux_table = Table(totaux_data, colWidths=[4 * cm, 4 * cm])
    totaux_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        # Ligne TTC en gras et violet
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (1, 2), (1, 2), VIOLET_DARK),
        ("FONTSIZE", (0, 2), (-1, 2), 12),
        ("LINEABOVE", (0, 2), (-1, 2), 1, VIOLET_LIGHT),
    ]))

    # Aligner le tableau des totaux à droite
    wrapper = Table([[totaux_table]], colWidths=[16 * cm])
    wrapper.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "RIGHT")]))
    elements.append(wrapper)

    # ── Footer ───────────────────────────────────────────────────────
    elements.append(Spacer(1, 30))
    elements.append(HRFlowable(
        width="100%", thickness=1, color=GRAY_TEXT,
        spaceBefore=10, spaceAfter=6
    ))
    elements.append(Paragraph(
        f"Généré par DocuFlow AI v2.0 — {datetime.now().strftime('%d/%m/%Y à %H:%M')} — "
        f"PFE 2025 · Mistral OCR · PostgreSQL",
        styles["Footer"]
    ))

    # Construire le PDF
    pdf.build(elements)
    return buffer.getvalue()


def generate_summary_pdf(documents: list[dict], title: str = "Synthèse des Documents") -> bytes:
    """
    Génère un PDF de synthèse pour une liste de documents.

    Args:
        documents: Liste de dicts de documents
        title: Titre du rapport

    Returns:
        bytes du fichier PDF
    """
    buffer = BytesIO()
    pdf = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )

    styles = _get_styles()
    elements = []

    # En-tête
    elements.append(Paragraph("📄 DocuFlow AI", styles["DocuTitle"]))
    elements.append(Paragraph(title, styles["DocuSubtitle"]))
    elements.append(HRFlowable(
        width="100%", thickness=2, color=VIOLET_LIGHT,
        spaceBefore=4, spaceAfter=12
    ))

    # Statistiques globales
    total = len(documents)
    valides = sum(1 for d in documents if d.get("is_valid"))
    total_ttc = sum(float(d.get("total_ttc", 0) or 0) for d in documents)

    stats_data = [
        ["Documents", str(total)],
        ["Valides", f"{valides} ({valides/total*100:.0f}%)" if total > 0 else "0"],
        ["Total TTC", f"{total_ttc:,.3f} TND"],
    ]
    stats_table = Table(stats_data, colWidths=[4 * cm, 4 * cm])
    stats_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), GRAY_TEXT),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(stats_table)
    elements.append(Spacer(1, 12))

    # Tableau des documents
    elements.append(Paragraph("📋 Liste des Documents", styles["SectionHeader"]))

    header = ["#", "Fournisseur", "N° Facture", "Date", "TTC", "Statut"]
    table_data = [header]

    for i, doc in enumerate(documents):
        status = "✓" if doc.get("is_valid") else "⚠"
        table_data.append([
            str(i + 1),
            str(doc.get("fournisseur_nom", "N/A") or "N/A")[:25],
            str(doc.get("facture_numero", "N/A") or "N/A")[:15],
            str(doc.get("facture_date", "N/A") or "N/A")[:10],
            f"{float(doc.get('total_ttc', 0) or 0):.3f}",
            status,
        ])

    doc_table = Table(
        table_data,
        colWidths=[1 * cm, 5 * cm, 3 * cm, 2.5 * cm, 3 * cm, 1.5 * cm]
    )
    doc_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), VIOLET_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("FONTSIZE", (0, 1), (-1, -1), 7),
        ("BACKGROUND", (0, 1), (-1, -1), GRAY_LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.white),
        ("ALIGN", (4, 1), (4, -1), "RIGHT"),
        ("ALIGN", (5, 1), (5, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        *[("BACKGROUND", (0, i), (-1, i), colors.white)
          for i in range(2, len(table_data), 2)],
    ]))
    elements.append(doc_table)

    # Footer
    elements.append(Spacer(1, 30))
    elements.append(HRFlowable(
        width="100%", thickness=1, color=GRAY_TEXT,
        spaceBefore=10, spaceAfter=6
    ))
    elements.append(Paragraph(
        f"Généré par DocuFlow AI v2.0 — {datetime.now().strftime('%d/%m/%Y à %H:%M')} — "
        f"{total} documents",
        styles["Footer"]
    ))

    pdf.build(elements)
    return buffer.getvalue()
