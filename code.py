import streamlit as st
import os
import base64
import json
import time
import re
import sqlite3
import pandas as pd
from openai import OpenAI
from mistralai import Mistral
from tavily import TavilyClient

##############################
# Clés API & initialisation
##############################
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

if not OPENAI_API_KEY or not MISTRAL_API_KEY or not TAVILY_API_KEY:
    st.error("Veuillez définir les variables OPENAI_API_KEY, MISTRAL_API_KEY et TAVILY_API_KEY dans votre environnement.")
    st.stop()

client_openai = OpenAI(api_key=OPENAI_API_KEY)
client_mistral = Mistral(api_key=MISTRAL_API_KEY)
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

##############################
# Connexion à la base SQLite
##############################
conn = sqlite3.connect("leads.db", check_same_thread=False)
cursor = conn.cursor()

##############################
# Fonctions utilitaires
##############################

def clean_response(response):
    """Nettoie la réponse en supprimant les tags HTML et convertit '\\n' en retours à la ligne."""
    match = re.search(r'value="(.*?)"\)', response, re.DOTALL)
    cleaned = match.group(1) if match else response
    cleaned = re.sub(r'<[^>]+>', '', cleaned)
    return cleaned.replace("\\n", "\n").strip()

def extract_text_from_ocr_response(ocr_response):
    """Extrait le texte OCR en ignorant les balises image."""
    extracted_text = ""
    pages = getattr(ocr_response, "pages", ocr_response if isinstance(ocr_response, list) else [])
    for page in pages:
        if hasattr(page, "markdown") and page.markdown:
            lines = page.markdown.split("\n")
            filtered = [line.strip() for line in lines if not line.startswith("![")]
            if filtered:
                extracted_text += "\n".join(filtered) + "\n"
    return extracted_text.strip()

def wait_for_run_completion(thread_id, run_id, timeout=30):
    """Attend la fin d'un run d'assistant avec un timeout de 30 secondes."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        time.sleep(1)
        run = client_openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        if run.status in ['completed', 'failed', 'requires_action']:
            return run
    return None  # Timeout atteint

def parse_agent1_response(text):
    """Extrait Nom, Prénom, Téléphone et Mail à partir de la réponse de l'assistant."""
    data = {"nom": "", "prenom": "", "telephone": "", "mail": ""}
    nom = re.search(r"Nom\s*:\s*(.+)", text)
    prenom = re.search(r"Pr[ée]nom\s*:\s*(.+)", text)
    tel = re.search(r"T[eé]l[eé]phone?\s*:\s*(.+)", text, re.IGNORECASE)
    mail = re.search(r"Mail\s*:\s*([\w\.-]+@[\w\.-]+\.\w+)", text)

    if nom:
        data["nom"] = nom.group(1).strip()
    if prenom:
        data["prenom"] = prenom.group(1).strip()
    if tel:
        data["telephone"] = tel.group(1).strip()
    if mail:
        data["mail"] = mail.group(1).strip()
    
    return data

##############################
# Interface utilisateur
##############################
st.subheader("Capture / Upload de la carte de visite")

image_file = st.camera_input("Prenez une photo des cartes de visite")
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align:center;'>OU</h4>", unsafe_allow_html=True)
uploaded_file = st.file_uploader("Uploader la carte", type=["jpg", "jpeg", "png"])

qualification = st.selectbox("Qualification du lead", ["Smart Talk", "Formation", "Audit", "Modules IA"])
note = st.text_area("Ajouter une note", placeholder="Entrez votre note ici...")

if note.strip() == "":
    st.error("Veuillez saisir une note avant de continuer.")
    st.stop()

# Récupération de l'image
image_data_uri = None
if image_file is not None:
    st.image(image_file, caption="Carte capturée", use_column_width=True)
    image_bytes = image_file.getvalue()
elif uploaded_file is not None:
    st.image(uploaded_file, caption="Carte uploadée", use_column_width=True)
    image_bytes = uploaded_file.getvalue()
else:
    st.info("Veuillez capturer ou uploader une photo de la carte.")

if image_bytes:
    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    image_data_uri = f"data:image/jpeg;base64,{base64_image}"

# Traitement de l'image
if st.button("Envoyer la note"):
    if not image_data_uri:
        st.error("Aucune image fournie.")
    else:
        try:
            # Extraction OCR
            ocr_response = client_mistral.ocr.process(
                model="mistral-ocr-latest",
                document={"type": "image_url", "image_url": image_data_uri}
            )
            ocr_text = extract_text_from_ocr_response(ocr_response)

            if not ocr_text:
                st.warning("Aucun texte exploitable n'a été extrait.")
            else:
                st.subheader("Texte OCR extrait :")
                st.text(ocr_text)

                # Assistant 1 : Extraction et recherche
                thread1 = client_openai.beta.threads.create()
                client_openai.beta.threads.messages.create(
                    thread_id=thread1.id, role="user", content=f"Données extraites :\n{ocr_text}"
                )
                run1 = client_openai.beta.threads.runs.create(
                    thread_id=thread1.id, assistant_id="assistant_id_1"
                )
                run1 = wait_for_run_completion(thread1.id, run1.id)
                response_agent1 = run1.result if run1 else "Erreur lors de la récupération"

                st.subheader("Réponse agent 1 :")
                st.markdown(response_agent1)

                # Extraction des champs via parsing
                parsed_data = parse_agent1_response(response_agent1)

                # Envoi en base de données
                cursor.execute(
                    "INSERT INTO leads (ocr_text, nom, prenom, telephone, mail, qualification, note) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (ocr_text, parsed_data["nom"], parsed_data["prenom"], parsed_data["telephone"], parsed_data["mail"], qualification, note)
                )
                conn.commit()
                st.success("Le lead a été ajouté.")

        except Exception as e:
            st.error(f"Erreur : {e}")

