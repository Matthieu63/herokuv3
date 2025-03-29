import sqlite3
import os

# Chemins des bases de données
VOCAB_DB = os.path.join(os.path.dirname(__file__), 'vocab.db')
DIALOGUE_DB = os.path.join(os.path.dirname(__file__), 'dialogue.db')


def get_db_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_vocab_db():
    """Crée les tables pour le vocabulaire dans vocab.db."""
    conn = get_db_connection(VOCAB_DB)
    with conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT,
                synthese TEXT,
                youglish TEXT,
                note INTEGER,
                tags TEXT,
                image TEXT,
                exemples TEXT NOT NULL DEFAULT ''
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE
            )
        ''')
    conn.close()

def init_dialogues_db():
    """Crée les tables pour les dialogues dans dialogue.db."""
    conn = get_db_connection(DIALOGUE_DB)
    with conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS dialogues_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                upload_date DATETIME
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS dialogues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER,
                dialogue_number INTEGER,
                personne_a TEXT,
                personne_b TEXT,
                FOREIGN KEY(file_id) REFERENCES dialogues_files(id)
            )
        ''')
    conn.close()
