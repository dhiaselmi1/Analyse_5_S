import os
import sys
import threading
import time
import re
import requests
from PyPDF2 import PdfReader
from fpdf import FPDF
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
import itertools
import json
from datetime import datetime
import unicodedata
from typing import Dict, List, Optional

# === Configuration ===
INPUT_PDF_PATH = os.path.join("pdfs", "document.pdf")
OUTPUT_PDF_PATH = os.path.join("output", "rapport_porter_enrichi.pdf")
MODEL_NAME = "llama3:instruct"
SPINNER_RUNNING = True

# Optionnel : API keys pour des recherches plus avancées
SERPAPI_KEY = os.getenv("SERPAPI_KEY")  # Pour Google Search API
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")  # Pour News API


# === Animation spinner ===
def spinner(message="🔄 Traitement en cours..."):
    for c in itertools.cycle(["|", "/", "-", "\\"]):
        if not SPINNER_RUNNING:
            break
        sys.stdout.write(f"\r{message} {c}")
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write(f"\r✅ {message.replace('🔄', '').strip()} terminé !       \n")


# === Étape 1 : Lire le contenu du PDF ===
def read_pdf(file_path: str) -> str:
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text.strip()


# === Étape 2 : Extraire les informations de l'entreprise ===
def extract_company_info(text: str) -> Dict[str, any]:
    """Extrait le nom de l'entreprise et ses domaines d'activité du PDF"""

    template = """
    Analyse le texte suivant et extrait uniquement les informations demandées au format JSON :

    {text}

    Retourne UNIQUEMENT un JSON valide avec cette structure exacte :
    {{
        "nom_entreprise": "nom exact de l'entreprise",
        "domaines_activite": ["domaine1", "domaine2", "domaine3"],
        "secteur_principal": "secteur principal",
        "pays": "pays où opère l'entreprise",
        "concurrents_mentionnes": ["concurrent1", "concurrent2"]
    }}

    Assure-toi que le JSON soit valide et sans texte supplémentaire.
    """

    prompt = PromptTemplate(template=template, input_variables=["text"])
    llm = OllamaLLM(model=MODEL_NAME)
    runner = prompt | llm

    global SPINNER_RUNNING
    SPINNER_RUNNING = True
    t = threading.Thread(target=spinner, args=("🔍 Extraction des informations entreprise...",))
    t.start()

    try:
        result = runner.invoke({"text": text[:8000]})
        SPINNER_RUNNING = False
        t.join()

        # Nettoyer le résultat et extraire le JSON
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            company_info = json.loads(json_match.group())
            print(company_info)
            return company_info
        else:
            print("⚠️  Impossible d'extraire les informations au format JSON")
            return {}
    except Exception as e:
        SPINNER_RUNNING = False
        t.join()
        print(f"❌ Erreur lors de l'extraction : {e}")
        return {}


# === Étape 3 : Recherche web enrichie ===
def web_search_basic(query: str, num_results: int = 5) -> List[Dict]:
    """Recherche web basique avec requests (sans API payante)"""
    try:
        # Simulation d'une recherche - à remplacer par une vraie API
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        # Pour une vraie implémentation, utilisez une API comme SerpAPI, Google Custom Search, etc.
        # Simulation avec dates et sources réalistes pour le template
        current_date = datetime.now()
        results = [
            {
                "title": f"Dernières actualités - {query}",
                "snippet": "Informations récentes trouvées sur le web avec contexte détaillé...",
                "url": "https://example.com/news/article1",
                "date": current_date.strftime("%Y-%m-%d"),
                "source": "Les Échos",
                "published_date": "2025-01-15"
            },
            {
                "title": f"Analyse sectorielle - {query}",
                "snippet": "Étude approfondie des tendances du marché...",
                "url": "https://example.com/analysis/sector",
                "date": current_date.strftime("%Y-%m-%d"),
                "source": "Reuters",
                "published_date": "2025-01-10"
            }
        ]

        return results[:num_results]
    except Exception as e:
        print(f"❌ Erreur de recherche web : {e}")
        return []


def collect_company_data(company_info: Dict) -> Dict[str, List]:
    """Collecte des données web sur l'entreprise et ses concurrents"""

    if not company_info.get("nom_entreprise"):
        return {"error": "Nom d'entreprise non trouvé"}

    company_name = company_info["nom_entreprise"]
    domains = company_info.get("domaines_activite", [])
    competitors = company_info.get("concurrents_mentionnes", [])

    collected_data = {
        "company_official": [],
        "company_linkedin": [],
        "industry_news": [],
        "competitor_news": [],
        "search_metadata": {
            "timestamp": datetime.now().isoformat(),
            "company": company_name,
            "domains_searched": domains,
            "competitors_searched": competitors
        }
    }

    global SPINNER_RUNNING

    # 1. Site officiel de l'entreprise
    SPINNER_RUNNING = True
    t1 = threading.Thread(target=spinner, args=("🌐 Recherche site officiel...",))
    t1.start()

    official_query = f"{company_name} site officiel actualités 2025"
    collected_data["company_official"] = web_search_basic(official_query, 5)
    print(collected_data["company_official"])
    SPINNER_RUNNING = False
    t1.join()

    # 2. LinkedIn de l'entreprise
    SPINNER_RUNNING = True
    t2 = threading.Thread(target=spinner, args=("💼 Recherche LinkedIn entreprise...",))
    t2.start()

    linkedin_query = f"{company_name} linkedin company news updates"
    collected_data["company_linkedin"] = web_search_basic(linkedin_query, 5)
    print(collected_data["company_linkedin"])
    SPINNER_RUNNING = False
    t2.join()

    # 3. Actualités du secteur pour chaque domaine
    for domain in domains[:3]:  # Limiter à 3 domaines
        SPINNER_RUNNING = True
        t3 = threading.Thread(target=spinner, args=(f"📰 Actualités {domain}...",))
        t3.start()

        news_query = f"actualités {domain} tendances marché janvier 2025"
        domain_news = web_search_basic(news_query, 4)

        # Ajouter métadonnées pour identifier le domaine
        for news in domain_news:
            news["domain"] = domain
            news["search_type"] = "industry_news"

        collected_data["industry_news"].extend(domain_news)
        print(collected_data["industry_news"])
        SPINNER_RUNNING = False
        t3.join()

    # 4. Actualités des concurrents
    for competitor in competitors[:4]:  # Limiter à 4 concurrents
        SPINNER_RUNNING = True
        t4 = threading.Thread(target=spinner, args=(f"🏢 Actualités {competitor}...",))
        t4.start()

        competitor_query = f'"{competitor}" actualités news 2025 stratégie'
        competitor_news = web_search_basic(competitor_query, 10)

        # Ajouter métadonnées pour identifier le concurrent
        for news in competitor_news:
            news["competitor"] = competitor
            news["search_type"] = "competitor_news"

        collected_data["competitor_news"].extend(competitor_news)

        SPINNER_RUNNING = False
        t4.join()

    return collected_data


# === Étape 4 : Générer l'analyse Porter enrichie ===
def generate_enhanced_porter_analysis(original_text: str, company_info: Dict, web_data: Dict) -> str:
    """Génère une analyse Porter enrichie avec les données web"""

    template = """
    Tu es un expert en stratégie d'entreprise et en intelligence économique.

    Ta mission est de créer un **rapport en francais enrichi d'au moins 10 000 caractères** selon le modèle des **5 forces de Porter**, pour l’entreprise suivante, en exploitant toutes les données fournies :

    ---

    ## INFORMATIONS ENTREPRISE :
    {company_info}

    ## DOCUMENT ORIGINAL :
    {original_text}

    ## DONNÉES WEB COLLECTÉES :
    {web_data}

    ---

    Génère un rapport selon cette structure **exacte** :

    # RAPPORT D'ANALYSE PORTER ENRICHI - {company_name}

    ## SYNTHÈSE EXÉCUTIVE  
    Fais une synthèse dense, percutante et stratégique des forces en présence et de la position concurrentielle globale de l'entreprise.

    ## INFORMATIONS ENTREPRISE
    - **Nom** : {company_name}  
    - **Secteurs d'activité** : {domains}  
    - **Positionnement** : analyse basée sur les données disponibles et les actualités collectées

    ---

    ## 1. RIVALITÉ ENTRE CONCURRENTS EXISTANTS  
    ### Données du marché récentes  
    [Inclure au minimum une actualité récente sur un concurrent direct avec date et source]  

    ### Analyse stratégique  
    - Nombre et taille des concurrents  
    - Intensité concurrentielle actuelle  
    - Innovations ou différenciations identifiées  
    - Parts de marché estimées  
    - Barrières de sortie

    ---

    ## 2. MENACE DES NOUVEAUX ENTRANTS  
    ### Tendances du secteur  
    [Inclure au minimum une actualité sur les nouvelles entreprises ou innovations entrantes]  

    ### Analyse  
    - Barrières à l'entrée actuelles  
    - Évolution réglementaire récente  
    - Besoins en capital / technologie  
    - Nouveaux entrants identifiés

    ---

    ## 3. MENACE DES PRODUITS DE SUBSTITUTION  
    ### Innovations / Disruptions identifiées  
    [Utiliser les données web pour citer au moins une technologie ou alternative crédible]  

    ### Analyse  
    - Substituts viables et en développement  
    - Facilité de substitution pour les clients  
    - Niveau de menace pour le modèle économique actuel

    ---

    ## 4. POUVOIR DE NÉGOCIATION DES CLIENTS  
    ### Évolution du marché client  
    [Basé sur les tendances web avec source]  

    ### Analyse  
    - Volume et diversité de la clientèle  
    - Sensibilité prix et comportement d’achat  
    - Possibilités de substitution côté client  
    - Tendances comportementales récentes

    ---

    ## 5. POUVOIR DE NÉGOCIATION DES FOURNISSEURS  
    ### Informations sur la chaîne d’approvisionnement  
    [Basé sur les données ou actualités récentes si présentes]  

    ### Analyse  
    - Concentration des fournisseurs  
    - Spécificité des intrants  
    - Risques d’approvisionnement  
    - Négociation et dépendance

    ---

    ## DERNIÈRES ACTUALITÉS SECTORIELLES  
    **Inclure obligatoirement au moins 3 actualités pertinentes** pour **les domaines d’activité de l’entreprise**, et **au moins 3 pour ses concurrents directs**.

    ### Actualités des domaines d'activité  
    Pour chaque actualité :  
    - **Titre**  
    - **Date de publication**  
    - **Source** (nom du média/site)  
    - **Résumé** : au moins 500 caractères  
    - **Impact stratégique** : en quoi cela affecte l’entreprise

    ### Actualités des concurrents identifiés  
    Pour chaque actualité liée à un concurrent :  
    - **Concurrent concerné**  
    - **Titre de l’actualité**  
    - **Date de publication**  
    - **Source**  
    - **Résumé** : au moins 500 caractères  
    - **Analyse stratégique** : implication concurrentielle, menace ou opportunité

    ---

    ## RECOMMANDATIONS STRATÉGIQUES ENRICHIES  
    ### Actions prioritaires  
    1. **Court terme (0-6 mois)** : décisions opérationnelles rapides basées sur les dernières actualités  
    2. **Moyen terme (6-18 mois)** : alignement stratégique basé sur les tendances sectorielles  
    3. **Long terme (18+ mois)** : anticipation et vision stratégique durable

    ### Opportunités identifiées  
    [Basé sur les actualités et données avec sources]

    ### Menaces à surveiller  
    [Basé sur l’analyse concurrentielle ou environnementale]

    ---

    ## SOURCES ET VEILLE STRATÉGIQUE  
    - Liste des **sources officielles** (avec URL)  
    - Liste des **actualités sectorielles analysées** (titre, date, source, lien si disponible)  
    - Liste des **sources concurrentielles** utilisées  
    - Recommandations de veille continue (indicateurs, fréquence, outils)

    ---

    **IMPORTANT :**
    - Fournir **au moins 10 000 caractères** (ne résume pas trop).  
    - Pour chaque actualité, inclure la **date de publication**, le **nom de la source**, et **le lien** (si disponible).  
    - Réponds uniquement avec le rapport structuré ci-dessus. Aucun texte hors-structure. Pas d'introduction ni de conclusion globale hors rapport.
    """

    company_name = company_info.get("nom_entreprise", "Entreprise")
    domains = ", ".join(company_info.get("domaines_activite", []))

    prompt = PromptTemplate(
        template=template,
        input_variables=["company_info", "original_text", "web_data", "company_name", "domains"]
    )

    llm = OllamaLLM(model=MODEL_NAME)
    runner = prompt | llm

    global SPINNER_RUNNING
    SPINNER_RUNNING = True
    t = threading.Thread(target=spinner, args=("🧠 Génération analyse Porter enrichie...",))
    t.start()

    result = runner.invoke({
        "company_info": json.dumps(company_info, indent=2, ensure_ascii=False),
        "original_text": original_text[:4000],
        "web_data": json.dumps(web_data, indent=2, ensure_ascii=False)[:3000],
        "company_name": company_name,
        "domains": domains
    })

    SPINNER_RUNNING = False
    t.join()

    return result


# === Étape 5 : Générer un PDF enrichi ===
def clean_text(text: str) -> str:
    """Nettoie les caractères spéciaux pour éviter les erreurs Unicode dans le PDF."""
    return unicodedata.normalize("NFKD", text).encode("ASCII", "ignore").decode("ASCII")


def create_enhanced_pdf_report(text: str, company_info: Dict, output_path: str):
    """Crée un PDF enrichi avec métadonnées"""

    pdf = FPDF()
    pdf.add_page()

    # En-tête
    pdf.set_font("Arial", "B", 16)
    company_name = company_info.get("nom_entreprise", "Entreprise")
    pdf.cell(0, 10, f"ANALYSE PORTER - {clean_text(company_name)}", ln=True, align="C")

    pdf.set_font("Arial", size=10)
    pdf.cell(0, 5, f"Genere le {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
    pdf.ln(10)

    # Contenu
    pdf.set_font("Arial", size=10)
    lines = text.split("\n")

    for line in lines:
        cleaned_line = clean_text(line)
        if line.startswith("#"):
            pdf.set_font("Arial", "B", 12)
        elif line.startswith("##"):
            pdf.set_font("Arial", "B", 11)
        else:
            pdf.set_font("Arial", size=10)

        pdf.multi_cell(0, 6, cleaned_line)
        pdf.ln(2)

    # Créer le dossier output s'il n'existe pas
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    pdf.output(output_path)


# === Main enrichi ===
