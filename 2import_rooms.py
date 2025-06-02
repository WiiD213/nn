import sqlite3
import pandas as pd

DB_FILENAME = 'hotel.db'

def init_rooms_db():
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    
    # Создаем таблицу категорий номеров
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS RoomCategories (
        id_category INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    )
    ''')
    
    # Создаем таблицу номеров
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Rooms (
        id_room INTEGER PRIMARY KEY AUTOINCREMENT,
        room_number TEXT NOT NULL,
        floor INTEGER NOT NULL,
        id_category INTEGER NOT NULL,
        status TEXT DEFAULT 'Свободен',
        FOREIGN KEY (id_category) REFERENCES RoomCategories (id_category)
    )
    ''')
    
    conn.commit()
    conn.close()

def import_rooms_from_excel(excel_file):
    # Читаем данные из Excel
    df = pd.read_excel(excel_file)
    
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    
    # Импортируем категории
    categories = df['Категория'].unique()
    for category in categories:
        cursor.execute("INSERT OR IGNORE INTO RoomCategories (name) VALUES (?)", (category,))
    
    # Получаем ID категорий
    cursor.execute("SELECT id_category, name FROM RoomCategories")
    category_ids = {name: id for id, name in cursor.fetchall()}
    
    # Импортируем номера
    for _, row in df.iterrows():
        cursor.execute("""
            INSERT OR IGNORE INTO Rooms (room_number, floor, id_category, status)
            VALUES (?, ?, ?, ?)
        """, (
            str(row['Номер']),
            int(row['Этаж']),
            category_ids[row['Категория']],
            'Свободен'
        ))
    
    conn.commit()
    conn.close()
    print("Данные успешно импортированы")

if __name__ == "__main__":
    init_rooms_db()
    # Замените 'rooms.xlsx' на имя вашего Excel файла
    import_rooms_from_excel('rooms.xlsx')