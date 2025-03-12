import streamlit as st
import sqlite3
import pandas as pd

st.set_page_config(page_title="Le charte visite ðŸ± - Voir les leads", layout="centered")
st.title("Le charte visite ðŸ± - Voir les leads")

# Connexion Ã  la base de donnÃ©es
conn = sqlite3.connect("leads.db", check_same_thread=False)
cursor = conn.cursor()

# Fonction pour ajouter une colonne si elle n'existe pas
def add_column_if_missing(cursor, table, column, col_type):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    if column not in columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        conn.commit()

# Migration du schÃ©ma : on s'assure que toutes les colonnes sont prÃ©sentes
add_column_if_missing(cursor, "leads", "ocr_text", "TEXT")
add_column_if_missing(cursor, "leads", "nom", "TEXT")
add_column_if_missing(cursor, "leads", "prenom", "TEXT")
add_column_if_missing(cursor, "leads", "telephone", "TEXT")
add_column_if_missing(cursor, "leads", "mail", "TEXT")
add_column_if_missing(cursor, "leads", "agent1", "TEXT")
add_column_if_missing(cursor, "leads", "agent2", "TEXT")
add_column_if_missing(cursor, "leads", "agent3", "TEXT")
add_column_if_missing(cursor, "leads", "qualification", "TEXT")
add_column_if_missing(cursor, "leads", "note", "TEXT")
add_column_if_missing(cursor, "leads", "timestamp", "DATETIME DEFAULT CURRENT_TIMESTAMP")

# Bouton pour ajouter une ligne fictive
if st.button("Ajouter une ligne fictive"):
    dummy_data = (
        "Ceci est un OCR fictif",
        "Doe",
        "John",
        "0123456789",
        "john.doe@example.com",
        "RÃ©ponse fictive agent1",
        "RÃ©ponse fictive agent2",
        "RÃ©ponse fictive agent3",
        "Smart Talk",
        "Ceci est une note fictive"
    )
    cursor.execute(
        "INSERT INTO leads (ocr_text, nom, prenom, telephone, mail, agent1, agent2, agent3, qualification, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        dummy_data
    )
    conn.commit()
    st.success("Ligne fictive ajoutÃ©e.")

# Bouton pour reset la base de donnÃ©es (supprime toutes les lignes)
if st.button("Reset la base de donnÃ©es"):
    cursor.execute("DELETE FROM leads")
    conn.commit()
    st.success("La base de donnÃ©es a Ã©tÃ© rÃ©initialisÃ©e.")

# RÃ©cupÃ©ration et affichage des donnÃ©es
try:
    cursor.execute("""
        SELECT id, ocr_text, nom, prenom, telephone, mail, 
               agent1, agent2, agent3, qualification, note, timestamp 
        FROM leads ORDER BY timestamp DESC
    """)
    rows = cursor.fetchall()
    
    if rows:
        columns = [description[0] for description in cursor.description]
        df = pd.DataFrame(rows, columns=columns)
        st.dataframe(df)
    else:
        st.info("Aucun lead n'a Ã©tÃ© enregistrÃ© pour le moment.")
except Exception as e:
    st.error("Erreur lors de la rÃ©cupÃ©ration des leads : " + str(e))

conn.close()
