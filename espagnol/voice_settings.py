import os
import sqlite3
from flask import Blueprint, request, jsonify
import logging

# Configuration du logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Création du blueprint pour les paramètres de voix
# Notez que nous ne définissons pas de préfixe d'URL ici
voice_settings_bp = Blueprint('voice_settings', __name__)

# Configuration de la base de données
DATABASE = 'dialogue.db'

def get_db_connection():
    """Connexion à la base de données SQLite."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_voice_settings_db():
    """Création des tables pour les préférences de voix si elles n'existent pas."""
    try:
        conn = get_db_connection()
        with conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS voice_settings (
                    id INTEGER PRIMARY KEY,
                    voice_a TEXT,
                    voice_b TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Vérifier s'il existe déjà des paramètres
            settings = conn.execute("SELECT COUNT(*) as count FROM voice_settings").fetchone()
            if settings['count'] == 0:
                # Insérer les valeurs par défaut
                conn.execute(
                    "INSERT INTO voice_settings (voice_a, voice_b) VALUES (?, ?)",
                    ('Lucia', 'Enrique')
                )
                conn.commit()
                logger.info("Valeurs par défaut des voix insérées")
                
        conn.close()
        logger.info("Table voice_settings initialisée")
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de la table voice_settings: {e}")

def get_default_voices():
    """Retourne les voix par défaut."""
    return {
        'voice_a': 'Lucia',
        'voice_b': 'Enrique'
    }

@voice_settings_bp.route('/api/voice-settings', methods=['GET'])
def get_voice_settings():
    """Récupère les paramètres de voix enregistrés."""
    try:
        conn = get_db_connection()
        settings = conn.execute("SELECT voice_a, voice_b FROM voice_settings ORDER BY id DESC LIMIT 1").fetchone()
        conn.close()
        
        if settings:
            return jsonify({
                'voice_a': settings['voice_a'],
                'voice_b': settings['voice_b']
            })
        else:
            # Retourner les valeurs par défaut si aucun paramètre n'est trouvé
            return jsonify(get_default_voices())
    
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des paramètres de voix: {e}")
        return jsonify(get_default_voices()), 500

@voice_settings_bp.route('/api/voice-settings', methods=['POST'])
def save_voice_settings():
    """Enregistre les paramètres de voix."""
    try:
        data = request.get_json()
        
        if not data or 'voice_a' not in data or 'voice_b' not in data:
            return jsonify({'error': 'Données incomplètes'}), 400
        
        voice_a = data['voice_a']
        voice_b = data['voice_b']
        
        conn = get_db_connection()
        
        # Vérifier si des paramètres existent déjà
        existing = conn.execute("SELECT id FROM voice_settings ORDER BY id DESC LIMIT 1").fetchone()
        
        if existing:
            # Mettre à jour les paramètres existants
            conn.execute(
                "UPDATE voice_settings SET voice_a = ?, voice_b = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (voice_a, voice_b, existing['id'])
            )
        else:
            # Insérer de nouveaux paramètres
            conn.execute(
                "INSERT INTO voice_settings (voice_a, voice_b) VALUES (?, ?)",
                (voice_a, voice_b)
            )
        
        conn.commit()
        conn.close()
        
        logger.info(f"Paramètres de voix enregistrés: A={voice_a}, B={voice_b}")
        return jsonify({'success': True, 'message': 'Paramètres enregistrés'})
    
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement des paramètres de voix: {e}")
        return jsonify({'error': str(e)}), 500

@voice_settings_bp.route('/api/voice-settings/default', methods=['GET'])
def get_default_voice_setting():
    """Récupère la voix par défaut pour la synthèse vocale."""
    try:
        conn = get_db_connection()
        settings = conn.execute("SELECT voice_a FROM voice_settings ORDER BY id DESC LIMIT 1").fetchone()
        conn.close()
        
        if settings:
            return jsonify({
                'voice': settings['voice_a']
            })
        else:
            # Retourner une valeur par défaut si aucun paramètre n'est trouvé
            return jsonify({'voice': 'Lucia'})
    
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la voix par défaut: {e}")
        return jsonify({'voice': 'Lucia'}), 500

@voice_settings_bp.record_once
def on_load(state):
    """Initialisation de la base de données lors du chargement du blueprint."""
    init_voice_settings_db()