import secrets
import sqlite3
import tempfile
from pathlib import Path

from app import create_app


def test_password_muy_larga_no_registra_usuario():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        database = str(Path(temp_dir) / "test.db")
        app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret",
                "DATABASE": database,
            }
        )
        client = app.test_client()

        client.get("/register")
        with client.session_transaction() as session:
            csrf_token = session["csrf_token"]

        with sqlite3.connect(database) as connection:
            users_before = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]

        username = f"prueba_{secrets.randbelow(1_000_000):06d}"
        password = "a" * 1000
        client.post(
            "/register",
            data={
                "csrf_token": csrf_token,
                "username": username,
                "password": password,
            },
            follow_redirects=True,
        )

        with sqlite3.connect(database) as connection:
            users_after = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]

        assert users_after == users_before


def test_login_bloquea_despues_de_cinco_intentos_fallidos():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret",
                "DATABASE": str(Path(temp_dir) / "test.db"),
            }
        )
        client = app.test_client()
        username = f"prueba_{secrets.token_hex(8)}"
        password = "secure-pass-1"

        client.get("/register")
        with client.session_transaction() as session:
            csrf_token = session["csrf_token"]
        client.post(
            "/register",
            data={
                "csrf_token": csrf_token,
                "username": username,
                "password": password,
            },
            follow_redirects=True,
        )
        with client.session_transaction() as session:
            csrf_token = session["csrf_token"]
        client.post(
            "/logout",
            data={"csrf_token": csrf_token},
            follow_redirects=True,
        )
        with client.session_transaction() as session:
            csrf_token = session["csrf_token"]

        for _ in range(5):
            client.post(
                "/login",
                data={
                    "csrf_token": csrf_token,
                    "username": username,
                    "password": "wrong-password",
                },
            )

        client.post(
            "/login",
            data={
                "csrf_token": csrf_token,
                "username": username,
                "password": password,
            },
        )

        with client.session_transaction() as session:
            assert "user_id" not in session
