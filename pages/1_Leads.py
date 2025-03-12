import streamlit as st
import sqlite3
import pandas as pd

st.set_page_config(page_title="Le charte visite 🐱 - Voir les leads", layout="centered")
st.title("Le charte visite 🐱 - Voir les leads")

# Connexion à la base de données
conn = sqlite3.connect("leads.db", check_same_thread=False)
cursor = conn.cursor()

# Fonction pour vérifier si une table existe
def table_exists(cursor, table_name):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cursor.fetchone() is not None

# Fonction pour créer la table si elle n'existe pas
def create_leads_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ocr_text TEXT,
            nom TEXT,
            prenom TEXT,
            telephone TEXT,
            mail TEXT,
            agent1 TEXT,
            agent2 TEXT,
            agent3 TEXT,
            qualification TEXT,
            note TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

# Fonction pour ajouter une colonne si elle est absente
def add_column_if_missing(cursor, table, column, col_type):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    if column not in columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        conn.commit()

# Création de la table si elle n'existe pas
create_leads_table(cursor)

# Migration du schéma : ajout des colonnes manquantes
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
        "Réponse fictive agent1",
        "Réponse fictive agent2",
        "Réponse fictive agent3",
        "Smart Talk",
        "Ceci est une note fictive"
    )
    cursor.execute(
        "INSERT INTO leads (ocr_text, nom, prenom, telephone, mail, agent1, agent2, agent3, qualification, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        dummy_data
    )
    conn.commit()
    st.success("Ligne fictive ajoutée.")

# Bouton pour reset la base de données (supprime toutes les lignes)
if st.button("Reset la base de données"):
    cursor.execute("DELETE FROM leads")
    conn.commit()
    st.success("La base de données a été réinitialisée.")

# Récupération et affichage des données
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
        st.info("Aucun lead n'a été enregistré pour le moment.")
except Exception as e:
    st.error("Erreur lors de la récupération des leads : " + str(e))

# Fermeture de la connexion à la base de données
conn.close()
