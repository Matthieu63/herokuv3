# vocab.py
import csv
import sqlite3
import os
import re
import time
import requests
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash


# espagnol/vocab.py


vocab_bp = Blueprint('vocab_esp', __name__, template_folder="/espagnol/templates")




DATABASE = 'vocab_es.db'
default_tags = ["médecine"]

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def word_exists(word, conn=None):
    """Vérifie si un mot existe déjà (insensible à la casse)."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    result = conn.execute(
        "SELECT id FROM words WHERE lower(word) = ?", (word.lower(),)
    ).fetchone()

    if close_conn:
        conn.close()

    return result is not None



def format_response_text(text):
    paragraphs = text.split("\n\n")
    formatted_paragraphs = []
    for p in paragraphs:
        p = p.replace("\n", "<br>")
        if p.strip():
            formatted_paragraphs.append(f"<p>{p.strip()}</p>")
    return "\n".join(formatted_paragraphs)

def is_editor_empty(html):
    text = re.sub('<[^<]+?>', '', html)
    text = text.replace('&nbsp;', ' ').strip()
    return len(text) == 0

# (Le reste de tes fonctions et routes inchangé…)


def generate_synthese(word):
    prompt = (
        f"Est-ce que le mot '{word}' est fréquemment utilisé ? Si oui, explique pour quels usages, "
        "avec plusieurs phrases exemples en espagnol (sans traduction). "
        "Puis, à la fin, liste 'synonymes :' suivi des synonymes et 'antonymes :' suivi des antonymes."
    )
    api_key = os.environ.get("CLAUDE_API_KEY")
    headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    data = {
        "model": "claude-3-5-sonnet-20241022", 
        "max_tokens": 512, 
        "messages": [{"role": "user", "content": prompt}]
    }

    resp = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=data)
    if resp.status_code != 200:
        print(f"[ERROR] Claude API error: {resp.status_code}, {resp.text}")
        return f"<em>Erreur API Claude: {resp.status_code}</em>"
    
    result = resp.json()
    print("[DEBUG Claude] Response JSON:", result)
    
    # Extraction de la réponse selon le format de l'API Claude 3.5
    # La réponse devrait être dans content du dernier message
    if "content" in result:
        # Format direct
        raw = result.get("content", [])[0].get("text", "").strip()
    elif "messages" in result and len(result["messages"]) > 0:
        # Format avec messages
        last_message = result["messages"][-1]
        raw = last_message.get("content", [])[0].get("text", "").strip()
    else:
        # Anciens formats possibles
        raw = result.get("completion", "").strip()
        if not raw and "message" in result:
            raw = result["message"].get("content", "").strip()

    if not raw:
        return "<em>Pas de synthèse générée par Claude.</em>"

    return format_response_text(raw)

def generate_image(word):
    prompt = f"Crée moi une image qui illustre le mieux pour toi le mot {word} selon les usages courants."
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise Exception("Clé API OpenAI manquante.")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    data = {
        "model": "dall-e-3",
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024"
    }
    response = requests.post("https://api.openai.com/v1/images/generations", headers=headers, json=data)
    if response.status_code == 200:
        result = response.json()
        if "data" in result and isinstance(result["data"], list) and len(result["data"]) > 0:
            return result["data"][0].get("url", "")
        else:
            return ""
    else:
        return ""

def init_vocab_db():
    conn = get_db_connection()
    with conn:
        # Créer la table words si elle n'existe pas déjà
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
        
        # Créer la table tags si elle n'existe pas déjà
        conn.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE
            )
        ''')
        
        # Vérifier si la table tags est vide
        tag_count = conn.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
        print(f"[DEBUG] Nombre de tags dans la base de données: {tag_count}")
        
        if tag_count == 0:
            print("[DEBUG] Ajout des tags par défaut...")
            # Ajouter les tags par défaut
            default_tags = ["médecine", "nourriture", "voyage", "famille", "maison", "commerce", "éducation"]
            for tag in default_tags:
                try:
                    conn.execute("INSERT INTO tags (name) VALUES (?)", (tag,))
                    print(f"[DEBUG] Tag ajouté: {tag}")
                except sqlite3.IntegrityError:
                    print(f"[DEBUG] Le tag '{tag}' existe déjà")
            conn.commit()
            
        # Vérifier si la table words est vide
        count = conn.execute("SELECT COUNT(*) FROM words").fetchone()[0]
        print(f"[DEBUG] Nombre de mots dans la base de données: {count}")
        
        if count == 0:
            print("[DEBUG] Ajout du mot par défaut 'Hola'...")
            default_word = "Hola"
            default_synthese = generate_synthese(default_word)
            default_image = generate_image(default_word)
            conn.execute(
                "INSERT INTO words (word, synthese, youglish, note, tags, image, exemples) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (default_word, default_synthese, "https://youglish.com/pronounce/hola/spanish", 0, "salutation, espagnol", default_image, "")
            )
            conn.commit()
            print("[DEBUG] Mot par défaut ajouté avec succès")
    
    # Vérification finale
    conn = get_db_connection()
    tag_count = conn.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
    word_count = conn.execute("SELECT COUNT(*) FROM words").fetchone()[0]
    print(f"[DEBUG] Vérification après initialisation: {tag_count} tags et {word_count} mots")
    if tag_count > 0:
        tags = [row['name'] for row in conn.execute("SELECT name FROM tags").fetchall()]
        print(f"[DEBUG] Tags dans la base: {tags}")
    conn.close()

@vocab_bp.record_once
def on_load(state):
    # Cette fonction est appelée une seule fois lorsque le blueprint est enregistré dans l'application
    init_vocab_db()

# Modification de la fonction index pour récupérer tous les tags correctement
@vocab_bp.route("/")
def index():
    tag_filter = request.args.get('tag', '').strip()
    rating_filter = request.args.get('rating', '').strip()
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1
    try:
        limit = int(request.args.get('limit', 10))
    except ValueError:
        limit = 10
    offset = (page - 1) * limit

    conn = get_db_connection()
    
    # Construction de la requête pour les mots filtrés
    query = "SELECT * FROM words"
    params = []
    conditions = []
    if tag_filter:
        conditions.append("lower(tags) LIKE ?")
        params.append('%' + tag_filter.lower() + '%')
    if rating_filter:
        conditions.append("note = ?")
        params.append(rating_filter)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    # Compter le total pour la pagination
    total_count = conn.execute("SELECT COUNT(*) FROM (" + query + ")", params).fetchone()[0]
    
    # Requête principale avec limite et offset pour pagination
    query += " ORDER BY lower(word) LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    words = conn.execute(query, params).fetchall()

    # CORRECTION: Récupération directe et explicite des tags de la table tags
    all_tags = []
    try:
        # Récupérer tous les tags de la table tags
        print("[DEBUG] Récupération des tags depuis la table tags...")
        rows = conn.execute("SELECT name FROM tags ORDER BY name").fetchall()
        for row in rows:
            tag_name = row['name']
            all_tags.append(tag_name)
            print(f"[DEBUG] Tag trouvé: '{tag_name}'")
        
        # Si aucun tag n'est trouvé, afficher un avertissement
        if not all_tags:
            print("[DEBUG] ATTENTION: Aucun tag trouvé dans la table tags")
    except Exception as e:
        print(f"[DEBUG] ERREUR lors de la récupération des tags: {e}")
    
    # Récupérer également les tags des mots (pour être sûr)
    tags_from_words = set()
    try:
        words_with_tags = conn.execute("SELECT DISTINCT tags FROM words WHERE tags IS NOT NULL AND tags != ''").fetchall()
        for word in words_with_tags:
            if word['tags']:
                tags = [t.strip() for t in word['tags'].split(',') if t.strip()]
                tags_from_words.update(tags)
        
        print(f"[DEBUG] Tags extraits des mots: {tags_from_words}")
        
        # Ajouter les tags des mots qui ne sont pas déjà dans all_tags
        for tag in tags_from_words:
            if tag not in all_tags:
                all_tags.append(tag)
                print(f"[DEBUG] Ajout du tag '{tag}' depuis les mots")
    except Exception as e:
        print(f"[DEBUG] ERREUR lors de l'extraction des tags des mots: {e}")
    
    # Trier les tags par ordre alphabétique
    all_tags.sort()
    
    # Afficher un résumé des tags pour le débogage
    print(f"[DEBUG] Liste finale des tags (total: {len(all_tags)}): {all_tags}")
    
    # Récupérer les tags disponibles pour le formulaire d'ajout de mot
    available_tags = all_tags.copy()
    
    conn.close()

    import math
    total_pages = math.ceil(total_count / limit)
    
    # Rendu du template avec tous les paramètres nécessaires
    return render_template(
        "espagnol/index.html",
        words=words,
        tag_filter=tag_filter,
        rating_filter=rating_filter,
        all_tags=all_tags,  # Liste des tags pour les filtres
        available_tags=available_tags,  # Liste des tags pour le formulaire d'ajout
        page=page,
        limit=limit,
        total_count=total_count,
        total_pages=total_pages
    )

@vocab_bp.route("/check_duplicate", methods=["POST"])
def check_duplicate():
    """Vérifie si un mot existe déjà dans la base de données."""
    data = request.get_json()
    word = data.get("word", "").strip().lower()
    
    if not word:
        return jsonify({"status": "error", "message": "Mot manquant"}), 400
    
    conn = get_db_connection()
    existing = conn.execute("SELECT id, word, synthese, tags, image FROM words WHERE lower(word) = ?", (word,)).fetchone()
    conn.close()
    
    if existing:
        # Convertir l'objet Row SQLite en dictionnaire
        existing_dict = dict(existing)
        return jsonify({
            "status": "duplicate",
            "word": existing_dict
        })
    else:
        return jsonify({"status": "ok"})

@vocab_bp.route("/check_duplicates_bulk", methods=["POST"])
def check_duplicates_bulk():
    """Vérifie en masse si des mots existent déjà dans la base de données."""
    data = request.get_json()
    words = data.get("words", [])
    
    if not words:
        return jsonify({"status": "error", "message": "Aucun mot fourni"}), 400
    
    conn = get_db_connection()
    result = {
        "new_words": [],
        "duplicates": []
    }
    
    for word in words:
        word = word.strip()
        if not word:
            continue
            
        existing = conn.execute("SELECT id, word, synthese, tags, image FROM words WHERE lower(word) = ?", (word.lower(),)).fetchone()
        
        if existing:
            # Convertir l'objet Row SQLite en dictionnaire
            existing_dict = dict(existing)
            result["duplicates"].append({
                "word": word,
                "existing": existing_dict
            })
        else:
            result["new_words"].append(word)
    
    conn.close()
    return jsonify(result)

# Correction de la fonction add_word dans vocab.py

# Modification de la fonction add_word pour inclure une redirection côté serveur

@vocab_bp.route("/add", methods=["POST"])
def add_word():
    # Vérifier si la requête est en JSON ou en form-data
    if request.content_type and 'application/json' in request.content_type:
        # Traitement pour les requêtes JSON
        data = request.get_json() or {}
        word = data.get("word", "").strip()
        synthese = data.get("synthese", "").strip()
        youglish = data.get("youglish", "")
        tags = data.get("tags", "")
        image = data.get("image", "").strip()
        disable_auto_synthese = data.get("disable_auto_synthese", False)
    else:
        # Traitement pour les requêtes form-data
        word = request.form.get("word", "").strip()
        synthese = request.form.get("synthese", "").strip()
        youglish = request.form.get("youglish", "")
        tags = request.form.get("tags", "")
        disable_auto_synthese = request.form.get("disable_auto_synthese") in ["true", "True", "1", True, "on"]
        
        # Traitement du fichier image
        if 'image' in request.files and request.files['image'].filename:
            image_file = request.files['image']
            import base64
            from io import BytesIO
            # Convertir l'image en base64 pour stockage en BDD
            image_data = BytesIO(image_file.read())
            encoded_image = base64.b64encode(image_data.getvalue()).decode('utf-8')
            mime_type = image_file.content_type
            image = f"data:{mime_type};base64,{encoded_image}"
        else:
            image = ""
    
    if not word:
        return jsonify({"status": "error", "message": "Aucun mot fourni"}), 400

    # Générer la synthèse si nécessaire
    if not synthese and not disable_auto_synthese:
        try:
            synthese = generate_synthese(word)
            print(f"[DEBUG] Synthèse générée : {synthese[:100]}...")
        except Exception as e:
            print(f"[DEBUG] generate_synthese error: {e}")
            synthese = f"<em>Erreur lors de la génération de la synthèse: {e}</em>"
    
    # Générer l'image si nécessaire
    if not image:
        try:
            image = generate_image(word)
            print(f"[DEBUG] Image générée : {image[:50]}...")
        except Exception as e:
            print(f"[DEBUG] generate_image error: {e}")
            image = ""

    # Si youglish n'est pas fourni, générer l'URL
    if not youglish:
        youglish = f"https://youglish.com/pronounce/{word}/spanish"

    print(f"[DEBUG] Inserting → word={word}, synthese={synthese[:50]}..., image={image[:50]}...")
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO words (word, synthese, youglish, note, tags, image, exemples) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (word, synthese, youglish, 0, tags, image, "")
        )
        conn.commit()
        
        # Récupérer le format de la requête (AJAX ou normale)
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if is_ajax:
            # Si c'est une requête AJAX, retourner un JSON
            return jsonify({"status": "success", "synthese": synthese, "image": image})
        else:
            # Si c'est une requête normale, rediriger vers la page d'index
            flash(f"Le mot '{word}' a été ajouté avec succès!", "success")
            return redirect(url_for('vocab_esp.index'))
            
    except Exception as e:
        print(f"[DEBUG] DB insert error: {e}")
        conn.close()
        return jsonify({"status": "error", "message": str(e)}), 500
    
    conn.close()
    return jsonify({"status": "success", "synthese": synthese, "image": image})

# Correction de la fonction bulk_add pour gérer correctement les ajouts en masse
@vocab_bp.route("/bulk_add", methods=["GET", "POST"])
def bulk_add():
    conn = get_db_connection()
    tags_in_db = conn.execute("SELECT name FROM tags").fetchall()
    available_tags = [tag["name"] for tag in tags_in_db]
    
    if request.method == "POST":
        text = request.form.get("words_text", "")
        selected_tags = request.form.getlist("tags_bulk")
        tags_str = ", ".join(selected_tags)
        disable_auto_synthese = request.form.get("disable_auto_synthese") == "on"
        disable_auto_image = request.form.get("disable_auto_image") == "on"
        skip_duplicates = request.form.get("skip_duplicates") == "on"
        
        words = [w.strip() for w in text.splitlines() if w.strip()]
        count = 0
        duplicates = 0
        
        for word in words:
            # Vérifier si le mot existe déjà
            existing = conn.execute("SELECT id FROM words WHERE lower(word) = ?", (word.lower(),)).fetchone()
            if existing:
                duplicates += 1
                if skip_duplicates:
                    continue  # Sauter ce mot s'il existe déjà
            
            youglish_url = f"https://youglish.com/pronounce/{word}/spanish"
            
            # Générer la synthèse si non désactivée
            if not disable_auto_synthese:
                try:
                    synthese = generate_synthese(word)
                except Exception as e:
                    print(f"[DEBUG] generate_synthese error for {word}: {e}")
                    synthese = f"<em>Erreur lors de la génération de la synthèse: {e}</em>"
            else:
                synthese = ""
                
            # Générer l'image si non désactivée
            if not disable_auto_image:
                try:
                    image_url = generate_image(word)
                except Exception as e:
                    print(f"[DEBUG] generate_image error for {word}: {e}")
                    image_url = ""
            else:
                image_url = ""
                
            conn.execute(
                "INSERT INTO words (word, synthese, youglish, note, tags, image, exemples) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (word, synthese, youglish_url, 0, tags_str, image_url, "")
            )
            count += 1
            
        conn.commit()
        conn.close()
        
        if duplicates > 0:
            message = f"{count} mots ajoutés avec succès."
            if skip_duplicates:
                message += f" {duplicates} doublons ignorés."
            else:
                message += f" Note: {duplicates} mots étaient déjà présents dans la base."
            flash(message, "success")
        else:
            flash(f"{count} mots ajoutés avec succès.", "success")
            
        return redirect(url_for("vocab_esp.index"))  # Correction: vocab_esp au lieu de vocab
    else:
        conn.close()
        return render_template("espagnol/bulk_add.html", available_tags=available_tags)


@vocab_bp.route("/update_word", methods=["POST"])
def update_word():
    data = request.get_json()
    word_id = data.get("id")
    field = data.get("field")
    value = data.get("value")
    if field not in ['word', 'synthese', 'youglish', 'tags', 'image']:
        return jsonify({"status": "error", "message": "Champ non autorisé"}), 400
    conn = get_db_connection()
    with conn:
        conn.execute(f"UPDATE words SET {field} = ? WHERE id = ?", (value, word_id))
    conn.close()
    return jsonify({"status": "success"})

@vocab_bp.route("/update_note", methods=["POST"])
def update_note():
    data = request.get_json()
    word_id = data.get("id")
    note = data.get("note")
    conn = get_db_connection()
    with conn:
        conn.execute("UPDATE words SET note = ? WHERE id = ?", (note, word_id))
    conn.close()
    return jsonify({"status": "success"})

@vocab_bp.route("/delete", methods=["POST"])
def delete_word():
    data = request.get_json()
    word_id = data.get("id")
    if not word_id:
        return jsonify({"status": "error", "message": "ID manquant"}), 400
    conn = get_db_connection()
    with conn:
        conn.execute("DELETE FROM words WHERE id = ?", (word_id,))
    conn.close()
    return jsonify({"status": "success"})

@vocab_bp.route("/flashcard")
def flashcard():
    tag_filter = request.args.get('tag', '').strip()
    rating_filter = request.args.get('rating', '').strip()
    try:
        index = int(request.args.get('index', 0))
    except ValueError:
        index = 0

    conn = get_db_connection()
    query = "SELECT * FROM words"
    params = []
    conditions = []
    if tag_filter:
        conditions.append("lower(tags) LIKE ?")
        params.append('%' + tag_filter.lower() + '%')
    if rating_filter:
        conditions.append("note = ?")
        params.append(rating_filter)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    words = conn.execute(query, params).fetchall()
    conn.close()

    total = len(words)
    if total == 0:
        word = None
        end = False
    else:
        if index >= total:
            word = None
            end = True
        else:
            word = words[index]
            end = False

    return render_template("espagnol/flash_card.html",
                           word=word,
                           index=index,
                           total=total,
                           tag_filter=tag_filter,
                           rating_filter=rating_filter,
                           end=end)

# Modification de la fonction manage_tags dans vocab.py
@vocab_bp.route("/admin/tags", methods=["GET", "POST"])
def manage_tags():
    """Gestion des tags avec débogage amélioré pour garantir l'insertion en BDD"""
    
    conn = get_db_connection()
    
    if request.method == "POST":
        # Ajout d'un nouveau tag
        if "new_tag" in request.form:
            new_tag = request.form.get("new_tag", "").strip()
            print(f"[DEBUG] Tentative d'ajout du tag: '{new_tag}'")
            
            if new_tag:
                try:
                    # Vérifier si le tag existe déjà (case insensitive)
                    existing = conn.execute("SELECT name FROM tags WHERE lower(name) = lower(?)", (new_tag,)).fetchone()
                    
                    if existing:
                        print(f"[DEBUG] Le tag '{new_tag}' existe déjà sous la forme '{existing['name']}'")
                        flash(f"Le tag '{new_tag}' existe déjà.", "warning")
                    else:
                        # Ajout du tag avec commit explicite
                        print(f"[DEBUG] Insertion du tag '{new_tag}' dans la base de données")
                        conn.execute("INSERT INTO tags (name) VALUES (?)", (new_tag,))
                        conn.commit()
                        
                        # Vérification que le tag a bien été ajouté
                        verification = conn.execute("SELECT name FROM tags WHERE name = ?", (new_tag,)).fetchone()
                        if verification:
                            print(f"[DEBUG] Le tag '{new_tag}' a été ajouté avec succès!")
                            flash(f"Le tag '{new_tag}' a été ajouté avec succès!", "success")
                        else:
                            print(f"[DEBUG] ERREUR: Le tag '{new_tag}' n'a pas été inséré correctement!")
                            flash(f"Erreur lors de l'ajout du tag '{new_tag}'.", "danger")
                
                except sqlite3.IntegrityError as e:
                    print(f"[DEBUG] Erreur d'intégrité SQLite: {e}")
                    flash(f"Erreur: {e}", "danger")
                except Exception as e:
                    print(f"[DEBUG] Exception non prévue: {e}")
                    flash(f"Erreur inattendue: {e}", "danger")
        
        # Suppression d'un tag
        elif "delete_tag" in request.form:
            delete_tag = request.form.get("delete_tag", "").strip()
            print(f"[DEBUG] Tentative de suppression du tag: '{delete_tag}'")
            
            if delete_tag:
                try:
                    # Supprimer le tag
                    conn.execute("DELETE FROM tags WHERE name = ?", (delete_tag,))
                    
                    # Mettre à jour les mots qui utilisent ce tag
                    rows = conn.execute("SELECT id, tags FROM words WHERE tags LIKE ?", 
                                       ('%' + delete_tag + '%',)).fetchall()
                    
                    for row in rows:
                        tags_list = [t.strip() for t in row['tags'].split(',') if t.strip()]
                        new_tags = [t for t in tags_list if t.lower() != delete_tag.lower()]
                        updated_tags = ', '.join(new_tags)
                        
                        print(f"[DEBUG] Mise à jour des tags pour le mot ID {row['id']}: '{row['tags']}' -> '{updated_tags}'")
                        conn.execute("UPDATE words SET tags = ? WHERE id = ?", (updated_tags, row['id']))
                    
                    conn.commit()
                    flash(f"Le tag '{delete_tag}' a été supprimé avec succès!", "success")
                
                except Exception as e:
                    print(f"[DEBUG] Erreur lors de la suppression du tag: {e}")
                    flash(f"Erreur lors de la suppression: {e}", "danger")
    
    # Récupération des tags avec leur nombre d'utilisations
    tags_data = []
    
    try:
        tags_raw = conn.execute("SELECT name FROM tags ORDER BY name").fetchall()
        print(f"[DEBUG] Nombre de tags trouvés: {len(tags_raw)}")
        
        for tag in tags_raw:
            # Compter les occurrences de ce tag dans les mots
            count = conn.execute(
                "SELECT COUNT(*) FROM words WHERE tags LIKE ?", 
                ('%' + tag['name'] + '%',)
            ).fetchone()[0]
            
            print(f"[DEBUG] Tag '{tag['name']}' utilisé {count} fois")
            
            tags_data.append({
                "name": tag['name'],
                "count": count
            })
    
    except Exception as e:
        print(f"[DEBUG] Erreur lors de la récupération des tags: {e}")
        flash(f"Erreur lors du chargement des tags: {e}", "danger")
    
    # Fermeture de la connexion
    conn.close()
    
    return render_template("espagnol/manage_tags.html", tags=tags_data)

    
@vocab_bp.route('/word/<int:id>')
def word_detail(id):
    conn = get_db_connection()
    ids = [row['id'] for row in conn.execute("SELECT id FROM words ORDER BY lower(word)").fetchall()]
    conn.close()
    idx = ids.index(id)
    prev_id = ids[idx-1] if idx > 0 else None
    next_id = ids[idx+1] if idx < len(ids)-1 else None
    word = get_db_connection().execute("SELECT * FROM words WHERE id=?", (id,)).fetchone()
    return render_template('espagnol/word_detail.html', word=word, prev_id=prev_id, next_id=next_id)

@vocab_bp.route("/debug/check_tags")
def debug_check_tags():
    """
    Route de diagnostic pour vérifier l'état des tags dans la base de données
    et forcer l'ajout de tags par défaut si nécessaire.
    """
    result = {
        "status": "success",
        "messages": [],
        "tags_in_db": [],
        "tags_in_words": []
    }
    
    conn = get_db_connection()
    
    # 1. Vérifier la table tags
    try:
        tag_count = conn.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
        result["messages"].append(f"Nombre de tags dans la table tags: {tag_count}")
        
        if tag_count > 0:
            tags_in_db = [row['name'] for row in conn.execute("SELECT name FROM tags ORDER BY name").fetchall()]
            result["tags_in_db"] = tags_in_db
            result["messages"].append(f"Tags trouvés: {', '.join(tags_in_db)}")
        else:
            result["messages"].append("AUCUN TAG trouvé dans la table tags!")
            
            # Ajouter des tags par défaut
            default_tags = ["médecine", "nourriture", "voyage", "famille", "maison", "commerce", "éducation"]
            for tag in default_tags:
                try:
                    conn.execute("INSERT INTO tags (name) VALUES (?)", (tag,))
                    result["messages"].append(f"Tag par défaut ajouté: {tag}")
                except sqlite3.IntegrityError:
                    result["messages"].append(f"Erreur: Le tag '{tag}' existe déjà")
            conn.commit()
            
            # Vérifier à nouveau après l'ajout
            tags_in_db = [row['name'] for row in conn.execute("SELECT name FROM tags ORDER BY name").fetchall()]
            result["tags_in_db"] = tags_in_db
            result["messages"].append(f"Tags après correction: {', '.join(tags_in_db)}")
    
    except Exception as e:
        result["status"] = "error"
        result["messages"].append(f"ERREUR lors de la vérification des tags: {str(e)}")
    
    # 2. Vérifier les tags utilisés dans les mots
    try:
        tags_from_words = set()
        words_with_tags = conn.execute("SELECT id, word, tags FROM words WHERE tags IS NOT NULL AND tags != ''").fetchall()
        
        for word in words_with_tags:
            if word['tags']:
                tags = [t.strip() for t in word['tags'].split(',') if t.strip()]
                result["messages"].append(f"Mot '{word['word']}' (ID: {word['id']}) a les tags: {', '.join(tags)}")
                tags_from_words.update(tags)
        
        result["tags_in_words"] = list(tags_from_words)
        result["messages"].append(f"Tags extraits des mots: {', '.join(tags_from_words)}")
        
        # Vérifier si tous les tags des mots existent dans la table tags
        missing_tags = [tag for tag in tags_from_words if tag not in result["tags_in_db"]]
        if missing_tags:
            result["messages"].append(f"Tags manquants dans la table tags: {', '.join(missing_tags)}")
            
            # Ajouter les tags manquants
            for tag in missing_tags:
                try:
                    conn.execute("INSERT INTO tags (name) VALUES (?)", (tag,))
                    result["messages"].append(f"Tag manquant ajouté: {tag}")
                except sqlite3.IntegrityError:
                    result["messages"].append(f"Erreur: Impossible d'ajouter le tag '{tag}'")
            conn.commit()
    
    except Exception as e:
        result["status"] = "error"
        result["messages"].append(f"ERREUR lors de la vérification des tags des mots: {str(e)}")
    
    conn.close()
    
    # Retourner les résultats sous forme de page HTML
    html_result = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Diagnostic des Tags</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; }}
            h1 {{ color: #3f51b5; }}
            .success {{ color: green; }}
            .error {{ color: red; }}
            .info {{ color: blue; }}
            pre {{ background: #f5f5f5; padding: 10px; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <h1>Diagnostic des Tags</h1>
        <p class="{result['status']}">Statut: {result['status'].upper()}</p>
        
        <h2>Messages de diagnostic:</h2>
        <ul>
        {"".join([f"<li>{msg}</li>" for msg in result['messages']])}
        </ul>
        
        <h2>Tags dans la base de données:</h2>
        <pre>{", ".join(result['tags_in_db']) if result['tags_in_db'] else "Aucun"}</pre>
        
        <h2>Tags utilisés dans les mots:</h2>
        <pre>{", ".join(result['tags_in_words']) if result['tags_in_words'] else "Aucun"}</pre>
        
        <p><a href="/espagnol/">Retour à la page d'accueil</a></p>
        <p><a href="/espagnol/admin/tags">Aller à la gestion des tags</a></p>
    </body>
    </html>
    """
    
    return html_result