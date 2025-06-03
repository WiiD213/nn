import sqlite3

conn = sqlite3.connect('hotel.db')
cursor = conn.cursor()

query = '''
SELECT
    ROUND(
        (
            (
                SELECT SUM(
                    JULIANDAY(
                        MIN(check_out, '2025-03-31')
                    ) - JULIANDAY(
                        MAX(check_in, '2025-03-01')
                    )
                )
                FROM Bookings
                WHERE check_in < '2025-03-31' AND check_out > '2025-03-01'
            )
        ) * 100.0 /
        (
            (SELECT COUNT(*) FROM Rooms) * 31
        )
    , 2) AS occupancy_percent
;'''

cursor.execute(query)
result = cursor.fetchone()[0]
print(f"Процент загрузки номерного фонда за март 2025: {result if result is not None else 0}%")
conn.close()
input("Нажмите Enter для выхода...") 