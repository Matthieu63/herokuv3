import os
import json
from flask import Flask, render_template, redirect, url_for, request, session, render_template_string
from dotenv import load_dotenv

# Chargement des variables d’environnement
load_dotenv()

from espagnol.vocab import vocab_bp
from espagnol.dialogues import dialogues_bp
from espagnol.stories import stories_bp
from espagnol.voice_settings import voice_settings_bp
from espagnol.polly import polly_bp

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "changez_cette_valeur_en_prod")


# Enregistrement des blueprints
app.register_blueprint(vocab_bp, url_prefix="/espagnol")
app.register_blueprint(dialogues_bp, url_prefix="/espagnol/dialogues")
app.register_blueprint(stories_bp, url_prefix="/espagnol/stories")
app.register_blueprint(voice_settings_bp, url_prefix="/espagnol")
app.register_blueprint(polly_bp, url_prefix="/espagnol")

# Chemin vers le fichier des utilisateurs
USER_FILE = 'users.json'

# Charger les utilisateurs depuis le JSON
def load_users():
    with open(USER_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

# Sauvegarder les utilisateurs
def save_users(users):
    with open(USER_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

@app.route('/')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    users = load_users()
    user = users.get(session['user'])
    return render_template('index.html', user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()

        user = users.get(username)
        if user and user['password'] == password:
            session['user'] = username
            session['is_admin'] = user.get('is_admin', False)
            return redirect(url_for('home'))
        else:
            flash("Identifiants invalides", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    users = load_users()
    user = users.get(session['user'])
    return render_template('dashboard.html', user=user)

# L'admin pourra modifier les accès des utilisateurs
@app.route('/admin')
def admin():
    if not session.get('is_admin'):
        return redirect(url_for('dashboard'))

    users = load_users()
    return render_template('admin.html', users=users)

# Exemple de route pour une langue : ESPAGNOL
@app.route('/espagnol', methods=['GET', 'POST'])
def espagnol():
    if 'user' not in session:
        return redirect(url_for('login'))

    users = load_users()
    user = users.get(session['user'])

    if "espagnol" not in user['access']['languages']:
        return "Accès refusé", 403

    # Initialiser la clé 'data' s'il n'y en a pas encore (mais ne rien mettre par défaut)
    if 'data' not in user:
        user['data'] = {}
    if 'espagnol' not in user['data']:
        user['data']['espagnol'] = {}

    # Sauvegarde facultative si tu veux que l'arbo soit créée automatiquement
    users[session['user']] = user
    save_users(users)

    return render_template("espagnol.html", user=user)

if __name__ == '__main__':
    if not os.path.exists(USER_FILE):
        # Crée un utilisateur admin par défaut si le fichier n'existe pas
        default = {
            "admin": {
                "password": "admin123",
                "is_admin": True,
                "access": {
                    "languages": ["français", "espagnol"],
                    "modules": ["christ", "culture", "recettes"]
                }
            }
        }
        save_users(default)
    app.run(debug=True)
