# auth_app.py
import tkinter as tk
from tkinter import messagebox, simpledialog
import sqlite3
from datetime import datetime, timedelta
import os

DB_FILENAME = 'hotel.db'

# --- Функции для работы с базой данных Users ---

def get_user(login):
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, password, role, is_blocked, failed_attempts, last_login, must_change_password FROM Users WHERE login=?", (login,))
    user = cursor.fetchone()
    conn.close()
    return user

def update_user(user_id, **kwargs):
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    update_fields = ', '.join([f"{key}=?" for key in kwargs.keys()])
    query = f"UPDATE Users SET {update_fields} WHERE id=?"
    values = list(kwargs.values()) + [user_id]
    cursor.execute(query, values)
    conn.commit()
    conn.close()

def get_user_by_id(user_id):
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE id=?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def add_user(login, password, role):
    if get_user(login):
        return False, "Пользователь с таким логином уже существует"
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO Users (login, password, role, must_change_password, last_login) VALUES (?, ?, ?, 1, ?)",
        (login, password, role, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()
    return True, "Пользователь успешно добавлен"

def unblock_user(login):
    user = get_user(login)
    if not user:
        return False, "Пользователь не найден"
    update_user(user[0], is_blocked=0, failed_attempts=0)
    return True, "Пользователь разблокирован"

# --- Логика авторизации ---

def check_user(login, password):
    user = get_user(login)
    if not user:
        return None, "Вы ввели неверный логин или пароль. Пожалуйста проверьте ещё раз введенные данные"

    user_id, db_password, role, is_blocked, failed_attempts, last_login_str, must_change_password = user

    # Проверка блокировки по неактивности
    if last_login_str:
        try:
            last_login_dt = datetime.strptime(last_login_str, "%Y-%m-%d %H:%M:%S")
            if datetime.now() - last_login_dt > timedelta(days=30) and not is_blocked:
                update_user(user_id, is_blocked=1)
                return None, "Вы заблокированы из-за долгого отсутствия. Обратитесь к администратору"
        except (ValueError, TypeError):
             pass # Игнорируем ошибку парсинга даты, если формат не соответствует

    if is_blocked:
        return None, "Вы заблокированы. Обратитесь к администратору"

    # Проверка пароля
    if password == db_password:
        update_user(user_id, failed_attempts=0, last_login=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        return (user_id, role, must_change_password), "Вы успешно авторизовались"
    else:
        failed_attempts += 1
        if failed_attempts >= 3:
            update_user(user_id, is_blocked=1)
            return None, "Вы заблокированы после 3-х неудачных попыток. Обратитесь к администратору"
        else:
            update_user(user_id, failed_attempts=failed_attempts)
            return None, "Вы ввели неверный логин или пароль. Пожалуйста проверьте ещё раз введенные данные"

# --- Логика смены пароля ---

def change_password_action(user_id, old_pwd_entry, new_pwd_entry, confirm_pwd_entry, window_to_close):
    old_pwd = old_pwd_entry.get()
    new_pwd = new_pwd_entry.get()
    confirm_pwd = confirm_pwd_entry.get()

    if not old_pwd or not new_pwd or not confirm_pwd:
        messagebox.showerror("Ошибка", "Все поля обязательны для заполнения", parent=window_to_close)
        return

    user = get_user_by_id(user_id)
    if not user:
        messagebox.showerror("Ошибка", "Пользователь не найден", parent=window_to_close)
        return

    if old_pwd != user[2]: # user[2] это пароль в базе
        messagebox.showerror("Ошибка", "Текущий пароль неверен", parent=window_to_close)
        return
    if new_pwd != confirm_pwd:
        messagebox.showerror("Ошибка", "Новый пароль и подтверждение не совпадают", parent=window_to_close)
        return
    if len(new_pwd) < 4: # Пример простого требования к паролю
        messagebox.showerror("Ошибка", "Новый пароль слишком короткий (минимум 4 символа)", parent=window_to_close)
        return

    update_user(user_id, password=new_pwd, must_change_password=0)
    messagebox.showinfo("Успех", "Пароль успешно изменён", parent=window_to_close)
    window_to_close.destroy() # Закрыть окно смены пароля


def show_change_password_window(user_id):
    win = tk.Toplevel(root) # Делаем дочерним окном root
    win.title("Смена пароля")
    win.geometry("300x170") # Увеличим размер окна
    win.transient(root) # Сделать окно зависимым от главного
    win.grab_set()     # Модальное окно (блокирует взаимодействие с другими окнами)

    tk.Label(win, text="Текущий пароль:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
    old_pwd_entry = tk.Entry(win, show="*", width=25)
    old_pwd_entry.grid(row=0, column=1, padx=5, pady=5)
    old_pwd_entry.focus_set() # Установить фокус на первое поле

    tk.Label(win, text="Новый пароль:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
    new_pwd_entry = tk.Entry(win, show="*", width=25)
    new_pwd_entry.grid(row=1, column=1, padx=5, pady=5)

    tk.Label(win, text="Подтверждение:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
    confirm_pwd_entry = tk.Entry(win, show="*", width=25)
    confirm_pwd_entry.grid(row=2, column=1, padx=5, pady=5)

    change_btn = tk.Button(win, text="Изменить пароль",
                           command=lambda: change_password_action(user_id, old_pwd_entry, new_pwd_entry, confirm_pwd_entry, win))
    change_btn.grid(row=3, column=0, columnspan=2, pady=10)

    win.protocol("WM_DELETE_WINDOW", lambda: on_change_pwd_close(user_id, win))

def on_change_pwd_close(user_id, window):
    user = get_user_by_id(user_id)
    if user and user[6] == 1: # user[6] это must_change_password
         messagebox.showwarning("Внимание", "Вы должны сменить пароль для продолжения.", parent=window)
    else:
        window.destroy()

# --- Логика Админ-панели ---

admin_window = None # Глобальная переменная для окна админ-панели

def add_user_action():
    login = simpledialog.askstring("Добавить пользователя", "Введите логин:", parent=admin_window)
    if not login: return
    password = simpledialog.askstring("Добавить пользователя", "Введите пароль:", show="*", parent=admin_window)
    if not password: return
    role = simpledialog.askstring("Добавить пользователя", "Введите роль (Администратор/Пользователь):", parent=admin_window)
    if role not in ['Администратор', 'Пользователь']:
        messagebox.showerror("Ошибка", "Неверная роль. Введите 'Администратор' или 'Пользователь'.", parent=admin_window)
        return

    ok, msg = add_user(login.strip(), password.strip(), role.strip()) # Убираем пробелы
    if ok:
        messagebox.showinfo("Успех", msg, parent=admin_window)
    else:
        messagebox.showerror("Ошибка", msg, parent=admin_window)

def unblock_user_action():
    login = simpledialog.askstring("Разблокировать пользователя", "Введите логин пользователя для разблокировки:", parent=admin_window)
    if not login: return
    ok, msg = unblock_user(login.strip()) # Убираем пробелы
    if ok:
        messagebox.showinfo("Успех", msg, parent=admin_window)
    else:
        messagebox.showerror("Ошибка", msg, parent=admin_window)


def show_admin_panel_window():
    global admin_window
    if admin_window is None or not admin_window.winfo_exists():
        admin_window = tk.Toplevel(root) # Делаем дочерним окном root
        admin_window.title("Админ-панель")
        admin_window.geometry("250x100")
        admin_window.transient(root) # Сделать окно зависимым от главного
        admin_window.protocol("WM_DELETE_WINDOW", lambda: admin_window.destroy()) # Просто закрываем окно крестиком

        tk.Button(admin_window, text="Добавить пользователя", command=add_user_action).pack(pady=5, padx=10)
        tk.Button(admin_window, text="Разблокировать пользователя", command=unblock_user_action).pack(pady=5, padx=10)
    else:
        admin_window.lift() # Поднять окно на передний план


# --- GUI Приложение (Главное окно Авторизации) ---

def login_button_action():
    login = entry_login.get().strip()
    password = entry_password.get().strip()

    if not login or not password:
        messagebox.showerror("Ошибка", "Поля Логин и Пароль обязательны для заполнения")
        return

    user_info, msg = check_user(login, password)

    if user_info:
        user_id, role, must_change_password = user_info
        # messagebox.showinfo("Успех", msg) # Это сообщение часто избыточно перед открытием нового окна
        root.withdraw() # Скрыть окно авторизации

        if must_change_password:
            show_change_password_window(user_id)
        elif role == "Администратор":
            show_admin_panel_window()
        else:
            # Здесь можно открыть рабочий стол для обычного пользователя
            messagebox.showinfo("Рабочий стол", f"Добро пожаловать, {role} {login}!")
            # Если для пользователя нет рабочего стола, можно просто закрыть главное окно
            # root.destroy()

    else:
        messagebox.showerror("Ошибка", msg)

def on_closing():
    # Спрашиваем пользователя перед выходом
    if messagebox.askokcancel("Выход", "Вы хотите выйти из приложения авторизации?"):
        root.destroy()

# --- Запуск GUI ---
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Авторизация в гостиничной системе")
    root.geometry("300x150")
    root.eval('tk::PlaceWindow . center') # Разместить окно по центру экрана
    root.protocol("WM_DELETE_WINDOW", on_closing) # Обработка закрытия окна крестиком

    tk.Label(root, text="Логин:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
    entry_login = tk.Entry(root, width=25)
    entry_login.grid(row=0, column=1, padx=10, pady=5)

    tk.Label(root, text="Пароль:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
    entry_password = tk.Entry(root, show="*", width=25)
    entry_password.grid(row=1, column=1, padx=10, pady=5)

    btn_login = tk.Button(root, text="Войти", command=login_button_action, width=15)
    btn_login.grid(row=2, column=0, columnspan=2, pady=10)

    entry_login.bind('<Return>', lambda event=None: login_button_action())
    entry_password.bind('<Return>', lambda event=None: login_button_action())

    entry_login.focus_set() # Установить фокус на поле логина при запуске

    root.mainloop()