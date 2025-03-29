import os
from flask import Blueprint, request, send_file, jsonify
import boto3
import io
import logging

# Configuration du logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

polly_bp = Blueprint('polly', __name__)

# Définir directement les identifiants (à partir des informations que vous avez fournies)
import boto3

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")  # Valeur par défaut

# Initialisation sécurisée
try:
    polly_client = boto3.client(
        "polly",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )

    masked_secret = AWS_SECRET_ACCESS_KEY[:4] + "****" + AWS_SECRET_ACCESS_KEY[-4:] if AWS_SECRET_ACCESS_KEY else "None"
    logger.info(f"Using AWS Access Key ID: {AWS_ACCESS_KEY_ID}")
    logger.info(f"Secret Key (masked): {masked_secret}")
    logger.info(f"Region: {AWS_REGION}")
    logger.info("AWS Polly client initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize AWS Polly client: {e}")
    polly_client = None




# Afficher les informations de connexion (en masquant partiellement la clé secrète)
masked_secret = AWS_SECRET_ACCESS_KEY[:4] + "****" + AWS_SECRET_ACCESS_KEY[-4:] if AWS_SECRET_ACCESS_KEY else "None"
logger.info(f"Using AWS Access Key ID: {AWS_ACCESS_KEY_ID}")
logger.info(f"Secret Key (masked): {masked_secret}")
logger.info(f"Region: {AWS_REGION}")

# Configurer le client AWS Polly
try:
    polly_client = boto3.client(
        'polly',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )
    logger.info("AWS Polly client initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize AWS Polly client: {e}")
    polly_client = None

# Voix disponibles par langue
AVAILABLE_VOICES = {
    'es-ES': ['Lucia', 'Enrique', 'Conchita', 'Sergio'],
    'fr-FR': ['Léa', 'Mathieu', 'Céline'],
    'en-US': ['Joanna', 'Matthew', 'Salli', 'Joey'],
    'pt-BR': ['Camila', 'Ricardo', 'Vitória']
}

# Configuration des moteurs par voix
VOICE_ENGINE_MAP = {
    "Lucia": "neural",     # Lucia fonctionne mieux avec neural
    "Enrique": "standard", # Enrique avec standard
    "Sergio": "neural",    # Sergio nécessite neural
    "Conchita": "standard", # Conchita avec standard
    "Léa": "neural",
    "Mathieu": "standard",
    "Céline": "standard",
    "Joanna": "neural",
    "Matthew": "neural",
    "Salli": "neural",
    "Joey": "standard",
    "Camila": "neural",
    "Ricardo": "standard",
    "Vitória": "standard"
}

@polly_bp.route('/api/polly', methods=['POST'])
def synthesize_speech():
    """API endpoint pour convertir du texte en parole avec Amazon Polly."""
    if polly_client is None:
        return jsonify({'error': 'AWS Polly client not initialized'}), 500
    
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'Missing text parameter'}), 400
        
        text = data['text']
        if not text.strip():
            return jsonify({'error': 'Empty text parameter'}), 400
        
        # Paramètres configurables
        voice_id = data.get('voice', 'Lucia')  # Lucia pour l'espagnol
        language_code = data.get('language', 'es-ES')
        
        logger.info(f"Synthesizing speech for text: {text[:50]}... with voice: {voice_id}")
        
        # Obtenir le moteur approprié pour cette voix
        engine = VOICE_ENGINE_MAP.get(voice_id, "standard")  # Standard par défaut
        
        logger.info(f"Utilisation du moteur '{engine}' pour la voix '{voice_id}'")
        
        # Essayer avec le moteur spécifique pour cette voix
        try:
            response = polly_client.synthesize_speech(
                Text=text,
                OutputFormat='mp3',
                VoiceId=voice_id,
                LanguageCode=language_code,
                Engine=engine
            )
        except Exception as e:
            logger.error(f"Error with {engine} engine: {e}")
            # Si cela échoue, essayer avec l'autre moteur
            try:
                fallback_engine = "neural" if engine == "standard" else "standard"
                logger.info(f"Tentative avec moteur de secours '{fallback_engine}'")
                response = polly_client.synthesize_speech(
                    Text=text,
                    OutputFormat='mp3',
                    VoiceId=voice_id,
                    LanguageCode=language_code,
                    Engine=fallback_engine
                )
            except Exception as nested_e:
                logger.error(f"Error with fallback engine: {nested_e}")
                raise
        
        audio_stream = response['AudioStream'].read()
        audio_file = io.BytesIO(audio_stream)
        audio_file.seek(0)
        
        return send_file(audio_file, mimetype='audio/mpeg')
    
    except Exception as e:
        logger.error(f"Error in speech synthesis: {e}")
        return jsonify({'error': str(e)}), 500

# Endpoint pour récupérer la liste des voix disponibles
@polly_bp.route('/api/polly/voices', methods=['GET'])
def get_voices():
    """Récupère la liste des voix disponibles pour une langue donnée."""
    if polly_client is None:
        return jsonify({'error': 'AWS Polly client not initialized'}), 500
    
    try:
        language = request.args.get('language', 'es-ES')
        
        # Si la langue est dans notre dictionnaire prédéfini, utiliser ces voix
        if language in AVAILABLE_VOICES:
            voices = [
                {'id': voice_id, 'name': voice_id, 'gender': 'Female' if voice_id in ['Lucia', 'Conchita', 'Léa', 'Céline', 'Joanna', 'Salli', 'Camila', 'Vitória'] else 'Male'}
                for voice_id in AVAILABLE_VOICES[language]
            ]
            return jsonify(voices)
        
        # Sinon, essayer de récupérer les voix depuis l'API AWS
        try:
            response = polly_client.describe_voices(LanguageCode=language)
            
            voices = [
                {'id': voice['Id'], 'name': voice['Name'], 'gender': voice['Gender']}
                for voice in response['Voices']
            ]
            
            if not voices:  # Si aucune voix n'est trouvée, utiliser les valeurs par défaut pour l'espagnol
                voices = [
                    {'id': 'Lucia', 'name': 'Lucia', 'gender': 'Female'},
                    {'id': 'Enrique', 'name': 'Enrique', 'gender': 'Male'},
                    {'id': 'Conchita', 'name': 'Conchita', 'gender': 'Female'},
                    {'id': 'Sergio', 'name': 'Sergio', 'gender': 'Male'}
                ]
                logger.warning(f"No voices found for language {language}, using defaults")
        except Exception as e:
            logger.error(f"Error calling describe_voices: {e}")
            voices = [
                {'id': 'Lucia', 'name': 'Lucia', 'gender': 'Female'},
                {'id': 'Enrique', 'name': 'Enrique', 'gender': 'Male'},
                {'id': 'Conchita', 'name': 'Conchita', 'gender': 'Female'},
                {'id': 'Sergio', 'name': 'Sergio', 'gender': 'Male'}
            ]
            
        return jsonify(voices)
    
    except Exception as e:
        logger.error(f"Error in get_voices endpoint: {e}")
        return jsonify({'error': str(e)}), 500

@polly_bp.route('/api/polly/speak', methods=['POST'])
def speak_text():
    """API endpoint pour convertir un texte en parole avec Amazon Polly (format simplifié)."""
    if polly_client is None:
        return jsonify({'error': 'AWS Polly client not initialized'}), 500
    
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'Missing text parameter'}), 400
        
        text = data['text']
        if not text.strip():
            return jsonify({'error': 'Empty text parameter'}), 400
        
        # Paramètres configurables avec valeurs par défaut
        voice_id = data.get('voice', 'Lucia')  # Voix par défaut pour l'espagnol
        language_code = data.get('language', 'es-ES')
        
        logger.info(f"Synthesizing speech for text: {text[:50]}... with voice: {voice_id}")
        
        # Obtenir le moteur approprié pour cette voix
        engine = VOICE_ENGINE_MAP.get(voice_id, "standard")
        
        # Essayer avec le moteur spécifique pour cette voix
        try:
            response = polly_client.synthesize_speech(
                Text=text,
                OutputFormat='mp3',
                VoiceId=voice_id,
                LanguageCode=language_code,
                Engine=engine
            )
        except Exception as e:
            logger.error(f"Error with {engine} engine: {e}")
            # Si cela échoue, essayer avec l'autre moteur
            try:
                fallback_engine = "neural" if engine == "standard" else "standard"
                logger.info(f"Tentative avec moteur de secours '{fallback_engine}'")
                response = polly_client.synthesize_speech(
                    Text=text,
                    OutputFormat='mp3',
                    VoiceId=voice_id,
                    LanguageCode=language_code,
                    Engine=fallback_engine
                )
            except Exception as nested_e:
                logger.error(f"Error with fallback engine: {nested_e}")
                raise
        
        audio_stream = response['AudioStream'].read()
        audio_file = io.BytesIO(audio_stream)
        audio_file.seek(0)
        
        return send_file(audio_file, mimetype='audio/mpeg')
    
    except Exception as e:
        logger.error(f"Error in speech synthesis: {e}")
        return jsonify({'error': str(e)}), 500