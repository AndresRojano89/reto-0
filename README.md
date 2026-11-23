# Enfoque — gestor de tareas

Aplicación web en español para organizar tareas personales. Cada usuario tiene una cuenta y solo puede consultar o modificar sus propias tareas.

## Requisitos

- Python 3.10 o posterior
- pip

## Instalación y ejecución

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:SECRET_KEY = "reemplaza-esto-por-una-clave-aleatoria"
python app.py
```

Abre <http://127.0.0.1:5000>. La base SQLite `tasks.db` se crea automáticamente junto a `app.py`. Para usar otro archivo, configura `TASKS_DATABASE`.

`SESSION_COOKIE_SECURE=1` requiere HTTPS; omítela en desarrollo local por HTTP. Para desplegarla, define una `SECRET_KEY` larga y aleatoria y ejecuta la aplicación detrás de un servidor WSGI con depuración desactivada. No uses el servidor de desarrollo de Flask en producción.

## Funciones

- Registro e inicio de sesión con contraseñas almacenadas mediante hash.
- Creación, edición, finalización y eliminación de tareas.
- Aislamiento de tareas por usuario y protección CSRF en formularios POST.
