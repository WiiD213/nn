import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import sqlite3
from datetime import datetime, timedelta
import os

DB_FILENAME = 'autopark.db'

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
    for key, value in kwargs.items():
        cursor.execute(f"UPDATE Users SET {key}=? WHERE id=?", (value, user_id))
    conn.commit()
    conn.close()

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

# --- Функции для работы с базой данных Vehicles ---
def get_vehicles_info():
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id_vehicle, vehicle_number, model, category, status, total_hours
        FROM Vehicles
        ORDER BY vehicle_number
    """)
    vehicles = cursor.fetchall()
    conn.close()
    return vehicles

def update_vehicle_status(vehicle_id, new_status):
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Vehicles SET status=? WHERE id_vehicle=?", (new_status, vehicle_id))
        conn.commit()
        return True, "Статус автомобиля успешно обновлен"
    except sqlite3.Error as e:
        conn.rollback()
        return False, f"Ошибка при обновлении статуса: {e}"
    finally:
        conn.close()

def calculate_vehicle_usage():
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    
    # Получаем общую статистику использования
    cursor.execute("""
        SELECT 
            v.vehicle_number,
            v.model,
            v.total_hours,
            COUNT(u.id_usage) as usage_count,
            SUM(strftime('%s', COALESCE(u.end_time, datetime('now'))) - strftime('%s', u.start_time)) / 3600.0 as total_hours_used
        FROM Vehicles v
        LEFT JOIN Usage u ON v.id_vehicle = u.id_vehicle
        GROUP BY v.id_vehicle
    """)
    usage_stats = cursor.fetchall()
    
    conn.close()
    return usage_stats

# --- GUI функции ---
def show_vehicles_list_window():
    vehicles_win = tk.Toplevel(root)
    vehicles_win.title("Список автомобилей")
    vehicles_win.geometry("600x400")
    
    # Создаем таблицу
    columns = ('Номер', 'Модель', 'Категория', 'Статус', 'Часы использования')
    tree = ttk.Treeview(vehicles_win, columns=columns, show='headings')
    
    # Настраиваем заголовки
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=100)
    
    # Добавляем данные
    vehicles = get_vehicles_info()
    for vehicle in vehicles:
        tree.insert('', 'end', values=vehicle[1:])
    
    # Добавляем скроллбар
    scrollbar = ttk.Scrollbar(vehicles_win, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    
    # Размещаем элементы
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

def show_usage_stats_window():
    stats_win = tk.Toplevel(root)
    stats_win.title("Статистика использования")
    stats_win.geometry("600x400")
    
    # Создаем таблицу
    columns = ('Номер', 'Модель', 'Всего часов', 'Количество использований', 'Процент загрузки')
    tree = ttk.Treeview(stats_win, columns=columns, show='headings')
    
    # Настраиваем заголовки
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=100)
    
    # Добавляем данные
    usage_stats = calculate_vehicle_usage()
    for stat in usage_stats:
        total_hours = stat[3] * 24  # Предполагаем, что каждый день использования = 24 часа
        usage_percent = (stat[4] / total_hours * 100) if total_hours > 0 else 0
        tree.insert('', 'end', values=(
            stat[0],  # Номер
            stat[1],  # Модель
            f"{stat[2]:.1f}",  # Всего часов
            stat[3],  # Количество использований
            f"{usage_percent:.1f}%"  # Процент загрузки
        ))
    
    # Добавляем скроллбар
    scrollbar = ttk.Scrollbar(stats_win, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    
    # Размещаем элементы
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

def show_admin_panel_window():
    admin_win = tk.Toplevel(root)
    admin_win.title("Админ-панель")
    admin_win.geometry("300x250")
    
    tk.Label(admin_win, text="Выберите действие:").pack(pady=10)
    
    tk.Button(admin_win, text="Список автомобилей", 
              command=show_vehicles_list_window).pack(pady=5, padx=20, fill='x')
    tk.Button(admin_win, text="Статистика использования", 
              command=show_usage_stats_window).pack(pady=5, padx=20, fill='x')
    tk.Button(admin_win, text="Добавить пользователя", 
              command=add_user_action).pack(pady=5, padx=20, fill='x')

def add_user_action():
    add_win = tk.Toplevel(root)
    add_win.title("Добавить пользователя")
    add_win.geometry("300x200")
    
    tk.Label(add_win, text="Логин:").pack(pady=5)
    login_entry = tk.Entry(add_win)
    login_entry.pack(pady=5)
    
    tk.Label(add_win, text="Пароль:").pack(pady=5)
    password_entry = tk.Entry(add_win, show="*")
    password_entry.pack(pady=5)
    
    tk.Label(add_win, text="Роль:").pack(pady=5)
    role_var = tk.StringVar(value="Пользователь")
    role_menu = tk.OptionMenu(add_win, role_var, "Пользователь", "Администратор")
    role_menu.pack(pady=5)
    
    def do_add():
        login = login_entry.get()
        password = password_entry.get()
        role = role_var.get()
        
        if not login or not password:
            messagebox.showerror("Ошибка", "Все поля должны быть заполнены")
            return
        
        ok, msg = add_user(login, password, role)
        if ok:
            messagebox.showinfo("Успех", msg)
            add_win.destroy()
        else:
            messagebox.showerror("Ошибка", msg)
    
    tk.Button(add_win, text="Добавить", command=do_add).pack(pady=10)

def login_action():
    login = entry_login.get()
    password = entry_password.get()
    
    if not login or not password:
        messagebox.showerror("Ошибка", "Введите логин и пароль")
        return
    
    user = get_user(login)
    if not user:
        messagebox.showerror("Ошибка", "Неверный логин или пароль")
        return
    
    user_id, db_password, role, is_blocked, failed_attempts, last_login, must_change_password = user
    
    if is_blocked:
        messagebox.showerror("Ошибка", "Аккаунт заблокирован")
        return
    
    if password != db_password:
        failed_attempts += 1
        if failed_attempts >= 3:
            update_user(user_id, is_blocked=1)
            messagebox.showerror("Ошибка", "Аккаунт заблокирован")
        else:
            update_user(user_id, failed_attempts=failed_attempts)
            messagebox.showerror("Ошибка", "Неверный логин или пароль")
        return
    
    update_user(user_id, failed_attempts=0, last_login=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    if must_change_password:
        show_change_password(user_id)
    elif role == "Администратор":
        show_admin_panel_window()
    else:
        messagebox.showinfo("Успех", "Вход выполнен успешно")

def show_change_password(user_id):
    win = tk.Toplevel(root)
    win.title("Смена пароля")
    win.geometry("300x150")
    
    tk.Label(win, text="Новый пароль:").pack(pady=5)
    new_password = tk.Entry(win, show="*")
    new_password.pack(pady=5)
    
    tk.Label(win, text="Подтвердите пароль:").pack(pady=5)
    confirm_password = tk.Entry(win, show="*")
    confirm_password.pack(pady=5)
    
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
    
    tk.Button(win, text="Изменить пароль", command=do_change).pack(pady=10)

# --- Основное окно ---
root = tk.Tk()
root.title("Автопарк - Авторизация")
root.geometry("300x150")

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