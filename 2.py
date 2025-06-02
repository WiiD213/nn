# users_init.py
import sqlite3
from datetime import datetime

print("--- Запуск скрипта инициализации Users ---")

conn = sqlite3.connect('hotel.db')
cursor = conn.cursor()

try:
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        login TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('Администратор', 'Пользователь')),
        is_blocked INTEGER DEFAULT 0,
        failed_attempts INTEGER DEFAULT 0,
        last_login TEXT, -- Храним как TEXT в формате YYYY-MM-DD HH:MM:SS
        must_change_password INTEGER DEFAULT 1
    );
    """)
    conn.commit()
    print("Таблица Users проверена или создана успешно.")

    # Добавим первого администратора, если его нет
    cursor.execute("SELECT * FROM Users WHERE login = ?", ('admin',))
    if not cursor.fetchone():
        # При первом создании задаем last_login как текущее время
        cursor.execute(
            "INSERT INTO Users (login, password, role, must_change_password, last_login) VALUES (?, ?, ?, ?, ?)",
            ('admin', 'admin', 'Администратор', 1, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        print("Пользователь admin/admin добавлен (требуется смена пароля при первом входе).")
    else:
        print("Пользователь admin уже существует.")

except sqlite3.Error as e:
    print(f"Ошибка базы данных при инициализации Users: {e}")
    conn.rollback()
except Exception as e:
    print(f"Произошла ошибка: {e}")

finally:
    conn.close()
    print("--- Скрипт инициализации Users завершен ---")
    input("Нажмите Enter для выхода...") # Пауза для просмотра результата
