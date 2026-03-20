# Book Club Management System

A Flask web app backed by PostgreSQL for managing book clubs, members, meetings, reviews, and reading lists. Built for CSCE 608 - Database Systems, Project 1.

## Project Structure

```
project1/
├── bookclub/
│   ├── app.py              # Flask routes and SQL queries
│   ├── requirements.txt    # Python dependencies
│   ├── static/             # CSS and JS assets
│   └── templates/          # Jinja2 HTML templates
├── data_generation/
│   ├── schema.sql          # PostgreSQL schema (drop + create all tables)
│   └── fetch_data.py       # Generates and inserts synthetic data via Faker
└── .env                    # DB credentials (not committed)
```

## Prerequisites

Install these before following the setup steps below.

- **Python 3.10+** — https://www.python.org/downloads/
- **PostgreSQL 16** — https://www.postgresql.org/download/
  The installer includes **pgAdmin 4**, which provides a GUI for browsing tables and running queries. Make sure to note the password you set for the `postgres` user during installation.

## Local Setup

### 1. Create the database

Open a terminal (or use the pgAdmin Query Tool) and run:

```bash
psql -U postgres -c "CREATE DATABASE bookclub;"
psql -U postgres -d bookclub -f data_generation/schema.sql
```

On Windows you may need to use the full path to psql, e.g. `"C:\Program Files\PostgreSQL\16\bin\psql.exe"`.

### 2. Configure environment

Create a `.env` file in the project root:

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=bookclub
DB_USER=postgres
DB_PASSWORD=your_password
SECRET_KEY=some_secret
```

### 3. Generate data

```bash
cd data_generation
pip install faker psycopg2-binary python-dotenv
python fetch_data.py
```

This populates all 12 tables with synthetic data (~5k-25k rows depending on club meeting frequency).

### 4. Run the app

```bash
cd bookclub
pip install -r requirements.txt
python app.py
```

The app runs at `http://localhost:5000`.

## Features

- Browse and search books by title and genre
- Member profiles with activity history
- Club and meeting management
- Reviews and reading lists
- Analytics dashboard with 11 queries (top-rated books, active members, attendance rates, etc.)
- Full CRUD for books, members, clubs, and meetings

## Common Errors

**`psql: error: connection to server on socket failed`**
PostgreSQL is not running. Start it via Services (Windows) or `pg_ctl start`.

**`fe_sendauth: no password supplied`**
Add `-W` to your psql command or set the `PGPASSWORD` environment variable.

**`FATAL: database "bookclub" does not exist`**
Run step 1 first to create the database before loading the schema.

**`ModuleNotFoundError: No module named 'psycopg2'`**
Run `pip install psycopg2-binary` inside the same Python environment you use to run the app.

**`could not connect to server` in the Flask app**
Check that the values in your `.env` file match your PostgreSQL installation (host, port, user, password).

**`UniqueViolation` when running fetch_data.py**
The database already has data. Re-run the schema first to drop and recreate all tables:
```bash
psql -U postgres -d bookclub -f data_generation/schema.sql
```

## Deploying to Heroku

This section covers deploying just the Flask app (`bookclub/`) to Heroku. You will need a Heroku account and the Heroku CLI installed (`brew install heroku` or download from the Heroku website).

### 1. Add required files

Create `bookclub/Procfile` (no extension):

```
web: python app.py
```

Update `app.py` to read the port from the environment (Heroku assigns a dynamic port):

```python
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
```

### 2. Create the Heroku app

```bash
cd bookclub
heroku login
heroku create your-app-name
```

### 3. Provision a PostgreSQL database

```bash
heroku addons:create heroku-postgresql:essential-0
```

This adds a `DATABASE_URL` environment variable to your app automatically.

### 4. Update the DB connection to support Heroku

Heroku provides a single `DATABASE_URL` instead of separate host/user/password variables. Update `get_db_connection()` in `app.py` to handle both:

```python
import urllib.parse

def get_db_connection():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Heroku provides postgres:// but psycopg2 needs postgresql://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        conn = psycopg2.connect(database_url)
    else:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            port=os.getenv("DB_PORT"),
        )
    conn.autocommit = False
    return conn
```

### 5. Set environment variables

```bash
heroku config:set SECRET_KEY=your_secret_key
```

### 6. Load the schema and data

```bash
heroku pg:psql < ../data_generation/schema.sql
heroku run python ../data_generation/fetch_data.py
```

Or connect to the Heroku database directly using pgAdmin with the credentials from:

```bash
heroku pg:credentials:url
```

### 7. Deploy

```bash
git add .
git commit -m "deploy to heroku"
git push heroku main
heroku open
```
