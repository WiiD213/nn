# --- Функции для работы с базой данных Users (используются приложением) ---

def get_user(login):
    """ Получает информацию о пользователе по логину из базы данных. """
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, password, role, is_blocked, failed_attempts, last_login, must_change_password FROM Users WHERE login=?", (login,))
    user = cursor.fetchone()
    conn.close()
    return user

def update_user(user_id, **kwargs):
    """ Обновляет данные пользователя в базе по его ID. """
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    update_fields = ', '.join([f"{key}=?" for key in kwargs.keys()])
    query = f"UPDATE Users SET {update_fields} WHERE id=?"
    values = list(kwargs.values()) + [user_id]
    cursor.execute(query, values)
    conn.commit()
    conn.close()

def add_user(login, password, role):
    """
    Добавляет нового пользователя в базу данных.
    Проверяет уникальность логина.
    """
    # Проверяем, существует ли пользователь с таким логином
    if get_user(login):
        return False, "Пользователь с таким логином уже существует" # Сообщение, если логин занят

    # Если логин свободен, добавляем пользователя
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    try:
        # must_change_password=1 по умолчанию для нового пользователя,
        # last_login ставим текущее время создания
        cursor.execute(
            "INSERT INTO Users (login, password, role, must_change_password, last_login) VALUES (?, ?, ?, 1, ?)",
            (login, password, role, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        return True, "Пользователь успешно добавлен"
    except sqlite3.Error as e:
        conn.rollback()
        return False, f"Ошибка базы данных при добавлении пользователя: {e}"
    finally:
        conn.close()


def unblock_user(login):
    """
    Снимает блокировку с пользователя и сбрасывает счетчик неудачных попыток.
    """
    user = get_user(login)
    if not user:
        return False, "Пользователь с таким логином не найден" # Сообщение, если пользователь не найден

    user_id, _, _, is_blocked, _, _, _ = user

    if not is_blocked:
         return False, f"Пользователь '{login}' не заблокирован." # Сообщение, если пользователь уже не заблокирован

    # Обновляем статус блокировки и сбрасываем счетчик
    update_user(user_id, is_blocked=0, failed_attempts=0)
    return True, f"Пользователь '{login}' успешно разблокирован."


# --- Логика Админ-панели (GUI) ---

admin_window = None # Глобальная переменная для окна админ-панели

def add_user_action():
    """ Действие при нажатии кнопки 'Добавить пользователя' в админ-панели. """
    # Запрашиваем данные у администратора через диалоговые окна
    login = simpledialog.askstring("Добавить пользователя", "Введите логин:", parent=admin_window)
    if not login: return # Если админ отменил ввод
    password = simpledialog.askstring("Добавить пользователя", "Введите пароль:", show="*", parent=admin_window)
    if not password: return # Если админ отменил ввод
    role = simpledialog.askstring("Добавить пользователя", "Введите роль (Администратор/Пользователь):", parent=admin_window)
    if not role: return # Если админ отменил ввод

    # Проверяем введенную роль
    if role.strip() not in ['Администратор', 'Пользователь']:
        messagebox.showerror("Ошибка", "Неверная роль. Введите 'Администратор' или 'Пользователь'.", parent=admin_window)
        return

    # Вызываем функцию добавления пользователя в базу
    ok, msg = add_user(login.strip(), password.strip(), role.strip()) # Убираем пробелы на всякий случай

    # Выводим результат операции
    if ok:
        messagebox.showinfo("Успех", msg, parent=admin_window)
    else:
        messagebox.showerror("Ошибка", msg, parent=admin_window)

def unblock_user_action():
    """ Действие при нажатии кнопки 'Разблокировать пользователя' в админ-панели. """
    # Запрашиваем логин пользователя у администратора
    login = simpledialog.askstring("Разблокировать пользователя", "Введите логин пользователя для разблокировки:", parent=admin_window)
    if not login: return # Если админ отменил ввод

    # Вызываем функцию разблокировки пользователя в базе
    ok, msg = unblock_user(login.strip()) # Убираем пробелы

    # Выводим результат операции
    if ok:
        messagebox.showinfo("Успех", msg, parent=admin_window)
    else:
        messagebox.showerror("Ошибка", msg, parent=admin_window)


def show_admin_panel_window():
    """ Создает и отображает окно администраторской панели. """
    global admin_window
    # Проверяем, существует ли окно и не было ли оно уничтожено
    if admin_window is None or not admin_window.winfo_exists():
        # Создаем новое окно
        admin_window = tk.Toplevel(root) # Делаем его дочерним окном главного окна авторизации (root)
        admin_window.title("Админ-панель")
        admin_window.geometry("250x120") # Увеличим немного размер
        admin_window.transient(root) # Сделать окно зависимым от главного (сворачивается вместе с ним)
        admin_window.protocol("WM_DELETE_WINDOW", lambda: admin_window.destroy()) # При закрытии крестиком просто уничтожаем это окно

        # Добавляем кнопки на панель
        tk.Button(admin_window, text="Добавить пользователя", command=add_user_action).pack(pady=5, padx=10, fill='x')
        tk.Button(admin_window, text="Разблокировать пользователя", command=unblock_user_action).pack(pady=5, padx=10, fill='x')
        # Здесь можно добавить другие кнопки: изменить пароль пользователя, посмотреть список пользователей и т.д.

    else:
        admin_window.lift() # Поднять окно на передний план, если оно уже открыто

# Эта функция вызывается из логики авторизации, если роль == "Администратор"
# Пример вызова в функции login_button_action:
# if user_info:
#     user_id, role, must_change_password = user_info
#     root.withdraw() # Скрыть окно авторизации
#     if must_change_password:
#         show_change_password_window(user_id)
#     elif role == "Администратор":
#         show_admin_panel_window() # <-- Вот здесь вызывается админ-панель
#     else:
#         # ... показать рабочий стол пользователя

import sqlite3
from datetime import datetime

DB_FILENAME = 'autopark.db'

def init_database():
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
    
    # Создаем таблицу Vehicles
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Vehicles (
        id_vehicle INTEGER PRIMARY KEY AUTOINCREMENT,
        vehicle_number TEXT UNIQUE NOT NULL,
        model TEXT NOT NULL,
        category TEXT NOT NULL,
        status TEXT DEFAULT 'Свободен',
        total_hours REAL DEFAULT 0
    )
    ''')
    
    # Создаем таблицу Usage для отслеживания использования
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Usage (
        id_usage INTEGER PRIMARY KEY AUTOINCREMENT,
        id_vehicle INTEGER,
        start_time TEXT NOT NULL,
        end_time TEXT,
        FOREIGN KEY (id_vehicle) REFERENCES Vehicles (id_vehicle)
    )
    ''')
    
    # Проверяем, существует ли администратор
    cursor.execute("SELECT id FROM Users WHERE login='admin'")
    if not cursor.fetchone():
        # Создаем администратора
        cursor.execute('''
        INSERT INTO Users (login, password, role, last_login)
        VALUES (?, ?, ?, ?)
        ''', ('admin', 'admin', 'Администратор', datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    conn.commit()
    conn.close()
    print("База данных успешно инициализирована")

if __name__ == "__main__":
    init_database()