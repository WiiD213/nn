import sqlite3

conn = sqlite3.connect('hotel.db')
cursor = conn.cursor()

# Добавим гостя
cursor.execute("INSERT INTO Guests (full_name) VALUES (?)", ("Иванов Иван Иванович",))
guest_id = cursor.lastrowid

# Получим id номеров (первые 3)
room_ids = [row[0] for row in cursor.execute("SELECT id_room FROM Rooms LIMIT 3").fetchall()]

# Добавим бронирования (на март 2025)
bookings = [
    ("2025-03-01", "2025-03-05", "Завершено", guest_id, room_ids[0]),
    ("2025-03-10", "2025-03-15", "Завершено", guest_id, room_ids[1]),
    ("2025-03-20", "2025-03-25", "Завершено", guest_id, room_ids[2]),
]
cursor.executemany(
    "INSERT INTO Bookings (check_in, check_out, status, id_guest, id_room) VALUES (?, ?, ?, ?, ?)",
    bookings
)
conn.commit()

# Количество номеров
cursor.execute("SELECT COUNT(*) FROM Rooms")
room_count = cursor.fetchone()[0]

# Количество проданных ночей в марте 2025
cursor.execute('''
    SELECT SUM(
        JULIANDAY(
            MIN(check_out, '2025-03-31')
        ) - JULIANDAY(
            MAX(check_in, '2025-03-01')
        )
    )
    FROM Bookings
    WHERE check_in < '2025-03-31' AND check_out > '2025-03-01'
''')
sold_nights = cursor.fetchone()[0] or 0

days_in_march = 31
occupancy = (sold_nights / (room_count * days_in_march)) * 100 if room_count > 0 else 0

print(f"Процент загрузки номерного фонда за март 2025: {occupancy:.2f}%")
conn.close() 