import re
import tempfile
import unittest
from pathlib import Path

from app import create_app


class TaskAppTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret",
                "DATABASE": str(Path(self.temp_dir.name) / "test.db"),
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def csrf_token(self, client=None):
        current_client = client or self.client
        with current_client.session_transaction() as user_session:
            token = user_session.get("csrf_token")
            user_id = user_session.get("user_id")
        if token is None:
            current_client.get("/tasks" if user_id is not None else "/login", follow_redirects=True)
            with current_client.session_transaction() as user_session:
                token = user_session["csrf_token"]
        return token

    def register(self, username):
        token = self.csrf_token()
        return self.client.post(
            "/register",
            data={"csrf_token": token, "username": username, "password": "secure-pass-1"},
            follow_redirects=True,
        )

    def test_registration_task_lifecycle_and_login(self):
        response = self.register("ana")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Hola, ana", response.data)

        token = self.csrf_token()
        response = self.client.post(
            "/tasks",
            data={"csrf_token": token, "title": "Preparar presentación", "description": "Para el lunes"},
            follow_redirects=True,
        )
        self.assertIn(b"Preparar presentaci", response.data)
        task_id = int(re.search(rb"/tasks/(\d+)/edit", response.data).group(1))

        response = self.client.post(
            f"/tasks/{task_id}/edit",
            data={"csrf_token": token, "title": "Presentación lista", "description": ""},
            follow_redirects=True,
        )
        self.assertIn(b"Presentaci", response.data)
        self.assertIn(b"lista", response.data)

        response = self.client.post(
            f"/tasks/{task_id}/toggle", data={"csrf_token": token}, follow_redirects=True
        )
        self.assertIn(b"task-done", response.data)

        response = self.client.post(
            f"/tasks/{task_id}/delete", data={"csrf_token": token}, follow_redirects=True
        )
        self.assertIn(b"Tu lista empieza aqu", response.data)

        self.client.post("/logout", data={"csrf_token": token}, follow_redirects=True)
        token = self.csrf_token()
        response = self.client.post(
            "/login",
            data={"csrf_token": token, "username": "ana", "password": "secure-pass-1"},
            follow_redirects=True,
        )
        self.assertIn(b"Hola, ana", response.data)

    def test_users_cannot_access_each_others_tasks(self):
        self.register("ana")
        token = self.csrf_token()
        self.client.post(
            "/tasks", data={"csrf_token": token, "title": "Privada"}, follow_redirects=True
        )
        task_id = int(re.search(rb"/tasks/(\d+)/edit", self.client.get("/tasks").data).group(1))

        other_client = self.app.test_client()
        token = self.csrf_token(other_client)
        other_client.post(
            "/register",
            data={"csrf_token": token, "username": "luis", "password": "secure-pass-2"},
        )
        self.assertEqual(other_client.get(f"/tasks/{task_id}/edit").status_code, 404)
        token = self.csrf_token(other_client)
        response = other_client.post(
            f"/tasks/{task_id}/delete", data={"csrf_token": token}
        )
        self.assertEqual(response.status_code, 404)

    def test_post_without_csrf_token_is_rejected(self):
        self.assertEqual(self.client.post("/register", data={"username": "ana"}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
