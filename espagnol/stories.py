from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from espagnol.db import get_db_connection, VOCAB_DB
import sqlite3, datetime
import random
import os
import re
import requests


# Création du blueprint pour les histoires
# On utilise le même modèle que pour vocab_bp
stories_bp = Blueprint('stories_esp', __name__, template_folder="/espagnol/templates", url_prefix='/espagnol/stories')

# Configuration de la base de données
# On utilise le même chemin que celui de vocab_es.db pour assurer la cohérence
from espagnol.db import VOCAB_DB
# On récupère le répertoire parent du fichier vocab_es.db
VOCAB_DIR = os.path.dirname(VOCAB_DB)
STORIES_DB = os.path.join(VOCAB_DIR, "stories_es.db")

def get_stories_db_connection():
    """Connexion à la base de données des histoires."""
    conn = sqlite3.connect(STORIES_DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_stories_db():
    """Crée les tables pour les histoires."""
    conn = get_stories_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            rating INTEGER,
            tags TEXT,
            theme TEXT,
            creation_date DATETIME,
            words_used TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dialogues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id INTEGER,
            dialogue_number INTEGER,
            personne_a TEXT,
            personne_b TEXT,
            FOREIGN KEY(story_id) REFERENCES stories(id)
        )
    ''')
    conn.commit()
    conn.close()

# ─────────── Hook pour initialiser la base ───────────
@stories_bp.record_once
def on_load(state):
    """Initialisation de la base de données lors du chargement du blueprint."""
    init_stories_db()

def get_filtered_words(tags=None, rating=None):
    """Récupère les mots filtrés par tags et/ou rating."""
    conn = get_db_connection(VOCAB_DB)
    cursor = conn.cursor()
    query = "SELECT * FROM words"
    params = []
    conditions = []
    
    if tags:
        for tag in tags:
            conditions.append("lower(tags) LIKE ?")
            params.append('%' + tag.lower() + '%')
    
    if rating:
        conditions.append("note = ?")
        params.append(rating)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    words = cursor.execute(query, params).fetchall()
    conn.close()
    return words

def get_words_usage_history(limit=10):
    """Récupère l'historique d'utilisation des mots dans les histoires."""
    conn = get_stories_db_connection()
    cursor = conn.cursor()
    
    recent_stories = cursor.execute(
        "SELECT words_used FROM stories ORDER BY creation_date DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    
    word_usage = {}
    for story in recent_stories:
        if story['words_used']:
            words = story['words_used'].split(',')
            for word in words:
                word = word.strip()
                if word:
                    word_usage[word] = word_usage.get(word, 0) + 1
    
    return word_usage

def get_rotation_candidates():
    """Identifie les mots qui ont été utilisés dans 3 histoires consécutives ou plus."""
    conn = get_stories_db_connection()
    cursor = conn.cursor()
    
    recent_stories = cursor.execute(
        "SELECT words_used FROM stories ORDER BY creation_date DESC LIMIT 5"
    ).fetchall()
    conn.close()
    
    if len(recent_stories) < 3:
        return []
    
    story_words = []
    for story in recent_stories:
        if story['words_used']:
            words = [w.strip() for w in story['words_used'].split(',')]
            story_words.append(words)
    
    rotation_candidates = []
    for word in story_words[0]:
        consecutive_count = 1
        for i in range(1, min(3, len(story_words))):
            if word in story_words[i]:
                consecutive_count += 1
            else:
                break
        
        if consecutive_count >= 3:
            rotation_candidates.append(word)
    
    return rotation_candidates

def clean_dialogue_text(text):
    """Nettoie et formate le texte d'un dialogue sans le tronquer."""
    text = text.strip(' "\'')
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\n+', '\n', text)
    if text.endswith('...') or text.endswith('…'):
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) > 1:
            last_sentence = sentences[-1]
            if last_sentence.endswith('...') or last_sentence.endswith('…'):
                text = ' '.join(sentences[:-1]) + '.'
    return text

def generate_story(words, theme):
    """Génère une histoire avec 2 dialogues en utilisant les mots sélectionnés et le thème."""
    # Au lieu de prendre systématiquement les 75 premiers mots, on en sélectionne un échantillon aléatoire
    if len(words) > 75:
        selected_words = random.sample(words, 75)
    else:
        selected_words = words

    # On extrait la liste des mots
    words_list = [word['word'] for word in selected_words]
    
    # Récupérer l'historique d'utilisation des mots
    word_usage = get_words_usage_history(10)
    
    # Trier les mots pour privilégier ceux peu utilisés
    prioritized_words = sorted(words_list, key=lambda w: word_usage.get(w, 0))
    
    # On divise en trois groupes pour favoriser la diversité
    never_used = [w for w in prioritized_words if w not in word_usage]
    rarely_used = [w for w in prioritized_words if w in word_usage and word_usage[w] < 2]
    other_words = [w for w in prioritized_words if w not in never_used and w not in rarely_used]
    
    random.shuffle(never_used)
    random.shuffle(rarely_used)
    random.shuffle(other_words)
    
    # On combine en donnant la priorité aux mots jamais ou rarement utilisés
    final_words = never_used + rarely_used + other_words
    rotation_candidates = get_rotation_candidates()
    if rotation_candidates:
        final_words = [w for w in final_words if w not in rotation_candidates] + rotation_candidates[-10:]
    
    final_words = final_words[:75]  # On limite à 75 mots maximum
    # On divise la liste pour les 2 dialogues
    words_group1 = final_words[:len(final_words)//2]
    words_group2 = final_words[len(final_words)//2:]
    
    group1_text = ", ".join(words_group1)
    group2_text = ", ".join(words_group2)

    
    prompt = (
        f"Por favor, crea exactamente 2 diálogos narrativos, naturales y coherentes en español, que simulen una conversación real entre dos personas.\n\n"
        f"INSTRUCCIONES IMPORTANTES:\n"
        f"1. Utiliza exclusivamente las etiquetas 'Personne A:' y 'Personne B:' (no uses nombres propios).\n"
        f"2. Cada intervención debe consistir en 4 a 5 frases completas, descriptivas y naturales, sin limitarse a un número fijo de palabras por frase.\n"
        f"3. Cada frase debe terminar con un punto u otro signo de puntuación apropiado.\n"
        f"4. No escribas frases incompletas ni uses 'etc.' o '...'.\n"
        f"5. Incorpora de forma coherente el tema y las siguientes palabras clave obligatorias, pero utiliza también otras palabras que enriquezcan la narrativa y permitan transiciones lógicas entre las ideas.\n"
        f"6. Si las palabras clave son verbos, conjúgalos correctamente según el contexto, y ajusta el género de los sustantivos o adjetivos para que la conversación sea natural.\n"
        f"7. El diálogo debe parecer una conversación real: incluye preguntas, respuestas, comentarios espontáneos, interjecciones y transiciones naturales.\n"
        f"8. El tema es: {theme}\n"
        f"9. No te sientas obligado a utilizar un número máximo de palabras; utiliza la cantidad de palabras que consideres necesaria para que la narrativa sea fluida y auténtica.\n"
        f"10. Ten en cuenta que la lista de palabras se actualiza constantemente; utiliza palabras nuevas cuando estén disponibles y evita repetir siempre los mismos términos.\n\n"
        
        f"Para el PRIMER diálogo, integra obligatoriamente las siguientes palabras clave: {group1_text}\n"
        f"Para el SEGUNDO diálogo, integra obligatoriamente las siguientes palabras clave: {group2_text}\n\n"
        
        f"Asegúrate de que cada diálogo tenga una narrativa coherente y parezca una conversación real, con turnos de habla naturales y respuestas que se relacionen entre sí.\n\n"
        
        f"FORMATO EXACTO A SEGUIR:\n\n"
        
        f"Dialogue 1:\n"
        f"Personne A: [Frase 1. Frase 2. Frase 3. Frase 4.]\n"
        f"Personne B: [Frase 1. Frase 2. Frase 3. Frase 4.]\n"
        f"FIN DIALOGUE 1\n\n"
        
        f"Dialogue 2:\n"
        f"Personne A: [Frase 1. Frase 2. Frase 3. Frase 4.]\n"
        f"Personne B: [Frase 1. Frase 2. Frase 3. Frase 4.]\n"
        f"FIN DIALOGUE 2\n\n"
        
        f"EJEMPLO CONCRETO (no usar estas frases exactas):\n\n"
        
        f"Dialogue 1:\n"
        f"Personne A: Hola, ¿cómo estás hoy? El médico es muy afable y fortachón. Trabaja con amor en el cerro y ayuda a desahogar el dolor ajeno. ¿Qué opinas de su dedicación?\n"
        f"Personne B: Pues, la azafata trae los frascos de medicina y se nota la pasión en su trabajo. La amistad trasciende las riñas cotidianas. Realmente debemos divulgar estas buenas acciones humanitarias. ¿No crees que es inspirador?\n"
        f"FIN DIALOGUE 1\n\n"
        
        f"Dialogue 2:\n"
        f"Personne A: Buenas tardes, ¿cómo te ha ido en el trabajo hoy? Noté que el ambiente en el hospital estuvo muy animado. Me pregunto si la nueva directriz ha ayudado a mejorar el servicio.\n"
        f"Personne B: Hola, sí, la verdad es que ha sido un día interesante. Hubo momentos de tensión, pero también muchos gestos de solidaridad. ¿Tú qué opinas de la manera en que se manejaron las urgencias?\n"
        f"Personne A: Creo que, a pesar de los desafíos, se evidenció un verdadero compromiso por parte de todos. Me gustó ver cómo, incluso en situaciones complicadas, se generaba un ambiente de apoyo mutuo.\n"
        f"Personne B: Exacto, y eso marca una gran diferencia. Además, la forma en que se aplicó el protocolo mostró mejoras claras. ¿No crees que estos cambios podrían motivar a más personal a dar lo mejor de sí?\n"
        f"FIN DIALOGUE 2\n\n"
        
        f"Asegúrate de que ambos diálogos estén completos, sean coherentes, parezcan una conversación real y no se corten."
    )

    try:
        api_key = os.environ.get("CLAUDE_API_KEY")
        if not api_key:
            raise Exception("Clé API Claude manquante.")
        
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        data = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 2000,
            "temperature": 0.7,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        print(f"Envoi d'une requête à Claude avec {len(prompt)} caractères")
        response = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=data)
        
        if response.status_code == 200:
            result = response.json()
            if "content" in result and isinstance(result["content"], list):
                story_text = result["content"][0]["text"]
                print(f"Réponse reçue: {len(story_text)} caractères")
                return story_text, final_words
            else:
                return "Erreur dans la réponse de l'API: format inattendu.", []
        else:
            return f"Erreur API: {response.status_code} - {response.text}", []
    
    except Exception as e:
        return f"Erreur: {str(e)}", []

def extract_dialogues_from_response(response_text, num_dialogues=2):
    """Extrait les dialogues de la réponse en utilisant les marqueurs FIN DIALOGUE."""
    dialogues = []
    for i in range(1, num_dialogues + 1):
        pattern = rf"Dialogue\s+{i}:\s*(.*?)\s*FIN DIALOGUE {i}"
        match = re.search(pattern, response_text, re.DOTALL | re.IGNORECASE)
        if match:
            dialogue_text = match.group(1).strip()
            # Extraction des parties Personne A et Personne B
            parts = re.split(r'Personne\s+A:\s*', dialogue_text, flags=re.IGNORECASE)
            if len(parts) < 2:
                dialogues.append({
                    "personne_a": "Dialogue incompleto para Personne A.",
                    "personne_b": "Dialogue incompleto para Personne B."
                })
                continue
            remaining = parts[1]
            parts_b = re.split(r'Personne\s+B:\s*', remaining, flags=re.IGNORECASE)
            if len(parts_b) < 2:
                dialogues.append({
                    "personne_a": remaining.strip(),
                    "personne_b": "Dialogue incompleto para Personne B."
                })
                continue
            personne_a_text = parts_b[0].strip()
            personne_b_text = parts_b[1].strip()
            dialogues.append({
                "personne_a": personne_a_text,
                "personne_b": personne_b_text
            })
        else:
            dialogues.append({
                "personne_a": "Lo siento, hubo un problema al generar este diálogo.",
                "personne_b": "Por favor, inténtalo de nuevo."
            })
    print(f"Dialogues extraits: {len(dialogues)}")
    return dialogues[:num_dialogues]

# ─────────── Routes ───────────
@stories_bp.route("/")
def index():
    """Affiche la liste des histoires créées."""
    conn = get_stories_db_connection()
    cursor = conn.cursor()
    stories = cursor.execute("SELECT * FROM stories ORDER BY creation_date DESC").fetchall()
    conn.close()
    return render_template("espagnol/stories_index.html", stories=stories)

@stories_bp.route("/create", methods=["GET", "POST"])
def create():
    """Affiche le formulaire de création d'histoire et traite sa soumission."""
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        theme = request.form.get("theme", "").strip()
        selected_tags = request.form.getlist("tags")
        rating = request.form.get("rating")
        
        if not title:
            flash("Veuillez donner un titre à votre histoire.")
            return redirect(url_for("stories_esp.create"))
        
        filtered_words = get_filtered_words(tags=selected_tags, rating=rating)
        
        if not filtered_words:
            flash("Aucun mot ne correspond aux critères sélectionnés.")
            return redirect(url_for("stories_esp.create"))
        
        story_text, words_used = generate_story(filtered_words, theme)
        
        if not story_text.startswith("Erreur"):
            dialogues_list = extract_dialogues_from_response(story_text, 2)
            conn = get_stories_db_connection()
            cursor = conn.cursor()
            creation_date = datetime.datetime.now().isoformat()
            tags_str = ", ".join(selected_tags) if selected_tags else ""
            words_used_str = ", ".join(words_used)
            
            cursor.execute(
                "INSERT INTO stories (title, rating, tags, theme, creation_date, words_used) VALUES (?, ?, ?, ?, ?, ?)",
                (title, rating, tags_str, theme, creation_date, words_used_str)
            )
            story_id = cursor.lastrowid
            
            for i, dialogue in enumerate(dialogues_list, start=1):
                cursor.execute(
                    "INSERT INTO dialogues (story_id, dialogue_number, personne_a, personne_b) VALUES (?, ?, ?, ?)",
                    (story_id, i, dialogue["personne_a"], dialogue["personne_b"])
                )
            
            conn.commit()
            conn.close()
            
            flash(f"Histoire '{title}' créée avec succès !")
            return redirect(url_for("stories_esp.view", story_id=story_id))
        else:
            flash(story_text)
            return redirect(url_for("stories_esp.create"))
    
    conn = get_db_connection(VOCAB_DB)
    tags_from_words = set()
    for w in conn.execute("SELECT tags FROM words").fetchall():
        if w["tags"]:
            for t in w["tags"].split(','):
                cleaned = t.strip()
                if cleaned:
                    tags_from_words.add(cleaned)
    tags_in_db = conn.execute("SELECT name FROM tags").fetchall()
    tags_db_set = {tag["name"] for tag in tags_in_db}
    available_tags = sorted(tags_from_words.union(tags_db_set))
    conn.close()
    
    return render_template("espagnol/stories_create.html", available_tags=available_tags)

@stories_bp.route("/view/<int:story_id>")
def view(story_id):
    """Affiche les dialogues d'une histoire."""
    conn = get_stories_db_connection()
    cursor = conn.cursor()
    story = cursor.execute("SELECT * FROM stories WHERE id = ?", (story_id,)).fetchone()
    
    if not story:
        flash("Histoire non trouvée.")
        return redirect(url_for("stories_esp.index"))
    
    dialogues = cursor.execute(
        "SELECT * FROM dialogues WHERE story_id = ? ORDER BY dialogue_number",
        (story_id,)
    ).fetchall()
    conn.close()
    
    return render_template("espagnol/stories_view.html", story=story, dialogues=dialogues)

@stories_bp.route("/delete/<int:story_id>", methods=["POST"])
def delete(story_id):
    """Supprime une histoire et ses dialogues."""
    conn = get_stories_db_connection()
    cursor = conn.cursor()
    
    story = cursor.execute("SELECT * FROM stories WHERE id = ?", (story_id,)).fetchone()
    if not story:
        conn.close()
        return jsonify({"status": "error", "message": "Histoire non trouvée."}), 404
    
    cursor.execute("DELETE FROM dialogues WHERE story_id = ?", (story_id,))
    cursor.execute("DELETE FROM stories WHERE id = ?", (story_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({"status": "success"})