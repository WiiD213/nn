import tkinter as tk
from tkinter import messagebox, simpledialog
import sqlite3
from datetime import datetime, timedelta
import os

DB_FILENAME = 'hotel.db'

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
    for key, value in kwargs.items():
        cursor.execute(f"UPDATE Users SET {key}=? WHERE id=?", (value, user_id))
    conn.commit()
    conn.close()

def check_user(login, password):
    user = get_user(login)
    if not user:
        return None, "Вы ввели неверный логин или пароль. Пожалуйста проверьте ещё раз введенные данные"
    user_id, db_password, role, is_blocked, failed_attempts, last_login, must_change_password = user
    # Проверка блокировки по неактивности
    if last_login:
        last_login_dt = datetime.strptime(last_login, "%Y-%m-%d %H:%M:%S")
        if datetime.now() - last_login_dt > timedelta(days=30):
            update_user(user_id, is_blocked=1)
            return None, "Вы заблокированы. Обратитесь к администратору"
    if is_blocked:
        return None, "Вы заблокированы. Обратитесь к администратору"
    if password == db_password:
        update_user(user_id, failed_attempts=0, last_login=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        return (user_id, role, must_change_password), "Вы успешно авторизовались"
    else:
        failed_attempts += 1
        if failed_attempts >= 3:
            update_user(user_id, is_blocked=1)
            return None, "Вы заблокированы. Обратитесь к администратору"
        else:
            update_user(user_id, failed_attempts=failed_attempts)
            return None, "Вы ввели неверный логин или пароль. Пожалуйста проверьте ещё раз введенные данные"

def change_password(user_id, old_pwd, new_pwd, confirm_pwd):
    user = get_user_by_id(user_id)
    if not user:
        return False, "Пользователь не найден"
    if old_pwd != user[2]:
        return False, "Текущий пароль неверен"
    if new_pwd != confirm_pwd:
        return False, "Новый пароль и подтверждение не совпадают"
    if len(new_pwd) < 4:
        return False, "Пароль слишком короткий"
    update_user(user_id, password=new_pwd, must_change_password=0)
    return True, "Пароль успешно изменён"

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
        "INSERT INTO Users (login, password, role, must_change_password, last_login) VALUES (?, ?, ?, ?, ?)",
        (login, password, role, 1, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
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

# --- Функции для работы с базой данных Rooms и RoomCategories ---

def get_rooms_info():
    """ Получает информацию обо всех номерах с категориями. """
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            r.room_number,
            r.floor,
            rc.name, -- Название категории
            r.status,
            r.id_room -- Нужен для управления статусом
        FROM Rooms r
        JOIN RoomCategories rc ON r.id_category = rc.id_category
        ORDER BY r.floor, r.room_number
    """)
    rooms = cursor.fetchall()
    conn.close()
    return rooms

def calculate_occupancy():
    """ Рассчитывает процент загруженности номеров. """
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    
    # Общая загруженность
    cursor.execute("""
        SELECT 
            COUNT(*) as total_rooms,
            SUM(CASE WHEN status = 'Занят' THEN 1 ELSE 0 END) as occupied_rooms
        FROM Rooms
    """)
    total_rooms, occupied_rooms = cursor.fetchone()
    total_occupancy = (occupied_rooms / total_rooms * 100) if total_rooms > 0 else 0

    # Загруженность по категориям
    cursor.execute("""
        SELECT 
            rc.name as category,
            COUNT(*) as total_rooms,
            SUM(CASE WHEN r.status = 'Занят' THEN 1 ELSE 0 END) as occupied_rooms
        FROM Rooms r
        JOIN RoomCategories rc ON r.id_category = rc.id_category
        GROUP BY rc.name
    """)
    category_occupancy = cursor.fetchall()

    # Загруженность по этажам
    cursor.execute("""
        SELECT 
            floor,
            COUNT(*) as total_rooms,
            SUM(CASE WHEN status = 'Занят' THEN 1 ELSE 0 END) as occupied_rooms
        FROM Rooms
        GROUP BY floor
    """)
    floor_occupancy = cursor.fetchall()

    conn.close()
    return total_occupancy, category_occupancy, floor_occupancy

def update_room_status(room_id, new_status):
    """ Обновляет статус номера по его ID. """
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Rooms SET status=? WHERE id_room=?", (new_status, room_id))
        conn.commit()
        return True, "Статус номера успешно обновлен."
    except sqlite3.Error as e:
        conn.rollback()
        return False, f"Ошибка при обновлении статуса номера: {e}"
    finally:
        conn.close()

# --- Логика авторизации ---

def login_action():
    login = entry_login.get()
    password = entry_password.get()
    if not login or not password:
        messagebox.showerror("Ошибка", "Поля Логин и Пароль обязательны для заполнения")
        return
    user, msg = check_user(login, password)
    if user:
        user_id, role, must_change_password = user
        messagebox.showinfo("Успех", msg)
        if must_change_password:
            show_change_password(user_id)
        elif role == "Администратор":
            show_admin_panel_window()
        else:
            messagebox.showinfo("Вход", "Добро пожаловать, пользователь!")
    else:
        messagebox.showerror("Ошибка", msg)

# --- Логика смены пароля ---

def show_change_password(user_id):
    win = tk.Toplevel()
    win.title("Смена пароля")
    win.geometry("300x150")
    win.transient(root)
    win.grab_set()

    tk.Label(win, text="Новый пароль:").grid(row=0, column=0, pady=5)
    new_password = tk.Entry(win, show="*")
    new_password.grid(row=0, column=1, pady=5)

    tk.Label(win, text="Подтвердите пароль:").grid(row=1, column=0, pady=5)
    confirm_password = tk.Entry(win, show="*")
    confirm_password.grid(row=1, column=1, pady=5)

    def do_change():
        if new_password.get() != confirm_password.get():
            messagebox.showerror("Ошибка", "Пароли не совпадают")
            return
        if not new_password.get():
            messagebox.showerror("Ошибка", "Пароль не может быть пустым")
            return
        update_user(user_id, password=new_password.get(), must_change_password=0)
        messagebox.showinfo("Успех", "Пароль успешно изменен")
        win.destroy()

    tk.Button(win, text="Изменить пароль", command=do_change).grid(row=2, column=0, columnspan=2, pady=10)

# --- Логика Админ-панели (GUI) ---

admin_window = None # Главное окно админ-панели

def add_user_action():
    """ Обработчик нажатия кнопки 'Добавить пользователя' """
    add_win = tk.Toplevel(root)
    add_win.title("Добавить пользователя")
    add_win.geometry("300x250")
    add_win.transient(root)
    add_win.grab_set()

    main_frame = tk.Frame(add_win, padx=20, pady=20)
    main_frame.grid(row=0, column=0, sticky="nsew")
    add_win.grid_rowconfigure(0, weight=1)
    add_win.grid_columnconfigure(0, weight=1)

    tk.Label(main_frame, text="Логин:").grid(row=0, column=0, pady=5, sticky="w")
    login_entry = tk.Entry(main_frame, width=30)
    login_entry.grid(row=0, column=1, pady=5, padx=5)

    tk.Label(main_frame, text="Пароль:").grid(row=1, column=0, pady=5, sticky="w")
    password_entry = tk.Entry(main_frame, show="*", width=30)
    password_entry.grid(row=1, column=1, pady=5, padx=5)

    tk.Label(main_frame, text="Роль:").grid(row=2, column=0, pady=5, sticky="w")
    role_var = tk.StringVar(main_frame)
    role_var.set("Пользователь")
    role_menu = tk.OptionMenu(main_frame, role_var, "Пользователь", "Администратор")
    role_menu.grid(row=2, column=1, pady=5, padx=5, sticky="w")

    def do_add():
        login = login_entry.get()
        password = password_entry.get()
        role = role_var.get()

        if not login or not password:
            messagebox.showerror("Ошибка", "Все поля должны быть заполнены", parent=add_win)
            return

        ok, msg = add_user(login, password, role)
        if ok:
            messagebox.showinfo("Успех", msg, parent=add_win)
            add_win.destroy()
        else:
            messagebox.showerror("Ошибка", msg, parent=add_win)

    add_button = tk.Button(main_frame, text="Добавить", command=do_add, width=20)
    add_button.grid(row=3, column=0, columnspan=2, pady=20)

def unblock_user_action():
    """ Обработчик нажатия кнопки 'Разблокировать пользователя' """
    login = simpledialog.askstring("Разблокировать пользователя", "Введите логин пользователя:")
    if login:
        ok, msg = unblock_user(login)
        if ok:
            messagebox.showinfo("Успех", msg)
        else:
            messagebox.showerror("Ошибка", msg)

def show_users_list_window():
    """ Отображает окно со списком пользователей. """
    users_list_win = tk.Toplevel(root)
    users_list_win.title("Список пользователей")
    users_list_win.geometry("400x300")
    users_list_win.transient(root)
    users_list_win.grab_set()

    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    cursor.execute("SELECT login, role, is_blocked, failed_attempts FROM Users")
    users = cursor.fetchall()
    conn.close()

    text_widget = tk.Text(users_list_win, wrap="word")
    text_widget.pack(expand=True, fill="both", padx=10, pady=10)

    text_widget.insert(tk.END, "Логин\t\tРоль\t\tЗаблокирован\tПопытки\n")
    text_widget.insert(tk.END, "--------------------------------------------------\n")
    for login, role, is_blocked, failed_attempts in users:
        status = "Да" if is_blocked else "Нет"
        text_widget.insert(tk.END, f"{login}\t\t{role}\t\t{status}\t\t{failed_attempts}\n")

    text_widget.config(state="disabled")

def show_rooms_info_window():
    """ Отображает окно с информацией о номерах. """
    rooms_info_win = tk.Toplevel(root)
    rooms_info_win.title("Информация о номерах")
    rooms_info_win.geometry("500x300")
    rooms_info_win.transient(root)
    rooms_info_win.grab_set()

    rooms = get_rooms_info()

    text_widget = tk.Text(rooms_info_win, wrap="word")
    text_widget.pack(expand=True, fill="both", padx=10, pady=10)

    text_widget.insert(tk.END, "Номер\tЭтаж\tКатегория\t\tСтатус\n")
    text_widget.insert(tk.END, "------------------------------------------------------------\n")
    for room_number, floor, category_name, status, _ in rooms:
        text_widget.insert(tk.END, f"{room_number}\t{floor}\t{category_name}\t\t{status}\n")

    text_widget.config(state="disabled")

def show_manage_room_status_window():
    """ Отображает окно для управления статусами номеров. """
    manage_status_win = tk.Toplevel(root)
    manage_status_win.title("Управление статусами номеров")
    manage_status_win.geometry("300x250")
    manage_status_win.transient(root)
    manage_status_win.grab_set()

    rooms = get_rooms_info()

    if not rooms:
        tk.Label(manage_status_win, text="Номера не найдены.").pack(pady=10)
        return

    tk.Label(manage_status_win, text="Выберите номер:").pack(pady=5)
    selected_room_display = tk.StringVar(manage_status_win)
    room_options_dict = {f"Номер {r[0]} (Этаж {r[1]}, {r[2]}, Статус: {r[3]})": r[4] for r in rooms}
    room_menu = tk.OptionMenu(manage_status_win, selected_room_display, *room_options_dict.keys())
    room_menu.pack(pady=5)
    if room_options_dict:
        selected_room_display.set(list(room_options_dict.keys())[0])

    tk.Label(manage_status_win, text="Выберите новый статус:").pack(pady=5)
    new_status_var = tk.StringVar(manage_status_win)
    status_options = ['Чистый', 'Грязный', 'Занят', 'Назначен к уборке', 'В ремонте', 'Свободен']
    status_menu = tk.OptionMenu(manage_status_win, new_status_var, *status_options)
    status_menu.pack(pady=5)
    new_status_var.set(status_options[0])

    def apply_status():
        selected_display = selected_room_display.get()
        room_id_to_update = room_options_dict.get(selected_display)
        status_to_set = new_status_var.get()

        if room_id_to_update is None or not status_to_set:
            messagebox.showwarning("Внимание", "Выберите номер и статус.", parent=manage_status_win)
            return

        ok, msg = update_room_status(room_id_to_update, status_to_set)
        if ok:
            messagebox.showinfo("Успех", msg, parent=manage_status_win)
        else:
            messagebox.showerror("Ошибка", msg, parent=manage_status_win)

    apply_btn = tk.Button(manage_status_win, text="Применить статус", command=apply_status)
    apply_btn.pack(pady=10)

def show_occupancy_window():
    """ Отображает окно с информацией о загруженности номеров. """
    occupancy_win = tk.Toplevel(root)
    occupancy_win.title("Загруженность номеров")
    occupancy_win.geometry("500x400")
    occupancy_win.transient(root)
    occupancy_win.grab_set()

    total_occupancy, category_occupancy, floor_occupancy = calculate_occupancy()

    text_widget = tk.Text(occupancy_win, wrap="word")
    text_widget.pack(expand=True, fill="both", padx=10, pady=10)

    text_widget.insert(tk.END, f"Общая загруженность: {total_occupancy:.1f}%\n\n")

    text_widget.insert(tk.END, "Загруженность по категориям:\n")
    text_widget.insert(tk.END, "Категория\t\tВсего номеров\tЗанято\tЗагруженность\n")
    text_widget.insert(tk.END, "------------------------------------------------------------\n")
    for category, total, occupied in category_occupancy:
        occupancy = (occupied / total * 100) if total > 0 else 0
        text_widget.insert(tk.END, f"{category}\t\t{total}\t\t{occupied}\t{occupancy:.1f}%\n")

    text_widget.insert(tk.END, "\nЗагруженность по этажам:\n")
    text_widget.insert(tk.END, "Этаж\tВсего номеров\tЗанято\tЗагруженность\n")
    text_widget.insert(tk.END, "------------------------------------------------------------\n")
    for floor, total, occupied in floor_occupancy:
        occupancy = (occupied / total * 100) if total > 0 else 0
        text_widget.insert(tk.END, f"{floor}\t{total}\t\t{occupied}\t{occupancy:.1f}%\n")

    text_widget.config(state="disabled")

def show_admin_panel_window():
    """ Создает и отображает главное окно администраторской панели. """
    global admin_window
    if admin_window is None or not admin_window.winfo_exists():
        admin_window = tk.Toplevel(root)
        admin_window.title("Админ-панель")
        admin_window.geometry("300x350")
        admin_window.transient(root)
        admin_window.protocol("WM_DELETE_WINDOW", lambda: admin_window.destroy())

        tk.Label(admin_window, text="Выберите действие:").pack(pady=10)

        tk.Button(admin_window, text="Добавить пользователя", command=add_user_action).pack(pady=5, padx=20, fill='x')
        tk.Button(admin_window, text="Список пользователей", command=show_users_list_window).pack(pady=5, padx=20, fill='x')
        tk.Button(admin_window, text="Информация о номерах", command=show_rooms_info_window).pack(pady=5, padx=20, fill='x')
        tk.Button(admin_window, text="Управление статусами номеров", command=show_manage_room_status_window).pack(pady=5, padx=20, fill='x')
        tk.Button(admin_window, text="Загруженность номеров", command=show_occupancy_window).pack(pady=5, padx=20, fill='x')
        tk.Button(admin_window, text="Разблокировать пользователя", command=unblock_user_action).pack(pady=5, padx=20, fill='x')

    else:
        admin_window.lift()

def ensure_admin_exists():
    """Проверяет наличие администратора и создает его, если не существует"""
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    
    # Проверяем, существует ли администратор
    cursor.execute("SELECT COUNT(*) FROM Users WHERE role='Администратор'")
    admin_count = cursor.fetchone()[0]
    
    if admin_count == 0:
        # Создаем администратора
        cursor.execute("""
            INSERT INTO Users (login, password, role, is_blocked, failed_attempts, must_change_password, last_login)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ('admin', 'admin', 'Администратор', 0, 0, 0, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        print("Администратор создан (логин: admin, пароль: admin)")
    
    conn.close()

# --- GUI ---

root = tk.Tk()
root.title("Авторизация")
root.geometry("300x150")

# Проверяем наличие администратора при запуске
ensure_admin_exists()

# Центрируем окно
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
x = (screen_width - 300) // 2
y = (screen_height - 150) // 2
root.geometry(f"300x150+{x}+{y}")

tk.Label(root, text="Логин:").pack(pady=5)
entry_login = tk.Entry(root)
entry_login.pack(pady=5)

tk.Label(root, text="Пароль:").pack(pady=5)
entry_password = tk.Entry(root, show="*")
entry_password.pack(pady=5)

tk.Button(root, text="Войти", command=login_action).pack(pady=10)

def on_closing():
    if messagebox.askokcancel("Выход", "Вы уверены, что хотите выйти?"):
        root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop() 