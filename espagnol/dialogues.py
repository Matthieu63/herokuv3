import os
import re
import sqlite3
import datetime
import requests
from flask import Blueprint, request, render_template, redirect, url_for, flash, send_from_directory

# Création du blueprint pour les dialogues
dialogues_bp = Blueprint('dialogues', __name__, url_prefix='/dialogues')

# Configuration de la base de données et des fichiers
DATABASE = 'dialogue_es.db'
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
ALLOWED_EXTENSIONS = {'pdf'}

# Vérifier et créer le dossier de stockage des fichiers PDF
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def get_db_connection():
    """Connexion à la base de données SQLite."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_dialogues_db():
    """Création des tables si elles n'existent pas."""
    conn = get_db_connection()
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

def parse_dialogues(response_text):
    """Extrait et structure les dialogues à partir du texte de réponse de Claude (en espagnol ou français)."""
    # Ajoutons des logs pour voir ce que contient la réponse
    print(f"Texte de réponse reçu : {response_text[:200]}...")  # Afficher les 200 premiers caractères
    
    dialogues = []
    
    # Essayons d'identifier chaque dialogue individuellement
    # Ceci est plus souple et permet de s'adapter à différents formats
    dialogue_blocks = re.split(r"(?:Diálogo|Dialogue)\s*\d+\s*:", response_text)
    
    # Le premier élément est généralement vide ou contient du texte d'introduction
    if dialogue_blocks and len(dialogue_blocks) > 1:
        dialogue_blocks = dialogue_blocks[1:]  # Ignorer le premier élément
    
    for block in dialogue_blocks:
        # Rechercher la personne A et la personne B dans chaque bloc
        persona_a_match = re.search(r"(?:Persona|Personne)\s*A\s*:\s*(.*?)(?=(?:Persona|Personne)\s*B\s*:|$)", block, re.DOTALL)
        persona_b_match = re.search(r"(?:Persona|Personne)\s*B\s*:\s*(.*?)$", block, re.DOTALL)
        
        if persona_a_match and persona_b_match:
            dialogues.append({
                "personne_a": persona_a_match.group(1).strip(),
                "personne_b": persona_b_match.group(1).strip()
            })
    
    # Si aucun dialogue n'est trouvé, essayons un pattern plus simple
    if not dialogues:
        print("Aucun dialogue trouvé avec le premier pattern, essai d'un pattern alternatif...")
        
        # Rechercher simplement des paires de questions/réponses
        qa_pairs = re.findall(r"(?:Persona|Personne)\s*A\s*:\s*(.*?)(?:Persona|Personne)\s*B\s*:\s*(.*?)(?=(?:Persona|Personne)\s*A\s*:|$)", 
                              response_text, re.DOTALL)
        
        for qa_pair in qa_pairs:
            dialogues.append({
                "personne_a": qa_pair[0].strip(),
                "personne_b": qa_pair[1].strip()
            })
    
    # Afficher le nombre de dialogues trouvés
    print(f"Nombre de dialogues extraits : {len(dialogues)}")
    
    return dialogues

def extract_youtube_transcript(youtube_url):
    """
    Extrait la transcription d'une vidéo YouTube.
    
    Parameters:
    youtube_url (str): URL de la vidéo YouTube
    
    Returns:
    str: Transcription de la vidéo
    """
    try:
        # Extraire l'ID de la vidéo YouTube de l'URL
        import re
        from urllib.parse import urlparse, parse_qs
        
        # Gestion des formats d'URL YouTube courants
        if 'youtu.be' in youtube_url:
            video_id = youtube_url.split('/')[-1].split('?')[0]
        else:
            parsed_url = urlparse(youtube_url)
            if parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
                if parsed_url.path == '/watch':
                    video_id = parse_qs(parsed_url.query)['v'][0]
                elif parsed_url.path.startswith('/embed/'):
                    video_id = parsed_url.path.split('/')[2]
                elif parsed_url.path.startswith('/v/'):
                    video_id = parsed_url.path.split('/')[2]
            else:
                raise ValueError("Format d'URL YouTube non reconnu")
        
        # Utiliser youtube_transcript_api pour obtenir la transcription
        from youtube_transcript_api import YouTubeTranscriptApi
        
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['es'])
        
        # Fusionner tous les segments de transcription
        transcript_text = ' '.join([item['text'] for item in transcript_list])
        
        return transcript_text
        
    except ImportError:
        raise Exception("Le module youtube_transcript_api est requis. Installez-le avec 'pip install youtube-transcript-api'")
    except Exception as e:
        print(f"Erreur lors de l'extraction de la transcription YouTube: {e}")
        return None
    
@dialogues_bp.route("/youtube", methods=["GET", "POST"])
def youtube_dialogues():
    """Permet de générer des dialogues à partir d'une vidéo YouTube."""
    if request.method == "POST":
        youtube_url = request.form.get("youtube_url", "").strip()
        
        if not youtube_url:
            flash("Veuillez entrer une URL YouTube valide.")
            return redirect(url_for("dialogues.youtube_dialogues"))
        
        # Extraction de la transcription
        transcript = extract_youtube_transcript(youtube_url)
        
        if not transcript:
            flash("Impossible d'extraire la transcription de cette vidéo YouTube.")
            return redirect(url_for("dialogues.youtube_dialogues"))
        
        # Génération des dialogues à partir de la transcription
        api_response = generate_dialogues(transcript)
        
        if not api_response:
            flash("La génération des dialogues a échoué.")
            return redirect(url_for("dialogues.youtube_dialogues"))
        
        dialogues_list = parse_dialogues(api_response)
        
        if not dialogues_list:
            flash("Aucun dialogue n'a pu être extrait de la réponse.")
            return redirect(url_for("dialogues.youtube_dialogues"))
        
        # Enregistrement des dialogues dans la base de données
        conn = get_db_connection()
        cur = conn.cursor()
        upload_date = datetime.datetime.now().isoformat()
        
        # Utiliser l'URL YouTube comme nom de fichier
        filename = f"YouTube - {youtube_url[:50]}..."
        
        cur.execute("INSERT INTO dialogues_files (filename, upload_date) VALUES (?, ?)", (filename, upload_date))
        file_id = cur.lastrowid
        
        for i, dialogue in enumerate(dialogues_list, start=1):
            cur.execute(
                "INSERT INTO dialogues (file_id, dialogue_number, personne_a, personne_b) VALUES (?, ?, ?, ?)",
                (file_id, i, dialogue["personne_a"], dialogue["personne_b"])
            )
        
        conn.commit()
        conn.close()
        
        flash(f"Dialogues générés pour la vidéo YouTube.")
        return redirect(url_for("dialogues.dialogues_view", file_id=file_id))
    
    return render_template("espagnol/youtube_dialogues.html")

@dialogues_bp.record_once
def on_load(state):
    """Initialisation de la base de données lors du chargement du blueprint."""
    init_dialogues_db()

def allowed_file(filename):
    """Vérifie si le fichier a une extension autorisée."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(pdf_path):
    """Extrait le texte d'un fichier PDF."""
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        raise Exception("PyPDF2 est requis. Installe-le avec 'pip install PyPDF2'.")
    
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text.strip()


def generate_dialogues(pdf_text):
    """
    Génère des dialogues immersifs à partir d'un texte de podcast en utilisant Claude.
    
    Parameters:
    pdf_text (str): Le texte extrait du PDF
    
    Returns:
    str: Dialogues générés
    """
    prompt = (
        "En te basant uniquement sur le texte suivant (une transcription d'un podcast en espagnol), "
        "génère 8 dialogues immersifs en espagnol. Chaque dialogue doit être structuré en deux lignes : "
        "la première correspond à une question posée par la personne A, et la seconde est une réponse détaillée "
        "de la personne B sous forme d'un paragraphe de 5 lignes. "
        "Les dialogues doivent refléter une conversation naturelle et immersive, où la personne B "
        "parle à la première personne et partage ses expériences, réflexions et connaissances.\n\n"
        f"Texte du podcast :\n{pdf_text}\n\n"
        "Merci de fournir uniquement les 8 dialogues au format suivant :\n"
        "Dialogue 1:\n"
        "Personne A: [Question courte]\n"
        "Personne B: [Réponse détaillée en 5 lignes]\n"
        "Dialogue 2:\n"
        "Personne A: [Question courte]\n"
        "Personne B: [Réponse détaillée en 5 lignes]\n"
        "..."
    )

    try:
        # Utiliser l'API Claude
        api_key = os.getenv("CLAUDE_API_KEY")
        if not api_key:
            raise ValueError("Clé API Claude manquante.")
            
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        # Format correct pour l'API Claude
        data = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 2000,
            "system": "Tu es un assistant expert en rédaction de dialogues immersifs.",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        response = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=data)
        
        if response.status_code == 200:
            result = response.json()
            return result["content"][0]["text"]
        else:
            raise ValueError(f"Erreur Claude API: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"Erreur lors de la génération des dialogues: {e}")
        return None

@dialogues_bp.route("/", methods=["GET", "POST"])
def dialogues_index():
    """Affiche la liste des fichiers PDF traités et permet l'upload."""
    if request.method == "POST":
        if "pdf_file" not in request.files:
            flash("Aucun fichier envoyé.")
            return redirect(url_for("dialogues.dialogues_index"))

        file = request.files["pdf_file"]
        if file.filename == "" or not allowed_file(file.filename):
            flash("Fichier invalide. Seuls les fichiers PDF sont autorisés.")
            return redirect(url_for("dialogues.dialogues_index"))
        
        filename = file.filename
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        pdf_text = extract_text_from_pdf(filepath)
        
        # Générer les dialogues avec Claude
        api_response = generate_dialogues(pdf_text)

        if not api_response:
            flash("La génération des dialogues a échoué.")
            return redirect(url_for("dialogues.dialogues_index"))

        dialogues_list = parse_dialogues(api_response)
        conn = get_db_connection()
        cur = conn.cursor()
        upload_date = datetime.datetime.now().isoformat()

        cur.execute("INSERT INTO dialogues_files (filename, upload_date) VALUES (?, ?)", (filename, upload_date))
        file_id = cur.lastrowid

        for i, dialogue in enumerate(dialogues_list, start=1):
            cur.execute(
                "INSERT INTO dialogues (file_id, dialogue_number, personne_a, personne_b) VALUES (?, ?, ?, ?)",
                (file_id, i, dialogue["personne_a"], dialogue["personne_b"])
            )
        
        conn.commit()
        conn.close()
        
        flash(f"Dialogues générés pour le fichier {filename} en utilisant Claude.")
        return redirect(url_for("dialogues.dialogues_view", file_id=file_id))

    conn = get_db_connection()
    files = conn.execute("SELECT * FROM dialogues_files ORDER BY upload_date DESC").fetchall()
    conn.close()
    return render_template("espagnol/dialogues_index.html", files=files)

@dialogues_bp.route("/view/<int:file_id>")
def dialogues_view(file_id):
    """Affiche les dialogues générés pour un fichier donné."""
    conn = get_db_connection()
    file_record = conn.execute("SELECT * FROM dialogues_files WHERE id = ?", (file_id,)).fetchone()
    dialogues_data = conn.execute("SELECT * FROM dialogues WHERE file_id = ? ORDER BY dialogue_number", (file_id,)).fetchall()
    conn.close()

    if not file_record:
        flash("Fichier non trouvé.")
        return redirect(url_for("dialogues.dialogues_index"))

    return render_template("espagnol/dialogues_view.html", file=file_record, dialogues=dialogues_data)