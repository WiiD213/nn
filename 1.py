import sqlite3
import pandas as pd
import os
from datetime import datetime

# --- Настройки ---
DB_FILENAME = 'hotel.db'
EXCEL_FILENAME = 'Номерной фонд.xlsx'
DOCS_SUBFOLDER = 'Документы заказчика'

# --- 1. Подключение к базе данных ---
print(f"Подключаюсь к базе данных: {DB_FILENAME}")
try:
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    print("Соединение с базой данных установлено.")
except sqlite3.Error as e:
    print(f"Ошибка подключения к базе данных: {e}")
    input("Нажмите Enter для выхода...")
    exit()

# --- 2. Создание всех таблиц ---
print("Создаю таблицы (если они еще не созданы)...")
try:
    cursor.executescript("""
    -- Категории номеров
    CREATE TABLE IF NOT EXISTS RoomCategories (
        id_category INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT,
        base_price REAL,
        capacity INTEGER
    );

    -- Номера
    CREATE TABLE IF NOT EXISTS Rooms (
        id_room INTEGER PRIMARY KEY AUTOINCREMENT,
        room_number TEXT NOT NULL,
        floor TEXT,
        status TEXT, -- Например: Чистый, Грязный, Занят, Назначен к уборке
        id_category INTEGER NOT NULL,
        FOREIGN KEY (id_category) REFERENCES RoomCategories(id_category)
    );

    -- Гости
    CREATE TABLE IF NOT EXISTS Guests (
        id_guest INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        contact_info TEXT,
        passport_info TEXT,
        stay_history TEXT
    );

    -- Бронирования
    CREATE TABLE IF NOT EXISTS Bookings (
        id_booking INTEGER PRIMARY KEY AUTOINCREMENT,
        check_in DATE NOT NULL,
        check_out DATE NOT NULL,
        status TEXT, -- Например: Активно, Завершено, Отменено
        id_guest INTEGER NOT NULL,
        id_room INTEGER NOT NULL,
        FOREIGN KEY (id_guest) REFERENCES Guests(id_guest),
        FOREIGN KEY (id_room) REFERENCES Rooms(id_room)
    );

    -- Сотрудники
    CREATE TABLE IF NOT EXISTS Employees (
        id_employee INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        position TEXT,
        contact_info TEXT,
        schedule TEXT
    );

    -- Уборка
    CREATE TABLE IF NOT EXISTS Cleaning (
        id_cleaning INTEGER PRIMARY KEY AUTOINCREMENT,
        cleaning_date DATE NOT NULL,
        status TEXT, -- Например: Выполнено, В процессе, Требуется проверка
        id_room INTEGER NOT NULL,
        id_employee INTEGER NOT NULL,
        FOREIGN KEY (id_room) REFERENCES Rooms(id_room),
        FOREIGN KEY (id_employee) REFERENCES Employees(id_employee)
    );

    -- Платежи
    CREATE TABLE IF NOT EXISTS Payments (
        id_payment INTEGER PRIMARY KEY AUTOINCREMENT,
        payment_date DATE NOT NULL,
        amount REAL,
        payment_type TEXT, -- Например: Наличные, Карта
        id_booking INTEGER NOT NULL,
        FOREIGN KEY (id_booking) REFERENCES Bookings(id_booking)
    );

    -- Пользователи системы (для авторизации)
    CREATE TABLE IF NOT EXISTS Users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        login TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('Администратор', 'Пользователь')),
        is_blocked INTEGER DEFAULT 0,
        failed_attempts INTEGER DEFAULT 0,
        last_login DATE,
        must_change_password INTEGER DEFAULT 1
    );
    """)
    conn.commit()
    print("Все таблицы успешно созданы или уже существуют.")
except sqlite3.Error as e:
    print(f"Ошибка при создании таблиц: {e}")
    conn.rollback()
    conn.close()
    input("Нажмите Enter для выхода...")
    exit()

# --- 3. Добавление первого пользователя-администратора ---
print("Проверяю наличие пользователя 'admin'...")
try:
    cursor.execute("SELECT * FROM Users WHERE login = ?", ('admin',))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO Users (login, password, role, must_change_password) VALUES (?, ?, ?, ?)",
            ('admin', 'admin', 'Администратор', 1)
        )
        conn.commit()
        print("Пользователь admin/admin добавлен (требуется смена пароля при первом входе).")
    else:
        print("Пользователь admin уже существует.")
except sqlite3.Error as e:
    print(f"Ошибка при добавлении пользователя 'admin': {e}")
    conn.rollback()
    conn.close()
    input("Нажмите Enter для выхода...")
    exit()

# --- 4. Импорт данных из Excel ---
print(f"Пытаюсь найти файл Excel: {EXCEL_FILENAME}")
excel_path = EXCEL_FILENAME
if not os.path.exists(excel_path):
    excel_path = os.path.join(DOCS_SUBFOLDER, EXCEL_FILENAME)

if not os.path.exists(excel_path):
    print(f"Ошибка: Файл '{EXCEL_FILENAME}' не найден.")
    print(f"Убедитесь, что он находится либо в текущей папке, либо в папке '{DOCS_SUBFOLDER}'.")
else:
    print(f"Файл Excel найден: {excel_path}")
    print("Читаю данные из Excel...")
    try:
        df = pd.read_excel(excel_path)
        print("Данные из Excel прочитаны.")

        # Проверяем необходимые столбцы
        expected_cols = ['Этаж', 'Номер', 'Категория']
        if not all(col in df.columns for col in expected_cols):
            print(f"Ошибка: В Excel-файле должны быть столбцы: {expected_cols}.")
            print("Найдены столбцы:", df.columns.tolist())
        else:
            print("Столбцы в Excel соответствуют требованиям. Начинаю импорт номеров...")
            imported_count = 0
            for index, row in df.iterrows():
                try:
                    category_name = str(row['Категория']).strip()
                    room_number = str(row['Номер']).strip()
                    floor = str(row['Этаж']).strip()

                    # Проверяем, существует ли номер с таким номером комнаты, чтобы избежать дубликатов при повторном запуске
                    cursor.execute("SELECT id_room FROM Rooms WHERE room_number = ?", (room_number,))
                    if cursor.fetchone() is not None:
                        # print(f"Номер {room_number} уже существует, пропускаю.")
                        continue # Пропускаем, если номер уже есть

                    # Находим или создаем категорию
                    cursor.execute("SELECT id_category FROM RoomCategories WHERE name = ?", (category_name,))
                    cat = cursor.fetchone()
                    if not cat:
                        cursor.execute("INSERT INTO RoomCategories (name) VALUES (?)", (category_name,))
                        id_category = cursor.lastrowid
                        # print(f"Добавлена новая категория: {category_name}")
                    else:
                        id_category = cat[0]

                    # Добавляем номер
                    cursor.execute(
                        "INSERT INTO Rooms (room_number, floor, id_category, status) VALUES (?, ?, ?, ?)",
                        (room_number, floor, id_category, 'Чистый') # По умолчанию новый номер чистый
                    )
                    imported_count += 1
                except Exception as row_e:
                    print(f"Ошибка при обработке строки {index + 2} из Excel: {row_e}") # +2 потому что индексация с 0 + заголовок
                    # Продолжаем импорт других строк
            conn.commit()
            print(f"Импорт номеров завершен. Добавлено новых номеров: {imported_count}.")

    except FileNotFoundError:
         # Эта ошибка уже обработана выше, но оставляем для надежности
        print(f"Ошибка: Файл '{excel_path}' не найден.")
    except Exception as e:
        print(f"Ошибка при чтении или импорте данных из Excel: {e}")
        conn.rollback()

print("Скрипт инициализации завершен.")
conn.close()

# --- Пауза в конце ---
input("Нажмите Enter для выхода...")