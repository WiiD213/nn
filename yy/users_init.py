import sqlite3
from datetime import datetime

DB_FILENAME = 'hotel.db'

def init_db():
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    
    # Создаем таблицу Users
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        login TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        is_blocked INTEGER DEFAULT 0,
        failed_attempts INTEGER DEFAULT 0,
        last_login TEXT,
        must_change_password INTEGER DEFAULT 0
    )
    ''')
    
    # Добавляем администратора, если его еще нет
    try:
        cursor.execute(
            "INSERT INTO Users (login, password, role, must_change_password, last_login) VALUES (?, ?, ?, ?, ?)",
            ('admin', 'admin', 'Администратор', 0, datetime.now().strftime("%Y-%m-%d %H:%M:%S'))
        )
        print("Администратор добавлен (логин: admin, пароль: admin)")
    except sqlite3.IntegrityError:
        print("Администратор уже существует")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()