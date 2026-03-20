# Book Club Management System

A Flask web app backed by PostgreSQL for managing book clubs, members, meetings, reviews, and reading lists. Built for CSCE 608 - Database Systems, Project 1.



## Live Demo

[https://bookclub-csce608-bc4909af3b88.herokuapp.com/](https://bookclub-csce608-bc4909af3b88.herokuapp.com/)

## Project Structure

```
project1/
├── bookclub/
│   ├── app.py              # Flask routes and SQL queries
│   ├── requirements.txt    # Python dependencies
│   ├── .env                # DB credentials (not committed)
│   ├── static/             # CSS and JS assets
│   └── templates/          # Jinja2 HTML templates
└── data_generation/
    ├── schema.sql          # PostgreSQL schema (drop + create all tables)
    └── fetch_data.py       # Generates and inserts synthetic data via Faker
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

Create a `.env` file inside the `bookclub/` folder (next to `app.py`):

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

