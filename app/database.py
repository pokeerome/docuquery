import sqlite3

DB_FILE = "data/users.db"

def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            hashed_password TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def create_user(email: str, hashed_password: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO users (email, hashed_password) VALUES (?, ?)",
        (email, hashed_password)
    )
    conn.commit()
    conn.close()

def get_user_by_email(email: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, email, hashed_password FROM users WHERE email = ?", (email,))
    row = c.fetchone()
    conn.close()
    if row is None:
        return None
    return {"id": row[0], "email": row[1], "hashed_password": row[2]}