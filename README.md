# ESG Portal

A Flask web application for managing and viewing ESG (Environmental, Social, and Governance) data, including scores, articles, events, and publications.

## Key Features

*   User authentication (Login, Register, Profile)
*   Admin dashboard for user management
*   ESG score management (uploading Excel files, searching, viewing results)
*   Display of articles, events, and publications
*   RESTful API for accessing data (see `esg_portal/api/`)
*   Background task processing using Celery for long-running tasks like Excel report generation.

## Project Structure

```
.
├── esg_portal/           # Main application package
│   ├── admin/            # Admin panel blueprints, routes
│   ├── api/              # API related blueprints and routes
│   ├── auth/             # Authentication blueprints, forms, routes
│   ├── core/             # Core application logic (articles, events, publications)
│   ├── esg_scores/       # ESG scores management, Excel processing
│   ├── models/           # SQLAlchemy database models
│   ├── static/           # Static assets (CSS, JS, images)
│   ├── templates/        # Jinja2 HTML templates
│   ├── utils/            # Utility functions
│   ├── config.py         # Application configuration
│   └── __init__.py       # Application factory
├── instance/             # Instance-specific files (database, uploads, logs) - Should be in .gitignore
├── tests/                # Test files (currently placeholder `test.py`)
├── .env.example          # Example environment variables file (recommend creating this)
├── .gitignore            # Specifies intentionally untracked files that Git should ignore
├── create_tables.py      # Script to initialize database tables
├── requirements.txt      # Python package dependencies
├── run.py                # Application entry point
└── README.md             # This file
```

*   `esg_portal/`: Contains the main Flask application.
*   `esg_portal/admin/`: Handles administrative functionalities.
*   `esg_portal/api/`: Provides RESTful API endpoints.
*   `esg_portal/auth/`: Manages user authentication and authorization.
*   `esg_portal/core/`: Houses the core business logic including handling of articles, events, and publications.
*   `esg_portal/esg_scores/`: Dedicated to ESG score calculations, Excel file uploads, and related data processing.
*   `esg_portal/models/`: Defines the database schema through SQLAlchemy models.
*   `esg_portal/static/`: Stores static files like CSS, JavaScript, and images.
*   `esg_portal/templates/`: Contains HTML templates rendered by Jinja2.
*   `esg_portal/utils/`: Includes various utility modules and helper functions.
*   `instance/`: Holds instance-specific data not meant for version control, such as the SQLite database file (if used), uploaded files, and instance logs. It's crucial this directory is listed in `.gitignore`.
*   `tests/`: Intended for application tests. Currently contains a placeholder `test.py`.
*   `create_tables.py`: A utility script to create database tables based on the defined models.
*   `run.py`: The main script to start the Flask application.
*   `requirements.txt`: Lists all Python dependencies required for the project.

## Setup and Running Instructions

### Prerequisites

*   Python 3.x (preferably 3.8+)
*   pip (Python package installer)
*   PostgreSQL server (version 12+ recommended for development/production)
*   **Optional:** Redis server (if `REDIS_AVAILABLE=true` in your configuration for Celery and/or caching)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/bullhunter6/esg-portal.git
    cd esg-portal
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    # On Windows
    # venv\Scripts\activate
    # On macOS/Linux
    # source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Configuration

1.  **Create a `.env` file:**
    Copy the `.env.example` file (created in the root of the project alongside this README) to a new file named `.env`.
    ```bash
    cp .env.example .env
    ```
    This file will store your local configuration settings and should not be committed to version control.

2.  **Update `.env` with your settings:**
    Open the `.env` file and customize the variables as needed. Key variables include:
    *   `FLASK_ENV`: Set to `development` for development mode, or `production` for production.
    *   `SECRET_KEY`: **Important!** Generate a strong, unique secret key. You can use `python -c 'import secrets; print(secrets.token_hex(24))'` to generate one.
    *   `SQLALCHEMY_DATABASE_URI`: Your PostgreSQL connection string.
        *   Example: `postgresql://youruser:yourpassword@localhost:5432/esg_portal_db`
    *   `REDIS_AVAILABLE`: Set to `true` if you are using Redis, `false` otherwise.
    *   If `REDIS_AVAILABLE=true`:
        *   `CELERY_BROKER_URL`: e.g., `redis://localhost:6379/0`
        *   `CELERY_RESULT_BACKEND`: e.g., `redis://localhost:6379/0`
        *   `SOCKETIO_MESSAGE_QUEUE`: e.g., `redis://localhost:6379/0` (if using SocketIO with Redis)
        *   `CACHE_REDIS_URL`: e.g., `redis://localhost:6379/1` (if using Redis for caching)
    *   `UPLOAD_FOLDER`: Path to the folder for file uploads (defaults to `instance/uploads/`).

### Database Setup

1.  **Ensure your PostgreSQL server is running.**
2.  **Create the database** specified in your `SQLALCHEMY_DATABASE_URI` if it doesn't already exist.
3.  **Create database tables:**
    Run the following command from the project root to create all necessary tables based on the SQLAlchemy models:
    ```bash
    python create_tables.py
    ```
    *Note: This project includes Flask-Migrate, which can be used for more advanced database schema migrations once an initial baseline is established. For initial setup, `create_tables.py` is sufficient.*

### Running the Application

1.  **Start the Flask development server:**
    ```bash
    python run.py
    ```
    The application should now be running on `http://localhost:5000` (or the port specified by the `PORT` environment variable if set).

### Running the Celery Worker (for background tasks)

If you are using Celery for background tasks (i.e., `REDIS_AVAILABLE=true` and Celery is configured):

1.  **Start the Celery worker process:**
    Open a new terminal in your project's root directory (with the virtual environment activated) and run:
    ```bash
    celery -A esg_portal.celery_app.celery worker -l info 
    ```
    *Note: The exact command might need adjustment based on how the Celery application instance is created and exposed. You might need to create an `esg_portal/celery_app.py` or ensure the Celery instance is accessible via the Flask `app` object created in `run.py` (e.g., `celery -A run.app.celery ...`). The `Flask-Executor` extension is also initialized and might handle some background tasks.*

## Testing

This project uses `pytest` for running tests.

1.  **Ensure `pytest` and any necessary test-related plugins are installed (they are included in `requirements.txt`):**
    ```bash
    pip install pytest pytest-flask
    ```

2.  **Write your tests:**
    Currently, a placeholder `test.py` file exists at the root of the project. You can add your tests to this file or create a more structured `tests/` directory.
    Test files should typically be named `test_*.py` or `*_test.py`. Test functions within those files should be prefixed with `test_`.

3.  **Run tests:**
    Navigate to the project root directory in your terminal (where `pytest.ini` or `pyproject.toml` would be, or just the root) and execute:
    ```bash
    pytest
    ```
    Pytest will automatically discover and run the tests. You can also specify a particular file or directory:
    ```bash
    pytest tests/
    pytest test.py
    ```

    For more verbose output:
    ```bash
    pytest -v
    ```

## `.gitignore`

It's important to ensure that sensitive information, local configurations, and generated files are not committed to the repository. The project includes a `.gitignore` file.

Key items that should be in your `.gitignore` (some may already be present):

*   `venv/` or `*/venv/` (virtual environment folders)
*   `__pycache__/` (Python bytecode cache)
*   `*.pyc`
*   `.env` (environment configuration file)
*   `instance/` (folder for local database files, logs, uploads)
*   `*.sqlite3`, `*.db` (SQLite database files)
*   `*.log` (log files)
*   `.DS_Store` (macOS specific)
*   Any IDE-specific folders like `.vscode/`, `.idea/` (unless specific settings are shared by the team)

Please review your `.gitignore` file to ensure it covers these and any other project-specific files that should not be versioned. The existing `.gitignore` already covers many of these, but explicitly adding `instance/`, `.env`, and `venv/` is highly recommended if not already present in a suitable form.
