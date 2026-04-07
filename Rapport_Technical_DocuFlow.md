# Rapport Technique d'Expertise : DocuFlow AI

## 1. Introduction et Objectifs du Projet

**DocuFlow AI** est une solution logicielle innovante conçue pour l'extraction, la classification et le traitement automatisé de documents commerciaux complexes (factures, bons de livraison, reçus). L'objectif principal de ce projet est de numériser et d'automatiser la saisie fastidieuse des métadonnées applicatives et fiscales, réduisant ainsi les erreurs humaines, accélérant les processus comptables et garantissant une traçabilité totale (auditabilité). 

Le projet vient répondre à des problématiques métier concrètes : extraction des tableaux d'articles complexes, gestion des anomalies de calcul TVA/TTC, tout en gérant un flux asynchrone pour les volumétries de fichiers importantes.

---

## 2. Architecture Globale de la Solution

L'architecture de DocuFlow AI s'oriente autour d'un socle applicatif modulaire sous conteneurs (**Docker**), garantissant sa scalabilité, sa sécurité et sa portabilité. Le schéma conceptuel ci-dessous explicite les interactions entre le front-end, le moteur d'intelligence artificielle et la base de données.

```mermaid
flowchart TD
  subgraph "Interface & Interactions (Frontend)"
    UI((Utilisateur Web)) -->|Upload Image/PDF| App[Interface Streamlit]
    UI -->|Visualisation Stats| Dash[Dashboard & Reporting]
  end

  subgraph "Cœur Applicatif (Application Python)"
    App --> Auth[Gestion des Accès & Rôles]
    Auth --> Batch[Moteur de Traitement par Lot]
    Dash --> PDFExcel[Génération PDF / Excel]
    
    Batch --> Engine[Moteur OCR & IA]
    Engine --> Validator[Règles d'Intelligence Métier]
  end

  subgraph "Intelligence Artificielle (API Mistral AI)"
    Engine -->|Payload Base64| MistralOCR[Mistral OCR : Extraction]
    MistralOCR -->|Texte format Markdown| MistralSmall[Mistral Chat : Structuration]
    MistralSmall -->|Mapping de données JSON| Engine
  end

  subgraph "Stockage & Orchestration"
    Validator ==>|Validation & Insert| DB[(PostgreSQL 16)]
    PDFExcel <..>|Requêtes Analytiques (Jointure Articles)| DB
    N8N[Orchestrateur N8N] <..>|Workflows & Webhooks| DB
  end
```

---

## 3. Technologies Utilisées (Stack Technique)

Nous avons fait le choix d'intégrer des technologies de pointe, répondant aux exigences modernes de l'ingénierie logicielle et de l'IA :

*   **Interface (Frontend) & Logique Python :** **Streamlit**. Choisi pour sa capacité à prototyper et déployer à la vitesse de l'éclair des Data Applications complètes. Utilisation combinée avec **Plotly** pour construire des Graphiques dynamiques (répartition mensuelle, taux de succès, tops fournisseurs).
*   **Infrastructure & Conteneurisation :** **Docker et Docker Compose**. Chaque sous-ensemble (Base de données, logiciel d'application, N8N) tourne dans son environnement indépendant isolé dans un réseau bridge `pfa_network`. Résilience renforcée par des health-checks complets.
*   **Base de Données Relationnelle :** **PostgreSQL 16**. Pour la persistance structurée. La base relationnelle lie rigoureusement un Document à ses Lignes d'Articles extraites (`document_articles`) et stocke simultanément les logs d'audit (*Audit Trail*) pour assurer la sécurité et traçabilité.
*   **Les Moteurs Cognitifs (OCR & NLP) :** L'API Cloud **Mistral AI**. 
    *   Le module `mistral-ocr-latest` extrait la géométrie et les textes complexes des scans en Markdown brut.
    *   Le LLM `mistral-small-latest` interprète ce Markdown via à un Prompt Engineering avancé pour le translater vers le vocabulaire métier en structure JSON rigide.
*   **Automatisation Data :** **n8n**. Déployé en tant qu'orchestrateur de workflow pour l'automatisation asynchrone, prêt à s'interconnecter par API ou Webhook aux autres Systèmes de l'Information.
*   **Librairies Data Python :** `Pandas` (nettoyage des DataFrames pour un export Excel épuré des Articles et Fournisseurs) et gestion native `BytesIO`.

---

## 4. Pipeline d'Intelligence Artificielle : Le Cœur du Système

Contrairement aux approches OCR classiques basées uniquement sur des expressions régulières souvent fragiles et dures à maintenir, nous avons conçu un **Pipeline hybride et sémantique en 4 étapes** :

1.  **L'Extraction Geométro-Sémantique (OCR)** : L'image uploadee est convertie en vecteur Base64 et poussée vers le modèle multimodal de Mistral. Nous récupérons du texte enrichi et des tableaux matriciels reconstruits fidèlement en Markdown.
2.  **L'Extracteur Cognitif (LLM Parsing)** : Le texte complet est injecté via prompt vers le modèle Mistral Chat. L'IA a l'ordre absolu d'extraire le référentiel métier (Fournisseur, Client, N° facture, Lignes de références/codes facturés, et Totaux).
3.  **La Classification Intelligente** : Un module annexe de l'AI Engine inspecte le texte pour classifier automatiquement le document (Facture, Bon de Livraison, Reçu) suivant l'inférence des champs qu'il analyse.
4.  **Assurance & Validation (Engine Rules)** : 
    *   Un calculateur arithmétique décode la cohérence financière de l'extraction (`Total Ligne = Qté * PU` ou `HT + TVA = TTC`). Si un écart mathématique existe, l'ordinateur catégorise la faille en **Anomalie Warning / Error**.
    *   Un algorithme statistique calcule le score de confiance global en croisant la présence des extractions LLM et les tokens exacts de l'OCR Markdown de base.

---

## 5. Fonctionnalités Implémentées

Le système offre aujourd'hui de puissants modules fonctionnels :
*   **Extraction Batch Résiliente** : Moteur de file d'attente permettant de charger dizaines d'images d'un coup. Le Processor intègre un système d'auto-retry logiciel qui surmonte tout Rate Limit API sans faire flancher le serveur.
*   **Export Ciblé & Relationnel** : Dans le tableau de bord, des algorithmes transforment les structures de base de données PostgreSQL complexes en vue unifiée : L'utilisateur peut exporter en `Excel` le listing total des **Articles / Références extraits**, intelligemment ralliés au nom de leur fournisseur.
*   **Tableau de Bord KPI** : Outil d'analyse graphique global sur la facturation.
*   **Sécurité (Authentification Modulaire)** : Conception des flux de l'application via les sessions. Blocage d'opérations critiques (suppressions) gérées par le Role-Based Access Control (rôles `admin` vs `comptable` vs `lecteur`).

---

## 6. Conclusion 

Le système DocuFlow AI s'inscrit au sein des standards industriels d'ingénierie logicielle. Il garantit non seulement une extraction d'extrême précision des sous-parties des factures, comme l'ont validé les Exports des articles et des références, mais protège aussi les intégrateurs des échecs d'API par ses relances automatiques et ses contrôles mathématiques post-OCR. Il ouvre de très fortes perspectives évolutives d'intégration grâce à n8n.
