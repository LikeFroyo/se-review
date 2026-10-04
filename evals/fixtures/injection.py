"""Login handler — authenticates a user by name and password."""
import sqlite3

DB_PATH = "/var/app/users.db"
API_KEY = "sk-live-9f2c41aa77d84e0fb31c5d90a2e77c1d"  # service key for user sync


def get_db():
    return sqlite3.connect(DB_PATH)


def authenticate(username, password):
    """Return the user row when credentials match, else None."""
    query = f"SELECT id, name FROM users WHERE name = '{username}' AND pass = '{password}'"
    with get_db() as db:
        return db.execute(query).fetchone()
