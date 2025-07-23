import os
import sys
import threading
import time
from PyPDF2 import PdfReader
from fpdf import FPDF

from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
import itertools

# === Configuration ===
INPUT_PDF_PATH = os.path.join("pdfs", "document.pdf")
OUTPUT_PDF_PATH = os.path.join("output", "rapport_porter.pdf")
MODEL_NAME = "llama3:instruct"
SPINNER_RUNNING = True

# === Animation spinner ===
def spinner(message="🔄 Génération du rapport..."):
    for c in itertools.cycle(["|", "/", "-", "\\"]):
        if not SPINNER_RUNNING:
            break
        sys.stdout.write(f"\r{message} {c}")
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write("\r✅ Rapport généré avec succès !       \n")

# === Étape 1 : Lire le contenu du PDF ===
def read_pdf(file_path):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text.strip()

# === Étape 2 : Générer l’analyse Porter ===
def generate_porter_analysis(text, model=MODEL_NAME):
    template = """
    Tu es un expert en stratégie d'entreprise. À partir de l'analyse suivante :

    {text}

    Génère un **rapport structuré** et bien riche à partir de data de l'entreprise dont vous avez analysez le document , explicatif, selon le modèle des **5 forces de Porter** (concurrence intra sectorielle, menace de nouveaux entrants , pouvoir de négociation des clients , pouvoir des négociation des fournisseurs, produits de substitution ) pour l'entreprise donnée dans la dataset, en suivant cette structure exacte :

    ---

    ## 1. Rivalité entre concurrents existants  
    Analyse les éléments suivants :
    - Nombre de concurrents  
    - Diversité / différenciation  
    - Part de marché  
    - Barrières de sortie  
    - Coûts de changement  
    - Taux de croissance du secteur  

    ---

    ## 2. Menace des nouveaux entrants  
    Analyse les éléments suivants :  
    - Barrières à l'entrée  
    - Coûts d’entrée initiaux  
    - Besoin de capitaux / technologie  
    - Accès aux canaux de distribution  
    - Réputation de marque des acteurs actuels  

    ---

    ## 3. Menace des produits de substitution  
    Analyse les éléments suivants :  
    - Nombre d'alternatives viables  
    - Coût et facilité de substitution  
    - Différenciation perçue  
    - Sensibilité au prix des clients  

    ---

    ## 4. Pouvoir de négociation des clients  
    Analyse les éléments suivants :  
    - Nombre de clients  
    - Taille et volume des commandes  
    - Possibilité de substitution  
    - Accès à l'information  
    - Sensibilité au prix  

    ---

    ## 5. Pouvoir de négociation des fournisseurs  
    Analyse les éléments suivants :  
    - Nombre et taille des fournisseurs  
    - Spécificité des intrants  
    - Possibilité de substitution  
    - Importance du fournisseur  

    ---

    ## Recommandations stratégiques  
    Sur la base des 5 forces ci-dessus, propose des recommandations concrètes et des pistes d'amélioration possibles pour :  
    - Renforcer la position concurrentielle  
    - Réduire les menaces  
    - Créer un avantage compétitif durable  
    - Innover ou se différencier

    Réponds uniquement avec un **rapport bien structuré**, clair, professionnel, et sans reformuler le texte d'entrée. N’ajoute rien d’autre en dehors de ce rapport.
    """

    prompt = PromptTemplate(template=template, input_variables=["text"])
    llm = OllamaLLM(model=model)
    runner = prompt | llm

    global SPINNER_RUNNING
    SPINNER_RUNNING = True
    t = threading.Thread(target=spinner)
    t.start()

    result = runner.invoke({"text": text[:8000]})

    SPINNER_RUNNING = False
    t.join()

    return result  # ← ici le texte est directement retourné

# === Étape 3 : Générer un PDF ===

import unicodedata

def clean_text(text):
    """Nettoie les caractères spéciaux pour éviter les erreurs Unicode dans le PDF."""
    return unicodedata.normalize("NFKD", text).encode("ASCII", "ignore").decode("ASCII")

def create_pdf_report(text, output_path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    lines = text.split("\n")
    for line in lines:
        pdf.multi_cell(0, 10, clean_text(line))

    pdf.output(output_path)


# === Main ===
if __name__ == "__main__":
    if not os.path.exists(INPUT_PDF_PATH):
        print(f"❌ Fichier introuvable : {INPUT_PDF_PATH}")
        exit(1)

    print("📥 Lecture du PDF...")
    text = read_pdf(INPUT_PDF_PATH)

    print("🧠 Analyse stratégique en cours...")
    analysis = generate_porter_analysis(text)

    print("📄 Création du fichier PDF...")
    create_pdf_report(analysis, OUTPUT_PDF_PATH)

    print(f"📂 Fichier disponible : {OUTPUT_PDF_PATH}")
