import hmac
import os
import secrets
import sqlite3
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DATABASE = Path(os.environ.get("TASKS_DATABASE", BASE_DIR / "tasks.db"))


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        DATABASE=str(DATABASE),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE") == "1",
        MAX_CONTENT_LENGTH=1024 * 1024,
    )
    if test_config:
        app.config.update(test_config)

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
        return g.db

    @app.teardown_appcontext
    def close_db(_error=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def init_db():
        database_path = Path(app.config["DATABASE"])
        database_path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(database_path)
        try:
            db.execute("PRAGMA foreign_keys = ON")
            with db:
                db.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                        password_hash TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        title TEXT NOT NULL,
                        description TEXT NOT NULL DEFAULT '',
                        completed INTEGER NOT NULL DEFAULT 0 CHECK (completed IN (0, 1)),
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                )
        finally:
            db.close()

    init_db()

    @app.before_request
    def csrf_protection():
        if request.method == "POST":
            submitted_token = request.form.get("csrf_token", "")
            session_token = session.get("csrf_token", "")
            if not session_token or not hmac.compare_digest(submitted_token, session_token):
                abort(400, description="El formulario expiró. Recarga la página e inténtalo de nuevo.")

    @app.context_processor
    def inject_csrf_token():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(32)
        return {"csrf_token": session["csrf_token"]}

    def login_required(view):
        @wraps(view)
        def wrapped_view(**kwargs):
            if g.get("user") is None:
                return redirect(url_for("login"))
            return view(**kwargs)

        return wrapped_view

    @app.before_request
    def load_logged_in_user():
        user_id = session.get("user_id")
        g.user = (
            get_db().execute("SELECT id, username FROM users WHERE id = ?", (user_id,)).fetchone()
            if user_id is not None
            else None
        )

    @app.route("/")
    def index():
        if g.user is None:
            return redirect(url_for("login"))
        return redirect(url_for("tasks"))

    @app.route("/register", methods=("GET", "POST"))
    def register():
        if g.user is not None:
            return redirect(url_for("tasks"))
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            error = None
            if not username or len(username) < 3 or len(username) > 30:
                error = "El usuario debe tener entre 3 y 30 caracteres."
            elif not all(character.isalnum() or character in "._-" for character in username):
                error = "El usuario solo puede contener letras, números, punto, guion y guion bajo."
            elif len(password) < 8:
                error = "La contraseña debe tener al menos 8 caracteres."

            if error is None:
                try:
                    cursor = get_db().execute(
                        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                        (username, generate_password_hash(password)),
                    )
                    get_db().commit()
                except sqlite3.IntegrityError:
                    error = "Ese nombre de usuario ya está registrado."
                else:
                    session.clear()
                    session["user_id"] = cursor.lastrowid
                    return redirect(url_for("tasks"))
            flash(error, "error")
        return render_template("auth.html", mode="register")

    @app.route("/login", methods=("GET", "POST"))
    def login():
        if g.user is not None:
            return redirect(url_for("tasks"))
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user = get_db().execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()
            if user is None or not check_password_hash(user["password_hash"], password):
                flash("Usuario o contraseña incorrectos.", "error")
            else:
                session.clear()
                session["user_id"] = user["id"]
                return redirect(url_for("tasks"))
        return render_template("auth.html", mode="login")

    @app.post("/logout")
    @login_required
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/tasks", methods=("GET", "POST"))
    @login_required
    def tasks():
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            if not title:
                flash("Escribe un título para la tarea.", "error")
            elif len(title) > 120:
                flash("El título no puede superar los 120 caracteres.", "error")
            elif len(description) > 2000:
                flash("La descripción no puede superar los 2000 caracteres.", "error")
            else:
                get_db().execute(
                    "INSERT INTO tasks (user_id, title, description) VALUES (?, ?, ?)",
                    (g.user["id"], title, description),
                )
                get_db().commit()
                flash("Tarea creada.", "success")
                return redirect(url_for("tasks"))

        user_tasks = get_db().execute(
            "SELECT id, title, description, completed, created_at FROM tasks "
            "WHERE user_id = ? ORDER BY completed ASC, id DESC",
            (g.user["id"],),
        ).fetchall()
        return render_template("tasks.html", tasks=user_tasks)

    @app.route("/tasks/<int:task_id>/edit", methods=("GET", "POST"))
    @login_required
    def edit_task(task_id):
        task = get_db().execute(
            "SELECT id, title, description FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, g.user["id"]),
        ).fetchone()
        if task is None:
            abort(404)

        if request.method == "POST":
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            if not title:
                flash("Escribe un título para la tarea.", "error")
            elif len(title) > 120:
                flash("El título no puede superar los 120 caracteres.", "error")
            elif len(description) > 2000:
                flash("La descripción no puede superar los 2000 caracteres.", "error")
            else:
                get_db().execute(
                    "UPDATE tasks SET title = ?, description = ? WHERE id = ? AND user_id = ?",
                    (title, description, task_id, g.user["id"]),
                )
                get_db().commit()
                flash("Tarea actualizada.", "success")
                return redirect(url_for("tasks"))
        return render_template("edit_task.html", task=task)

    @app.post("/tasks/<int:task_id>/toggle")
    @login_required
    def toggle_task(task_id):
        cursor = get_db().execute(
            "UPDATE tasks SET completed = CASE completed WHEN 0 THEN 1 ELSE 0 END "
            "WHERE id = ? AND user_id = ?",
            (task_id, g.user["id"]),
        )
        get_db().commit()
        if cursor.rowcount == 0:
            abort(404)
        return redirect(url_for("tasks"))

    @app.post("/tasks/<int:task_id>/delete")
    @login_required
    def delete_task(task_id):
        cursor = get_db().execute(
            "DELETE FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, g.user["id"]),
        )
        get_db().commit()
        if cursor.rowcount == 0:
            abort(404)
        flash("Tarea eliminada.", "success")
        return redirect(url_for("tasks"))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
