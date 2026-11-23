# Proyecto
Aplicación web en español para registrar usuarios y organizar tareas personales.
Cada usuario puede crear, editar, completar y eliminar solo sus propias tareas.

# Stack
- Framework: Python 3.10+ y Flask 3.
- Base de datos: SQLite mediante el módulo sqlite3.
- Librerías principales: Flask, Werkzeug y Jinja2.
- Pruebas y calidad: pytest, unittest y Ruff.

# Comandos
- Instalar: `pip install -r requirements.txt`
- Ejecutar: `python app.py`
- Pruebas: `python -m pytest -v`
- Estilo: `ruff check .`

# Estructura
- `.gitignore`: excluye entornos virtuales, secretos, bases de datos y cachés.
- `.venv/`: entorno virtual local con las dependencias instaladas.
- `README.md`: requisitos, instalación, ejecución y resumen funcional.
- `app.py`: fábrica Flask, base de datos, autenticación y rutas CRUD.
- `test_app.py`: pruebas de registro, tareas, permisos y protección CSRF.
- `requirements.txt`: declara la dependencia principal de Flask.
- `tasks.db`: base SQLite generada para el almacenamiento local.
- `static/`: archivos públicos compartidos por las plantillas.
- `static/style.css`: estilos visuales de la interfaz.
- `templates/`: plantillas HTML renderizadas por Flask.
- `templates/base.html`: diseño base compartido.
- `templates/auth.html`: formularios de registro e inicio de sesión.
- `templates/tasks.html`: listado y creación de tareas.
- `templates/edit_task.html`: formulario de edición de tareas.

# Qué no hacer
- No modificar las pruebas para que pasen.
- No escribir claves en el código.
- No instalar dependencias sin explicar para qué.
- No hacer commit ni push.

# Lecciones aprendidas
