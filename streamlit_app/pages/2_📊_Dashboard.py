"""
DocuFlow AI — Dashboard Analytique
KPIs, graphiques Plotly, exports Excel/CSV/PDF.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
from styles import apply_theme, render_sidebar
from auth import is_authenticated, get_current_user
from database import DatabaseManager

if not is_authenticated():
    st.switch_page("app.py")
    st.stop()

apply_theme()
user = get_current_user()
render_sidebar(user)

st.markdown("""
<div class="main-header">
    <h1>📊 Dashboard Analytique</h1>
    <p>Vue d'ensemble de vos documents traités et statistiques clés</p>
</div>
""", unsafe_allow_html=True)

# ── Charger les données ──────────────────────────────────────────────
try:
    db = DatabaseManager()
    stats = db.get_dashboard_stats()
    documents = db.get_documents(limit=500)
except Exception as e:
    st.error(f"❌ Connexion BDD échouée : {e}")
    st.stop()

# ── KPIs ─────────────────────────────────────────────────────────────
st.markdown("### 📈 Indicateurs Clés")
k1, k2, k3, k4, k5 = st.columns(5)

total_docs = stats.get("total_documents", 0) or 0
valid_docs = stats.get("valid_documents", 0) or 0
total_facture = float(stats.get("total_facture", 0) or 0)
nb_fournisseurs = stats.get("unique_fournisseurs", 0) or 0
avg_conf = float(stats.get("avg_confidence", 0) or 0)
taux_succes = (valid_docs / total_docs * 100) if total_docs > 0 else 0

with k1:
    st.markdown(f'<div class="stat-box"><div class="stat-number">{total_docs}</div><div class="stat-label">Documents traités</div></div>', unsafe_allow_html=True)
with k2:
    st.markdown(f'<div class="stat-box"><div class="stat-number">{total_facture:,.0f}</div><div class="stat-label">Total facturé (TND)</div></div>', unsafe_allow_html=True)
with k3:
    st.markdown(f'<div class="stat-box"><div class="stat-number">{taux_succes:.0f}%</div><div class="stat-label">Taux de succès OCR</div></div>', unsafe_allow_html=True)
with k4:
    st.markdown(f'<div class="stat-box"><div class="stat-number">{nb_fournisseurs}</div><div class="stat-label">Fournisseurs uniques</div></div>', unsafe_allow_html=True)
with k5:
    st.markdown(f'<div class="stat-box"><div class="stat-number">{avg_conf:.0%}</div><div class="stat-label">Confiance moyenne IA</div></div>', unsafe_allow_html=True)

if total_docs == 0:
    st.info("📭 Aucun document traité. Allez dans **Extraction** pour commencer.")
    st.stop()

# ── Graphiques ───────────────────────────────────────────────────────
st.markdown("### 📉 Visualisations")

col_chart1, col_chart2 = st.columns(2)

# Facturation mensuelle
with col_chart1:
    par_mois = stats.get("par_mois", [])
    if par_mois:
        df_mois = pd.DataFrame(par_mois)
        df_mois = df_mois.sort_values("mois")
        fig1 = px.bar(
            df_mois, x="mois", y="montant_ttc",
            title="💰 Facturation Mensuelle (TND)",
            labels={"mois": "Mois", "montant_ttc": "Montant TTC"},
            color_discrete_sequence=["#8b5cf6"]
        )
        fig1.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e2e8f0", xaxis_gridcolor="rgba(139,92,246,0.1)",
            yaxis_gridcolor="rgba(139,92,246,0.1)"
        )
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("Pas de données mensuelles")

# Top fournisseurs
with col_chart2:
    top_fournisseurs = stats.get("top_fournisseurs", [])
    if top_fournisseurs:
        df_top = pd.DataFrame(top_fournisseurs)
        fig2 = px.bar(
            df_top, x="total", y="fournisseur_nom", orientation="h",
            title="🏢 Top Fournisseurs",
            labels={"total": "Total facturé (TND)", "fournisseur_nom": ""},
            color_discrete_sequence=["#60a5fa"]
        )
        fig2.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e2e8f0", yaxis=dict(autorange="reversed"),
            xaxis_gridcolor="rgba(139,92,246,0.1)"
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Pas de données fournisseurs")

col_chart3, col_chart4 = st.columns(2)

# Répartition par type
with col_chart3:
    par_type = stats.get("par_type", [])
    if par_type:
        df_type = pd.DataFrame(par_type)
        fig3 = px.pie(
            df_type, names="type", values="count",
            title="📋 Répartition par Type",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#e2e8f0")
        st.plotly_chart(fig3, use_container_width=True)

# Documents par mois (count)
with col_chart4:
    if par_mois:
        df_count = pd.DataFrame(par_mois).sort_values("mois")
        fig4 = px.line(
            df_count, x="mois", y="count",
            title="📈 Volume de Documents par Mois",
            labels={"mois": "Mois", "count": "Nombre"},
            markers=True, color_discrete_sequence=["#34d399"]
        )
        fig4.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e2e8f0", xaxis_gridcolor="rgba(139,92,246,0.1)",
            yaxis_gridcolor="rgba(139,92,246,0.1)"
        )
        st.plotly_chart(fig4, use_container_width=True)

# ── Export des données ───────────────────────────────────────────────────────────
st.markdown("### ⬇️ Export des Données")

if documents:
    df_export = pd.DataFrame(documents)
    cols_display = [c for c in ["id", "file_name", "fournisseur_nom", "facture_numero",
                    "facture_date", "total_ht", "total_tva", "total_ttc",
                    "document_class", "is_valid", "confidence_score", "created_at"] if c in df_export.columns]
    df_display = df_export[cols_display] if cols_display else df_export

    col_csv, col_excel, col_pdf = st.columns(3)

    # ── CSV : récapitulatif documents ──
    with col_csv:
        csv = df_display.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📄 Export CSV (documents)",
            csv, "docuflow_documents.csv", "text/csv",
            use_container_width=True
        )

    # ── Excel : articles uniquement (référence, désignation, qte, prix, fournisseur) ──
    with col_excel:
        try:
            articles_data = db.get_articles_for_export()
            if articles_data:
                df_articles = pd.DataFrame(articles_data)
                output = BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    df_articles.to_excel(writer, index=False, sheet_name="Articles")
                    # Ajuster la largeur des colonnes
                    ws = writer.sheets["Articles"]
                    for col in ws.columns:
                        max_len = max(len(str(cell.value or "")) for cell in col)
                        ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 50)
                st.download_button(
                    "📊 Export Excel (articles)",
                    output.getvalue(),
                    "docuflow_articles.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            else:
                st.info("📦 Aucun article en base")
        except Exception as e:
            st.warning(f"Export Excel indisponible : {e}")

    # ── PDF : synthèse ──
    with col_pdf:
        try:
            from pdf_export import generate_summary_pdf
            pdf_bytes = generate_summary_pdf(documents, title="Synthèse DocuFlow AI")
            st.download_button(
                "📕 Export PDF", pdf_bytes, "docuflow_synthese.pdf",
                "application/pdf", use_container_width=True
            )
        except Exception as e:
            st.warning(f"Export PDF indisponible : {e}")
