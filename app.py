
import os
import sqlite3
import uuid

from functools import wraps
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)
from flask_wtf.csrf import CSRFProtect, CSRFError
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv


# =========================================
# CONFIGURATION GÉNÉRALE
# =========================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(BASE_DIR, ".env"))

app = Flask(__name__)

SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY manquante dans les variables d'environnement.")

app.config["SECRET_KEY"] = SECRET_KEY

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "Manou papillon")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

if not ADMIN_PASSWORD:
    raise RuntimeError("ADMIN_PASSWORD manquante dans les variables d'environnement.")


# =========================================
# SESSIONS ET SÉCURITÉ
# =========================================

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

app.config["SESSION_COOKIE_SECURE"] = (
    os.getenv("COOKIE_SECURE", "False").lower() == "true"
)

app.config["PERMANENT_SESSION_LIFETIME"] = 3600

# Protection CSRF : jetons conservés et vérifiés
app.config["WTF_CSRF_ENABLED"] = True
app.config["WTF_CSRF_SSL_STRICT"] = False
app.config["WTF_CSRF_TIME_LIMIT"] = 7200

app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

# Render utilise un proxy HTTPS
app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_proto=1,
    x_host=1
)

csrf = CSRFProtect(app)


# =========================================
# FICHIERS ET BASE DE DONNÉES
# =========================================

DATABASE = os.path.join(BASE_DIR, "tic_ops.db")

UPLOAD_FOLDER = os.path.join(
    BASE_DIR,
    "static",
    "uploads"
)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


# =========================================
# CONNEXION SQLITE
# =========================================

def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                price INTEGER NOT NULL,
                sizes TEXT,
                colors TEXT,
                image TEXT NOT NULL
            )
        """)


init_db()


# =========================================
# PROTECTION ADMINISTRATEUR
# =========================================

def admin_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if not session.get("admin"):
            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return wrapper


# =========================================
# VÉRIFICATION DES IMAGES
# =========================================

def allowed_file(filename):

    if not filename or "." not in filename:
        return False

    extension = filename.rsplit(".", 1)[1].lower()

    return extension in ALLOWED_EXTENSIONS


# =========================================
# ÉVITER LES PAGES DE CONNEXION EN CACHE
# =========================================

@app.after_request
def prevent_login_cache(response):

    if request.endpoint == "login":
        response.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate, max-age=0"
        )
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

    return response


# =========================================
# GESTION DES ERREURS CSRF
# =========================================

@app.errorhandler(CSRFError)
def handle_csrf_error(error):

    flash(
        "Session de sécurité expirée. "
        "Recharge la page et essaie de te reconnecter."
    )

    return redirect(url_for("login")), 303


# =========================================
# PAGE D'ACCUEIL
# =========================================

@app.route("/")
def index():

    with get_db() as db:
        products = db.execute(
            "SELECT * FROM products ORDER BY id DESC"
        ).fetchall()

    return render_template(
        "index.html",
        products=products
    )


# =========================================
# CONNEXION ADMINISTRATEUR
# =========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if session.get("admin"):
        return redirect(url_for("admin"))

    if request.method == "POST":

        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if (
            username == ADMIN_USERNAME
            and password == ADMIN_PASSWORD
        ):

            session.clear()
            session.permanent = True
            session["admin"] = True

            return redirect(url_for("admin"))

        flash("Identifiants incorrects.")

    return render_template("login.html")


# =========================================
# DÉCONNEXION
# =========================================

@app.route("/logout", methods=["POST"])
@admin_required
def logout():

    session.clear()

    return redirect(url_for("index"))


# =========================================
# TABLEAU DE BORD ADMIN
# =========================================

@app.route("/admin")
@admin_required
def admin():

    with get_db() as db:
        products = db.execute(
            "SELECT * FROM products ORDER BY id DESC"
        ).fetchall()

    return render_template(
        "admin.html",
        products=products
    )


# =========================================
# PUBLIER UN VÊTEMENT
# =========================================

@app.route("/admin/add", methods=["POST"])
@admin_required
def add_product():

    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    sizes = request.form.get("sizes", "").strip()
    colors = request.form.get("colors", "").strip()

    try:
        price = int(request.form.get("price", ""))

    except (ValueError, TypeError):
        flash("Le prix doit être valide.")
        return redirect(url_for("admin"))

    photo = request.files.get("image")

    if not name or price <= 0:
        flash("Vérifie le nom et le prix.")
        return redirect(url_for("admin"))

    if not photo or not photo.filename:
        flash("Ajoute une photo du vêtement.")
        return redirect(url_for("admin"))

    if not allowed_file(photo.filename):
        flash("Format accepté : JPG, JPEG, PNG ou WEBP.")
        return redirect(url_for("admin"))

    safe_name = secure_filename(photo.filename)

    if not safe_name or "." not in safe_name:
        flash("Nom de photo invalide.")
        return redirect(url_for("admin"))

    extension = safe_name.rsplit(".", 1)[1].lower()

    filename = f"{uuid.uuid4().hex}.{extension}"

    image_path = os.path.join(
        UPLOAD_FOLDER,
        filename
    )

    photo.save(image_path)

    try:

        with get_db() as db:
            db.execute("""
                INSERT INTO products
                (name, description, price, sizes, colors, image)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                name,
                description,
                price,
                sizes,
                colors,
                filename
            ))

    except Exception:

        if os.path.isfile(image_path):
            os.remove(image_path)

        raise

    flash("Vêtement publié avec succès !")

    return redirect(url_for("admin"))


# =========================================
# SUPPRIMER UN VÊTEMENT
# =========================================

@app.route("/admin/delete/<int:product_id>", methods=["POST"])
@admin_required
def delete_product(product_id):

    image_filename = None

    with get_db() as db:

        product = db.execute(
            "SELECT image FROM products WHERE id = ?",
            (product_id,)
        ).fetchone()

        if product:

            image_filename = os.path.basename(
                product["image"]
            )

            db.execute(
                "DELETE FROM products WHERE id = ?",
                (product_id,)
            )

    if image_filename:

        image_path = os.path.join(
            UPLOAD_FOLDER,
            image_filename
        )

        if os.path.isfile(image_path):
            os.remove(image_path)

        flash("Vêtement supprimé.")

    else:
        flash("Vêtement introuvable.")

    return redirect(url_for("admin"))


# =========================================
# ERREUR : FICHIER TROP VOLUMINEUX
# =========================================

@app.errorhandler(413)
def file_too_large(error):

    return "Photo trop volumineuse. Maximum : 5 Mo.", 413


# =========================================
# DÉMARRAGE LOCAL
# =========================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
